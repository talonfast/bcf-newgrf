"""Byte-level helpers to write NewGRF pseudo sprites (actions).

Integers are little endian: b() bytes, w() words, d() dwords, ext() extended bytes.
Variable action 2 chains are built from Adjust terms and written by varaction2().
"""

import calendar
import struct

from .text import encode as text

# Features
SHIPS, AIRCRAFT, GLOBAL, AIRPORTS, OBJECTS, AIRPORTTILES = 0x02, 0x03, 0x08, 0x0D, 0x0F, 0x11

# Variable action 2 operators
ADD, SUB, SMIN, SMAX, UMIN, UMAX, SDIV, SMOD, UDIV, UMOD, MUL, AND, OR, XOR = range(0x0E)
STO, RST, PSTO, ROR, SCMP, UCMP, SHL, SHR, SAR = range(0x0E, 0x17)

# Callbacks (variable 0C)
CB_REFIT_CAPACITY = 0x15
CB_ADDITIONAL_TEXT = 0x23
CB_PROPERTY = 0x36
CB_CREATE_EFFECT = 0x160


def b(*values):
    return bytes(v & 0xFF for v in values)


def w(value):
    return struct.pack("<H", value & 0xFFFF)


def d(value):
    return struct.pack("<I", value & 0xFFFFFFFF)


def fits(n, what, high=0xFF, low=0):
    """A count or ID that must fit its field; b() alone would silently wrap it."""
    if not low <= n <= high:
        raise ValueError(f"{what} is {n}, must be {low}..{high}")
    return n


def ext(value):
    """Extended byte: one byte, or FF followed by a word."""
    return bytes([value]) if value < 0xFF else b"\xff" + w(value)


def label(s):
    s = s.encode("ascii") if isinstance(s, str) else s
    if len(s) != 4:
        raise ValueError(f"label {s!r} must be four characters")
    return s


# ------------------------------------------------------------------------------------ units

def date(year, month=1, day=1):
    """Days since 1 Jan of year 0, as OpenTTD (and nml's date()) count them."""
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day_in_year = sum(days_in_month[:month - 1]) + day
    if month >= 3 and calendar.isleap(year):
        day_in_year += 1
    return year * 365 + calendar.leapdays(0, year) + day_in_year - 1


def _speed(value, mul, div, display_mul, display_div):
    """km/h -> property value, rounded the way nml does it so OpenTTD shows the quoted speed."""
    raw = int(float(value) * mul / div + 0.5)

    def shown(v):  # OpenTTD's km/h display of property value v
        kmh_ish = v * display_mul // display_div
        return ((10 * kmh_ish * 103) >> 6) // 16

    while shown(raw) > value:
        raw -= 1
    lower = raw
    while shown(raw) < value:
        raw += 1
    higher = raw
    return lower if abs(shown(lower) - value) < abs(shown(higher) - value) else higher


def ship_speed_kmh(kmh):
    return _speed(kmh, 10000 * 5, 1397 * 18, 1, 2)


def aircraft_speed_kmh(kmh):
    return _speed(kmh, 701 * 5, 2507 * 18, 128, 10)


# ------------------------------------------------------------------------------------ actions

def action0(feature, first_id, props, count=1):
    """props: [(property number, value bytes for all count IDs)]"""
    return (b(0x00, feature, fits(len(props), "action 0 properties"), fits(count, "action 0 IDs", low=1))
            + ext(first_id) + b"".join(b(p) + v for p, v in props))


def action1(feature, num_sets, sprites_per_set, first_set=0):
    if first_set == 0 and 0 < num_sets < 0x100:
        return b(0x01, feature, num_sets) + ext(sprites_per_set)
    return b(0x01, feature, 0) + ext(first_set) + ext(num_sets) + ext(sprites_per_set)


def action2_vehicle(feature, set_id, loaded, loading):
    """Basic action 2 for vehicles: lists of sprite set numbers."""
    return (b(0x02, feature, fits(set_id, "action 2 set ID"), fits(len(loaded), "loaded sets"),
              fits(len(loading), "loading sets")) + b"".join(w(s) for s in loaded + loading))


def action3(feature, ids, default, cargo=(), override=False):
    """ids: item IDs; cargo: [(cargo type, set ID)]; default: set ID."""
    out = b(0x03, feature, fits(len(ids), "action 3 IDs", 0x7F, 1) | (0x80 if override else 0))
    out += b"".join(ext(i) for i in ids)
    out += b(fits(len(cargo), "action 3 cargo types")) + b"".join(b(c) + w(s) for c, s in cargo)
    return out + w(default)


def action4_names(feature, first_id, names):
    """Names of vehicles etc. by item ID (language "any")."""
    # Byte IDs only: an ID from 0xFF needs the word form (language ID | 0x80).
    return (b(0x04, feature, 0x7F, fits(len(names), "action 4 names", low=1),
              fits(first_id, "action 4 ID", 0xFE)) + b"".join(text(s) for s in names))


def action4_d0xx(first_id, strings, feature=0x00):
    return (b(0x04, feature, 0xFF, fits(len(strings), "action 4 strings", low=1)) + w(first_id)
            + b"".join(text(s) for s in strings))


def cargo_table(labels):
    """Action 0 global property 09: the cargo translation table."""
    return action0(GLOBAL, 0, [(0x09, b"".join(label(x) for x in labels))], count=len(labels))


# --------------------------------------------------------------------- variable action 2

class Adjust:
    """One term of a variable action 2 calculation: (var(param) >> shift) & mask, optionally
    (... + add) / divisor or % divisor, combined with the previous value by op."""

    def __init__(self, var, shift=0, mask=0xFFFFFFFF, param=None, op=ADD, add=0, div=None, mod=None):
        self.var, self.shift, self.mask, self.param, self.op = var, shift, mask, param, op
        self.add, self.div, self.mod = add, div, mod

    def encode(self, size, first, last):
        out = b"" if first else b(self.op)
        out += b(self.var)
        if 0x60 <= self.var < 0x80:
            out += b(self.param or 0)
        flags = self.shift | (0 if last else 0x20)
        if self.div is not None:
            flags |= 0x40
        elif self.mod is not None:
            flags |= 0x80
        out += b(flags) + _sized(self.mask, size)
        if self.div is not None or self.mod is not None:
            out += _sized(self.add, size) + _sized(self.div if self.div is not None else self.mod, size)
        return out


def const(value, op=ADD):
    """A constant term (variable 1A)."""
    return Adjust(0x1A, mask=value, op=op)


def _sized(v, size):
    return {1: b, 2: w, 4: d}[size](v)


def cb(value):
    """Result: callback result value (15 bits)."""
    return 0x8000 | (value & 0x7FFF)


def varaction2(feature, set_id, adjusts, ranges, default, scope="self", size=4):
    """adjusts: [Adjust]; ranges: [(result, low, high)] in priority order; a result is an action 2
    set ID or cb(value). With no ranges the calculated value itself is the callback result."""
    type_byte = {("self", 1): 0x81, ("self", 2): 0x85, ("self", 4): 0x89,
                 ("parent", 1): 0x82, ("parent", 2): 0x86, ("parent", 4): 0x8A}[(scope, size)]
    out = b(0x02, feature, fits(set_id, "action 2 set ID"), type_byte)
    for i, a in enumerate(adjusts):
        out += a.encode(size, i == 0, i == len(adjusts) - 1)
    out += b(fits(len(ranges), "varaction2 ranges"))
    for result, lo, hi in ranges:
        out += w(result) + _sized(lo, size) + _sized(hi, size)
    return out + w(default)
