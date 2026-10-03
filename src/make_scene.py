"""Compose a Tsawwassen-style terminal scene at 2x zoom from the rendered
sprites: road approach, toll plaza, holding lanes, terminal building and
Quay Market, control tower, a walkway out to a berth with its ramp and
wingwalls, and ferries alongside / under way.

Usage: python src/make_scene.py [out.png]
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GFX = os.path.join(ROOT, "gfx")
Z = 2
TW, TH = 64 * Z, 32 * Z
MAP_W, MAP_H = 14, 12           # tiles along x (to SW) and y (to SE)
SHORE = 7                       # ty >= SHORE is water
ORIGIN = (MAP_H * TW // 2 + 40, 110)

# (object, variant, view, north tile x, y)
PLACED = (
    [("tollplaza", 0, 1, tx, 0) for tx in (1, 2, 3, 4)] +
    [("holding", (tx * 7 + ty * 3) % 2, 1, tx, ty) for tx in (1, 2, 3, 4) for ty in (1, 2, 3)] +
    [("terminal", 0, 0, 7, 1), ("quaymarket", 0, 0, 7, 4), ("ctltower", 0, 0, 10, 2)] +
    [("walkway", 0, 1, 5, ty) for ty in (4, 5)] +
    [("berthramp", 0, 1, 5, 6), ("wingwall", 0, 3, 4, 7), ("wingwall", 0, 1, 6, 7),
     ("wingwall", 0, 3, 4, 8), ("wingwall", 0, 1, 6, 8)]
)
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


def ground(tx, ty, rng):
    if ty >= SHORE:
        return tuple(int(c) for c in np.array((46, 92, 146)) + rng.randint(-3, 4, 3))
    if tx == 0 or (ty == 0 and tx <= 5):
        return (78, 80, 84)                                   # approach road
    if ty == SHORE - 1 or (6 <= tx <= 11 and 1 <= ty <= 5) or ty == 4:
        return (186, 184, 176)                                # terminal plaza / quay
    return tuple(int(c) for c in np.array((96, 136, 70)) + rng.randint(-4, 5, 3))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "scene.png")
    rng = np.random.RandomState(3)
    W, H = (MAP_W + MAP_H) * TW // 2 + 80, (MAP_W + MAP_H) * TH // 2 + 300
    img = Image.new("RGBA", (W, H), (30, 40, 52, 255))
    d = ImageDraw.Draw(img)
    for tx in range(MAP_W):
        for ty in range(MAP_H):
            nx, ny = north(tx, ty)
            c = ground(tx, ty, rng)
            poly = [(nx, ny), (nx + TW // 2, ny + TH // 2), (nx, ny + TH), (nx - TW // 2, ny + TH // 2)]
            d.polygon(poly, fill=c)
            d.line(poly + [poly[0]], fill=tuple(max(0, v - 12) for v in c), width=1)

    objs = json.load(open(os.path.join(GFX, "objects.json")))
    ships = json.load(open(os.path.join(GFX, "sprites.json")))
    sprites = []
    for oid, var, view, ox, oy in PLACED:
        v = objs[oid]["variants"][var][str(view)]
        sheet = os.path.join(GFX, "obj_%s_%d_v%d_2x.png" % (oid, var, view))
        for (tx, ty), entry in zip(v["tiles"], v["2x"]):
            im, xo, yo = crop(sheet, entry)
            nx, ny = north(ox + tx, oy + ty)
            sprites.append(((ox + tx) + (oy + ty) + 0.5, im, nx + xo, ny + yo))
    for sid, state, view, x, y in SHIPS:
        suf = "_mv" if state == "moving" else ""
        im, xo, yo = crop(os.path.join(GFX, "%s%s_2x.png" % (sid, suf)), ships[sid][state]["2x"][view])
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
    d.text((24, 18), "Tsawwassen terminal — BC Ferries NewGRF", font=f, fill=(255, 255, 255))
    d.text((24, 56), "Toll plaza · holding lanes · terminal building · Quay Market · control tower · "
           "walkway · berth ramp & wingwalls · Spirit of British Columbia in the berth · 2x zoom",
           font=f2, fill=(200, 214, 230))
    a = np.array(img.convert("RGB")).astype(int)
    fg = np.abs(a - np.array([30, 40, 52])).sum(-1) > 12
    ys, xs = np.nonzero(fg[100:])
    box = (max(0, xs.min() - 30), 0, min(img.width, xs.max() + 30), min(img.height, ys.max() + 130))
    img.crop(box).convert("RGB").save(out, optimize=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
