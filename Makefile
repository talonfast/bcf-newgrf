PY    ?= .venv/bin/python
NMLC  ?= .venv/bin/nmlc
GRF    = bcferries.grf

all: $(GRF)

gfx/sprites.json: src/render.py src/ships.py src/ships_models.py src/pirate.py src/make_gfx.py $(wildcard src/decals/*.png)
	$(PY) src/make_gfx.py

bcferries.nml lang/english.lng: gfx/sprites.json src/make_nml.py src/ships.py
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

.PHONY: all preview showcase install setup clean

showcase: gfx/sprites.json
	$(PY) src/make_showcase.py showcase.png
