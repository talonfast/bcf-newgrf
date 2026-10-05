"""Read a container version 2 GRF: pseudo sprites and decoded real sprites.

    entries, sprites = read(path)

entries: list of bytes (pseudo sprite) or int (real sprite ID, a key of sprites).
sprites: {id: [Representation]} where a Representation has depth (8 or 32), zoom (1, 2, 4),
x_offs, y_offs and pixels (H x W uint8 palette indices, or H x W x 4 RGBA; with a mask channel
H x W x 5).
"""

import struct
from dataclasses import dataclass

import numpy as np

from .lz77 import decompress as unlz77

SIGNATURE = b"\x00\x00GRF\x82\x0d\x0a\x1a\x0a"
ZOOM = {0x00: 1, 0x02: 2, 0x01: 4}


@dataclass
class Representation:
    depth: int
    zoom: int
    x_offs: int
    y_offs: int
    pixels: np.ndarray
    stored: int = 0  # bytes this representation takes in the file


def bytes_per_pixel(typ):
    n = 0
    if typ & 0x01:
        n += 3
    if typ & 0x02:
        n += 1
    if typ & 0x04:
        n += 1
    return n


def unchunk(raw, typ, w, h):
    """Tile-compressed ("chunked") sprite data -> H x W x bpp, transparent where not coded."""
    bpp = bytes_per_pixel(typ)
    out = np.zeros((h, w, bpp), np.uint8)
    long_offsets = len(raw) > 0xFFFF
    long_runs = w > 256
    for y in range(h):
        (off,) = struct.unpack_from("<I", raw, y * 4) if long_offsets else struct.unpack_from("<H", raw, y * 2)
        while True:
            if long_runs:
                hdr, skip = struct.unpack_from("<HH", raw, off)
                off += 4
                last, n = hdr & 0x8000, hdr & 0x7FFF
            else:
                hdr, skip = raw[off], raw[off + 1]
                off += 2
                last, n = hdr & 0x80, hdr & 0x7F
            out[y, skip:skip + n] = np.frombuffer(raw, np.uint8, n * bpp, off).reshape(n, bpp)
            off += n * bpp
            if last:
                break
    return out


def decode_sprite(data, pos, length):
    typ, zoom, h, w, xo, yo = struct.unpack_from("<BBHHhh", data, pos)
    p = pos + 10
    end = pos + length
    bpp = bytes_per_pixel(typ)
    if typ & 0x08:
        (size,) = struct.unpack_from("<I", data, p)
        p += 4
        raw, p = unlz77(data, p, size)
        px = unchunk(raw, typ, w, h)
    else:
        raw, p = unlz77(data, p, w * h * bpp)
        px = np.frombuffer(raw, np.uint8).reshape(h, w, bpp)
    if p != end:
        raise ValueError("sprite data length mismatch")
    if typ & 0x03:
        depth = 32
        if not typ & 0x02:  # RGB without alpha: opaque
            px = np.concatenate([px[..., :3], np.full((h, w, 1), 255, np.uint8), px[..., 3:]], axis=2)
    else:
        depth = 8
        px = px[..., 0]
    return Representation(depth, ZOOM[zoom], xo, yo, px.copy(), length)


def read(path, decode_sprites=True):
    data = open(path, "rb").read()
    if data[:10] != SIGNATURE:
        raise ValueError(f"{path}: not a container version 2 GRF")
    (offset,) = struct.unpack_from("<I", data, 10)
    data_start = 14 + offset
    pos = 15
    entries = []
    while True:
        (n,) = struct.unpack_from("<I", data, pos)
        pos += 4
        if n == 0:
            break
        kind = data[pos]
        if kind == 0xFF:
            entries.append(bytes(data[pos + 1:pos + 1 + n]))
        elif kind == 0xFD:
            entries.append(struct.unpack_from("<I", data, pos + 1)[0])
        else:
            raise ValueError(f"unexpected sprite kind {kind:#x}")
        pos += 1 + n
    entries = entries[1:]  # sprite count
    if pos != data_start:
        raise ValueError("main section length mismatch")
    sprites = {}
    while True:
        (sid,) = struct.unpack_from("<I", data, pos)
        pos += 4
        if sid == 0:
            break
        (length,) = struct.unpack_from("<I", data, pos)
        pos += 4
        if decode_sprites:
            sprites.setdefault(sid, []).append(decode_sprite(data, pos, length))
        else:
            typ, zoom = data[pos], data[pos + 1]
            sprites.setdefault(sid, []).append(Representation(32 if typ & 3 else 8, ZOOM[zoom], 0, 0, None, length))
        pos += length
    if pos != len(data):
        raise ValueError("trailing bytes")
    return entries, sprites
