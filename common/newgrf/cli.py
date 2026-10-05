"""Command line for the per-set build scripts: python src/build_<set>.py [output.grf] [--jobs N]"""

import argparse


def output(default):
    ap = argparse.ArgumentParser()
    ap.add_argument("output", nargs="?", default=default)
    ap.add_argument("--jobs", type=int, default=None, help="sprite encoding processes (default: all cores)")
    args = ap.parse_args()
    return args.output, args.jobs
