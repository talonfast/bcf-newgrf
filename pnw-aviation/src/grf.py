"""
Minimal NewGRF (container version 2) writer.

Pseudo sprites (actions) are written to the main section. Real sprites go to the
sprite data section and are referenced from the main section by ID, so one
sprite can carry several zoom levels (1x, 2x, 4x).
"""

import struct

GRF_V2_SIG = b"\x00\x00GRF\x82\x0d\x0a\x1a\x0a"

# Zoom level byte of a sprite data section entry.
ZOOM_1X = 0x00
ZOOM_4X = 0x01
ZOOM_2X = 0x02
ZOOM_CODE = {1: ZOOM_1X, 2: ZOOM_2X, 4: ZOOM_4X}

SPRITE_TYPE_PALETTE = 0x04  # 8bpp palette data, no tile compression


def b(*values: int) -> bytes:
    return bytes(values)


def w(value: int) -> bytes:
    return struct.pack("<H", value & 0xFFFF)


def d(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)


def ext(value: int) -> bytes:
    """Extended byte: one byte, or FF followed by a word."""
    return bytes([value]) if value < 0xFF else b"\xff" + w(value)


def text(s: str) -> bytes:
    return s.encode("utf-8") + b"\x00"


def lz77(data: bytes) -> bytes:
    """Compress with the TTD LZ77 variant: literal runs (1..128) and back references (3..16 bytes, offset 1..2047)."""
    out = bytearray()
    literals = bytearray()
    n = len(data)
    i = 0
    index: dict[bytes, list[int]] = {}

    def flush():
        pos = 0
        while pos < len(literals):
            chunk = literals[pos:pos + 128]
            out.append(len(chunk) & 0x7F)  # 128 is encoded as 0
            out.extend(chunk)
            pos += 128
        literals.clear()

    while i < n:
        best_len = 0
        best_off = 0
        if i + 3 <= n:
            key = data[i:i + 3]
            for j in reversed(index.get(key, [])):
                off = i - j
                if off > 2047:
                    break
                length = 3
                while length < 16 and i + length < n and data[j + length] == data[i + length]:
                    length += 1
                if length > best_len:
                    best_len, best_off = length, off
                    if length == 16:
                        break
        if best_len >= 3:
            flush()
            out.append(((-best_len << 3) | (best_off >> 8)) & 0xFF)
            out.append(best_off & 0xFF)
            step = best_len
        else:
            literals.append(data[i])
            step = 1
        for k in range(i, min(i + step, n - 2)):
            index.setdefault(data[k:k + 3], []).append(k)
        i += step
    flush()
    return bytes(out)


class RealSprite:
    """One sprite, possibly with several zoom levels: {zoom: (pixels 2D uint8 array, x_offs, y_offs)}."""

    def __init__(self, levels: dict):
        self.levels = levels


class GRFWriter:
    def __init__(self):
        self.entries: list[bytes | RealSprite] = []

    def pseudo(self, data: bytes):
        self.entries.append(data)

    def real(self, sprite: RealSprite):
        self.entries.append(sprite)

    def build(self) -> bytes:
        main = bytearray()
        data = bytearray()
        count = len(self.entries)
        main += d(4) + b"\xff" + d(count)
        sprite_id = 0
        for e in self.entries:
            if isinstance(e, bytes):
                main += d(len(e)) + b"\xff" + e
            else:
                sprite_id += 1
                main += d(4) + b"\xfd" + d(sprite_id)
                for zoom in sorted(e.levels):
                    pixels, xo, yo = e.levels[zoom]
                    h, wd = pixels.shape
                    payload = lz77(pixels.astype("uint8").tobytes())
                    body = b(SPRITE_TYPE_PALETTE, ZOOM_CODE[zoom]) + w(h) + w(wd) + w(xo) + w(yo) + payload
                    data += d(sprite_id) + d(len(body)) + body
        main += d(0)
        data += d(0)
        header = GRF_V2_SIG
        # Offset of the sprite data section, relative to the end of this field; then compression byte 0.
        section_offset = 1 + len(main)
        return header + d(section_offset) + b"\x00" + bytes(main) + bytes(data)
