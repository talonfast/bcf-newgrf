"""
Software renderer for OpenTTD sprites.

Geometry is turned into a cloud of surface points (position, normal, colour) in
OpenTTD world units: x and y are 1/16 of a tile, z is in "height pixels" (8 per
height level). Points are projected with OpenTTD's dimetric projection

    screen x = (y - x) * 2,   screen y = x + y - z

z-buffered, shaded, supersampled and finally matched to the DOS palette.
"""

import numpy as np
from scipy import ndimage

from newgrf.palette import DOS_PALETTE

_PAL = np.array(DOS_PALETTE, dtype=np.float32)
# Palette entries usable for static graphics: skip transparent (0), company colour (C6-CD) and the animated range (E3-FF).
ALLOWED = np.array([i for i in range(1, 256) if not (0xC6 <= i <= 0xCD) and i < 0xE3], dtype=np.uint8)
_ALLOWED_RGB = _PAL[ALLOWED]

LIGHT = np.array([0.55, -0.30, 1.0], dtype=np.float32)
LIGHT /= np.linalg.norm(LIGHT)
AMBIENT = 0.58
DIFFUSE = 0.52

# Direction order of vehicle sprites: N, NE, E, SE, S, SW, W, NW (direction of travel, OpenTTD Direction enum).
_S = 0.7071067811865476
HEADINGS = [(-_S, -_S), (-1.0, 0.0), (-_S, _S), (0.0, 1.0), (_S, _S), (1.0, 0.0), (_S, -_S), (0.0, -1.0)]


class Cloud:
    """Surface points: pos (N,3) world units, normal (N,3), rgb (N,3) 0..255, and per-point shading gain (N,)."""

    def __init__(self, pos, normal, rgb, gain=None):
        self.pos = np.asarray(pos, dtype=np.float32).reshape(-1, 3)
        self.normal = np.asarray(normal, dtype=np.float32).reshape(-1, 3)
        self.rgb = np.asarray(rgb, dtype=np.float32).reshape(-1, 3)
        self.gain = np.ones(len(self.pos), np.float32) if gain is None else np.asarray(gain, np.float32).reshape(-1)

    @staticmethod
    def concat(clouds):
        clouds = [c for c in clouds if len(c.pos)]
        if not clouds:
            return Cloud(np.zeros((0, 3)), np.zeros((0, 3)), np.zeros((0, 3)))
        return Cloud(np.concatenate([c.pos for c in clouds]), np.concatenate([c.normal for c in clouds]),
                     np.concatenate([c.rgb for c in clouds]), np.concatenate([c.gain for c in clouds]))

    def select(self, mask):
        return Cloud(self.pos[mask], self.normal[mask], self.rgb[mask], self.gain[mask])


def shade(cloud: Cloud) -> np.ndarray:
    lam = np.clip(cloud.normal @ LIGHT, 0.0, 1.0)
    f = (AMBIENT + DIFFUSE * lam) * cloud.gain
    return np.clip(cloud.rgb * f[:, None], 0, 255)


def quantize(rgb: np.ndarray) -> np.ndarray:
    """Nearest allowed palette index for each RGB row (weighted Euclidean distance)."""
    weights = np.array([0.30, 0.59, 0.11], np.float32) * 3
    out = np.empty(len(rgb), np.uint8)
    for s in range(0, len(rgb), 20000):
        chunk = rgb[s:s + 20000]
        diff = chunk[:, None, :] - _ALLOWED_RGB[None, :, :]
        dist = (diff * diff * weights).sum(axis=2)
        out[s:s + 20000] = ALLOWED[np.argmin(dist, axis=1)]
    return out


def render(cloud: Cloud, zoom: int, ss: int = 2, min_coverage: float = 0.5):
    """
    Render a cloud at a zoom level (1, 2 or 4).
    Returns (pixels uint8 HxW palette indices, x_offs, y_offs) relative to the world origin,
    or None when nothing is visible.
    """
    if len(cloud.pos) == 0:
        return None
    s = zoom * ss
    x, y, z = cloud.pos[:, 0], cloud.pos[:, 1], cloud.pos[:, 2]
    sx = np.floor((y - x) * 2 * s).astype(np.int64)
    sy = np.floor((x + y - z) * s).astype(np.int64)
    depth = x + y + 2 * z

    # Align the supersampled grid to whole target pixels.
    x0 = (sx.min() // ss) * ss
    y0 = (sy.min() // ss) * ss
    wd = ((sx.max() - x0) // ss + 1) * ss
    ht = ((sy.max() - y0) // ss + 1) * ss
    px = sx - x0
    py = sy - y0
    flat = py * wd + px

    # Z-buffer: keep the nearest point (largest depth) of every pixel.
    order = np.lexsort((depth, flat))
    flat_sorted = flat[order]
    last = np.ones(len(order), bool)
    last[:-1] = flat_sorted[1:] != flat_sorted[:-1]
    winners = order[last]

    rgb_pts = shade(cloud)
    img = np.zeros((ht * wd, 3), np.float32)
    cov = np.zeros(ht * wd, np.float32)
    img[flat[winners]] = rgb_pts[winners]
    cov[flat[winners]] = 1.0
    img = img.reshape(ht, wd, 3)
    cov = cov.reshape(ht, wd)

    # Downsample: average the covered subpixels of each block.
    th, tw = ht // ss, wd // ss
    cov_b = cov.reshape(th, ss, tw, ss).sum(axis=(1, 3))
    img_b = img.reshape(th, ss, tw, ss, 3).sum(axis=(1, 3))
    mask = cov_b >= min_coverage * ss * ss
    if not mask.any():
        return None
    rgb = img_b[mask] / cov_b[mask][:, None]
    pixels = np.zeros((th, tw), np.uint8)
    pixels[mask] = quantize(rgb)

    # Crop to the visible area.
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    pixels = pixels[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    return pixels, int(x0 // ss + cols[0]), int(y0 // ss + rows[0])


# ---------------------------------------------------------------------------
# Voxel models (aircraft), defined in metres in a local frame:
#   f = forward (nose positive), r = right, u = up (0 = waterline).

class VoxelModel:
    def __init__(self, f_range, r_range, u_range, res=0.05):
        self.res = res
        self.f = np.arange(f_range[0], f_range[1], res, dtype=np.float32)
        self.r = np.arange(r_range[0], r_range[1], res, dtype=np.float32)
        self.u = np.arange(u_range[0], u_range[1], res, dtype=np.float32)
        self.mat = np.zeros((len(self.f), len(self.r), len(self.u)), np.uint8)
        self.materials = {}  # id -> rgb
        self.painters = []   # callables (F, R, U, mat) -> mat, applied to surface points

    def material(self, mid, rgb):
        self.materials[mid] = rgb

    def _sub(self, bbox):
        (f0, f1), (r0, r1), (u0, u1) = bbox
        def rng(axis, a, b_):
            i0 = max(0, int(np.floor((a - axis[0]) / self.res)) - 1)
            i1 = min(len(axis), int(np.ceil((b_ - axis[0]) / self.res)) + 2)
            return slice(i0, i1)
        sf, sr, su = rng(self.f, f0, f1), rng(self.r, r0, r1), rng(self.u, u0, u1)
        F, R, U = np.meshgrid(self.f[sf], self.r[sr], self.u[su], indexing="ij")
        return (sf, sr, su), F, R, U

    def add(self, bbox, inside, mat, overwrite=False):
        """inside(F, R, U) -> bool mask; mat is a material id or callable(F, R, U) -> ids."""
        sl, F, R, U = self._sub(bbox)
        m = inside(F, R, U)
        if not m.any():
            return
        ids = mat(F, R, U) if callable(mat) else np.full(F.shape, mat, np.uint8)
        block = self.mat[sl]
        if not overwrite:
            m &= block == 0
        block[m] = ids[m]

    def paint(self, painter):
        self.painters.append(painter)

    def surface(self):
        occ = self.mat > 0
        surf = occ & ~ndimage.binary_erosion(occ)
        smooth = ndimage.gaussian_filter(occ.astype(np.float32), 1.6)
        gf, gr, gu = np.gradient(smooth)
        idx = np.nonzero(surf)
        n = -np.stack([gf[idx], gr[idx], gu[idx]], axis=1)
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-6)
        F, R, U = self.f[idx[0]], self.r[idx[1]], self.u[idx[2]]
        mat = self.mat[idx].copy()
        for p in self.painters:
            mat = p(F, R, U, mat)
        return F, R, U, n, mat

    def cloud_for_heading(self, heading, metres_per_unit, z_per_metre, surface=None):
        F, R, U, n, mat = surface if surface is not None else self.surface()
        hx, hy = heading
        rx, ry = hy, -hx  # right = forward x up
        X = F * hx + R * rx
        Y = F * hy + R * ry
        pos = np.stack([X / metres_per_unit, Y / metres_per_unit, U * z_per_metre], axis=1)
        nrm = np.stack([n[:, 0] * hx + n[:, 1] * rx, n[:, 0] * hy + n[:, 1] * ry, n[:, 2]], axis=1)
        lut = np.zeros((256, 3), np.float32)
        gain = np.ones(256, np.float32)
        for mid, spec in self.materials.items():
            rgb, g = (spec, 1.0) if len(spec) == 3 else (spec[:3], spec[3])
            lut[mid] = rgb
            gain[mid] = g
        return Cloud(pos, nrm, lut[mat], gain[mat])


# ---------------------------------------------------------------------------
# Shape helpers for voxel models.

def loft(keys, power=2.5, axis_r=0.0):
    """Body of revolution-ish: keys = [(f, half_width, bottom, top)], superellipse sections. Returns (bbox, inside)."""
    k = np.array(keys, np.float32)
    fk, hw, bot, top = k[:, 0], k[:, 1], k[:, 2], k[:, 3]
    def inside(F, R, U):
        w_ = np.interp(F, fk, hw)
        b_ = np.interp(F, fk, bot)
        t_ = np.interp(F, fk, top)
        uc = (b_ + t_) / 2
        hh = np.maximum((t_ - b_) / 2, 1e-3)
        v = (np.abs(R - axis_r) / np.maximum(w_, 1e-3)) ** power + (np.abs(U - uc) / hh) ** power
        return (F >= fk[0]) & (F <= fk[-1]) & (v <= 1.0)
    bbox = ((fk.min(), fk.max()), (axis_r - hw.max(), axis_r + hw.max()), (bot.min(), top.max()))
    return bbox, inside


def interp_profile(keys):
    k = np.array(keys, np.float32)
    return lambda F: np.interp(F, k[:, 0], k[:, 1])


def box(f0, f1, r0, r1, u0, u1):
    bbox = ((f0, f1), (r0, r1), (u0, u1))
    return bbox, lambda F, R, U: (F >= f0) & (F <= f1) & (R >= r0) & (R <= r1) & (U >= u0) & (U <= u1)


def wing(le_f, chord, half_span, u_bottom, thickness, r_center=0.0, taper=1.0, sweep=0.0, dihedral=0.0, round_tips=True):
    """Straight wing; chord tapers linearly to chord*taper at the tips, leading edge sweeps back by `sweep` at the tips."""
    def inside(F, R, U):
        t = np.clip(np.abs(R - r_center) / half_span, 0, 1)
        c = chord * (1 - (1 - taper) * t)
        le = le_f - sweep * t
        ub = u_bottom + dihedral * t
        # Thin airfoil: thicker near the leading third.
        x = np.clip((le - F) / np.maximum(c, 1e-3), 0, 1)
        th = thickness * np.clip(1.6 * np.sqrt(x) * (1 - x) + 0.25, 0.2, 1.0)
        ok = (np.abs(R - r_center) <= half_span) & (F <= le) & (F >= le - c) & (U >= ub) & (U <= ub + th)
        if round_tips:
            ok &= ~((t > 0.985) & ((x < 0.12) | (x > 0.9)))
        return ok
    bbox = ((le_f - sweep - chord, le_f), (r_center - half_span, r_center + half_span),
            (u_bottom - 0.05, u_bottom + abs(dihedral) + thickness + 0.05))
    return bbox, inside


def _point_in_poly(px, py, poly):
    inside = np.zeros(px.shape, bool)
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cond = ((y1 > py) != (y2 > py))
        xint = (x2 - x1) * (py - y1) / ((y2 - y1) if y2 != y1 else 1e-9) + x1
        inside ^= cond & (px < xint)
    return inside


def fin(poly_fu, thickness, r_center=0.0):
    """Vertical fin: polygon in the (f, u) plane, extruded sideways."""
    p = np.array(poly_fu, np.float32)
    def inside(F, R, U):
        return (np.abs(R - r_center) <= thickness / 2) & _point_in_poly(F, U, poly_fu)
    bbox = ((p[:, 0].min(), p[:, 0].max()), (r_center - thickness, r_center + thickness), (p[:, 1].min(), p[:, 1].max()))
    return bbox, inside


def cylinder(p0, p1, radius):
    a = np.array(p0, np.float32)
    bvec = np.array(p1, np.float32) - a
    L2 = float(bvec @ bvec)
    def inside(F, R, U):
        vf, vr, vu = F - a[0], R - a[1], U - a[2]
        t = np.clip((vf * bvec[0] + vr * bvec[1] + vu * bvec[2]) / L2, 0, 1)
        df, dr, du = vf - t * bvec[0], vr - t * bvec[1], vu - t * bvec[2]
        return df * df + dr * dr + du * du <= radius * radius
    lo = np.minimum(a, a + bvec) - radius
    hi = np.maximum(a, a + bvec) + radius
    return ((lo[0], hi[0]), (lo[1], hi[1]), (lo[2], hi[2])), inside


def cone_x(f0, f1, r0_, u_c, radius0, radius1=0.0):
    """Cone along the forward axis (spinners)."""
    def inside(F, R, U):
        t = np.clip((F - f0) / (f1 - f0), 0, 1)
        rad = radius0 + (radius1 - radius0) * t
        return (F >= f0) & (F <= f1) & ((R - r0_) ** 2 + (U - u_c) ** 2 <= rad * rad)
    m = max(radius0, radius1)
    return ((f0, f1), (r0_ - m, r0_ + m), (u_c - m, u_c + m)), inside
