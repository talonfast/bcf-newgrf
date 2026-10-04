"""Compose a Tsawwassen-style terminal scene at 2x zoom from the rendered
sprites: road approach, toll plaza, holding lanes, terminal building and
Quay Market, control tower, a walkway out to a berth with its ramp and
wingwalls, and ferries alongside / under way.

Usage: python src/make_scene.py [out.png]
"""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "common"))

import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GFX = os.path.join(ROOT, "gfx")
SHIP_GFX = os.path.join(os.path.dirname(ROOT), "vessels", "gfx")
Z = 2
TW, TH = 64 * Z, 32 * Z
MAP_W, MAP_H = 14, 12           # tiles along x (to SW) and y (to SE)
SHORE = 7                       # ty >= SHORE is water
ORIGIN = (MAP_H * TW // 2 + 40, 110)

# (object, variant, view, north tile x, y)
TSAWWASSEN = (
    [("tollplaza", 0, 1, tx, 0) for tx in (1, 2, 3, 4)] +
    [("holding", (tx * 7 + ty * 3) % 2, 1, tx, ty) for tx in (1, 2, 3, 4) for ty in (1, 2, 3)] +
    [("terminal", 0, 0, 7, 1), ("quaymarket", 0, 0, 7, 4), ("ctltower", 0, 0, 10, 2)] +
    [("busshelter", 0, 0, tx, 3) for tx in (7, 8)] +
    [("footplaza", (tx + 1) % 2, 0, tx, ty) for tx, ty in ((9, 3), (10, 3), (9, 4))] +
    [("walkwaytower", 0, 1, 5, 3)] +
    [("walkway", 0, 1, 5, ty) for ty in (4, 5)] +
    [("berthramp", 0, 1, 5, 6), ("wingwall", 0, 3, 4, 7), ("wingwall", 0, 1, 6, 7),
     ("wingwall", 0, 3, 4, 8), ("wingwall", 0, 1, 6, 8)]
)
SWARTZ_BAY = (
    [("tollplaza", 0, 1, tx, 0) for tx in (1, 2, 3, 4)] +
    [("holding", (tx * 5 + ty) % 2, 1, tx, ty) for tx in (1, 2, 3, 4) for ty in (1, 2, 3)] +
    [("sblandsend", 0, 0, 6, 1), ("sbterminal", 0, 0, 6, 3), ("sbtower", 0, 0, 9, 2),
     ("footplaza", 1, 0, 8, 3), ("busshelter", 0, 0, 8, 1)] +
    [("sbfootbridge", 0, 1, 5, ty) for ty in (3, 4)] +
    [("sbbridgetower", 0, 1, 5, 5), ("sbramp", 0, 1, 4, 5)] +
    [("sbwingwall", 0, 3, 3, ty) for ty in (6, 7)] +
    [("sbwingwall", 0, 1, 5, ty) for ty in (6, 7)]
)
SWARTZ_SHIPS = [("coastal", "still", 3, 4.5 * 16, 8.3 * 16),
                ("spirit_vi", "moving", 5, 10.0 * 16, 9.0 * 16),
                ("intermediate_cum", "moving", 1, 2.5 * 16, 10.4 * 16)]
PENDER = (
    [("islforest", (tx * 3 + ty * 7) % 3, 0, tx, ty) for tx in range(0, 14) for ty in range(0, 5)
     if not (3 <= tx <= 8 and 2 <= ty <= 4)] +
    [("islbooth", 0, 0, 4, 2), ("thestand", 0, 0, 6, 3), ("islgantry", 0, 1, 5, 4)] +
    [("islwingwall", 0, 3, 4, 5), ("islwingwall", 0, 1, 6, 5)] +
    [("isldolphin", 0, 0, 3, 6), ("isldolphin", 0, 0, 7, 6)]
)
PENDER_SHIPS = [("intermediate_cum", "still", 3, 5.5 * 16, 6.6 * 16),
                ("salish_heron", "moving", 5, 10.5 * 16, 8.2 * 16)]
LAYOUTS = {
    "pender": dict(placed=PENDER, ships=PENDER_SHIPS, shore=5,
                   title="Otter Bay, Pender Island — BC Ferries NewGRF",
                   sub="Gulf Islands forest · island ticket booth · The Stand · Otter Bay ramp "
                       "towers · red-fender berth walls · timber dolphins · 2x zoom"),
    "tsawwassen": dict(placed=None, ships=None, shore=7,
                       title="Tsawwassen terminal — BC Ferries NewGRF",
                       sub="Toll plaza · holding lanes · terminal building · bus shelters & foot-passenger "
                           "plaza · Quay Market · control tower · walkway & stair tower · berth ramp & "
                           "wingwalls · 2x zoom"),
    "swartzbay": dict(placed=SWARTZ_BAY, ships=SWARTZ_SHIPS, shore=6,
                      title="Swartz Bay terminal — BC Ferries NewGRF",
                      sub="Departures/Arrivals · Lands End cafe & market tent · traffic tower · "
                          "open-truss foot bridge & gangway tower · lattice ramp gantry · "
                          "blue/orange berth walls · 2x zoom"),
}
# (ship id, state, direction, world x, world y); direction 3 = SE (towards the berth)
SHIPS = [("spirit", "still", 3, 5.5 * 16, 8.7 * 16),
         ("coastal_cel_2010", "moving", 5, 10.5 * 16, 9.4 * 16),
         ("salish_raven", "moving", 1, 3.0 * 16, 10.6 * 16)]


def north(tx, ty):
    return ORIGIN[0] + (ty - tx) * TW // 2, ORIGIN[1] + (tx + ty) * TH // 2


def world(x, y):
    return ORIGIN[0] + int((y - x) * 2 * Z), ORIGIN[1] + int((x + y) * Z)


def crop(sheet, entry):
    x, y, w, h, xo, yo = entry
    return Image.open(sheet).convert("RGBA").crop((x, y, x + w, y + h)), xo, yo


def ground(tx, ty, rng, SHORE):
    if ty >= SHORE:
        return tuple(int(c) for c in np.array((46, 92, 146)) + rng.randint(-3, 4, 3))
    if SHORE == 5:                                            # island: forest floor
        return tuple(int(c) for c in np.array((90, 110, 62)) + rng.randint(-4, 5, 3))
    if tx == 0 or (ty == 0 and tx <= 5):
        return (78, 80, 84)                                   # approach road
    if ty == SHORE - 1 or (6 <= tx <= 11 and 1 <= ty <= 5) or ty == 4:
        return (186, 184, 176)                                # terminal plaza / quay
    return tuple(int(c) for c in np.array((96, 136, 70)) + rng.randint(-4, 5, 3))


def main():
    which = sys.argv[2] if len(sys.argv) > 2 else "tsawwassen"
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "scene.png")
    L = LAYOUTS[which]
    placed, ships_at, shore = L["placed"] or TSAWWASSEN, L["ships"] or SHIPS, L["shore"]
    rng = np.random.RandomState(3)
    W, H = (MAP_W + MAP_H) * TW // 2 + 80, (MAP_W + MAP_H) * TH // 2 + 300
    img = Image.new("RGBA", (W, H), (30, 40, 52, 255))
    d = ImageDraw.Draw(img)
    for tx in range(MAP_W):
        for ty in range(MAP_H):
            nx, ny = north(tx, ty)
            c = ground(tx, ty, rng, shore)
            poly = [(nx, ny), (nx + TW // 2, ny + TH // 2), (nx, ny + TH), (nx - TW // 2, ny + TH // 2)]
            d.polygon(poly, fill=c)
            d.line(poly + [poly[0]], fill=tuple(max(0, v - 12) for v in c), width=1)

    objs = json.load(open(os.path.join(GFX, "objects.json")))
    ships = json.load(open(os.path.join(SHIP_GFX, "sprites.json")))
    sprites = []
    for oid, var, view, ox, oy in placed:
        v = objs[oid]["variants"][var][str(view)]
        sheet = os.path.join(GFX, "obj_%s_%d_v%d_2x.png" % (oid, var, view))
        for (tx, ty), entry in zip(v["tiles"], v["2x"]):
            im, xo, yo = crop(sheet, entry)
            nx, ny = north(ox + tx, oy + ty)
            sprites.append(((ox + tx) + (oy + ty) + 0.5, im, nx + xo, ny + yo))
    for sid, state, view, x, y in ships_at:
        suf = "_mv" if state == "moving" else ""
        im, xo, yo = crop(os.path.join(SHIP_GFX, "%s%s_2x.png" % (sid, suf)), ships[sid][state]["2x"][view])
        sx, sy = world(x, y)
        sprites.append(((x + y) / 16, im, sx + xo, sy + yo))
    for _, im, x, y in sorted(sprites, key=lambda s: s[0]):
        img.alpha_composite(im, (x, y))

    try:
        f = ImageFont.truetype("/System/Library/Fonts/Avenir Next.ttc", 28, index=2)
        f2 = ImageFont.truetype("/System/Library/Fonts/Avenir Next.ttc", 16, index=5)
    except OSError:
        f = f2 = ImageFont.load_default()
    d = ImageDraw.Draw(img)
    d.text((24, 18), L["title"], font=f, fill=(255, 255, 255))
    d.text((24, 56), L["sub"], font=f2, fill=(200, 214, 230))
    a = np.array(img.convert("RGB")).astype(int)
    fg = np.abs(a - np.array([30, 40, 52])).sum(-1) > 12
    ys, xs = np.nonzero(fg[100:])
    box = (max(0, xs.min() - 30), 0, min(img.width, xs.max() + 30), min(img.height, ys.max() + 130))
    img.crop(box).convert("RGB").save(out, optimize=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
