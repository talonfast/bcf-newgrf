![Coastal GrfLink](docs/coastal-grflink.png)

OpenTTD NewGRFs for coastal British Columbia: the BC Ferries fleet and its
terminals, plus the airlines and airports that connect the coast. Plain
NewGRF (NML), for OpenTTD 13+ and JGR's Patch Pack. One repo, separate GRFs
so you can load only what you want:

| Set | Folder | GRF | GRF ID |
|---|---|---|---|
| BC Ferries: Vessels | `vessels/` | `bcferries.grf` | `TFBC` |
| BC Ferries: Terminals | `terminals/` | `bc-terminals.grf` | `TFBT` |
| BC Aviation: Aircraft | `aircraft/` | `bc-aircraft.grf` | `TFBA` |
| BC Aviation: Airports (YVR, YYJ) | `airports/` | `bc-airports.grf` | `TFBY` |
| Coastal: Waterfront | `coastal/` | `coastal-waterfront.grf` | `TFBW` |

Shared code lives in `common/`: the voxel renderer (`render.py`), NML helpers,
and the logo/livery artwork in `common/decals/`.

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

## Coastal: Waterfront
Object classes **Waterfront: Victoria**, **Waterfront: Vancouver** and
**Waterfront: docks & marinas**. Water objects are placed on water tiles.

| Object | Tiles | Notes |
|---|---|---|
| Float home | 1x1, water | Fisherman's Wharf; four random colour/shape variants |
| Fish & chips float | 1x1, water | take-out shack, picnic tables, umbrellas |
| Fisgard Lighthouse | 1x1 | tower, red lantern, red-brick keeper's house, rocky islet |
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
```
make setup        # one time: .venv with nml, pillow, numpy
make              # build every GRF (or: make vessels / terminals / aircraft / airports / coastal)
make release      # releases/<set>-vN.tar for each set
make install      # copy the release tars into OpenTTD's newgrf folder
make scenes showcase aircraft-preview    # preview images
make decals       # regenerate common/decals artwork (macOS fonts)
```
Bump the set's version (`GRF_VERSION` in `vessels/src/make_nml.py`,
`VERSION` in `terminals/src/make_nml_terminals.py`,
`aircraft/src/make_aircraft.py`, `airports/src/make_airports.py` and
`coastal/src/make_coastal.py`) and add a line to its `CHANGELOG.txt` before
releasing.

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
