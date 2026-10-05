"""Build coastal-waterfront.grf from src/make_coastal.py's OBJECTS and the rendered gfx/.

Usage: python src/build_coastal.py [output.grf]
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "common"))
from make_coastal import CLASSES, OBJECTS  # noqa: E402
from newgrf import GRF, cli  # noqa: E402
from newgrf.objects import add_objects, load_meta  # noqa: E402

VERSION = 1
NAME = "Coastal: Waterfront {SILVER}v%d" % VERSION
DESCRIPTION = ("Waterfront objects for Victoria and Vancouver: Fisherman's Wharf float homes and fish & chips "
               "float, Fisgard Lighthouse, Granville Island Public Market, the Giants silos, artisan sheds, "
               "seawall, floating docks, marinas and harbour ferry docks. Float homes, docks and marinas go on "
               "water tiles.")


def build(path, jobs=None):
    grf = GRF("TFBW", NAME, DESCRIPTION, VERSION, 1)
    add_objects(grf, OBJECTS, load_meta(os.path.join(ROOT, "gfx", "objects.json")), CLASSES,
                os.path.join(ROOT, "gfx"))
    grf.write(path, jobs)


if __name__ == "__main__":
    build(*cli.output(os.path.join(ROOT, "coastal-waterfront.grf")))
