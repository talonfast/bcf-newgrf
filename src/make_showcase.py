"""Compose showcase.png: one ship per class on open water, labelled.

Uses the rendered 2x sprites in gfx/ (run make first).
Usage: python src/make_showcase.py [out.png]
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from ships import FLEET  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GFX = os.path.join(ROOT, "gfx")
COLS, CELL_W, CELL_H = 5, 420, 250
VIEWS = [2, 1, 6, 3, 5]          # E, NE, W, SE, SW - varied headings across a row


def water(w, h):
    """Calm sea with a faint isometric tile grid (64x32 at 1x = 128x64 at 2x)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    base = np.array([44, 84, 136], np.float32) + (yy / h)[..., None] * np.array([-8, -10, -14])
    ripple = 3 * np.sin(xx * 0.11 + np.sin(yy * 0.07) * 2) * np.sin(yy * 0.23)
    img = base + ripple[..., None]
    gx = xx / 128 + yy / 64
    gy = -xx / 128 + yy / 64
    edge = (np.abs(gx - np.round(gx)) < 0.008) | (np.abs(gy - np.round(gy)) < 0.008)
    img[edge] = img[edge] * 0.9 + 255 * 0.1
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "showcase.png")
    meta = json.load(open(os.path.join(GFX, "sprites.json")))
    ships = [s for s in FLEET if not s.get("variant_of")]
    rows = -(-len(ships) // COLS)
    W, H = COLS * CELL_W, rows * CELL_H + 90
    img = water(W, H)
    d = ImageDraw.Draw(img)
    try:
        title = ImageFont.truetype("/System/Library/Fonts/Avenir Next.ttc", 40, index=2)
        label = ImageFont.truetype("/System/Library/Fonts/Avenir Next.ttc", 20, index=5)
        small = ImageFont.truetype("/System/Library/Fonts/Avenir Next.ttc", 15, index=7)
    except OSError:
        title = label = small = ImageFont.load_default()
    d.text((28, 22), "BC Ferries & MV Coho — OpenTTD NewGRF", font=title, fill=(255, 255, 255))
    d.text((W - 28, 40), "%d ships · 32bpp up to 4x · JGRPP / OpenTTD 13+" % len(FLEET),
           font=small, fill=(210, 225, 240), anchor="ra")
    for i, s in enumerate(ships):
        r, c = divmod(i, COLS)
        view = VIEWS[(c + r) % len(VIEWS)]
        state, suf = (("moving", "_mv") if (i % 3 != 2) else ("still", ""))
        x, y, w, h, xo, yo = meta[s["id"]][state]["2x"][view]
        sheet = Image.open(os.path.join(GFX, "%s%s_2x.png" % (s["id"], suf)))
        spr = sheet.crop((x, y, x + w, y + h))
        cx, cy = c * CELL_W + CELL_W // 2, 90 + r * CELL_H + int(CELL_H * 0.55)
        img.alpha_composite(spr, (cx + xo, cy + yo))
        yl = 90 + (r + 1) * CELL_H - 34
        d.text((cx, yl), s["name"], font=label, fill=(255, 255, 255), anchor="mm",
               stroke_width=3, stroke_fill=(20, 40, 70))
        d.text((cx, yl + 20), "%d" % s["year"], font=small, fill=(200, 216, 236), anchor="mm",
               stroke_width=2, stroke_fill=(20, 40, 70))
    img.convert("RGB").save(out, optimize=True)
    print("wrote", out, img.size)


if __name__ == "__main__":
    main()
