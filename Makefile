# One repo, four GRFs. Each set lives in its own folder with src/, gfx/, lang/.
#   make                  build every GRF
#   make vessels|terminals|aircraft
#   make decals           regenerate shared logos/art in common/decals (macOS fonts)
#   make scenes showcase  preview images
#   make release          package releases/<set>-vN.tar for every set
#   make install          copy the release tars into OpenTTD's newgrf folder

PY    := $(CURDIR)/.venv/bin/python
NMLC  := $(CURDIR)/.venv/bin/nmlc
COMMON := common/render.py common/nmlcommon.py common/pirate.py $(wildcard common/decals/*.png)

V_GRF := vessels/bcferries.grf
T_GRF := terminals/bc-terminals.grf
A_GRF := aircraft/bc-aircraft.grf

all: vessels terminals aircraft airports coastal
vessels: $(V_GRF)
terminals: $(T_GRF)
aircraft: $(A_GRF)

# ---- vessels ---------------------------------------------------------------
vessels/gfx/sprites.json: $(COMMON) $(wildcard vessels/src/*.py)
	cd vessels && $(PY) src/make_gfx.py
vessels/bcferries.nml: vessels/gfx/sprites.json vessels/src/make_nml.py vessels/src/ships.py
	cd vessels && $(PY) src/make_nml.py
$(V_GRF): vessels/bcferries.nml
	cd vessels && $(NMLC) -c --grf=bcferries.grf bcferries.nml

# ---- terminals -------------------------------------------------------------
terminals/gfx/objects.json: $(COMMON) terminals/src/buildings.py terminals/src/make_objects.py
	cd terminals && $(PY) src/make_objects.py
terminals/bc-terminals.nml: terminals/gfx/objects.json terminals/src/make_nml_terminals.py
	cd terminals && $(PY) src/make_nml_terminals.py
$(T_GRF): terminals/bc-terminals.nml
	cd terminals && $(NMLC) -c --grf=bc-terminals.grf bc-terminals.nml

# ---- aircraft --------------------------------------------------------------
aircraft/bc-aircraft.nml: $(COMMON) $(wildcard aircraft/src/*.py)
	cd aircraft && $(PY) src/make_aircraft.py
$(A_GRF): aircraft/bc-aircraft.nml
	cd aircraft && $(NMLC) -c --grf=bc-aircraft.grf bc-aircraft.nml

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

# ---- releases --------------------------------------------------------------
V_VER := $(shell sed -n 's/^GRF_VERSION = //p' vessels/src/make_nml.py)
T_VER := $(shell sed -n 's/^VERSION = //p' terminals/src/make_nml_terminals.py)
A_VER := $(shell sed -n 's/^VERSION = //p' aircraft/src/make_aircraft.py)

# $(call pack,setdir,grf,relname)
define pack
	rm -rf dist/$(3) && mkdir -p dist/$(3) releases
	cp $(1)/$(2) dist/$(3)/
	cp README.md dist/$(3)/readme.txt
	cp $(1)/CHANGELOG.txt dist/$(3)/changelog.txt
	cp LICENSE.txt dist/$(3)/license.txt
	cd dist && COPYFILE_DISABLE=1 tar --no-mac-metadata -cf ../releases/$(3).tar $(3)
	rm -rf dist
	@ls -la releases/$(3).tar
endef

release: all
	$(call pack,vessels,bcferries.grf,bcferries-v$(V_VER))
	$(call pack,terminals,bc-terminals.grf,bc-terminals-v$(T_VER))
	$(call pack,aircraft,bc-aircraft.grf,bc-aircraft-v$(A_VER))
	$(call pack,airports,bc-airports.grf,bc-airports-v$(P_VER))
	$(call pack,coastal,coastal-waterfront.grf,coastal-waterfront-v$(W_VER))

install: release
	cp releases/bcferries-v$(V_VER).tar releases/bc-terminals-v$(T_VER).tar \
	   releases/bc-aircraft-v$(A_VER).tar releases/bc-airports-v$(P_VER).tar \
	   releases/coastal-waterfront-v$(W_VER).tar \
	   "$(HOME)/Documents/OpenTTD/newgrf/"

setup:
	python3 -m venv .venv && .venv/bin/pip install nml pillow numpy

clean:
	rm -rf */gfx */*.nml */*.grf */.nmlcache */lang releases dist

.PHONY: all vessels terminals aircraft decals showcase scenes aircraft-preview release install setup clean

# ---- airports --------------------------------------------------------------
P_GRF := airports/bc-airports.grf
P_VER := $(shell sed -n 's/^VERSION = //p' airports/src/make_airports.py)
airports: $(P_GRF)
airports/bc-airports.nml: $(COMMON) $(wildcard airports/src/*.py) terminals/src/buildings.py
	cd airports && $(PY) src/make_airports.py
$(P_GRF): airports/bc-airports.nml
	cd airports && $(NMLC) -c --grf=bc-airports.grf bc-airports.nml
.PHONY: airports

# ---- coastal waterfront ----------------------------------------------------
W_GRF := coastal/coastal-waterfront.grf
W_VER := $(shell sed -n 's/^VERSION = //p' coastal/src/make_coastal.py)
coastal: $(W_GRF)
coastal/coastal-waterfront.nml: $(COMMON) $(wildcard coastal/src/*.py) terminals/src/buildings.py
	cd coastal && $(PY) src/make_coastal.py
$(W_GRF): coastal/coastal-waterfront.nml
	cd coastal && $(NMLC) -c --grf=coastal-waterfront.grf coastal-waterfront.nml
.PHONY: coastal

# ---- PNW Aviation (TGTFTD seaplanes; own GRF writer, no NML) ---------------
pnw-aviation:
	cd pnw-aviation/src && $(PY) build.py
.PHONY: pnw-aviation
