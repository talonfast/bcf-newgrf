"""Download the official vector logos (SVG) used for liveries and signage
into common/logos/, and rasterise each to a large transparent PNG.

Sources: Wikimedia Commons, English Wikipedia (non-free logos) and Wikinews.
Rasterising: macOS Quick Look (qlmanage); white backgrounds are keyed out.
These are trademarks of their owners - personal use only (see LICENSE.txt).

Usage: python common/fetch_logos.py
"""
import os
import subprocess
import time
import urllib.parse
import urllib.error
import urllib.request

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "logos")
UA = {"User-Agent": "coastal-grflink-logo-fetch/1.0"}

LOGOS = {
    "bcferries": ("en.wikipedia.org", "BC Ferries Logo.svg"),
    "aircanada": ("commons.wikimedia.org", "Air Canada logo.svg"),
    "aircanada_express": ("commons.wikimedia.org", "Air Canada Express logo.svg"),
    "alaska": ("commons.wikimedia.org", "Alaska Airlines logo.svg"),
    "horizon": ("commons.wikimedia.org", "Horizon Air Logo.svg"),
    "westjet": ("commons.wikimedia.org", "WestJetLogo2018.svg"),
    "vancouver2010": ("url", "https://upload.wikimedia.org/wikinews/en/a/a7/2010_Winter_Olympics_logo.svg"),
}


def fetch(url, path, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req) as r, open(path, "wb") as f:
                f.write(r.read())
            return
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == tries - 1:
                raise
            time.sleep(10 * (i + 1))                  # Wikimedia rate limit: back off


def rasterise(svg, png, size=2000):
    subprocess.run(["qlmanage", "-t", "-s", str(size), "-o", OUT, svg], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ql = svg + ".png"
    im = Image.open(os.path.join(OUT, os.path.basename(ql))).convert("RGBA")
    a = np.array(im).astype(np.int32)
    white = (a[..., :3].min(-1) > 245)
    a[white, 3] = 0                                   # key out the white page
    im = Image.fromarray(a.astype(np.uint8))
    im = im.crop(im.getbbox())
    im.save(png)
    os.remove(os.path.join(OUT, os.path.basename(ql)))


def main():
    os.makedirs(OUT, exist_ok=True)
    for key, (site, name) in LOGOS.items():
        svg = os.path.join(OUT, key + ".svg")
        if os.path.exists(os.path.join(OUT, key + ".png")):
            continue
        if site == "url":
            url = name
        else:
            url = "https://%s/wiki/Special:FilePath/%s" % (site, urllib.parse.quote(name))
        fetch(url, svg)
        rasterise(svg, os.path.join(OUT, key + ".png"))
        print("fetched", key, Image.open(os.path.join(OUT, key + ".png")).size)
        time.sleep(4)


if __name__ == "__main__":
    main()
