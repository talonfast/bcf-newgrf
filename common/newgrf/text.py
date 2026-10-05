"""NewGRF strings: "{BLACK}Real-world: {GOLD}78" -> bytes for Action 4 / 8 / 14.

Pure ASCII strings are written as bytes with the control codes inline (as nmlc does). Anything
else gets the UTF-8 marker (U+00DE) and the control codes as U+E0xx.
"""

CODES = {
    "": 0x0D,  # new line
    "BLUE": 0x88, "SILVER": 0x89, "GOLD": 0x8A, "RED": 0x8B, "PURPLE": 0x8C, "LTBROWN": 0x8D,
    "ORANGE": 0x8E, "GREEN": 0x8F, "YELLOW": 0x90, "DKGREEN": 0x91, "CREAM": 0x92, "BROWN": 0x93,
    "WHITE": 0x94, "LTBLUE": 0x95, "GRAY": 0x96, "DKBLUE": 0x97, "BLACK": 0x98,
}


def _parts(s):
    """Split into ("text", str) and ("code", int) parts."""
    i = 0
    while i < len(s):
        j = s.find("{", i)
        if j < 0:
            yield "text", s[i:]
            return
        if j > i:
            yield "text", s[i:j]
        k = s.index("}", j)
        name = s[j + 1:k]
        if name not in CODES:
            raise ValueError(f"unknown string code {{{name}}} in {s!r}")
        yield "code", CODES[name]
        i = k + 1


def encode(s: str, terminate=True) -> bytes:
    parts = list(_parts(s))
    if all(kind == "code" or v.isascii() for kind, v in parts):
        out = b"".join(v.encode("ascii") if kind == "text" else bytes([v]) for kind, v in parts)
    else:
        out = "Þ".encode() + b"".join(
            v.encode("utf-8") if kind == "text" else chr(0xE000 + v).encode("utf-8") for kind, v in parts)
    return out + b"\x00" if terminate else out
