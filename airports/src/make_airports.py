"""Render the airport objects to gfx/ (sprite sheets + objects.json). src/build_airports.py makes
bc-airports.grf from them (with the seaplane terminals of src/make_seaplane_terminals.py).

Usage: python src/make_airports.py [--preview out.png] [ids...]
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
import airport_buildings as AB  # noqa: E402

GFX = os.path.join(ROOT, "gfx")

# Order = object ID: append only!
OBJECTS = [
    dict(id="yvrtower", name="YVR control tower", models=[AB.yvr_tower], size=(1, 1), views=1,
         year=1996, height=6, cost=6, cls="yvr"),
    dict(id="yvrterminal", name="YVR terminal hall", models=[AB.yvr_terminal], size=(2, 2), views=4,
         year=1996, height=3, cost=8, cls="yvr"),
    dict(id="jetbridge", name="Jet bridge", models=[AB.jet_bridge], size=(1, 1), views=4,
         year=1970, height=2, cost=3, cls="yvr"),
    dict(id="parkade", name="Airport parkade", models=[AB.yvr_parkade], size=(2, 2), views=2,
         year=1970, height=2, cost=6, cls="yvr"),
    dict(id="yyjterminal", name="YYJ terminal", models=[AB.yyj_terminal], size=(2, 1), views=4,
         year=2004, height=2, cost=6, cls="yyj"),
    dict(id="yyjtower", name="YYJ control tower", models=[AB.yyj_tower], size=(1, 1), views=1,
         year=1960, height=4, cost=4, cls="yyj"),
    dict(id="apronservice", name="Apron service equipment",
         models=[lambda: AB.apron_service(0), lambda: AB.apron_service(1)], size=(1, 1), views=4,
         year=1960, height=1, cost=1, cls="yvr"),
    dict(id="floatplane", name="Floatplane dock (Harbour Air)", models=[AB.harbour_air_dock],
         size=(1, 1), views=4, year=1982, height=1, cost=2, water=True, cls="yyj"),
]
# cls -> (class label, unused, class name)
CLASSES = {"yvr": ("BCAY", None, "BC Aviation: YVR & airside"),
           "yyj": ("BCAV", None, "BC Aviation: YYJ & floatplanes")}

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
            rendered = model().render_object(views=range(obj["views"]))
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
