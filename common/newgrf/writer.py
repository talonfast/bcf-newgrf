"""Assemble a container version 2 GRF.

    g = GRF(b"TFBA", name, description, version=3, min_version=1)
    g.add(action_bytes)          # pseudo sprites (see actions.py)
    g.sprite(sprite)             # real sprites (see sprites.py)
    text_id = g.string("...")    # global D0xx strings
    g.write(path)

The header (Action 14 static info, Action 8, the D0xx strings) is put in front of the body when the
file is written. Identical sprites are stored once. Sprite encoding runs on all cores and is cached
by content under .grfcache/ in the repository, so rebuilds only encode what changed.
"""

import os
import time
from concurrent.futures import ProcessPoolExecutor

from . import sprites as S
from .actions import action4_d0xx, b, d, w
from .text import encode as text

SIGNATURE = b"\x00\x00GRF\x82\x0d\x0a\x1a\x0a"
CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".grfcache")


class Param:
    """A GRF parameter for Action 14 (int setting with named values)."""

    def __init__(self, number, name, desc, minimum, maximum, default, names=None):
        self.number, self.name, self.desc = number, name, desc
        self.minimum, self.maximum, self.default, self.names = minimum, maximum, default, names or {}


def a14_bin(label, data):
    return b"B" + label + w(len(data)) + data


def a14_text(label, s):
    return b"T" + label + b"\x7f" + text(s)


class GRF:
    def __init__(self, grfid, name, description, version, min_version, params=(), palette=b"D", blitter=b"3"):
        self.grfid = grfid if isinstance(grfid, bytes) else grfid.encode("ascii")
        self.name, self.description = name, description
        self.version, self.min_version = version, min_version
        self.params, self.palette, self.blitter = list(params), palette, blitter
        self.entries = []
        self.strings = []           # D0xx strings in ID order
        self._string_ids = {}

    # ---------------------------------------------------------------- content
    def add(self, data: bytes):
        self.entries.append(bytes(data))

    def sprite(self, sprite: S.Sprite):
        self.entries.append(sprite)

    def string(self, s: str) -> int:
        """ID (0xD000 + n) of a global string; equal strings share one ID."""
        if s not in self._string_ids:
            if len(self.strings) >= 0x400:
                raise ValueError("too many D0xx strings")
            self._string_ids[s] = 0xD000 + len(self.strings)
            self.strings.append(s)
        return self._string_ids[s]

    # ---------------------------------------------------------------- header
    def header(self):
        info = (a14_bin(b"VRSN", d(self.version)) + a14_bin(b"MINV", d(self.min_version))
                + a14_bin(b"NPAR", bytes([len(self.params)])))
        if self.params:
            para = b""
            for p in self.params:
                body = a14_text(b"NAME", p.name) + a14_text(b"DESC", p.desc)
                body += a14_bin(b"MASK", bytes([p.number])) + a14_bin(b"LIMI", d(p.minimum) + d(p.maximum))
                if p.names:
                    body += b"C" + b"VALU" + b"".join(
                        b"T" + d(v) + b"\x7f" + text(s) for v, s in sorted(p.names.items())) + b"\x00"
                body += a14_bin(b"DFLT", d(p.default))
                para += b"C" + d(p.number) + body + b"\x00"
            info += b"C" + b"PARA" + para + b"\x00"
        info += a14_bin(b"PALS", self.palette)
        if self.blitter:
            info += a14_bin(b"BLTR", self.blitter)
        out = [b(0x14) + b"C" + b"INFO" + info + b"\x00" + b"\x00",
               b(0x08, 0x08) + self.grfid + text(self.name) + text(self.description)]
        for first in range(0, len(self.strings), 255):
            out.append(action4_d0xx(0xD000 + first, self.strings[first:first + 255]))
        return out

    # ---------------------------------------------------------------- output
    def write(self, path, jobs=None, quiet=False):
        t0 = time.time()
        entries = self.header() + self.entries
        # Unique representations, by content.
        reps = {}
        sprite_keys = []
        for e in entries:
            if isinstance(e, S.Sprite):
                keys = []
                for r in e.reps:
                    n = S.normalise(r)
                    k = S.content_key(n)
                    reps.setdefault(k, n)
                    keys.append(k)
                sprite_keys.append(tuple(keys))
        encoded = _encode_all(reps, jobs, quiet)

        # Main section: one sprite data ID per distinct sprite.
        ids = {}
        main = bytearray()
        main += d(4) + b"\xff" + d(len(entries))
        data = bytearray()
        it = iter(sprite_keys)
        for e in entries:
            if isinstance(e, bytes):
                main += d(len(e)) + b"\xff" + e
                continue
            keys = next(it)
            if keys not in ids:
                ids[keys] = len(ids) + 1
                for k in sorted(keys, key=lambda k: (reps[k].depth, reps[k].zoom)):
                    body = encoded[k]
                    data += d(ids[keys]) + d(len(body)) + body
            main += d(4) + b"\xfd" + d(ids[keys])
        main += d(0)
        data += d(0)
        out = SIGNATURE + d(1 + len(main)) + b"\x00" + bytes(main) + bytes(data)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "wb") as f:
            f.write(out)
        if not quiet:
            n_sprites = len(sprite_keys)
            print(f"wrote {path}: {len(out) / 1e6:.1f} MB, {len(entries) - n_sprites} pseudo sprites, "
                  f"{n_sprites} real sprites ({len(ids)} distinct) in {time.time() - t0:.0f}s")
        return out


def _cache_path(key):
    h = key.hex()
    return os.path.join(CACHE, h[:2], h[2:] + ".bin")


def _encode_job(args):
    key, rep = args
    body = S.encode(rep)
    p = _cache_path(key)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + f".{os.getpid()}.tmp"
    with open(tmp, "wb") as f:
        f.write(body)
    os.replace(tmp, p)
    return key, body


def _encode_all(reps, jobs, quiet):
    out = {}
    todo = []
    for k, r in reps.items():
        p = _cache_path(k)
        if os.path.exists(p):
            with open(p, "rb") as f:
                out[k] = f.read()
        else:
            todo.append((k, r))
    if not todo:
        return out
    if not quiet:
        print(f"encoding {len(todo)} sprite images ({len(reps) - len(todo)} cached) ...", flush=True)
    todo.sort(key=lambda kr: -kr[1].pixels.nbytes)  # big ones first, for even load
    if len(todo) < 8 or jobs == 1:
        results = map(_encode_job, todo)
        for k, body in results:
            out[k] = body
    else:
        with ProcessPoolExecutor(max_workers=jobs or os.cpu_count()) as ex:
            for k, body in ex.map(_encode_job, todo, chunksize=1):
                out[k] = body
    return out

