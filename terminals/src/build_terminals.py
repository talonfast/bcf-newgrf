"""Build bc-terminals.grf from src/make_objects.py's OBJECTS and the rendered gfx/.

Usage: python src/build_terminals.py [output.grf]
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "common"))
from make_objects import OBJECTS  # noqa: E402
from newgrf import GRF, cli  # noqa: E402
from newgrf.objects import add_objects, load_meta  # noqa: E402

VERSION = 2
NAME = "BC Ferries: Terminals {SILVER}v%d" % VERSION
DESCRIPTION = ("Terminal objects for Tsawwassen, Swartz Bay and the Southern Gulf Islands: buildings, toll "
               "plazas, holding lanes, berths, walkways, foot-passenger areas, The Stand at Otter Bay and "
               "island forest. Use with BC Ferries: Vessels.")

# cls -> (class label, unused, class name)
CLASSES = {None: ("BCFT", None, "BC Ferries: Tsawwassen"),
           "sb": ("BCFS", None, "BC Ferries: Swartz Bay"),
           "isl": ("BCFI", None, "BC Ferries: Gulf Islands")}


def build(path, jobs=None):
    grf = GRF("TFBT", NAME, DESCRIPTION, VERSION, 1)
    add_objects(grf, OBJECTS, load_meta(os.path.join(ROOT, "gfx", "objects.json")), CLASSES,
                os.path.join(ROOT, "gfx"))
    grf.write(path, jobs)


if __name__ == "__main__":
    build(*cli.output(os.path.join(ROOT, "bc-terminals.grf")))
