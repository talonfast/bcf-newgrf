"""Objects (feature 0F) from rendered tiles: terminals, airports and coastal waterfront.

Each object has views (rotations) and variants (random per tile); each tile of each view of each
variant is one sprite, drawn on concrete or water. The graphics chain picks the view (variable 48),
then for objects with several variants the tile's random bits (5F), then the tile by its offset in
the object (40).
"""

import json
import os

from . import actions as A
from .sprites import sheet_sprites

GROUND_CONCRETE = 0x058C
GROUND_WATER = 0x0FDD
FLAG_ON_WATER, FLAG_NOT_ON_LAND = 0x0008, 0x0200
ALL_CLIMATES = 0x0F


def add_objects(grf, objects, meta, classes, gfx_dir):
    """objects: the set's OBJECTS list (append only: list position = object ID); meta: its
    objects.json; classes: {cls: (class label, unused, class name)}."""
    for num, o in enumerate(objects):
        oid = o["id"]
        variants = meta[oid]["variants"]
        label, _, class_name = classes[o.get("cls")]
        class_text = grf.string(class_name)
        name_text = grf.string(o["name"])
        w, h = o["size"]
        grf.add(A.action0(A.OBJECTS, num, [
            (0x08, A.label(label)),
            (0x09, A.w(class_text)),
            (0x0A, A.w(name_text)),
            (0x0B, A.b(ALL_CLIMATES)),
            (0x0C, A.b(h << 4 | w)),
            (0x0D, A.b(o["cost"])),
            (0x14, A.b(o["cost"])),
            (0x0E, A.d(A.date(o["year"]))),
            (0x10, A.w(FLAG_ON_WATER | FLAG_NOT_ON_LAND if o.get("water") else 0)),
            (0x16, A.b(o["height"])),
            (0x17, A.b(o["views"])),
        ]))

        # One sprite set per tile.
        tiles = {}  # (view, variant) -> [(tile offset, set number)]
        sprites = []
        for view in range(o["views"]):
            for vi, vmeta in enumerate(variants):
                v = vmeta[str(view)]
                base = os.path.join(gfx_dir, "obj_%s_%d_v%d" % (oid, vi, view))
                sprs = sheet_sprites(base, {k: v[k] for k in ("8bpp", "1x", "2x", "4x")})
                tiles[(view, vi)] = [(tx + 16 * ty, len(sprites) + i) for i, (tx, ty) in enumerate(v["tiles"])]
                sprites += sprs
        grf.add(A.action1(A.OBJECTS, len(sprites), 1))
        for s in sprites:
            grf.sprite(s)

        ground = GROUND_WATER if o.get("water") else GROUND_CONCRETE
        zext = 8 * (o["height"] + 1)
        next_id = iter(range(0xFF))

        def layout(set_number):
            gid = next(next_id)
            grf.add(A.b(0x02, A.OBJECTS, gid, 1) + A.w(ground) + A.w(0)
                    + A.w(set_number) + A.w(0x8000) + A.b(0, 0, 0, 16, 16, zext))
            return gid

        def by_tile(view, vi):
            cases = [(offset, layout(s)) for offset, s in tiles[(view, vi)]]
            if len(cases) == 1:
                return cases[0][1]
            gid = next(next_id)
            grf.add(A.varaction2(A.OBJECTS, gid, [
                A.Adjust(0x40, shift=8, mask=0xFF),                  # relative_y
                A.Adjust(0x1A, mask=16, op=A.MUL),
                A.Adjust(0x40, mask=0xFF, op=A.ADD),                 # + relative_x
            ], [(g, off, off) for off, g in cases], cases[0][1]))
            return gid

        def by_variant(view):
            cases = [by_tile(view, vi) for vi in range(len(variants))]
            if len(cases) == 1:
                return cases[0]
            gid = next(next_id)
            grf.add(A.varaction2(A.OBJECTS, gid, [A.Adjust(0x5F, shift=8, mask=0xFF, mod=len(cases))],
                                 [(g, k, k) for k, g in enumerate(cases)], cases[0]))
            return gid

        views = [by_variant(view) for view in range(o["views"])]
        top = views[0]
        if len(views) > 1:
            top = next(next_id)
            grf.add(A.varaction2(A.OBJECTS, top, [A.Adjust(0x48, mask=0xFF)],
                                 [(g, k, k) for k, g in enumerate(views)], views[0]))
        grf.add(A.action3(A.OBJECTS, [num], default=top))


def load_meta(path):
    with open(path) as f:
        return json.load(f)
