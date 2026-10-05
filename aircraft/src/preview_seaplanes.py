"""Render preview sheets (PNG) of the seaplane and S-76 sprites to preview/:
python src/preview_seaplanes.py [model ...]       (needs scipy)"""

import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "common"))
from newgrf.palette import DOS_PALETTE  # noqa: E402
from pointcloud import HEADINGS, render  # noqa: E402
from seaplane_sprites import METRES_PER_UNIT, Z_PER_METRE  # noqa: E402
from seaplanes import MODELS  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "preview"
BG = 0xF5  # placeholder; replaced by a water-ish colour below


def to_rgb(pixels, bg=(56, 92, 120)):
    pal = np.array(DOS_PALETTE, np.uint8)
    img = pal[pixels]
    img[pixels == 0] = bg
    return img


def sheet(name, zooms=(1, 2, 4), scale=4):
    model = MODELS[name]()
    t = time.time()
    surf = model.surface()
    rows = []
    for z in zooms:
        cells = []
        for h in HEADINGS:
            cloud = model.cloud_for_heading(h, METRES_PER_UNIT, Z_PER_METRE, surf)
            px, xo, yo = render(cloud, z)
            cells.append((px, xo, yo))
        cw = max(c[0].shape[1] for c in cells) + 4
        ch = max(c[0].shape[0] for c in cells) + 4
        row = np.zeros((ch, cw * len(cells)), np.uint8)
        for i, (px, xo, yo) in enumerate(cells):
            row[2:2 + px.shape[0], i * cw + 2:i * cw + 2 + px.shape[1]] = px
        up = (4 // z) * scale // 4 * 1 if z < 4 else scale // 4 or 1
        rows.append(np.kron(row, np.ones((max(1, scale * 1 // z), max(1, scale * 1 // z)), np.uint8)))
    width = max(r.shape[1] for r in rows)
    full = np.zeros((sum(r.shape[0] for r in rows), width), np.uint8)
    y = 0
    for r in rows:
        full[y:y + r.shape[0], :r.shape[1]] = r
        y += r.shape[0]
    OUT.mkdir(exist_ok=True)
    Image.fromarray(to_rgb(full)).save(OUT / f"{name}.png")
    print(f"{name}: {time.time() - t:.1f}s -> {OUT / (name + '.png')}")


if __name__ == "__main__":
    for n in sys.argv[1:] or MODELS:
        sheet(n)
