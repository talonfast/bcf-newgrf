PY    ?= .venv/bin/python
NMLC  ?= .venv/bin/nmlc
GRF    = bcferries.grf

all: $(GRF)

gfx/sprites.json: src/render.py src/ships.py src/ships_models.py src/pirate.py src/make_gfx.py $(wildcard src/decals/*.png)
	$(PY) src/make_gfx.py

gfx/objects.json: src/render.py src/buildings.py src/make_objects.py
	$(PY) src/make_objects.py

bcferries.nml lang/english.lng: gfx/sprites.json gfx/objects.json src/make_nml.py src/ships.py
	$(PY) src/make_nml.py

$(GRF): bcferries.nml lang/english.lng
	$(NMLC) -c --grf=$(GRF) bcferries.nml

preview: gfx/sprites.json
	$(PY) src/make_gfx.py --preview preview.png

install: $(GRF)
	cp $(GRF) "$(HOME)/Documents/OpenTTD/newgrf/"

setup:
	python3 -m venv .venv && .venv/bin/pip install nml pillow numpy

clean:
	rm -rf gfx bcferries.nml lang $(GRF) preview.png .nmlcache

.PHONY: all preview showcase scene install setup clean release

showcase: gfx/sprites.json
	$(PY) src/make_showcase.py showcase.png

VERSION := $(shell sed -n 's/^GRF_VERSION = //p' src/make_nml.py)
REL     := bcferries-v$(VERSION)

# releases/<name>.tar is what OpenTTD loads directly from its newgrf folder.
# COPYFILE_DISABLE keeps macOS from adding ._ metadata files to the tar.
release: $(GRF)
	rm -rf dist/$(REL) && mkdir -p dist/$(REL) releases
	cp $(GRF) dist/$(REL)/
	cp README.md dist/$(REL)/readme.txt
	cp CHANGELOG.txt dist/$(REL)/changelog.txt
	cp LICENSE.txt dist/$(REL)/license.txt
	cd dist && COPYFILE_DISABLE=1 tar --no-mac-metadata -cf ../releases/$(REL).tar $(REL)
	rm -rf dist
	@ls -la releases/$(REL).tar

scene: gfx/sprites.json gfx/objects.json
	$(PY) src/make_scene.py scene.png
