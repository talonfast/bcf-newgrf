![Coastal GrfLink](docs/coastal-grflink.png)

OpenTTD NewGRFs for coastal British Columbia: the BC Ferries fleet and its
terminals, plus the airlines, seaplanes and airports that connect the coast.
For OpenTTD 13+ and JGR's Patch Pack; the Harbour Air seaplanes and the
seaplane terminals need [TGTFTD](https://github.com/teagangosling/TGTFTD), the
JGRPP fork with seaplanes. One repo, separate GRFs so you can load only what
you want:

| Set | Folder | GRF | GRF ID |
|---|---|---|---|
| BC Ferries: Vessels | `vessels/` | `bcferries.grf` | `TFBC` |
| BC Ferries: Terminals | `terminals/` | `bc-terminals.grf` | `TFBT` |
| BC Aviation: Aircraft (airliners, seaplanes, S-76) | `aircraft/` | `bc-aircraft.grf` | `TFBA` |
| BC Aviation: Airports (YVR, YYJ, seaplane terminals) | `airports/` | `bc-airports.grf` | `TFBY` |
| Coastal: Waterfront | `coastal/` | `coastal-waterfront.grf` | `TFBW` |

Shared code lives in `common/`: the GRF writer (`newgrf/`), the voxel
renderer (`render.py`), the point-cloud renderer of the seaplanes and seaplane
terminals (`pointcloud.py`), and the logo/livery artwork in `common/decals/`.

## Installing
Download the tars from the GitHub **Releases** page and drop them, as-is, into
`~/Documents/OpenTTD/newgrf/` (Windows: `Documents\OpenTTD\newgrf\`). OpenTTD
reads the GRFs straight from the tars. Remove an older tar of the same set
when you update.

## BC Ferries: Vessels
43 ships (27 classes plus named sister ships) from British Columbia's ferry
fleet, plus Black Ball Line's MV Coho and the Victoria Clipper.

| Ship | Year | Pax | Vehicles | Knots |
|---|---|---|---|---|
| MV Coho (Black Ball, current white/red livery) | 1959 | 1000 | 115 | 15 |
| Sidney class | 1960 | 1000 | 106 | 18 |
| V-class / V-class (stretched, variant) | 1962 / 1970 | 1000 / 1360 | 106 / 192 | 18 |
| Burnaby class | 1965 | 1200 | 192 | 18 |
| Bowen class | 1965 | 400 | 70 | 14 |
| Queen of Prince Rupert | 1966 | 458 | 80 | 18 |
| T-class (Tachek, Quadra Queen II) | 1969 | 150 | 26 | 11 |
| Nimpkish | 1973 | 95 | 16 | 10 |
| C-class / C-class Oak Bay (variant) | 1976 / 1981 | 1466 / 1494 | 362 / 322 | 20.5 |
| Quinitsa | 1977 | 300 | 44 | 12 |
| Queen of the North | 1980 | 700 | 115 | 19 |
| Quinsam | 1982 | 400 | 63 | 11.5 |
| Intermediate class (Capilano, Cumberland) | 1991 | 462 | 100 | 15.5 |
| Spirit class / Spirit class LNG (variant) | 1993 / 2018 | 2100 / 1965 | 358 | 19.5 |
| Century class (Skeena Queen) | 1997 | 600 | 92 | 14.5 |
| PacifiCat class | 1999 | 1000 | 250 | 34 |
| Northern Adventure | 2007 | 600 | 112 | 19 |
| Coastal class / Coastal class Vancouver 2010 (variant) | 2008 | 1604 | 310 | 21 |
| Northern Expedition | 2009 | 600 | 130 | 19.5 |
| Salish class | 2016 | 600 | 145 | 15.5 |
| Island class | 2020 | 300 | 47 | 14 |
| Victoria Clipper IV / V (variant), passenger-only | 1993 / 2019 | 330 / 540 | - | 28 / 36 |
| Pirate Pak (extra credit: White Spot kids' meal, afloat) | 1970 | 4 | 1 | 6 |

Figures are approximate, rounded real-world values. In-game years are the
years each class entered service. Variants appear grouped under the parent
ship in the build list (OpenTTD 13+/JGRPP).

### Cargo
Passengers by default. Refit to the vehicle deck to carry `VEHI` (FIRS-style
"Vehicles", one per car space) or any mail/express/piece-goods/armoured/
refrigerated cargo (two units per car space). Bulk and liquid are excluded.

**Parameter "Capacity scale":** 100% (realistic), 50% or 25%.

## BC Ferries: Terminals
Placeable from the landscaping toolbar under **BC Ferries: Tsawwassen**:
| Object | Tiles | Notes |
|---|---|---|
| Tsawwassen Quay Market | 2x1 | glass hall, glulam timber, from 2009 |
| Ferry terminal building | 2x2 | roof-top BC Ferries letters |
| Toll plaza | 1x1 | place tiles side by side across the road |
| Vehicle holding lanes | 1x1 | two random car layouts |
| Berth ramp and towers | 1x1 | at the quay edge, ramp towards the water |
| Berth wingwall and dolphin | 1x1 | on water; fenders face the neighbouring tile |
| Passenger walkway | 1x1 | place tiles in a row |
| Terminal control tower | 1x1 | |
| Foot passenger and bus shelter | 1x1 | bus lane on one side |
| Foot passenger plaza | 1x1 | two random layouts |
| Walkway stair tower | 1x1 | walkway leaves from one side; continue with walkway tiles |

Swartz Bay has its own object class:

| Object | Tiles | Notes |
|---|---|---|
| Departures / Arrivals building | 2x1 | blue portal frames, roof-edge lettering, flags |
| Lands End cafe and market tent | 2x1 | |
| Traffic tower and playground | 1x1 | |
| Foot passenger bridge (open truss) | 1x1 | place tiles in a row |
| Foot bridge tower and gangway | 1x1 | bridge arrives from one side, gangway leaves the other |
| Berth ramp gantry (lattice) | 1x1 | |
| Berth wall (blue and orange fenders) | 1x1 | on water |

The Southern Gulf Islands class has: Otter Bay ramp towers, island berth
wall (red fenders, on water), timber trestle pier (on water), timber pile
dolphins (on water), island ticket booth, **The Stand (Otter Bay)** - the
burger stand run from a converted RV - and Gulf Islands forest (firs, arbutus,
mossy granite; three random layouts).

`make scenes` composes `terminals/scene*.png` (Tsawwassen, Swartz Bay,
Pender Island) from these sprites.



## BC Aviation: Aircraft
| Aircraft | Airline | Year | Seats |
|---|---|---|---|
| Dash 8-400 (Q400) | Air Canada Express | 2011 | 78 |
| Airbus A321 | Air Canada | 2001 | 190 |
| Boeing 777-300ER | Air Canada | 2007 | 400 |
| Boeing 787-9 | Air Canada | 2015 | 298 |
| Boeing 737 MAX 8 | Air Canada | 2017 | 169 |
| Airbus A220-300 | Air Canada | 2020 | 137 |
| Boeing 737-900ER / 737 MAX 9 (variant) | Alaska Airlines | 2012 / 2019 | 178 |
| Embraer 175 | Alaska (Horizon) | 2017 | 76 |
| Boeing 787-9 | Alaska Airlines | 2025 | 300 |
| Boeing 737-800 | WestJet | 2003 | 174 |

### Seaplanes and helicopter
| Aircraft | Livery | Type | Passengers | Mail | Game speed | Introduced |
|---|---|---|---|---|---|---|
| DHC-2 Beaver | Harbour Air | seaplane | 6 | 1 | 184 mph | 1948 |
| DHC-6 Twin Otter | Harbour Air | seaplane | 19 | 3 | 216 mph | 1966 |
| Sikorsky S-76 | Helijet | helicopter | 12 | 2 | 200 mph | 1979 |
| DHC-3T Turbo Otter | Harbour Air | seaplane | 14 | 2 | 192 mph | 1980 |
| Cessna 208B Grand Caravan EX | Harbour Air | seaplane | 9 | 2 | 208 mph | 2013 |

* The seaplanes need TGTFTD 0.2.0 or newer (`tgtftd_seaplanes` feature
  version 3) and use its seaplane terminals (BC Aviation: Airports). In other
  builds they are hidden, and only the S-76 remains.
* Passenger numbers come from the Harbour Air and Helijet fleet pages. Speeds
  are raised to about 200 mph so the aircraft keep up in the game (real cruise
  speeds are 180-296 km/h for the seaplanes and 135 kn for the S-76); the
  faster types stay slightly faster.
* All seaplanes are *small* aircraft, so they are safe at short-strip terminals.
* The S-76 is a normal helicopter: it uses land heliports and airports, not
  seaplane terminals, and works in any OpenTTD build. It has its own rotor
  sprites (stopped, plus three spinning frames).
* Harbour Air: white fuselage; navy rear fuselage and fin with a yellow
  pinstripe and yellow "HA" logo; navy wings, nacelles and Caravan struts;
  white floats with red bands. Helijet: white nose and cockpit; metallic blue
  body behind a raked split with a red stripe.

## BC Aviation: Airports
OpenTTD's airport layouts and aircraft movement are built into the game, so
this set dresses a standard airport (build an international or
intercontinental airport, then place these around it). Object classes
**BC Aviation: YVR & airside** and **BC Aviation: YYJ & floatplanes**:

| Object | Tiles | Notes |
|---|---|---|
| YVR control tower | 1x1 | banded teal glass cab |
| YVR terminal hall | 2x2 | barrel-vault roof, departures curb |
| Jet bridge | 1x1 | rotunda at the terminal side, cab towards the stand |
| Airport parkade | 2x2 | |
| Apron service equipment | 1x1 | two random layouts |
| YYJ terminal | 2x1 | glass rotunda with disc roof |
| YYJ control tower | 1x1 | |
| Floatplane dock (Harbour Air) | 1x1 | on water, DHC-2 Beaver moored |

### Seaplane terminals (TGTFTD)
Real airports for the seaplanes, built on water. They need TGTFTD 0.2.0 or
newer; in other builds they are hidden.

| Terminal | TGTFTD terminal type | Size | Slots | Hangars | Available |
|---|---|---|---|---|---|
| Victoria Harbour Seaplane Terminal | kerb terminal with hangar | 5 x 4 | 5 | 1 | 1950 |
| Vancouver (Coal Harbour) Seaplane Terminal | large kerb terminal | 7 x 7 | 8 | 2 | 1950 |
| Nanaimo Harbour Flight Centre | kerb dock | 6 x 3 | 8 | none | 1950 |
| Wooden Seaplane Dock | seaplane dock | 1 x 2 | 1 | none | 1920 |

All terminals are kerb style: seaplanes pull up alongside a long dock at the
first free slot and leave forward along a one-way lane, and every water runway
is split so one seaplane can land while another takes off.

* **Victoria**: the floating terminal barge with its wavy green living roof, a
  floating hangar, and a long dock with five slots in front of them.
* **Vancouver**: a central pier with the two-storey glass terminal and the
  control tower, four slots along each face, two floating hangars and two
  water runways (one per side of the pier).
* **Nanaimo**: a long floating dock with eight slots and a small waiting
  shelter; no hangar. Four rotations.
* **Wooden Seaplane Dock**: a small floating wooden dock with one berth.
  Seaplanes land and take off on the open water beside it, outside the 1 x 2
  footprint; four rotations, so that water can be on any side.

The docks are drawn as ground overlays on the game's own water, so sea, canal
and river water show through. Harbour Air and Helijet names and liveries are
used for a fan-made game add-on; this project isn't affiliated with either
company.

## Coastal: Waterfront
Object classes **Waterfront: Victoria**, **Waterfront: Vancouver** and
**Waterfront: docks & marinas**. Water objects are placed on water tiles.
Drawn in the classic OpenTTD style (flat-shaded, outlined, no fine detail)
so they sit comfortably next to base-set buildings.

| Object | Tiles | Notes |
|---|---|---|
| Float home | 1x1, water | Fisherman's Wharf; four random colour/shape variants |
| Fish & chips float | 1x1, water | take-out shack, picnic tables, umbrellas |
| Fisgard Lighthouse | 1x1 | tower, red lantern, red-brick keeper's house, rocky islet |
| BC Parliament Buildings | 3x2 | copper domes, gilded Captain Vancouver, fountain, lawn |
| Granville Island Public Market | 2x2 | corrugated sheds, rooftop sign, striped awnings, produce |
| Ocean Concrete 'Giants' silos | 2x1 | stylised after the OSGEMEOS murals |
| Artisan shed | 1x1 | four colours |
| Seawall promenade | 1x1 | bike path, railing, willow (one of two variants) |
| Floating dock walkway | 1x1, water | two variants |
| Marina slips | 1x1, water | sailboats and motorboats, two variants |
| Harbour ferry dock | 1x1, water | ticket hut, little harbour ferries |
| Timber pile pier | 1x1, water | |

## Logos
Liveries and signage use the official vector logos, fetched by
`common/fetch_logos.py` into `common/logos/` (SVG plus a rasterised PNG):
BC Ferries, Air Canada, Air Canada Express, Alaska Airlines, Horizon,
WestJet and the Vancouver 2010 emblem. `make decals` cuts them into the
decals the renderer projects onto hulls, stacks, fins and fuselages.

## Building
Needs Python 3.10+ with `numpy` and `Pillow` (and `scipy` to re-render the
seaplanes and seaplane terminals). No NML or grfcodec: `common/newgrf/`
writes the GRFs directly (container version 2, 8bpp and 32bpp sprites at 1x,
2x and 4x zoom).
```
python build.py                  # build every GRF (or: python build.py vessels aircraft ...)
python tools/release.py          # build, then package releases/<set>-vN.tar for each set
python tools/release.py --install                      # ... and copy them into $OPENTTD_NEWGRF
python tools/release.py aircraft --upload --notes ".." # ... and publish GitHub release bc-aircraft-vN
```
With make: `make setup` (one time: `.venv` with pillow, numpy, scipy), `make`,
`make release`, `make install`, `make scenes showcase aircraft-preview
seaplane-preview` (preview images) and `make decals` (regenerate
common/decals artwork, macOS fonts).

The rendered sprite sheets in each set's `gfx/` are committed, so a build
doesn't render anything. `make` re-renders a set when its models change; by
hand: `vessels/src/make_gfx.py`, `terminals/src/make_objects.py`,
`aircraft/src/make_aircraft.py` and `make_seaplanes.py`,
`airports/src/make_airports.py` and `make_seaplane_terminals.py`,
`coastal/src/make_coastal.py`. Sprite encoding is cached in `.grfcache/`.

Bump the set's `VERSION` in its `src/build_<set>.py` and add a line to its
`CHANGELOG.txt` before releasing. Item IDs are append only (list position =
ID); the seaplanes and the S-76 use aircraft IDs 0x60-0x64, after the default
aircraft, so they replace none of them.

`python aircraft/src/build_aircraft.py test.grf --vanilla-test` (and the same
for `airports/src/build_airports.py`) builds a test version that keeps the
seaplanes and kerb terminals visible in stock OpenTTD, as ordinary small
planes and land airports, to check their graphics without TGTFTD. Don't ship
it.

`python tools/compare_grf.py NEW.grf REF.grf [REF2.grf ...]` compares GRFs by
behaviour: properties, strings, sprites (pixel by pixel) and every graphics
and callback chain, evaluated for all the values of the variables it reads.

TGTFTD support (`common/newgrf/tgtftd.py`): Action 14 property mappings for
`aircraft_is_seaplane` and `airport_seaplane_terminal`, and feature tests for
`tgtftd_seaplanes` versions 2 (seaplane docks) and 3 (kerb docks); Action 7 on
the bits they set skips the TGTFTD-only parts in other builds. Seaplane
terminal tiles (feature 11) use sprite layouts on ground sprite `0x0FDD`, so the
game draws its real water underneath. Seaplane scale: 1 world unit (1/16 tile)
= 1.6 m horizontally, 1.6 height pixels per metre.

Graphics: 8bpp at 1x (fallback) plus 32bpp at 1x, 2x and 4x zoom. The
32bpp sprites need a 32bpp blitter (the default in current OpenTTD/JGRPP).
Liveries are matched to photos: the modern BC Ferries scheme (black lower
hull, blue pinstripe, "≋BCFerries" wordmark and ship name on the hull,
royal-blue stacks with white waves, navy logo panels on Salish/Island
class), the older 1960s-90s scheme for Sidney, V-class and Queen of the
North, Coho's current white/red Black Ball livery, and the Coastal class
Vancouver 2010 wrap as on Coastal Renaissance in 2008-10: side one has
the alpine skier / "vancouver 2010" / sit-skier panels, side two the
Okanagan vineyard / "British Columbia" / speed skaters, each framed by the
lime-royal-navy swooshes, with the Olympic and Paralympic emblems. The
photo panels are original artwork in the same composition, not the
copyrighted photographs.

Logos and lettering are decal masks in `common/decals/` (generated by
`common/make_decals.py` from macOS system fonts; only needed to redo artwork)
projected onto the 3D hulls and stacks.

Rendering: cast shadows with soft edges, ambient occlusion, glass and paint
sheen, 2x2 anti-aliasing at 4x zoom, a soft shadow on the water, and
age-based weathering (plating seams, rust streaks, waterline grime). Ships
under way show a bow wave and stern wake (switched on `current_speed`).

Sister ships appear as variants under their class in the build list, each
with its own name on the hull; the three Coastal class Vancouver 2010 wraps
are all different (Coastal Inspiration's second side is a best guess).

Salish class hull art: each ship carries simplified, sprite-scale renderings
of its real livery by Coast Salish artists - Salish Orca by Darlene Gait
(Esquimalt Nation), Salish Eagle by John Marston (Stz'uminus First Nation),
Salish Raven by Thomas Cannell (Musqueam) and Salish Heron by Maynard
Johnny Jr. These are the artists' copyrighted works: this set is for
personal use, and it should not be published (e.g. on BaNaNaS) with them
without permission from BC Ferries and the artists.

Sprites are rendered procedurally from 3D models in `src/ships_models.py` (stats in `src/ships.py`)
(`src/render.py` is a small voxel renderer that outputs sprites in all 8 directions at 4x, then downsamples). Edit a model or stat there and rerun `make`.

Airline liveries, logos and the Air Canada, Alaska Airlines and WestJet marks
belong to those airlines; like the BC Ferries material, they are depicted
for personal use only.
