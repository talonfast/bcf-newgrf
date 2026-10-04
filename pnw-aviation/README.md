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

| Terminal | TGTFTD terminal type | Size | Slots | Hangars | Available |
|---|---|---|---|---|---|
| Victoria Harbour Seaplane Terminal | kerb terminal with hangar | 5 × 4 | 5 | 1 | 1950 |
| Vancouver (Coal Harbour) Seaplane Terminal | large kerb terminal | 7 × 7 | 8 | 2 | 1950 |
| Nanaimo Harbour Flight Centre | kerb dock | 6 × 3 | 8 | none | 1950 |
| Wooden Seaplane Dock | seaplane dock | 1 × 2 | 1 | none | 1920 |

All terminals are kerb style: seaplanes pull up alongside a long dock at the first free slot and leave forward
along a one-way lane, and every water runway is split so one seaplane can land while another takes off.

* **Victoria**: the floating terminal barge with its wavy green living roof, a floating hangar, and a long dock
  with five slots in front of them.
* **Vancouver**: a central pier with the two-storey glass terminal and the control tower, four slots along each
  face, two floating hangars and two water runways (one per side of the pier).
* **Nanaimo**: a long floating dock with eight slots and a small waiting shelter; no hangar. Four rotations.
* **Wooden Seaplane Dock**: a small floating wooden dock with one berth. Seaplanes land and take off on the open
  water beside it, outside the 1 × 2 footprint; four rotations, so that water can be on any side.

The seaplanes and terminals need TGTFTD 0.2.0 or newer (`tgtftd_seaplanes` feature version 3). In other builds
they are hidden, and only the S-76 remains.

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
