"""Pirate Pak box geometry, shared by the 3D model and the side artwork.

u runs from -L/2 (the flat stern deck: dessert / coleslaw tub and gold coin)
to +L/2 (the curved prow: drink cup and sail). Heights in OpenTTD units.
"""
import numpy as np

L = 14.0
B = 4.4
H_WELL = 3.4          # side walls of the open middle well
H_DECK = 4.4          # raised printed decks at both ends
H_TIP = 7.6           # top of the curved prow
STERN_END = -3.4      # stern deck spans -L/2 .. STERN_END
PROW_START = 2.2      # prow deck spans PROW_START .. L/2
CURVE_START = 4.6     # prow walls curve up from here to the tip


def profile(u):
    """Height of the box top (walls / decks) along the hull."""
    u = np.asarray(u, dtype=np.float32)
    t = np.clip((u - CURVE_START) / (L / 2 - CURVE_START), 0, 1)
    h = np.where(u < STERN_END, H_DECK, H_WELL)
    h = np.where(u >= PROW_START, H_DECK + (H_TIP - H_DECK) * t ** 1.8, h)
    return h
