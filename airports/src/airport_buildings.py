"""
YVR and YYJ landmark objects, built with the terminals toolkit
(terminals/src/buildings.py). Placed around a standard OpenTTD airport:
OpenTTD's airport layouts and movement are fixed, so these dress it.
Photos on Commons: YVR control tower (2008-2021), YVR terminals, YYJ
terminal and apron (2019).
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "common"))
sys.path.insert(0, os.path.join(_REPO, "terminals", "src"))
from buildings import (Building, _paving, _stain, _people, _person, _bench, _planter,  # noqa: E402
                       _lamp, _car, _flagpole, _signpost, CAR_COLOURS)


def _apron(b, seed=0.0):
    """Apron concrete slabs with expansion joints and tyre marks."""
    b.sol(lambda X, Y, Z: [((Z <= 0.2), "apronconc"),
                           ((Z <= 0.2) & _stain(X, Y, seed, 3.0, 0.2), "concrete2"),
                           ((Z <= 0.2) & ((np.mod(X, 4.0) < 0.08) | (np.mod(Y, 4.0) < 0.08)), "grey")],
          None)


def yvr_tower():
    """YVR control tower: tall round concrete shaft with a flared foot and a
    balcony ring, the wide many-sided cab in banded teal glass under a dark
    cornice, roof railing, antennas and radome."""
    b = Building(1, 1)
    b.extra_top = 10.0
    _paving(b, seed=5.0)
    r = lambda X, Y: np.sqrt((X - 8.0) ** 2 + (Y - 8.0) ** 2)  # noqa: E731
    ang = lambda X, Y: np.arctan2(Y - 8.0, X - 8.0)  # noqa: E731

    def tower(X, Y, Z):
        R = r(X, Y)
        poly = R * np.cos(np.mod(ang(X, Y), np.pi / 8) - np.pi / 16) / np.cos(np.pi / 16)  # 16-sided
        shaft = (R < 1.7 + 1.2 * np.clip((3.0 - Z) / 3.0, 0, 1)) & (Z > 0.25) & (Z <= 36.0)
        flutes = shaft & (np.mod(ang(X, Y) * 6 / np.pi, 1) < 0.12) & (Z > 3.0)
        balcony = (R < 2.7) & (R > 1.6) & (np.abs(Z - 24.0) < 0.3)
        rail = (np.abs(R - 2.6) < 0.08) & (Z > 24.3) & (Z <= 25.2) & \
            ((Z > 25.05) | (np.mod(ang(X, Y) * 10, 1) < 0.15))
        cab_base = (poly < 4.4) & (Z > 34.0) & (Z <= 35.4)
        cab = (poly < 4.6) & (Z > 35.4) & (Z <= 41.0)
        bands = cab & (np.mod(Z - 35.4, 1.4) < 0.28)
        mull = cab & (np.mod(ang(X, Y), np.pi / 8) < 0.05)
        cornice = (poly < 4.9) & (Z > 41.0) & (Z <= 41.8)
        roof = (poly < 4.2) & (Z > 41.8) & (Z <= 42.6)
        return [(shaft, "concrete"), (flutes, "concrete2"), (balcony, "concrete"), (rail, "steel"),
                (cab_base, "concrete"), (cab, "tealglass"), (bands, "tealdark"), (mull, "steel"),
                (cornice, "tealdark"), (roof, "silver")]
    b.sol(tower, None, 2.0, 14.0)
    b.radome(8.0 - b.cx, 6.2 - b.cy, 42.6, r=0.7)
    for x, h in ((9.4, 47.0), (7.0, 46.0)):
        b.bx(x - 0.07, x + 0.07, 9.0, 9.14, 42.6, h, "steel")
    b.bx(6.4, 9.6, 9.0, 9.1, 45.0, 45.15, "steel")
    rng = np.random.RandomState(201)
    _people(b, 3, 1.0, 15.0, 12.5, 15.0, 0.25, rng)
    return b


def yvr_terminal():
    """YVR terminal section: teal-green glass curtain wall over a granite
    base, the silver barrel-vaulted roof with a glazed ridge, west coast
    timber soffit at the entrance canopy, the departures-level road and
    curb with cars dropping off, trees in planters."""
    b = Building(2, 2)
    b.extra_top = 8.0
    _paving(b, seed=6.0)
    X0, X1, Y0, Y1, ZE = 1.5, 30.5, 3.0, 22.0, 13.0

    def hall(X, Y, Z):
        inside = (X >= X0) & (X <= X1) & (Y >= Y0) & (Y <= Y1) & (Z > 0.25) & (Z <= ZE)
        face = inside & ((np.minimum(X - X0, X1 - X) < 0.15) | (np.minimum(Y - Y0, Y1 - Y) < 0.15))
        along = np.where(np.minimum(Y - Y0, Y1 - Y) < 0.15, X, Y)
        base = face & (Z < 2.4)
        mull = face & ~base & ((np.mod(along, 1.6) < 0.14) | (np.mod(Z, 2.6) < 0.14))
        return [(inside, "white"), (face, "tealglass"), (mull, "steel"), (base, "granite")]
    b.sol(hall, None, X0, X1)

    def roof(X, Y, Z):
        yc, half = (Y0 + Y1) / 2, (Y1 - Y0) / 2 + 1.2
        q = np.clip(np.abs(Y - yc) / half, 0, 1)
        zr = ZE + 5.0 * np.sqrt(1 - q ** 2)
        shell = (X > X0 - 1.0) & (X < X1 + 1.0) & (np.abs(Y - yc) < half) & (Z > ZE) & (Z <= zr) & \
            (Z > zr - 0.6)
        ribs = shell & (np.mod(X, 2.4) < 0.2)
        ridge = shell & (np.abs(Y - yc) < 1.4)
        return [(shell, "silver"), (ribs, "steel"), (ridge, "tealglass")]
    b.sol(roof, None, X0 - 1.0, X1 + 1.0)
    # entrance canopies with timber soffit over the departures curb
    for xc in (8.0, 16.0, 24.0):
        b.bx(xc - 3.0, xc + 3.0, Y1, Y1 + 4.0, 6.6, 7.1, "silver")
        b.bx(xc - 3.0, xc + 3.0, Y1, Y1 + 4.0, 6.3, 6.6, "timber")
        for xp in (xc - 2.7, xc + 2.5):
            b.bx(xp, xp + 0.25, Y1 + 3.6, Y1 + 3.85, 0.25, 6.3, "steel")

    # departures road along the front, cars at the curb
    def road(X, Y, Z):
        g = (Y > 26.5) & (Z <= 0.3)
        return [(g, "asphalt"), (g & (np.abs(Y - 29.3) < 0.08) & (np.mod(X, 3.0) < 1.6), "laneline"),
                ((Y > 26.0) & (Y <= 26.5) & (Z <= 0.45), "concrete")]
    b.sol(road, None)
    rng = np.random.RandomState(211)
    for x in (4.0, 11.0, 19.5, 27.0):
        _car(b, x, 27.6, 0.3, True, CAR_COLOURS[rng.randint(len(CAR_COLOURS))])
    _people(b, 16, 2.0, 30.0, 22.4, 25.8, 0.25, rng,
            avoid=[(5.0, 11.0, 25.4, 26.0), (13.0, 19.0, 25.4, 26.0), (21.0, 27.0, 25.4, 26.0)])
    for x in (2.6, 29.4):
        _planter(b, x, 24.6, 0.25, r=0.9, tree=True)
    b.bx(10.0, 13.0, 9.0, 12.0, ZE + 4.0, ZE + 5.6, "steel")
    return b


def jet_bridge():
    """Jet bridge (passenger boarding bridge): glazed rotunda by the
    terminal, telescoping tunnel sections reaching out over the apron on a
    wheeled bogie, and the cab with its canopy at the aircraft end."""
    b = Building(1, 1)
    b.extra_top = 4.0
    _apron(b, 2.0)
    Z0, Z1 = 7.0, 10.6
    b.sol(lambda X, Y, Z: [((np.sqrt((X - 2.4) ** 2 + (Y - 8.0) ** 2) < 1.6) & (Z > 0.2) & (Z <= Z1 + 0.4), "jbgrey"),
                           ((np.abs(np.sqrt((X - 2.4) ** 2 + (Y - 8.0) ** 2) - 1.55) < 0.08) & (Z > Z0 + 0.8) &
                            (Z <= Z1 - 0.6), "glass")], None, 0.6, 4.2)

    def tunnel(X, Y, Z):
        w = np.where(X < 8.0, 1.5, 1.35)                       # telescoping step
        t = (X > 3.6) & (X < 13.0) & (np.abs(Y - 8.0) < w) & (Z > Z0) & (Z <= Z1)
        seams = t & ((np.abs(X - 8.0) < 0.12) | (np.mod(X, 1.0) < 0.06))
        band = t & (np.abs(Y - 8.0) > w - 0.12) & (Z > Z0 + 1.4) & (Z < Z1 - 1.2)
        return [(t, "jbgrey"), (seams, "nacgrey"), (band, "window")]
    b.sol(tunnel, None, 3.6, 13.0)
    b.bx(13.0, 15.4, 5.8, 10.2, Z0 - 0.4, Z1 + 0.6, "jbgrey")        # cab
    b.bx(15.2, 15.6, 6.2, 9.8, Z0, Z1 - 0.2, "acblack")              # bellows/canopy
    b.bx(13.1, 15.3, 5.75, 5.8, Z0 + 1.2, Z1 - 0.6, "window")
    b.bx(10.6, 11.0, 7.6, 8.4, 0.2, Z0, "steel")                     # bogie leg
    b.bx(10.0, 11.6, 6.6, 9.4, 0.2, 1.2, "nacgrey")
    for y in (6.9, 9.1):
        b.bx(10.2, 11.4, y - 0.3, y + 0.3, 0.0, 0.8, "tyre")
    # lead-in line and stop bar for the aircraft
    b.sol(lambda X, Y, Z: (Z <= 0.25) & (((np.abs(Y - 14.0) < 0.12) & (X > 2.0)) |
                                          ((np.abs(X - 14.5) < 0.25) & (np.abs(Y - 14.0) < 1.2))),
          "yellow")
    return b


def yvr_parkade():
    """Parkade: three decks of concrete with spandrel stripes, a ramp, cars
    on the open top deck, light standards and a stair core with a sign."""
    b = Building(2, 2)
    b.extra_top = 4.0
    _paving(b, seed=7.0)
    X0, X1, Y0, Y1 = 1.5, 30.5, 1.5, 30.5
    decks = (0.25, 4.0, 7.75, 11.5)

    def body(X, Y, Z):
        inb = (X >= X0) & (X <= X1) & (Y >= Y0) & (Y <= Y1)
        out = []
        for z in decks[1:]:
            out.append((inb & (Z > z - 0.5) & (Z <= z), "concrete"))
            edge = inb & ((np.minimum(X - X0, X1 - X) < 0.25) | (np.minimum(Y - Y0, Y1 - Y) < 0.25))
            out.append((edge & (Z > z) & (Z <= z + 1.1), "concrete"))
            out.append((edge & (Z > z + 0.7) & (Z <= z + 1.1), "concrete2"))
        cols = inb & (np.mod(X - X0, 5.6) < 0.5) & (np.mod(Y - Y0, 5.6) < 0.5) & (Z > 0.25) & (Z <= decks[-1])
        out.append((cols, "concrete"))
        top = inb & (Z > decks[-1] - 0.01) & (Z <= decks[-1] + 0.05)
        out.append((top & (np.abs(np.mod(Y - Y0, 5.6) - 2.8) > 2.7), "laneline"))
        return out
    b.sol(body, None, X0, X1)
    b.bx(X1 - 4.0, X1, Y0, Y0 + 4.0, 0.25, decks[-1] + 3.0, "concrete")   # stair core
    b.bx(X1 - 3.9, X1 - 0.1, Y0 + 3.95, Y0 + 4.05, decks[-1] + 0.6, decks[-1] + 2.4, "bcfblue")
    rng = np.random.RandomState(221)
    for i in range(14):
        _car(b, 3.5 + (i % 7) * 3.6, 5.0 + (i // 7) * 16.0 + rng.uniform(-0.3, 0.3), decks[-1], False,
             CAR_COLOURS[rng.randint(len(CAR_COLOURS))])
    for x, y in ((8.0, 16.0), (24.0, 16.0)):
        _lamp(b, x, y, decks[-1], h=9.0)
    return b


def yyj_terminal():
    """YYJ terminal: low beige stucco building with a dark glass band and
    flat roof, the glass rotunda (drum) with its overhanging white disc roof
    at one end, entrance canopies, a Garry oak, curbside cars."""
    b = Building(2, 1)
    b.extra_top = 6.0
    _paving(b, seed=8.0)
    X0, X1, Y0, Y1 = 9.0, 30.5, 2.5, 11.0

    def body(X, Y, Z):
        inside = (X >= X0) & (X <= X1) & (Y >= Y0) & (Y <= Y1) & (Z > 0.25) & (Z <= 8.0)
        face = inside & ((np.minimum(X - X0, X1 - X) < 0.12) | (np.minimum(Y - Y0, Y1 - Y) < 0.12))
        along = np.where(np.minimum(Y - Y0, Y1 - Y) < 0.12, X, Y)
        win = face & (Z > 2.0) & (Z < 4.4) & (np.mod(along, 2.2) < 1.6)
        return [(inside, "beige"), (win, "window"), (face & (Z < 0.9), "granite"),
                (inside & (Z > 7.7), "membrane"), (face & (Z > 7.2), "white")]
    b.sol(body, None, X0, X1)
    r = lambda X, Y: np.sqrt((X - 6.0) ** 2 + (Y - 6.8) ** 2)  # noqa: E731

    def drum(X, Y, Z):
        R = r(X, Y)
        glass = (R < 4.6) & (Z > 0.25) & (Z <= 9.4)
        mull = glass & (np.mod(np.arctan2(Y - 6.8, X - 6.0) * 10 / np.pi, 1) < 0.12)
        sill = (R < 4.7) & (Z > 0.25) & (Z <= 1.2)
        disc = (R < 5.6) & (Z > 9.4) & (Z <= 10.2)
        return [(glass, "glass"), (mull, "steel"), (sill, "beige"), (disc, "white")]
    b.sol(drum, None, 0.4, 11.6)
    for x0 in (13.0, 22.0):                                       # entrance canopies
        b.bx(x0, x0 + 5.0, Y1, Y1 + 2.6, 4.6, 5.0, "white")
        b.bx(x0 + 0.2, x0 + 4.8, Y1 - 0.02, Y1, 0.25, 4.4, "glass")

    def oak(X, Y, Z):                                             # Garry oak in leaf
        trunk = (np.abs(X - 1.6) < 0.3) & (np.abs(Y - 13.6) < 0.3) & (Z <= 5.0)
        d = (X - 1.6) ** 2 + (Y - 13.6) ** 2 + ((Z - 7.2) * 0.85) ** 2
        lumpy = 3.0 + 0.5 * np.sin(X * 2.1 + Z * 1.3) * np.sin(Y * 1.7 - Z)
        crown = d < lumpy ** 2
        return [(trunk, "piling"), (crown, "fir2"), (crown & (np.mod(X * 1.3 + Y * 0.7 + Z * 0.9, 1.0) < 0.3), "moss")]
    b.sol(oak, None, 0.0, 4.8)
    rng = np.random.RandomState(231)
    for x in (12.0, 19.0, 26.5):
        _car(b, x, 14.4, 0.25, True, CAR_COLOURS[rng.randint(len(CAR_COLOURS))])
    _people(b, 8, 9.5, 30.0, 11.6, 13.4, 0.25, rng)
    _flagpole(b, 3.0, 12.0, 0.25, "canada", h=10.0)
    return b


def yyj_tower():
    """YYJ control tower: slim square concrete tower, glass cab with a dark
    band and white roof, antennas."""
    b = Building(1, 1)
    b.extra_top = 8.0
    _paving(b, seed=9.0)
    b.bx(4.0, 12.0, 4.0, 12.0, 0.25, 3.6, "beige")
    b.bx(4.0, 12.0, 4.0, 12.0, 1.6, 2.6, "window")
    b.bx(4.1, 11.9, 4.1, 11.9, 1.6, 2.6, "beige")
    b.bx(6.6, 9.4, 6.6, 9.4, 3.6, 22.0, "concrete")
    b.bx(6.5, 9.5, 6.5, 9.5, 12.0, 12.4, "concrete2")
    b.bx(5.4, 10.6, 5.4, 10.6, 22.0, 23.0, "concrete")
    b.bx(5.2, 10.8, 5.2, 10.8, 23.0, 26.2, "tealglass")
    b.bx(5.2, 10.8, 5.2, 10.8, 25.0, 25.5, "tealdark")
    b.bx(4.8, 11.2, 4.8, 11.2, 26.2, 26.8, "white")
    b.bx(7.9, 8.1, 7.9, 8.1, 26.8, 30.0, "steel")
    b.bx(9.4, 9.5, 6.0, 6.1, 26.8, 29.0, "steel")
    return b


def apron_service(variant=0):
    """Apron with ground service equipment: baggage tug towing a train of
    carts, a belt loader, a fuel truck or catering truck, cones and crew in
    hi-vis vests, yellow taxi guidance lines."""
    b = Building(1, 1)
    b.extra_top = 2.0
    _apron(b, 3.0 + variant)
    b.sol(lambda X, Y, Z: (Z <= 0.25) & ((np.abs(Y - 3.0) < 0.12) | (np.abs(X - 13.0) < 0.12)), "yellow")
    rng = np.random.RandomState(241 + variant)
    # tug and baggage carts along X
    b.bx(1.0, 3.0, 9.0, 10.6, 0.2, 1.4, "yellow")
    b.bx(1.4, 2.2, 9.1, 10.5, 1.4, 2.4, "glass")
    for i in range(3):
        x = 3.6 + i * 2.6
        b.bx(x, x + 2.2, 9.0, 10.6, 0.5, 1.0, "nacgrey")
        b.bx(x + 0.1, x + 2.1, 9.1, 10.5, 1.0, 2.4, "harbourblue" if i % 2 else "car5")
        b.bx(x + 0.1, x + 2.1, 9.0, 9.1, 1.0, 2.4, "dark")
    if variant == 0:
        # fuel truck
        b.bx(2.0, 4.2, 12.8, 15.0, 0.3, 2.6, "white")
        b.bx(2.4, 4.0, 12.9, 14.9, 1.6, 2.4, "glass")
        b.sol(lambda X, Y, Z: (X > 4.4) & (X < 11.0) & ((Y - 13.9) ** 2 + (Z - 1.9) ** 2 < 1.15 ** 2),
              "silver", 4.4, 11.0)
        b.bx(10.4, 10.9, 12.8, 15.0, 0.3, 1.0, "dark")
    else:
        # belt loader angled up
        b.bx(3.0, 5.4, 12.8, 14.6, 0.3, 1.6, "yellow")
        b.sol(lambda X, Y, Z: (X > 4.0) & (X < 12.0) & (np.abs(Y - 13.7) < 0.55) &
              (np.abs(Z - (1.4 + (X - 4.0) * 0.45)) < 0.18), "acblack", 4.0, 12.0)
    for x, y in ((14.4, 5.0), (14.4, 11.0), (1.0, 5.4)):
        b.bx(x - 0.2, x + 0.2, y - 0.2, y + 0.2, 0.2, 0.9, "orange")
    for _ in range(3):
        x, y = rng.uniform(2.0, 12.0), rng.uniform(4.0, 7.5)
        _person(b, x, y, 0.2, rng)
        b.bx(x - 0.26, x + 0.26, y - 0.22, y + 0.22, 1.25, 1.55, "yellow")      # hi-vis
    return b


def harbour_air_dock():
    """Floatplane dock (Harbour Air, Coal Harbour / YVR South): timber float
    with a little white terminal shed, and a DHC-2 Beaver on floats moored
    alongside in white with blue."""
    b = Building(1, 1)
    b.extra_top = 3.0
    b.bx(1.0, 15.0, 1.0, 4.0, 0.0, 0.7, "timber")                  # float
    b.sol(lambda X, Y, Z: (X > 1.0) & (X < 15.0) & (Y > 1.0) & (Y < 4.0) & (Z > 0.6) & (Z <= 0.7) &
          (np.mod(X, 0.8) < 0.08), "piling", 1.0, 15.0)
    b.bx(2.0, 6.5, 1.3, 3.8, 0.7, 3.8, "white")                   # shed
    b.bx(1.8, 6.7, 1.1, 4.0, 3.8, 4.2, "harbourblue")
    b.bx(3.2, 5.2, 3.78, 3.82, 0.9, 2.8, "glass")
    for x in (1.2, 14.6):
        b.bx(x - 0.2, x + 0.2, 0.6, 1.0, 0.0, 3.0, "piling")
    rng = np.random.RandomState(251)
    _people(b, 3, 7.5, 14.0, 1.6, 3.4, 0.7, rng)
    # Beaver on floats, nose towards +X
    fz = 0.5
    for y in (8.6, 11.4):
        b.sol(lambda X, Y, Z, y=y: (X > 4.5) & (X < 12.5) & (np.abs(Y - y) < 0.35) & (Z <= fz + 0.5) &
              (Z > 0.0) & (Z <= fz + 0.5 - 0.6 * np.clip((X - 11.4) / 1.1, 0, 1)), "silver", 4.5, 12.5)
        for x in (7.0, 10.0):
            b.bx(x - 0.06, x + 0.06, y - 0.06, y + 0.06, fz + 0.5, fz + 2.0, "steel")
    b.sol(lambda X, Y, Z: (X > 5.0) & (X < 12.0) & (np.abs(Y - 10.0) < 0.8 - 0.5 * np.clip((7.0 - X) / 2.0, 0, 1)) &
          (np.abs(Z - (fz + 2.6)) < 0.75), "white", 5.0, 12.0)              # fuselage
    b.bx(5.0, 12.0, 9.18, 10.82, fz + 2.3, fz + 2.6, "harbourblue")         # cheatline
    b.bx(9.6, 11.0, 9.15, 10.85, fz + 2.9, fz + 3.3, "window")
    b.bx(8.6, 10.2, 4.6, 15.4, fz + 3.35, fz + 3.6, "white")                # high wing
    b.bx(8.6, 10.2, 4.6, 5.0, fz + 3.35, fz + 3.6, "harbourblue")
    b.bx(8.6, 10.2, 15.0, 15.4, fz + 3.35, fz + 3.6, "harbourblue")
    b.bx(4.3, 5.3, 9.9, 10.1, fz + 2.6, fz + 4.2, "harbourblue")            # fin
    b.bx(4.6, 5.6, 8.6, 11.4, fz + 2.6, fz + 2.8, "white")
    b.bx(12.0, 12.4, 9.5, 10.5, fz + 2.2, fz + 3.0, "acblack")              # cowling
    b.bx(12.4, 12.5, 8.8, 11.2, fz + 2.5, fz + 2.7, "acblack")              # prop
    return b
