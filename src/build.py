"""
Build pnw_aviation.grf (PNW Aviation): Harbour Air seaplanes, the Helijet S-76 and the Victoria / Vancouver
seaplane terminals for TGTFTD.

    python build.py [output.grf]

Needs Python 3.10+, numpy, scipy and Pillow. Writes the GRF to ../build/.
"""

import datetime
import struct
import sys
import time
from pathlib import Path

import numpy as np

from aircraft import MODELS, s76_rotor
from grf import GRFWriter, RealSprite, b, w, d, ext, text
from sprites import aircraft_sprites, rotor_sprites
from terminals import SCENES
from tiles import cut

GRFID = b"HAS\x01"
VERSION = 2
NAME = "PNW Aviation"
DESCRIPTION = (
    "{BLUE}PNW Aviation{}{BLACK}Pacific Northwest aircraft: DHC-2 Beaver, DHC-3T Turbo Otter, DHC-6 Twin Otter and "
    "Cessna 208B Grand Caravan EX seaplanes in Harbour Air livery, the Sikorsky S-76 helicopter in Helijet livery, "
    "the Victoria Harbour and Vancouver (Coal Harbour) seaplane terminals and a small wooden seaplane dock. "
    "{}{ORANGE}The seaplanes and terminals need TGTFTD; without it they are hidden. The S-76 works everywhere."
)

FEAT_AIRCRAFT = 0x03
FEAT_AIRPORTS = 0x0D
FEAT_AIRPORTTILES = 0x11

PROP_AIRCRAFT_IS_SEAPLANE = 0xF0
PROP_AIRPORT_SEAPLANE_TERMINAL = 0xF1
BIT_AIRCRAFT_MAPPED = 4
BIT_AIRPORT_MAPPED = 5

SFX_TAKEOFF_PROPELLER = 0x08
SFX_TAKEOFF_JET = 0x09  # used by the default helicopters
SPR_FLAT_WATER_TILE = 0x0FDD


def days_since_1920(y, m=1, day=1):
    return (datetime.date(y, m, day) - datetime.date(1920, 1, 1)).days


def mph(speed):
    """Aircraft speed property: 1 unit = 8 mph."""
    return round(speed / 8)


# Engine ID, model, name, introduction, passengers, game speed in mph (boosted to ~200 mph for playability; real cruise 180-296 km/h), mail bags, cost, running cost, vehicle life.
AIRCRAFT = [
    (0x60, "beaver", "DHC-2 Beaver (Harbour Air)", (1948, 4, 1), 6, 184, 1, 8, 30, 40),
    (0x61, "turbo_otter", "DHC-3T Turbo Otter (Harbour Air)", (1980, 6, 1), 14, 192, 2, 14, 50, 40),
    (0x62, "twin_otter", "DHC-6 Twin Otter (Harbour Air)", (1966, 1, 1), 19, 216, 3, 22, 80, 35),
    (0x63, "grand_caravan", "Cessna 208B Grand Caravan EX (Harbour Air)", (2013, 1, 1), 9, 208, 2, 18, 55, 30),
]

# Helicopters (normal aircraft, any airport or heliport; not seaplanes). Same fields as AIRCRAFT.
HELICOPTERS = [
    (0x64, "s76", "Sikorsky S-76 (Helijet)", (1979, 2, 1), 12, 200, 2, 16, 75, 30),
]

# Airport local ID, scene, name, substitute airport (05 Commuter, 04 International), first year,
# airport_seaplane_terminal value: 1 = seaplane version of the substitute, 2 = TGTFTD seaplane dock (1x2, one berth, no hangar).
AIRPORTS = [
    (0, "victoria", "Victoria Harbour Seaplane Terminal", 0x05, 1950, 1),
    (1, "vancouver", "Vancouver (Coal Harbour) Seaplane Terminal", 0x04, 1950, 1),
    (2, "dock", "Wooden Seaplane Dock", 0x00, 1920, 2),
]
BIT_SEAPLANE_DOCKS = 6  # bit of global variable 9D: TGTFTD seaplanes feature version >= 2 (seaplane docks)
AIRPORT_NAME_TEXT = 0xDC00


def a14_text(chunk_id: bytes, value: str) -> bytes:
    return b"T" + chunk_id + b"\x7f" + text(value)


def a14_binary(chunk_id: bytes, data: bytes) -> bytes:
    return b"B" + chunk_id + w(len(data)) + data


def a14_property_mapping(name, feature, prop, success_bit):
    return (b"C" + b"A0PM" + b"T" + b"NAME" + b"\x00" + text(name)
            + a14_binary(b"FEAT", bytes([feature])) + a14_binary(b"PROP", bytes([prop]))
            + a14_binary(b"SETT", bytes([success_bit])) + b"\x00")


def skip_if_bit(variable, bit, is_set, num_sprites):
    """Action 7: skip num_sprites if the bit of the global variable is set (is_set=True) or clear (is_set=False)."""
    return b(0x07, variable, 0x01, 0x00 if is_set else 0x01, bit, num_sprites)


def build(out_path: Path, vanilla_test: bool = False):
    """vanilla_test: keep aircraft and terminals (as land airports) without TGTFTD, for checking graphics in stock OpenTTD."""
    t0 = time.time()
    g = GRFWriter()

    # Static information first (the file scan stops at Action 8), then Action 8.
    g.pseudo(b(0x14) + b"C" + b"INFO" + a14_binary(b"PALS", b"D") + a14_binary(b"VRSN", d(VERSION))
             + a14_binary(b"MINV", d(VERSION)) + b"\x00" + b"\x00")
    g.pseudo(b(0x08, 0x08) + GRFID + text(NAME) + text(DESCRIPTION))
    # Map the TGTFTD properties; each mapping sets a bit of global variable 8D when it succeeds.
    g.pseudo(b(0x14)
             + a14_property_mapping("aircraft_is_seaplane", FEAT_AIRCRAFT, PROP_AIRCRAFT_IS_SEAPLANE, BIT_AIRCRAFT_MAPPED)
             + a14_property_mapping("airport_seaplane_terminal", FEAT_AIRPORTS, PROP_AIRPORT_SEAPLANE_TERMINAL, BIT_AIRPORT_MAPPED)
             # Feature test: set bit BIT_SEAPLANE_DOCKS of variable 9D if TGTFTD seaplanes version >= 2 (seaplane docks).
             + b"C" + b"FTST" + b"T" + b"NAME" + b"\x00" + text("tgtftd_seaplanes")
             + a14_binary(b"MINV", w(2)) + a14_binary(b"SETP", bytes([BIT_SEAPLANE_DOCKS])) + b"\x00"
             + b"\x00")

    # ------------------------------------------------------------------ aircraft
    for eid, model, name, intro, pax, speed, mail, cost, running, life in AIRCRAFT:
        props = [
            b(0x00) + w(days_since_1920(*intro)),
            b(0x02, 20),           # reliability decay
            b(0x03, life),         # vehicle life (years)
            b(0x04, 255),          # model life (years)
            b(0x06, 0x0F),         # all climates
            b(0x07, 5),            # loading speed
            b(0x08, 0xFF),         # new graphics
            b(0x09, 0x02),         # plane, not helicopter
            b(0x0A, 0x00),         # small: safe at short-strip terminals
            b(0x0B, cost),
            b(0x0C, mph(speed)),
            b(0x0D, 18),           # acceleration
            b(0x0E, running),
            b(0x0F) + w(pax),
            b(0x11, mail),
            b(0x12, SFX_TAKEOFF_PROPELLER),
        ]
        g.pseudo(b(0x00, FEAT_AIRCRAFT, len(props), 1) + ext(eid) + b"".join(props))
        g.pseudo(b(0x04, FEAT_AIRCRAFT, 0x7F, 1) + ext(eid) + text(name))

    print("rendering aircraft ...")
    g.pseudo(b(0x01, FEAT_AIRCRAFT, len(AIRCRAFT), 8))
    for _, model, *_ in AIRCRAFT:
        for s in aircraft_sprites(MODELS[model]()):
            g.real(s)
    for i, (eid, *_rest) in enumerate(AIRCRAFT):
        # Basic vehicle sprite group: one sprite set, loaded and loading.
        g.pseudo(b(0x02, FEAT_AIRCRAFT, i, 1, 1) + w(i) + w(i))
        g.pseudo(b(0x03, FEAT_AIRCRAFT, 1) + ext(eid) + b(0) + w(i))

    first = AIRCRAFT[0][0]
    n = len(AIRCRAFT)
    # TGTFTD: make them seaplanes. Otherwise: hide them (no climates).
    g.pseudo(skip_if_bit(0x8D, BIT_AIRCRAFT_MAPPED, False, 1))
    g.pseudo(b(0x00, FEAT_AIRCRAFT, 1, n) + ext(first) + b(PROP_AIRCRAFT_IS_SEAPLANE) + b(0x01, 0x01) * n)
    if not vanilla_test:
        g.pseudo(skip_if_bit(0x8D, BIT_AIRCRAFT_MAPPED, True, 1))
        g.pseudo(b(0x00, FEAT_AIRCRAFT, 1, n) + ext(first) + b(0x06) + b(0x00) * n)

    # ------------------------------------------------------------------ helicopters
    for eid, model, name, intro, pax, speed, mail, cost, running, life in HELICOPTERS:
        props = [
            b(0x00) + w(days_since_1920(*intro)),
            b(0x02, 20), b(0x03, life), b(0x04, 255), b(0x06, 0x0F), b(0x07, 5),
            b(0x08, 0xFF),         # new graphics
            b(0x09, 0x00),         # helicopter
            b(0x0B, cost),
            b(0x0C, mph(speed)),
            b(0x0D, 20),
            b(0x0E, running),
            b(0x0F) + w(pax),
            b(0x11, mail),
            b(0x12, SFX_TAKEOFF_JET),
        ]
        g.pseudo(b(0x00, FEAT_AIRCRAFT, len(props), 1) + ext(eid) + b"".join(props))
        g.pseudo(b(0x04, FEAT_AIRCRAFT, 0x7F, 1) + ext(eid) + text(name))
    print("rendering helicopters ...")
    for eid, model, *_ in HELICOPTERS:
        # Body: one set of 8 directions.
        g.pseudo(b(0x01, FEAT_AIRCRAFT, 1, 8))
        for s in aircraft_sprites(MODELS[model]()):
            g.real(s)
        g.pseudo(b(0x02, FEAT_AIRCRAFT, 0, 1, 1) + w(0) + w(0))
        g.pseudo(b(0x03, FEAT_AIRCRAFT, 1) + ext(eid) + b(0) + w(0))
        # Rotor: a "wagon override" of the helicopter with itself; frame 0 = stopped, 1-3 = turning.
        g.pseudo(b(0x01, FEAT_AIRCRAFT, 1, 4))
        for s in rotor_sprites([s76_rotor(45, 0.42), s76_rotor(15, 0.30), s76_rotor(45, 0.30), s76_rotor(75, 0.30)]):
            g.real(s)
        g.pseudo(b(0x02, FEAT_AIRCRAFT, 1, 1, 1) + w(0) + w(0))
        g.pseudo(b(0x03, FEAT_AIRCRAFT, 0x81) + ext(eid) + b(0) + w(1))

    # ------------------------------------------------------------------ terminals
    print("rendering terminals ...")
    # A seaplane dock has no land equivalent; the vanilla test build leaves it out.
    airports = [a for a in AIRPORTS if not (vanilla_test and a[5] == 2)]
    tile_ids = {}          # id(TileGraphics) -> local airport tile ID
    tile_list = []         # TileGraphics in ID order
    layouts = {}
    for local_id, scene_name, *_ in airports:
        scene = SCENES[scene_name]()
        cut_tiles = cut(scene)
        layouts[local_id] = (scene.size, cut_tiles)
        for t in cut_tiles.values():
            if t is not None:
                tile_ids[id(t)] = len(tile_list)
                tile_list.append(t)

    # Airport tiles: substitute = default tile 00 (apron), no animation.
    g.pseudo(b(0x00, FEAT_AIRPORTTILES, 1, len(tile_list)) + ext(0) + b(0x08) + b(0x00) * len(tile_list))

    # One sprite set per sprite.
    sets = []
    for t in tile_list:
        for s in (t.ground, t.building):
            if s is not None:
                sets.append(s)
    sprite_set = {id(s): i for i, s in enumerate(sets)}
    g.pseudo(b(0x01, FEAT_AIRPORTTILES, 0x00) + ext(0) + ext(len(sets)) + ext(1))
    for s in sets:
        g.real(s)

    # Action 2 sprite layouts and Action 3 per tile. Group IDs are reused in blocks of 250.
    for tid, t in enumerate(tile_list):
        group = tid % 250
        parts = []
        if t.ground is not None:
            # Child sprite before any parent sprite: drawn as a ground overlay on top of the water.
            parts.append(w(sprite_set[id(t.ground)]) + w(0x8000) + b(0, 0, 0x80))
        if t.building is not None:
            parts.append(w(sprite_set[id(t.building)]) + w(0x8000) + b(0, 0, 0) + b(16, 16, t.height))
        g.pseudo(b(0x02, FEAT_AIRPORTTILES, group, len(parts)) + w(SPR_FLAT_WATER_TILE) + w(0) + b"".join(parts))
        g.pseudo(b(0x03, FEAT_AIRPORTTILES, 1) + ext(tid) + b(0) + w(group))

    for local_id, _, name, *_ in airports:
        g.pseudo(b(0x04, FEAT_AIRPORTS, 0xFF, 1) + w(AIRPORT_NAME_TEXT + local_id) + text(name))

    if not vanilla_test:
        # Without TGTFTD skip all airports; docks additionally need feature version 2 (one more Action 7 each).
        n_sprites = sum(2 if a[5] == 2 else 1 for a in airports)
        g.pseudo(skip_if_bit(0x8D, BIT_AIRPORT_MAPPED, False, n_sprites))
    for local_id, scene_name, name, substitute, year, kind in airports:
        (sx, sy), cut_tiles = layouts[local_id]
        layout = bytearray(b(0x00))  # rotation: north
        for ty in range(sy):
            for tx in range(sx):
                t = cut_tiles[(tx, ty)]
                if t is None:
                    layout += b(tx, ty, 0x00)  # default tile: drawn as plain water on a seaplane terminal
                else:
                    layout += b(tx, ty, 0xFE) + w(tile_ids[id(t)])
        layout += b(0x00, 0x80)
        props = [
            b(0x08, substitute),
            b(PROP_AIRPORT_SEAPLANE_TERMINAL, 0x01, kind) if not vanilla_test else b(0x0E, 4),
            b(0x0A, 1) + d(len(layout)) + bytes(layout),
            b(0x0C) + w(year) + w(0xFFFF),
            b(0x10) + w(AIRPORT_NAME_TEXT + local_id),
        ]
        if kind == 2 and not vanilla_test:
            g.pseudo(skip_if_bit(0x9D, BIT_SEAPLANE_DOCKS, False, 1))
        g.pseudo(b(0x00, FEAT_AIRPORTS, len(props), 1) + ext(local_id) + b"".join(props))

    data = g.build()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    print(f"wrote {out_path} ({len(data) / 1024:.0f} KiB, {len(tile_list)} airport tiles, {len(sets)} tile sprites) in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    default = Path(__file__).resolve().parent.parent / "build" / "pnw_aviation.grf"
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    build(Path(args[0]) if args else default, vanilla_test="--vanilla-test" in sys.argv)
