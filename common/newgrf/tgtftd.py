"""TGTFTD's seaplane extensions (https://github.com/teagangosling/TGTFTD), via Action 14.

Property mappings give TGTFTD-only properties a number in this GRF and set a bit of global variable
8D when TGTFTD knows them; feature tests set a bit of global variable 9D when TGTFTD's
tgtftd_seaplanes feature has at least the given version. Action 7 on those bits then skips the
TGTFTD-only parts in other builds.
"""

from .actions import b, fits, w
from .text import encode as text

PROP_AIRCRAFT_IS_SEAPLANE = 0xF0
PROP_AIRPORT_SEAPLANE_TERMINAL = 0xF1
BIT_AIRCRAFT_MAPPED = 4          # global variable 8D
BIT_AIRPORT_MAPPED = 5           # global variable 8D
BIT_SEAPLANE_DOCKS = 6           # global variable 9D: tgtftd_seaplanes >= 2 (seaplane docks)
BIT_SEAPLANE_KERB_DOCKS = 7      # global variable 9D: tgtftd_seaplanes >= 3 (kerb docks)


def _binary(chunk_id, data):
    return b"B" + chunk_id + w(len(data)) + data


def property_mapping(name, feature, prop, success_bit):
    return (b"C" + b"A0PM" + b"T" + b"NAME" + b"\x00" + text(name)
            + _binary(b"FEAT", bytes([feature])) + _binary(b"PROP", bytes([prop]))
            + _binary(b"SETT", bytes([success_bit])) + b"\x00")


def feature_test(name, min_version, bit):
    return (b"C" + b"FTST" + b"T" + b"NAME" + b"\x00" + text(name)
            + _binary(b"MINV", w(min_version)) + _binary(b"SETP", bytes([bit])) + b"\x00")


def action14(*chunks):
    return b(0x14) + b"".join(chunks) + b"\x00"


def mapped(prop, values):
    """A mapped property for consecutive IDs: each value with its length."""
    return b(prop) + b"".join(bytes([len(v)]) + v for v in values)


def skip_if_bit(variable, bit, is_set, num_sprites):
    """Action 7: skip num_sprites if the bit of the global variable is set (is_set) or clear."""
    # 0 would skip to the end of the file.
    return b(0x07, variable, 0x01, 0x00 if is_set else 0x01, bit, fits(num_sprites, "action 7 skip", low=1))
