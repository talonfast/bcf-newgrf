"""Render the terminal objects to gfx/obj_<id>_v<view>[_1x|_2x|_4x].png and
write gfx/objects.json (per view: tile order + sprite sheet entries).

Usage: python src/make_objects.py [--preview out.png]
"""
import json
import os
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "common"))
from render import ZOOM, downsample, save_sheet_8, save_sheet_32  # noqa: E402
from buildings import (quay_market, terminal_building, toll_plaza, holding_lanes,  # noqa: E402
                       berth_ramp, wingwall, walkway, control_tower, bus_shelter, foot_plaza,
                       walkway_tower, sb_terminal, sb_landsend, sb_tower, sb_footbridge,
                       sb_bridgetower, sb_wingwall, sb_ramp, island_forest, island_gantry,
                       island_wingwall, island_trestle, island_dolphin, island_booth, the_stand)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GFX = os.path.join(ROOT, "gfx")

# Order = object ID: append only! views: rotations offered in the build menu.
# variants: picked per tile at random (random_bits). water: built on water.
OBJECTS = [
    dict(id="quaymarket", name="Tsawwassen Quay Market", models=[quay_market], size=(2, 1),
         views=4, year=2009, height=2, cost=6),
    dict(id="terminal", name="Ferry terminal building", models=[terminal_building],
         size=(2, 2), views=4, year=1960, height=3, cost=8),
    dict(id="tollplaza", name="Toll plaza", models=[toll_plaza], size=(1, 1), views=2,
         year=1960, height=3, cost=3),
    dict(id="holding", name="Vehicle holding lanes",
         models=[lambda: holding_lanes(0), lambda: holding_lanes(1)], size=(1, 1), views=2,
         year=1960, height=1, cost=1),
    dict(id="berthramp", name="Berth ramp and towers", models=[berth_ramp], size=(1, 1),
         views=4, year=1960, height=4, cost=5),
    dict(id="wingwall", name="Berth wingwall and dolphin", models=[wingwall], size=(1, 1),
         views=4, year=1960, height=1, cost=3, water=True),
    dict(id="walkway", name="Passenger walkway", models=[walkway], size=(1, 1), views=2,
         year=1960, height=2, cost=3),
    dict(id="ctltower", name="Terminal control tower", models=[control_tower], size=(1, 1),
         views=1, year=1960, height=4, cost=4),
    dict(id="busshelter", name="Foot passenger and bus shelter", models=[bus_shelter],
         size=(1, 1), views=4, year=1960, height=1, cost=2),
    dict(id="footplaza", name="Foot passenger plaza",
         models=[lambda: foot_plaza(0), lambda: foot_plaza(1)], size=(1, 1), views=1,
         year=1960, height=1, cost=2),
    dict(id="walkwaytower", name="Walkway stair tower", models=[walkway_tower], size=(1, 1),
         views=4, year=1960, height=2, cost=3),
    # ---- Swartz Bay -------------------------------------------------------
    dict(id="sbterminal", name="Departures / Arrivals building", models=[sb_terminal],
         size=(2, 1), views=4, year=1960, height=2, cost=6, cls="sb"),
    dict(id="sblandsend", name="Lands End cafe and market tent", models=[sb_landsend],
         size=(2, 1), views=4, year=1960, height=2, cost=5, cls="sb"),
    dict(id="sbtower", name="Traffic tower and playground", models=[sb_tower], size=(1, 1),
         views=4, year=1960, height=3, cost=4, cls="sb"),
    dict(id="sbfootbridge", name="Foot passenger bridge (open truss)", models=[sb_footbridge],
         size=(1, 1), views=2, year=1960, height=2, cost=3, cls="sb"),
    dict(id="sbbridgetower", name="Foot bridge tower and gangway", models=[sb_bridgetower],
         size=(1, 1), views=4, year=1960, height=4, cost=4, cls="sb"),
    dict(id="sbwingwall", name="Berth wall (blue and orange fenders)", models=[sb_wingwall],
         size=(1, 1), views=4, year=1960, height=1, cost=3, water=True, cls="sb"),
    dict(id="sbramp", name="Berth ramp gantry (lattice)", models=[sb_ramp], size=(1, 1),
         views=4, year=1960, height=3, cost=5, cls="sb"),
    # ---- Southern Gulf Islands --------------------------------------------
    dict(id="islgantry", name="Island ramp towers (Otter Bay)", models=[island_gantry],
         size=(1, 1), views=4, year=1960, height=3, cost=4, cls="isl"),
    dict(id="islwingwall", name="Island berth wall (red fenders)", models=[island_wingwall],
         size=(1, 1), views=4, year=1960, height=1, cost=2, water=True, cls="isl"),
    dict(id="isltrestle", name="Timber trestle pier", models=[island_trestle], size=(1, 1),
         views=2, year=1960, height=1, cost=2, water=True, cls="isl"),
    dict(id="isldolphin", name="Timber pile dolphins", models=[island_dolphin], size=(1, 1),
         views=1, year=1960, height=1, cost=1, water=True, cls="isl"),
    dict(id="islbooth", name="Island ticket booth", models=[island_booth], size=(1, 1),
         views=4, year=1960, height=3, cost=2, cls="isl"),
    dict(id="thestand", name="The Stand (Otter Bay)", models=[the_stand], size=(1, 1),
         views=4, year=1990, height=3, cost=2, cls="isl"),
    dict(id="islforest", name="Gulf Islands forest",
         models=[lambda: island_forest(0), lambda: island_forest(1), lambda: island_forest(2)],
         size=(1, 1), views=1, year=1900, height=4, cost=1, cls="isl"),
]


def at_zoom(tiles, zoom):
    f = ZOOM // zoom
    return [(downsample(rgba, f), x0 // f, y0 // f) for _, _, rgba, x0, y0 in tiles]


def preview(rendered, path):
    """All four views assembled on a grass/concrete patch, at 2x."""
    canvas = Image.new("RGBA", (1600, 520), (92, 130, 70, 255))
    for k, view in enumerate(sorted(rendered)):
        cx, cy = 200 + k * 400, 200
        for (tx, ty, rgba, x0, y0) in sorted(rendered[view], key=lambda t: t[0] + t[1]):
            r = downsample(rgba, 2)
            im = Image.fromarray(np.dstack([np.clip(r[..., :3], 0, 255),
                                            np.clip(r[..., 3] * 255, 0, 255)]).astype(np.uint8))
            # tile north corner on screen (2x zoom): x = 2*(y-x)*2, y = (x+y)*2
            nx, ny = cx + (ty - tx) * 64, cy + (tx + ty) * 32
            canvas.alpha_composite(im, (nx + x0 // 2, ny + y0 // 2))
    canvas.save(path)


def main():
    pv = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
    only = [a for a in sys.argv[1:] if not a.startswith("--") and a != pv]
    os.makedirs(GFX, exist_ok=True)
    mpath = os.path.join(GFX, "objects.json")
    meta = json.load(open(mpath)) if os.path.exists(mpath) else {}
    for obj in OBJECTS:
        if only and obj["id"] not in only:
            continue
        t = time.time()
        meta[obj["id"]] = {"variants": []}
        for vi, model in enumerate(obj["models"]):
            rendered = model().render_object(views=range(obj["views"]))
            vmeta = {}
            for view, tiles in rendered.items():
                base = os.path.join(GFX, "obj_%s_%d_v%d" % (obj["id"], vi, view))
                z1, z2, z4 = at_zoom(tiles, 1), at_zoom(tiles, 2), at_zoom(tiles, 4)
                vmeta[str(view)] = {
                    "tiles": [[tx, ty] for tx, ty, *_ in tiles],
                    "8bpp": save_sheet_8(z1, base + ".png"),
                    "1x": save_sheet_32(z1, base + "_1x.png"),
                    "2x": save_sheet_32(z2, base + "_2x.png"),
                    "4x": save_sheet_32(z4, base + "_4x.png"),
                }
            meta[obj["id"]]["variants"].append(vmeta)
            if pv and vi == 0:
                preview(rendered, pv.replace(".png", "_%s.png" % obj["id"]))
        print("rendered %-18s %.1fs" % (obj["id"], time.time() - t), flush=True)
    json.dump(meta, open(mpath, "w"), indent=1)


if __name__ == "__main__":
    main()
