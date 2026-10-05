"""Render the waterfront objects to gfx/ (sprite sheets + objects.json).
src/build_coastal.py makes coastal-waterfront.grf from them.

Usage: python src/make_coastal.py [--preview out.png] [ids...]
"""
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
REPO = os.path.dirname(ROOT)
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(REPO, "common"))
sys.path.insert(0, os.path.join(REPO, "terminals", "src"))
from render import save_sheet_8, save_sheet_32  # noqa: E402
from make_objects import at_zoom, preview  # noqa: E402
import buildings  # noqa: E402
import waterfront as WF  # noqa: E402

buildings.DETAIL = False          # classic OpenTTD sprite style for this set

GFX = os.path.join(ROOT, "gfx")

# Order = object ID: append only!
OBJECTS = [
    dict(id="floathome", name="Float home", models=[lambda v=v: WF.float_home(v) for v in range(4)],
         size=(1, 1), views=4, year=1960, height=4, cost=3, water=True, cls="vic"),
    dict(id="fishchips", name="Fish & chips float", models=[WF.fish_and_chips], size=(1, 1), views=4,
         year=1985, height=3, cost=3, water=True, cls="vic"),
    dict(id="fisgard", name="Fisgard Lighthouse", models=[WF.fisgard_lighthouse], size=(1, 1),
         views=4, year=1860, height=6, cost=4, cls="vic"),
    dict(id="publicmarket", name="Granville Island Public Market", models=[WF.public_market],
         size=(2, 2), views=4, year=1979, height=3, cost=8, cls="van"),
    dict(id="giants", name="Ocean Concrete 'Giants' silos", models=[WF.giants_silos], size=(2, 1),
         views=2, year=2014, height=7, cost=6, cls="van"),
    dict(id="artisanshed", name="Artisan shed", models=[lambda v=v: WF.artisan_shed(v) for v in range(4)],
         size=(1, 1), views=4, year=1979, height=3, cost=2, cls="van"),
    dict(id="seawall", name="Seawall promenade", models=[lambda: WF.seawall(0), lambda: WF.seawall(1)],
         size=(1, 1), views=4, year=1971, height=3, cost=2, cls="van"),
    dict(id="dockwalk", name="Floating dock walkway", models=[lambda: WF.dock_walk(0), lambda: WF.dock_walk(1)],
         size=(1, 1), views=2, year=1950, height=1, cost=1, water=True, cls="dock"),
    dict(id="marina", name="Marina slips", models=[lambda: WF.marina_slips(0), lambda: WF.marina_slips(1)],
         size=(1, 1), views=4, year=1950, height=4, cost=2, water=True, cls="dock"),
    dict(id="ferrydock", name="Harbour ferry dock", models=[WF.ferry_dock], size=(1, 1), views=4,
         year=1985, height=2, cost=2, water=True, cls="dock"),
    dict(id="pilepier", name="Timber pile pier", models=[WF.pile_pier], size=(1, 1), views=2,
         year=1900, height=1, cost=1, water=True, cls="dock"),
    dict(id="legislature", name="BC Parliament Buildings", models=[WF.legislature], size=(3, 2),
         views=4, year=1897, height=6, cost=12, cls="vic"),
]
# cls -> (class label, unused, class name)
CLASSES = {"vic": ("CWVI", None, "Waterfront: Victoria"),
           "van": ("CWVA", None, "Waterfront: Vancouver"),
           "dock": ("CWDK", None, "Waterfront: docks & marinas")}


def main():
    args = sys.argv[1:]
    pv = None
    if "--preview" in args:
        i = args.index("--preview")
        pv = args[i + 1]
        del args[i:i + 2]
    os.makedirs(GFX, exist_ok=True)
    mpath = os.path.join(GFX, "objects.json")
    meta = json.load(open(mpath)) if os.path.exists(mpath) else {}
    for obj in OBJECTS:
        if args and obj["id"] not in args:
            continue
        t = time.time()
        meta[obj["id"]] = {"variants": []}
        for vi, model in enumerate(obj["models"]):
            m = model()
            m.style = "classic"
            m.zscale = 2.0
            rendered = m.render_object(views=range(obj["views"]))
            vmeta = {}
            for view, tiles in rendered.items():
                base = os.path.join(GFX, "obj_%s_%d_v%d" % (obj["id"], vi, view))
                z1, z2, z4 = at_zoom(tiles, 1), at_zoom(tiles, 2), at_zoom(tiles, 4)
                vmeta[str(view)] = {"tiles": [[tx, ty] for tx, ty, *_ in tiles],
                                    "8bpp": save_sheet_8(z1, base + ".png"),
                                    "1x": save_sheet_32(z1, base + "_1x.png"),
                                    "2x": save_sheet_32(z2, base + "_2x.png"),
                                    "4x": save_sheet_32(z4, base + "_4x.png")}
            meta[obj["id"]]["variants"].append(vmeta)
            if pv and vi == 0:
                preview(rendered, pv.replace(".png", "_%s.png" % obj["id"]))
        print("rendered %-14s %.1fs" % (obj["id"], time.time() - t), flush=True)
    json.dump(meta, open(mpath, "w"), indent=1)


if __name__ == "__main__":
    main()
