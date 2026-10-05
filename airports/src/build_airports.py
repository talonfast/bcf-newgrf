"""Build bc-airports.grf: the airport objects of src/make_airports.py and the TGTFTD seaplane
terminals of src/make_seaplane_terminals.py, from the rendered gfx/.

Usage: python src/build_airports.py [output.grf] [--vanilla-test]

--vanilla-test keeps the kerb terminals without TGTFTD (as land airports, leaving out the docks),
to check their graphics in a stock OpenTTD.
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "common"))
from make_airports import CLASSES, OBJECTS  # noqa: E402
from make_seaplane_terminals import AIRPORTS  # noqa: E402
from newgrf import GRF, cli  # noqa: E402
from newgrf import actions as A  # noqa: E402
from newgrf import tgtftd as T  # noqa: E402
from newgrf.objects import GROUND_WATER, add_objects, load_meta  # noqa: E402
from newgrf.sprites import sheet_sprites  # noqa: E402

VERSION = 3
NAME = "BC Aviation: Airports {SILVER}v%d" % VERSION
DESCRIPTION = (
    "Landmarks to dress OpenTTD airports as YVR and YYJ: control towers, terminal halls, jet bridges, "
    "parkade, apron service equipment and a Harbour Air floatplane dock. Use with BC Aviation: Aircraft."
    "{}{}Seaplane terminals for TGTFTD: Victoria Harbour, Vancouver (Coal Harbour), Nanaimo Harbour Flight "
    "Centre and a small wooden seaplane dock.{}{ORANGE}The seaplane terminals need TGTFTD; without it they "
    "are hidden.")

AIRPORT_NAME_TEXT = 0xDC00
# Terminal kind -> bit of global variable 9D it needs (seaplane docks: version 2, kerb docks: version 3).
FEATURE_BIT = {2: T.BIT_SEAPLANE_DOCKS, 3: T.BIT_SEAPLANE_KERB_DOCKS, 4: T.BIT_SEAPLANE_KERB_DOCKS,
               5: T.BIT_SEAPLANE_KERB_DOCKS}


def add_seaplane_terminals(grf, meta, vanilla_test):
    gfx = os.path.join(ROOT, "gfx")
    # A seaplane dock has no land equivalent; the vanilla test build leaves it out.
    airports = [a for a in AIRPORTS if not (vanilla_test and a[5] >= 2)]
    tiles = []           # (ground set or None, building set or None, height), by airport tile ID
    sprites = []
    layouts = {}         # airport ID -> [(rotation, (w, h), {(tx, ty): tile ID})]
    for local_id, scene_name, _, _, _, kind in airports:
        layouts[local_id] = []
        for rot_meta in meta[scene_name]:
            sheet = sheet_sprites(os.path.join(gfx, "sea_%s_r%d" % (scene_name, rot_meta["rotation"])),
                                  {k: rot_meta[k] for k in ("8bpp", "8bpp_2x", "8bpp_4x")})
            base = len(sprites)
            sprites += sheet
            ids = {}
            for tx, ty, ground, building, height in rot_meta["tiles"]:
                ids[(tx, ty)] = len(tiles)
                tiles.append((None if ground is None else base + ground,
                              None if building is None else base + building, height))
            layouts[local_id].append((rot_meta["rotation"] * 2, tuple(rot_meta["size"]), ids))  # N=0 E=2 S=4 W=6

    # Airport tiles: substitute = default tile 00 (apron), no animation.
    grf.add(A.action0(A.AIRPORTTILES, 0, [(0x08, A.b(0x00) * len(tiles))], count=len(tiles)))
    grf.add(A.action1(A.AIRPORTTILES, len(sprites), 1))
    for s in sprites:
        grf.sprite(s)
    # A sprite layout and action 3 per tile; set IDs are reused in blocks of 250.
    for tid, (ground, building, height) in enumerate(tiles):
        group = tid % 250
        parts = []
        if ground is not None:
            # Child sprite before any parent sprite: drawn as a ground overlay on top of the water.
            parts.append(A.w(ground) + A.w(0x8000) + A.b(0, 0, 0x80))
        if building is not None:
            parts.append(A.w(building) + A.w(0x8000) + A.b(0, 0, 0) + A.b(16, 16, height))
        grf.add(A.b(0x02, A.AIRPORTTILES, group, len(parts)) + A.w(GROUND_WATER) + A.w(0) + b"".join(parts))
        grf.add(A.action3(A.AIRPORTTILES, [tid], default=group))

    for local_id, _, name, *_ in airports:
        grf.add(A.b(0x04, A.AIRPORTS, 0xFF, 1) + A.w(AIRPORT_NAME_TEXT + local_id) + A.text(name))

    if not vanilla_test:
        # Without TGTFTD skip all airports; docks additionally need a feature version (one more Action 7 each).
        n_sprites = sum(2 if a[5] >= 2 else 1 for a in airports)
        grf.add(T.skip_if_bit(0x8D, T.BIT_AIRPORT_MAPPED, False, n_sprites))
    for local_id, scene_name, name, substitute, year, kind in airports:
        layout = bytearray()
        for rotation, (sx, sy), ids in layouts[local_id]:
            layout += A.b(rotation)
            for ty in range(sy):
                for tx in range(sx):
                    if (tx, ty) in ids:
                        layout += A.b(tx, ty, 0xFE) + A.w(ids[(tx, ty)])
                    else:
                        layout += A.b(tx, ty, 0x00)  # default tile: drawn as plain water on a seaplane terminal
            layout += A.b(0x00, 0x80)
        props = A.b(0x08, substitute)
        props += T.mapped(T.PROP_AIRPORT_SEAPLANE_TERMINAL, [A.b(kind)]) if not vanilla_test else A.b(0x0E, 4)
        props += A.b(0x0A, len(layouts[local_id])) + A.d(len(layout)) + bytes(layout)
        props += A.b(0x0C) + A.w(year) + A.w(0xFFFF)
        props += A.b(0x10) + A.w(AIRPORT_NAME_TEXT + local_id)
        if kind >= 2 and not vanilla_test:
            grf.add(T.skip_if_bit(0x9D, FEATURE_BIT[kind], False, 1))
        grf.add(A.b(0x00, A.AIRPORTS, 5, 1) + A.ext(local_id) + props)


def build(path, jobs=None, vanilla_test=False):
    grf = GRF("TFBY", NAME, DESCRIPTION, VERSION, 1)
    grf.add(T.action14(
        T.property_mapping("airport_seaplane_terminal", A.AIRPORTS, T.PROP_AIRPORT_SEAPLANE_TERMINAL,
                           T.BIT_AIRPORT_MAPPED),
        T.feature_test("tgtftd_seaplanes", 2, T.BIT_SEAPLANE_DOCKS),
        T.feature_test("tgtftd_seaplanes", 3, T.BIT_SEAPLANE_KERB_DOCKS)))
    add_objects(grf, OBJECTS, load_meta(os.path.join(ROOT, "gfx", "objects.json")), CLASSES,
                os.path.join(ROOT, "gfx"))
    with open(os.path.join(ROOT, "gfx", "seaplane_terminals.json")) as f:
        add_seaplane_terminals(grf, json.load(f), vanilla_test)
    grf.write(path, jobs)


if __name__ == "__main__":
    vanilla = "--vanilla-test" in sys.argv
    if vanilla:
        sys.argv.remove("--vanilla-test")
    out, jobs = cli.output(os.path.join(ROOT, "bc-airports.grf"))
    build(out, jobs, vanilla)
