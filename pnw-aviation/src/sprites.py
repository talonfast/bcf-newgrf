"""Scale of the aircraft graphics and helpers to turn models into GRF sprites."""

from grf import RealSprite
from render import HEADINGS, render

# 1 OpenTTD world unit (1/16 tile) = 1.6 m horizontally; 1.6 height pixels per metre vertically.
METRES_PER_UNIT = 1.6
Z_PER_METRE = 1.6
ZOOMS = (1, 2, 4)


ROTOR_Z_OFFSET = 5  # the rotor vehicle sits 5 height pixels above the helicopter


def rotor_sprites(models):
    """Rotor sprites (stopped + 3 moving frames): direction independent, positioned relative to the rotor vehicle."""
    out = []
    for model in models:
        cloud = model.cloud_for_heading(HEADINGS[0], METRES_PER_UNIT, Z_PER_METRE)
        cloud.pos[:, 2] -= ROTOR_Z_OFFSET
        out.append(RealSprite({z: render(cloud, z) for z in ZOOMS}))
    return out


def aircraft_sprites(model):
    """8 RealSprites (N, NE, E, SE, S, SW, W, NW) with 1x, 2x and 4x zoom levels."""
    surf = model.surface()
    out = []
    for h in HEADINGS:
        cloud = model.cloud_for_heading(h, METRES_PER_UNIT, Z_PER_METRE, surf)
        out.append(RealSprite({z: render(cloud, z) for z in ZOOMS}))
    return out
