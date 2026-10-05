# One repo, five GRFs. Each set lives in its own folder: src/ (models, render and build scripts) and
# gfx/ (the rendered sprite sheets, committed). The GRFs are written directly by common/newgrf.
#   make                  build every GRF (re-rendering a set's gfx/ first when its models changed)
#   make vessels|terminals|aircraft|airports|coastal
#   make release          package releases/<set>-vN.tar for every set
#   make install          ... and copy them into OpenTTD's newgrf folder ($OPENTTD_NEWGRF)
#   make decals           regenerate shared logos/art in common/decals (macOS fonts)
#   make scenes showcase aircraft-preview seaplane-preview    preview images
# Without make: python build.py [set ...] and python tools/release.py [set ...] [--install] [--upload]

PY     := $(if $(wildcard .venv/bin/python),$(CURDIR)/.venv/bin/python,python3)
NEWGRF := build.py $(wildcard common/newgrf/*.py)
COMMON := common/render.py common/pirate.py common/newgrf/palette.py $(wildcard common/decals/*.png)
CLOUD  := common/pointcloud.py common/newgrf/palette.py common/newgrf/sprites.py
# Re-renders gfx/ only when the inputs' contents changed (file times alone change on every checkout).
RENDER := $(PY) tools/render_if_changed.py

all: vessels terminals aircraft airports coastal

# ---- vessels ---------------------------------------------------------------
vessels/gfx/sprites.json: $(COMMON) vessels/src/make_gfx.py vessels/src/ships.py vessels/src/ships_models.py
	$(RENDER) $@ vessels/src/make_gfx.py $^
vessels/bcferries.grf: vessels/gfx/sprites.json vessels/src/build_vessels.py vessels/src/ships.py vessels/src/ships_models.py $(NEWGRF)
	$(PY) build.py vessels
vessels: vessels/bcferries.grf

# ---- terminals -------------------------------------------------------------
terminals/gfx/objects.json: $(COMMON) terminals/src/buildings.py terminals/src/make_objects.py
	$(RENDER) $@ terminals/src/make_objects.py $^
terminals/bc-terminals.grf: terminals/gfx/objects.json terminals/src/build_terminals.py $(NEWGRF)
	$(PY) build.py terminals
terminals: terminals/bc-terminals.grf

# ---- aircraft (airliners, and the TGTFTD seaplanes and S-76) ---------------
aircraft/gfx/aircraft.json: $(COMMON) aircraft/src/aircraft.py aircraft/src/make_aircraft.py
	$(RENDER) $@ aircraft/src/make_aircraft.py $^
aircraft/gfx/seaplanes.json: $(CLOUD) aircraft/src/seaplanes.py aircraft/src/seaplane_sprites.py aircraft/src/make_seaplanes.py
	$(RENDER) $@ aircraft/src/make_seaplanes.py $^
aircraft/bc-aircraft.grf: aircraft/gfx/aircraft.json aircraft/gfx/seaplanes.json aircraft/src/build_aircraft.py $(NEWGRF)
	$(PY) build.py aircraft
aircraft: aircraft/bc-aircraft.grf

# ---- airports (objects, and the TGTFTD seaplane terminals) -----------------
airports/gfx/objects.json: $(COMMON) airports/src/airport_buildings.py airports/src/make_airports.py terminals/src/buildings.py terminals/src/make_objects.py
	$(RENDER) $@ airports/src/make_airports.py $^
airports/gfx/seaplane_terminals.json: $(CLOUD) airports/src/seaplane_terminals.py airports/src/seaplane_tiles.py airports/src/make_seaplane_terminals.py
	$(RENDER) $@ airports/src/make_seaplane_terminals.py $^
airports/bc-airports.grf: airports/gfx/objects.json airports/gfx/seaplane_terminals.json airports/src/build_airports.py $(NEWGRF)
	$(PY) build.py airports
airports: airports/bc-airports.grf

# ---- coastal waterfront ----------------------------------------------------
coastal/gfx/objects.json: $(COMMON) coastal/src/waterfront.py coastal/src/make_coastal.py terminals/src/buildings.py terminals/src/make_objects.py
	$(RENDER) $@ coastal/src/make_coastal.py $^
coastal/coastal-waterfront.grf: coastal/gfx/objects.json coastal/src/build_coastal.py $(NEWGRF)
	$(PY) build.py coastal
coastal: coastal/coastal-waterfront.grf

# ---- previews --------------------------------------------------------------
decals:
	$(PY) common/make_decals.py
showcase: vessels/gfx/sprites.json
	cd vessels && $(PY) src/make_showcase.py showcase.png
scenes: vessels/gfx/sprites.json terminals/gfx/objects.json
	cd terminals && $(PY) src/make_scene.py scene.png tsawwassen
	cd terminals && $(PY) src/make_scene.py scene_swartzbay.png swartzbay
	cd terminals && $(PY) src/make_scene.py scene_pender.png pender
	cd terminals && $(PY) src/make_scene.py ../coastal/scene_victoria.png victoria
aircraft-preview:
	cd aircraft && $(PY) src/make_aircraft.py --preview preview.png
seaplane-preview:
	$(PY) aircraft/src/preview_seaplanes.py
	$(PY) airports/src/preview_seaplane_terminals.py 4

# ---- releases --------------------------------------------------------------
release: all
	$(PY) tools/release.py
install: all
	$(PY) tools/release.py --install

setup:
	python3 -m venv .venv && .venv/bin/pip install pillow numpy scipy

clean:
	rm -f */*.grf
	rm -rf releases dist .grfcache

.PHONY: all vessels terminals aircraft airports coastal decals showcase scenes aircraft-preview seaplane-preview release install setup clean
