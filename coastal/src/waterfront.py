"""
Waterfront objects for Victoria and Vancouver, built with the terminals
toolkit (terminals/src/buildings.py). Photos on Commons: Fisherman's Wharf
(Victoria, 2024), Granville Island Public Market, Ocean Concrete 'Giants',
Aquabus dock, Fisgard Lighthouse.

Water objects are modelled with z = 0 at the water surface.
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "common"))
sys.path.insert(0, os.path.join(_REPO, "terminals", "src"))
from render import decal_mask, decal_size  # noqa: E402
from buildings import (Building, _paving, _stain, _people, _person, _bench, _planter,  # noqa: E402
                       _lamp, _car, _flagpole, _fir, _rock, CAR_COLOURS)

HOUSE_COLOURS = ["fhpink", "fhteal", "fhyellow", "fhnavy", "fhpurple", "fhgreen", "fhred"]


def _float(b, x0, x1, y0, y1, h=0.7):
    """Timber float deck sitting on the water, plank lines and dark edge."""
    import buildings as _b
    b.sol(lambda X, Y, Z: [((X > x0) & (X < x1) & (Y > y0) & (Y < y1) & (Z <= h), "floatwood"),
                           ((X > x0) & (X < x1) & (Y > y0) & (Y < y1) & (Z <= h) & (Z > h - 0.08) &
                            (np.mod(X, 0.7) < 0.07) & _b.DETAIL, "piling"),
                           ((X > x0) & (X < x1) & (Y > y0) & (Y < y1) & (Z <= 0.3), "piling")],
          None, x0, x1)


def _rail(b, x0, x1, y0, y1, z, mat="white", h=1.0, sides="nsew"):
    def fn(X, Y, Z):
        inb = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1) & (Z > z) & (Z <= z + h)
        edge = np.zeros(X.shape, bool)
        if "n" in sides:
            edge |= np.abs(Y - y0) < 0.07
        if "s" in sides:
            edge |= np.abs(Y - y1) < 0.07
        if "w" in sides:
            edge |= np.abs(X - x0) < 0.07
        if "e" in sides:
            edge |= np.abs(X - x1) < 0.07
        return inb & edge & ((Z > z + h - 0.15) | (np.mod(X + Y, 0.6) < 0.1))
    b.sol(fn, mat, x0 - 0.1, x1 + 0.1)


def _house(b, x0, x1, y0, y1, z0, z1, wall, roof="gable", roof_mat="grey", trim="white", along_x=True,
           pitch=0.75):
    """Clapboard house: siding lines, white-trimmed windows and door, roof
    (gable along the long axis, or a shed/mono-pitch)."""
    def walls(X, Y, Z):
        inside = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1) & (Z > z0) & (Z <= z1)
        dx, dy = np.minimum(X - x0, x1 - X), np.minimum(Y - y0, y1 - Y)
        face = inside & ((dx < 0.12) | (dy < 0.12))
        along = np.where(dy < 0.12, X, Y)
        storey = np.mod(Z - z0, 2.6)
        win = face & (storey > 0.9) & (storey < 2.0) & (np.abs(np.mod(along, 1.9) - 0.95) < 0.42)
        frame = face & (storey > 0.8) & (storey < 2.1) & (np.abs(np.mod(along, 1.9) - 0.95) < 0.52) & ~win
        corner = inside & (dx < 0.14) & (dy < 0.14)
        return [(inside, wall), (frame, trim), (win, "window"), (corner, trim)]
    b.sol(walls, None, x0, x1)
    if roof == "gable":
        def gable(X, Y, Z):
            if along_x:
                c, half, a = (y0 + y1) / 2, (y1 - y0) / 2 + 0.3, Y
                inr = (X > x0 - 0.3) & (X < x1 + 0.3)
            else:
                c, half, a = (x0 + x1) / 2, (x1 - x0) / 2 + 0.3, X
                inr = (Y > y0 - 0.3) & (Y < y1 + 0.3)
            zr = z1 + (half - np.abs(a - c)) * pitch
            body = inr & (np.abs(a - c) < half) & (Z > z1) & (Z <= zr)
            shell = body & (Z > zr - 0.3)
            if along_x:
                fill = (X >= x0) & (X <= x1)
            else:
                fill = (Y >= y0) & (Y <= y1)
            return [(body & fill, wall), (shell, roof_mat)]
        b.sol(gable, None, x0 - 0.3, x1 + 0.3)
    elif roof == "none":
        pass
    else:                                          # shed roof rising to +y
        b.sol(lambda X, Y, Z: (X > x0 - 0.3) & (X < x1 + 0.3) & (Y > y0 - 0.3) & (Y < y1 + 0.3) &
              (Z > z1 + 0.25 * (Y - y0)) & (Z <= z1 + 0.25 * (Y - y0) + 0.3), roof_mat, x0 - 0.3, x1 + 0.3)


WALK = (6.5, 9.5)          # floating walkway band across the tile; float homes and dock pieces share it


def _kayak(b, x, y, z, along_x, mat):
    lx, ly = (1.9, 0.32) if along_x else (0.32, 1.9)
    b.ellipsoid(x - b.cx, y - b.cy, z + 0.25, lx, ly, 0.22, mat)


def _gazebo(b, x, y, z, mat="dark"):
    for dx in (-1.1, 1.1):
        for dy in (-1.1, 1.1):
            b.bx(x + dx - 0.07, x + dx + 0.07, y + dy - 0.07, y + dy + 0.07, z, z + 2.0, "steel")
    b.sol(lambda X, Y, Z: (np.maximum(np.abs(X - x), np.abs(Y - y)) < 1.5) &
          (Z > z + 2.0) & (Z <= z + 2.0 + 0.9 * (1 - np.maximum(np.abs(X - x), np.abs(Y - y)) / 1.5)),
          mat, x - 1.6, x + 1.6)


def _small_home(b, x0, x1, side, style, wall, trim, roof_mat, accent, rng):
    """One float home on its own float, tight against the walkway. side = -1
    (north of the walkway) or +1 (south). Styles, after Fisherman's Wharf
    and Fraser River float homes: 'arch' (arched shingle roof, loft),
    'flatdeck' (two storeys, upper floor overhanging on posts, rooftop deck
    with black railing and ladder), 'gable' (two storeys, skylights),
    'shed' (storey and a half, mono-pitch with skylights), 'cottage' (one
    storey, big deck with umbrella and loungers)."""
    w0, w1 = WALK
    if side < 0:
        fy0, fy1 = 0.4, w0                      # float runs from the tile edge to the walkway
        hy0, hy1 = 1.0, w0 - 0.9                # house leaves a strip of deck by the walkway
    else:
        fy0, fy1 = w1, 15.6
        hy0, hy1 = w1 + 0.9, 15.0
    _float(b, x0, x1, fy0, fy1)
    hx0, hx1 = x0 + 0.5, x1 - 2.2               # deck at one end
    z = 0.7
    if style == "cottage":
        hx1 = x0 + (x1 - x0) * 0.55
    if style == "arch":
        _house(b, hx0, hx1, hy0, hy1, z, z + 1.6, wall, roof="none", trim=trim)
        c, half = (hy0 + hy1) / 2, (hy1 - hy0) / 2 + 0.25

        def arch(X, Y, Z):
            q = np.clip(np.abs(Y - c) / half, 0, 1)
            zr = z + 1.6 + 4.2 * np.sqrt(np.clip(1 - q ** 1.6, 0, 1))      # rounded gambrel
            inr = (X > hx0 - 0.25) & (X < hx1 + 0.25) & (np.abs(Y - c) < half) & (Z > z + 1.4) & (Z <= zr)
            gable_end = inr & ((X < hx0 + 0.12) | (X > hx1 - 0.12)) & (Z < zr - 0.35)
            win = gable_end & (np.abs(Y - c) < 0.6) & (Z > z + 2.6) & (Z < z + 4.0)
            return [(inr, roof_mat), (gable_end, wall), (win, "window")]
        b.sol(arch, None, hx0 - 0.3, hx1 + 0.3)
    elif style == "flatdeck":
        z1 = z + 2.6
        _house(b, hx0, hx1, hy0, hy1, z, z1, wall, roof="none", trim=trim)
        oy = -0.7 * side                           # upper floor cantilevers towards the walkway
        _house(b, hx0, hx1 + 1.2, min(hy0, hy0 - oy), max(hy1, hy1 - oy), z1, z1 + 2.6, wall,
               roof="none", trim=trim)
        b.bx(hx0 - 0.1, hx1 + 1.3, min(hy0, hy0 - oy) - 0.1, max(hy1, hy1 - oy) + 0.1,
             z1 + 2.6, z1 + 2.85, trim)
        _rail(b, hx0, hx1 + 1.2, min(hy0, hy0 - oy), max(hy1, hy1 - oy), z1 + 2.85, "acblack", h=1.1)
        for px in (hx1 + 1.0,):
            for py in (min(hy0, hy0 - oy) + 0.2, max(hy1, hy1 - oy) - 0.2):
                b.bx(px - 0.1, px + 0.1, py - 0.1, py + 0.1, z, z1, "timber")
        b.sol(lambda X, Y, Z: (np.abs(X - (hx1 + 0.6)) < 0.08) & (np.abs(Y - (hy0 + hy1) / 2) < 0.5) &
              (Z > z1) & (Z <= z1 + 3.9) & ((np.mod(Z, 0.45) < 0.1) | (np.abs(np.abs(Y - (hy0 + hy1) / 2) - 0.45) < 0.06)),
              "acblack", hx1, hx1 + 1.2)                              # ladder to the roof deck
        b.bx(hx0 + 1.0, hx0 + 2.0, hy0 + 0.6, hy0 + 1.6, z1 + 2.85, z1 + 3.4, "fhgreen")   # planter
    elif style in ("gable", "shed"):
        z1 = z + (5.2 if style == "gable" else 3.4)
        _house(b, hx0, hx1, hy0, hy1, z, z1, wall, roof=style, roof_mat=roof_mat, trim=trim,
               along_x=True, pitch=0.9)
        for k in range(2):                           # skylights
            sx = hx0 + (hx1 - hx0) * (0.3 + 0.4 * k)
            b.bx(sx - 0.35, sx + 0.35, (hy0 + hy1) / 2 - 1.0, (hy0 + hy1) / 2 - 0.3,
                 z1 + 0.8, z1 + 1.15, "glass")
        if style == "gable" and rng.rand() < 0.6:     # ladder up the roof
            b.bx(hx0 + 1.0, hx0 + 1.15, hy0, hy1, z1 + 0.2, z1 + 0.5, "steel")
    else:                                            # cottage
        _house(b, hx0, hx1, hy0, hy1, z, z + 2.8, wall, roof="gable", roof_mat=roof_mat, trim=trim,
               along_x=False, pitch=0.9)
        b.bx(hx1 + 0.6, x1 - 0.6, hy0 + 0.5, hy0 + 1.4, z, z + 0.5, "white")       # loungers
        b.bx(hx1 + 0.6, x1 - 0.6, hy1 - 1.4, hy1 - 0.5, z, z + 0.5, "white")
        ux, uy = (hx1 + x1) / 2, (hy0 + hy1) / 2
        b.bx(ux - 0.05, ux + 0.05, uy - 0.05, uy + 0.05, z, z + 2.6, "steel")
        b.sol(lambda X, Y, Z: ((X - ux) ** 2 + (Y - uy) ** 2 < 1.6 ** 2) & (Z > z + 2.3) &
              (Z <= z + 2.7 - 0.25 * np.sqrt((X - ux) ** 2 + (Y - uy) ** 2)), accent, ux - 1.7, ux + 1.7)
    # door onto the walkway side, deck clutter at the open end
    dy = hy1 if side < 0 else hy0
    b.bx((hx0 + hx1) / 2 - 0.5, (hx0 + hx1) / 2 + 0.5, dy - 0.06, dy + 0.06, z, z + 2.1, accent)
    if style != "cottage":
        if rng.rand() < 0.6:
            _kayak(b, (hx1 + x1) / 2 + 0.2, (hy0 + hy1) / 2, z, False, ["fhyellow", "awngreen", "flagred"][rng.randint(3)])
        else:
            _gazebo(b, (hx1 + x1) / 2 + 0.1, (hy0 + hy1) / 2, z)
    _rail(b, x0 + 0.1, x1 - 0.1, fy0 + 0.1, fy1 - 0.1, z, trim if trim != "acblack" else "timber",
          h=0.9, sides="n" if side < 0 else "s")


# (north home, south home): (x0, x1, style, wall, trim, roof, accent)
FLOAT_HOME_LAYOUTS = [
    [(0.4, 8.2, "flatdeck", "lime", "acblack", "dark", "fhyellow"),
     (8.4, 15.6, "arch", "fhred", "white", "dark", "fhteal")],
    [(0.4, 8.0, "gable", "fhteal", "white", "grey", "fhyellow"),
     (8.2, 15.6, "cottage", "fhyellow", "white", "fhteal", "flagred")],
    [(0.4, 7.8, "shed", "blue", "white", "grey", "flagred"),
     (8.0, 15.6, "flatdeck", "fhpink", "white", "grey", "fhteal")],
    [(0.4, 8.0, "arch", "fhgreen", "white", "dark", "fhyellow"),
     (8.2, 15.6, "gable", "fhpurple", "white", "fhred", "white")],
]


def float_home(variant=0):
    """Float homes lining both sides of a floating walkway (lines up with the
    'Floating dock walkway' piece): small, quirky one- and two-storey homes
    in bright colours, decks with kayaks, gazebos and umbrellas."""
    b = Building(1, 1)
    b.extra_top = 4.0
    rng = np.random.RandomState(301 + variant)
    _float(b, 0.0, 16.0, WALK[0], WALK[1])
    for x in (4.0, 12.0):
        b.bx(x - 0.2, x + 0.2, WALK[1] - 0.4, WALK[1] - 0.1, 0.7, 1.0, "steel")
    north, south = FLOAT_HOME_LAYOUTS[variant % len(FLOAT_HOME_LAYOUTS)]
    for side, (x0, x1, style, wall, trim, roof, accent) in ((-1, north), (1, south)):
        _small_home(b, x0, x1, side, style, wall, trim, roof, accent, rng)
    return b


def fish_and_chips():
    """Float restaurant (Barb's style): small take-out shack with a big
    'FISH & CHIPS' sign, order window, picnic tables with umbrellas on the
    float, people queuing, gulls on the railing."""
    b = Building(1, 1)
    b.extra_top = 6.0
    rng = np.random.RandomState(311)
    _float(b, 0.8, 15.2, 0.8, 15.2)
    _house(b, 2.0, 9.0, 2.0, 7.0, 0.7, 3.8, "white", roof="shed", roof_mat="fhteal")
    b.bx(3.0, 8.0, 6.95, 7.05, 1.8, 3.0, "window")                       # order window
    b.bx(2.8, 8.2, 7.0, 7.6, 1.6, 1.8, "timber")
    b.bx(2.0, 9.0, 7.0, 8.4, 3.6, 3.8, "fhteal")                          # awning
    iw, ih = decal_size("fishchips")
    b.sol(lambda X, Y, Z: (Y > 7.05) & (Y < 7.15) & (X > 2.2) & (X < 8.8) &
          decal_mask("fishchips", 5.5 - X, Z, 0.0, 4.5, 0.75, width=0.75 * iw / ih / 2.24), "flagred", 2.0, 9.0)
    b.bx(2.2, 8.8, 7.0, 7.05, 4.0, 5.0, "white")
    for x, y, c in ((11.5, 4.0, "flagred"), (11.5, 10.5, "fhyellow"), (5.0, 12.0, "fhteal")):
        b.bx(x - 1.3, x + 1.3, y - 0.45, y + 0.45, 1.6, 1.8, "timber")
        b.bx(x - 1.3, x + 1.3, y - 1.25, y - 0.85, 1.2, 1.35, "timber")
        b.bx(x - 1.3, x + 1.3, y + 0.85, y + 1.25, 1.2, 1.35, "timber")
        b.bx(x - 0.05, x + 0.05, y - 0.05, y + 0.05, 0.7, 3.8, "steel")
        b.sol(lambda X, Y, Z, x=x, y=y, c=c: ((X - x) ** 2 + (Y - y) ** 2 < 1.6 ** 2) &
              (Z > 3.4) & (Z <= 3.9 - 0.3 * np.sqrt((X - x) ** 2 + (Y - y) ** 2)), c, x - 1.7, x + 1.7)
    for i in range(4):
        _person(b, 4.0 + i * 0.8, 8.4 + rng.uniform(-0.2, 0.2), 0.7, rng)
    _people(b, 4, 9.5, 14.5, 2.0, 14.0, 0.7, rng, avoid=[(10.0, 13.0, 3.0, 5.4), (10.0, 13.0, 9.5, 11.9)])
    _rail(b, 0.9, 15.1, 0.9, 15.1, 0.7, "white", sides="se")
    return b


def dock_walk(variant=0):
    """Floating dock walkway along X: planked float on pontoons, cleats,
    a lamp, life ring, bollards; variant 1 adds a gangway shed and people."""
    b = Building(1, 1)
    b.extra_top = 3.0
    rng = np.random.RandomState(321 + variant)
    w0, w1 = WALK
    _float(b, 0.0, 16.0, w0, w1)
    for x in (2.0, 6.0, 10.0, 14.0):
        b.bx(x - 0.15, x + 0.15, w0 + 0.1, w0 + 0.4, 0.7, 0.95, "steel")
        b.bx(x - 0.15, x + 0.15, w1 - 0.4, w1 - 0.1, 0.7, 0.95, "steel")
    _lamp(b, 8.0, w1 - 0.3, 0.7, h=5.0)
    b.bx(4.0, 4.6, w1 - 0.1, w1, 1.4, 2.0, "orange")
    if variant == 1:                              # a branch finger float off the walkway
        _float(b, 11.0, 13.0, w1, 15.6)
        _float(b, 3.0, 5.0, 0.4, w0)
    return b


def _sailboat(b, x, y, along_x, rng, length=6.0):
    lx, ly = (length / 2, 1.1) if along_x else (1.1, length / 2)
    hull = HOUSE_COLOURS[rng.randint(len(HOUSE_COLOURS))] if rng.rand() < 0.3 else "white"

    def fn(X, Y, Z):
        u = (X - x) / lx if along_x else (Y - y) / ly
        v = (Y - y) / ly if along_x else (X - x) / lx
        w = 1 - np.clip(u, 0, 1) ** 2 * 0.9
        h = (np.abs(v) < w * np.sqrt(np.clip(1 - u ** 2, 0, 1))) & (np.abs(u) < 1) & (Z > 0.0) & (Z <= 0.9)
        cabin = (np.abs(v) < 0.55) & (u > -0.4) & (u < 0.25) & (Z > 0.9) & (Z <= 1.4)
        return [(h, hull), (h & (Z < 0.25), "navy"), (cabin, "white"), (cabin & (Z > 1.05) & (Z < 1.25), "window")]
    b.sol(fn, None, x - lx - 0.2, x + lx + 0.2)
    mx = x + (0.1 * length if along_x else 0)
    my = y + (0 if along_x else 0.1 * length)
    b.bx(mx - 0.06, mx + 0.06, my - 0.06, my + 0.06, 0.9, 0.9 + length * 1.3, "steel")
    b.ellipsoid(mx - b.cx, my - b.cy, 1.6, (0.9 if along_x else 0.2), (0.2 if along_x else 0.9), 0.18, "harbourblue")


def _motorboat(b, x, y, along_x, rng, length=5.0):
    lx, ly = (length / 2, 1.0) if along_x else (1.0, length / 2)

    def fn(X, Y, Z):
        u = (X - x) / lx if along_x else (Y - y) / ly
        v = (Y - y) / ly if along_x else (X - x) / lx
        w = np.where(u > 0.3, 1 - (u - 0.3) / 0.7 * 0.8, 1.0)
        h = (np.abs(v) < w) & (np.abs(u) < 1) & (Z > 0.0) & (Z <= 1.0)
        cab = (np.abs(v) < 0.7) & (u > -0.3) & (u < 0.35) & (Z > 1.0) & (Z <= 1.9)
        return [(h, "white"), (h & (Z < 0.3), "harbourblue"), (cab, "white"),
                (cab & (Z > 1.25) & (Z < 1.65), "window")]
    b.sol(fn, None, x - lx - 0.2, x + lx + 0.2)


def marina_slips(variant=0):
    """Marina: a main float along Y=8 with finger floats, sailboats and
    motorboats in the slips."""
    b = Building(1, 1)
    b.extra_top = 3.0
    rng = np.random.RandomState(331 + variant)
    _float(b, 0.0, 16.0, 7.0, 9.0)
    for x in (2.6, 7.6, 12.6):
        _float(b, x - 0.5, x + 0.5, 0.5, 7.0)
        _float(b, x - 0.5, x + 0.5, 9.0, 15.5)
    for x in (5.1, 10.1, 15.0):
        for y in (3.8, 12.2):
            if rng.rand() < 0.8:
                if rng.rand() < 0.55 + 0.2 * variant:
                    _sailboat(b, x - 0.05, y, False, rng, length=rng.uniform(5.0, 6.4))
                else:
                    _motorboat(b, x - 0.05, y, False, rng, length=rng.uniform(4.0, 5.4))
    _lamp(b, 8.0, 8.0, 0.7, h=4.5)
    return b


def ferry_dock():
    """Harbour ferry dock (Aquabus / Victoria Harbour Ferry): float with a
    small ticket hut and flag, and two of the little round-bowed passenger
    ferries alongside, one in rainbow stripes."""
    b = Building(1, 1)
    b.extra_top = 4.0
    rng = np.random.RandomState(341)
    _float(b, 0.5, 15.5, 1.0, 5.0)
    _house(b, 11.0, 14.5, 1.5, 4.5, 0.7, 3.2, "fhteal", roof="gable", roof_mat="white")
    _flagpole(b, 2.0, 2.0, 0.7, "canada", h=7.0)
    _people(b, 4, 2.5, 10.0, 1.5, 4.6, 0.7, rng)
    for k, (x, y) in enumerate(((5.0, 8.0), (11.5, 12.0))):
        def boat(X, Y, Z, x=x, y=y, k=k):
            u, v = (X - x) / 3.2, (Y - y) / 1.3
            hull = (u ** 2 * 0.6 + v ** 2 < 1) & (np.abs(u) < 1.15) & (Z > 0.0) & (Z <= 1.0)
            cab = (np.abs(u) < 0.7) & (np.abs(v) < 0.8) & (Z > 1.0) & (Z <= 2.4)
            roof = (np.abs(u) < 0.8) & (np.abs(v) < 0.9) & (Z > 2.4) & (Z <= 2.65)
            out = [(hull, "white"), (hull & (Z < 0.35), "harbourblue"), (cab, "white"),
                   (cab & (Z > 1.4) & (Z < 2.15), "glass")]
            if k == 1:                          # rainbow roof
                band = np.floor((u + 0.8) / 1.6 * 6).astype(int)
                for i, m in enumerate(["flagred", "orange", "fhyellow", "fhgreen", "fhteal", "fhpurple"]):
                    out.append((roof & (band == i), m))
            else:
                out.append((roof, "harbourblue"))
            return out
        b.sol(boat, None, x - 4.0, x + 4.0)
    return b


def pile_pier():
    """Timber pier on piles over the water, with a railing and a lamp."""
    b = Building(1, 1)
    b.extra_top = 3.0
    ZD = 3.4

    def pier(X, Y, Z):
        piles = (np.abs(np.mod(X, 4.0) - 2.0) < 0.25) & (np.abs(np.mod(Y, 4.0) - 2.0) < 0.25) & (Z <= ZD)
        deck = (Z > ZD - 0.4) & (Z <= ZD)
        planks = deck & (np.mod(X, 0.7) < 0.08)
        return [(piles, "piling"), (deck, "floatwood"), (planks, "piling")]
    b.sol(pier, None)
    _rail(b, 0.0, 16.0, 0.2, 15.8, ZD, "piling", h=1.1, sides="ns")
    _lamp(b, 8.0, 15.4, ZD, h=5.0)
    return b


def public_market():
    """Granville Island Public Market: grey-green corrugated industrial
    sheds with gabled roofs and clerestory, roof vents, the big rooftop
    'PUBLIC MARKET' sign with lamps, green/white and blue/white striped
    awnings over the stalls, red trim, produce stands, flag, people."""
    b = Building(2, 2)
    b.extra_top = 10.0
    rng = np.random.RandomState(351)
    _paving(b, seed=11.0)
    X0, X1, Y0, Y1, ZE = 2.0, 30.0, 2.5, 24.0, 8.0

    def shed(X, Y, Z):
        inside = (X >= X0) & (X <= X1) & (Y >= Y0) & (Y <= Y1) & (Z > 0.25) & (Z <= ZE)
        face = inside & ((np.minimum(X - X0, X1 - X) < 0.12) | (np.minimum(Y - Y0, Y1 - Y) < 0.12))
        along = np.where(np.minimum(Y - Y0, Y1 - Y) < 0.12, X, Y)
        ribs = face & (np.mod(along, 0.4) < 0.1)
        doors = face & (Z < 4.2) & (np.mod(along, 4.0) < 2.6)
        trim = face & (np.abs(Z - 4.4) < 0.18)
        return [(inside, "corrugated"), (ribs, "grey"), (doors, "window"), (trim, "flagred")]
    b.sol(shed, None, X0, X1)

    def roofs(X, Y, Z):                                   # three gables across the hall
        out = []
        for k in range(3):
            y0 = Y0 + k * (Y1 - Y0) / 3
            yc, half = y0 + (Y1 - Y0) / 6, (Y1 - Y0) / 6 + 0.3
            zr = ZE + (half - np.abs(Y - yc)) * 0.6
            r = (X > X0 - 0.4) & (X < X1 + 0.4) & (np.abs(Y - yc) < half) & (Z > ZE) & (Z <= zr)
            out += [(r, "corrugated"), (r & (Z > zr - 0.3), "roofmetal"),
                    (r & (np.mod(X, 0.5) < 0.08) & (Z > zr - 0.3), "grey")]
        return out
    b.sol(roofs, None, X0 - 0.4, X1 + 0.4)
    for x in (6.0, 13.0, 20.0, 27.0):                     # roof vents
        b.sol(lambda X, Y, Z, x=x: ((X - x) ** 2 + (Y - 9.6) ** 2 < 0.55 ** 2) & (Z > ZE + 2.0) &
              (Z <= ZE + 3.4), "steel", x - 0.6, x + 0.6)
    # rooftop sign with gooseneck lamps
    iw, ih = decal_size("publicmarket")
    b.bx(4.0, 28.0, Y1 - 4.2, Y1 - 3.9, ZE + 3.4, ZE + 6.2, "corrugated")
    b.sol(lambda X, Y, Z: (Y > Y1 - 3.9) & (Y < Y1 - 3.8) & (X > 4.0) & (X < 28.0) &
          decal_mask("publicmarket", 16.0 - X, Z, 0.0, ZE + 4.8, 2.0, width=2.0 * iw / ih / 2.24), "white",
          4.0, 28.0)
    b.bx(4.0, 28.0, Y1 - 3.9, Y1 - 3.8, ZE + 3.4, ZE + 3.6, "flagred")
    for x in np.arange(5.0, 28.0, 2.6):
        b.bx(x - 0.06, x + 0.06, Y1 - 4.2, Y1 - 3.0, ZE + 6.2, ZE + 6.35, "steel")
        b.bx(x - 0.18, x + 0.18, Y1 - 3.2, Y1 - 2.9, ZE + 5.9, ZE + 6.2, "white")
    # striped awnings over the stalls along the front
    for k, x0 in enumerate(np.arange(X0 + 0.5, X1 - 4.0, 5.2)):
        col = "awngreen" if k % 2 == 0 else "blue"
        b.sol(lambda X, Y, Z, x0=x0, col=col: [
            ((X > x0) & (X < x0 + 4.8) & (Y > Y1) & (Y < Y1 + 2.6) &
             (np.abs(Z - (4.8 - 0.4 * (Y - Y1))) < 0.12), "white"),
            ((X > x0) & (X < x0 + 4.8) & (Y > Y1) & (Y < Y1 + 2.6) &
             (np.abs(Z - (4.8 - 0.4 * (Y - Y1))) < 0.12) & (np.mod(X, 0.8) < 0.4), col)], None, x0, x0 + 4.8)
        # produce crates under the awning
        b.bx(x0 + 0.5, x0 + 4.3, Y1 + 0.3, Y1 + 1.4, 0.25, 1.1, "timber")
        for i in range(4):
            b.bx(x0 + 0.6 + i * 0.95, x0 + 1.4 + i * 0.95, Y1 + 0.4, Y1 + 1.3, 1.1, 1.35,
                 ["flagred", "fhyellow", "awngreen", "orange"][(i + k) % 4])
    _flagpole(b, 29.0, 27.0, 0.25, "canada", h=14.0)
    _people(b, 20, 2.0, 30.0, 27.0, 31.0, 0.25, rng)
    for x in (6.0, 22.0):
        _car(b, x, 29.0, 0.25, True, CAR_COLOURS[rng.randint(len(CAR_COLOURS))])
    return b


def giants_silos():
    """Ocean Concrete silos on Granville Island, painted as 'Giants' by
    OSGEMEOS (2014): six tall silos, each a different brightly patterned
    figure (stylised here), with the conveyor gantry above."""
    b = Building(2, 1)
    b.extra_top = 8.0
    _paving(b, seed=12.0)
    palettes = [("fhyellow", "flagred"), ("blue", "fhyellow"), ("fhgreen", "flagred"),
                ("fhpurple", "fhyellow"), ("flagred", "blue"), ("fhteal", "orange")]
    for k in range(6):
        x = 3.5 + k * 5.0
        body, pat = palettes[k]

        def silo(X, Y, Z, x=x, body=body, pat=pat):
            r = np.sqrt((X - x) ** 2 + (Y - 8.0) ** 2)
            cyl = (r < 2.3) & (Z > 0.25) & (Z <= 26.0)
            a = np.arctan2(Y - 8.0, X - x)
            face = cyl & (Z > 14.0) & (Z < 21.0) & (np.abs(a - 1.2) < 0.9)         # the giant's face
            eyes = face & (np.abs(Z - 18.4) < 0.5) & (np.abs(np.abs(a - 1.2) - 0.35) < 0.15)
            pattern = cyl & (Z <= 14.0) & ((np.mod(Z * 0.9 + a * 2.0, 2.0) < 0.6) |
                                           (np.mod(Z * 0.6 - a * 3.0, 3.0) < 0.5))
            return [(cyl, body), (pattern, pat), (face, "skin"), (eyes, "acblack"),
                    (cyl & (Z > 25.2), "concrete")]
        b.sol(silo, None, x - 2.5, x + 2.5)
    b.bx(1.0, 31.0, 7.4, 8.6, 26.0, 27.4, "steel")                       # conveyor gantry
    b.sol(lambda X, Y, Z: (X > 26.0) & (X < 32.0) & (np.abs(Y - 8.0) < 0.6) &
          (np.abs(Z - (27.0 - (X - 26.0) * 3.0)) < 0.5), "steel", 26.0, 32.0)
    return b


def artisan_shed(variant=0):
    """Granville Island artisan shed: a small corrugated building painted a
    bright colour, roll-up door, striped awning, sign board, people."""
    b = Building(1, 1)
    b.extra_top = 3.0
    rng = np.random.RandomState(361 + variant)
    _paving(b, seed=13.0 + variant)
    col = ["fhyellow", "blue", "fhred", "fhteal"][variant % 4]

    def shed(X, Y, Z):
        inside = (X >= 2.0) & (X <= 14.0) & (Y >= 2.0) & (Y <= 10.0) & (Z > 0.25) & (Z <= 6.0)
        face = inside & ((np.minimum(X - 2.0, 14.0 - X) < 0.12) | (np.minimum(Y - 2.0, 10.0 - Y) < 0.12))
        along = np.where(np.minimum(Y - 2.0, 10.0 - Y) < 0.12, X, Y)
        return [(inside, col), (face & (np.mod(along, 0.4) < 0.1), "grey"),
                (face & (Y > 9.88) & (X > 6.0) & (X < 10.0) & (Z < 4.0), "window")]
    b.sol(shed, None, 2.0, 14.0)
    b.sol(lambda X, Y, Z: (X > 1.6) & (X < 14.4) & (Y > 1.6) & (Y < 10.4) &
          (Z > 6.0) & (Z <= 6.0 + (4.4 - np.abs(Y - 6.0)) * 0.5), "roofmetal", 1.6, 14.4)
    b.sol(lambda X, Y, Z: [((X > 3.0) & (X < 13.0) & (Y > 10.0) & (Y < 12.2) &
                            (np.abs(Z - (4.2 - 0.4 * (Y - 10.0))) < 0.12), "white"),
                           ((X > 3.0) & (X < 13.0) & (Y > 10.0) & (Y < 12.2) &
                            (np.abs(Z - (4.2 - 0.4 * (Y - 10.0))) < 0.12) & (np.mod(X, 0.8) < 0.4),
                            "flagred" if variant % 2 else "awngreen")], None, 3.0, 13.0)
    b.bx(4.0, 12.0, 10.0, 10.1, 4.6, 5.6, "white")
    _people(b, 4, 2.0, 14.0, 12.5, 15.5, 0.25, rng)
    _planter(b, 14.5, 13.5, 0.25, r=0.7, tree=False)
    return b


def fisgard_lighthouse():
    """Fisgard Lighthouse (1860, Esquimalt Harbour): white round tower with
    red lantern room and black cap, the red-brick keeper's house attached,
    on a rocky islet with the causeway leaving to one side."""
    b = Building(1, 1)
    b.extra_top = 8.0
    rng = np.random.RandomState(371)
    for _ in range(9):
        _rock(b, rng.uniform(1.0, 15.0), rng.uniform(1.0, 15.0), 0.2, rng.uniform(1.2, 2.4), rng)
    b.sol(lambda X, Y, Z: (Z <= 1.6) & (((X - 8.0) ** 2 + (Y - 8.0) ** 2) < 6.5 ** 2), "granite")
    b.sol(lambda X, Y, Z: (Z > 1.5) & (Z <= 1.7) & (((X - 8.0) ** 2 + (Y - 8.0) ** 2) < 6.0 ** 2) &
          _stain(X, Y, 3.0, 1.2, 0.5), "moss")
    # keeper's house: red brick, white trim, hipped roof
    _house(b, 3.5, 9.5, 5.0, 11.0, 1.7, 6.4, "brick", roof="gable", roof_mat="dark", trim="white")
    r = lambda X, Y: np.sqrt((X - 11.0) ** 2 + (Y - 8.0) ** 2)  # noqa: E731
    b.sol(lambda X, Y, Z: [((r(X, Y) < 1.35 - 0.012 * Z) & (Z > 1.7) & (Z <= 19.0), "white"),
                           ((r(X, Y) < 1.9) & (Z > 19.0) & (Z <= 19.4), "white"),
                           ((np.abs(r(X, Y) - 1.8) < 0.07) & (Z > 19.4) & (Z <= 20.2), "acblack"),
                           ((r(X, Y) < 1.15) & (Z > 19.4) & (Z <= 21.4), "flagred"),
                           ((r(X, Y) < 1.15) & (Z > 19.8) & (Z <= 21.0) &
                            (np.mod(np.arctan2(Y - 8.0, X - 11.0) * 4 / np.pi, 1) < 0.7), "glass"),
                           ((r(X, Y) < 1.25 * (1 - (Z - 21.4) / 1.4)) & (Z > 21.4) & (Z <= 22.8), "acblack")],
          None, 9.0, 13.0)
    return b


def seawall(variant=0):
    """Seawall promenade on the shore: paved walk with a bike path, railing
    on the water edge (+X), benches, lamps, a weeping willow, people."""
    b = Building(1, 1)
    b.extra_top = 12.0
    rng = np.random.RandomState(381 + variant)
    b.sol(lambda X, Y, Z: [((Z <= 0.25), "concrete"),
                           ((Z <= 0.25) & (X < 6.0), "asphalt"),
                           ((Z <= 0.25) & (X < 6.0) & (np.abs(X - 3.0) < 0.08) & (np.mod(Y, 2.0) < 1.1), "fhyellow"),
                           ((Z <= 0.25) & (X > 6.0) & _stain(X, Y, 14.0 + variant, 2.0, 0.2), "concrete2"),
                           ((Z <= 0.6) & (X > 15.2), "granite")], None)
    _rail(b, 15.0, 15.4, 0.0, 16.0, 0.6, "steel", h=1.2, sides="e")
    _bench(b, 13.0, 4.0, 0.25, False)
    _lamp(b, 14.4, 12.0, 0.25, h=7.0)

    blobs = [(9.5, 10.5, 9.0, 2.6), (8.0, 9.6, 8.2, 2.2), (11.0, 9.8, 8.0, 2.1),
             (9.2, 12.2, 8.1, 2.2), (10.6, 11.8, 8.6, 1.9)]

    def willow(X, Y, Z):
        trunk = (np.abs(X - 9.5) < 0.35) & (np.abs(Y - 10.5) < 0.35) & (Z <= 6.5)
        crown = np.zeros(X.shape, bool)
        hang = np.zeros(X.shape, bool)
        for bx, by, bz, br in blobs:
            d2 = ((X - bx) ** 2 + (Y - by) ** 2) / br ** 2
            crown |= d2 + ((Z - bz) / (br * 0.7)) ** 2 < 1.0
            # drooping strands under the outer half of each blob, ragged lengths
            ln = 2.0 + 3.0 * (0.5 + 0.5 * np.sin(np.arctan2(Y - by, X - bx) * 7.0 + bx))
            hang |= (d2 < 1.0) & (d2 > 0.35) & (Z < bz) & (Z > bz - ln * np.sqrt(d2)) & \
                (np.mod(np.arctan2(Y - by, X - bx) * 14 / np.pi, 1.0) < 0.5)
        leaf = crown | hang
        return [(trunk, "piling"), (leaf, "willow"),
                (leaf & (np.mod(X * 1.9 + Y * 1.3 + Z * 2.3, 1.0) < 0.3), "moss")]
    if variant == 0:
        b.sol(willow, None, 5.0, 14.0)
    _people(b, 5, 0.6, 14.4, 0.6, 15.4, 0.25, rng, avoid=[(6.0, 13.0, 7.0, 14.0)] if variant == 0 else [])
    return b


def _stone_block(b, x0, x1, y0, y1, z0, z1, storey=2.4, arched=True):
    """Stone block with rows of (arched) windows, string courses and a
    cornice, as on the Parliament Buildings."""
    def fn(X, Y, Z):
        inside = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1) & (Z > z0) & (Z <= z1)
        dx, dy = np.minimum(X - x0, x1 - X), np.minimum(Y - y0, y1 - Y)
        face = inside & ((dx < 0.12) | (dy < 0.12))
        along = np.where(dy < 0.12, X, Y)
        sz = np.mod(Z - z0, storey)
        bay = np.mod(along, 1.4)
        win = face & (np.abs(bay - 0.7) < 0.3) & (sz > 0.7) & (sz < 1.9)
        if arched:
            win &= ~((sz > 1.6) & (np.abs(bay - 0.7) > 0.3 - (1.9 - sz)))
        course = face & (sz < 0.14)
        cornice = inside & (Z > z1 - 0.35)
        return [(inside, "andesite"), (win, "window"), (course, "stone"), (cornice, "stone")]
    b.sol(fn, None, x0, x1)


def _dome(b, x, y, z, r, h, lantern=True, statue=False):
    """Copper dome on a drum, with a lantern (and the gilded statue)."""
    def dome(X, Y, Z):
        rr = (X - x) ** 2 + (Y - y) ** 2
        ang = np.arctan2(Y - y, X - x)
        zd = z + h * 0.35
        drum = (rr < (r * 0.92) ** 2) & (Z > z) & (Z <= zd)
        drum_win = drum & (np.mod(ang * 8 / np.pi, 1) < 0.35) & (Z > z + h * 0.08) & (Z < z + h * 0.28)
        shell = (rr + ((Z - zd) / (h * 0.65) * r) ** 2 < r ** 2) & (Z > zd)
        ribs = shell & (np.mod(ang * 6 / np.pi, 1) < 0.12)
        return [(drum, "andesite"), (drum_win, "window"), (shell, "copper"), (ribs, "fhgreen")]
    b.sol(dome, None, x - r - 0.2, x + r + 0.2)
    top = z + h
    if lantern:
        b.sol(lambda X, Y, Z: [(((X - x) ** 2 + (Y - y) ** 2 < (r * 0.28) ** 2) & (Z > top - 0.2) &
                                (Z <= top + h * 0.3), "andesite"),
                               (((X - x) ** 2 + (Y - y) ** 2 < (r * 0.28) ** 2) & (Z > top + h * 0.06) &
                                (Z <= top + h * 0.24) &
                                (np.mod(np.arctan2(Y - y, X - x) * 4 / np.pi, 1) < 0.45), "window")],
              None, x - r, x + r)
        b.ellipsoid(x - b.cx, y - b.cy, top + h * 0.33, r * 0.3, r * 0.3, h * 0.12, "copper")
        top += h * 0.42
    if statue:                                     # gilded Captain George Vancouver
        b.bx(x - 0.12, x + 0.12, y - 0.12, y + 0.12, top, top + 0.9, "gold")
        b.ellipsoid(x - b.cx, y - b.cy, top + 1.05, 0.16, 0.16, 0.18, "gold")


def legislature():
    """British Columbia Parliament Buildings, Victoria (1897, F. M.
    Rattenbury): long symmetrical grey stone front, the central block with its
    big copper dome, lantern and gilded statue of Captain Vancouver, corner
    turrets with small domes, wings ending in pavilions with paired domes;
    grand stairs, the fountain, the lawn with its path, and flags."""
    b = Building(3, 2)
    b.extra_top = 4.0
    # lawn, path and forecourt
    b.sol(lambda X, Y, Z: [((Z <= 0.25), "lawn"),
                           ((Z <= 0.25) & (Y < 21.0), "concrete"),
                           ((Z <= 0.26) & (np.abs(X - 24.0) < 1.2) & (Y >= 21.0), "concrete"),
                           ((Z <= 0.26) & (((X - 24.0) ** 2 + (Y - 25.5) ** 2) < 3.2 ** 2), "concrete")], None)
    # wings and end pavilions
    _stone_block(b, 4.0, 19.0, 9.0, 19.0, 0.25, 5.2)
    _stone_block(b, 29.0, 44.0, 9.0, 19.0, 0.25, 5.2)
    for xa, xb in ((2.5, 9.0), (39.0, 45.5)):
        _stone_block(b, xa, xb, 8.0, 20.0, 0.25, 6.4)
        b.sol(lambda X, Y, Z, xa=xa, xb=xb: (X > xa) & (X < xb) & (Y > 8.0) & (Y < 20.0) & (Z > 6.4) &
              (Z <= 6.4 + 1.6 * np.clip(np.minimum(np.minimum(X - xa, xb - X), np.minimum(Y - 8.0, 20.0 - Y)) / 2.0, 0, 1)),
              "copper", xa, xb)                              # hipped copper roof
        for xc in (xa + 1.3, xb - 1.3):
            b.bx(xc - 1.0, xc + 1.0, 18.0, 20.2, 6.4, 7.6, "andesite")
            _dome(b, xc, 19.1, 7.6, 1.0, 2.2, lantern=True)
    for xa, xb in ((9.0, 19.0), (29.0, 39.0)):                # mansard roofs on the wings
        b.sol(lambda X, Y, Z, xa=xa, xb=xb: (X > xa) & (X < xb) & (Y > 9.0) & (Y < 19.0) & (Z > 5.2) &
              (Z <= 5.2 + 1.2 * np.clip(np.minimum(Y - 9.0, 19.0 - Y) / 1.5, 0, 1)), "copper", xa, xb)
    # central block, entrance arch, corner turrets
    _stone_block(b, 19.0, 29.0, 7.0, 21.0, 0.25, 7.6)
    b.bx(22.4, 25.6, 20.95, 21.1, 0.25, 3.4, "window")
    b.sol(lambda X, Y, Z: (np.abs(Y - 21.05) < 0.12) & ((X - 24.0) ** 2 + (Z - 3.4) ** 2 < 1.6 ** 2) &
          (Z > 3.4), "window", 22.0, 26.0)
    for xc in (20.2, 27.8):
        for yc in (8.2, 19.8):
            b.bx(xc - 1.0, xc + 1.0, yc - 1.0, yc + 1.0, 7.6, 9.2, "andesite")
            _dome(b, xc, yc, 9.2, 1.0, 2.0)
    b.bx(20.5, 27.5, 9.0, 19.0, 7.6, 9.0, "andesite")
    _dome(b, 24.0, 14.0, 9.0, 3.4, 5.4, lantern=True, statue=True)
    # grand stairs, fountain, flags
    for k in range(5):
        b.bx(21.0 - k * 0.3, 27.0 + k * 0.3, 21.0 + k * 0.45, 21.45 + k * 0.45, 0.25, 1.4 - k * 0.25, "stone")
    b.sol(lambda X, Y, Z: [(((X - 24.0) ** 2 + (Y - 25.5) ** 2 < 2.6 ** 2) & (Z <= 0.6), "stone"),
                           (((X - 24.0) ** 2 + (Y - 25.5) ** 2 < 2.3 ** 2) & (Z <= 0.62) & (Z > 0.5), "glass"),
                           (((X - 24.0) ** 2 + (Y - 25.5) ** 2 < 0.25 ** 2) & (Z <= 2.4), "stone"),
                           (((X - 24.0) ** 2 + (Y - 25.5) ** 2 < 1.1 ** 2) & (np.abs(Z - 2.4) < 0.18), "stone")],
          None, 21.0, 27.0)
    _flagpole(b, 14.0, 22.0, 0.25, "bc", h=8.0)
    _flagpole(b, 34.0, 22.0, 0.25, "canada", h=8.0)
    for x in (6.0, 42.0):
        _fir(b, x, 27.0, 0.25, 14.0, np.random.RandomState(int(x)))
    return b
