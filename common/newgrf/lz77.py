"""The TTD LZ77 variant used for GRF sprite data.

Literal runs of 1..128 bytes, and back references of 3..16 bytes at offsets 1..2047.
"""

from bisect import bisect_left

MAX_OFFSET = 2047
MAX_LENGTH = 16


def compress(data: bytes) -> bytes:
    out = bytearray()
    literals = bytearray()
    n = len(data)
    index: dict[bytes, list[int]] = {}

    def flush():
        for pos in range(0, len(literals), 128):
            chunk = literals[pos:pos + 128]
            out.append(len(chunk) & 0x7F)  # 128 is written as 0
            out.extend(chunk)
        literals.clear()

    def longest(i):
        best_len = best_off = 0
        for j in reversed(index.get(data[i:i + 3], ())):
            off = i - j
            if off > MAX_OFFSET:
                break
            length = 3
            limit = min(MAX_LENGTH, n - i)
            while length < limit and data[j + length] == data[i + length]:
                length += 1
            if length > best_len:
                best_len, best_off = length, off
                if length == limit:
                    break
        return best_len, best_off

    def add(k):
        if k + 3 <= n:
            lst = index.setdefault(data[k:k + 3], [])
            lst.append(k)
            if len(lst) > 64 and k - lst[0] > MAX_OFFSET:  # forget positions that are out of reach
                del lst[:bisect_left(lst, k - MAX_OFFSET)]

    i = 0
    while i < n:
        length, off = longest(i) if i + 3 <= n else (0, 0)
        if length >= 3:
            flush()
            out.append(((-length << 3) | (off >> 8)) & 0xFF)
            out.append(off & 0xFF)
            for k in range(i, i + length):
                add(k)
            i += length
        else:
            literals.append(data[i])
            add(i)
            i += 1
    flush()
    return bytes(out)


def decompress(data: bytes, pos: int, size: int):
    """-> (bytes, end position)"""
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
            start = len(out) - off
            if off >= n:
                out += out[start:start + n]
            else:  # overlapping: the last off bytes repeat
                out += (out[start:] * (n // off + 1))[:n]
    if len(out) != size:
        raise ValueError(f"LZ77 data decodes to {len(out)} bytes, expected {size}")
    return bytes(out), pos
