"""Cut seaplane terminal scenes into per-tile sprites ({zoom: (8bpp pixels, x_offs, y_offs)})."""

import numpy as np

from pointcloud import render

ZOOMS = (1, 2, 4)
OVERLAP = 0.25  # world units of overlap between neighbouring tiles, hides seams after downsampling


class TileGraphics:
    def __init__(self, ground, building, height: int):
        self.ground = ground      # drawn as a ground overlay (child sprite) on the water, or None
        self.building = building  # drawn as a building sprite, or None
        self.height = height      # bounding box z extent of the building sprite


def _slice(cloud, tx, ty):
    x, y = cloud.pos[:, 0], cloud.pos[:, 1]
    m = (x >= tx * 16 - OVERLAP) & (x < tx * 16 + 16 + OVERLAP) & (y >= ty * 16 - OVERLAP) & (y < ty * 16 + 16 + OVERLAP)
    c = cloud.select(m)
    c.pos = c.pos - np.array([tx * 16, ty * 16, 0], np.float32)
    return c


def _sprite(cloud):
    if len(cloud.pos) == 0:
        return None
    levels = {}
    for z in ZOOMS:
        r = render(cloud, z)
        if r is None:
            return None
        levels[z] = r
    return levels


def cut(scene):
    """{(tx, ty): TileGraphics or None (plain water)}"""
    ground = scene.cloud("ground")
    building = scene.cloud("building")
    out = {}
    for ty in range(scene.size[1]):
        for tx in range(scene.size[0]):
            g = _slice(ground, tx, ty)
            b_ = _slice(building, tx, ty)
            gs = _sprite(g)
            bs = _sprite(b_)
            if gs is None and bs is None:
                out[(tx, ty)] = None
                continue
            h = int(np.ceil(b_.pos[:, 2].max())) + 1 if len(b_.pos) else 0
            out[(tx, ty)] = TileGraphics(gs, bs, min(max(h, 1), 255))
    return out
