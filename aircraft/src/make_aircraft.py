"""Render the aircraft (src/aircraft.py) to gfx/air_<id>[_1x|_2x|_4x].png and gfx/aircraft.json.
src/build_aircraft.py makes bc-aircraft.grf from them (with the seaplanes of src/make_seaplanes.py).

Usage: python src/make_aircraft.py [--preview out.png] [ids...]
"""
import json
import os
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "common"))
import aircraft as A  # noqa: E402
from render import save_sheet_8, save_sheet_32, views_at  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GFX = os.path.join(ROOT, "gfx")

# Order = engine ID: append only! Speeds are cruise speeds; capacities are
# the operator's typical configuration (rounded).
AIRFLEET = [
    dict(id="ac_dash8", name="Air Canada Express Dash 8-400", model=A.dash8_400, year=2011,
         pax=78, mail=8, kmh=667, small=True, cost=60, run=50, life=30, model_life=40,
         desc="De Havilland Canada Q400 turboprop, flown for Air Canada Express by Jazz. "
              "The YYJ - YVR shuttle workhorse."),
    dict(id="ac_a321", name="Air Canada Airbus A321", model=A.a321, year=2001, pax=190, mail=20,
         kmh=876, cost=120, run=95, life=30, model_life=35, desc="Mainline narrowbody."),
    dict(id="ac_777", name="Air Canada Boeing 777-300ER", model=A.b777_300er, year=2007,
         pax=400, mail=60, kmh=905, cost=230, run=190, life=30, model_life=35,
         desc="Long-haul flagship out of YVR."),
    dict(id="ac_787", name="Air Canada Boeing 787-9", model=A.b787_9, year=2015, pax=298,
         mail=45, kmh=903, cost=200, run=150, life=30, model_life=35,
         desc="Dreamliner for transpacific routes from YVR."),
    dict(id="ac_737max", name="Air Canada Boeing 737 MAX 8", model=A.b737_max8, year=2017,
         pax=169, mail=18, kmh=839, cost=120, run=85, life=30, model_life=35,
         desc="Narrowbody with split scimitar winglets."),
    dict(id="ac_a220", name="Air Canada Airbus A220-300", model=A.a220_300, year=2020, pax=137,
         mail=14, kmh=871, cost=110, run=75, life=30, model_life=35,
         desc="Quebec-built (ex-Bombardier CSeries) narrowbody."),
    dict(id="as_739", name="Alaska Airlines Boeing 737-900ER", model=A.b737_900er, year=2012,
         pax=178, mail=18, kmh=840, cost=120, run=88, life=30, model_life=30,
         desc="Alaska's main narrowbody on Seattle routes."),
    dict(id="as_e175", name="Alaska (Horizon) Embraer 175", model=A.e175, year=2017, pax=76,
         mail=8, kmh=870, cost=80, run=60, life=30, model_life=35,
         desc="Regional jet flown by Horizon Air for Alaska."),
    dict(id="as_max9", name="Alaska Airlines Boeing 737 MAX 9", model=A.b737_max9, year=2019,
         pax=178, mail=18, kmh=839, cost=125, run=82, life=30, model_life=35,
         desc="Stretched MAX with scimitar winglets.", variant_of="as_739"),
    dict(id="wj_738", name="WestJet Boeing 737-800", model=A.b737_800_wj, year=2003, pax=174,
         mail=18, kmh=840, cost=115, run=88, life=30, model_life=30,
         desc="WestJet's mainstay, in the 2018 dark teal livery."),
    dict(id="as_789", name="Alaska Airlines Boeing 787-9", model=lambda: A.b787_9("as"), year=2025,
         pax=300, mail=45, kmh=903, cost=200, run=150, life=30, model_life=35,
         desc="Alaska's long-haul Dreamliner, in the new aurora livery."),
]

def preview(rows, path):
    W = max(sum(r[0].shape[1] for r in row) + 10 * len(row) for row in rows) + 20
    H = sum(max(r[0].shape[0] for r in row) + 12 for row in rows) + 20
    out = Image.new("RGBA", (W, H), (110, 150, 200, 255))
    y = 10
    for row in rows:
        x = 10
        for rgba, xo, yo in row:
            im = Image.fromarray(np.dstack([np.clip(rgba[..., :3], 0, 255),
                                            np.clip(rgba[..., 3] * 255, 0, 255)]).astype(np.uint8))
            out.alpha_composite(im, (x, y))
            x += im.width + 10
        y += max(r[0].shape[0] for r in row) + 12
    out.save(path)


def main():
    args = sys.argv[1:]
    pv = None
    if "--preview" in args:
        i = args.index("--preview")
        pv = args[i + 1]
        del args[i:i + 2]
    os.makedirs(GFX, exist_ok=True)
    mpath = os.path.join(GFX, "aircraft.json")
    meta = json.load(open(mpath)) if os.path.exists(mpath) else {}
    rows = []
    for a in AIRFLEET:
        if args and a["id"] not in args:
            continue
        t = time.time()
        views = a["model"]().render()
        base = os.path.join(GFX, "air_" + a["id"])
        z1, z2, z4 = (views_at(views, z) for z in (1, 2, 4))
        meta[a["id"]] = {"8bpp": save_sheet_8(z1, base + ".png"), "1x": save_sheet_32(z1, base + "_1x.png"),
                         "2x": save_sheet_32(z2, base + "_2x.png"), "4x": save_sheet_32(z4, base + "_4x.png")}
        rows.append(z2)
        print("rendered %-12s %.1fs" % (a["id"], time.time() - t), flush=True)
    json.dump(meta, open(mpath, "w"), indent=1)
    if pv and rows:
        preview(rows, pv)


if __name__ == "__main__":
    main()
