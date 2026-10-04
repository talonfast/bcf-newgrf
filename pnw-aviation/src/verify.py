"""Decode a container v2 GRF written by grf.py and check its structure and sprite data: python verify.py file.grf"""

import struct
import sys

import numpy as np


def unlz77(data, pos, size):
    out = bytearray()
    while len(out) < size:
        code = data[pos]
        pos += 1
        if code < 0x80:
            n = code or 0x80
            out += data[pos:pos + n]
            pos += n
        else:
            c = code - 256
            off = ((c & 7) << 8) | data[pos]
            pos += 1
            n = -(c >> 3)
            for _ in range(n):
                out.append(out[-off])
    assert len(out) == size, (len(out), size)
    return bytes(out), pos


def main(path):
    data = open(path, "rb").read()
    assert data[:10] == b"\x00\x00GRF\x82\x0d\x0a\x1a\x0a", "bad signature"
    (offset,) = struct.unpack_from("<I", data, 10)
    data_start = 14 + offset
    assert data[14] == 0, "compression byte"
    pos = 15
    (n, kind) = struct.unpack_from("<IB", data, pos)
    assert n == 4 and kind == 0xFF
    (count,) = struct.unpack_from("<I", data, pos + 5)
    pos += 9
    pseudo, refs = 0, []
    actions = {}
    while True:
        (n,) = struct.unpack_from("<I", data, pos)
        pos += 4
        if n == 0:
            break
        kind = data[pos]
        if kind == 0xFF:
            act = data[pos + 1]
            actions[act] = actions.get(act, 0) + 1
            pseudo += 1
        else:
            assert kind == 0xFD and n == 4
            refs.append(struct.unpack_from("<I", data, pos + 1)[0])
        pos += 1 + n
    assert pos == data_start, f"main section ends at {pos}, data section at {data_start}"
    assert pseudo + len(refs) == count, (pseudo, len(refs), count)

    sprites = {}
    while True:
        (sid,) = struct.unpack_from("<I", data, pos)
        pos += 4
        if sid == 0:
            break
        (length, typ, zoom, h, w, xo, yo) = struct.unpack_from("<IBBHHhh", data, pos)
        body_end = pos + 4 + length
        px, end = unlz77(data, pos + 4 + 10, w * h)
        assert end == body_end, f"sprite {sid}: compressed data size mismatch"
        sprites.setdefault(sid, {})[zoom] = (np.frombuffer(px, np.uint8).reshape(h, w), xo, yo)
        pos = body_end
    assert pos == len(data), "trailing bytes"
    missing = [r for r in refs if r not in sprites]
    assert not missing, f"missing sprites {missing[:5]}"
    zl = {k: sorted(v) for k, v in sprites.items()}
    print(f"OK: {pseudo} pseudo sprites {dict(sorted(actions.items()))}, {len(refs)} real sprites, "
          f"zoom levels per sprite: {sorted(set(map(tuple, zl.values())))}")
    return sprites


if __name__ == "__main__":
    main(sys.argv[1])
