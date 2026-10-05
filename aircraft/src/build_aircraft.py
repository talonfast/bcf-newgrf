"""Build bc-aircraft.grf: the airliners of src/make_aircraft.py and the TGTFTD seaplanes and S-76
helicopter of src/make_seaplanes.py, from the rendered gfx/.

Usage: python src/build_aircraft.py [output.grf] [--vanilla-test]

--vanilla-test keeps the seaplanes visible without TGTFTD (as ordinary small planes), to check
their graphics in a stock OpenTTD.
"""
import datetime
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "common"))
from make_aircraft import AIRFLEET  # noqa: E402
from make_seaplanes import HELICOPTERS, SEAPLANES  # noqa: E402
from newgrf import GRF, cli  # noqa: E402
from newgrf import actions as A  # noqa: E402
from newgrf import tgtftd as T  # noqa: E402
from newgrf.sprites import sheet_sprites  # noqa: E402

VERSION = 3
NAME = "BC Aviation: Aircraft {SILVER}v%d" % VERSION
DESCRIPTION = (
    "Aircraft serving British Columbia in current liveries: Air Canada (A220, A321, 737 MAX 8, 787-9, "
    "777-300ER, Air Canada Express Dash 8-400), Alaska Airlines (737-900ER, 737 MAX 9, 787-9, Horizon E175) "
    "and WestJet (737-800); Harbour Air seaplanes (DHC-2 Beaver, DHC-3T Turbo Otter, DHC-6 Twin Otter, "
    "Cessna 208B Grand Caravan EX) and the Helijet Sikorsky S-76.{}{ORANGE}The seaplanes need TGTFTD; "
    "without it they are hidden. Seaplane terminals are in BC Aviation: Airports.")

AIRCRAFT_TYPE_SMALL, AIRCRAFT_TYPE_LARGE = 2, 3
SOUND_TAKEOFF_PROPELLER, SOUND_TAKEOFF_JET = 0x06, 0x07
SFX_TAKEOFF_PROPELLER, SFX_TAKEOFF_JET = 0x08, 0x09   # the seaplanes' original sound effect numbers


def add_airliner(grf, num, a, meta, engine_ids, text):
    atype = AIRCRAFT_TYPE_SMALL if a.get("small") else AIRCRAFT_TYPE_LARGE
    props = [
        (0x06, A.b(0x07)),
        (0x1A, A.d(A.date(a["year"]))),
        (0x04, A.b(a["model_life"])),
        (0x03, A.b(a["life"])),
        (0x02, A.b(10)),                     # reliability decay
        (0x0B, A.b(a["cost"])),
        (0x0E, A.b(a["run"])),
        (0x08, A.b(0xFF)),                   # new graphics
        (0x09, A.b(atype & 2)),              # plane, not helicopter
        (0x0A, A.b(atype & 1)),              # large
        (0x0C, A.b(A.aircraft_speed_kmh(a["kmh"]))),
        (0x0F, A.w(a["pax"])),
        (0x11, A.b(a["mail"])),
        (0x12, A.b(SOUND_TAKEOFF_PROPELLER if a.get("small") else SOUND_TAKEOFF_JET)),
    ]
    if a.get("variant_of"):
        props.append((0x20, A.w(engine_ids[a["variant_of"]])))
    grf.add(A.action0(A.AIRCRAFT, num, props))
    grf.add(A.action4_names(A.AIRCRAFT, num, [a["name"]]))
    sprites = sheet_sprites(os.path.join(ROOT, "gfx", "air_" + a["id"]), meta[a["id"]])
    grf.add(A.action1(A.AIRCRAFT, 1, len(sprites)))
    for s in sprites:
        grf.sprite(s)
    grf.add(A.action2_vehicle(A.AIRCRAFT, 0, [0], [0]))
    grf.add(A.varaction2(A.AIRCRAFT, 1, [A.Adjust(0x0C, mask=0xFFFF)],
                         [(A.cb(text - 0xD000), A.CB_ADDITIONAL_TEXT, A.CB_ADDITIONAL_TEXT)], 0))
    grf.add(A.action3(A.AIRCRAFT, [num], default=0, cargo=[(0xFF, 1)]))


def airliner_description(a):
    return "%s{}{BLACK}Real-world: {GOLD}%d{BLACK} seats, cruise {GOLD}%d{BLACK} km/h" % (
        a["desc"], a["pax"], a["kmh"])


def days_since_1920(y, m=1, day=1):
    return (datetime.date(y, m, day) - datetime.date(1920, 1, 1)).days


def mph(speed):
    """Aircraft speed property: 1 unit = 8 mph."""
    return round(speed / 8)


def seaplane_props(eid, helicopter, intro, pax, speed, mail, cost, running, life):
    props = [
        (0x00, A.w(days_since_1920(*intro))),
        (0x02, A.b(20)),                     # reliability decay
        (0x03, A.b(life)),
        (0x04, A.b(255)),                    # model life (years)
        (0x06, A.b(0x0F)),                   # all climates
        (0x07, A.b(5)),                      # loading speed
        (0x08, A.b(0xFF)),                   # new graphics
        (0x09, A.b(0x00 if helicopter else 0x02)),
    ]
    if not helicopter:
        props.append((0x0A, A.b(0x00)))      # small: safe at short-strip terminals
    props += [
        (0x0B, A.b(cost)),
        (0x0C, A.b(mph(speed))),
        (0x0D, A.b(20 if helicopter else 18)),  # acceleration
        (0x0E, A.b(running)),
        (0x0F, A.w(pax)),
        (0x11, A.b(mail)),
        (0x12, A.b(SFX_TAKEOFF_JET if helicopter else SFX_TAKEOFF_PROPELLER)),
    ]
    return A.action0(A.AIRCRAFT, eid, props)


def add_seaplanes(grf, meta, vanilla_test):
    """The Harbour Air seaplanes (TGTFTD) and the Helijet S-76 (any build)."""
    gfx = os.path.join(ROOT, "gfx")
    for eid, model, name, intro, pax, speed, mail, cost, running, life in SEAPLANES:
        grf.add(seaplane_props(eid, False, intro, pax, speed, mail, cost, running, life))
        grf.add(A.action4_names(A.AIRCRAFT, eid, [name]))
    grf.add(A.action1(A.AIRCRAFT, len(SEAPLANES), 8))
    for _, model, *_ in SEAPLANES:
        for s in sheet_sprites(os.path.join(gfx, "sea_" + model), meta[model]):
            grf.sprite(s)
    for i, (eid, *_rest) in enumerate(SEAPLANES):
        grf.add(A.action2_vehicle(A.AIRCRAFT, i, [i], [i]))
        grf.add(A.action3(A.AIRCRAFT, [eid], default=i))

    # TGTFTD: make them seaplanes. Otherwise: hide them (no climates).
    first, n = SEAPLANES[0][0], len(SEAPLANES)
    grf.add(T.skip_if_bit(0x8D, T.BIT_AIRCRAFT_MAPPED, False, 1))
    grf.add(A.b(0x00, A.AIRCRAFT, 1, n) + A.ext(first) + T.mapped(T.PROP_AIRCRAFT_IS_SEAPLANE, [b"\x01"] * n))
    if not vanilla_test:
        grf.add(T.skip_if_bit(0x8D, T.BIT_AIRCRAFT_MAPPED, True, 1))
        grf.add(A.action0(A.AIRCRAFT, first, [(0x06, A.b(0x00) * n)], count=n))

    for eid, model, name, intro, pax, speed, mail, cost, running, life in HELICOPTERS:
        grf.add(seaplane_props(eid, True, intro, pax, speed, mail, cost, running, life))
        grf.add(A.action4_names(A.AIRCRAFT, eid, [name]))
    for eid, model, *_ in HELICOPTERS:
        # Body: one set of 8 directions.
        body = sheet_sprites(os.path.join(gfx, "sea_" + model), meta[model])
        grf.add(A.action1(A.AIRCRAFT, 1, len(body)))
        for s in body:
            grf.sprite(s)
        grf.add(A.action2_vehicle(A.AIRCRAFT, 0, [0], [0]))
        grf.add(A.action3(A.AIRCRAFT, [eid], default=0))
        # Rotor: a "wagon override" of the helicopter with itself; frame 0 = stopped, 1-3 = turning.
        rotor = sheet_sprites(os.path.join(gfx, "sea_%s_rotor" % model), meta[model + "_rotor"])
        grf.add(A.action1(A.AIRCRAFT, 1, len(rotor)))
        for s in rotor:
            grf.sprite(s)
        grf.add(A.action2_vehicle(A.AIRCRAFT, 1, [0], [0]))
        grf.add(A.action3(A.AIRCRAFT, [eid], default=1, override=True))


def build(path, jobs=None, vanilla_test=False):
    grf = GRF("TFBA", NAME, DESCRIPTION, VERSION, 1)
    grf.add(T.action14(T.property_mapping("aircraft_is_seaplane", A.AIRCRAFT, T.PROP_AIRCRAFT_IS_SEAPLANE,
                                          T.BIT_AIRCRAFT_MAPPED)))
    texts = [grf.string(airliner_description(a)) for a in AIRFLEET]
    grf.add(A.cargo_table(["PASS", "MAIL"]))
    with open(os.path.join(ROOT, "gfx", "aircraft.json")) as f:
        meta = json.load(f)
    engine_ids = {a["id"]: num for num, a in enumerate(AIRFLEET)}
    for num, a in enumerate(AIRFLEET):          # list position = engine ID: append only!
        add_airliner(grf, num, a, meta, engine_ids, texts[num])
    with open(os.path.join(ROOT, "gfx", "seaplanes.json")) as f:
        add_seaplanes(grf, json.load(f), vanilla_test)
    grf.write(path, jobs)


if __name__ == "__main__":
    vanilla = "--vanilla-test" in sys.argv
    if vanilla:
        sys.argv.remove("--vanilla-test")
    out, jobs = cli.output(os.path.join(ROOT, "bc-aircraft.grf"))
    build(out, jobs, vanilla)
