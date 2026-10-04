# PNW Aviation (TGTFTD NewGRF)

Pacific Northwest aircraft and seaplane terminals for [TGTFTD](https://github.com/teagangosling/TGTFTD),
the JGRPP fork with seaplanes and seaplane terminals.

## Aircraft

| Aircraft | Livery | Type | Passengers | Mail | Game speed | Introduced |
|---|---|---|---|---|---|---|
| DHC-2 Beaver | Harbour Air | seaplane | 6 | 1 | 184 mph | 1948 |
| DHC-6 Twin Otter | Harbour Air | seaplane | 19 | 3 | 216 mph | 1966 |
| Sikorsky S-76 | Helijet | helicopter | 12 | 2 | 200 mph | 1979 |
| DHC-3T Turbo Otter | Harbour Air | seaplane | 14 | 2 | 192 mph | 1980 |
| Cessna 208B Grand Caravan EX | Harbour Air | seaplane | 9 | 2 | 208 mph | 2013 |

* Passenger numbers come from the Harbour Air and Helijet fleet pages.
* Speeds are raised to about 200 mph so the aircraft keep up in the game. Real cruise speeds are 180–296 km/h
  for the seaplanes and 135 kn for the S-76. The faster types stay slightly faster.
* All seaplanes are *small* aircraft, so they are safe at short-strip terminals.
* The S-76 is a normal helicopter. It uses land heliports and airports, not seaplane terminals, and it is
  available in any OpenTTD build. It has its own rotor sprites: stopped, plus three spinning frames.

## Seaplane terminals

| Terminal | Based on | Size | Berths | Hangars | Available |
|---|---|---|---|---|---|
| Victoria Harbour Seaplane Terminal | Commuter airport | 5 × 4 | 3 | 1 | 1950 |
| Vancouver (Coal Harbour) Seaplane Terminal | International airport | 7 × 7 | 6 | 2 | 1950 |
| Wooden Seaplane Dock | TGTFTD seaplane dock | 1 × 2 | 1 | none | 1920 |
| Seaplane Kerb Dock | TGTFTD seaplane kerb dock | 6 × 3 | 8 slots | none | 1950 |

* **Victoria**: a floating terminal barge with a wavy green living roof, glulam posts and silver siding.
  It has a flag deck, a gangway to a floating hangar, and three berths between finger docks.
* **Vancouver**: a central floating pier with a two-storey glass terminal and a control tower. It has six nose-in
  berths on finger docks, two floating hangars and a fuel dock.
* Both have marker buoys along the water runways. Taxiways and runways are open water.
* **Wooden Seaplane Dock**: just a small floating wooden dock with pilings and one berth. Seaplanes land and take
  off on the open water beside it, outside the 1 × 2 footprint. It comes in all four rotations (rotate it in the
  airport window), so you can put that open water on whichever side of the dock has it.
* **Seaplane Kerb Dock**: a long floating dock where seaplanes pull up alongside at the first free slot, like cars
  at a kerb, and leave forward along a one-way lane. Its split water runway is inside the 6 × 3 footprint, so it
  needs no open water around it; if all eight slots are taken, a landed seaplane takes off again and comes back.
  Needs TGTFTD with kerb docks (`tgtftd_seaplanes` feature version 3); four rotations.
  It has no hangar, so seaplanes are bought and serviced at a terminal that has one. It needs a TGTFTD build with
  seaplane docks (`tgtftd_seaplanes` feature version 2); on older builds it is hidden.

The seaplanes and terminals need TGTFTD. In other builds they are hidden, and only the S-76 remains.

## Building

Needs Python 3.10+ with `numpy`, `scipy` and `Pillow`. No grfcodec or NML is needed: the script writes the
GRF (container version 2, with 1x, 2x and 4x zoom sprites) directly.

```
cd src
python build.py                 # -> build/pnw_aviation.grf
python preview.py               # aircraft sprite sheets -> preview/
python preview_terminals.py 4   # terminal mock-ups at 4x zoom -> preview/
python verify.py ../build/pnw_aviation.grf   # decode and check the GRF
python release.py --notes "..."  # build, verify, install locally and upload the GitHub release v<VERSION>
```

Releases are made on this machine with `release.py`, not by GitHub Actions. Bump `VERSION` in `build.py` first.

`python build.py out.grf --vanilla-test` builds a test version that keeps everything visible in stock OpenTTD.
The terminals become land airports, so you can check the graphics without TGTFTD. Don't ship it.

## How it works

* `aircraft.py`: voxel models of the aircraft in metres, plus the livery painters.
  * Harbour Air: white fuselage; navy rear fuselage and fin with a yellow pinstripe and yellow "HA" logo; navy
    wings, nacelles and Caravan struts; white floats with red bands.
  * Helijet: white nose and cockpit; metallic blue body behind a raked split with a red stripe; white pinstripes
    on the engine cowling.
* `terminals.py`: the terminal scenes as surface primitives in OpenTTD world units, tagged *ground* (docks,
  drawn as ground overlays on the game's own animated water) or *building* (sorted sprites).
* `render.py`: projects geometry with OpenTTD's dimetric projection, z-buffers, shades, supersamples and matches
  the result to the DOS palette. It avoids the company-colour and animated palette ranges.
* `tiles.py`: cuts each scene into per-tile ground and building sprites.
* `build.py`: writes the NewGRF actions:
  * aircraft: Action 0/1/2/3/4, and `aircraft_is_seaplane` through the Action 14 property mapping;
  * helicopter rotor: a self wagon-override Action 3 on a 4-sprite set;
  * airport tiles (feature 11): sprite layouts with ground sprite `0x0FDD`, so the game draws the real sea,
    canal or river water underneath;
  * airports (feature 0D): substitute airport, `airport_seaplane_terminal` (1 = terminal, 2 = dock), layout,
    years and name. The dock is guarded by a feature test for `tgtftd_seaplanes` version 2.

Scale: 1 world unit (1/16 tile) = 1.6 m horizontally, 1.6 height pixels per metre.

## Notes and limits

* Each terminal has one layout, facing north. Aircraft paths come from the substitute airport, so the docks
  are placed around its berths and taxi routes.
* Harbour Air and Helijet names and liveries are used for a fan-made game add-on. This project isn't affiliated
  with either company.
