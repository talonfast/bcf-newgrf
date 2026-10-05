"""Load a GRF the way OpenTTD does and evaluate what each item does, to compare two GRFs by behaviour.

    model = load(entries, sprite_keys, params={0: 1}, tgtftd=True)

The loader runs the activation stage: Action 6/7/9/D with the given GRF parameters, Action 14 property
mappings and feature tests (TGTFTD's seaplane extensions when tgtftd=True), and collects Action 0
properties, Action 1 sprite sets, Action 2 groups (resolved when defined, as OpenTTD does), Action 3
mappings and Action 4 strings. evaluate() then runs an item's variable action 2 chain for every
combination of the variables it reads (see candidates()), so two GRFs can be compared result by result.
"""

import struct
from dataclasses import dataclass, field

TGTFTD_MAPPINGS = {"aircraft_is_seaplane", "airport_seaplane_terminal"}
TGTFTD_FEATURES = {"tgtftd_seaplanes": 5}

VEHICLE_FEATURES = {0x00, 0x01, 0x02, 0x03}
LAYOUT_FEATURES = {0x07, 0x09, 0x0F, 0x11, 0x14}

# Property sizes by feature: int, or a function(buf, pos, count) -> list of values and new pos.
GENERAL_VEHICLE = {0x00: 2, 0x02: 1, 0x03: 1, 0x04: 1, 0x05: 1, 0x06: 1, 0x07: 1}


def _list_prop(lensize, itemsize):
    def read(buf, pos):
        n = int.from_bytes(buf[pos:pos + lensize], "little")
        end = pos + lensize + n * itemsize
        return bytes(buf[pos:end]), end
    return read


def _airport_layouts(buf, pos):
    (size,) = struct.unpack_from("<I", buf, pos + 1)
    end = pos + 5 + size
    return bytes(buf[pos:end]), end


PROP_SIZES = {
    0x02: {**GENERAL_VEHICLE, 0x08: 1, 0x09: 1, 0x0A: 1, 0x0B: 1, 0x0C: 1, 0x0D: 2, 0x0F: 1, 0x10: 1, 0x11: 4,
           0x12: 1, 0x13: 1, 0x14: 1, 0x15: 1, 0x16: 1, 0x17: 1, 0x18: 2, 0x19: 2, 0x1A: 4, 0x1B: 1, 0x1C: 1,
           0x1D: 2, 0x1E: _list_prop(1, 1), 0x1F: _list_prop(1, 1), 0x20: 2, 0x21: 4, 0x23: 2, 0x24: 1, 0x25: 2},
    0x03: {**GENERAL_VEHICLE, 0x08: 1, 0x09: 1, 0x0A: 1, 0x0B: 1, 0x0C: 1, 0x0D: 1, 0x0E: 1, 0x0F: 2, 0x11: 1,
           0x12: 1, 0x13: 4, 0x14: 1, 0x15: 1, 0x16: 1, 0x17: 1, 0x18: 2, 0x19: 2, 0x1A: 4, 0x1B: 1, 0x1C: 2,
           0x1D: _list_prop(1, 1), 0x1E: _list_prop(1, 1), 0x1F: 2, 0x20: 2, 0x21: 4, 0x23: 2},
    0x08: {0x09: 4},
    0x0D: {0x08: 1, 0x0A: _airport_layouts, 0x0C: 4, 0x0D: 1, 0x0E: 1, 0x0F: 1, 0x10: 2, 0x11: 2},
    0x0F: {0x08: 4, 0x09: 2, 0x0A: 2, 0x0B: 1, 0x0C: 1, 0x0D: 1, 0x0E: 4, 0x0F: 4, 0x10: 2, 0x11: 2, 0x12: 1,
           0x13: 2, 0x14: 1, 0x15: 2, 0x16: 1, 0x17: 1, 0x18: 1},
    0x11: {0x08: 1, 0x09: 1, 0x0E: 1, 0x0F: 2, 0x10: 1, 0x11: 1},
}


class Reader:
    def __init__(self, data, pos=0):
        self.data, self.pos = data, pos

    def byte(self):
        self.pos += 1
        return self.data[self.pos - 1]

    def word(self):
        self.pos += 2
        return struct.unpack_from("<H", self.data, self.pos - 2)[0]

    def dword(self):
        self.pos += 4
        return struct.unpack_from("<I", self.data, self.pos - 4)[0]

    def sized(self, size):
        return {1: self.byte, 2: self.word, 4: self.dword}[size]()

    def ext(self):
        v = self.byte()
        return self.word() if v == 0xFF else v

    def string(self):
        end = self.data.index(0, self.pos)
        s = bytes(self.data[self.pos:end])
        self.pos = end + 1
        return s

    def rest(self):
        return bytes(self.data[self.pos:])

    def done(self):
        return self.pos >= len(self.data)


# ------------------------------------------------------------------------------------ nodes
# Action 2 groups become tuples, so equal behaviour compares equal:
#   ("sets", loaded, loading)              vehicle sprite sets (each a tuple of sprite keys)
#   ("layout", ground, sprites)            sprite layout (ground and building/child sprites)
#   ("var", size, adjusts, ranges, default) variable action 2 (results are nodes)
#   ("cb", value)                          callback result
#   ("undefined", id)


@dataclass
class Model:
    grfid: bytes = b""
    name: bytes = b""
    description: bytes = b""
    info: tuple = ()
    props: dict = field(default_factory=dict)       # (feature, id) -> [(prop, value bytes)]
    names: dict = field(default_factory=dict)       # (feature, id) -> string bytes
    strings: dict = field(default_factory=dict)     # word string ID -> bytes
    string_features: dict = field(default_factory=dict)  # word string ID -> feature of its action 4
    maps: dict = field(default_factory=dict)        # (feature, id) -> {cargo: node, "default": node}
    overrides: dict = field(default_factory=dict)   # (feature, engine, wagon) -> {cargo..., "default"}
    mappings: dict = field(default_factory=dict)    # property mapping name -> (feature, prop)
    tests: list = field(default_factory=list)       # feature tests: (name, min version, bit)
    other: list = field(default_factory=list)       # other actions, raw
    issues: list = field(default_factory=list)


def _a14_tree(r):
    """Action 14 chunks -> nested tuples."""
    out = []
    while not r.done():
        kind = r.byte()
        if kind == 0:
            break
        lbl = bytes(r.data[r.pos:r.pos + 4])
        r.pos += 4
        if kind == ord("C"):
            out.append(("C", lbl, _a14_tree(r)))
        elif kind == ord("B"):
            n = r.word()
            out.append(("B", lbl, bytes(r.data[r.pos:r.pos + n])))
            r.pos += n
        elif kind == ord("T"):
            lang = r.byte()
            out.append(("T", lbl, lang, r.string()))
        else:
            raise ValueError(f"bad action 14 chunk type {kind:#x}")
    return tuple(out)


def _chunk(tree, *path):
    for item in tree:
        if item[1] == path[0]:
            return item if len(path) == 1 else _chunk(item[2], *path[1:])
    return None


def load(entries, sprite_keys, params=None, tgtftd=False):
    """entries: pseudo sprites (bytes) and real sprite IDs (int); sprite_keys: {id: content key}."""
    m = Model()
    params = dict(params or {})
    globals_ = {0x8D: 0, 0x9D: 0}
    spritesets = {}              # feature -> {set: tuple of sprite keys}
    groups = {}                  # (feature, id) -> node
    mapped = {}                  # (feature, prop) -> mapping name
    last_engine = {}             # feature -> last engine ID of a non-override action 3
    pending_mod = None           # action 6 changes for the next sprite
    i = 0
    n = len(entries)
    while i < n:
        e = entries[i]
        i += 1
        if not isinstance(e, bytes):
            continue  # a real sprite outside of an action 1
        data = bytearray(e)
        if pending_mod:
            for value, size, offset, add in pending_mod:
                cur = int.from_bytes(data[offset:offset + size], "little") if add else 0
                data[offset:offset + size] = ((cur + value) & ((1 << (8 * size)) - 1)).to_bytes(size, "little")
            pending_mod = None
        r = Reader(bytes(data))
        act = r.byte()
        if act == 0x00:
            feature, nprops, count, first = r.byte(), r.byte(), r.byte(), r.ext()
            for _ in range(nprops):
                prop = r.byte()
                key = mapped.get((feature, prop))
                for k in range(count):
                    if key is not None:
                        size = r.ext()
                        value = bytes(r.data[r.pos:r.pos + size])
                        r.pos += size
                        m.props.setdefault((feature, first + k), []).append((key, value))
                        continue
                    size = PROP_SIZES.get(feature, {}).get(prop)
                    if size is None:
                        raise ValueError(f"unknown property {prop:#x} of feature {feature:#x}")
                    if callable(size):
                        value, r.pos = size(r.data, r.pos)
                    else:
                        value = bytes(r.data[r.pos:r.pos + size])
                        r.pos += size
                    m.props.setdefault((feature, first + k), []).append((prop, value))
            if not r.done():
                raise ValueError("trailing bytes in action 0")
        elif act == 0x01:
            feature, num_sets = r.byte(), r.byte()
            first = 0
            if num_sets == 0:
                first, num_sets = r.ext(), r.ext()
            per = r.ext()
            sets = spritesets.setdefault(feature, {})
            for s in range(num_sets):
                keys = []
                for _ in range(per):
                    sid = entries[i]
                    i += 1
                    if isinstance(sid, bytes):
                        raise ValueError("pseudo sprite inside an action 1 block")
                    keys.append(sprite_keys[sid])
                sets[first + s] = tuple(keys)
        elif act == 0x02:
            feature, gid, typ = r.byte(), r.byte(), r.byte()
            groups[(feature, gid)] = _read_group(r, feature, typ, groups, spritesets.get(feature, {}), m)
        elif act == 0x03:
            feature, nids = r.byte(), r.byte()
            override = bool(nids & 0x80)
            ids = [r.ext() for _ in range(nids & 0x7F)]
            ncargo = r.byte()
            mapping = {}
            for _ in range(ncargo):
                cargo, gid = r.byte(), r.word()
                mapping[cargo] = groups.get((feature, gid), ("undefined", gid))
            gid = r.word()
            mapping["default"] = groups.get((feature, gid), ("undefined", gid))
            for item in ids:
                if override:
                    m.overrides[(feature, last_engine[feature], item)] = mapping
                else:
                    m.maps[(feature, item)] = mapping
            if not override and ids:
                last_engine[feature] = ids[-1]
        elif act == 0x04:
            feature, lang, num = r.byte(), r.byte(), r.byte()
            if lang & 0x80:
                first = r.word()
                for k in range(num):
                    m.strings[first + k] = r.string()
                    m.string_features[first + k] = feature
            else:
                first = r.ext() if feature in VEHICLE_FEATURES else r.byte()
                for k in range(num):
                    m.names[(feature, first + k)] = r.string()
        elif act == 0x06:
            pending_mod = []
            while True:
                p = r.byte()
                if p == 0xFF:
                    break
                size, offset = r.byte(), r.ext()
                pending_mod.append((params.get(p, 0), size & 0x7F, offset, bool(size & 0x80)))
        elif act in (0x07, 0x09):
            var, size, cond = r.byte(), r.byte(), r.byte()
            if cond in (0x06, 0x07, 0x08, 0x09, 0x0A):
                value = r.dword()
                active = False  # no other GRFs are loaded
                skip = {0x06: active, 0x07: not active, 0x08: False, 0x09: True, 0x0A: True}[cond]
            else:
                value = r.sized(size) if size in (1, 2, 4) else r.dword()
                v = params.get(var, 0) if var < 0x80 else globals_.get(var, 0)
                v &= (1 << (8 * min(size, 4))) - 1
                if cond == 0x00:
                    skip = bool(v >> value & 1)
                elif cond == 0x01:
                    skip = not (v >> value & 1)
                elif cond == 0x02:
                    skip = v == value
                elif cond == 0x03:
                    skip = v != value
                elif cond == 0x04:
                    skip = v < value
                elif cond == 0x05:
                    skip = v > value
                else:
                    raise ValueError(f"unsupported action 7 condition {cond:#x}")
            count = r.byte()
            if skip:
                i = n if count == 0 else i + count
        elif act == 0x08:
            r.byte()
            m.grfid = bytes(r.data[r.pos:r.pos + 4])
            r.pos += 4
            m.name, m.description = r.string(), r.string()
        elif act == 0x0D:
            target, op, src1, src2 = r.byte(), r.byte(), r.byte(), r.byte()
            data_ = r.dword() if not r.done() else 0

            def src(s):
                if s == 0xFF:
                    return data_
                if s == 0xFE:
                    raise ValueError("action D with special source FE is not supported")
                return params.get(s, 0) if s < 0x80 else globals_.get(s, 0)

            if op & 0x80 and target in params:
                continue
            a, c = src(src1), src(src2)
            sa = a - (1 << 32) if a & 0x80000000 else a
            sc = c - (1 << 32) if c & 0x80000000 else c
            op &= 0x7F
            if op == 0x00:
                v = a
            elif op == 0x01:
                v = a + c
            elif op == 0x02:
                v = a - c
            elif op == 0x03:
                v = a * c
            elif op == 0x04:
                v = sa * sc
            elif op == 0x05:
                v = (a << sc) if sc >= 0 else (a >> -sc)
            elif op == 0x06:
                v = (sa << sc) if sc >= 0 else (sa >> -sc)
            elif op == 0x07:
                v = a & c
            elif op == 0x08:
                v = a | c
            elif op == 0x09:
                v = a // c if c else 0
            elif op == 0x0A:
                v = int(sa / sc) if sc else 0
            elif op == 0x0B:
                v = a % c if c else 0
            elif op == 0x0C:
                v = sa - int(sa / sc) * sc if sc else 0
            else:
                raise ValueError(f"unsupported action D operation {op:#x}")
            params[target] = v & 0xFFFFFFFF
        elif act == 0x14:
            tree = _a14_tree(r)
            for item in tree:
                if item[1] == b"INFO":
                    m.info = item[2]
                elif item[1] == b"A0PM":
                    sub = item[2]
                    name = _chunk(sub, b"NAME")[3].decode()
                    feature = _chunk(sub, b"FEAT")[2][0]
                    prop = _chunk(sub, b"PROP")[2][0]
                    mapped[(feature, prop)] = name
                    m.mappings[name] = feature
                    sett = _chunk(sub, b"SETT")
                    if tgtftd and name in TGTFTD_MAPPINGS and sett:
                        globals_[0x8D] |= 1 << sett[2][0]
                elif item[1] == b"FTST":
                    sub = item[2]
                    name = _chunk(sub, b"NAME")[3].decode()
                    minv = int.from_bytes(_chunk(sub, b"MINV")[2], "little")
                    setp = _chunk(sub, b"SETP")
                    m.tests.append((name, minv))
                    have = TGTFTD_FEATURES.get(name, 0) if tgtftd else 0
                    if have >= minv and setp:
                        globals_[0x9D] |= 1 << setp[2][0]
                else:
                    m.other.append(("A14", item))
        elif act == 0x10:
            pass  # label
        else:
            m.other.append(bytes(data))
    return m


def _read_group(r, feature, typ, groups, sets, m):
    def result(word):
        if word & 0x8000:
            return ("cb", word & 0x7FFF)
        return groups.get((feature, word), ("undefined", word))

    def set_sprites(s):
        if s not in sets:
            m.issues.append(f"feature {feature:#x}: undefined sprite set {s}")
        return sets.get(s, ())

    if typ in (0x81, 0x82, 0x85, 0x86, 0x89, 0x8A):
        size = {0x81: 1, 0x82: 1, 0x85: 2, 0x86: 2, 0x89: 4, 0x8A: 4}[typ]
        scope = "parent" if typ in (0x82, 0x86, 0x8A) else "self"
        adjusts = []
        op = None
        while True:
            var = r.byte()
            param = r.byte() if 0x60 <= var < 0x80 else None
            flags = r.byte()
            mask = r.sized(size)
            add = divmod_ = None
            kind = None
            if flags & 0xC0:
                kind = "div" if flags & 0x40 else "mod"
                add, divmod_ = r.sized(size), r.sized(size)
            adjusts.append((op, var, param, flags & 0x1F, mask, kind, add, divmod_))
            if not flags & 0x20:
                break
            op = r.byte()
        nranges = r.byte()
        ranges = []
        for _ in range(nranges):
            res = r.word()
            lo, hi = r.sized(size), r.sized(size)
            ranges.append((result(res), lo, hi))
        default = result(r.word())
        return ("var", size, scope, tuple(adjusts), tuple(ranges), default)
    if typ in (0x80, 0x83, 0x84):
        raise ValueError("random action 2 is not supported")
    if feature in LAYOUT_FEATURES:
        num = typ
        advanced = bool(num & 0x40)
        num &= 0x3F

        def sprite(child_allowed):
            spr, pal = r.word(), r.word()
            flags = r.word() if advanced else 0
            custom = bool(pal & 0x8000)
            target = set_sprites(spr & 0x3FFF) if custom else spr
            return (custom, target, pal & 0x7FFF, spr & 0xC000 if custom else 0), flags

        ground, gflags = sprite(False)
        gregs = _read_regs(r, gflags, True)
        items = []
        for _ in range(num):
            spr, flags = sprite(True)
            x, y, z = r.byte(), r.byte(), r.byte()
            if z == 0x80:
                item = ("child", spr, _s8(x), _s8(y))
            else:
                item = ("building", spr, _s8(x), _s8(y), z, r.byte(), r.byte(), r.byte())
            items.append((item, flags, _read_regs(r, flags, z == 0x80)))
        return ("layout", (ground, gflags, gregs), tuple(items))
    nloading = r.byte()
    loaded = tuple(set_sprites(r.word()) for _ in range(typ))
    loading = tuple(set_sprites(r.word()) for _ in range(nloading))
    return ("sets", loaded, loading)


def _s8(v):
    return v - 256 if v >= 128 else v


def _read_regs(r, flags, child):
    """Registers following an advanced sprite layout entry, by flag."""
    regs = {}
    for bit, name, count in ((0x01, "dodraw", 1), (0x02, "sprite", 1), (0x04, "palette", 1),
                             (0x10, "offset_xy", 2), (0x20, "offset_z", 1)):
        if flags & bit:
            if bit == 0x20 and child:
                continue
            regs[name] = tuple(r.byte() for _ in range(count))
    for bit, name in ((0x40, "sprite_var10"), (0x80, "palette_var10")):
        if flags & bit:
            regs[name] = r.byte()
    unknown = flags & ~0xF7 if not child else flags & ~0xD7
    if unknown:
        raise ValueError(f"unsupported sprite layout flags {flags:#x}")
    return regs


# ------------------------------------------------------------------------------------ evaluate

def _signed(v, size):
    bits = 8 * size
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


class Env:
    """Variable values for one evaluation; unknown variables are branched over candidates."""

    def __init__(self, fixed, candidates, params):
        self.fixed, self.candidates, self.params = fixed, candidates, params


def evaluate(node, env, regs=None, assigned=None):
    """-> list of (assignments, result). Results: ("sets", ...), ("layout", ...), ("cb", value, regs)."""
    regs = dict(regs or {})
    assigned = dict(assigned or {})
    out = []
    _eval(node, env, regs, assigned, out, 0)
    return out


def _eval(node, env, regs, assigned, out, depth):
    if depth > 64:
        raise ValueError("action 2 chain too deep")
    kind = node[0]
    if kind != "var":
        if kind == "cb":
            res = ("cb", node[1], tuple(sorted((k, v) for k, v in regs.items() if k >= 0x100)))
        elif kind == "layout":
            res = _resolve_layout(node, regs)
        else:
            res = node
        out.append((dict(assigned), res))
        return
    _, size, scope, adjusts, ranges, default = node
    _calc(node, adjusts, 0, 0, size, scope, env, regs, assigned, out, depth)


def var_key(scope, var, param):
    """Callback variables (0C, 10, 18) are the same in every scope."""
    return ("cb", var, None) if var in (0x0C, 0x10, 0x18) else (scope, var, param)


def _read_var(var, param, scope, env, regs, assigned):
    """-> list of (value, assigned-after)."""
    if var == 0x1A:
        return [(0xFFFFFFFF, assigned)]
    if var == 0x7D:
        return [(regs.get(param, 0), assigned)]
    if var == 0x7C:
        return [(0, assigned)]
    if var == 0x7F:
        return [(env.params.get(param, 0), assigned)]
    key = var_key(scope, var, param)
    if key in env.fixed:
        return [(env.fixed[key], assigned)]
    if key in assigned:
        return [(assigned[key], assigned)]
    vals = env.candidates.get(key) or env.candidates.get((scope, var, None)) or [0]
    return [(v, {**assigned, key: v}) for v in vals]


def _calc(node, adjusts, index, last, size, scope, env, regs, assigned, out, depth):
    if index == len(adjusts):
        _pick(node, last, size, env, regs, assigned, out, depth)
        return
    op, var, param, shift, mask, kind, add, divmod_ = adjusts[index]
    for raw, assigned2 in _read_var(var, param, scope, env, regs, assigned):
        v = (raw >> shift) & mask
        if kind is not None:
            v = _signed(v + add, size)
            dv = _signed(divmod_, size)
            if dv == 0:
                v = 0
            elif kind == "div":
                v = int(v / dv)
            else:
                v = v - int(v / dv) * dv
        v &= (1 << (8 * size)) - 1
        regs2 = dict(regs)
        new = v if op is None else _op(op, last, v, size, regs2)
        _calc(node, adjusts, index + 1, new, size, scope, env, regs2, assigned2, out, depth)


def _op(op, a, b, size, regs):
    bits = 8 * size
    m = (1 << bits) - 1
    sa, sb = _signed(a, size), _signed(b, size)
    if op == 0x00:
        r = a + b
    elif op == 0x01:
        r = a - b
    elif op == 0x02:
        r = min(sa, sb)
    elif op == 0x03:
        r = max(sa, sb)
    elif op == 0x04:
        r = min(a, b)
    elif op == 0x05:
        r = max(a, b)
    elif op == 0x06:
        r = int(sa / sb) if sb else a
    elif op == 0x07:
        r = sa - int(sa / sb) * sb if sb else a
    elif op == 0x08:
        r = a // b if b else a
    elif op == 0x09:
        r = a % b if b else a
    elif op == 0x0A:
        r = a * b
    elif op == 0x0B:
        r = a & b
    elif op == 0x0C:
        r = a | b
    elif op == 0x0D:
        r = a ^ b
    elif op == 0x0E:
        regs[b] = sa
        r = a
    elif op == 0x0F:
        r = b
    elif op == 0x10:
        r = a  # persistent storage is not modelled
    elif op == 0x11:
        k = b & (bits - 1)
        r = ((a >> k) | (a << (bits - k))) if k else a
    elif op == 0x12:
        r = 0 if sa < sb else (1 if sa == sb else 2)
    elif op == 0x13:
        r = 0 if a < b else (1 if a == b else 2)
    elif op == 0x14:
        r = a << (b & 0x1F)
    elif op == 0x15:
        r = a >> (b & 0x1F)
    elif op == 0x16:
        r = sa >> (b & 0x1F)
    else:
        raise ValueError(f"unsupported variable action 2 operator {op:#x}")
    return r & m


def _pick(node, value, size, env, regs, assigned, out, depth):
    _, _, _, _, ranges, default = node
    if not ranges:
        res = ("cb", value & 0x7FFF, tuple(sorted((k, v) for k, v in regs.items() if k >= 0x100)))
        out.append((dict(assigned), res))
        return
    target = default
    for res, lo, hi in ranges:
        if lo <= value <= hi:
            target = res
            break
    _eval(target, env, regs, assigned, out, depth + 1)


def _resolve_layout(node, regs):
    """Apply registers to a sprite layout -> the sprites OpenTTD would draw."""
    _, (ground, gflags, gregs), items = node

    def resolve(spr, flags, r):
        custom, target, pal, spr_flags = spr
        if flags & 0x01 and not regs.get(r["dodraw"][0], 0):
            return None
        offset = regs.get(r["sprite"][0], 0) if flags & 0x02 else 0
        if custom:
            target = target[offset] if 0 <= offset < len(target) else ("bad sprite offset", offset)
        else:
            target = target + offset
        if flags & 0x04:
            pal += regs.get(r["palette"][0], 0)
        return (custom, target, pal, spr_flags)

    g = resolve(ground, gflags, gregs)
    drawn = []
    for item, flags, r in items:
        spr = resolve(item[1], flags, r)
        if spr is None:
            continue
        geom = list(item[2:])
        if flags & 0x10:
            geom[0] += _signed(regs.get(r["offset_xy"][0], 0), 4)
            geom[1] += _signed(regs.get(r["offset_xy"][1], 0), 4)
        if flags & 0x20 and item[0] == "building":
            geom[2] += _signed(regs.get(r["offset_z"][0], 0), 4)
        drawn.append((item[0], spr, tuple(geom)))
    return ("layout", g, tuple(drawn))


# ------------------------------------------------------------------------------------ candidates

def walk(node, seen=None):
    """All nodes reachable from node."""
    seen = seen if seen is not None else {}
    stack = [node]
    while stack:
        nd = stack.pop()
        if id(nd) in seen:
            continue
        seen[id(nd)] = nd
        if nd[0] == "var":
            for res, _, _ in nd[4]:
                stack.append(res)
            stack.append(nd[5])
    return list(seen.values())


def candidates(nodes, extra=None):
    """Candidate raw values for each variable read in the given chains.

    From each read: 0, every range bound and its neighbours (shifted back into place when the
    read is the only variable term), each mask bit, plus extra[(scope, var, param)] values. Reads of
    the same variable with different shifts are combined, so e.g. two bytes of var 40 vary together.
    """
    parts = {}
    for nd in nodes:
        if nd[0] != "var":
            continue
        _, size, scope, adjusts, ranges, _ = nd
        reads = [a for a in adjusts if a[1] not in (0x1A, 0x7D, 0x7C, 0x7F)]
        for a in reads:
            op, var, param, shift, mask, kind, add, dm = a
            key = var_key(scope, var, param)
            vals = {0, mask}
            for k in range(32):
                if mask >> k & 1:
                    vals.add(1 << k)
            if len(reads) == 1 and kind is None:
                for _, lo, hi in ranges:
                    for v in (lo, hi, lo - 1, hi + 1):
                        if 0 <= v <= mask:
                            vals.add(v)
            vals = {(v & mask) << shift for v in vals}
            parts.setdefault(key, {}).setdefault((shift, mask), set()).update(vals)
    out = {}
    for key, by_field in parts.items():
        combos = {0}
        for (shift, mask), vals in by_field.items():
            combos = {c | v for c in combos for v in vals} if len(combos) * len(vals) <= 4096 else combos | vals
        if extra and key in extra:
            combos |= set(extra[key])
        out[key] = sorted(combos)
    if extra:
        for key, vals in extra.items():
            out.setdefault(key, sorted(set(vals)))
    return out
