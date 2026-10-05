"""
Voxel models of the Harbour Air seaplanes, in metres.

Local frame: f = forward (nose positive), r = right, u = up, u = 0 is the waterline
(bottom of the floats). The origin is roughly the centre of the aircraft.

Dimensions follow Harbour Air's fleet page (length, wingspan); the rest is
estimated from drawings and photos.
"""

import numpy as np

from pointcloud import VoxelModel, loft, wing, fin, cylinder, cone_x, box

# Harbour Air colours (RGB, optional shading gain).
WHITE = (238, 238, 238)
FLOAT_WHITE = (226, 228, 230)
NAVY = (18, 40, 112)
YELLOW = (250, 206, 24)
RED = (206, 36, 36)
GLASS = (46, 66, 92, 0.95)
GREY = (150, 152, 156)
DARK = (44, 44, 48)
METAL = (120, 124, 130)

M_WHITE, M_NAVY, M_YELLOW, M_RED, M_GLASS, M_GREY, M_DARK, M_FLOAT, M_METAL, M_FIN = range(1, 11)

# "HA" logo bitmap for the fin (row 0 = top).
HA_LOGO = [
    "#..#...##..",
    "#..#..#..#.",
    "####..####.",
    "#..#..#..#.",
    "#..#..#..#.",
]


def _materials(m: VoxelModel):
    m.material(M_WHITE, WHITE)
    m.material(M_NAVY, NAVY)
    m.material(M_YELLOW, YELLOW)
    m.material(M_RED, RED)
    m.material(M_GLASS, GLASS)
    m.material(M_GREY, GREY)
    m.material(M_DARK, DARK)
    m.material(M_FLOAT, FLOAT_WHITE)
    m.material(M_METAL, METAL)
    m.material(M_FIN, NAVY)


def _livery(m: VoxelModel, *, swoosh_front, swoosh_back, fus_bottom, fus_top, windshield, windows, window_band,
            fin_logo, float_bands, cowl_front=None):
    """
    Paint the fuselage (white, M_WHITE) with the Harbour Air scheme:
      * navy rear fuselage behind a line rising from swoosh_front (at the belly) to swoosh_back (at the roof),
        with a yellow pinstripe along it,
      * glazing, navy fin with a yellow "HA" logo, red bands on the floats.
    windshield: (f0, f1, depth below top) ; windows: list of (f0, f1) ; window_band: (u0, u1)
    fin_logo: (f_front, f_back, u_bottom, u_top) box on the fin for the logo.
    """
    def painter(F, R, U, mat):
        mat = mat.copy()
        body = mat == M_WHITE
        h = np.clip((U - fus_bottom) / (fus_top - fus_bottom), 0, 1)
        fb = swoosh_front + (swoosh_back - swoosh_front) * h ** 0.8
        navy = body & (F < fb)
        stripe = body & (F >= fb) & (F < fb + 0.22)
        mat[navy] = M_NAVY
        mat[stripe] = M_YELLOW

        side = np.abs(R) > 0.25
        u0, u1 = window_band
        for f0, f1 in windows:
            mat[body & ~navy & side & (F >= f0) & (F <= f1) & (U >= u0) & (U <= u1)] = M_GLASS
        wf0, wf1, depth = windshield
        mat[body & (F >= wf0) & (F <= wf1) & (U >= fus_top - depth - (F - wf0) / (wf1 - wf0) * 0.35)] = M_GLASS
        if cowl_front is not None:
            mat[body & (F >= cowl_front)] = M_DARK

        # Fin logo.
        lf0, lf1, lu0, lu1 = fin_logo
        on_fin = (mat == M_FIN) & (F <= lf0) & (F >= lf1) & (U >= lu0) & (U <= lu1)
        if on_fin.any():
            rows, cols = len(HA_LOGO), len(HA_LOGO[0])
            ui = ((lu1 - U[on_fin]) / (lu1 - lu0) * rows).astype(int).clip(0, rows - 1)
            # Italic slant: letters lean forward towards the top.
            slant = (U[on_fin] - lu0) / (lu1 - lu0) * 0.12 * (lf0 - lf1)
            fi = ((lf0 - F[on_fin] + slant) / (lf0 - lf1) * cols).astype(int).clip(0, cols - 1)
            lit = np.array([[c == "#" for c in row] for row in HA_LOGO])[ui, fi]
            idx = np.nonzero(on_fin)[0][lit]
            mat[idx] = M_YELLOW

        fl = mat == M_FLOAT
        for f0, f1 in float_bands:
            mat[fl & (F >= f0) & (F <= f1) & (U > 0.12)] = M_RED
        return mat
    m.paint(painter)


def _floats(m, r_off, keys, struts, strut_mat=M_GREY, strut_radius=0.065):
    for side in (-1, 1):
        bbox, inside = loft(keys, power=2.2, axis_r=side * r_off)
        m.add(bbox, inside, M_FLOAT)
        for (f0, u0, f1, r1, u1) in struts:
            bbox, inside = cylinder((f0, side * r_off, u0), (f1, side * r1, u1), strut_radius)
            m.add(bbox, inside, strut_mat)
        # Spreader bar between the floats.
    return m


def beaver() -> VoxelModel:
    """de Havilland Canada DHC-2 Beaver: 10.0 m long, 14.67 m span."""
    m = VoxelModel((-5.4, 5.2), (-7.5, 7.5), (-0.05, 4.7))
    _materials(m)
    fus = [(-5.15, 0.05, 2.98, 3.12), (-3.6, 0.30, 2.70, 3.30), (-1.6, 0.58, 2.05, 3.42), (0.0, 0.64, 1.95, 3.46),
           (1.55, 0.64, 1.95, 3.46), (2.65, 0.62, 2.00, 3.02), (4.25, 0.62, 2.05, 3.00), (4.6, 0.46, 2.20, 2.86)]
    bbox, inside = loft(fus, power=2.6)
    m.add(bbox, inside, M_WHITE)
    m.add(*cone_x(4.55, 4.95, 0.0, 2.53, 0.22, 0.04), M_DARK)
    m.add(*wing(1.60, 1.60, 7.33, 3.40, 0.26), M_NAVY)
    for s in (-1, 1):
        m.add(*cylinder((0.85, s * 0.55, 2.10), (0.85, s * 2.9, 3.40), 0.055), M_GREY)
    m.add(*wing(-4.15, 0.95, 2.50, 3.02, 0.12, taper=0.8), M_NAVY)
    m.add(*fin([(-3.55, 3.25), (-4.55, 4.40), (-4.95, 4.48), (-5.25, 4.25), (-5.30, 3.00), (-4.2, 3.0)], 0.13), M_FIN)
    _floats(m, 1.35, [(-3.4, 0.10, 0.30, 0.66), (-1.0, 0.38, 0.05, 0.80), (0.3, 0.40, 0.00, 0.80), (2.6, 0.40, 0.05, 0.80),
                      (3.7, 0.28, 0.35, 0.78), (4.05, 0.07, 0.62, 0.72)],
            [(1.75, 0.78, 1.65, 0.45, 2.05), (-0.55, 0.78, -0.45, 0.45, 2.00)])
    _livery(m, swoosh_front=-0.9, swoosh_back=-3.35, fus_bottom=1.95, fus_top=3.46,
            windshield=(1.55, 2.55, 0.10), windows=[(0.55, 1.35), (-0.55, 0.30), (-1.55, -0.80)], window_band=(2.80, 3.22),
            fin_logo=(-4.15, -5.15, 3.55, 4.30), float_bands=[(2.80, 2.90), (3.08, 3.18)], cowl_front=4.48)
    return m


def turbo_otter() -> VoxelModel:
    """de Havilland Canada DHC-3T Turbo Otter: 13.78 m long, 17.44 m span."""
    m = VoxelModel((-7.1, 7.2), (-8.9, 8.9), (-0.05, 5.5))
    _materials(m)
    fus = [(-6.9, 0.06, 3.35, 3.52), (-4.6, 0.38, 2.85, 3.78), (-2.1, 0.78, 2.15, 3.96), (0.0, 0.80, 2.05, 3.98),
           (2.25, 0.80, 2.05, 3.98), (3.35, 0.70, 2.15, 3.42), (5.6, 0.48, 2.35, 3.24), (6.6, 0.30, 2.55, 3.10)]
    m.add(*loft(fus, power=2.6), M_WHITE)
    m.add(*cone_x(6.55, 7.0, 0.0, 2.83, 0.24, 0.04), M_DARK)
    m.add(*cylinder((5.0, 0.42, 2.95), (5.0, 0.62, 2.95), 0.11), M_METAL)  # exhaust stub
    m.add(*wing(2.25, 1.95, 8.72, 3.92, 0.30), M_NAVY)
    for s in (-1, 1):
        m.add(*cylinder((1.45, s * 0.72, 2.25), (1.45, s * 3.4, 3.92), 0.06), M_GREY)
    m.add(*wing(-5.45, 1.20, 3.20, 3.56, 0.13, taper=0.75), M_NAVY)
    m.add(*fin([(-4.4, 3.72), (-5.85, 5.20), (-6.40, 5.32), (-6.85, 5.05), (-6.95, 3.40), (-5.6, 3.5)], 0.14), M_FIN)
    _floats(m, 1.62, [(-4.3, 0.12, 0.32, 0.74), (-1.5, 0.45, 0.05, 0.90), (0.2, 0.47, 0.00, 0.90), (3.7, 0.47, 0.05, 0.90),
                      (5.1, 0.32, 0.40, 0.88), (5.5, 0.08, 0.70, 0.82)],
            [(3.35, 0.88, 3.30, 0.55, 2.20), (0.25, 0.88, 0.30, 0.55, 2.10)])
    _livery(m, swoosh_front=-1.6, swoosh_back=-4.5, fus_bottom=2.05, fus_top=3.98,
            windshield=(2.30, 3.30, 0.12),
            windows=[(1.45, 2.05), (0.55, 1.15), (-0.35, 0.25), (-1.25, -0.65), (-2.15, -1.55)], window_band=(3.18, 3.68),
            fin_logo=(-5.05, -6.75, 4.20, 5.15), float_bands=[(4.05, 4.15), (4.35, 4.45)])
    return m


def twin_otter() -> VoxelModel:
    """de Havilland Canada DHC-6 Twin Otter: 15.85 m long, 19.81 m span."""
    m = VoxelModel((-8.1, 8.1), (-10.0, 10.0), (-0.05, 6.3))
    _materials(m)
    fus = [(-7.9, 0.10, 3.55, 3.85), (-5.0, 0.55, 2.85, 4.00), (-3.0, 0.80, 2.30, 4.05), (2.0, 0.80, 2.30, 4.05),
           (3.1, 0.78, 2.32, 4.00), (4.05, 0.70, 2.40, 3.55), (6.0, 0.45, 2.55, 3.25), (7.55, 0.22, 2.75, 3.05),
           (7.92, 0.05, 2.88, 2.95)]
    m.add(*loft(fus, power=3.2), M_WHITE)
    m.add(*wing(3.0, 1.98, 9.9, 4.0, 0.32), M_NAVY)
    for s in (-1, 1):
        nac = [(-1.2, 0.05, 3.85, 4.05), (0.0, 0.40, 3.55, 4.35), (3.6, 0.42, 3.50, 4.38), (4.6, 0.30, 3.62, 4.25)]
        m.add(*loft(nac, power=2.2, axis_r=s * 2.65), M_NAVY)
        m.add(*cone_x(4.55, 4.95, s * 2.65, 3.93, 0.20, 0.04), M_DARK)
        m.add(*cylinder((1.2, s * 0.75, 2.45), (1.6, s * 4.3, 4.0), 0.06), M_GREY)
    m.add(*wing(-6.55, 1.30, 3.20, 3.88, 0.14), M_NAVY)
    m.add(*fin([(-4.9, 3.95), (-6.85, 6.00), (-7.65, 6.05), (-7.95, 5.80), (-7.95, 3.80), (-6.0, 3.9)], 0.15), M_FIN)
    _floats(m, 2.05, [(-4.6, 0.13, 0.35, 0.80), (-1.6, 0.50, 0.05, 0.98), (0.4, 0.52, 0.00, 0.98), (4.6, 0.52, 0.05, 0.98),
                      (6.0, 0.36, 0.45, 0.96), (6.5, 0.08, 0.78, 0.90)],
            [(3.6, 0.96, 3.5, 0.60, 2.40), (0.5, 0.96, 0.5, 0.60, 2.35), (0.5, 0.96, 1.2, 2.65, 3.55)])
    _livery(m, swoosh_front=-2.4, swoosh_back=-5.1, fus_bottom=2.30, fus_top=4.05,
            windshield=(3.05, 4.10, 0.12),
            windows=[(1.95, 2.45), (1.25, 1.65), (0.55, 0.95), (-0.15, 0.25), (-0.85, -0.45), (-1.55, -1.15), (-2.25, -1.85)],
            window_band=(3.30, 3.70),
            fin_logo=(-5.75, -7.75, 4.75, 5.90), float_bands=[(1.6, 1.7), (-0.5, -0.4)])
    return m


def grand_caravan() -> VoxelModel:
    """Cessna 208B Grand Caravan EX: 12.67 m long, 15.88 m span."""
    m = VoxelModel((-6.6, 6.6), (-8.1, 8.1), (-0.05, 5.6))
    _materials(m)
    fus = [(-6.35, 0.08, 3.28, 3.45), (-4.0, 0.45, 2.75, 3.70), (-2.0, 0.78, 2.15, 3.85), (1.5, 0.80, 2.10, 3.88),
           (2.6, 0.75, 2.15, 3.52), (4.8, 0.50, 2.35, 3.25), (5.9, 0.32, 2.52, 3.06)]
    m.add(*loft(fus, power=2.7), M_WHITE)
    m.add(*cone_x(5.85, 6.35, 0.0, 2.80, 0.24, 0.04), M_DARK)
    m.add(*wing(1.65, 1.65, 7.94, 3.86, 0.28, taper=0.75), M_NAVY)
    for s in (-1, 1):
        m.add(*cylinder((0.45, s * 0.75, 2.25), (0.65, s * 3.6, 3.86), 0.085), M_NAVY)
    m.add(*wing(-5.25, 1.10, 3.10, 3.38, 0.13, taper=0.75), M_NAVY)
    m.add(*fin([(-3.8, 3.75), (-5.55, 5.25), (-6.15, 5.32), (-6.40, 5.10), (-6.40, 3.30), (-5.2, 3.4)], 0.14), M_FIN)
    _floats(m, 1.65, [(-4.5, 0.12, 0.34, 0.76), (-1.6, 0.46, 0.05, 0.92), (0.3, 0.48, 0.00, 0.92), (3.9, 0.48, 0.05, 0.92),
                      (4.9, 0.33, 0.42, 0.90), (5.25, 0.08, 0.72, 0.84)],
            [(3.0, 0.90, 2.7, 0.55, 2.25), (-0.1, 0.90, -0.2, 0.55, 2.15)], strut_mat=M_NAVY, strut_radius=0.08)
    _livery(m, swoosh_front=-1.2, swoosh_back=-4.4, fus_bottom=2.10, fus_top=3.88,
            windshield=(1.6, 2.6, 0.12),
            windows=[(0.95, 1.45), (0.15, 0.55), (-0.55, -0.15), (-1.25, -0.85), (-1.95, -1.55)], window_band=(3.15, 3.55),
            fin_logo=(-4.75, -6.25, 4.15, 5.10), float_bands=[(3.2, 3.3), (3.45, 3.55)])
    return m


MODELS = {
    "beaver": beaver,
    "turbo_otter": turbo_otter,
    "twin_otter": twin_otter,
    "grand_caravan": grand_caravan,
}


# ---------------------------------------------------------------------------
# Helijet Sikorsky S-76: white nose and cockpit, metallic blue body behind a raked
# split line with a thin red stripe, white pinstripes on the engine cowling.

HJ_BLUE = (34, 96, 146)
HJ_RED = (204, 40, 40)
ROTOR_GREY = (58, 60, 64)
M_HJ_BLUE, M_HJ_RED, M_ROTOR, M_TAIL_ROTOR = 11, 12, 13, 14


def s76() -> VoxelModel:
    """Sikorsky S-76 in Helijet colours: fuselage 13.2 m, 4-blade main rotor 13.41 m (rotor drawn separately)."""
    m = VoxelModel((-9.0, 5.3), (-1.3, 1.3), (-0.05, 4.0))
    _materials(m)
    m.material(M_HJ_BLUE, HJ_BLUE)
    m.material(M_HJ_RED, HJ_RED)
    m.material(M_ROTOR, ROTOR_GREY)
    m.material(M_TAIL_ROTOR, (128, 130, 136))
    fus = [(5.0, 0.05, 1.15, 1.35), (4.6, 0.55, 0.80, 1.85), (3.6, 0.80, 0.62, 2.25), (2.4, 0.95, 0.58, 2.45),
           (0.0, 1.00, 0.58, 2.50), (-1.6, 0.95, 0.62, 2.45), (-2.6, 0.70, 1.10, 2.35), (-4.0, 0.38, 1.50, 2.15),
           (-7.6, 0.18, 1.70, 2.00), (-8.0, 0.12, 1.72, 2.02)]
    m.add(*loft(sorted(fus), power=2.4), M_WHITE)
    cowl = [(1.8, 0.10, 2.30, 2.45), (1.2, 0.68, 2.25, 2.95), (-1.6, 0.70, 2.25, 3.00), (-2.6, 0.30, 2.20, 2.65)]
    m.add(*loft(sorted(cowl), power=2.6), M_WHITE)
    m.add(*cylinder((0.0, 0.0, 2.9), (0.0, 0.0, 3.35), 0.16), M_DARK)  # rotor mast
    m.add(*fin([(-6.9, 1.95), (-7.9, 3.55), (-8.55, 3.65), (-8.45, 1.85)], 0.16), M_FIN)
    m.add(*wing(-6.55, 0.75, 1.65, 1.82, 0.10), M_HJ_BLUE)
    # Tail rotor: thin spinning disc on the left of the fin.
    m.add(((-9.0, -7.5), (-0.30, -0.16), (2.2, 3.9)),
          lambda F, R, U: (np.abs(R + 0.23) <= 0.04) & ((F + 8.25) ** 2 + (U - 3.05) ** 2 <= 0.85 ** 2), M_TAIL_ROTOR)
    for f, r in ((3.8, 0.0), (-0.8, -1.05), (-0.8, 1.05)):
        m.add(*cylinder((f, r - 0.09, 0.22), (f, r + 0.09, 0.22), 0.22), M_DARK)
        m.add(*cylinder((f, r * 0.8, 0.22), (f, r * 0.8, 0.75), 0.05), M_GREY)

    def painter(F, R, U, mat):
        mat = mat.copy()
        body = mat == M_WHITE
        fb = 1.0 + np.clip((U - 0.6) / 1.9, 0, 1) * 1.6  # raked split behind the cockpit door
        blue = body & (F < fb)
        mat[blue] = M_HJ_BLUE
        mat[body & (F < fb) & (F >= fb - 0.16)] = M_HJ_RED
        # White pinstripes on the blue engine cowling.
        mat[blue & (U > 2.5) & (np.mod(U - 2.5, 0.16) < 0.045)] = M_WHITE
        mat[mat == M_FIN] = M_HJ_BLUE
        side = np.abs(R) > 0.3
        mat[body & ~blue & (F >= 3.1) & (F <= 4.55) & (U >= 1.45 + (F - 3.1) * 0.12)] = M_GLASS  # windshield
        for f0, f1 in ((1.7, 2.6), (0.6, 1.4), (-0.6, 0.3)):
            mat[(mat != M_GLASS) & (body | blue) & side & (F >= f0) & (F <= f1) & (U >= 1.55) & (U <= 2.05)] = M_GLASS
        return mat
    m.paint(painter)
    return m


def s76_rotor(phase_deg: float, chord: float) -> VoxelModel:
    """Main rotor, 4 blades of 6.7 m at the given phase; drawn as a separate sprite on the rotor vehicle."""
    m = VoxelModel((-6.9, 6.9), (-6.9, 6.9), (3.2, 3.6))
    m.material(M_ROTOR, ROTOR_GREY)
    m.material(M_RED, HJ_RED)
    m.material(M_WHITE, WHITE)
    m.add(*cylinder((0, 0, 3.35), (0, 0, 3.5), 0.3), M_ROTOR)
    for k in range(4):
        a = np.radians(phase_deg + 90 * k)
        m.add(*cylinder((0, 0, 3.42), (6.7 * np.cos(a), 6.7 * np.sin(a), 3.42), chord / 2), M_ROTOR)

    def tips(F, R, U, mat):
        mat = mat.copy()
        d = np.hypot(F, R)
        mat[(d > 6.0) & (d <= 6.35)] = M_RED
        mat[(d > 6.35)] = M_WHITE
        return mat
    m.paint(tips)
    return m


MODELS["s76"] = s76
