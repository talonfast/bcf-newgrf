"""Render the TGTFTD seaplanes and the S-76 helicopter (src/seaplanes.py) to 8bpp sprite sheets
gfx/sea_<model>.png (1x), gfx/sea_<model>_8bpp_2x.png and _8bpp_4x.png, and gfx/seaplanes.json.
src/build_aircraft.py adds them to bc-aircraft.grf.

Usage: python src/make_seaplanes.py [model ...]       (needs scipy)
"""
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "common"))
from newgrf.sprites import save_sheet  # noqa: E402

GFX = os.path.join(ROOT, "gfx")

# Engine ID, model, name, introduction, passengers, game speed in mph (boosted to ~200 mph for
# playability; real cruise 180-296 km/h), mail bags, cost, running cost, vehicle life. These IDs
# come after the default aircraft, so no default aircraft is replaced.
SEAPLANES = [
    (0x60, "beaver", "DHC-2 Beaver (Harbour Air)", (1948, 4, 1), 6, 184, 1, 8, 30, 40),
    (0x61, "turbo_otter", "DHC-3T Turbo Otter (Harbour Air)", (1980, 6, 1), 14, 192, 2, 14, 50, 40),
    (0x62, "twin_otter", "DHC-6 Twin Otter (Harbour Air)", (1966, 1, 1), 19, 216, 3, 22, 80, 35),
    (0x63, "grand_caravan", "Cessna 208B Grand Caravan EX (Harbour Air)", (2013, 1, 1), 9, 208, 2, 18, 55, 30),
]

# Helicopters (normal aircraft, any airport or heliport; not seaplanes). Same fields as SEAPLANES.
HELICOPTERS = [
    (0x64, "s76", "Sikorsky S-76 (Helijet)", (1979, 2, 1), 12, 200, 2, 16, 75, 30),
]

# S-76 rotor: frame 0 stopped, 1-3 turning; (blade phase in degrees, chord).
S76_ROTOR = [(45, 0.42), (15, 0.30), (45, 0.30), (75, 0.30)]


def save(name, sprites, meta):
    """sprites: [{zoom: (pixels, x_offs, y_offs)}] -> sheets + meta[name]."""
    base = os.path.join(GFX, "sea_" + name)
    meta[name] = {
        "8bpp": save_sheet([s[1] for s in sprites], base + ".png", 8),
        "8bpp_2x": save_sheet([s[2] for s in sprites], base + "_8bpp_2x.png", 8),
        "8bpp_4x": save_sheet([s[4] for s in sprites], base + "_8bpp_4x.png", 8),
    }


def main():
    from seaplane_sprites import aircraft_sprites, rotor_sprites
    from seaplanes import MODELS, s76_rotor

    only = sys.argv[1:]
    os.makedirs(GFX, exist_ok=True)
    path = os.path.join(GFX, "seaplanes.json")
    meta = json.load(open(path)) if os.path.exists(path) else {}
    for _, model, *_ in SEAPLANES + HELICOPTERS:
        if only and model not in only:
            continue
        t = time.time()
        save(model, aircraft_sprites(MODELS[model]()), meta)
        print("rendered %-14s %.1fs" % (model, time.time() - t), flush=True)
    if not only or "s76" in only:
        save("s76_rotor", rotor_sprites([s76_rotor(phase, chord) for phase, chord in S76_ROTOR]), meta)
    with open(path, "w") as f:
        json.dump(meta, f, indent=1)


if __name__ == "__main__":
    main()
