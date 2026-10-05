"""Real sprites: loading them from sprite sheets and encoding them for a container version 2 GRF.

A Sprite is one entry in the GRF with one or more representations (8bpp and/or 32bpp, at 1x, 2x
and/or 4x zoom). Sprite sheets are the PNG files in a set's gfx/ folder; each sprite in a sheet is
an entry [x, y, width, height, x_offs, y_offs].
"""

import hashlib
import struct

import numpy as np
from PIL import Image

from . import lz77
from .palette import DOS_PALETTE

ZOOM_CODE = {1: 0x00, 2: 0x02, 4: 0x01}
TYPE_RGB, TYPE_ALPHA, TYPE_PALETTE, TYPE_CHUNKED = 0x01, 0x02, 0x04, 0x08


class Rep:
    """One representation: depth 8 (H x W palette indices) or 32 (H x W x 4 RGBA)."""
    __slots__ = ("depth", "zoom", "pixels", "x_offs", "y_offs")

    def __init__(self, depth, zoom, pixels, x_offs, y_offs):
        self.depth, self.zoom, self.pixels, self.x_offs, self.y_offs = depth, zoom, pixels, x_offs, y_offs


class Sprite:
    def __init__(self, reps):
        self.reps = list(reps)


# ---------------------------------------------------------------------------------------- sheets

_sheets = {}


def _load_sheet(path):
    if path not in _sheets:
        im = Image.open(path)
        if im.mode == "P":
            _sheets[path] = (8, np.asarray(im, np.uint8))
        else:
            _sheets[path] = (32, np.asarray(im.convert("RGBA"), np.uint8))
    return _sheets[path]


def from_sheet(path, entry, zoom):
    depth, sheet = _load_sheet(path)
    x, y, w, h, xo, yo = entry
    return Rep(depth, zoom, sheet[y:y + h, x:x + w], xo, yo)


def sheet_sprites(base, entries):
    """Sprites from a set of sheets in the coastal-grflink layout.

    base: path without extension; entries: {"8bpp": [...], "1x": [...], "2x": [...], "4x": [...]}
    (any subset). 8bpp sheets at 2x / 4x are "8bpp_2x" / "8bpp_4x" -> base_8bpp_2x.png.
    """
    files = {"8bpp": (base + ".png", 1), "1x": (base + "_1x.png", 1), "2x": (base + "_2x.png", 2),
             "4x": (base + "_4x.png", 4), "8bpp_2x": (base + "_8bpp_2x.png", 2),
             "8bpp_4x": (base + "_8bpp_4x.png", 4)}
    count = {len(v) for v in entries.values()}
    if len(count) != 1:
        raise ValueError(f"{base}: zoom levels have different sprite counts")
    out = []
    for i in range(count.pop()):
        out.append(Sprite(from_sheet(files[k][0], entries[k][i], files[k][1]) for k in entries))
    return out


def save_sheet(items, path, depth):
    """items: [(pixels, x_offs, y_offs)] -> PNG sheet; returns the entries."""
    gap = 2
    width = sum(p.shape[1] for p, _, _ in items) + gap * (len(items) + 1)
    height = max(p.shape[0] for p, _, _ in items) + gap * 2
    sheet = np.zeros((height, width) + ((4,) if depth == 32 else ()), np.uint8)
    entries = []
    x = gap
    for pixels, xo, yo in items:
        h, w = pixels.shape[:2]
        sheet[gap:gap + h, x:x + w] = pixels
        entries.append([x, gap, w, h, int(xo), int(yo)])
        x += w + gap
    if depth == 8:
        im = Image.frombytes("P", (width, height), np.ascontiguousarray(sheet).tobytes())
        im.putpalette([c for rgb in DOS_PALETTE for c in rgb])
    else:
        im = Image.fromarray(sheet, "RGBA")
    im.save(path, optimize=True)
    return entries


# -------------------------------------------------------------------------------------- encoding

def normalise(rep):
    """Crop to the visible pixels; clear the colour of fully transparent 32bpp pixels."""
    px = rep.pixels
    if rep.depth == 32:
        px = np.where(px[..., 3:4] == 0, 0, px).astype(np.uint8)
        mask = px[..., 3] != 0
    else:
        mask = px != 0
    rows = np.flatnonzero(mask.any(axis=1))
    cols = np.flatnonzero(mask.any(axis=0))
    if len(rows) == 0:
        return Rep(rep.depth, rep.zoom, px[:1, :1] * 0, 0, 0)
    y0, y1, x0, x1 = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
    return Rep(rep.depth, rep.zoom, np.ascontiguousarray(px[y0:y1, x0:x1]),
               rep.x_offs + int(x0), rep.y_offs + int(y0))


def content_key(rep):
    h = hashlib.sha1()
    h.update(struct.pack("<BBhh", rep.depth, rep.zoom, rep.x_offs, rep.y_offs))
    h.update(struct.pack("<II", *rep.pixels.shape[:2]))
    h.update(rep.pixels.tobytes())
    return h.digest()


def _chunked(px, depth, width, height):
    """Rows of opaque runs. Returns the uncompressed chunked data."""
    bpp = 1 if depth == 8 else 4
    flat = px.reshape(height, width, bpp)
    opaque = (flat[..., -1] if depth == 32 else flat[..., 0]) != 0
    long_runs = width > 256
    max_run = 0x7FFF if long_runs else 0x7F
    rows = []
    for y in range(height):
        row = bytearray()
        o = opaque[y]
        xs = np.flatnonzero(np.diff(np.concatenate([[0], o.astype(np.int8), [0]])))
        runs = []
        for start, end in zip(xs[0::2], xs[1::2]):
            for s in range(start, end, max_run):
                runs.append((s, min(end, s + max_run)))
        if not runs:
            runs = [(0, 0)]
        for k, (s, e) in enumerate(runs):
            last = k == len(runs) - 1
            n = e - s
            if long_runs:
                row += struct.pack("<HH", n | (0x8000 if last else 0), s)
            else:
                row += bytes([n | (0x80 if last else 0), s])
            row += flat[y, s:e].tobytes()
        rows.append(bytes(row))
    # OpenTTD reads 4 byte row offsets exactly when the data is larger than 64 KiB.
    body = sum(len(r) for r in rows)
    osize = 2 if 2 * height + body <= 0xFFFF else 4
    offsets = []
    off = osize * height
    for r in rows:
        offsets.append(off)
        off += len(r)
    table = struct.pack("<%d%s" % (height, "H" if osize == 2 else "I"), *offsets)
    return table + b"".join(rows)


def encode(rep):
    """Encode one (normalised) representation -> sprite data section body (without ID/length)."""
    px = rep.pixels
    h, w = px.shape[:2]
    if rep.depth == 32:
        base = TYPE_RGB | TYPE_ALPHA
    else:
        base = TYPE_PALETTE
    head = lambda t: struct.pack("<BBHHhh", t, ZOOM_CODE[rep.zoom], h, w, rep.x_offs, rep.y_offs)  # noqa: E731
    chunked_raw = _chunked(px, rep.depth, w, h)
    chunked = head(base | TYPE_CHUNKED) + struct.pack("<I", len(chunked_raw)) + lz77.compress(chunked_raw)
    if rep.depth == 32 and len(chunked_raw) < px.nbytes:
        return chunked
    plain = head(base) + lz77.compress(px.tobytes())
    return chunked if len(chunked) < len(plain) else plain
