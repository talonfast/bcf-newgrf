"""
Scene geometry of the two seaplane terminals, as clouds of surface points.

Coordinates are OpenTTD world units relative to the north corner of the airport:
x and y in 1/16 tile (16 per tile), z in height pixels above the water.
Every primitive is tagged as "ground" (flat floating docks, drawn as ground
overlays under everything else) or "building" (drawn as a sorted sprite).

Layouts (default rotation, x to the south-west, y to the south-east):

Victoria Harbour (Commuter airport state machine, 5 x 4):
    row 0  terminal barge (2 tiles) + flag deck, gangway, floating hangar (4,0)
    row 1  taxi lane (open water)
    row 2  three berths (1,2) (2,2) (3,2) between finger docks, main dock on the south-east edge
    row 3  water runway with marker buoys

Vancouver / Coal Harbour (International airport state machine, 7 x 7):
    rows 0 and 6  water runways with marker buoys
    column 3      central pier: two-storey terminal (3,2)-(3,3), control tower (3,4)
    berths        (2,2) (2,3) (2,4) and (4,2) (4,3) (4,4), nose-in to the pier between finger docks
    hangars       (0,3) and (6,1); fuel dock (0,2)
"""

import numpy as np

from render import Cloud

STEP = 0.045  # sampling step in world units (dense enough for 4x zoom with 2x supersampling)

# Colours
DECK = (172, 168, 158)
DECK_WOOD = (150, 118, 84)
HULL = (78, 82, 92)
SILVER = (196, 200, 206)
GLASS = (58, 92, 112)
GLASS_DARK = (40, 64, 82)
GLULAM = (186, 136, 82)
LIVING_ROOF = (96, 138, 62)
WHITE = (226, 228, 228)
NAVY = (22, 46, 112)
YELLOW = (248, 204, 30)
RED = (212, 40, 40)
DOOR = (92, 96, 102)
CONCRETE = (186, 186, 180)
ROOF_GREY = (150, 152, 156)
DARK = (54, 56, 60)
BUOY = (250, 170, 30)


class Scene:
    """
    rotation: 0 = north (as designed), 1 = east, 2 = south, 3 = west; primitives are given in the north frame and
    placed rotated, matching how OpenTTD rotates airport movement data (RotateAirportMovingData).
    """

    def __init__(self, size_x, size_y, rotation=0):
        self.design_size = (size_x, size_y)
        self.rotation = rotation
        self.size = (size_y, size_x) if rotation in (1, 3) else (size_x, size_y)
        self.parts = {"ground": [], "building": []}

    def to_world(self, x, y):
        w0, h0 = self.design_size[0] * 16, self.design_size[1] * 16
        return [(x, y), (y, w0 - x), (w0 - x, h0 - y), (h0 - y, x)][self.rotation]

    def to_design(self, x, y):
        w0, h0 = self.design_size[0] * 16, self.design_size[1] * 16
        return [(x, y), (w0 - y, x), (w0 - x, h0 - y), (y, h0 - x)][self.rotation]

    def add(self, layer, pos, normal, rgb, gain=None):
        self.parts[layer].append(Cloud(pos, normal, rgb, gain))

    def cloud(self, layer):
        return Cloud.concat(self.parts[layer])


def _grid(a0, a1, b0, b1, step=STEP):
    a = np.arange(a0, a1 + 1e-6, step, dtype=np.float32)
    b_ = np.arange(b0, b1 + 1e-6, step, dtype=np.float32)
    A, B = np.meshgrid(a, b_, indexing="ij")
    return A.ravel(), B.ravel()


def _colour(spec, x, y, z, face):
    if callable(spec):
        return np.asarray(spec(x, y, z, face), np.float32)
    return np.broadcast_to(np.asarray(spec, np.float32), (len(x), 3))


def box(scene, layer, x0, x1, y0, y1, z0, z1, colour, top=None):
    """Axis-aligned box; only the faces the camera can see (+x, +y, +z) are sampled."""
    top = colour if top is None else top
    if getattr(scene, "rotation", 0):
        # Rotate the box, sample it in the world frame, colour it with design-frame coordinates.
        (ax, ay), (bx, by) = scene.to_world(x0, y0), scene.to_world(x1, y1)
        swap = scene.rotation in (1, 3)

        def wrap(spec):
            if not callable(spec):
                return spec

            def f(x, y, z, face):
                dx, dy = scene.to_design(x, y)
                return spec(dx, dy, z, {"x": "y", "y": "x"}.get(face, face) if swap else face)
            return f
        r, scene.rotation = scene.rotation, 0
        try:
            box(scene, layer, min(ax, bx), max(ax, bx), min(ay, by), max(ay, by), z0, z1, wrap(colour), wrap(top))
        finally:
            scene.rotation = r
        return
    X, Y = _grid(x0, x1, y0, y1)
    Z = np.full_like(X, z1)
    scene.add(layer, np.stack([X, Y, Z], 1), np.tile([0, 0, 1.0], (len(X), 1)), _colour(top, X, Y, Z, "top"))
    Y2, Z2 = _grid(y0, y1, z0, z1)
    X2 = np.full_like(Y2, x1)
    scene.add(layer, np.stack([X2, Y2, Z2], 1), np.tile([1.0, 0, 0], (len(X2), 1)), _colour(colour, X2, Y2, Z2, "x"))
    X3, Z3 = _grid(x0, x1, z0, z1)
    Y3 = np.full_like(X3, y1)
    scene.add(layer, np.stack([X3, Y3, Z3], 1), np.tile([0, 1.0, 0], (len(X3), 1)), _colour(colour, X3, Y3, Z3, "y"))


def heightfield(scene, layer, x0, x1, y0, y1, h, colour, skirt_to=None, skirt_colour=None, jitter=0.0, seed=1):
    """Surface z = h(x, y), with optional vertical skirts on the +x and +y edges down to skirt_to."""
    X, Y = _grid(x0, x1, y0, y1)
    Z = h(X, Y).astype(np.float32)
    e = 0.05
    dzdx = (h(X + e, Y) - h(X - e, Y)) / (2 * e)
    dzdy = (h(X, Y + e) - h(X, Y - e)) / (2 * e)
    n = np.stack([-dzdx, -dzdy, np.ones_like(X)], 1)
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    gain = None
    if jitter:
        rng = np.random.default_rng(seed)
        # Coarse noise (per 0.5 unit cell) so it survives downsampling as texture.
        cell = (np.floor(X * 2).astype(np.int64) * 7919 + np.floor(Y * 2).astype(np.int64) * 104729) % 1000003
        gain = 1.0 + jitter * (rng.random(1000003)[cell] * 2 - 1)
    scene.add(layer, np.stack([X, Y, Z], 1), n, _colour(colour, X, Y, Z, "top"), gain)
    if skirt_to is not None:
        sc = skirt_colour or colour
        for edge in ("x", "y"):
            if edge == "x":
                B = np.arange(y0, y1 + 1e-6, STEP, dtype=np.float32)
                Xe = np.full_like(B, x1)
                Ye = B
                nrm = [1.0, 0, 0]
            else:
                B = np.arange(x0, x1 + 1e-6, STEP, dtype=np.float32)
                Xe = B
                Ye = np.full_like(B, y1)
                nrm = [0, 1.0, 0]
            top = h(Xe, Ye)
            pts = []
            for xe, ye, t in zip(Xe, Ye, top):
                zz = np.arange(skirt_to, t + 1e-6, STEP, dtype=np.float32)
                pts.append(np.stack([np.full_like(zz, xe), np.full_like(zz, ye), zz], 1))
            P = np.concatenate(pts)
            scene.add(layer, P, np.tile(nrm, (len(P), 1)), _colour(sc, P[:, 0], P[:, 1], P[:, 2], edge))


def cylinder(scene, layer, cx, cy, r, z0, z1, colour, top_colour=None):
    if getattr(scene, "rotation", 0):
        cx, cy = scene.to_world(cx, cy)
    ang = np.arange(-np.pi / 4 - np.pi / 2, np.pi * 0.75 + 1e-6, STEP / max(r, 0.2))  # camera-facing half
    zz = np.arange(z0, z1 + 1e-6, STEP, dtype=np.float32)
    A, Z = np.meshgrid(ang, zz, indexing="ij")
    A, Z = A.ravel(), Z.ravel()
    X = cx + r * np.cos(A)
    Y = cy + r * np.sin(A)
    n = np.stack([np.cos(A), np.sin(A), np.zeros_like(A)], 1)
    scene.add(layer, np.stack([X, Y, Z], 1), n, _colour(colour, X, Y, Z, "side"))
    X2, Y2 = _grid(cx - r, cx + r, cy - r, cy + r)
    m = (X2 - cx) ** 2 + (Y2 - cy) ** 2 <= r * r
    X2, Y2 = X2[m], Y2[m]
    Z2 = np.full_like(X2, z1)
    scene.add(layer, np.stack([X2, Y2, Z2], 1), np.tile([0, 0, 1.0], (len(X2), 1)),
              _colour(top_colour or colour, X2, Y2, Z2, "top"))


def sphere(scene, layer, cx, cy, cz, r, colour):
    th = np.arange(0, np.pi / 2 + 1e-6, STEP / r)
    ph = np.arange(0, 2 * np.pi, STEP / r)
    T, P = np.meshgrid(th, ph, indexing="ij")
    n = np.stack([np.sin(T) * np.cos(P), np.sin(T) * np.sin(P), np.cos(T)], 1).reshape(-1, 3)
    n = n[n @ np.array([1, 1, 2.0]) > -0.2]
    scene.add(layer, np.array([cx, cy, cz]) + n * r, n, np.broadcast_to(np.asarray(colour, np.float32), (len(n), 3)))


# ---------------------------------------------------------------------------
# Reusable pieces

def pontoon(scene, x0, x1, y0, y1, colour=DECK, z=1.0):
    """Low floating dock: drawn as a ground overlay."""
    box(scene, "ground", x0, x1, y0, y1, -0.3, z, lambda x, y, zz, f: np.where((zz < z - 0.25)[:, None], HULL, colour)
        if f != "top" else np.broadcast_to(np.asarray(colour, np.float32), (len(x), 3)))


def buoy(scene, x, y, colour=BUOY):
    sphere(scene, "building", x, y, 0.2, 0.55, colour)


def runway_buoys(scene, y_centre, x_from, x_to, every=16):
    for x in np.arange(x_from, x_to + 1e-6, every):
        buoy(scene, x, y_centre - 5.5)
        buoy(scene, x, y_centre + 5.5)


def floating_hangar(scene, x0, y0):
    """Floating maintenance hangar filling one tile; the door faces south-east (+y), towards the taxiway."""
    pontoon(scene, x0 + 0.5, x0 + 15.5, y0 + 0.5, y0 + 15.5, colour=DECK)
    wx0, wx1, wy0, wy1, wz = x0 + 1.5, x0 + 14.5, y0 + 1.5, y0 + 13.5, 13.0

    def walls(x, y, z, face):
        c = np.empty((len(x), 3), np.float32)
        c[:] = WHITE
        if face == "y":
            door = (x > x0 + 3.0) & (x < x0 + 13.0) & (z < 11.0)
            c[door] = DOOR
            panel = door & (np.mod(z - 1.0, 2.0) < 0.25)
            c[panel] = DARK
        band = (z > wz - 1.6) & (z < wz - 0.9)
        c[band] = YELLOW
        return c

    box(scene, "building", wx0, wx1, wy0, wy1, 1.0, wz, walls)
    cx = (wx0 + wx1) / 2
    heightfield(scene, "building", wx0 - 0.5, wx1 + 0.5, wy0 - 0.5, wy1 + 0.7,
                lambda x, y: wz + 3.2 * (1 - np.abs(x - cx) / ((wx1 - wx0) / 2 + 0.5)),
                NAVY, skirt_to=wz - 0.4, skirt_colour=lambda x, y, z, f: np.where((z > wz - 0.1)[:, None], WHITE, NAVY))


# ---------------------------------------------------------------------------

def victoria() -> Scene:
    """Victoria Harbour Seaplane Terminal: floating terminal with a wavy living roof (Commuter layout, 5 x 4)."""
    s = Scene(5, 4)

    # Terminal barge spanning (0,0)-(2,0).
    box(s, "ground", 0.8, 43.0, 0.8, 15.4, -0.4, 1.4, HULL, top=DECK_WOOD)
    # Building: silver metal siding with big glazed walls, glulam posts, wavy green roof.
    bx0, bx1, by0, by1, top = 3.0, 30.0, 3.0, 13.0, 10.5

    def facade(x, y, z, face):
        c = np.empty((len(x), 3), np.float32)
        c[:] = SILVER
        along = x if face == "y" else y
        glazed = (z > 2.4) & (z < 9.3)
        c[glazed] = GLASS
        posts = np.mod(along - 0.4, 3.0) < 0.45
        c[glazed & posts] = GLULAM
        c[(z > 9.3) & (z < 9.9)] = GLULAM
        if face == "y":
            door = (x > 13.5) & (x < 16.5) & (z < 8.0)
            c[door] = GLASS_DARK
        return c

    box(s, "building", bx0, bx1, by0, by1, 1.4, top, facade)

    def roof_h(x, y):
        return top + 2.2 + 1.7 * np.sin((x - bx0) * 2 * np.pi / 9.0) * np.clip((x - 1.5) / 3.0, 0.4, 1.0)

    heightfield(s, "building", bx0 - 1.2, bx1 + 1.2, by0 - 1.0, by1 + 1.3, roof_h, LIVING_ROOF,
                skirt_to=None, jitter=0.12)
    # Roof edge (glulam fascia) on the visible edges.
    heightfield(s, "building", bx1 + 1.2, bx1 + 1.25, by0 - 1.0, by1 + 1.3, lambda x, y: roof_h(x, y), GLULAM,
                skirt_to=top + 0.2, skirt_colour=GLULAM)
    heightfield(s, "building", bx0 - 1.2, bx1 + 1.25, by1 + 1.3, by1 + 1.35, roof_h, GLULAM,
                skirt_to=top + 0.2, skirt_colour=GLULAM)
    # Benches and a Canadian flag on the open deck at (2,0).
    for bx in (34.0, 38.0):
        box(s, "building", bx, bx + 2.4, 10.5, 11.3, 1.4, 2.6, GLULAM)
    cylinder(s, "building", 41.0, 3.5, 0.18, 1.4, 24.0, WHITE)

    def flag(x, y, z, face):
        c = np.empty((len(x), 3), np.float32)
        c[:] = RED
        c[(y > 5.0) & (y < 7.0)] = (240, 240, 240)
        c[(y > 5.7) & (y < 6.3) & (z > 20.6) & (z < 22.4)] = RED  # maple leaf, roughly
        return c

    box(s, "building", 40.95, 41.05, 3.6, 8.0, 19.5, 23.5, flag)

    # Gangway along row 0 to the floating hangar at (4,0).
    pontoon(s, 43.0, 65.0, 5.0, 8.0)
    floating_hangar(s, 64.0, 0.0)

    # Docks for the berths at (1,2) (2,2) (3,2): main dock on the south-east edge, finger docks between the berths.
    # Column 0 is kept clear: aircraft leave the runway there.
    pontoon(s, 14.0, 64.6, 44.0, 47.6)
    for fx in (14.0, 30.9, 47.3, 63.0):
        pontoon(s, fx, fx + 1.6, 33.0, 44.0)
    for fx in (14.0, 30.9, 47.3, 63.0):
        cylinder(s, "building", fx + 0.8, 33.4, 0.25, 0.8, 3.0, DARK)  # mooring piles

    # Water runway markers.
    runway_buoys(s, 54.0, 2.0, 78.0)
    return s


def vancouver() -> Scene:
    """Vancouver (Coal Harbour) Seaplane Terminal: central floating pier with a glass terminal and tower (International layout, 7 x 7)."""
    s = Scene(7, 7)

    # Central pier, column 3, rows 2-4.
    box(s, "ground", 48.4, 63.6, 32.0, 80.0, -0.4, 1.5, HULL, top=DECK)

    # Finger docks for the six berths (aircraft at x = 38 and x = 70, y = 38 / 54 / 70, nose towards the pier).
    for fy in (32.0, 45.6, 61.6, 76.6):
        pontoon(s, 40.0, 48.4, fy, fy + 1.5)
        pontoon(s, 63.6, 72.0, fy, fy + 1.5)
        cylinder(s, "building", 40.6, fy + 0.75, 0.25, 0.8, 3.0, DARK)
        cylinder(s, "building", 71.4, fy + 0.75, 0.25, 0.8, 3.0, DARK)

    # Two-storey glass terminal on (3,2)-(3,3).
    bx0, bx1, by0, by1, top = 50.5, 61.5, 34.5, 62.0, 15.0

    def curtain(x, y, z, face):
        c = np.empty((len(x), 3), np.float32)
        c[:] = GLASS
        along = x if face == "y" else y
        c[np.mod(along - bx0, 2.4) < 0.35] = WHITE
        for zf in (1.5, 8.2, 14.2):
            c[(z >= zf) & (z < zf + 0.8)] = WHITE
        if face == "x":
            c[(y > 46.5) & (y < 50.0) & (z < 7.5)] = GLASS_DARK  # entrance
        return c

    box(s, "building", bx0, bx1, by0, by1, 1.5, top, curtain, top=ROOF_GREY)
    # Flat roof with a wide overhang, white fascia.
    box(s, "building", bx0 - 1.3, bx1 + 1.3, by0 - 1.3, by1 + 1.3, top, top + 1.4,
        lambda x, y, z, f: np.broadcast_to(np.asarray(WHITE, np.float32), (len(x), 3)), top=ROOF_GREY)
    box(s, "building", 53.0, 57.0, 40.0, 44.0, top + 1.4, top + 3.0, ROOF_GREY)  # rooftop plant
    box(s, "building", 54.0, 59.0, 52.0, 55.0, top + 1.4, top + 2.6, ROOF_GREY)
    # Harbour Air sign band on the south-west facade.
    box(s, "building", bx1, bx1 + 0.15, 40.0, 56.0, 10.0, 12.0,
        lambda x, y, z, f: np.where(((np.mod(y - 40.0, 2.0) < 1.2) & (z > 10.5) & (z < 11.5))[:, None], YELLOW, NAVY))

    # Control tower on (3,4).
    box(s, "building", 54.0, 58.0, 69.0, 73.0, 1.5, 24.0, CONCRETE)

    def cab(x, y, z, face):
        c = np.empty((len(x), 3), np.float32)
        c[:] = GLASS_DARK
        c[z < 25.0] = CONCRETE
        c[z > 28.6] = WHITE
        return c

    box(s, "building", 52.5, 59.5, 67.5, 74.5, 24.0, 29.2, cab, top=DARK)
    box(s, "building", 52.0, 60.0, 67.0, 75.0, 29.2, 30.0, WHITE, top=DARK)
    cylinder(s, "building", 56.0, 71.0, 0.15, 30.0, 36.0, DARK)
    # Covered walkway from the terminal to the tower.
    box(s, "building", 53.0, 59.0, 62.0, 67.5, 1.5, 6.0, lambda x, y, z, f: np.where((z > 5.0)[:, None], WHITE, GLASS),
        top=ROOF_GREY)

    # Fuel dock on (0,2).
    pontoon(s, 2.0, 13.0, 36.0, 43.0)
    box(s, "building", 3.0, 7.0, 37.0, 41.0, 1.0, 6.0, WHITE, top=NAVY)
    box(s, "building", 9.0, 10.0, 39.0, 40.0, 1.0, 4.0, YELLOW)  # fuel pump

    floating_hangar(s, 0.0, 48.0)   # hangar 1 at (0,3)
    floating_hangar(s, 96.0, 16.0)  # hangar 2 at (6,1)

    runway_buoys(s, 6.0, 2.0, 110.0)
    runway_buoys(s, 104.0, 2.0, 110.0)
    return s


SCENES = {"victoria": victoria, "vancouver": vancouver}


PLANK = (156, 116, 74)
PLANK_GAP = (110, 80, 50)
PILING = (104, 80, 56)


def wooden_dock(rotation=0) -> Scene:
    """Small floating wooden seaplane dock, 1 x 2 tiles (TGTFTD seaplane dock state machine).

    One berth at (10, 16), aircraft facing north-west with its wings over the dock; the dock runs along the
    north-east edge (low x). Seaplanes land and take off on the water lane at x = 24, outside the footprint.
    """
    s = Scene(1, 2, rotation)
    x0, x1, y0, y1 = 0.8, 5.4, 1.0, 31.0

    def planks(x, y, z, face):
        c = np.empty((len(x), 3), np.float32)
        c[:] = PLANK
        if face == "top":
            c[np.mod(y - y0, 1.1) < 0.18] = PLANK_GAP  # planks laid across the dock
        else:
            c[z < 0.55] = HULL                          # floats under the deck
            c[z >= 0.55] = PLANK_GAP
        return c

    box(s, "ground", x0, x1, y0, y1, -0.3, 1.2, planks)
    # Pilings at the corners and halfway, mooring cleats on the berth side.
    for py in (y0 + 0.4, 16.0, y1 - 0.4):
        for px in (x0 + 0.3, x1 - 0.3):
            cylinder(s, "building", px, py, 0.32, 0.6, 4.2, PILING, top_colour=PLANK_GAP)
    for cy in (11.0, 21.0):
        box(s, "building", x1 - 0.7, x1 - 0.3, cy - 0.5, cy + 0.5, 1.2, 1.7, DARK)
    return s


SCENES["dock"] = wooden_dock
