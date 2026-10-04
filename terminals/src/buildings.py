"""
Buildings for OpenTTD objects, on the same voxel renderer as the ships.

A Building is modelled in local coordinates X (long axis), Y (across),
Z (up, in pixels), with its footprint at X in [0, 16*W], Y in [0, 16*D].
render_object() lights the whole building once per view (so shadows fall
across tile seams), then splits it into one sprite per tile, each offset
from that tile's north corner, for OpenTTD's per-tile bounding boxes.
Views 1 and 3 are rotated 90 degrees, with the footprint swapped as OpenTTD
does for objects.
"""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "common"))

import numpy as np

import render
from render import Ship, MAT_RGB, GLOSSY, LIGHT, ZOOM, BASE_STEP, shade, raster, over, _blur

TILE = 16
DETAIL = True      # False: classic OpenTTD style - no people, stains or fine texture


class Building(Ship):
    def __init__(self, w_tiles, d_tiles):
        # square plan: blunt=1 makes the inherited hull half-beam constant
        super().__init__(w_tiles * TILE, d_tiles * TILE, "double", taper=0.05, blunt=1.0)
        self.W, self.D = w_tiles, d_tiles
        self.cx, self.cy = w_tiles * TILE / 2, d_tiles * TILE / 2

    # all builders take local X/Y (footprint coordinates) and Z in pixels
    def bx(self, x0, x1, y0, y1, z0, z1, mat):
        return self.box(x0 - self.cx, x1 - self.cx, y0 - self.cy, y1 - self.cy, z0, z1, mat)

    def sol(self, fn, mat, x0=-1e9, x1=1e9):
        cx, cy = self.cx, self.cy
        return self.solid(lambda U, V, W: fn(U + cx, V + cy, W), mat, x0 - cx, x1 - cx)

    def _top(self):
        """Height of the voxel grid: measured, so free-form solids (towers,
        trees, roofs) are never clipped. A coarse pass finds the highest
        occupied voxel; extra_top is kept as headroom."""
        if getattr(self, "_top_cache", None) is None:
            import render as _r
            fine = _r.STEP
            _r.STEP = 0.5
            try:
                us = np.arange(-self.L / 2, self.L / 2, 0.5) + 0.25
                vs = np.arange(-self.B / 2 - 0.9, self.B / 2 + 0.9, 0.5) + 0.25
                ws = np.arange(0, 120.0, 0.5) + 0.25
                occ = (self.voxelise(us, vs, ws)[0] > 0).any(axis=(0, 1))
                hi = ws[np.nonzero(occ)[0].max()] if occ.any() else 1.0
            finally:
                _r.STEP = fine
            self._top_cache = hi + 2.0
        return self._top_cache

    extra_top = 2.0

    def render_object(self, views=(0, 1, 2, 3)):
        """{view: [(tx, ty, rgba, x0, y0), ...]} at ZOOM, one entry per tile."""
        render.STEP = BASE_STEP
        pos, nrm, m, tag, aux, ao = self.surface()
        base = MAT_RGB[m]
        glossy = GLOSSY[m]
        bright = base.mean(1)
        spec_k = np.where(glossy, 0.9, np.where(bright > 170, 0.22, 0.12)).astype(np.float32)
        shin = np.where(glossy, 40.0, 14.0).astype(np.float32)
        X, Y, Z = pos[:, 0] + self.cx, pos[:, 1] + self.cy, pos[:, 2]
        nu, nv, nz = nrm[:, 0], nrm[:, 1], nrm[:, 2]
        Zm = Z.copy()                                  # model height, for textures
        zs = getattr(self, "zscale", 1.0)
        if zs != 1.0:
            # OpenTTD draws buildings tall: stretch everything above deck /
            # ground level (z > 1) vertically, leaving floats and hulls thin
            Z = np.where(Z > 1.0, 1.0 + (Z - 1.0) * zs, Z)
            nz = nz / zs
            ln = np.sqrt(nu ** 2 + nv ** 2 + nz ** 2) + 1e-6
            nu, nv, nz = nu / ln, nv / ln, nz / ln
        Wp, Dp = self.W * TILE, self.D * TILE
        out = {}
        for view in views:
            if view == 0:
                x, y, nx, ny, fw, fd = X, Y, nu, nv, self.W, self.D
            elif view == 1:
                x, y, nx, ny, fw, fd = Dp - Y, X, -nv, nu, self.D, self.W
            elif view == 2:
                x, y, nx, ny, fw, fd = Wp - X, Dp - Y, -nu, -nv, self.W, self.D
            else:
                x, y, nx, ny, fw, fd = Y, Wp - X, nv, -nu, self.D, self.W
            if getattr(self, "style", "detailed") == "classic":
                col = shade_classic(nx, ny, nz, base, X, Y, Zm)
            else:
                col = shade(x, y, Z, nx, ny, nz, base, ao, glossy, spec_k, shin)
            gx, gy = x - LIGHT[0] * Z / LIGHT[2], y - LIGHT[1] * Z / LIGHT[2]
            tiles = []
            for tx in range(fw):
                for ty in range(fd):
                    tiles.append((tx, ty) + self._tile(x, y, Z, col, gx, gy, tx, ty))
            out[view] = tiles
        return out

    def _tile(self, x, y, z, col, gx, gy, tx, ty):
        ox, oy = tx * TILE, ty * TILE
        sel = (x >= ox) & (x < ox + TILE) & (y >= oy) & (y < oy + TILE)
        gsel = (gx >= ox) & (gx < ox + TILE) & (gy >= oy) & (gy < oy + TILE)
        lx, ly, lz = x[sel] - ox, y[sel] - oy, z[sel]
        sx, sy = ZOOM * 2 * (ly - lx), ZOOM * ((lx + ly) - lz)
        gsx = ZOOM * 2 * ((gy[gsel] - oy) - (gx[gsel] - ox))
        gsy = ZOOM * ((gx[gsel] - ox) + (gy[gsel] - oy))
        allx = np.concatenate([sx, gsx, [0.0]])
        ally = np.concatenate([sy, gsy, [0.0]])
        x0 = (int(np.floor(allx.min())) // ZOOM - 1) * ZOOM
        y0 = (int(np.floor(ally.min())) // ZOOM - 1) * ZOOM
        wdt = -(-(int(np.ceil(allx.max())) - x0 + 3) // ZOOM) * ZOOM
        hgt = -(-(int(np.ceil(ally.max())) - y0 + 3) // ZOOM) * ZOOM
        classic = getattr(self, "style", "detailed") == "classic"
        if classic:
            bc, ba = raster_hard(sx, sy, lx + ly + 2 * lz, col[sel], x0, y0, wdt, hgt)
            return np.dstack([bc, ba]), x0, y0
        bc, ba = raster(sx, sy, lx + ly + 2 * lz, col[sel], x0, y0, wdt, hgt)
        sh = np.zeros(hgt * wdt, np.float32)
        sh[(gsy.astype(int) - y0) * wdt + (gsx.astype(int) - x0)] = 1
        sh_a = 0.3 * np.clip(_blur(sh.reshape(hgt, wdt), 3, 2) * 1.6, 0, 1)
        sh_c = np.broadcast_to(np.array([20, 22, 26], np.float32), (hgt, wdt, 3))
        c, a = over(bc, ba, sh_c, sh_a)
        return np.dstack([c, a]), x0, y0


def shade_classic(nx, ny, nz, base, X=None, Y=None, Z=None):
    """OpenTTD base-set look (cf. the Swedish Houses set): one flat tone per
    face orientation - roofs lightest, the left (south-west, +x) face mid, the
    right (south-east, +y) face darker - plus hand-drawn texture: roof tile
    rows on slopes, plank/siding lines on walls and a little pixel noise."""
    top = np.clip(nz, 0, 1)
    left = np.clip(nx, 0, 1)
    right = np.clip(ny, 0, 1)
    tot = top + left + right + 1e-6
    level = (1.08 * top + 0.95 * left + 0.74 * right) / tot
    level = np.round(level * 10) / 10
    if Z is not None:
        slope = (nz > 0.2) & (nz < 0.95)                  # pitched roofs: tile rows
        level = np.where(slope & (np.mod(np.floor(Z / 0.45), 2) == 1), level * 0.9, level)
        wall = np.abs(nz) < 0.2                           # walls: siding / plank lines
        level = np.where(wall & (np.mod(Z, 0.5) < 0.1), level * 0.92, level)
        h = np.sin(X * 91.7 + Y * 47.3 + Z * 13.1) * 43758.5453
        level = level * (0.96 + 0.08 * (h - np.floor(h)))  # hand-pixelled noise
    return np.clip(base * level[:, None], 0, 255)


OUTLINE = 0.78      # classic style: edges only slightly darkened, like base-set sprites


def raster_hard(sx, sy, depth, col, x0, y0, wdt, hgt):
    """Single-sample z-buffer (crisp pixel edges) with a dark outline round
    the silhouette and along depth breaks, like hand-drawn sprites."""
    order = np.argsort(depth)
    lin = (np.floor(sy + 0.5).astype(int) - y0) * wdt + (np.floor(sx + 0.5).astype(int) - x0)
    buf = np.full(hgt * wdt, -1, dtype=np.int64)
    buf[lin[order]] = order
    hit = buf >= 0
    img = np.zeros((hgt * wdt, 3), np.float32)
    img[hit] = col[buf[hit]]
    dmap = np.full(hgt * wdt, -1e9, np.float32)
    dmap[hit] = depth[buf[hit]]
    img = img.reshape(hgt, wdt, 3)
    a = hit.reshape(hgt, wdt)
    dmap = dmap.reshape(hgt, wdt)
    edge = np.zeros_like(a)
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-2, 0), (2, 0), (0, -2), (0, 2)):
        na = np.roll(np.roll(a, dy, 0), dx, 1)
        edge |= a & ~na                            # silhouette, 2 px at 4x
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nd = np.roll(np.roll(dmap, dy, 0), dx, 1)
        edge |= a & (nd - dmap > 4.0)              # a real step to something in front
    img[edge] *= OUTLINE
    return img, a.astype(np.float32)


# ---------------------------------------------------------------------------
# Tsawwassen Quay Market (BC Ferries, 2009; Bird Construction / Fast + Epp)
# ---------------------------------------------------------------------------

def quay_market():
    """The ~100 m retail hall at Tsawwassen terminal (photos on Commons,
    2009): floor-to-ceiling glass on a grey mullion grid with glulam timber
    columns, a thin mono-pitch roof rising towards the front with a deep
    overhang, timber soffit and angled glulam brackets; louvred panels and a
    grey tiled end wall with vending machines; paved surround."""
    b = Building(2, 1)
    X0, X1, Y0, Y1 = 2.0, 30.0, 4.5, 12.0          # glass box
    ZF, ZR = 0.6, 12.6                             # floor, eaves (drawn tall, as OpenTTD buildings are)
    # paving with joints, a grass verge and a tree behind
    b.sol(lambda X, Y, Z: [
        ((Z <= 0.25), "concrete"),
        ((Z <= 0.25) & ((np.mod(X, 2.0) < 0.06) | (np.mod(Y, 2.0) < 0.06)), "grey"),
        ((Z <= 0.3) & (Y < 2.6), "grass")], None)
    b.bx(X0 - 0.3, X1 + 0.3, Y0 - 0.3, Y1 + 0.3, 0.25, ZF, "concrete")    # plinth

    def hall(X, Y, Z):
        inside = (X >= X0) & (X <= X1) & (Y >= Y0) & (Y <= Y1) & (Z > ZF) & (Z <= ZR)
        face = (np.minimum(X - X0, X1 - X) < 0.12) | (np.minimum(Y - Y0, Y1 - Y) < 0.12)
        along = np.where(np.minimum(Y - Y0, Y1 - Y) < 0.12, X, Y)
        bay = np.mod(along - X0, 1.25)
        mull = bay < 0.13
        timber_col = mull & (np.mod(np.floor((along - X0) / 1.25), 2) == 0)
        transom = (np.abs(Z - 4.6) < 0.09) | (np.abs(Z - 8.8) < 0.09) | (Z < ZF + 0.35)
        out = [(inside, "white"), (inside & face, "glass"), (inside & face & mull, "steel"),
               (inside & face & transom, "steel"), (inside & face & timber_col, "timber")]
        # louvred panels in two front bays (first photo)
        louv = inside & (Y > Y1 - 0.12) & (((X > 3.4) & (X < 6.4)) | ((X > 7.2) & (X < 10.2))) & \
            (Z < 8.6)
        out += [(louv, "louvre"), (louv & (np.mod(Z, 0.36) < 0.1), "dark")]
        # grey tiled end wall with a door and two vending machines (third photo)
        end = inside & (X < X0 + 0.12)
        out += [(end, "stone"), (end & ((np.mod(Y, 0.9) < 0.04) | (np.mod(Z, 0.9) < 0.04)), "grey"),
                (end & (np.abs(Y - 8.2) < 0.7) & (Z < 5.6), "glass")]
        # shop signs glowing behind the glass
        for (sx0, sx1, m) in ((13.0, 14.6, "red"), (18.5, 20.2, "green"), (24.0, 25.6, "yellow")):
            out.append((inside & (Y > Y1 - 0.12) & (X > sx0) & (X < sx1) & (np.abs(Z - 6.8) < 0.4),
                        m))
        return out
    b.sol(hall, None, X0, X1)
    b.bx(X0 - 0.5, X0 - 0.12, 6.0, 7.0, ZF, 4.0, "red")            # vending machines
    b.bx(X0 - 0.5, X0 - 0.12, 9.6, 10.6, ZF, 4.0, "red")

    # mono-pitch roof rising to the front, deep overhang, timber soffit
    RX0, RX1, RY0, RY1 = 0.6, 31.4, 2.6, 14.2

    def roof_bottom(Y):
        return ZR + 0.12 * (Y - RY0)

    def roof(X, Y, Z):
        zb = roof_bottom(Y)
        r = (X >= RX0) & (X <= RX1) & (Y >= RY0) & (Y <= RY1) & (Z > zb) & (Z <= zb + 0.7)
        fascia = r & ((np.minimum(X - RX0, RX1 - X) < 0.15) | (np.minimum(Y - RY0, RY1 - Y) < 0.15))
        soffit = r & (Z < zb + 0.15)
        ribs = r & (Z > zb + 0.55) & (np.mod(X, 0.5) < 0.08)
        return [(r, "roofmetal"), (soffit, "timber"), (ribs, "grey"), (fascia, "alu")]
    b.sol(roof, None, RX0, RX1)

    # glulam brackets: angled struts from the wall out to the roof edge, front and back
    def brackets(X, Y, Z):
        on = np.mod(X - X0, 2.5) < 0.22
        out = []
        for wall_y, edge_y in ((Y1, RY1 - 0.3), (Y0, RY0 + 0.3)):
            t = np.clip((Y - wall_y) / (edge_y - wall_y), 0, 1)
            zline = (ZR - 2.0) + t * (roof_bottom(edge_y) - (ZR - 2.0))
            span = (np.sign(edge_y - wall_y) * (Y - wall_y) >= 0) & \
                (np.abs(Y - wall_y) <= abs(edge_y - wall_y))
            out.append((on & span & (np.abs(Z - zline) < 0.22) & (X > X0) & (X < X1), "timber"))
        # glulam edge beam just outside the fascia and beam ends poking out past
        # it - the bits of the timber structure visible from above
        for ry, sgn in ((RY1, 1), (RY0, -1)):
            zb = roof_bottom(ry)
            yy = sgn * (Y - ry)
            out.append(((yy > 0) & (yy < 0.22) & (Z > zb - 0.35) & (Z <= zb + 0.25) &
                        (X > RX0) & (X < RX1), "timber"))
            out.append((on & (yy > 0) & (yy < 0.55) & (Z > zb - 0.3) & (Z <= zb + 0.35) &
                        (X > X0) & (X < X1), "timber"))
        return out
    b.sol(brackets, None, RX0, RX1)

    # rooftop units
    b.bx(8.0, 10.4, 6.0, 8.6, roof_bottom(6.0) + 0.7, roof_bottom(6.0) + 1.8, "steel")
    b.bx(20.0, 21.6, 6.4, 8.0, roof_bottom(6.4) + 0.7, roof_bottom(6.4) + 1.5, "steel")
    # outside: benches, lamp posts, a tree and shrubs
    for x in (12.0, 17.0, 22.0):
        b.bx(x, x + 1.4, 13.2, 13.6, 0.25, 0.75, "timber")
    for x in (5.0, 15.5, 26.0):
        b.bx(x - 0.07, x + 0.07, 14.6, 14.74, 0.25, 9.5, "steel")
        b.bx(x - 0.25, x + 0.25, 14.45, 14.9, 9.2, 9.6, "dark")
    b.bx(27.3, 27.6, 1.2, 1.5, 0.25, 3.0, "timber")
    b.ellipsoid(27.45 - b.cx, 1.35 - b.cy, 5.0, 1.1, 1.1, 2.8, "forest")
    for x in (4.0, 9.0, 14.0, 19.0):
        b.ellipsoid(x - b.cx, 1.6 - b.cy, 0.6, 0.7, 0.5, 0.6, "grass")

    # cafe tables with umbrellas, planters, bins and people on the front walk
    rng = np.random.RandomState(21)
    for x in (12.5, 15.5, 18.5):
        b.bx(x - 0.5, x + 0.5, 15.1, 15.9, 0.9, 1.05, "white")
        b.bx(x - 0.05, x + 0.05, 15.45, 15.55, 0.25, 2.9, "steel")
        b.sol(lambda X, Y, Z, x=x: ((X - x) ** 2 + (Y - 15.5) ** 2 < 1.15 ** 2) &
              (Z > 2.6) & (Z <= 3.0 - 0.3 * np.sqrt((X - x) ** 2 + (Y - 15.5) ** 2)),
              "umbrella", x - 1.2, x + 1.2)
    for x in (3.0, 29.0):
        _planter(b, x, 14.0, 0.25, r=0.8, tree=True)
    b.bx(10.4, 10.9, 13.2, 13.7, 0.25, 1.3, "bcfblue")             # bins
    b.bx(23.6, 24.1, 13.2, 13.7, 0.25, 1.3, "bcfblue")
    _people(b, 9, 3.0, 29.0, 12.8, 15.6, 0.25, rng,
            avoid=[(11.5, 19.5, 14.8, 16.2), (11.7, 13.7, 13.1, 13.8), (16.7, 18.7, 13.1, 13.8)])
    return b


# ---------------------------------------------------------------------------
# The rest of Tsawwassen terminal (photos on Commons: tollbooths, loading
# ramp, passenger gangway, lineup, views from arriving ferries, 2008-2024)
# ---------------------------------------------------------------------------

def _stain(X, Y, seed, scale=3.0, cover=0.22):
    """Blotchy mask for weathering patches on ground surfaces."""
    if not DETAIL:
        return np.zeros(np.shape(X), bool)
    v = (np.sin(X / scale * 1.7 + seed) * np.sin(Y / scale * 1.3 + seed * 2.1) +
         0.5 * np.sin(X / scale * 3.9 + Y / scale * 2.7 + seed * 0.7))
    return v > 1.15 - cover * 3


def _paving(b, mat="concrete", joints=2.0, seed=0.0):
    b.sol(lambda X, Y, Z: [((Z <= 0.25), mat),
                           ((Z <= 0.25) & _stain(X, Y, seed + 1.0), "concrete2"),
                           ((Z <= 0.25) & ((np.mod(X, joints) < 0.06) |
                                           (np.mod(Y, joints) < 0.06)), "grey")], None)


def _car(b, x, y, z, along_x, mat, length=5.2, width=2.4, truck=False):
    """A car (or box truck) at OpenTTD road-vehicle scale, centred on x, y."""
    lx, ly = (length, width) if along_x else (width, length)
    x0, x1, y0, y1 = x - lx / 2, x + lx / 2, y - ly / 2, y + ly / 2
    if truck:
        b.bx(x0, x1, y0, y1, z + 0.3, z + 1.6, "dark")
        bl = (x0 + 1.6, x1, y0, y1) if along_x else (x0, x1, y0 + 1.6, y1)
        b.bx(*bl, z + 1.6, z + 4.6, "white")
        cab = (x0, x0 + 1.5, y0 + 0.1, y1 - 0.1) if along_x else (x0 + 0.1, x1 - 0.1, y0, y0 + 1.5)
        b.bx(*cab, z + 1.6, z + 3.4, mat)
        return
    b.bx(x0, x1, y0, y1, z + 0.3, z + 1.7, mat)
    gl = (x0 + 1.2, x1 - 1.0, y0 + 0.2, y1 - 0.2) if along_x else (x0 + 0.2, x1 - 0.2, y0 + 1.2, y1 - 1.0)
    b.bx(*gl, z + 1.7, z + 2.6, "glass")
    rf = (gl[0] + 0.1, gl[1] - 0.1, gl[2] + 0.05, gl[3] - 0.05)
    b.bx(*rf, z + 2.6, z + 2.75, mat)


CAR_COLOURS = ["car1", "car2", "car3", "car4", "car5", "car6", "white", "steel", "grey"]
CLOTHES = ["car1", "car2", "denim", "car4", "car5", "car6", "white", "red", "navy", "orange"]


# ---- street furniture and people (OpenTTD road-vehicle scale) ------------

def _person(b, x, y, z, rng):
    """A standing person: legs, coloured top, head."""
    if not DETAIL:
        return
    top = CLOTHES[rng.randint(len(CLOTHES))]
    b.bx(x - 0.2, x + 0.2, y - 0.16, y + 0.16, z, z + 0.85, "denim" if rng.rand() < 0.6 else "dark")
    b.bx(x - 0.24, x + 0.24, y - 0.2, y + 0.2, z + 0.85, z + 1.6, top)
    b.ellipsoid(x - b.cx, y - b.cy, z + 1.82, 0.19, 0.19, 0.22, "skin" if rng.rand() < 0.7 else "skin2")


def _people(b, n, x0, x1, y0, y1, z, rng, avoid=()):
    if not DETAIL:
        return
    for _ in range(n):
        for _try in range(8):
            x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
            if not any(ax0 <= x <= ax1 and ay0 <= y <= ay1 for ax0, ax1, ay0, ay1 in avoid):
                _person(b, x, y, z, rng)
                break


def _bench(b, x, y, z, along_x=True, length=1.6):
    lx, ly = (length, 0.5) if along_x else (0.5, length)
    b.bx(x - lx / 2, x + lx / 2, y - ly / 2, y + ly / 2, z + 0.35, z + 0.55, "timber")
    if along_x:
        b.bx(x - lx / 2, x + lx / 2, y + 0.15, y + 0.25, z + 0.55, z + 1.0, "timber")
    else:
        b.bx(x + 0.15, x + 0.25, y - ly / 2, y + ly / 2, z + 0.55, z + 1.0, "timber")
    b.bx(x - lx / 2 + 0.1, x - lx / 2 + 0.2, y - ly / 2, y + ly / 2, z, z + 0.35, "steel")


def _planter(b, x, y, z, r=0.9, tree=False):
    b.bx(x - r, x + r, y - r, y + r, z, z + 0.7, "stone")
    b.bx(x - r + 0.1, x + r - 0.1, y - r + 0.1, y + r - 0.1, z + 0.6, z + 0.75, "dark")
    if tree:
        b.bx(x - 0.12, x + 0.12, y - 0.12, y + 0.12, z + 0.7, z + 3.0, "timber")
        b.ellipsoid(x - b.cx, y - b.cy, z + 4.2, 1.0, 1.0, 1.7, "forest")
    else:
        b.ellipsoid(x - b.cx, y - b.cy, z + 0.95, r * 0.8, r * 0.8, 0.45, "grass")


def _lamp(b, x, y, z, h=9.5):
    b.bx(x - 0.07, x + 0.07, y - 0.07, y + 0.07, z, z + h, "steel")
    b.bx(x - 0.25, x + 0.25, y - 0.2, y + 0.2, z + h - 0.3, z + h + 0.1, "dark")


def _flagpole(b, x, y, z, flag, h=11.0):
    """Flag on a pole; flag = 'canada' or 'bc'."""
    b.bx(x - 0.06, x + 0.06, y - 0.06, y + 0.06, z, z + h, "white")
    fz0, fz1, fy0, fy1 = z + h - 1.6, z + h - 0.1, y + 0.06, y + 0.1
    if flag == "canada":
        b.bx(x - 0.02, x + 0.02, fy0, fy0 + 2.6, fz0, fz1, "white")
        b.bx(x - 0.03, x + 0.03, fy0, fy0 + 0.65, fz0, fz1, "flagred")
        b.bx(x - 0.03, x + 0.03, fy0 + 1.95, fy0 + 2.6, fz0, fz1, "flagred")
        b.bx(x - 0.03, x + 0.03, fy0 + 1.05, fy0 + 1.55, fz0 + 0.45, fz1 - 0.45, "flagred")
    else:   # British Columbia: blue waves below, red/white union, gold sun
        b.bx(x - 0.02, x + 0.02, fy0, fy0 + 2.6, fz0, fz1, "white")
        b.bx(x - 0.03, x + 0.03, fy0, fy0 + 2.6, fz1 - 0.55, fz1, "flagred")
        b.bx(x - 0.03, x + 0.03, fy0, fy0 + 2.6, fz0, fz0 + 0.6, "blue")
        b.bx(x - 0.03, x + 0.03, fy0 + 0.9, fy0 + 1.7, fz0 + 0.55, fz0 + 0.9, "yellow")


def _bollards(b, x0, x1, y, z, step=1.4):
    x = x0
    while x <= x1:
        b.bx(x - 0.15, x + 0.15, y - 0.15, y + 0.15, z, z + 0.9, "yellow")
        x += step


def _signpost(b, x, y, z, mat="bcfblue", h=3.4, w=1.4, along_x=True):
    b.bx(x - 0.06, x + 0.06, y - 0.06, y + 0.06, z, z + h, "steel")
    if along_x:
        b.bx(x - w / 2, x + w / 2, y - 0.05, y + 0.05, z + h - 1.0, z + h, mat)
        b.bx(x - w / 2 + 0.2, x + w / 2 - 0.2, y + 0.05, y + 0.08, z + h - 0.75, z + h - 0.3, "white")
    else:
        b.bx(x - 0.05, x + 0.05, y - w / 2, y + w / 2, z + h - 1.0, z + h, mat)
        b.bx(x + 0.05, x + 0.08, y - w / 2 + 0.2, y + w / 2 - 0.2, z + h - 0.75, z + h - 0.3, "white")



def terminal_building():
    """Main terminal: glazed ground floor with timber columns and blue louvres
    (like the Quay Market next door), silver ribbed metal-clad upper floor
    with a window band and the BC Ferries wordmark on its front."""
    from render import decal_mask, decal_size
    b = Building(2, 2)
    b.extra_top = 4.0
    _paving(b)
    X0, X1, Y0, Y1 = 3.0, 29.0, 6.0, 26.0
    b.bx(X0 - 0.4, X1 + 0.4, Y0 - 0.4, Y1 + 0.4, 0.25, 0.6, "concrete")

    def body(X, Y, Z):
        inside = (X >= X0) & (X <= X1) & (Y >= Y0) & (Y <= Y1) & (Z > 0.6) & (Z <= 16.0)
        face = (np.minimum(X - X0, X1 - X) < 0.12) | (np.minimum(Y - Y0, Y1 - Y) < 0.12)
        along = np.where(np.minimum(Y - Y0, Y1 - Y) < 0.12, X, Y)
        ground = Z <= 8.0
        bay = np.mod(along - X0, 1.3)
        out = [(inside, "white"), (inside & face & ground, "glass"),
               (inside & face & ground & (bay < 0.13), "steel"),
               (inside & face & ground & (bay < 0.2) & (np.mod(np.floor((along - X0) / 1.3), 2) == 0),
                "timber"),
               (inside & face & ground & (np.abs(Z - 4.6) < 0.1), "steel")]
        # blue louvre panels in the front bays (lineup photo)
        louv = inside & face & ground & (Y > Y1 - 0.12) & (Z < 6.2) & \
            (((X > 6.0) & (X < 9.6)) | ((X > 11.0) & (X < 14.6)))
        out += [(louv, "bcfblue"), (louv & (np.mod(Z, 0.4) < 0.12), "navy")]
        # upper floor: silver ribbed cladding, window band
        up = inside & face & ~ground
        front = up & (Y > Y1 - 0.12)
        # the wordmark sits on the silver upper facade (Quay Market photos);
        # X runs to the viewer's left along this face, so read it reversed
        iw, ih = decal_size("wordmark")
        ink = front & decal_mask("wordmark", 22.0 - X, Z, 0.0, 12.2, 3.4,
                                 width=3.4 * iw / ih / 2.24)
        win = up & (Z > 10.6) & (Z < 12.8) & (np.mod(along, 2.0) < 1.6) & ~(front & (X > 15.0))
        out += [(up, "alu"), (up & (np.mod(along, 0.45) < 0.1), "steel"), (win, "window"),
                (ink, "bcfblue"),
                (inside & (Z > 15.7), "membrane"), (inside & (np.abs(Z - 8.0) < 0.2) & face, "navy")]
        return out
    b.sol(body, None, X0, X1)
    # entrance canopy on the front
    b.bx(13.0, 19.0, Y1, Y1 + 2.4, 6.4, 6.9, "white")
    b.bx(13.0, 19.0, Y1, Y1 + 2.4, 6.2, 6.4, "timber")
    # rooftop plant and lamp posts in the plaza
    b.bx(6.0, 10.0, 9.0, 13.0, 16.0, 17.6, "steel")
    b.bx(20.0, 23.0, 10.0, 12.0, 16.0, 17.2, "steel")
    for x in (4.0, 16.0, 28.0):
        b.bx(x - 0.07, x + 0.07, 29.6, 29.74, 0.25, 10.0, "steel")
        b.bx(x - 0.25, x + 0.25, 29.45, 29.9, 9.7, 10.1, "dark")

    # Canada and BC flags, entrance sign, planters, bike rack, people
    rng = np.random.RandomState(31)
    _flagpole(b, 24.0, 28.6, 0.25, "canada")
    _flagpole(b, 26.5, 28.6, 0.25, "bc")
    b.bx(13.6, 18.4, Y1 + 2.35, Y1 + 2.45, 6.9, 7.8, "navy")      # canopy sign band
    for x in (6.0, 10.0, 22.0):
        _planter(b, x, 28.4, 0.25, r=0.8, tree=(x != 10.0))
    for i in range(5):                                              # bike rack
        b.bx(2.0 + i * 0.5, 2.08 + i * 0.5, 27.5, 28.7, 0.25, 1.0, "steel")
    _people(b, 14, 4.0, 28.0, 26.6, 30.5, 0.25, rng,
            avoid=[(5.0, 7.0, 27.4, 29.4), (21.0, 23.0, 27.4, 29.4), (23.5, 27.0, 28.2, 29.0)])
    # rooftop plant: louvred grilles
    b.sol(lambda X, Y, Z: (X > 6.0) & (X < 10.0) & (Y > 9.0) & (Y < 13.0) & (Z > 16.0) & (Z < 17.6) &
          (np.mod(Z, 0.35) < 0.1) & ((np.minimum(X - 6.0, 10.0 - X) < 0.1) |
                                    (np.minimum(Y - 9.0, 13.0 - Y) < 0.1)), "dark", 6.0, 10.0)
    return b


def toll_plaza():
    """One tile of the toll plaza: two lanes along X, booths on the islands,
    the long white canopy and a white lattice light tower through it."""
    b = Building(1, 1)
    b.extra_top = 6.0

    def ground(X, Y, Z):
        g = Z <= 0.2
        lanes = [(g, "asphalt"),
                 (g & (np.mod(X, 3.0) < 1.6) & ((np.abs(Y - 4.0) < 0.08) | (np.abs(Y - 12.0) < 0.08)),
                  "laneline")]
        isl = ((np.abs(Y - 8.0) < 1.0) | (Y < 0.6) | (Y > 15.4)) & (Z <= 0.6)
        return lanes + [(isl, "concrete"), (isl & ((X < 2.0) | (X > 14.0)) & (Z > 0.4), "yellow")]
    b.sol(ground, None)
    for yc in (8.0, 0.0, 16.0):                      # booths (edge ones are half booths)
        y0, y1 = max(0.0, yc - 0.85), min(16.0, yc + 0.85)
        if y1 - y0 < 0.5:
            continue
        b.bx(6.0, 10.0, y0, y1, 0.6, 5.2, "white")
        b.bx(6.1, 9.9, y0, y1, 2.6, 4.4, "glass")
        b.bx(5.8, 10.2, y0, y1, 5.2, 5.6, "bcfblue")
    # canopy
    b.bx(3.0, 13.0, 0.0, 16.0, 9.6, 10.4, "white")
    b.bx(3.0, 13.0, 0.0, 16.0, 9.4, 9.6, "steel")
    b.bx(2.9, 3.1, 0.0, 16.0, 9.4, 10.6, "bcfblue")
    b.bx(12.9, 13.1, 0.0, 16.0, 9.4, 10.6, "bcfblue")

    def lattice(X, Y, Z):
        x0, x1, y0, y1 = 7.2, 8.8, 7.2, 8.8
        inb = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1) & (Z > 0.6) & (Z <= 24.0)
        post = (np.minimum(X - x0, x1 - X) < 0.18) & (np.minimum(Y - y0, y1 - Y) < 0.18)
        face = (np.minimum(X - x0, x1 - X) < 0.12) | (np.minimum(Y - y0, y1 - Y) < 0.12)
        along = np.where(np.minimum(X - x0, x1 - X) < 0.12, Y - y0, X - x0)
        diag = np.abs(np.mod(Z, 3.2) - along * 2.0) < 0.25
        return inb & (post | (face & diag) | (face & (np.mod(Z, 3.2) < 0.15)))
    b.sol(lattice, "white", 7.0, 9.0)
    b.bx(6.8, 9.2, 6.8, 9.2, 24.0, 24.6, "white")
    for d in (-1, 1):                                # floodlights on the mast
        b.bx(7.6 + d * 1.0, 8.4 + d * 1.0, 7.6, 8.4, 23.4, 24.0, "dark")

    # lane signals (green arrow / red X) and lane numbers on the canopy edge,
    # bollards at the island noses, attendants in the booths
    rng = np.random.RandomState(41)
    for yc, sig in ((4.0, "signgreen"), (12.0, "flagred")):
        b.bx(12.95, 13.25, yc - 0.9, yc + 0.9, 8.4, 9.4, "dark")
        b.bx(13.25, 13.3, yc - 0.6, yc + 0.6, 8.55, 9.25, sig)
        b.bx(2.75, 3.05, yc - 1.1, yc + 1.1, 8.3, 9.4, "bcfblue")
        b.bx(2.7, 2.75, yc - 0.5, yc + 0.5, 8.5, 9.2, "white")
    for x in (1.0, 15.0):
        b.bx(x - 0.15, x + 0.15, 7.85, 8.15, 0.6, 1.5, "yellow")
    _person(b, 8.0, 8.0, 0.6, rng)
    return b


def holding_lanes(variant=0):
    """Vehicle holding compound: four lanes along X with cars queued
    (OpenTTD road-vehicle scale). Variant 1 has a box truck and gaps."""
    b = Building(1, 1)
    rng = np.random.RandomState(7 + variant)

    def ground(X, Y, Z):
        g = Z <= 0.2
        lane_c = np.abs(np.mod(Y, 4.0) - 2.0) < 0.5
        return [(g, "asphalt"), (g & lane_c & _stain(X, Y * 3, 2.0 + variant, 1.2, 0.3), "oil"),
                (g & ((np.abs(np.mod(Y + 2.0, 4.0) - 2.0) > 1.92)), "laneline")]
    b.sol(ground, None)
    for lane in range(4):
        y = 2.0 + lane * 4.0
        for slot, x in enumerate((3.9, 11.4)):
            if variant == 1 and (lane, slot) == (2, 1):
                continue
            truck = variant == 1 and (lane, slot) == (1, 0)
            _car(b, x + rng.uniform(-0.4, 0.4), y, 0.2, True,
                 CAR_COLOURS[rng.randint(len(CAR_COLOURS))], truck=truck,
                 length=6.4 if truck else 5.2)

    # lane-head sign posts and a light standard; drivers stretching their legs
    _signpost(b, 15.2, 4.0, 0.2, "bcfblue", h=3.4, w=1.6, along_x=False)
    _signpost(b, 15.2, 12.0, 0.2, "bcfblue", h=3.4, w=1.6, along_x=False)
    _lamp(b, 15.4, 8.0, 0.2, h=12.0)
    _people(b, 2 + variant, 1.0, 14.0, 3.6, 4.4, 0.2, rng)
    return b


def berth_ramp():
    """Berth link span: the steel vehicle ramp running out to the water edge
    (+X) between two tall white tower legs carrying the blue machinery house
    and hoist cables, on a concrete apron with yellow guide lines."""
    b = Building(1, 1)
    b.extra_top = 6.0
    _paving(b)

    def ramp(X, Y, Z):
        zt = 1.4 - 0.9 * np.clip(X / 16.0, 0, 1)        # deck slopes down to the ship
        deck = (Y > 4.2) & (Y < 11.8) & (Z > 0.25) & (Z <= zt)
        edge = deck & ((np.abs(Y - 4.5) < 0.25) | (np.abs(Y - 11.5) < 0.25))
        center = deck & (np.abs(Y - 8.0) < 0.1) & (np.mod(X, 2.0) < 1.1)
        rail = (np.minimum(np.abs(Y - 4.3), np.abs(Y - 11.7)) < 0.08) & (Z > zt) & (Z <= zt + 1.1) & \
            ((Z > zt + 0.95) | (np.mod(X, 1.2) < 0.12))
        return [(deck, "steel"), (edge, "yellow"), (center, "yellow"), (rail, "yellow")]
    b.sol(ramp, None)
    for y in (3.0, 13.0):                                # tower legs
        b.bx(12.4, 13.8, y - 0.7, y + 0.7, 0.25, 26.0, "white")
        b.bx(12.3, 13.9, y - 0.8, y + 0.8, 0.25, 1.4, "concrete")
    b.bx(12.0, 14.2, 2.0, 14.0, 24.0, 26.6, "white")       # cross beam
    b.bx(12.2, 14.0, 5.2, 10.8, 26.6, 29.4, "stackblue")   # machinery house
    b.bx(12.1, 14.1, 5.0, 11.0, 29.4, 29.8, "white")
    for y in (5.0, 11.0):                                  # hoist cables
        b.bx(13.0, 13.12, y - 0.06, y + 0.06, 1.0, 24.0, "dark")

    # ramp operator's booth, barrier arms, traffic lights, chevrons
    b.bx(1.0, 3.6, 0.6, 3.2, 0.25, 3.6, "white")
    b.bx(0.9, 3.7, 0.5, 3.3, 3.6, 3.9, "bcfblue")
    b.bx(1.0, 3.6, 0.55, 3.25, 1.8, 2.9, "window")
    b.bx(1.1, 3.5, 0.65, 3.15, 1.8, 2.9, "white")
    for y0, y1 in ((4.4, 7.9), (8.1, 11.6)):                      # barrier arms
        b.sol(lambda X, Y, Z, y0=y0, y1=y1: [
            ((np.abs(X - 4.0) < 0.1) & (Y > y0) & (Y < y1) & (np.abs(Z - 1.9) < 0.1), "white"),
            ((np.abs(X - 4.0) < 0.1) & (Y > y0) & (Y < y1) & (np.abs(Z - 1.9) < 0.1) &
             (np.mod(Y, 0.8) < 0.4), "flagred")], None, 3.8, 4.2)
    b.bx(3.85, 4.15, 3.85, 4.15, 0.25, 2.0, "steel")
    b.bx(3.85, 4.15, 11.85, 12.15, 0.25, 2.0, "steel")
    for y in (3.6, 12.4):                                          # traffic lights
        b.bx(5.4, 5.55, y - 0.07, y + 0.07, 0.25, 3.4, "steel")
        b.bx(5.3, 5.65, y - 0.25, y + 0.25, 3.4, 4.6, "dark")
        b.bx(5.65, 5.7, y - 0.12, y + 0.12, 4.15, 4.45, "flagred")
        b.bx(5.65, 5.7, y - 0.12, y + 0.12, 3.6, 3.9, "signgreen")
    return b


def wingwall():
    """Berth wingwall on water, lining the +Y edge of its tile: white steel
    pillars with dark fender panels facing the berth in the neighbouring
    tile, a yellow-railed catwalk on top, and a rusty sheet-pile cell dolphin
    with a concrete cap at one end."""
    b = Building(1, 1)
    b.extra_top = 3.0
    py = 13.4                                          # pillar row
    for x in (6.0, 9.5, 13.0):
        b.sol(lambda X, Y, Z, x=x: ((X - x) ** 2 + (Y - py) ** 2 < 0.55 ** 2) & (Z <= 6.0),
              "white", x - 0.6, x + 0.6)
    b.bx(5.2, 15.8, py + 0.5, py + 0.8, 0.4, 5.4, "steel")       # fender frame
    b.bx(5.2, 15.8, py + 0.8, py + 1.2, 0.4, 5.4, "dark")        # rubber fenders, berth side
    b.bx(4.0, 16.0, py - 0.9, py + 0.6, 6.0, 6.3, "grey")         # catwalk
    for yy in (py - 0.85, py + 0.55):
        b.sol(lambda X, Y, Z, yy=yy: (np.abs(Y - yy) < 0.06) & (X > 4.0) & (Z > 6.3) & (Z <= 7.4) &
              ((Z > 7.25) | (np.mod(X, 1.2) < 0.12)), "yellow", 4.0, 16.0)
    # sheet-pile cell dolphin
    b.sol(lambda X, Y, Z: [
        (((X - 2.6) ** 2 + (Y - 12.4) ** 2 < 2.4 ** 2) & (Z <= 4.2), "rust"),
        (((X - 2.6) ** 2 + (Y - 12.4) ** 2 < 2.4 ** 2) & (Z <= 4.2) &
         (np.mod(np.arctan2(Y - 12.4, X - 2.6) * 14, 1) < 0.25), "dark"),
        (((X - 2.6) ** 2 + (Y - 12.4) ** 2 < 2.6 ** 2) & (Z > 4.2) & (Z <= 5.0), "concrete")],
        None, 0.0, 5.3)

    # navigation light, life rings, ladders
    b.bx(15.3, 15.5, py - 0.1, py + 0.1, 6.3, 8.0, "white")
    b.ellipsoid(15.4 - b.cx, py - b.cy, 8.25, 0.25, 0.25, 0.3, "signgreen")
    for x in (7.8, 11.3):
        b.bx(x - 0.3, x + 0.3, py - 0.95, py - 0.88, 6.6, 7.2, "orange")
    for x in (8.0, 14.6):
        b.sol(lambda X, Y, Z, x=x: (np.abs(Y - (py + 1.25)) < 0.06) & (np.abs(X - x) < 0.35) &
              (Z > 0.2) & (Z <= 6.0) & ((np.abs(np.abs(X - x) - 0.3) < 0.06) |
                                        (np.mod(Z, 0.5) < 0.08)), "steel", x - 0.4, x + 0.4)
    return b


def walkway():
    """Overhead passenger walkway segment: enclosed blue truss bridge with
    white diagonal bracing and a glazed band, on a white column."""
    b = Building(1, 1)
    b.extra_top = 6.0
    _paving(b)
    Y0, Y1, Z0, Z1 = 6.0, 10.0, 10.0, 14.6

    def tube(X, Y, Z):
        inb = (Y >= Y0) & (Y <= Y1) & (Z > Z0) & (Z <= Z1)
        side = inb & (np.minimum(Y - Y0, Y1 - Y) < 0.15)
        truss = side & (np.abs(np.mod(X, 4.0) - (Z - Z0) * 4.0 / (Z1 - Z0)) < 0.35)
        chord = side & ((np.abs(Z - Z0 - 0.3) < 0.25) | (np.abs(Z - Z1 + 0.3) < 0.25))
        glass = side & (Z > Z0 + 1.6) & (Z < Z1 - 1.2)
        return [(inb, "bcfblue"), (glass, "glass"), (truss, "white"), (chord, "white"),
                (inb & (Z > Z1 - 0.25), "white")]
    b.sol(tube, None)
    b.bx(7.3, 8.7, 7.3, 8.7, 0.25, 10.0, "white")          # column
    b.bx(6.8, 9.2, 5.6, 10.4, 9.4, 10.0, "white")          # cross head

    # passengers walking through the glazed walkway
    rng = np.random.RandomState(51)
    for x in (2.5, 6.0, 11.5, 14.0):
        _person(b, x + rng.uniform(-0.6, 0.6), 8.0 + rng.uniform(-0.8, 0.8), Z0 + 0.1, rng)
    return b


def control_tower():
    """Terminal control tower: white round shaft, blue-banded glass cab with
    an overhanging white roof and antenna mast, on a small base building."""
    b = Building(1, 1)
    b.extra_top = 6.0
    _paving(b)
    b.bx(3.0, 13.0, 3.0, 13.0, 0.25, 4.2, "white")
    b.bx(3.0, 13.0, 3.0, 13.0, 1.6, 3.2, "window")
    b.bx(3.2, 12.8, 3.2, 12.8, 1.6, 3.2, "white")          # leaves a window band only on faces
    r = lambda X, Y: np.sqrt((X - 8.0) ** 2 + (Y - 8.0) ** 2)  # noqa: E731
    b.sol(lambda X, Y, Z: [
        ((r(X, Y) < 1.9) & (Z > 4.2) & (Z <= 24.0), "white"),
        ((r(X, Y) < 3.3) & (Z > 22.0) & (Z <= 27.0), "white"),
        ((r(X, Y) < 3.3) & (r(X, Y) > 3.1) & (Z > 23.0) & (Z <= 26.0), "glass"),
        ((r(X, Y) < 3.3) & (r(X, Y) > 3.1) & (Z > 23.0) & (Z <= 26.0) &
         (np.mod(np.arctan2(Y - 8.0, X - 8.0) * 8 / np.pi, 1) < 0.12), "white"),
        ((r(X, Y) < 3.4) & (Z > 22.0) & (Z <= 23.0), "stackblue"),
        ((r(X, Y) < 3.8) & (Z > 27.0) & (Z <= 27.6), "white"),
        ((r(X, Y) < 3.8) & (Z > 26.6) & (Z <= 27.0), "stackblue")], None, 4.0, 12.0)
    b.bx(7.9, 8.1, 7.9, 8.1, 27.6, 32.0, "steel")
    b.bx(7.0, 9.0, 7.95, 8.05, 30.6, 30.8, "steel")

    # balcony railing round the cab, radar on the roof, entrance sign
    b.sol(lambda X, Y, Z: (np.abs(r(X, Y) - 3.75) < 0.07) & (Z > 22.0) & (Z <= 23.0) &
          ((Z > 22.85) | (np.mod(np.arctan2(Y - 8.0, X - 8.0) * 10, 1) < 0.12)), "steel", 4.0, 12.0)
    b.sol(lambda X, Y, Z: (r(X, Y) < 3.8) & (r(X, Y) > 3.3) & (Z > 21.8) & (Z <= 22.0), "steel",
          4.0, 12.0)
    b.bx(6.3, 9.7, 7.9, 8.1, 29.0, 29.2, "white")
    b.bx(6.0, 10.0, 12.95, 13.05, 2.6, 3.8, "bcfblue")
    b.bx(7.2, 8.8, 12.95, 13.06, 0.25, 2.4, "glass")
    return b


# ---------------------------------------------------------------------------
# Foot passengers
# ---------------------------------------------------------------------------

def bus_shelter():
    """Foot-passenger and bus shelter along X: glass back and end screens,
    a white canopy on posts, benches, people waiting, the bus stop sign,
    a bin and a bike rack; kerb and a strip of bus lane in front (+Y)."""
    b = Building(1, 1)
    b.extra_top = 2.0
    rng = np.random.RandomState(61)
    b.sol(lambda X, Y, Z: [((Z <= 0.25) & (Y < 11.0), "concrete"),
                           ((Z <= 0.25) & (Y < 11.0) & ((np.mod(X, 2.0) < 0.06) |
                                                         (np.mod(Y, 2.0) < 0.06)), "grey"),
                           ((Z <= 0.2) & (Y >= 11.0), "asphalt"),
                           ((Z <= 0.2) & (Y >= 11.0) & (np.abs(Y - 14.5) < 0.1) &
                            (np.mod(X, 3.0) < 1.6), "laneline"),
                           ((Z <= 0.35) & (np.abs(Y - 11.0) < 0.25), "concrete")], None)
    b.bx(1.5, 14.5, 4.6, 4.75, 0.25, 4.6, "glass")                 # back screen
    for x in (1.5, 14.35):
        b.bx(x, x + 0.15, 4.6, 8.4, 0.25, 4.6, "glass")             # end screens
    for x in (1.6, 8.0, 14.4):
        b.bx(x - 0.1, x + 0.1, 4.5, 4.7, 0.25, 5.0, "steel")
        b.bx(x - 0.1, x + 0.1, 8.5, 8.7, 0.25, 5.0, "steel")
    b.sol(lambda X, Y, Z: (X > 1.0) & (X < 15.0) & (Y > 4.2) & (Y < 9.6) &
          (Z > 5.0 + 0.08 * (Y - 4.2)) & (Z <= 5.35 + 0.08 * (Y - 4.2)), "white", 1.0, 15.0)
    b.bx(1.0, 15.0, 9.5, 9.6, 5.2, 5.8, "bcfblue")                 # canopy fascia
    for x in (4.2, 8.0, 11.8):
        _bench(b, x, 5.4, 0.25, True, length=2.4)
    _people(b, 6, 2.2, 13.8, 6.4, 9.6, 0.25, rng)
    for x in (4.2, 11.8):
        _person(b, x - 0.5, 5.2, 0.5, rng)                          # seated
    b.bx(15.0, 15.12, 10.3, 10.42, 0.25, 4.2, "steel")               # stop sign
    b.bx(14.75, 15.37, 10.32, 10.4, 3.2, 4.4, "signgreen")
    b.bx(0.6, 1.1, 9.6, 10.1, 0.25, 1.3, "bcfblue")                  # bin
    for i in range(4):                                              # bike rack
        b.bx(0.4, 1.4, 1.0 + i * 0.6, 1.08 + i * 0.6, 0.25, 1.0, "steel")
    return b


def foot_plaza(variant=0):
    """Foot-passenger plaza: paved square with benches round planted trees,
    an information board, ticket machines and people coming and going."""
    b = Building(1, 1)
    b.extra_top = 3.0
    rng = np.random.RandomState(71 + variant)
    b.sol(lambda X, Y, Z: [((Z <= 0.25), "concrete"),
                           ((Z <= 0.25) & ((np.mod(X + Y, 2.8) < 0.08) |
                                           (np.mod(X - Y, 2.8) < 0.08)), "stone")], None)
    for (x, y) in ((4.0, 4.0), (12.0, 12.0)) if variant == 0 else ((4.0, 12.0), (12.0, 4.0)):
        _planter(b, x, y, 0.25, r=1.3, tree=True)
        _bench(b, x, y + 2.0, 0.25, True)
        _bench(b, x + 2.0, y, 0.25, False)
    ix, iy = (12.0, 4.0) if variant == 0 else (4.0, 4.0)
    b.bx(ix - 0.1, ix + 0.1, iy - 0.8, iy + 0.8, 0.25, 3.2, "steel")   # info board
    b.bx(ix - 0.06, ix + 0.06, iy - 1.0, iy + 1.0, 1.6, 3.4, "bcfblue")
    b.bx(ix + 0.06, ix + 0.09, iy - 0.8, iy + 0.8, 1.8, 3.2, "white")
    for k in range(2):                                              # ticket machines
        tx = (4.0 if variant == 0 else 12.0) + k * 1.2
        b.bx(tx - 0.4, tx + 0.4, 11.4, 12.0, 0.25, 2.2, "bcfblue")
        b.bx(tx - 0.3, tx + 0.3, 11.36, 11.4, 1.2, 1.9, "window")
    _lamp(b, 8.0, 8.0, 0.25, h=10.0)
    _people(b, 9 + 3 * variant, 0.8, 15.2, 0.8, 15.2, 0.25, rng,
            avoid=[(2.5, 6.5, 2.5, 6.8), (10.5, 14.5, 10.5, 14.8), (2.5, 6.5, 10.5, 14.8),
                   (10.5, 14.5, 2.5, 6.8), (7.6, 8.4, 7.6, 8.4)])
    return b


def walkway_tower():
    """Stair and elevator tower where the overhead walkway comes down: a
    glazed stair core with white frame and blue cap, the walkway stub
    leaving towards +X at deck height, a ground-level door and canopy."""
    b = Building(1, 1)
    b.extra_top = 14.0              # the core and walkway stub are free-form solids
    _paving(b)
    X0, X1, Y0, Y1 = 3.0, 10.0, 4.0, 12.0

    def core(X, Y, Z):
        inb = (X >= X0) & (X <= X1) & (Y >= Y0) & (Y <= Y1) & (Z > 0.25) & (Z <= 16.0)
        face = inb & ((np.minimum(X - X0, X1 - X) < 0.12) | (np.minimum(Y - Y0, Y1 - Y) < 0.12))
        frame = face & ((np.mod(Z, 3.6) < 0.25) | (np.minimum(np.minimum(X - X0, X1 - X),
                                                               np.minimum(Y - Y0, Y1 - Y) + 99) < 0.0))
        corner = inb & (np.minimum(X - X0, X1 - X) < 0.35) & (np.minimum(Y - Y0, Y1 - Y) < 0.35)
        # stair flights seen through the glass
        stair = face & (np.abs(np.mod(Z - (X - X0) * 0.9, 3.6) - 1.8) < 0.18)
        return [(inb, "white"), (face, "glass"), (stair, "steel"), (frame, "white"),
                (corner, "white"), (inb & (Z > 15.4), "stackblue")]
    b.sol(core, None, X0, X1)
    # walkway stub towards +X (same section as the walkway segments)
    Z0, Z1 = 10.0, 14.6

    def stub(X, Y, Z):
        inb = (X > X1) & (Y >= 6.0) & (Y <= 10.0) & (Z > Z0) & (Z <= Z1)
        side = inb & (np.minimum(Y - 6.0, 10.0 - Y) < 0.15)
        truss = side & (np.abs(np.mod(X, 4.0) - (Z - Z0) * 4.0 / (Z1 - Z0)) < 0.35)
        glass = side & (Z > Z0 + 1.6) & (Z < Z1 - 1.2)
        return [(inb, "bcfblue"), (glass, "glass"), (truss, "white"), (inb & (Z > Z1 - 0.25), "white")]
    b.sol(stub, None, X1, 16.0)
    b.bx(X0 - 1.6, X0, 6.5, 9.5, 3.4, 3.8, "white")                  # door canopy
    b.bx(X0 - 0.05, X0 + 0.05, 7.2, 8.8, 0.25, 3.0, "glass")
    rng = np.random.RandomState(81)
    _people(b, 3, 0.6, 2.6, 5.0, 11.0, 0.25, rng)
    return b


# ---------------------------------------------------------------------------
# Swartz Bay terminal (photos on Commons 2013-2018: Departures/Arrivals
# entrance, Lands End cafe building, traffic tower, foot passenger bridge,
# berths with blue-over-orange fender panels and lattice ramp gantries)
# ---------------------------------------------------------------------------

def _face_text(b, name, x_center, z_center, height, y_face, mat, x0, x1, plate_y=0.35):
    """Standing letters (decal `name`) on a front (+Y) edge, read correctly."""
    from render import decal_mask, decal_size
    iw, ih = decal_size(name)
    width = height * iw / ih / 2.24
    b.sol(lambda X, Y, Z: (Y > y_face - plate_y) & (Y < y_face) & (X > x0) & (X < x1) &
          decal_mask(name, x_center - X, Z, 0.0, z_center, height, width=width), mat, x0, x1)


def sb_terminal():
    """Swartz Bay foot passenger building: low white block with blue steel
    portal frames over the DEPARTURES and ARRIVALS entrances, a blue BC
    Ferries panel between them, big navy letters on the roof edge, a white
    cantilever canopy, roof deck with railings and radar mast, three flags."""
    b = Building(2, 1)
    b.extra_top = 8.0
    rng = np.random.RandomState(91)
    _paving(b)
    X0, X1, Y0, Y1, ZT = 3.0, 29.0, 3.0, 10.5, 6.0

    def body(X, Y, Z):
        inside = (X >= X0) & (X <= X1) & (Y >= Y0) & (Y <= Y1) & (Z > 0.25) & (Z <= ZT)
        front = inside & (Y > Y1 - 0.12)
        doors = front & (Z < 3.6) & (((X > 6.2) & (X < 12.8)) | ((X > 19.2) & (X < 25.8)))
        bands = front & (np.abs(Z - 4.6) < 0.5)
        return [(inside, "white"), (doors, "glass"), (doors & (np.mod(X, 1.1) < 0.12), "steel"),
                (bands, "window"), (inside & (Z > ZT - 0.2), "membrane")]
    b.sol(body, None, X0, X1)
    for xa, xb in ((5.8, 13.2), (18.8, 26.2)):                    # blue portal frames
        for xp in (xa, xb - 0.6):
            b.bx(xp, xp + 0.6, Y1, Y1 + 0.6, 0.25, 6.6, "bcfblue")
        b.bx(xa, xb, Y1, Y1 + 0.6, 6.0, 6.6, "bcfblue")
        b.bx(xa + 0.6, xb - 0.6, Y1 + 0.3, Y1 + 2.6, 3.8, 4.1, "bcfblue")  # pergola rail
    b.bx(13.6, 18.4, Y1, Y1 + 0.2, 1.0, 5.6, "bcfblue")            # BC Ferries panel
    _face_text(b, "wordmark", 16.0, 3.8, 1.3, Y1 + 0.25, "white", 13.7, 18.3, plate_y=0.1)
    b.bx(X0 - 0.5, X1 + 0.5, Y0 - 0.3, Y1 + 2.0, ZT, ZT + 0.4, "white")  # cantilever roof
    _face_text(b, "departures", 9.5, ZT + 1.75, 2.5, Y1 + 1.6, "navy", 3.6, 15.4)
    _face_text(b, "arrivals", 22.5, ZT + 1.75, 2.5, Y1 + 1.6, "navy", 17.0, 28.4)
    # roof deck: railings, upper cabin, radar mast
    b.sol(lambda X, Y, Z: (Z > ZT + 0.4) & (Z <= ZT + 1.5) & (X > X0) & (X < X1) & (Y > Y0) &
          (Y < Y1 + 1.8) & ((np.minimum(X - X0, X1 - X) < 0.08) | (np.minimum(Y - Y0, Y1 + 1.8 - Y) < 0.08)) &
          ((Z > ZT + 1.35) | (np.mod(X + Y, 1.0) < 0.1)), "white", X0, X1)
    b.bx(10.0, 18.0, 4.0, 8.0, ZT + 0.4, ZT + 3.0, "white")
    b.bx(10.0, 18.0, 7.95, 8.05, ZT + 1.3, ZT + 2.4, "window")
    b.bx(13.9, 14.1, 5.9, 6.1, ZT + 3.0, ZT + 9.0, "steel")
    b.bx(13.2, 14.8, 5.95, 6.05, ZT + 8.2, ZT + 8.35, "white")
    b.radome(14.0 - b.cx, 7.0 - b.cy, ZT + 3.0, r=0.4)
    # flags: BC, Canada, BC Ferries (blue)
    _flagpole(b, 12.5, 13.4, 0.25, "bc", h=12.0)
    _flagpole(b, 16.0, 13.4, 0.25, "canada", h=12.5)
    b.bx(19.44, 19.56, 13.34, 13.46, 0.25, 12.0, "white")
    b.bx(19.48, 19.52, 13.46, 15.9, 10.4, 11.9, "bcfblue")
    # departure board, planter, benches, people
    b.bx(14.3, 15.9, 13.0, 13.1, 2.6, 4.2, "dark")
    b.bx(14.4, 15.8, 13.1, 13.12, 2.8, 3.8, "signgreen")
    _planter(b, 21.0, 14.2, 0.25, r=0.8)
    _bench(b, 4.0, 14.5, 0.25, True)
    _bench(b, 27.5, 14.5, 0.25, True)
    _people(b, 12, 4.0, 28.0, 11.8, 15.4, 0.25, rng,
            avoid=[(12.0, 13.0, 13.0, 14.0), (15.5, 16.5, 13.0, 14.0), (19.0, 20.0, 13.0, 14.0),
                   (20.0, 22.0, 13.2, 15.2), (14.0, 16.2, 12.8, 13.3)])
    return b


def sb_landsend():
    """Lands End cafe building: two-storey taupe stucco block with window
    rows, rooftop railing and plant, an outside balcony and stair along the
    side, a black barrel-vault canopy over the entrance stair, a blue sign
    band, and the white peaked market tent with its blue skirt next door."""
    b = Building(2, 1)
    b.extra_top = 6.0
    rng = np.random.RandomState(101)
    _paving(b)
    X0, X1, Y0, Y1 = 6.0, 21.0, 3.0, 11.0

    def body(X, Y, Z):
        inside = (X >= X0) & (X <= X1) & (Y >= Y0) & (Y <= Y1) & (Z > 0.25) & (Z <= 12.0)
        face = inside & ((np.minimum(X - X0, X1 - X) < 0.12) | (np.minimum(Y - Y0, Y1 - Y) < 0.12))
        along = np.where(np.minimum(Y - Y0, Y1 - Y) < 0.12, X, Y)
        win = face & (np.mod(along, 3.0) < 1.8) & (((Z > 2.0) & (Z < 4.0)) | ((Z > 7.4) & (Z < 9.6)))
        return [(inside, "stucco"), (win, "window"),
                (face & (np.abs(Z - 5.6) < 0.35), "bcfblue"), (inside & (Z > 11.8), "membrane"),
                (face & (np.abs(Z - 6.2) < 0.15), "dark")]
    b.sol(body, None, X0, X1)
    _face_text(b, "landsend", 15.0, 10.6, 0.9, Y1 + 0.12, "white", 12.0, 18.5, plate_y=0.12)
    # side balcony and stair along -X
    b.bx(X0 - 2.0, X0, Y0, Y1, 6.0, 6.3, "stucco")
    b.sol(lambda X, Y, Z: (X > X0 - 2.0) & (X < X0) & (Y > Y0) & (Y < Y1) & (Z > 6.3) & (Z <= 7.4) &
          ((X - (X0 - 2.0) < 0.08) | (np.minimum(Y - Y0, Y1 - Y) < 0.08)) &
          ((Z > 7.25) | (np.mod(Y, 0.6) < 0.1)), "stucco", X0 - 2.0, X0)
    for k in range(10):                                           # stair down to the plaza
        b.bx(X0 - 2.0, X0 - 0.2, Y1 + k * 0.45, Y1 + (k + 1) * 0.45, 0.25, 6.0 - k * 0.6, "concrete")
    # black barrel-vault canopy over the entrance stair (front)
    b.sol(lambda X, Y, Z: (X > X1 - 1.0) & (X < X1 + 3.4) & (Y > 9.0) & (Y < 13.6) &
          (np.abs(np.sqrt((Y - 11.3) ** 2 + (Z - 3.8) ** 2) - 2.3) < 0.18) & (Z > 3.8),
          "dark", X1 - 1.0, X1 + 3.4)
    for k in range(8):
        b.bx(X1 + 0.2, X1 + 3.0, Y1 + k * 0.4, Y1 + (k + 1) * 0.4, 0.25, 4.0 - k * 0.45, "concrete")
    # rooftop rail and plant
    b.sol(lambda X, Y, Z: (Z > 12.0) & (Z <= 13.0) & (X > X0) & (X < X1) & (Y > Y0) & (Y < Y1) &
          ((np.minimum(X - X0, X1 - X) < 0.08) | (np.minimum(Y - Y0, Y1 - Y) < 0.08)) &
          ((Z > 12.85) | (np.mod(X + Y, 1.2) < 0.1)), "steel", X0, X1)
    b.bx(13.0, 16.0, 5.0, 7.5, 12.0, 13.6, "steel")
    # the market tent: peaked cream roof, blue skirt, stalls, people
    TX0, TX1, TY0, TY1 = 23.5, 30.5, 5.0, 12.0

    def tent(X, Y, Z):
        dx, dy = np.abs(X - (TX0 + TX1) / 2) / 3.5, np.abs(Y - (TY0 + TY1) / 2) / 3.5
        peak = 4.0 + 4.0 * (1 - np.maximum(dx, dy))
        roof = (dx <= 1) & (dy <= 1) & (Z > 3.6) & (Z <= peak) & (Z > peak - 0.25)
        skirt = (dx <= 1) & (dy <= 1) & (Z > 3.0) & (Z <= 4.0) & (np.maximum(dx, dy) > 0.96)
        return [(roof, "tentcream"), (skirt, "blue")]
    b.sol(tent, None, TX0, TX1)
    for x in (TX0 + 0.1, TX1 - 0.2):
        for y in (TY0 + 0.1, TY1 - 0.2):
            b.bx(x, x + 0.12, y, y + 0.12, 0.25, 3.2, "white")
    b.bx(TX0 + 1.0, TX1 - 1.0, TY0 + 1.0, TY0 + 2.0, 0.25, 1.4, "timber")
    b.bx(TX0 + 1.0, TX1 - 1.0, TY0 + 1.1, TY0 + 1.9, 1.4, 1.6, "car5")
    _people(b, 5, TX0 + 0.5, TX1 - 0.5, TY0 + 2.5, TY1 + 2.5, 0.25, rng)
    _people(b, 3, 6.0, 20.0, 12.5, 15.5, 0.25, rng)
    return b


def sb_tower():
    """Swartz Bay traffic tower: a square white tower with a blue stripe,
    the BC Ferries panel, an overhanging glass cab with white roof, antenna
    and radar; a small fenced playground beside it."""
    b = Building(1, 1)
    b.extra_top = 6.0
    rng = np.random.RandomState(111)
    _paving(b)
    b.bx(5.4, 10.6, 5.4, 10.6, 0.25, 1.0, "concrete")
    b.bx(6.5, 9.5, 6.5, 9.5, 1.0, 14.0, "white")                   # shaft
    b.bx(7.6, 8.4, 9.5, 9.6, 1.0, 14.0, "bcfblue")                 # blue stripe
    b.bx(5.6, 10.4, 5.6, 10.4, 14.0, 19.0, "white")                # upper block
    b.bx(6.2, 9.8, 10.4, 10.5, 15.8, 17.6, "white")
    _face_text(b, "wordmark", 8.0, 16.7, 0.9, 10.55, "bcfblue", 6.0, 10.0, plate_y=0.1)
    b.bx(5.2, 10.8, 5.2, 10.8, 19.0, 21.6, "window")               # cab
    for x in (5.2, 10.6):
        b.bx(x, x + 0.2, 5.2, 10.8, 19.0, 21.6, "white")
    b.bx(4.6, 11.4, 4.6, 11.4, 21.6, 22.2, "white")                # overhanging roof
    b.bx(7.9, 8.1, 7.9, 8.1, 22.2, 26.0, "steel")
    b.radome(9.5 - b.cx, 6.5 - b.cy, 22.2, r=0.4)
    # playground: red and yellow climbing frame, slide, low fence
    b.bx(1.0, 4.4, 11.0, 14.6, 0.25, 0.3, "orange")
    for x, y in ((1.4, 11.4), (3.8, 11.4), (1.4, 13.8), (3.8, 13.8)):
        b.bx(x, x + 0.2, y, y + 0.2, 0.3, 3.4, "red")
    b.bx(1.4, 4.0, 11.4, 14.0, 2.4, 2.6, "yellow")
    b.bx(1.4, 4.0, 11.4, 14.0, 3.4, 3.8, "red")
    b.sol(lambda X, Y, Z: (X > 4.0) & (X < 6.4) & (Y > 12.4) & (Y < 13.2) &
          (np.abs(Z - (2.5 - (X - 4.0) * 0.9)) < 0.12), "yellow", 4.0, 6.4)
    b.sol(lambda X, Y, Z: (((np.abs(X - 0.4) < 0.05) | (np.abs(X - 6.8) < 0.05)) & (Y > 10.4) & (Y < 15.4) |
                           ((np.abs(Y - 10.4) < 0.05) | (np.abs(Y - 15.4) < 0.05)) & (X > 0.4) & (X < 6.8)) &
          (Z > 0.25) & (Z <= 1.2) & ((Z > 1.1) | (np.mod(X + Y, 0.5) < 0.08)), "yellow", 0.3, 6.9)
    _people(b, 3, 1.0, 6.0, 10.8, 15.0, 0.3, rng,
            avoid=[(1.2, 4.2, 11.2, 14.2)])
    return b


def sb_footbridge():
    """Swartz Bay foot passenger bridge segment: an open white Warren-truss
    walkway (deck, top chords, railings) on a slender white column."""
    b = Building(1, 1)
    b.extra_top = 6.0
    _paving(b)
    Y0, Y1, Z0, Z1 = 6.2, 9.8, 10.0, 13.6

    def truss(X, Y, Z):
        inb = (Y >= Y0) & (Y <= Y1) & (Z > Z0) & (Z <= Z1)
        side = inb & (np.minimum(Y - Y0, Y1 - Y) < 0.14)
        diag = side & (np.abs(np.abs(np.mod(X, 3.2) - 1.6) * (Z1 - Z0) / 1.6 - (Z - Z0)) < 0.3)
        chords = side & ((Z < Z0 + 0.3) | (Z > Z1 - 0.3))
        deck = inb & (Z <= Z0 + 0.25)
        top = inb & (Z > Z1 - 0.2) & (np.mod(X, 1.6) < 0.2)
        return [(deck, "grey"), (diag, "white"), (chords, "white"), (top, "white")]
    b.sol(truss, None)
    b.bx(7.4, 8.6, 7.4, 8.6, 0.25, 10.0, "white")
    b.bx(7.0, 9.0, 5.8, 10.2, 9.4, 10.0, "white")
    rng = np.random.RandomState(121)
    for x in (3.0, 11.0):
        _person(b, x + rng.uniform(-1, 1), 8.0 + rng.uniform(-0.6, 0.6), Z0 + 0.25, rng)
    return b


def sb_bridgetower():
    """Tall white frame tower at the berth: four posts with bracing levels,
    stair flights inside, machinery room with railings on top, the walkway
    arriving from -X at deck height and the tilting gangway sloping down to
    the ship's upper deck towards +X."""
    b = Building(1, 1)
    b.extra_top = 8.0
    _paving(b)
    X0, X1, Y0, Y1 = 4.0, 10.0, 4.5, 11.5

    def frame(X, Y, Z):
        inb = (X >= X0) & (X <= X1) & (Y >= Y0) & (Y <= Y1) & (Z > 0.25) & (Z <= 22.0)
        post = inb & (np.minimum(X - X0, X1 - X) < 0.45) & (np.minimum(Y - Y0, Y1 - Y) < 0.45)
        face = inb & ((np.minimum(X - X0, X1 - X) < 0.15) | (np.minimum(Y - Y0, Y1 - Y) < 0.15))
        level = face & (np.mod(Z, 5.0) < 0.35)
        brace = face & (np.abs(np.mod(Z, 5.0) - np.where(np.minimum(X - X0, X1 - X) < 0.15,
                                                         (Y - Y0) * 5.0 / (Y1 - Y0),
                                                         (X - X0) * 5.0 / (X1 - X0))) < 0.3)
        stair = inb & (np.abs(Y - 8.0) < 1.2) & \
            (np.abs(np.mod(Z - (X - X0) * 1.2, 5.0) - 0.4) < 0.25) & (X > X0 + 0.5) & (X < X1 - 0.5)
        return [(post, "white"), (level, "white"), (brace, "white"), (stair, "steel")]
    b.sol(frame, None, X0, X1)
    b.bx(X0 - 0.2, X1 + 0.2, Y0 - 0.2, Y1 + 0.2, 22.0, 25.0, "white")   # machinery room
    b.bx(X0, X1, Y1 + 0.15, Y1 + 0.22, 23.0, 24.2, "window")
    b.sol(lambda X, Y, Z: (Z > 25.0) & (Z <= 26.1) & (X > X0 - 0.2) & (X < X1 + 0.2) &
          (Y > Y0 - 0.2) & (Y < Y1 + 0.2) &
          ((np.minimum(X - X0 + 0.2, X1 + 0.2 - X) < 0.08) | (np.minimum(Y - Y0 + 0.2, Y1 + 0.2 - Y) < 0.08)) &
          ((Z > 25.95) | (np.mod(X + Y, 1.0) < 0.1)), "white", X0 - 0.2, X1 + 0.2)
    b.bx(6.9, 7.1, 7.9, 8.1, 26.0, 30.0, "steel")

    # walkway arriving from -X, and the tilting gangway down towards +X
    def ways(X, Y, Z):
        inside_y = (Y >= 6.2) & (Y <= 9.8)
        side = inside_y & (np.minimum(Y - 6.2, 9.8 - Y) < 0.14)
        arr = (X < X0) & (Z > 10.0) & (Z <= 13.6)
        arr_d = arr & side & (np.abs(np.abs(np.mod(X, 3.2) - 1.6) * 3.6 / 1.6 - (Z - 10.0)) < 0.3)
        arr_c = arr & side & ((Z < 10.3) | (Z > 13.3))
        zb = 10.0 - (X - X1) * 0.9                         # gangway slopes down
        gw = (X > X1) & (X < 16.0) & inside_y & (Z > zb) & (Z <= zb + 2.8)
        gw_c = gw & side & ((Z < zb + 0.3) | (Z > zb + 2.5))
        gw_d = gw & side & (np.mod(X, 1.0) < 0.15)
        return [(arr & inside_y & (Z <= 10.25), "grey"), (arr_d, "white"), (arr_c, "white"),
                (gw & (Z <= zb + 0.25), "grey"), (gw_c, "white"), (gw_d, "white")]
    b.sol(ways, None)
    return b


def sb_wingwall():
    """Swartz Bay berth wall on water: a concrete caisson with fender panels
    painted blue over orange-red on the berth side (+Y), a white-railed
    deck on top."""
    b = Building(1, 1)
    b.extra_top = 3.0
    b.bx(1.0, 15.0, 10.0, 14.2, 0.0, 5.0, "concrete")
    b.bx(1.0, 15.0, 10.0, 14.2, 5.0, 5.3, "grey")
    for x0 in (2.0, 6.8, 11.6):
        b.bx(x0, x0 + 3.6, 14.2, 14.7, 0.2, 2.8, "orangered")
        b.bx(x0, x0 + 3.6, 14.2, 14.7, 2.8, 5.0, "blue")
        b.bx(x0 + 1.75, x0 + 1.85, 14.7, 14.75, 0.2, 5.0, "dark")
    b.sol(lambda X, Y, Z: (Z > 5.3) & (Z <= 6.4) & (X > 1.0) & (X < 15.0) &
          ((np.abs(Y - 14.1) < 0.06) | (np.abs(Y - 10.1) < 0.06)) &
          ((Z > 6.25) | (np.mod(X, 1.2) < 0.12)), "white", 1.0, 15.0)
    b.bx(13.6, 13.8, 10.6, 10.8, 5.3, 7.2, "white")
    b.ellipsoid(13.7 - b.cx, 10.7 - b.cy, 7.45, 0.25, 0.25, 0.3, "flagred")
    return b


def sb_ramp():
    """Swartz Bay ramp gantry: grey steel lattice towers either side of the
    vehicle ramp, a machinery house with railings on the cross girder."""
    b = Building(1, 1)
    b.extra_top = 6.0
    _paving(b)

    def ramp(X, Y, Z):
        zt = 1.4 - 0.9 * np.clip(X / 16.0, 0, 1)
        deck = (Y > 4.2) & (Y < 11.8) & (Z > 0.25) & (Z <= zt)
        edge = deck & ((np.abs(Y - 4.5) < 0.25) | (np.abs(Y - 11.5) < 0.25))
        return [(deck, "steel"), (edge, "yellow")]
    b.sol(ramp, None)

    def lattice(X, Y, Z):
        out = []
        for yc in (2.6, 13.4):
            x0, x1, y0, y1 = 11.0, 14.6, yc - 1.4, yc + 1.4
            inb = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1) & (Z > 0.25) & (Z <= 18.0)
            post = inb & (np.minimum(X - x0, x1 - X) < 0.3) & (np.minimum(Y - y0, y1 - Y) < 0.3)
            face = inb & ((np.minimum(X - x0, x1 - X) < 0.12) | (np.minimum(Y - y0, y1 - Y) < 0.12))
            t = np.where(np.minimum(X - x0, x1 - X) < 0.12, (Y - y0) / (y1 - y0), (X - x0) / (x1 - x0))
            brace = face & (np.abs(np.mod(Z, 3.0) - t * 3.0) < 0.22)
            ring = face & (np.mod(Z, 3.0) < 0.2)
            out.append((post | brace | ring, "steel"))
        return out
    b.sol(lattice, None, 11.0, 14.6)
    b.bx(10.8, 14.8, 1.0, 15.0, 18.0, 19.4, "steel")                 # cross girder
    b.bx(11.2, 14.4, 4.5, 11.5, 19.4, 22.0, "grey")                  # machinery house
    b.bx(11.2, 14.4, 11.45, 11.55, 20.2, 21.2, "window")
    b.sol(lambda X, Y, Z: (Z > 19.4) & (Z <= 20.4) & (X > 10.8) & (X < 14.8) & (Y > 1.0) &
          (Y < 15.0) & ((np.minimum(X - 10.8, 14.8 - X) < 0.08) | (np.minimum(Y - 1.0, 15.0 - Y) < 0.08)) &
          ((Z > 20.25) | (np.mod(X + Y, 1.0) < 0.1)), "yellow", 10.8, 14.8)
    for y in (5.0, 11.0):
        b.bx(12.7, 12.82, y - 0.06, y + 0.06, 1.0, 18.0, "dark")
    return b



# ---------------------------------------------------------------------------
# Southern Gulf Islands terminals (photos on Commons: Otter Bay, Sturdies
# Bay, Village Bay, Lyall Harbour, Fulford Harbour). Small terminals in the
# forest: timber trestles, white lattice ramp towers, red-faced fenders,
# timber dolphins, a ticket booth, and The Stand at Otter Bay.
# ---------------------------------------------------------------------------

def _fir(b, x, y, z, h, rng):
    """Douglas fir: tall bare-ish trunk, narrow irregular crown of drooping
    tiers that thin to a spire (real firs are slender, not cones)."""
    b.bx(x - 0.15, x + 0.15, y - 0.15, y + 0.15, z, z + h * 0.45, "piling")
    tiers = 9
    for i in range(tiers):
        t = i / tiers
        zc = z + h * (0.22 + 0.72 * t)
        r = (1.0 - t * 0.9) * h * 0.075 * rng.uniform(0.8, 1.2)
        ox, oy = rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25)
        th = h * 0.1
        b.sol(lambda X, Y, Z, zc=zc, r=r, ox=ox, oy=oy, th=th:
              (np.sqrt((X - x - ox) ** 2 + (Y - y - oy) ** 2) < r * (1 - 0.7 * (Z - zc) / th)) &
              (Z > zc) & (Z <= zc + th), "fir" if i % 2 == 0 else "fir2", x - r - 0.5, x + r + 0.5)
    b.bx(x - 0.06, x + 0.06, y - 0.06, y + 0.06, z + h * 0.9, z + h, "fir")

def _arbutus(b, x, y, z, rng):
    """Arbutus (madrone): twisting red trunk, round open canopy."""
    lean = rng.uniform(-0.6, 0.6)
    b.sol(lambda X, Y, Z: (np.abs(X - (x + lean * (Z - z) / 4.0)) < 0.22) & (np.abs(Y - y) < 0.22) &
          (Z > z) & (Z <= z + 4.0), "arbutus", x - 1.0, x + 1.0)
    b.ellipsoid(x + lean - b.cx, y - b.cy, z + 5.2, 1.8, 1.6, 1.4, "fir2")
    b.ellipsoid(x + lean * 1.2 + 0.6 - b.cx, y + 0.4 - b.cy, z + 5.9, 1.1, 1.1, 0.9, "moss")


def _rock(b, x, y, z, r, rng):
    b.ellipsoid(x - b.cx, y - b.cy, z, r * rng.uniform(0.9, 1.3), r, r * 0.55, "granite")
    b.ellipsoid(x + r * 0.3 - b.cx, y - r * 0.2 - b.cy, z + r * 0.35, r * 0.6, r * 0.5, r * 0.25, "moss")


def island_forest(variant=0):
    """Gulf Islands woods: Douglas firs, arbutus, mossy granite outcrops."""
    b = Building(1, 1)
    b.extra_top = 26.0
    rng = np.random.RandomState(131 + variant)
    b.sol(lambda X, Y, Z: [((Z <= 0.3), "moss"),
                           ((Z <= 0.3) & _stain(X, Y, variant, 2.0, 0.25), "forestfloor")], None)
    spots = [(3.5, 4.0), (11.5, 3.5), (7.5, 9.0), (3.0, 13.0), (12.5, 12.5)]
    for i, (x, y) in enumerate(spots):
        x += rng.uniform(-1.0, 1.0)
        y += rng.uniform(-1.0, 1.0)
        if (i + variant) % 3 == 2:
            _arbutus(b, x, y, 0.3, rng)
        else:
            _fir(b, x, y, 0.3, rng.uniform(18.0, 26.0), rng)
    for _ in range(3):
        _rock(b, rng.uniform(1.5, 14.5), rng.uniform(1.5, 14.5), 0.3, rng.uniform(0.8, 1.6), rng)
    return b


def island_gantry():
    """Otter Bay style ramp gantry: two white lattice towers either side of
    the vehicle ramp, a cross girder carrying the 'Otter Bay · Pender Island'
    sign, machinery houses on top, red-faced fender walls at the water end."""
    b = Building(1, 1)
    b.extra_top = 6.0
    _paving(b, seed=3.0)

    def ramp(X, Y, Z):
        zt = 1.2 - 0.8 * np.clip(X / 16.0, 0, 1)
        deck = (Y > 5.0) & (Y < 11.0) & (Z > 0.25) & (Z <= zt)
        edge = deck & ((np.abs(Y - 5.3) < 0.2) | (np.abs(Y - 10.7) < 0.2))
        rail = (np.minimum(np.abs(Y - 5.1), np.abs(Y - 10.9)) < 0.07) & (Z > zt) & (Z <= zt + 1.1) & \
            ((Z > zt + 0.95) | (np.mod(X, 1.2) < 0.12))
        return [(deck, "asphalt"), (edge, "yellow"), (rail, "yellow")]
    b.sol(ramp, None)

    def towers(X, Y, Z):
        out = []
        for yc in (3.4, 12.6):
            x0, x1, y0, y1 = 10.6, 13.4, yc - 1.1, yc + 1.1
            inb = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1) & (Z > 0.25) & (Z <= 17.0)
            post = inb & (np.minimum(X - x0, x1 - X) < 0.25) & (np.minimum(Y - y0, y1 - Y) < 0.25)
            face = inb & ((np.minimum(X - x0, x1 - X) < 0.1) | (np.minimum(Y - y0, y1 - Y) < 0.1))
            t = np.where(np.minimum(X - x0, x1 - X) < 0.1, (Y - y0) / (y1 - y0), (X - x0) / (x1 - x0))
            brace = face & ((np.abs(np.mod(Z, 2.4) - t * 2.4) < 0.18) | (np.mod(Z, 2.4) < 0.15))
            out.append((post | brace, "white"))
        return out
    b.sol(towers, None, 10.6, 13.4)
    b.bx(10.4, 13.6, 1.8, 14.2, 17.0, 18.0, "white")                 # cross girder
    b.bx(10.2, 10.4, 4.6, 11.4, 15.0, 17.6, "white")                 # sign plate
    b.sol(lambda X, Y, Z: (X > 10.12) & (X < 10.22) & __import__("render").decal_mask(
        "otterbay", Y - 8.0, Z, 0.0, 16.3, 1.2, width=6.4), "navy", 10.0, 10.3)
    for yc in (3.4, 12.6):                                           # machinery houses
        b.bx(10.8, 13.2, yc - 1.0, yc + 1.0, 18.0, 19.8, "white")
        b.bx(10.7, 13.3, yc - 1.1, yc + 1.1, 19.8, 20.1, "steel")
        b.bx(11.9, 12.1, yc + 0.2, yc + 0.4, 20.1, 23.0, "white")     # flagpole
    b.bx(11.95, 12.05, 12.85, 14.0, 21.6, 22.9, "bcfblue")            # BC Ferries flag
    # red-faced fender walls at the water end, yellow railings, life ring
    for y0, y1 in ((0.2, 4.6), (11.4, 15.8)):
        b.bx(14.2, 16.0, y0, y1, 0.0, 4.4, "white")
        face_y = y1 if y0 < 1 else y0
        b.bx(14.2, 16.0, min(face_y, face_y + (0.3 if y0 < 1 else -0.3)),
             max(face_y, face_y + (0.3 if y0 < 1 else -0.3)), 0.6, 3.8, "flagred")
        b.sol(lambda X, Y, Z, y0=y0, y1=y1: (X > 14.2) & (X < 16.0) & (Y > y0) & (Y < y1) &
              (Z > 4.4) & (Z <= 5.4) & ((np.abs(X - 14.25) < 0.06) | (np.abs(X - 15.95) < 0.06)) &
              ((Z > 5.25) | (np.mod(Y, 1.0) < 0.12)), "yellow", 14.2, 16.0)
    b.bx(14.1, 14.2, 1.6, 2.2, 2.6, 3.2, "orange")
    return b


def island_wingwall():
    """Island berth wall on water: white steel frame with a red fender face
    towards the berth (+Y), yellow railing and walkway on top."""
    b = Building(1, 1)
    b.extra_top = 3.0
    b.bx(1.0, 15.0, 11.5, 14.6, 0.0, 4.6, "white")
    b.sol(lambda X, Y, Z: (X > 1.0) & (X < 15.0) & (np.abs(Y - 11.5) < 0.12) & (Z <= 4.6) &
          ((np.mod(X, 2.8) < 0.3) | (np.abs(np.mod(X, 2.8) - Z * 0.6) < 0.25)), "steel", 1.0, 15.0)
    b.bx(1.2, 14.8, 14.6, 14.95, 0.4, 3.9, "flagred")
    b.bx(1.2, 14.8, 14.6, 14.95, 0.0, 0.4, "piling")
    b.bx(1.0, 15.0, 11.5, 14.6, 4.6, 4.85, "grey")
    b.sol(lambda X, Y, Z: (X > 1.0) & (X < 15.0) & ((np.abs(Y - 11.6) < 0.06) | (np.abs(Y - 14.5) < 0.06)) &
          (Z > 4.85) & (Z <= 5.95) & ((Z > 5.8) | (np.mod(X, 1.2) < 0.12)), "yellow", 1.0, 15.0)
    b.bx(7.6, 8.2, 11.4, 11.5, 5.0, 5.6, "orange")
    return b


def island_trestle():
    """Sturdies Bay style timber trestle on water: pile bents with cross
    bracing carrying a deck with a road, a footpath and yellow railings."""
    b = Building(1, 1)
    b.extra_top = 3.0
    Y0, Y1, ZD = 3.0, 13.0, 4.4

    def trestle(X, Y, Z):
        bent = np.abs(np.mod(X, 4.0) - 2.0) < 0.35
        piles = bent & (np.abs(np.mod(Y - Y0, 2.5) - 1.25) > 1.0) & (Y > Y0) & (Y < Y1) & (Z <= ZD)
        brace = bent & (Y > Y0) & (Y < Y1) & (np.abs(np.mod(Y + Z * 1.2, 5.0) - 2.5) < 0.18) & (Z <= ZD)
        cap = (Y > Y0) & (Y < Y1) & (Z > ZD - 0.5) & (Z <= ZD) & (np.abs(np.mod(X, 4.0) - 2.0) < 0.5)
        stringer = (Y > Y0) & (Y < Y1) & (Z > ZD - 0.35) & (Z <= ZD) & (np.mod(Y - Y0, 1.6) < 0.4)
        deck = (Y > Y0) & (Y < Y1) & (Z > ZD) & (Z <= ZD + 0.35)
        road = deck & (Y > Y0 + 0.4) & (Y < Y1 - 2.2) & (Z > ZD + 0.25)
        path = deck & (Y >= Y1 - 2.0) & (Z > ZD + 0.25)
        cl = road & (np.abs(Y - (Y0 + Y1 - 1.8) / 2) < 0.08) & (np.mod(X, 2.0) < 1.1)
        rail = (np.minimum(np.abs(Y - Y0 - 0.1), np.abs(Y - Y1 + 0.1)) < 0.07) & (Z > ZD + 0.35) & \
            (Z <= ZD + 1.5) & ((Z > ZD + 1.35) | (np.abs(Z - ZD - 0.9) < 0.07) | (np.mod(X, 1.0) < 0.12))
        return [(piles, "piling"), (brace, "piling"), (cap, "cedar"), (stringer, "cedar"),
                (deck, "cedar"), (road, "asphalt"), (path, "timber"), (cl, "yellow"), (rail, "yellow")]
    b.sol(trestle, None)
    b.bx(7.9, 8.1, Y1 - 0.3, Y1 - 0.1, ZD + 0.35, ZD + 8.5, "steel")      # lamp post
    b.bx(7.6, 8.4, Y1 - 0.9, Y1 - 0.2, ZD + 8.2, ZD + 8.5, "dark")
    return b


def island_dolphin():
    """Timber pile dolphins on water: clusters of creosoted piles wrapped
    with steel cable, one with a red navigation marker."""
    b = Building(1, 1)
    b.extra_top = 3.0
    rng = np.random.RandomState(141)
    for cx, cy, top in ((4.0, 5.0, 10.0), (11.5, 10.0, 9.0), (5.5, 12.5, 9.5)):
        pts = [(cx + 0.42 * np.cos(a), cy + 0.42 * np.sin(a)) for a in np.linspace(0, 2 * np.pi, 7)[:-1]]
        pts.append((cx, cy))
        for px, py in pts:
            h = top + (0.8 if (px, py) == (cx, cy) else rng.uniform(-0.6, 0.0))
            lean = 0.06 * (cx - px), 0.06 * (cy - py)
            b.sol(lambda X, Y, Z, px=px, py=py, h=h, lean=lean:
                  ((X - px - lean[0] * Z) ** 2 + (Y - py - lean[1] * Z) ** 2 < 0.17 ** 2) & (Z <= h),
                  "piling", px - 1.0, px + 1.0)
        b.sol(lambda X, Y, Z, cx=cx, cy=cy, top=top: (np.abs(np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) - 0.62) < 0.08) &
              (np.abs(Z - top + 1.2) < 0.25), "steel", cx - 1.2, cx + 1.2)
    b.bx(3.8, 4.2, 4.8, 5.2, 10.8, 11.8, "flagred")                    # nav marker
    b.bx(3.9, 4.1, 4.9, 5.1, 11.8, 12.6, "white")
    return b


def island_booth():
    """Island terminal: cedar-sided ticket booth with green metal roof over
    a lane, a little washroom building, the BC Ferries sign, firs behind."""
    b = Building(1, 1)
    b.extra_top = 22.0
    rng = np.random.RandomState(151)

    def ground(X, Y, Z):
        g = Z <= 0.2
        lane = (Y > 6.0) & (Y < 12.5)
        return [(g, "gravel"), (g & lane, "asphalt"),
                (g & lane & (np.abs(Y - 9.25) < 0.08) & (np.mod(X, 3.0) < 1.6), "laneline"),
                (g & ~lane & _stain(X, Y, 4.0, 2.0, 0.2), "concrete2")]
    b.sol(ground, None)
    # booth on an island between lane and gravel, canopy over the lane
    b.bx(6.0, 10.0, 3.2, 5.8, 0.2, 0.5, "concrete")
    b.bx(6.4, 9.6, 3.6, 5.4, 0.5, 4.2, "cedar")
    b.bx(6.4, 9.6, 5.38, 5.45, 2.0, 3.6, "glass")
    b.sol(lambda X, Y, Z: (X > 5.6) & (X < 10.4) & (Y > 3.0) & (Y < 13.0) &
          (Z > 5.2 + 0.12 * (Y - 3.0)) & (Z <= 5.5 + 0.12 * (Y - 3.0)), "roofgreen", 5.6, 10.4)
    for x in (5.9, 10.1):
        b.bx(x - 0.1, x + 0.1, 12.6, 12.8, 0.2, 6.6, "cedar")
    _person(b, 8.0, 4.4, 0.5, rng)
    # washroom hut
    b.bx(1.0, 4.4, 0.8, 4.2, 0.2, 3.6, "cedar")
    b.sol(lambda X, Y, Z: (X > 0.7) & (X < 4.7) & (Y > 0.5) & (Y < 4.5) &
          (Z > 3.6) & (Z <= 3.6 + 1.2 * (1 - np.abs(Y - 2.5) / 2.0)), "roofgreen", 0.7, 4.7)
    b.bx(2.2, 3.2, 4.2, 4.25, 0.2, 2.6, "bcfblue")
    # BC Ferries sign post and a waiting bench
    _signpost(b, 13.6, 4.0, 0.2, "bcfblue", h=3.6, w=2.4, along_x=True)
    _bench(b, 12.0, 1.4, 0.2, True)
    # firs and arbutus behind
    _fir(b, 1.6, 14.4, 0.2, 21.0, rng)
    _fir(b, 14.6, 14.8, 0.2, 18.0, rng)
    _arbutus(b, 14.0, 1.2, 0.2, rng)
    return b


def the_stand():
    """The Stand, Otter Bay (Pender Island): the famous burger take-out run
    from a converted RV (no permanent buildings allowed on the site), with
    a striped awning, hand-painted sign, menu board, picnic tables under
    umbrellas, a gravel lot, people queuing, firs all around."""
    b = Building(1, 1)
    b.extra_top = 22.0
    rng = np.random.RandomState(161)
    b.sol(lambda X, Y, Z: [((Z <= 0.2), "gravel"),
                           ((Z <= 0.2) & _stain(X, Y, 7.0, 1.5, 0.2), "concrete2")], None)
    # the RV: cab at +X, boxy camper body, wheels, windows, stripe
    RX0, RX1, RY0, RY1 = 2.0, 11.6, 2.4, 5.8
    b.bx(RX0, RX1 - 2.0, RY0, RY1, 0.9, 5.0, "rvcream")
    b.bx(RX1 - 2.0, RX1, RY0 + 0.2, RY1 - 0.2, 0.9, 3.4, "rvcream")
    b.bx(RX1 - 2.6, RX1 - 2.0, RY0, RY1, 4.0, 5.2, "rvcream")          # over-cab bunk
    b.bx(RX1 - 0.6, RX1 + 0.05, RY0 + 0.4, RY1 - 0.4, 2.0, 3.0, "glass")
    b.bx(RX0, RX1, RY0 - 0.03, RY1 + 0.03, 1.8, 2.1, "cedar")          # stripe
    b.bx(RX0, RX1, RY0 - 0.04, RY1 + 0.04, 2.1, 2.25, "orange")
    for x in (3.4, 9.6):
        for y in (RY0 - 0.05, RY1 - 0.35):
            b.bx(x - 0.6, x + 0.6, y, y + 0.4, 0.2, 1.2, "dark")
    b.bx(4.0, 8.0, RY1, RY1 + 0.05, 2.6, 4.2, "window")                # serving hatch
    b.bx(3.8, 8.2, RY1, RY1 + 0.8, 2.4, 2.6, "timber")                 # counter
    # striped awning over the hatch
    b.sol(lambda X, Y, Z: (X > 3.0) & (X < 9.0) & (Y > RY1) & (Y < RY1 + 3.2) &
          (np.abs(Z - (4.8 - 0.35 * (Y - RY1))) < 0.12), "white", 3.0, 9.0)
    b.sol(lambda X, Y, Z: (X > 3.0) & (X < 9.0) & (Y > RY1) & (Y < RY1 + 3.2) &
          (np.abs(Z - (4.8 - 0.35 * (Y - RY1))) < 0.12) & (np.mod(X, 1.0) < 0.5), "flagred", 3.0, 9.0)
    for x in (3.1, 8.9):
        b.bx(x - 0.07, x + 0.07, RY1 + 3.0, RY1 + 3.14, 0.2, 3.7, "steel")
    # hand-painted sign on the roof and a menu board
    b.bx(4.0, 8.4, RY1 - 0.2, RY1 - 0.05, 5.0, 6.4, "white")
    b.sol(lambda X, Y, Z: (Y > RY1 - 0.05) & (Y < RY1 + 0.05) & (X > 4.0) & (X < 8.4) &
          __import__("render").decal_mask("thestand", 6.2 - X, Z, 0.0, 5.7, 1.0,
                                          width=1.0 * 1300 / 120 / 2.24), "flagred", 4.0, 8.4)
    b.bx(10.2, 10.3, 7.0, 7.1, 0.2, 2.6, "timber")
    b.bx(9.6, 10.9, 7.1, 7.18, 1.4, 2.8, "dark")
    b.bx(9.75, 10.75, 7.18, 7.2, 1.6, 2.6, "white")
    # picnic tables with umbrellas
    for x, y in ((4.0, 11.4), (9.4, 12.0)):
        b.bx(x - 1.4, x + 1.4, y - 0.5, y + 0.5, 1.1, 1.3, "timber")
        for dy in (-1.0, 1.0):
            b.bx(x - 1.4, x + 1.4, y + dy - 0.25, y + dy + 0.25, 0.65, 0.8, "timber")
        b.bx(x - 0.05, x + 0.05, y - 0.05, y + 0.05, 0.2, 3.4, "steel")
        b.sol(lambda X, Y, Z, x=x, y=y: ((X - x) ** 2 + (Y - y) ** 2 < 1.5 ** 2) &
              (Z > 3.0) & (Z <= 3.5 - 0.3 * np.sqrt((X - x) ** 2 + (Y - y) ** 2)),
              "bcfblue" if x < 6 else "car5", x - 1.6, x + 1.6)
    # the queue and diners
    for i in range(4):
        _person(b, 5.0 + i * 0.75, 7.6 + rng.uniform(-0.2, 0.2), 0.2, rng)
    _people(b, 4, 2.0, 11.0, 10.0, 13.4, 0.2, rng, avoid=[(2.4, 5.6, 10.7, 12.1), (7.8, 11.0, 11.3, 12.7)])
    # forest round the lot
    _fir(b, 13.8, 1.6, 0.2, 24.0, rng)
    _fir(b, 1.0, 1.0, 0.2, 26.0, rng)
    _arbutus(b, 1.4, 14.2, 0.2, rng)
    return b
