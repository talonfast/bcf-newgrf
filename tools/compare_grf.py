"""Compare GRFs by behaviour: python tools/compare_grf.py NEW.grf REF.grf [REF2.grf ...] [options]

The new GRF must behave exactly like the reference GRFs together (several references are merged,
e.g. a set and the PNW Aviation items folded into it). Checked under every environment given:

  --params 0=0,0=1,0=2   GRF parameter settings to try (each "n=v" or "n=v;m=w")
  --tgtftd               also load with TGTFTD's seaplane extensions available
  --expect-header        header differences (name, description, version) are expected: report only

Compared: Action 14 info, Action 8, property sequences per item, names and strings, property
mappings and feature tests, the sprites (decoded, cropped and compared pixel by pixel), and every
Action 3 chain, evaluated for all combinations of the variables it reads.
"""

import argparse
import hashlib
import os
import pickle
import struct
import sys
import time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "common"))


from newgrf import decode, simulate  # noqa: E402
from newgrf.sprites import Rep, content_key, normalise  # noqa: E402

# Extra candidate values for variables whose ranges apply after arithmetic (see simulate.candidates).
EXTRA = {
    ("self", 0xB4, None): list(range(80)) + [255, 1000, 65535],                 # ship speed
    ("self", 0x9F, None): list(range(8)),                                       # direction
    ("self", 0x48, None): list(range(4)),                                       # object view
    ("self", 0x5F, None): [r << 8 for r in range(16)] + [0xFF00],               # random bits
    ("self", 0x40, None): [(y << 8) | x for x in range(16) for y in range(16)],  # object tile offset
    ("self", 0x47, None): [lo | (cls << 16) for lo in (0, 1, 2, 3, 4, 0xFF)
                           for cls in (0, 1, 2, 4, 8, 0x10, 0x20, 0x40, 0x80, 0x100, 0x200, 0x400)],
}

def _keys_job(args):
    path, items = args
    data = open(path, "rb").read()
    out = {}
    for sid, offsets in items:
        keys = []
        for pos, length in offsets:
            r = decode.decode_sprite(data, pos, length)
            n = normalise(Rep(r.depth, r.zoom, r.pixels[..., :4] if r.depth == 32 else r.pixels, r.x_offs, r.y_offs))
            keys.append((r.depth, r.zoom, content_key(n)))
        out[sid] = tuple(sorted(keys))
    return out

def sprite_keys(path):
    """{sprite ID: content key} for every real sprite, cached by file content."""
    raw = open(path, "rb").read()
    digest = hashlib.sha1(raw).hexdigest()
    cache = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".grfcache",
                         "keys", digest + ".pickle")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    (offset,) = struct.unpack_from("<I", raw, 10)
    pos = 14 + offset
    by_id = {}
    while True:
        (sid,) = struct.unpack_from("<I", raw, pos)
        pos += 4
        if sid == 0:
            break
        (length,) = struct.unpack_from("<I", raw, pos)
        pos += 4
        by_id.setdefault(sid, []).append((pos, length))
        pos += length
    items = list(by_id.items())
    chunks = [items[i::os.cpu_count() * 4] for i in range(os.cpu_count() * 4)]
    keys = {}
    with ProcessPoolExecutor() as ex:
        for part in ex.map(_keys_job, [(path, c) for c in chunks if c]):
            keys.update(part)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    pickle.dump(keys, open(cache, "wb"))
    return keys

def load(path, params, tgtftd):
    entries, _ = decode.read(path, decode_sprites=False)
    return simulate.load(entries, sprite_keys(path), params, tgtftd)

def restrict(m, spec):
    """Keep only the given features of a reference ("03" or "0d,11,tests")."""
    keep = {int(x, 16) for x in spec.split(",") if x != "tests"}
    m.props = {k: v for k, v in m.props.items() if k[0] in keep}
    m.names = {k: v for k, v in m.names.items() if k[0] in keep}
    m.maps = {k: v for k, v in m.maps.items() if k[0] in keep}
    m.overrides = {k: v for k, v in m.overrides.items() if k[0] in keep}
    m.mappings = {k: v for k, v in m.mappings.items() if v in keep}
    m.strings = {k: v for k, v in m.strings.items() if m.string_features.get(k) in keep}
    if "tests" not in spec.split(","):
        m.tests = []
    return m


def merge(models):
    m = simulate.Model()
    first = models[0]
    m.grfid, m.name, m.description, m.info = first.grfid, first.name, first.description, first.info
    for x in models:
        for attr in ("props", "names", "strings", "maps", "overrides", "mappings"):
            dst, src = getattr(m, attr), getattr(x, attr)
            clash = set(dst) & set(src)
            if clash:
                raise SystemExit(f"references overlap in {attr}: {sorted(clash)[:5]}")
            dst.update(src)
        m.tests += x.tests
        m.other += x.other
        m.issues += x.issues
    return m

def describe(res):
    s = repr(res)
    return s if len(s) < 300 else s[:300] + "..."

def chains_equal(a, b, params, where, problems, stats):
    nodes = simulate.walk(a) + simulate.walk(b)
    cands = simulate.candidates(nodes, EXTRA)
    env = simulate.Env({}, cands, params)
    for x, y, label in ((a, b, "new"), (b, a, "reference")):
        for assigned, res in simulate.evaluate(x, env):
            stats["evaluations"] += 1
            other = simulate.evaluate(y, simulate.Env(assigned, cands, params))
            for assigned2, res2 in other:
                if res2 != res:
                    problems.append(f"{where}: with {assigned2 or assigned} the {label} GRF gives "
                                    f"{describe(res)}, the other {describe(res2)}")
                    return

def compare(new, ref, params, expect_header):
    problems, notes = [], []
    stats = {"items": 0, "chains": 0, "evaluations": 0}
    for attr in ("grfid", "name", "description", "info"):
        if getattr(new, attr) != getattr(ref, attr):
            msg = f"header {attr}: new {describe(getattr(new, attr))} / reference {describe(getattr(ref, attr))}"
            (notes if expect_header and attr != "grfid" else problems).append(msg)
    for key in sorted(set(new.props) | set(ref.props)):
        stats["items"] += 1
        if new.props.get(key) != ref.props.get(key):
            problems.append(f"properties of feature {key[0]:#04x} item {key[1]:#x}: new {new.props.get(key)} "
                            f"/ reference {ref.props.get(key)}")
    for attr in ("names", "strings", "mappings"):
        a, b = getattr(new, attr), getattr(ref, attr)
        for key in sorted(set(a) | set(b), key=repr):
            if a.get(key) != b.get(key):
                problems.append(f"{attr} {key}: new {a.get(key)!r} / reference {b.get(key)!r}")
    if sorted(new.tests) != sorted(ref.tests):
        problems.append(f"feature tests: new {new.tests} / reference {ref.tests}")
    if new.other != ref.other:
        problems.append(f"other actions differ: new {describe(new.other)} / reference {describe(ref.other)}")
    for issue in new.issues:
        problems.append(f"new GRF: {issue}")
    for kind in ("maps", "overrides"):
        a, b = getattr(new, kind), getattr(ref, kind)
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                problems.append(f"{kind} {key}: only in the {'new' if key in a else 'reference'} GRF")
                continue
            ma, mb = a[key], b[key]
            for cargo in sorted(set(ma) | set(mb), key=str):
                stats["chains"] += 1
                chains_equal(ma.get(cargo, ma["default"]), mb.get(cargo, mb["default"]), params,
                             f"{kind} {key} cargo {cargo}", problems, stats)
    return problems, notes, stats

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("new")
    ap.add_argument("refs", nargs="+")
    ap.add_argument("--params", default="")
    ap.add_argument("--tgtftd", action="store_true")
    ap.add_argument("--expect-header", action="store_true")
    args = ap.parse_args()
    param_sets = [{}]
    if args.params:
        param_sets = []
        for group in args.params.split(","):
            ps = {}
            for kv in group.split(";"):
                k, v = kv.split("=")
                ps[int(k, 0)] = int(v, 0)
            param_sets.append(ps)
    t0 = time.time()
    failed = False
    for tgtftd in ([False, True] if args.tgtftd else [False]):
        for ps in param_sets:
            new = load(args.new, ps, tgtftd)
            refs = []
            for r in args.refs:
                path, _, spec = r.rpartition(":") if not os.path.exists(r) else (r, "", "")
                refs.append(restrict(load(path, ps, tgtftd), spec) if spec else load(path, ps, tgtftd))
            ref = merge(refs)
            problems, notes, stats = compare(new, ref, ps, args.expect_header)
            tag = f"params {ps or 'default'}, TGTFTD {'on' if tgtftd else 'off'}"
            print(f"[{tag}] {stats['items']} items, {stats['chains']} chains, "
                  f"{stats['evaluations']} evaluations: {'OK' if not problems else f'{len(problems)} DIFFERENCES'}")
            for n in notes:
                print("  note:", n)
            for p in problems[:40]:
                print("  DIFF:", p)
            if len(problems) > 40:
                print(f"  ... {len(problems) - 40} more")
            failed |= bool(problems)
    print(f"{'FAILED' if failed else 'EQUIVALENT'} ({time.time() - t0:.0f}s)")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
