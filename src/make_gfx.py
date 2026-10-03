"""Render every ship to gfx/ and write gfx/sprites.json (NML sprite entries).

Per ship:  <id>.png     1x 8bpp (DOS palette) base sprites
           <id>_1x.png  1x 32bpp
           <id>_2x.png  2x 32bpp
           <id>_4x.png  4x 32bpp

Usage: python src/make_gfx.py [--preview out.png] [--zoom 1|2|4] [ids...]
"""
import json
import math
import os
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from render import save_sheet_8, save_sheet_32, views_at, HEADINGS, SCALE, ZS  # noqa: E402
from ships import FLEET  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GFX = os.path.join(ROOT, "gfx")
WATER = np.array((48, 88, 140), dtype=np.float32)


def preview(rows, path, zoom):
    """Composite each ship's 8 views over water, one ship per row."""
    cw, ch = 190 * zoom, 120 * zoom
    # isometric tile grid (64x32 px per tile at 1x) centred on the ship
    yy, xx = np.mgrid[0:ch, 0:cw]
    gx = (xx - cw // 2) / (64 * zoom) + (yy - ch * 5 // 8) / (32 * zoom)
    gy = -(xx - cw // 2) / (64 * zoom) + (yy - ch * 5 // 8) / (32 * zoom)
    edge = (np.abs(gx - np.round(gx)) < 0.012) | (np.abs(gy - np.round(gy)) < 0.012)
    out = []
    for items in rows:
        cells = []
        for rgba, xo, yo in items:
            cell = np.tile(WATER, (ch, cw, 1))
            cell[edge] = cell[edge] * 0.8 + 255 * 0.2
            h, w = rgba.shape[:2]
            cx, cy = cw // 2 + xo, ch * 5 // 8 + yo
            x0, y0 = max(cx, 0), max(cy, 0)
            x1, y1 = min(cx + w, cw), min(cy + h, ch)
            src = rgba[y0 - cy:y1 - cy, x0 - cx:x1 - cx]
            a = src[..., 3:4]
            cell[y0:y1, x0:x1] = cell[y0:y1, x0:x1] * (1 - a) + src[..., :3] * a
            cells.append(cell)
        out.append(np.concatenate(cells, axis=1))
    im = Image.fromarray(np.concatenate(out, axis=0).astype(np.uint8))
    if zoom == 1:
        im = im.resize((im.width * 3, im.height * 3), Image.NEAREST)
    im.save(path)


def smoke_offsets(model):
    """World (x, y, z) offsets of each stack outlet for the 8 directions,
    in OpenTTD units, for the create_effect callback (max 4 outlets)."""
    k = SCALE * model.scale
    out = []
    for hx, hy in HEADINGS:
        n = math.hypot(hx, hy)
        hx, hy = hx / n, hy / n
        px, py = -hy, hx
        pts = []
        for u, v, w in model.exhausts[:4]:
            x = (u * hx + v * px) * k
            y = (u * hy + v * py) * k
            z = w * ZS * k
            pts.append([int(round(np.clip(c, -128, 127))) for c in (x, y, z)])
        out.append(pts)
    return out


def build_ship(ship):
    model = ship["model"]()
    model.speed = ship["kn"]
    if "weather" in ship:
        model.weather = ship["weather"]
    views = model.render()
    meta, prev = {"smoke": smoke_offsets(model)}, {}
    for state, moving in (("still", False), ("moving", True)):
        base = os.path.join(GFX, ship["id"] + ("_mv" if moving else ""))
        z1, z2, z4 = (views_at(views, z, moving) for z in (1, 2, 4))
        meta[state] = {
            "8bpp": save_sheet_8(z1, base + ".png"),
            "1x": save_sheet_32(z1, base + "_1x.png"),
            "2x": save_sheet_32(z2, base + "_2x.png"),
            "4x": save_sheet_32(z4, base + "_4x.png"),
        }
        prev[state] = {1: z1, 2: z2, 4: z4}
    return meta, prev


def main():
    args = sys.argv[1:]
    pv, pzoom, pstate = None, 4, "still"
    if "--preview" in args:
        i = args.index("--preview")
        pv = args[i + 1]
        del args[i:i + 2]
    if "--zoom" in args:
        i = args.index("--zoom")
        pzoom = int(args[i + 1])
        del args[i:i + 2]
    if "--moving" in args:
        args.remove("--moving")
        pstate = "moving"
    os.makedirs(GFX, exist_ok=True)
    meta_path = os.path.join(GFX, "sprites.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    rows = []
    for ship in FLEET:
        if args and ship["id"] not in args:
            continue
        t = time.time()
        meta[ship["id"]], prev = build_ship(ship)
        rows.append(prev[pstate][pzoom])
        print("rendered %-18s %.1fs" % (ship["id"], time.time() - t), flush=True)
    json.dump(meta, open(meta_path, "w"), indent=1)
    if pv:
        preview(rows, pv, pzoom)


if __name__ == "__main__":
    main()
