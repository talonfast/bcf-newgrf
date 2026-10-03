"""Compose mock-up screenshots of the terminals (with aircraft at the berths): python preview_terminals.py [zoom]"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

from aircraft import MODELS
from palette import DOS_PALETTE
from render import HEADINGS, render
from sprites import METRES_PER_UNIT, Z_PER_METRE
from terminals import SCENES
from tiles import cut

OUT = Path(__file__).resolve().parent.parent / "preview"
WATER = (44, 84, 128)
WATER_EDGE = (36, 72, 112)

# Aircraft parked at the berths: (x, y, direction index) in world units; N=0 NE=1 E=2 SE=3 S=4 SW=5 W=6 NW=7.
BERTHS = {
    "victoria": [((24, 36), 3, "beaver"), ((40, 36), 3, "twin_otter"), ((56, 36), 3, "turbo_otter"), ((72, 22), 0, "grand_caravan")],
    "vancouver": [((38, 38), 5, "beaver"), ((38, 54), 5, "turbo_otter"), ((38, 70), 5, "twin_otter"),
                  ((70, 38), 1, "grand_caravan"), ((70, 54), 1, "beaver"), ((70, 70), 1, "turbo_otter"),
                  ((22, 87), 6, "twin_otter")],
}


def main(zoom=2):
    pal = np.array(DOS_PALETTE, np.uint8)
    for name, make in SCENES.items():
        scene = make()
        tiles = cut(scene)
        sx_, sy_ = scene.size
        W = (sx_ + sy_) * 32 * zoom + 200 * zoom
        H = (sx_ + sy_) * 16 * zoom + 200 * zoom
        img = np.zeros((H, W, 3), np.uint8)
        img[:] = (30, 30, 30)
        ox, oy = W // 2 + (sx_ - sy_) * 16 * zoom, 80 * zoom

        def scr(x, y, z=0.0):
            return ox + int(round((y - x) * 2 * zoom)), oy + int(round((x + y - z) * zoom))

        def blit(sprite_level, x, y, z=0.0):
            px, xo, yo = sprite_level
            X, Y = scr(x, y, z)
            X += xo
            Y += yo
            h, w = px.shape
            sub = img[Y:Y + h, X:X + w]
            m = px > 0
            sub[m] = pal[px[m]]

        # Water diamonds.
        for ty in range(sy_):
            for tx in range(sx_):
                for j in range(32 * zoom):
                    half = (j + 1) * 2 if j < 16 * zoom else (32 * zoom - j) * 2
                    X, Y = scr(tx * 16, ty * 16)
                    img[Y + j, X - half:X + half] = WATER if (tx + ty) % 2 else WATER_EDGE
        # Ground overlays, then buildings and aircraft back to front.
        for (tx, ty), t in tiles.items():
            if t and t.ground:
                blit(t.ground.levels[zoom], tx * 16, ty * 16)
        items = []
        for (tx, ty), t in tiles.items():
            if t and t.building:
                items.append((tx * 16 + ty * 16 + 16, "b", (tx, ty, t)))
        for (x, y), d, model in BERTHS.get(name, []):
            items.append((x + y, "a", (x, y, d, model)))
        models = {}
        for _, kind, data in sorted(items, key=lambda i: i[0]):
            if kind == "b":
                tx, ty, t = data
                blit(t.building.levels[zoom], tx * 16, ty * 16)
            else:
                x, y, d, model = data
                if model not in models:
                    m = MODELS[model]()
                    models[model] = (m, m.surface())
                m, surf = models[model]
                cloud = m.cloud_for_heading(HEADINGS[d], METRES_PER_UNIT, Z_PER_METRE, surf)
                blit(render(cloud, zoom), x, y)
        OUT.mkdir(exist_ok=True)
        rows = np.where(img.sum(axis=(1, 2)) != 90 * W)[0]
        cols = np.where(img.sum(axis=(0, 2)) != 90 * H)[0]
        img = img[max(rows[0] - 8, 0):rows[-1] + 8, max(cols[0] - 8, 0):cols[-1] + 8]
        Image.fromarray(img).save(OUT / f"terminal_{name}_z{zoom}.png")
        print("wrote", OUT / f"terminal_{name}_z{zoom}.png")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2)
