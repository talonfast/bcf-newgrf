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
import numpy as np

import render
from render import Ship, MAT_RGB, GLOSSY, LIGHT, ZOOM, BASE_STEP, shade, raster, over, _blur

TILE = 16


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
        top = 0.0
        for kind, p in self.ops:
            top = max(top, p.get("z1", 0) + 1)
        return top + self.extra_top

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
        bc, ba = raster(sx, sy, lx + ly + 2 * lz, col[sel], x0, y0, wdt, hgt)
        sh = np.zeros(hgt * wdt, np.float32)
        sh[(gsy.astype(int) - y0) * wdt + (gsx.astype(int) - x0)] = 1
        sh_a = 0.3 * np.clip(_blur(sh.reshape(hgt, wdt), 3, 2) * 1.6, 0, 1)
        sh_c = np.broadcast_to(np.array([20, 22, 26], np.float32), (hgt, wdt, 3))
        c, a = over(bc, ba, sh_c, sh_a)
        return np.dstack([c, a]), x0, y0


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
    return b


# ---------------------------------------------------------------------------
# The rest of Tsawwassen terminal (photos on Commons: tollbooths, loading
# ramp, passenger gangway, lineup, views from arriving ferries, 2008-2024)
# ---------------------------------------------------------------------------

def _paving(b, mat="concrete", joints=2.0):
    b.sol(lambda X, Y, Z: [((Z <= 0.25), mat),
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
    top = CLOTHES[rng.randint(len(CLOTHES))]
    b.bx(x - 0.2, x + 0.2, y - 0.16, y + 0.16, z, z + 0.85, "denim" if rng.rand() < 0.6 else "dark")
    b.bx(x - 0.24, x + 0.24, y - 0.2, y + 0.2, z + 0.85, z + 1.6, top)
    b.ellipsoid(x - b.cx, y - b.cy, z + 1.82, 0.19, 0.19, 0.22, "skin" if rng.rand() < 0.7 else "skin2")


def _people(b, n, x0, x1, y0, y1, z, rng, avoid=()):
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
    with a window band, the big BC Ferries letters standing on the roof."""
    from render import decal_mask
    b = Building(2, 2)
    b.extra_top = 6.0
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
        out += [(up, "alu"), (up & (np.mod(along, 0.45) < 0.1), "steel"),
                (up & (Z > 10.6) & (Z < 12.8) & (np.mod(along, 2.0) < 1.6), "window"),
                (inside & (Z > 15.7), "membrane"), (inside & (np.abs(Z - 8.0) < 0.2) & face, "navy")]
        return out
    b.sol(body, None, X0, X1)
    # entrance canopy on the front
    b.bx(13.0, 19.0, Y1, Y1 + 2.4, 6.4, 6.9, "white")
    b.bx(13.0, 19.0, Y1, Y1 + 2.4, 6.2, 6.4, "timber")
    # the big '~BCFerries' letters standing on the front edge of the roof
    cx = (X0 + X1) / 2

    def sign(X, Y, Z):
        plate = (Y > Y1 - 1.0) & (Y < Y1 - 0.6) & (Z > 16.0) & (Z < 20.6) & \
            (X > X0 + 1) & (X < X1 - 1)
        # X runs towards the viewer's left on the front (SE) face, so read it reversed
        ink = decal_mask("wordmark", cx - X, Z, 0.0, 18.3, 4.4, width=22.0)
        return [(plate & ink, "bcfblue"),
                ((Y > Y1 - 1.0) & (Y < Y1 - 0.6) & (Z > 16.0) & (Z < 16.4) & (X > X0 + 1) &
                 (X < X1 - 1), "steel")]
    b.sol(sign, None, X0, X1)
    # rooftop plant and lamp posts in the plaza
    b.bx(6.0, 10.0, 9.0, 13.0, 16.0, 17.6, "steel")
    b.bx(20.0, 23.0, 10.0, 12.0, 16.0, 17.2, "steel")
    for x in (4.0, 16.0, 28.0):
        b.bx(x - 0.07, x + 0.07, 29.6, 29.74, 0.25, 10.0, "steel")
        b.bx(x - 0.25, x + 0.25, 29.45, 29.9, 9.7, 10.1, "dark")
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
    return b


def holding_lanes(variant=0):
    """Vehicle holding compound: four lanes along X with cars queued
    (OpenTTD road-vehicle scale). Variant 1 has a box truck and gaps."""
    b = Building(1, 1)
    rng = np.random.RandomState(7 + variant)

    def ground(X, Y, Z):
        g = Z <= 0.2
        return [(g, "asphalt"),
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
    return b
