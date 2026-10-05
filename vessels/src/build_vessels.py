"""Build bcferries.grf from ships.FLEET and the rendered gfx/ (src/make_gfx.py).

Usage: python src/build_vessels.py [output.grf]
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "common"))
from ships import FLEET  # noqa: E402
from newgrf import GRF, Param, cli  # noqa: E402
from newgrf import actions as A  # noqa: E402
from newgrf.sprites import sheet_sprites  # noqa: E402

VERSION = 8
NAME = "BC Ferries: Vessels {SILVER}v%d" % VERSION
DESCRIPTION = ("Ferries of British Columbia: BC Ferries' Spirit, Coastal, C-class, Salish, Island and minor-route "
               "classes, plus Black Ball's MV Coho and the Victoria Clipper.{}{}Passenger ships with a refittable "
               "vehicle deck. Includes 32bpp sprites up to 4x zoom. Works with OpenTTD 13+ and JGR's Patch Pack.")
CAP_MODE = Param(0, "Capacity scale", "Real ferries carry thousands of passengers. Scale capacities down for a "
                 "more conventional OpenTTD balance.", 0, 2, 0,
                 {0: "Realistic (100%)", 1: "Half (50%)", 2: "Quarter (25%)"})

CARGO = ["PASS", "MAIL", "GOOD", "VEHI"]
PASS, VEHI = CARGO.index("PASS"), CARGO.index("VEHI")
# Cargo classes
CC_PASSENGERS, CC_MAIL, CC_EXPRESS, CC_ARMOURED, CC_BULK, CC_PIECE_GOODS, CC_LIQUID, CC_REFRIGERATED = (
    0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80)
FERRY_REFIT = CC_PASSENGERS | CC_MAIL | CC_EXPRESS | CC_PIECE_GOODS | CC_ARMOURED | CC_REFRIGERATED
FERRY_NO_REFIT = CC_LIQUID | CC_BULK
PAX_REFIT = CC_PASSENGERS | CC_MAIL           # passenger-only boats: passengers, or mail
PAX_NO_REFIT = CC_LIQUID | CC_BULK | CC_PIECE_GOODS

SOUND_DEPARTURE_FERRY = 0x05
SPAWN_STEAM, SPAWN_ELECTRIC = 0x41, 0x43
EFFECT_SPRITE_DIESEL = 0xF2
CB_RESULT_CREATE_EFFECT_CENTER, CB_RESULT_CREATE_EFFECT_NO_ROTATION = 0x2000, 0x4000
CBM_REFIT_CAPACITY = 0x08
VAR_SPEED, VAR_DIRECTION, VAR_CARGO = 0xB4, 0x9F, 0x47
VAR_CALLBACK, VAR_CALLBACK_PARAM, VAR_GRF_PARAM = 0x0C, 0x10, 0x7F

# LNG / hybrid ships puff less (random "electric" model); diesels puff steadily.
LIGHT_SMOKE = {"salish", "salish_eagle", "salish_raven", "salish_heron", "island", "spirit_lng"}


def reliability_decay(s):
    """How fast reliability falls between services. OpenTTD's own ships use 5 (the hovercraft 10);
    older classes wear a little faster, the PacifiCat like the hovercraft, and the cardboard Pirate
    Pak fastest of all."""
    if s["id"] == "piratepak":
        return 20
    if s["id"] == "pacificat":
        return 10
    return 7 if s["year"] < 1985 else 5


def description(s):
    if s.get("pax_only"):
        return "%s{}{BLACK}Passengers only. Real-world: {GOLD}%d{BLACK} passengers, %s knots" % (
            s["desc"], s["pax"], "%g" % s["kn"])
    if s.get("joke"):
        return s["desc"]
    return "%s{}{BLACK}Real-world: {GOLD}%d{BLACK} passengers, {GOLD}%d{BLACK} vehicles, %s knots" % (
        s["desc"], s["pax"], s["cars"], "%g" % s["kn"])


def create_effect(x, y, z, sprite=EFFECT_SPRITE_DIESEL):
    return (z & 0xFF) << 24 | (y & 0xFF) << 16 | (x & 0xFF) << 8 | sprite


def add_ship(grf, num, s, meta, engine_ids):
    sid = s["id"]
    m = meta[sid]
    smoke = m.get("smoke") if m.get("smoke", [[]])[0] else None
    pax_only = s.get("pax_only")
    cars = s["cars"] if not pax_only else 10
    cars2 = s["cars"] * 2 if not pax_only else max(10, s["pax"] // 20)
    speed = A.ship_speed_kmh(float("%.1f" % (s["kn"] * 1.852)))

    props = [
        (0x06, A.b(0x07)),                                   # temperate, arctic, tropical
        (0x1A, A.d(A.date(s["year"], 3, 1))),
        (0x04, A.b(s["model_life"])),
        (0x03, A.b(s["life"])),
        (0x02, A.b(reliability_decay(s))),
        (0x0A, A.b(s["cost"])),
        (0x0F, A.b(s["run"])),
        (0x08, A.b(0xFF)),                                   # new graphics
        (0x0B, A.b(min(speed, 0xFF))),
    ]
    if speed >= 0xFF:
        props.append((0x23, A.w(min(speed, 0xFFFF))))
    props += [
        (0x0C, A.b(PASS)),
        (0x0D, A.w(s["pax"])),
        (0x18, A.w(PAX_REFIT if pax_only else FERRY_REFIT)),
        (0x11, A.d(0)),
        (0x19, A.w(PAX_NO_REFIT if pax_only else FERRY_NO_REFIT)),
        (0x11, A.d(0)),
    ]
    if not pax_only:
        props += [(0x1E, A.b(1, VEHI)), (0x11, A.d(0))]     # refit to vehicles too
    props += [
        (0x13, A.b(10)),                                     # refit cost
        (0x07, A.b(max(10, s["pax"] // 20))),                # loading speed
        (0x10, A.b(SOUND_DEPARTURE_FERRY)),
    ]
    if s.get("variant_of"):
        props.append((0x20, A.w(engine_ids[s["variant_of"]])))
    if smoke:
        props.append((0x1C, A.b(SPAWN_ELECTRIC if sid in LIGHT_SMOKE else SPAWN_STEAM)))
    grf.add(A.action0(A.SHIPS, num, props))
    grf.add(A.action4_names(A.SHIPS, num, [s["name"]]))
    grf.add(A.action0(A.SHIPS, num, [(0x12, A.b(CBM_REFIT_CAPACITY))]))

    # Sprites: set 0 still, set 1 under way (wake and bow wave).
    gfx = os.path.join(ROOT, "gfx")
    still = sheet_sprites(os.path.join(gfx, sid), m["still"])
    moving = sheet_sprites(os.path.join(gfx, sid + "_mv"), m["moving"])
    grf.add(A.action1(A.SHIPS, 2, len(still)))
    for spr in still + moving:
        grf.sprite(spr)

    ids = iter(range(0xFF))

    def group(data_fn):
        gid = next(ids)
        grf.add(data_fn(gid))
        return gid

    g_still = group(lambda g: A.action2_vehicle(A.SHIPS, g, [0], [0]))
    g_moving = group(lambda g: A.action2_vehicle(A.SHIPS, g, [1], [1]))
    # Wake and bow wave only while under way (current_speed 0..3 km/h-ish: still).
    g_gfx = group(lambda g: A.varaction2(A.SHIPS, g, [
        A.Adjust(VAR_SPEED, mask=0xFFFF), A.const(0x23C3, A.MUL), A.const(0x10000, A.SDIV),
    ], [(g_still, 0, 3)], g_moving))

    def capacity(n):
        """Callback result max(1, n >> cap_mode)."""
        return group(lambda g: A.varaction2(A.SHIPS, g, [
            A.const(n), A.Adjust(VAR_GRF_PARAM, param=CAP_MODE.number, op=A.SHR), A.const(1, A.SMAX),
        ], [], 0))

    # Vehicle deck: FIRS-style VEHI cargo counts one per car space, other freight two units per car space.
    g_cap_vehi, g_cap_freight, g_cap_pax = capacity(cars), capacity(cars2), capacity(s["pax"])
    g_freight = group(lambda g: A.varaction2(A.SHIPS, g, [A.Adjust(VAR_CARGO, mask=0xFF)],
                                             [(g_cap_vehi, VEHI, VEHI)], g_cap_freight))
    g_cap = group(lambda g: A.varaction2(A.SHIPS, g, [A.Adjust(VAR_CARGO, shift=16, mask=CC_PASSENGERS)],
                                         [(g_freight, 0, 0)], g_cap_pax))

    # Exhaust smoke at the real stack outlets: per direction, create_effect() values in registers 0x100+.
    g_fx = None
    if smoke:
        per_dir = []
        for pts in smoke:
            adjusts = []
            for i, (x, y, z) in enumerate(pts):
                adjusts.append(A.const(create_effect(x, y, z), A.RST))
                adjusts.append(A.const(0x100 + i, A.STO))
            result = A.cb(CB_RESULT_CREATE_EFFECT_CENTER | CB_RESULT_CREATE_EFFECT_NO_ROTATION | len(pts))
            # A range that never matches: with no ranges the calculated value would be the result.
            per_dir.append(group(lambda g, adjusts=adjusts, result=result: A.varaction2(
                A.SHIPS, g, adjusts, [(result, 1, 0)], result)))
        g_fx = group(lambda g: A.varaction2(A.SHIPS, g, [A.Adjust(VAR_DIRECTION, mask=0xFF)],
                                            [(gd, d, d) for d, gd in enumerate(per_dir)], per_dir[0]))

    # Property callback: cargo_capacity (property 0D).
    g_prop = group(lambda g: A.varaction2(A.SHIPS, g, [A.Adjust(VAR_CALLBACK_PARAM, mask=0xFF)],
                                          [(g_cap, 0x0D, 0x0D)], g_gfx))
    callbacks = [(g_cap, A.CB_REFIT_CAPACITY, A.CB_REFIT_CAPACITY), (g_prop, A.CB_PROPERTY, A.CB_PROPERTY)]
    if g_fx is not None:
        callbacks.append((g_fx, A.CB_CREATE_EFFECT, A.CB_CREATE_EFFECT))
    g_world = group(lambda g: A.varaction2(A.SHIPS, g, [A.Adjust(VAR_CALLBACK, mask=0xFFFF)], callbacks, g_gfx))
    text = grf.string(description(s))
    g_purchase = group(lambda g: A.varaction2(A.SHIPS, g, [A.Adjust(VAR_CALLBACK, mask=0xFFFF)], [
        (g_still, 0, 0),
        (A.cb(text - 0xD000), A.CB_ADDITIONAL_TEXT, A.CB_ADDITIONAL_TEXT),
        (g_prop, A.CB_PROPERTY, A.CB_PROPERTY),
    ], g_gfx))
    grf.add(A.action3(A.SHIPS, [num], default=g_world, cargo=[(0xFF, g_purchase)]))


def build(path, jobs=None):
    grf = GRF("TFBC", NAME, DESCRIPTION, VERSION, 1, params=[CAP_MODE])
    # Descriptions first, in fleet order, so the string IDs follow the fleet.
    for s in FLEET:
        grf.string(description(s))
    grf.add(A.cargo_table(CARGO))
    with open(os.path.join(ROOT, "gfx", "sprites.json")) as f:
        meta = json.load(f)
    engine_ids = {s["id"]: num for num, s in enumerate(FLEET)}
    for num, s in enumerate(FLEET):          # list position = engine ID: append only!
        add_ship(grf, num, s, meta, engine_ids)
    grf.write(path, jobs)


if __name__ == "__main__":
    build(*cli.output(os.path.join(ROOT, "bcferries.grf")))
