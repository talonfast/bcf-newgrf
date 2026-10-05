"""Build the GRFs from the rendered sprites in each set's gfx/ folder.

    python build.py                      # every set
    python build.py vessels aircraft     # some sets
    python build.py --list               # set names, GRF files and versions

Each GRF is written next to its set (vessels/bcferries.grf, ...). Needs Python 3.10+ with numpy and
Pillow. Sprite encoding is cached in .grfcache/, so rebuilds only encode what changed.
"""
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))

# name: (folder, build script, GRF file, release name, file holding VERSION)
SETS = {
    "vessels": ("vessels", "src/build_vessels.py", "bcferries.grf", "bcferries", "src/build_vessels.py"),
    "terminals": ("terminals", "src/build_terminals.py", "bc-terminals.grf", "bc-terminals", "src/build_terminals.py"),
    "aircraft": ("aircraft", "src/build_aircraft.py", "bc-aircraft.grf", "bc-aircraft", "src/build_aircraft.py"),
    "airports": ("airports", "src/build_airports.py", "bc-airports.grf", "bc-airports", "src/build_airports.py"),
    "coastal": ("coastal", "src/build_coastal.py", "coastal-waterfront.grf", "coastal-waterfront", "src/build_coastal.py"),
}


def version(name):
    folder, _, _, _, vfile = SETS[name]
    with open(os.path.join(ROOT, folder, vfile)) as f:
        return int(re.search(r"^VERSION = (\d+)", f.read(), re.M).group(1))


def grf_path(name):
    folder, _, grf, _, _ = SETS[name]
    return os.path.join(ROOT, folder, grf)


def build(names, extra=()):
    for name in names:
        folder, script, grf, _, _ = SETS[name]
        t = time.time()
        print(f"== {name}", flush=True)
        subprocess.run([sys.executable, os.path.join(ROOT, folder, script), grf_path(name), *extra],
                       check=True)
        print(f"   {name} done in {time.time() - t:.0f}s", flush=True)


def main():
    args = sys.argv[1:]
    if "--list" in args:
        for name in SETS:
            print(f"{name:10} {SETS[name][0] + '/' + SETS[name][2]:34} v{version(name)}")
        return
    extra = [a for a in args if a.startswith("--")]
    names = [a for a in args if not a.startswith("--")] or list(SETS)
    unknown = [n for n in names if n not in SETS]
    if unknown:
        sys.exit(f"unknown set(s) {', '.join(unknown)}; sets: {', '.join(SETS)}")
    build(names, extra)


if __name__ == "__main__":
    main()
