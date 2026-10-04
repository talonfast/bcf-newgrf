"""
Tiny voxel renderer that turns a parametric ship description into
OpenTTD ship sprites (8 directions).

Everything is rendered once at 4x zoom (32bpp). The 2x and 1x 32bpp sprites
are box-filtered down from that (so they are anti-aliased), and the 1x 8bpp
fallback is the 1x image quantised to the DOS palette.

Coordinate systems
------------------
Ship-local:  u = along the hull (+u = bow), v = across the beam, w = up.
             u/v are OpenTTD world units (16 per tile edge); w is in
             OpenTTD height units (1 px at 1x zoom, before ZS).
World:       x -> SW, y -> SE, z -> up (OpenTTD convention).
Screen (1x): sx = 2 (y - x),  sy = (x + y) - z
"""
import math
import os
import numpy as np
from PIL import Image
from nml.palette import raw_palette_data

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
DOS_PAL = raw_palette_data[0]
PAL_RGB = np.array(DOS_PAL, dtype=np.float32).reshape(256, 3)

# Usable indices: skip 0 (transparent), company colours (198-205) and the
# animated / special range (>= 215) so nothing cycles or recolours.
USABLE = np.array([i for i in range(1, 215) if not (198 <= i <= 205)])
USABLE_RGB = PAL_RGB[USABLE]

# ---------------------------------------------------------------------------
# Materials (id -> base RGB)
# ---------------------------------------------------------------------------
MAT = {
    "white":   (238, 240, 242),
    "roof":    (200, 204, 208),
    "navy":    (14, 44, 120),
    "blue":    (36, 92, 178),
    "window":  (30, 44, 70),
    "glass":   (70, 110, 150),
    "deck":    (118, 124, 126),
    "green":   (92, 120, 96),
    "red":     (200, 34, 30),
    "black":   (30, 30, 34),
    "grey":    (150, 150, 150),
    "orange":  (240, 124, 20),
    "yellow":  (240, 196, 40),
    "dark":    (22, 24, 30),
    "steel":   (170, 176, 184),
    "rail":    (225, 228, 232),
    "car1":    (190, 40, 40),
    "car2":    (60, 90, 180),
    "car3":    (220, 220, 220),
    "car4":    (40, 40, 40),
    "car5":    (210, 180, 60),
    "car6":    (80, 140, 80),
    # Vancouver 2010 wrap
    "sky1":    (96, 164, 226),
    "sky2":    (178, 214, 240),
    "snow":    (246, 248, 252),
    "rock":    (104, 116, 140),
    "forest":  (28, 84, 52),
    "grass":   (116, 176, 64),
    "vine":    (64, 116, 40),
    "vblue":   (0, 108, 190),
    "vgreen":  (124, 192, 60),
    "teal":    (0, 150, 164),
    "suit":    (200, 30, 40),
    # BC Ferries livery
    "bcfblue":   (40, 78, 156),
    "stackblue": (36, 86, 178),
    "hullblack": (26, 26, 30),
    "antifoul":  (128, 44, 34),
    "copper":    (150, 96, 64),
    "ltblue":    (120, 172, 214),
    "cream":     (242, 238, 226),
    "stacknavy": (22, 34, 98),
    # Pirate Pak
    "cardboard": (236, 226, 204),
    "bun":       (206, 136, 58),
    "bunlight":  (232, 178, 96),
    "patty":     (92, 50, 30),
    "cheese":    (250, 188, 30),
    "lettuce":   (118, 184, 60),
    "tomato":    (214, 52, 40),
    "pickle":    (104, 140, 40),
    "icecream":  (252, 246, 228),
    "cuporange": (240, 150, 40),
    "deckwood":  (196, 118, 60),
    "deckline":  (150, 82, 40),
    "kraft":     (204, 172, 122),
    "cola":      (58, 30, 22),
    "lid":       (214, 222, 228),
    "slaw":      (242, 236, 210),
    "carrot":    (240, 130, 40),
    "gold":      (232, 184, 40),
    "fries":     (240, 196, 80),
    "paper":     (246, 244, 238),
    "mushroom":  (120, 84, 56),
    # buildings
    "concrete":  (192, 190, 182),
    "alu":       (172, 178, 184),
    "timber":    (204, 128, 58),
    "louvre":    (104, 110, 118),
    "stone":     (150, 152, 148),
    "roofmetal": (140, 144, 148),
    "rust":      (128, 72, 42),
    "asphalt":   (74, 76, 80),
    "laneline":  (232, 232, 226),
    "membrane":  (214, 216, 218),
    "skin":      (222, 182, 150),
    "skin2":     (150, 106, 78),
    "denim":     (56, 76, 120),
    "umbrella":  (226, 60, 48),
    "signgreen": (40, 170, 70),
    "flagred":   (214, 32, 40),
    "stucco":    (128, 110, 90),
    "tentcream": (238, 230, 200),
    "orangered": (220, 74, 42),
    "fir":       (34, 70, 40),
    "fir2":      (48, 92, 50),
    "arbutus":   (170, 70, 40),
    "granite":   (128, 126, 118),
    "moss":      (96, 112, 60),
    "cedar":     (138, 84, 52),
    "roofgreen": (60, 104, 72),
    "rvcream":   (236, 228, 206),
    "gravel":    (168, 160, 144),
    "piling":    (92, 70, 50),
    "concrete2": (172, 170, 162),
    "oil":       (88, 88, 90),
    "forestfloor": (82, 98, 56),
    # aircraft
    "acwhite":   (244, 245, 247),
    "acblack":   (22, 22, 26),
    "acred":     (214, 24, 42),
    "wingrey":   (186, 190, 196),
    "nacgrey":   (150, 154, 160),
    "asnavy":    (1, 42, 92),
    "asteal":    (0, 140, 160),
    "asgreen":   (118, 188, 60),
    "asblue":    (0, 98, 177),
    "asroyal":   (16, 78, 170),
    "asturq":    (24, 192, 142),
    "asmid":     (0, 156, 160),
    "wjteal":    (0, 74, 88),
    "wjlight":   (0, 160, 168),
    "tyre":      (30, 30, 32),
    # airports
    "tealglass": (54, 132, 146),
    "tealdark":  (24, 70, 84),
    "beige":     (214, 202, 174),
    "jbgrey":    (196, 198, 202),
    "silver":    (210, 214, 218),
    "apronconc": (176, 174, 166),
    "harbourblue": (0, 70, 140),
    # waterfront
    "fhpink":    (214, 96, 120),
    "fhteal":    (52, 150, 170),
    "fhyellow":  (236, 200, 90),
    "fhnavy":    (44, 66, 112),
    "fhpurple":  (132, 94, 170),
    "fhgreen":   (70, 140, 110),
    "fhred":     (184, 52, 48),
    "corrugated": (150, 156, 150),
    "awngreen":  (40, 150, 80),
    "willow":    (156, 186, 64),
    "brick":     (150, 62, 48),
    "sail":      (240, 240, 236),
    "floatwood": (150, 128, 102),
    "lime":      (176, 206, 40),
    "andesite":  (198, 190, 174),
    "copper":    (96, 168, 140),
    "gold":      (220, 176, 60),
    "lawn":      (98, 146, 62),
}
MAT_NAMES = list(MAT.keys())
MAT_ID = {n: i + 1 for i, n in enumerate(MAT_NAMES)}
MAX_MATS = 4096   # named materials first, then colours registered by textures
MAT_RGB = np.zeros((MAX_MATS, 3), dtype=np.float32)
for n, i in MAT_ID.items():
    MAT_RGB[i] = MAT[n]
GLOSSY = np.zeros(MAX_MATS, dtype=bool)
_next_mat = [len(MAT_NAMES) + 1]
for n in ("window", "glass", "lid", "tealglass"):
    GLOSSY[MAT_ID[n]] = True

# Headings in OpenTTD direction order: N NE E SE S SW W NW
HEADINGS = [(-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1)]

LIGHT = np.array([0.55, 0.12, 0.83])
LIGHT = LIGHT / np.linalg.norm(LIGHT)

ZOOM = 4             # render zoom (4 = ZOOM_LEVEL_IN_4X)
SCALE = 1.5          # global size of the fleet on the map (1.0 = Spirit ~1.6 tiles)
BASE_STEP = 0.05     # voxel size in *on-map* world units at 4x
STEP = BASE_STEP     # current voxel size in model units (set per ship in render)
ZS = 1.55            # vertical exaggeration so decks read clearly
CHUNK = 48           # voxels along u per slab (memory bound)

ASPECT = ZS / 2.83   # s-units per w-unit that look square in side view

# ---------------------------------------------------------------------------
# Decals (src/decals/*.png, white = ink) projected onto hull/funnel sides
# ---------------------------------------------------------------------------
DECAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "decals")
_decals = {}


def _decal(name, width, height):
    key = (name, round(width, 3), round(height, 3), STEP)
    if key not in _decals:
        im = Image.open(os.path.join(DECAL_DIR, name + ".png")).convert("L")
        nx = max(2, int(round(width / STEP * 2)))
        ny = max(2, int(round(height / STEP * 2)))
        _decals[key] = np.asarray(im.resize((nx, ny), Image.BOX), dtype=np.float32) > 110
    return _decals[key]


def decal_size(name):
    im = Image.open(os.path.join(DECAL_DIR, name + ".png"))
    return im.width, im.height


def decal_mask(name, s, w, s0, w0, height, width=None):
    """Mask of decal `name` centred at (s0, w0) on a surface parameterised
    by s (left-to-right as seen) and w (up). width defaults to the image
    aspect ratio corrected for the isometric side view."""
    if width is None:
        iw, ih = decal_size(name)
        width = height * iw / ih * ASPECT
    a = _decal(name, width, height)
    ny, nx = a.shape
    ix = np.floor((s - (s0 - width / 2)) / width * nx).astype(np.int32)
    iy = np.floor((w0 + height / 2 - w) / height * ny).astype(np.int32)
    ok = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
    out = np.zeros(s.shape, dtype=bool)
    out[ok] = a[iy[ok], ix[ok]]
    return out


_textures = {}


def _texture(name, width, height):
    """Texture resampled to the voxel grid and quantised to <= 48 colours,
    each registered as a material. Returns an int array of material ids
    (0 = transparent)."""
    key = (name, round(width, 3), round(height, 3), STEP)
    if key not in _textures:
        im = Image.open(os.path.join(DECAL_DIR, name + ".png")).convert("RGBA")
        nx = max(2, int(round(width / STEP * 2)))
        ny = max(2, int(round(height / STEP * 2)))
        im = im.resize((nx, ny), Image.LANCZOS)
        alpha = np.asarray(im)[..., 3] > 127
        q = im.convert("RGB").quantize(48, dither=Image.Dither.NONE)
        pal = np.array(q.getpalette()[:48 * 3], dtype=np.float32).reshape(-1, 3)
        base = _next_mat[0]
        _next_mat[0] += len(pal)
        MAT_RGB[base:base + len(pal)] = pal
        ids = np.asarray(q, dtype=np.int16) + base
        ids[~alpha] = 0
        _textures[key] = ids
    return _textures[key]


def texture_ids(name, s, w, s0, w0, height, width):
    a = _texture(name, width, height)
    ny, nx = a.shape
    ix = np.floor((s - (s0 - width / 2)) / width * nx).astype(np.int32)
    iy = np.floor((w0 + height / 2 - w) / height * ny).astype(np.int32)
    ok = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
    out = np.zeros(s.shape, dtype=np.int16)
    out[ok] = a[iy[ok], ix[ok]]
    return out


# 3x5 bitmap font for hull lettering
FONT = {
    "A": ["010", "101", "111", "101", "101"],
    "B": ["110", "101", "110", "101", "110"],
    "C": ["011", "100", "100", "100", "011"],
    "E": ["111", "100", "110", "100", "111"],
    "F": ["111", "100", "110", "100", "100"],
    "H": ["101", "101", "111", "101", "101"],
    "I": ["111", "010", "010", "010", "111"],
    "K": ["101", "101", "110", "101", "101"],
    "L": ["100", "100", "100", "100", "111"],
    "O": ["010", "101", "101", "101", "010"],
    "R": ["110", "101", "110", "101", "101"],
    "S": ["011", "100", "010", "001", "110"],
    "N": ["101", "111", "111", "101", "101"],
    "U": ["101", "101", "101", "101", "111"],
    "V": ["101", "101", "101", "101", "010"],
    "0": ["111", "101", "101", "101", "111"],
    "1": ["010", "110", "010", "010", "111"],
    "2": ["110", "001", "010", "100", "111"],
    " ": ["000", "000", "000", "000", "000"],
}


def text_mask(s, w, text, center_u, w_mid, height):
    """Boolean mask for lettering painted on a hull side.
    s: along-hull coordinate oriented so text reads left-to-right."""
    row_h = height / 5
    col_w = row_h * ZS / 2.83          # square-ish pixels in side view
    total = len(text) * 4 - 1
    c = np.floor((s - center_u) / col_w + total / 2).astype(int)
    r = np.floor((w_mid + height / 2 - w) / row_h).astype(int)
    out = np.zeros(s.shape, dtype=bool)
    ok = (c >= 0) & (c < total) & (r >= 0) & (r < 5)
    for i, ch in enumerate(text):
        g = FONT[ch]
        for rr in range(5):
            for cc in range(3):
                if g[rr][cc] == "1":
                    out |= ok & (c == i * 4 + cc) & (r == rr)
    return out


class Ship:
    """Parametric ship. Components are painted in order; later wins."""

    def __init__(self, length, beam, ends="double", taper=0.22, blunt=0.4):
        self.L = length
        self.B = beam
        self.ends = ends          # 'double', 'single', 'cat'
        self.taper = taper        # fraction of length used for end rounding
        self.blunt = blunt        # width fraction left at the very ends
        self.scale = 1.0          # extra per-ship size factor on top of SCALE
        self.weather = 0.35       # 0 = showroom clean .. 1 = rust-streaked veteran
        self.speed = 15.0         # knots, sizes the wake
        self.exhausts = []        # (u, v, w) stack outlets, for in-game smoke
        self.ops = []

    # half-beam of the hull at position u
    def hb(self, u):
        L, B = self.L, self.B
        r = self.taper * L
        au = np.abs(u)
        if self.ends == "double":
            q = np.clip((au - (L / 2 - r)) / r, 0, 1)
            return B / 2 * (self.blunt + (1 - self.blunt) * np.sqrt(1 - q ** 2))
        # single-ended: pointed bow at +u, near-square transom at -u
        qb = np.clip((u - (L / 2 - r)) / r, 0, 1)
        bow = np.sqrt(1 - qb ** 1.6) * (1 - 0.08 * qb)
        rs = 0.07 * L
        qs = np.clip((-u - (L / 2 - rs)) / rs, 0, 1)
        stern = 0.82 + 0.18 * np.sqrt(1 - qs ** 2)
        return B / 2 * np.where(u >= 0, bow, stern)

    # --- component builders -------------------------------------------------
    def hull(self, height, lower="navy", upper="white", band=1.2, deck="deck",
             sheer=0.0, stripe=None, doors=True, text=None, boot=None, rail=False,
             paint=None, decals=(), windows=None, height_fn=None, deck_paint=None):
        """stripe: None, a material name (thin line under the deck edge), or
        (w0, w1, material). text: (string, w_mid, letter_height, material).
        boot: (height, material) waterline boot-top painted over `lower`.
        paint: fn(s, w, h) -> [(mask, material)] for artwork on the hull
        sides (s runs left-to-right as seen by the viewer).
        decals: [dict(name, s, w, h, mat)] projected on both hull sides;
        add side="a" (v < 0) or "b" to restrict, tex=True for colour images.
        paint may also return (mask, dict(tex, s, w, width, h)) entries.
        windows: (w0, w1, period, duty) rows of hull windows over everything.
        height_fn: fn(u) -> deck height, replacing height + sheer.
        deck_paint: fn(U, V) -> [(mask, material)] for the exposed top."""
        self.ops.append(("hull", dict(h=height, lower=lower, upper=upper, band=band,
                                      deck=deck, sheer=sheer, stripe=stripe,
                                      doors=doors, text=text, boot=boot, rail=rail,
                                      paint=paint, decals=decals, windows=windows,
                                      height_fn=height_fn, deck_paint=deck_paint)))
        return self

    def cat_hulls(self, height, sep, hull_beam, lower="navy", upper="white", band=0.8):
        self.ops.append(("cat", dict(h=height, sep=sep, hb=hull_beam, lower=lower,
                                     upper=upper, band=band)))
        return self

    def block(self, u0, u1, z0, z1, wf=0.9, mat="white", roof="roof", windows=True,
              win_mat="window", v0=None, v1=None, round_ends=True, end_windows=None,
              rail=True, panes=True, decals=(), rect=False):
        """Superstructure block. u0/u1 are in hull units (not fractions).
        wf scales the local hull half-beam. v0/v1 (absolute) make an offset
        block (e.g. side-mounted cabins). rect: constant-width plan that can
        overhang the narrowing hull ends. panes: True, False or (period, duty)."""
        self.ops.append(("block", dict(u0=u0, u1=u1, z0=z0, z1=z1, wf=wf, mat=mat,
                                       roof=roof, windows=windows, win_mat=win_mat,
                                       v0=v0, v1=v1, round_ends=round_ends,
                                       end_windows=end_windows, rail=rail, panes=panes,
                                       decals=decals, rect=rect)))
        return self

    def funnel(self, u, v, z0, z1, ru=0.7, rv=0.45, mat="white", top="navy",
               top_h=0.8, band=None, rake=0.0, taper=0.0, decal=None, hollow=True,
               frame=None, profile="straight"):
        """Elliptical stack. rake: u shift per unit height (negative leans
        aft). taper: fractional radius change at the top. decal:
        (name, material, w0, w1) painted across both sides, or a list of them.
        frame: (material, width) outline along the front/back/top edges.
        profile: "straight" (linear taper) or "dome" (rounded bell top)."""
        self.ops.append(("funnel", dict(u=u, v=v, z0=z0, z1=z1, ru=ru, rv=rv, mat=mat,
                                        top=top, top_h=top_h, band=band, rake=rake,
                                        taper=taper, decal=decal, hollow=hollow,
                                        frame=frame, profile=profile)))
        return self

    def bcf_stack(self, u, v, z0, z1, ru=0.9, rv=0.7, rake=-0.12, taper=-0.1, pipes=3,
                  louvred=False):
        """Modern BC Ferries stack: royal blue with the big white wave logo,
        exhausts on top. louvred: the Coastal class navy casing with dark
        louvres and a light-blue outline."""
        hgt = z1 - z0
        logo = ("stack_logo", "white", z0 + hgt * 0.12, z1 - hgt * 0.08)
        if louvred:
            logo = ("stack_logo", "white", z0 + hgt * 0.08, z1 - hgt * 0.14)
            self.funnel(u, v, z0, z1, ru=ru, rv=rv, mat="stacknavy", top="stackblue",
                        top_h=0, rake=rake, hollow=False, profile="dome",
                        frame=("stackblue", 0.2),
                        decal=[("stack_grille", "navy", z0, z1 - 0.2), logo])
        else:
            self.funnel(u, v, z0, z1, ru=ru, rv=rv, mat="stackblue", top="stackblue", top_h=0,
                        rake=rake, taper=taper, hollow=False, decal=logo)
        ut = u + rake * (z1 - z0)
        self.exhaust(ut, v, z1 + 0.8)
        r = min(ru, rv) * (0.3 if louvred else 1 + taper) * 0.28 * (2.2 if louvred else 1)
        for i in range(pipes):
            du = (i - (pipes - 1) / 2) * r * 2.4
            self.funnel(ut + du, v, z1 - 0.2, z1 + 0.7, ru=r, rv=r, mat="dark",
                        top="copper", top_h=0.2)
        return self

    def exhaust(self, u, v, w):
        """Mark a stack outlet; OpenTTD spawns smoke there (max 4 per ship)."""
        self.exhausts.append((u, v, w))
        return self

    def solid(self, fn, mat, u0=-1e9, u1=1e9):
        """Free-form solid: fn(U, V, W) -> bool mask (or [(mask, mat)] if mat
        is None). u0/u1 bound it along the hull for speed."""
        self.ops.append(("solid", dict(fn=fn, mat=mat, u0=u0, u1=u1)))
        return self

    def ellipsoid(self, u, v, w, ru, rv, rw, mat):
        return self.solid(lambda U, V, W: ((U - u) / ru) ** 2 + ((V - v) / rv) ** 2 +
                          ((W - w) / rw) ** 2 <= 1, mat, u - ru, u + ru)

    def carve(self, u0, u1, inset, w0, w1=1e9):
        """Hollow out the hull between w0 and w1, leaving walls `inset` thick
        (open trays, or the tunnel between catamaran hulls)."""
        self.ops.append(("carve", dict(u0=u0, u1=u1, inset=inset, w0=w0, w1=w1)))
        return self

    def box(self, u0, u1, v0, v1, z0, z1, mat):
        self.ops.append(("box", dict(u0=u0, u1=u1, v0=v0, v1=v1, z0=z0, z1=z1, mat=mat)))
        return self

    def mast(self, u, z0, z1, mat="steel", v=0.0):
        self.box(u - 0.08, u + 0.08, v - 0.08, v + 0.08, z0, z1, mat)
        # yard arm + radar
        self.box(u - 0.06, u + 0.06, v - 0.6, v + 0.6, z1 - 0.6, z1 - 0.45, mat)
        self.box(u - 0.3, u + 0.3, v - 0.05, v + 0.05, z1 - 1.2, z1 - 1.05, "dark")
        return self

    def lifeboat(self, u0, u1, side, z):
        """Orange enclosed lifeboat hanging on the side of a deck (side=+-1)."""
        v_out = side * (self.B / 2 - 0.25)
        v_in = side * (self.B / 2 - 0.85)
        self.box(u0, u1, min(v_in, v_out), max(v_in, v_out), z, z + 0.75, "orange")
        self.box(u0 + 0.1, u1 - 0.1, min(v_in, v_out) + 0.1, max(v_in, v_out) - 0.1,
                 z + 0.75, z + 0.95, "white")
        # davits: an arm at each end, from the deck up and out over the boat
        for ud in (u0 + 0.05, u1 - 0.13):
            vi = v_in - side * 0.15
            self.box(ud, ud + 0.08, min(vi, vi + side * 0.08), max(vi, vi + side * 0.08),
                     z, z + 1.25, "steel")
            self.box(ud, ud + 0.08, min(vi, v_out), max(vi, v_out), z + 1.15, z + 1.25, "steel")
        return self

    def liferafts(self, u0, u1, z, half_width, pitch=0.42, sides=(-1, 1)):
        """Rows of white liferaft canisters along a deck edge."""
        for side in sides:
            v = side * (half_width - 0.22)
            u = u0
            while u <= u1:
                self.funnel(u, v, z, z + 0.32, ru=0.15, rv=0.15, mat="white", top="white",
                            top_h=0, hollow=False, band=((z + 0.12, z + 0.18), "steel"))
                u += pitch
        return self

    def radome(self, u, v, z, r=0.32):
        """White radar dome on a short pedestal."""
        self.box(u - 0.07, u + 0.07, v - 0.07, v + 0.07, z, z + 0.3, "steel")
        self.ellipsoid(u, v, z + 0.3 + r * 0.8, r, r, r, "white")
        return self

    def portal_cars(self, z, gap=0.62):
        """A couple of cars waiting just inside each car-deck portal."""
        L2 = self.L / 2
        for end in (-1, 1):
            for i, v in enumerate((-0.42, 0.42)):
                u_in = end * (L2 - 0.82)
                u_out = end * (L2 - 0.3)
                self.box(min(u_in, u_out), max(u_in, u_out), v - 0.2, v + 0.2, z, z + 0.55,
                         "car%d" % (2 + 3 * i + (end > 0)))
        return self

    def cars(self, u0, u1, v0, v1, z, seed=1):
        """Rows of little cars on an open car deck."""
        rng = np.random.RandomState(seed)
        lanes = np.arange(v0 + 0.35, v1 - 0.3, 0.75)
        for lane in lanes:
            u = u0 + 0.2
            while u + 1.1 < u1:
                if rng.rand() < 0.85:
                    m = "car%d" % rng.randint(1, 7)
                    ln = 0.9 + 0.3 * rng.rand()
                    tall = 0.55 + 0.25 * rng.rand()
                    self.box(u, u + ln, lane - 0.27, lane + 0.27, z, z + tall, m)
                    # cabin/greenhouse
                    self.box(u + 0.25, u + ln - 0.3, lane - 0.22, lane + 0.22,
                             z + tall, z + tall + 0.3, "glass")
                u += 1.4
        return self

    # --- rasterisation --------------------------------------------------------
    def _top(self):
        top = 0.0
        for kind, p in self.ops:
            top = max(top, p.get("z1", p.get("h", 0) + p.get("sheer", 0)) + 1)
        return top

    def _op_urange(self, kind, p):
        if kind in ("box", "block", "carve", "solid"):
            return p["u0"], p["u1"]
        if kind == "funnel":
            shift = p["rake"] * (p["z1"] - p["z0"])
            r = p["ru"] * (1 + max(0, p["taper"]))
            return p["u"] + min(0, shift) - r, p["u"] + max(0, shift) + r
        return -1e9, 1e9

    def voxelise(self, us, vs, ws):
        L, B = self.L, self.B
        U, V, W = np.meshgrid(us.astype(np.float32), vs.astype(np.float32),
                              ws.astype(np.float32), indexing="ij")
        mat = np.zeros(U.shape, dtype=np.int16)
        tag = np.zeros(U.shape, dtype=np.uint8)      # 1 = painted hull side plating
        aux = np.zeros(U.shape, dtype=np.float16)    # hull side: depth below the deck edge
        hb = self.hb(U)
        umin, umax = us[0], us[-1]

        def put(mask, name):
            mat[mask] = MAT_ID[name]
            tag[mask] = 0

        for kind, p in self.ops:
            a, b = self._op_urange(kind, p)
            if b < umin or a > umax:
                continue
            if kind == "hull":
                if p["height_fn"] is not None:
                    h = p["height_fn"](U)
                elif self.ends == "double":
                    h = p["h"] + p["sheer"] * np.clip(np.abs(U) / (L / 2), 0, 1) ** 3
                else:
                    h = p["h"] + p["sheer"] * np.clip(U / (L / 2), 0, 1) ** 2
                inside = (np.abs(V) <= hb) & (W <= h) & (np.abs(U) <= L / 2)
                put(inside, p["upper"])
                put(inside & (W <= p["band"]), p["lower"])
                if p["boot"]:
                    put(inside & (W <= p["boot"][0]), p["boot"][1])
                st = p["stripe"]
                if st:
                    if isinstance(st, str):
                        put(inside & (W > h - 0.6) & (W <= h - 0.3), st)
                    else:
                        put(inside & (W > st[0]) & (W <= st[1]), st[2])
                side = np.abs(V) > hb - 0.12
                s = np.where(V < 0, U, -U)
                side_a = V < 0
                if p["paint"]:
                    for mask, name in p["paint"](s, W, h, side_a):
                        if isinstance(name, dict):
                            ids = texture_ids(name["tex"], s, W, name["s"], name["w"], name["h"],
                                              name["width"])
                            sel = inside & side & mask & (ids > 0)
                            mat[sel] = ids[sel]
                        else:
                            put(inside & side & mask, name)
                for dc in p["decals"]:
                    sm = side
                    if dc.get("side") == "a":
                        sm = side & side_a
                    elif dc.get("side") == "b":
                        sm = side & ~side_a
                    if dc.get("tex"):
                        ids = texture_ids(dc["name"], s, W, dc["s"], dc["w"], dc["h"], dc["width"])
                        sel = inside & sm & (ids > 0)
                        mat[sel] = ids[sel]
                    else:
                        put(inside & sm & decal_mask(dc["name"], s, W, dc["s"], dc["w"], dc["h"]),
                            dc["mat"])
                if p["windows"]:
                    ww0, ww1, per, duty = p["windows"]
                    wm = (W > ww0) & (W <= ww1) & (np.mod(U, per) < per * duty) & \
                        (np.abs(U) < L / 2 - 1.5)
                    put(inside & side & wm, "window")
                if p["text"]:
                    txt, wm, th, tm = p["text"]
                    put(inside & side & text_mask(s, W, txt, 0.0, wm, th), tm)
                # exposed deck surface
                top = inside & (W > h - STEP * 1.01)
                put(top, p["deck"])
                if p["deck_paint"]:
                    for mask, name in p["deck_paint"](U, V):
                        put(top & mask, name)
                # bulwark lip keeps the deck edge white
                put(inside & (W > h - STEP * 1.01) & (np.abs(V) > hb - 0.15), p["upper"])
                if p["rail"]:
                    edge = (np.abs(V) <= hb) & (np.abs(V) > hb - 0.07) & (np.abs(U) <= L / 2)
                    post = np.mod(U, 0.35) < 0.08
                    rr = edge & (W > h) & (W <= h + 0.45) & ((W > h + 0.37) | post)
                    put(rr, "rail")
                hs = inside & side & (mat > 0)
                tag[hs] = 1
                aux[hs] = np.broadcast_to(h - W, W.shape)[hs]
                if p["doors"] and self.ends == "double":
                    # recessed car-deck portal: open bay, dark back wall, steel
                    # floor plate and the visor lip above the opening
                    au, wide = np.abs(U), np.abs(V) < hb * 0.62
                    z0, z1 = p["band"] + 0.2, h - 0.45
                    bay = inside & (au > L / 2 - 0.9) & wide & (W > z0) & (W < z1)
                    mat[bay] = 0
                    tag[bay] = 0
                    put((au > L / 2 - 0.95) & (au <= L / 2 - 0.85) & wide & (W > z0) & (W < z1)
                        & (np.abs(V) <= hb), "dark")
                    put(inside & (au > L / 2 - 0.9) & wide & (W > z0 - 0.12) & (W <= z0),
                        "steel")
                    put(inside & (au > L / 2 - 0.95) & (np.abs(V) < hb * 0.66) & (W >= z1) &
                        (W < z1 + 0.14), "steel")
            elif kind == "cat":
                for side in (-1, 1):
                    c = side * p["sep"]
                    q = np.clip((U - (L / 2 - 0.3 * L)) / (0.3 * L), 0, 1)
                    w = p["hb"] * np.sqrt(1 - q ** 1.5)
                    inside = (np.abs(V - c) <= w) & (W <= p["h"]) & (np.abs(U) <= L / 2)
                    put(inside, p["upper"])
                    put(inside & (W <= p["band"]), p["lower"])
            elif kind == "block":
                if p["v0"] is not None:
                    vm = (V >= p["v0"]) & (V <= p["v1"]) & (np.abs(V) <= hb * p["wf"])
                    side_d = np.minimum(np.abs(V - p["v0"]), np.abs(V - p["v1"]))
                    side_d = np.minimum(side_d, hb * p["wf"] - np.abs(V))
                elif p["rect"]:
                    wl = np.full(U.shape, B / 2 * p["wf"], dtype=np.float32)
                    vm = np.abs(V) <= wl
                    side_d = wl - np.abs(V)
                else:
                    if p["round_ends"]:
                        mid, half = (p["u0"] + p["u1"]) / 2, (p["u1"] - p["u0"]) / 2
                        rr = min(half, B * 0.5)
                        q = np.clip((np.abs(U - mid) - (half - rr)) / rr, 0, 1)
                        wl = np.minimum(hb * p["wf"],
                                        B / 2 * p["wf"] * (0.55 + 0.45 * np.sqrt(1 - q ** 2)))
                    else:
                        wl = hb * p["wf"]
                    vm = np.abs(V) <= wl
                    side_d = wl - np.abs(V)
                um = (U >= p["u0"]) & (U <= p["u1"])
                end_d = np.minimum(U - p["u0"], p["u1"] - U)
                inside = vm & um & (W > p["z0"]) & (W <= p["z1"])
                put(inside, p["mat"])
                if p["windows"]:
                    band = (W > p["z0"] + 0.55) & (W <= p["z1"] - 0.5)
                    surf_side = side_d < 0.12
                    surf_end = end_d < 0.12
                    ew = p["end_windows"]
                    if ew is None:
                        ew = True
                    if p["panes"]:
                        per, duty = p["panes"] if isinstance(p["panes"], tuple) else (0.34, 0.74)
                        pane_side = np.mod(U, per) < per * duty
                        pane_end = np.mod(V, per) < per * duty
                    else:
                        pane_side = pane_end = True
                    win = surf_side & pane_side
                    if ew:
                        win = win | (surf_end & ~surf_side & pane_end)
                    put(inside & band & win, p["win_mat"])
                if p["decals"]:
                    sd = np.where(V < 0, U, -U)
                    for dc in p["decals"]:
                        if dc.get("tex"):
                            ids = texture_ids(dc["name"], sd, W, dc["s"], dc["w"], dc["h"],
                                              dc["width"])
                            sel = inside & (side_d < 0.12) & (ids > 0)
                            mat[sel] = ids[sel]
                            tag[sel] = 0
                        else:
                            put(inside & (side_d < 0.12) &
                                decal_mask(dc["name"], sd, W, dc["s"], dc["w"], dc["h"]),
                                dc["mat"])
                if p["roof"]:
                    put(inside & (W > p["z1"] - STEP * 1.01), p["roof"])
                if p["rail"]:
                    edge = vm & um & ((side_d < 0.07) | (end_d < 0.07))
                    post = (np.mod(U, 0.35) < 0.08) | (np.mod(V, 0.35) < 0.08)
                    rr = edge & (W > p["z1"]) & (W <= p["z1"] + 0.45) & \
                        ((W > p["z1"] + 0.37) | post)
                    put(rr, "rail")
            elif kind == "funnel":
                hgt = p["z1"] - p["z0"]
                uc = p["u"] + p["rake"] * (W - p["z0"])
                t = np.clip((W - p["z0"]) / hgt, 0, 1)
                if p["profile"] == "dome":
                    sc = 0.3 + 0.7 * np.sqrt(np.clip(1 - t ** 2.2, 0, 1))
                else:
                    sc = 1 + p["taper"] * t
                e = ((U - uc) / (p["ru"] * sc)) ** 2 + ((V - p["v"]) / (p["rv"] * sc)) ** 2
                inside = (e <= 1) & (W > p["z0"]) & (W <= p["z1"])
                put(inside, p["mat"])
                if p["band"]:
                    bz, bmat = p["band"]
                    put(inside & (W > bz[0]) & (W <= bz[1]), bmat)
                fs = np.where(V < p["v"], U - uc, uc - U)
                fside = np.abs(V - p["v"]) > p["rv"] * sc * 0.2
                if p["frame"]:
                    fm, fw = p["frame"]
                    q = np.abs(U - uc) / (p["ru"] * sc)
                    put(inside & ((q > 1 - fw / (p["ru"] * sc)) | (W > p["z1"] - fw)), fm)
                dl = p["decal"]
                if dl and not isinstance(dl, list):
                    dl = [dl]
                for dn, dm, dw0, dw1 in dl or ():
                    put(inside & fside & decal_mask(dn, fs, W, 0.0, (dw0 + dw1) / 2, dw1 - dw0,
                                                    width=2 * p["ru"] * 0.86), dm)
                if p["top_h"]:
                    put(inside & (W > p["z1"] - p["top_h"]), p["top"])
                if p["hollow"]:
                    put(inside & (e < 0.55) & (W > p["z1"] - 0.15), "dark")
            elif kind == "solid":
                res = p["fn"](U, V, W)
                if p["mat"] is None:
                    for mask, name in res:
                        if isinstance(name, np.ndarray):          # texture material ids
                            sel = mask & (name > 0)
                            mat[sel] = name[sel]
                        else:
                            put(mask, name)
                else:
                    put(res, p["mat"])
            elif kind == "carve":
                cv = (U > p["u0"]) & (U < p["u1"]) & (np.abs(V) < hb - p["inset"]) & \
                    (W > p["w0"]) & (W < p["w1"])
                mat[cv] = 0
                tag[cv] = 0
            elif kind == "box":
                inside = (U >= p["u0"]) & (U <= p["u1"]) & (V >= p["v0"]) & (V <= p["v1"]) \
                    & (W > p["z0"]) & (W <= p["z1"])
                put(inside, p["mat"])
        return mat, tag, aux

    def surface(self):
        """Surface voxels of the whole ship: positions, normals, material,
        hull-side tag, depth below deck edge and ambient occlusion."""
        L, B = self.L, self.B
        pad = 5
        us_all = np.arange(-L / 2 - 0.3, L / 2 + 0.3, STEP) + STEP / 2
        vs = np.arange(-B / 2 - 0.9, B / 2 + 0.9, STEP) + STEP / 2
        ws = np.arange(0, self._top(), STEP) + STEP / 2
        out = []
        for start in range(0, len(us_all), CHUNK):
            lo, hi = max(0, start - pad), min(len(us_all), start + CHUNK + pad)
            us = us_all[lo:hi]
            mat, tag, aux = self.voxelise(us, vs, ws)
            occ = mat > 0
            padded = np.pad(occ, 1)
            nb = np.zeros_like(occ)
            for ax in range(3):
                for d in (-1, 1):
                    nb |= ~np.roll(padded, d, axis=ax)[1:-1, 1:-1, 1:-1]
            surf = occ & nb
            f = occ.astype(np.float32)
            for _ in range(4):
                for ax in range(3):
                    f = (np.roll(f, 1, ax) + f + np.roll(f, -1, ax)) / 3
            gu, gv, gw = np.gradient(f)
            keep = np.zeros_like(surf)
            keep[start - lo:start - lo + min(CHUNK, len(us_all) - start)] = True
            idx = np.nonzero(surf & keep)
            n = np.stack([-gu[idx], -gv[idx], -gw[idx]], 1)
            n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-6
            pos = np.stack([us[idx[0]], vs[idx[1]], ws[idx[2]]], 1).astype(np.float32)
            out.append((pos, n.astype(np.float32), mat[idx], tag[idx],
                        aux[idx].astype(np.float32)))
        cat = [np.concatenate([o[i] for o in out]) for i in range(5)]
        cat.append(self._ambient_occlusion(cat[0], cat[1]))
        return cat

    def _ambient_occlusion(self, pos, nrm):
        """How enclosed each surface point is, from a coarse blurred occupancy
        grid sampled a little way out along the normal (0.5 = deep corner)."""
        global STEP
        fine = STEP
        cstep = fine * 5
        STEP = cstep
        try:
            L, B = self.L, self.B
            us = np.arange(-L / 2 - 1.0, L / 2 + 1.0, cstep) + cstep / 2
            vs = np.arange(-B / 2 - 1.2, B / 2 + 1.2, cstep) + cstep / 2
            ws = np.arange(0, self._top() + 1.0, cstep) + cstep / 2
            occ = (self.voxelise(us, vs, ws)[0] > 0).astype(np.float32)
        finally:
            STEP = fine
        r = max(1, int(round(0.25 / cstep)))
        for _ in range(3):
            for ax in range(3):
                acc = occ.copy()
                for d in range(1, r + 1):
                    acc += np.roll(occ, d, ax) + np.roll(occ, -d, ax)
                occ = acc / (2 * r + 1)
        q = pos + nrm * 0.35
        iu = np.clip(((q[:, 0] - us[0]) / cstep).round().astype(int), 0, len(us) - 1)
        iv = np.clip(((q[:, 1] - vs[0]) / cstep).round().astype(int), 0, len(vs) - 1)
        iw = np.clip(((q[:, 2] - ws[0]) / cstep).round().astype(int), 0, len(ws) - 1)
        dens = occ[iu, iv, iw]
        return np.clip(1 - 1.4 * (dens - 0.08), 0.55, 1.0).astype(np.float32)

    def _weathered_colours(self, pos, mat, tag, aux):
        """Base colours with plating seams, panel-to-panel variation, rust
        streaks running down from the deck edge and waterline grime, all
        scaled by self.weather."""
        rgb = MAT_RGB[mat].copy()
        wx = self.weather
        side = tag == 1
        if not side.any() or wx <= 0:
            return rgb
        u, w, a = pos[side, 0], pos[side, 2], aux[side]
        c = rgb[side]
        bright = c.mean(1)

        def h2(x, y, seed):
            v = np.sin(x * 12.9898 + y * 78.233 + seed * 37.719) * 43758.5453
            return v - np.floor(v)
        # plating: seams and slightly uneven panels
        pu, pw = 1.5, 1.25
        seam = (np.abs(np.mod(u, pu) - pu / 2) > pu / 2 - 0.022) | \
            (np.abs(np.mod(w, pw) - pw / 2) > pw / 2 - 0.018)
        f = 1 + 0.035 * (h2(np.floor(u / pu), np.floor(w / pw), 1) - 0.5) * (0.4 + wx)
        f = np.where(seam, f * (1 - 0.025 * (0.4 + wx)), f)
        c *= f[:, None]
        # rust streaks bleeding from scuppers / fittings below the deck edge
        cell = np.floor(u / 0.55)
        src = (cell + 0.2 + 0.6 * h2(cell, 3, 2)) * 0.55
        ln = 0.6 + 2.4 * h2(cell, 5, 3)
        on = h2(cell, 7, 4) < wx * 0.5
        dist = a - 0.2
        width = 0.03 + 0.018 * np.clip(dist, 0, None)
        streak = on & (dist > 0) & (dist < ln) & (np.abs(u - src) < width)
        k = (wx * 0.85 * (1 - dist / ln) * (0.55 + 0.45 * h2(cell, 9, 5)))[streak]
        rust = np.array([128, 70, 42], np.float32)
        c[streak] = c[streak] * (1 - k[:, None]) + rust * k[:, None]
        # grime along the waterline on light paint
        g = np.clip((1.7 - w) / 0.9, 0, 1) * wx * (bright > 140)
        tint = np.array([0.86, 0.84, 0.78], np.float32)
        c *= (1 - g[:, None] * (1 - tint))
        rgb[side] = c
        return rgb

    def _wake(self, k):
        """Foam on the water for a ship under way: Kelvin bow-wave arms,
        a cushion at the bow, a turbulent stern wake. Points in model units
        (u, v) with alpha."""
        L, B = self.L, self.B
        sf = float(np.clip(self.speed / 18.0, 0.6, 2.0))
        step = 0.045 / k
        us = np.arange(-L / 2 - 0.85 * L * sf, L / 2 + 0.12 * L, step)
        vs = np.arange(-B * 2.2, B * 2.2, step)
        U, V = np.meshgrid(us, vs, indexing="ij")

        def noise(x, y, fq):
            """Smooth value noise in 0..1 (two octaves)."""
            def octave(f):
                xi, yi = np.floor(x * f), np.floor(y * f)
                xf, yf = x * f - xi, y * f - yi

                def hsh(a, b):
                    v = np.sin(a * 127.1 + b * 311.7) * 43758.5453
                    return v - np.floor(v)
                sx, sy = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)
                top = hsh(xi, yi) * (1 - sx) + hsh(xi + 1, yi) * sx
                bot = hsh(xi, yi + 1) * (1 - sx) + hsh(xi + 1, yi + 1) * sx
                return top * (1 - sy) + bot * sy
            return 0.65 * octave(fq) + 0.35 * octave(fq * 2.7)
        a = np.zeros(U.shape, np.float32)
        back = L / 2 - U                                   # distance aft of the bow
        arm = np.abs(np.abs(V) - (self.hb(np.clip(U, -L / 2, L / 2)) * 0.6 + 0.36 * back))
        kel = np.clip(1 - arm / (0.1 + 0.035 * back), 0, 1) * \
            np.exp(-np.clip(back, 0, None) / (0.22 * L * sf)) * 0.6 * (back >= 0)
        a = np.maximum(a, kel * noise(U, V, 2.5) ** 0.7)
        cush = (U > L / 2 - 0.25 * L) & (U < L / 2 + 0.06 * L * sf) & \
            (np.abs(V) < self.hb(np.clip(U, -L / 2, L / 2)) + 0.25)
        a = np.maximum(a, cush * 0.6 * noise(U, V, 3.0))
        d = -L / 2 - U
        sw = self.hb(np.full_like(U, -L / 2)) * 0.9 + 0.22 * np.clip(d, 0, None)
        stern = ((d > -0.3) & (np.abs(V) < sw)).astype(np.float32)
        a = np.maximum(a, stern * np.exp(-np.clip(d, 0, None) / (0.28 * L * sf)) * 0.85 *
                       (0.25 + 0.75 * noise(U, V, 1.8)) * np.clip(1 - np.abs(V) / sw, 0, 1) ** 0.5)
        hull = (np.abs(U) <= L / 2) & (np.abs(V) <= self.hb(np.clip(U, -L / 2, L / 2)))
        a[hull] = 0
        keep = a > 0.04
        return U[keep], V[keep], a[keep]

    def render(self):
        """Returns 8 views as (still RGBA, moving RGBA, x0, y0) float images
        at ZOOM; x0/y0 and sizes are aligned to ZOOM so they downsample
        exactly. 'moving' adds the wake."""
        global STEP
        k = SCALE * self.scale
        STEP = BASE_STEP / k          # keep the same voxel density on screen
        pos, nrm, m, tag, aux, ao = self.surface()
        # thin flat parts (wings, stabilisers): use exact up/down normals
        # instead of the stair-stepped voxel gradient, which streaks
        flat = np.isin(m, [MAT_ID[n] for n in getattr(self, "flat_mats", ())])
        if flat.any():
            up = np.sign(nrm[flat, 2]) + (nrm[flat, 2] == 0)
            nrm = nrm.copy()
            nrm[flat] = np.stack([np.zeros_like(up), np.zeros_like(up), up], 1)
            ao = ao.copy()
            ao[flat] = np.maximum(ao[flat], 0.92)
        base = self._weathered_colours(pos, m, tag, aux)
        glossy = GLOSSY[m]
        bright = base.mean(1)
        spec_k = np.where(glossy, 0.9, np.where(bright > 170, 0.22, 0.12)).astype(np.float32)
        shin = np.where(glossy, 40.0, 14.0).astype(np.float32)
        wk_u, wk_v, wk_a = self._wake(k) if getattr(self, "wake", True) else (np.zeros(0),) * 3
        wk_u, wk_v = wk_u * k, wk_v * k
        pos = pos * k
        pu, pv, pw = pos[:, 0], pos[:, 1], pos[:, 2]
        nu, nv, nw = nrm[:, 0], nrm[:, 1], nrm[:, 2]
        views = []
        for hx, hy in HEADINGS:
            n = math.hypot(hx, hy)
            hx, hy = hx / n, hy / n
            px_, py_ = -hy, hx
            x = pu * hx + pv * px_
            y = pu * hy + pv * py_
            z = pw * ZS
            wx = nu * hx + nv * px_
            wy = nu * hy + nv * py_
            wz = nw / ZS
            wl = np.sqrt(wx ** 2 + wy ** 2 + wz ** 2) + 1e-6
            wx, wy, wz = wx / wl, wy / wl, wz / wl
            col = shade(x, y, z, wx, wy, wz, base, ao, glossy, spec_k, shin)
            # --- screen positions: ship, its shadow on the water, the wake
            sx = ZOOM * 2 * (y - x)
            sy = ZOOM * ((x + y) - z)
            gx, gy = x - LIGHT[0] * z / LIGHT[2], y - LIGHT[1] * z / LIGHT[2]
            ssx, ssy = ZOOM * 2 * (gy - gx), ZOOM * (gx + gy)
            if not getattr(self, "ground_shadow", True):    # aircraft: OpenTTD draws its own
                ssx, ssy = sx[:1], sy[:1]
            wkx, wky = wk_u * hx + wk_v * px_, wk_u * hy + wk_v * py_
            wsx, wsy = ZOOM * 2 * (wky - wkx), ZOOM * (wkx + wky)
            allx = np.concatenate([sx, ssx, wsx])
            ally = np.concatenate([sy, ssy, wsy])
            x0 = (int(np.floor(allx.min())) // ZOOM - 1) * ZOOM
            y0 = (int(np.floor(ally.min())) // ZOOM - 1) * ZOOM
            wdt = -(-(int(np.ceil(allx.max())) - x0 + 3) // ZOOM) * ZOOM
            hgt = -(-(int(np.ceil(ally.max())) - y0 + 3) // ZOOM) * ZOOM
            ship_c, ship_a = raster(sx, sy, x + y + 2 * z, col, x0, y0, wdt, hgt)
            # --- soft shadow on the water
            sh = np.zeros(hgt * wdt, np.float32)
            sh[(ssy.astype(int) - y0) * wdt + (ssx.astype(int) - x0)] = 1
            sh = _blur(sh.reshape(hgt, wdt), 3, 2)
            sh_a = (0.26 if getattr(self, "ground_shadow", True) else 0.0) * np.clip(sh * 1.6, 0, 1)
            sh_c = np.array([12, 22, 38], np.float32)
            # --- wake foam
            wk = np.zeros(hgt * wdt, np.float32)
            np.maximum.at(wk, (wsy.astype(int) - y0) * wdt + (wsx.astype(int) - x0), wk_a)
            wk_a2 = np.clip(_blur(wk.reshape(hgt, wdt), 2, 1) * 1.15, 0, 0.9)
            wk_c = np.array([236, 244, 250], np.float32)
            uc_s, ua_s = np.broadcast_to(sh_c, (hgt, wdt, 3)), sh_a
            uc_m, ua_m = over(np.broadcast_to(wk_c, (hgt, wdt, 3)), wk_a2, uc_s, ua_s)
            still = over(ship_c, ship_a, uc_s, ua_s)
            moving = over(ship_c, ship_a, uc_m, ua_m)
            views.append((np.dstack([still[0], still[1]]), np.dstack([moving[0], moving[1]]),
                          x0, y0))
        return views


_CAM = np.array([1.0, 1.0, 2.0]) / math.sqrt(6)
_HALF = (LIGHT + _CAM) / np.linalg.norm(LIGHT + _CAM)
_E1 = np.cross(LIGHT, [0, 0, 1.0]) / np.linalg.norm(np.cross(LIGHT, [0, 0, 1.0]))
_E2 = np.cross(LIGHT, _E1)


def shade(x, y, z, wx, wy, wz, base, ao, glossy, spec_k, shin):
    """Light surface points given in screen-world coordinates (x SW, y SE,
    z up in pixels) with unit normals: ambient (occluded) + direct with cast
    shadows from a light-space depth map (3x3 soft filter) + specular, plus
    a little sky reflected in glass. Returns RGB float per point."""
    ndl = np.clip(wx * LIGHT[0] + wy * LIGHT[1] + wz * LIGHT[2], 0, 1)
    la = x * _E1[0] + y * _E1[1] + z * _E1[2]
    lb = x * _E2[0] + y * _E2[1] + z * _E2[2]
    ld = x * LIGHT[0] + y * LIGHT[1] + z * LIGHT[2]
    cs = 0.06
    ia = ((la - la.min()) / cs).astype(np.int64) + 1
    ib = ((lb - lb.min()) / cs).astype(np.int64) + 1
    na, nb_ = ia.max() + 2, ib.max() + 2
    maxd = np.full(na * nb_, -1e9, np.float32)
    o = np.argsort(ld)
    maxd[(ia * nb_ + ib)[o]] = ld[o]
    bias = 0.09 + 0.18 * (1 - ndl)
    lit_f = np.zeros_like(ld)
    for da in (-1, 0, 1):
        for db in (-1, 0, 1):
            lit_f += ld >= maxd[(ia + da) * nb_ + (ib + db)] - bias
    shadow = lit_f / 9.0
    spec = np.clip(wx * _HALF[0] + wy * _HALF[1] + wz * _HALF[2], 0, 1) ** shin
    col = base * (0.62 * ao + 0.48 * ndl * shadow)[:, None]
    col += (255 * spec_k * spec * shadow)[:, None]
    col[glossy] += (38 * np.clip(wz[glossy] + 0.3, 0, 1))[:, None]   # sky in glass
    return np.clip(col, 0, 255)


def raster(sx, sy, depth, col, x0, y0, wdt, hgt):
    """Z-buffer points into a wdt x hgt image at origin (x0, y0) with four
    jittered passes (2x2 anti-aliasing). Returns (rgb, alpha) arrays."""
    order = np.argsort(depth)
    acc = np.zeros((hgt * wdt, 3), np.float32)
    cnt = np.zeros(hgt * wdt, np.float32)
    for ox, oy in ((0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)):
        lin = (np.floor(sy + oy).astype(int) - y0) * wdt + (np.floor(sx + ox).astype(int) - x0)
        buf = np.full(hgt * wdt, -1, dtype=np.int64)
        buf[lin[order]] = order
        hit = buf >= 0
        acc[hit] += col[buf[hit]]
        cnt[hit] += 1
    return (acc / np.maximum(cnt, 1)[:, None]).reshape(hgt, wdt, 3), (cnt / 4).reshape(hgt, wdt)


def over(c1, a1, c2, a2):
    """Straight-alpha 'over' compositing of layer 1 on layer 2."""
    a = a1 + a2 * (1 - a1)
    c = (c1 * a1[..., None] + c2 * (a2 * (1 - a1))[..., None]) / np.maximum(a, 1e-6)[..., None]
    return c, a


def _blur(img, r, passes):
    for _ in range(passes):
        for ax in (0, 1):
            acc = img.copy()
            for d in range(1, r + 1):
                acc += np.roll(img, d, ax) + np.roll(img, -d, ax)
            img = acc / (2 * r + 1)
    return img


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def downsample(rgba, f):
    """Box-filter an RGBA (straight alpha) image by f, alpha-weighted."""
    if f == 1:
        return rgba
    h, w, _ = rgba.shape
    a = rgba[..., 3]
    pa = (rgba[..., :3] * a[..., None]).reshape(h // f, f, w // f, f, 3).sum(axis=(1, 3))
    asum = a.reshape(h // f, f, w // f, f).sum(axis=(1, 3))
    col = pa / np.maximum(asum, 1e-6)[..., None]
    return np.dstack([col, asum / (f * f)])


def quantise(rgba):
    """RGBA float -> DOS palette indices (alpha < 0.5 becomes transparent)."""
    h, w, _ = rgba.shape
    rgb = rgba[..., :3].reshape(-1, 3)
    op = rgba[..., 3].reshape(-1) >= 0.5
    out = np.zeros(h * w, dtype=np.uint8)
    c = rgb[op]
    diff = c[:, None, :] - USABLE_RGB[None, :, :]
    d = ((diff * np.array([0.30, 0.59, 0.11]) * 3) ** 2).sum(-1) + 0.5 * (diff ** 2).sum(-1)
    out[op] = USABLE[np.argmin(d, axis=1)]
    return out.reshape(h, w)


def views_at(views, zoom, moving=False):
    """(rgba, xofs, yofs) for each view at the given zoom (1, 2 or 4)."""
    f = ZOOM // zoom
    return [(downsample(mv if moving else st, f), x0 // f, y0 // f)
            for st, mv, x0, y0 in views]


def _pack(items, depth):
    gap = 2
    total_w = sum(i[0].shape[1] for i in items) + gap * (len(items) + 1)
    total_h = max(i[0].shape[0] for i in items) + gap * 2
    sheet = np.zeros((total_h, total_w) + ((4,) if depth == 32 else ()), dtype=np.uint8)
    entries = []
    x = gap
    for img, xo, yo in items:
        h, w = img.shape[:2]
        sheet[gap:gap + h, x:x + w] = img
        entries.append((x, gap, w, h, xo, yo))
        x += w + gap
    return sheet, entries


def save_sheet_32(items, path):
    items = [(np.dstack([np.clip(r[..., :3], 0, 255),
                         np.clip(r[..., 3] * 255, 0, 255)]).round().astype(np.uint8), xo, yo)
             for r, xo, yo in items]
    sheet, entries = _pack(items, 32)
    Image.fromarray(sheet).save(path)
    return entries


def save_sheet_8(items, path):
    items = [(quantise(r), xo, yo) for r, xo, yo in items]
    sheet, entries = _pack(items, 8)
    im = Image.frombytes("P", (sheet.shape[1], sheet.shape[0]), np.ascontiguousarray(sheet).tobytes())
    im.putpalette(DOS_PAL)
    im.save(path)
    return entries
