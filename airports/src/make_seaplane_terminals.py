"""Render the TGTFTD seaplane terminals (src/seaplane_terminals.py), cut them into tiles, and save
the tile sprites as 8bpp sheets gfx/sea_<scene>_r<rotation>[_8bpp_2x|_8bpp_4x].png with
gfx/seaplane_terminals.json. src/build_airports.py adds them to bc-airports.grf.

Usage: python src/make_seaplane_terminals.py [scene ...]       (needs scipy)
"""
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "common"))
from newgrf.sprites import save_sheet  # noqa: E402

GFX = os.path.join(ROOT, "gfx")

# Airport ID, scene, name, substitute airport (05 Commuter, 04 International), first year, TGTFTD
# airport_seaplane_terminal value (2 = seaplane dock: 1x2, one berth, no hangar; 3 = kerb dock;
# 4 = kerb terminal with hangar; 5 = large kerb terminal).
AIRPORTS = [
    (0, "victoria_kerb", "Victoria Harbour Seaplane Terminal", 0x05, 1950, 4),
    (1, "vancouver_kerb", "Vancouver (Coal Harbour) Seaplane Terminal", 0x04, 1950, 5),
    (2, "dock", "Wooden Seaplane Dock", 0x00, 1920, 2),
    (3, "nanaimo", "Nanaimo Harbour Flight Centre", 0x00, 1950, 3),
]
ROTATABLE = {2, 3}  # docks come in all four rotations, so the open water for landing can be on any side


def rotations(kind):
    return range(4) if kind in ROTATABLE else [0]


def main():
    from seaplane_terminals import SCENES
    from seaplane_tiles import cut

    only = sys.argv[1:]
    os.makedirs(GFX, exist_ok=True)
    path = os.path.join(GFX, "seaplane_terminals.json")
    meta = json.load(open(path)) if os.path.exists(path) else {}
    for _, scene_name, _, _, _, kind in AIRPORTS:
        if only and scene_name not in only:
            continue
        t = time.time()
        meta[scene_name] = []
        for rot in rotations(kind):
            scene = SCENES[scene_name](rot) if kind in ROTATABLE else SCENES[scene_name]()
            tiles = cut(scene)
            sprites, layout = [], []
            for ty in range(scene.size[1]):          # cut() order: row by row
                for tx in range(scene.size[0]):
                    tg = tiles[(tx, ty)]
                    if tg is None:
                        continue
                    entry = [tx, ty, None, None, tg.height]
                    for k, levels in ((2, tg.ground), (3, tg.building)):
                        if levels is not None:
                            entry[k] = len(sprites)
                            sprites.append(levels)
                    layout.append(entry)
            base = os.path.join(GFX, "sea_%s_r%d" % (scene_name, rot))
            meta[scene_name].append({
                "rotation": rot, "size": list(scene.size), "tiles": layout,
                "8bpp": save_sheet([s[1] for s in sprites], base + ".png", 8),
                "8bpp_2x": save_sheet([s[2] for s in sprites], base + "_8bpp_2x.png", 8),
                "8bpp_4x": save_sheet([s[4] for s in sprites], base + "_8bpp_4x.png", 8),
            })
        print("rendered %-14s %.1fs" % (scene_name, time.time() - t), flush=True)
    with open(path, "w") as f:
        json.dump(meta, f, indent=1)


if __name__ == "__main__":
    main()
