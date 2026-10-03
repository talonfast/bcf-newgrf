"""
Parametric 3D models for each vessel, with liveries matched to photos.

Model scale: length_units = 7 + metres * 0.11  (a Spirit ~ 1.6 tiles long)
             beam_units   = 1.4 + metres * 0.15
Heights are in OpenTTD height units (pixels at 1x before ZS).

Liveries
--------
modern  (2000s on): black lower hull with antifouling at the waterline, white
        above, a bcfblue pinstripe, the '~BCFerries' wordmark and the ship's
        name in italic serif on the hull, royal-blue stacks with white waves.
classic (1960s-90s): white with a navy boot-top band and pinstripe, white
        funnel with a light-blue band and black top.
"""
import numpy as np

from render import Ship


def L(m):
    return round(7 + m * 0.11, 1)


def Bm(m):
    return round(1.4 + m * 0.15, 1)


# ---------------------------------------------------------------------------
# Livery helpers
# ---------------------------------------------------------------------------

def modern_hull(s, h, black, key, stripe=None, mark=None, name=None, **kw):
    """stripe: w of the blue pinstripe (default: just under the deck edge).
    mark:   (s, w, height) of the wordmark; name: (s, w, height) of the name."""
    L2 = s.L / 2
    if stripe is None:
        stripe = h - 0.28
    decals = []
    if mark is not False:
        ms, mw, mh = mark or (0.3 * L2, black + (h - black) * 0.42, min(1.3, (h - black) * 0.4))
        decals.append(dict(name="wordmark", s=ms, w=mw, h=mh, mat="bcfblue"))
    if name is not False:
        ns, nw, nh = name or (-0.45 * L2, black + (h - black) * 0.4, min(0.5, (h - black) * 0.18))
        decals.append(dict(name="name_" + key, s=ns, w=nw, h=nh, mat="navy"))
    kw["stripe"] = None if stripe is False else (stripe - 0.12, stripe + 0.12, "bcfblue")
    s.hull(h, lower="hullblack", upper="white", band=black, boot=(0.22, "antifoul"),
           decals=decals, **kw)
    return s


def classic_hull(s, h, key, lower="navy", **kw):
    decals = [dict(name="name_" + key, s=-0.45 * s.L / 2, w=h * 0.55, h=min(0.5, h * 0.14),
                   mat="navy")]
    s.hull(h, lower=lower, upper="white", band=0.9 if lower == "navy" else 0.6,
           boot=(0.22, "antifoul"), stripe=(h - 0.4, h - 0.2, "navy"), decals=decals, **kw)
    return s


def classic_funnel(s, u, v, z0, z1, ru=0.9, rv=0.8):
    zm = z0 + (z1 - z0) * 0.45
    s.funnel(u, v, z0, z1, ru=ru, rv=rv, mat="white", top="black", top_h=0.7,
             band=((zm - 0.4, zm + 0.4), "ltblue"))
    return s


def logo_panel(s, u, v, z0, z1, ru=0.9, rv=0.12):
    """Navy panel carrying the white wave icon (Salish / Island classes)."""
    s.funnel(u, v, z0, z1, ru=ru, rv=rv, mat="navy", top="navy", top_h=0, hollow=False,
             decal=("logo_panel", "white", z0 + 0.15, z1 - 0.15))
    return s


def mark(s_, w, h):
    return [dict(name="wordmark", s=s_, w=w, h=h, mat="bcfblue")]


def central_house(s, hh, deck, top, mark_w=None, mark_h=1.0):
    """Superstructure over the middle of an open car deck (Bowen, Intermediate,
    T-class): full-width lower house with dark car-deck portals in its ends,
    a blue line along its top edge and optionally the wordmark."""
    wv = s.B / 2 * 0.97
    s.block(-hh, hh, deck, top, wf=0.97, rect=True, windows=False, rail=False,
            decals=mark(0.0, mark_w, mark_h) if mark_w else ())
    for end in (-1, 1):
        a, b = sorted((end * hh, end * (hh - 0.07)))
        s.box(a, b, -wv + 0.55, wv - 0.55, deck, deck + (top - deck) * 0.72, "dark")
    for side in (-1, 1):
        a, b = sorted((side * (wv - 0.03), side * (wv + 0.01)))
        s.box(-hh, hh, a, b, top - 0.3, top - 0.16, "bcfblue")
    return s


def ramp_gantries(s, deck, height=2.6, colour="dark"):
    """The arched ramp-hoist gantries over each end of a minor-route ferry."""
    L2, v = s.L / 2, s.B / 2 - 0.35
    for end in (-1, 1):
        u = end * (L2 - 0.55)
        for side in (-1, 1):
            s.box(u - 0.09, u + 0.09, side * v - 0.09, side * v + 0.09, deck, deck + height,
                  colour)
        s.box(u - 0.09, u + 0.09, -v, v, deck + height - 0.18, deck + height, colour)
    return s


def double_ender_top(s, half, z, deck_h=2.0, wf=0.8, bridge_len=1.8, wings=True):
    """Wheelhouses at both ends of a double-ended ferry, with bridge wings
    running out to the ship's sides and a glazed band across the front."""
    s.block(half - bridge_len, half, z, z + deck_h, wf=wf, round_ends=False)
    s.block(-half, -half + bridge_len, z, z + deck_h, wf=wf, round_ends=False)
    if wings:
        wv = s.B / 2 * 0.97
        zt = z + deck_h
        for end in (-1, 1):
            a, b = sorted((end * half, end * (half - 0.6)))
            s.box(a, b, -wv, wv, zt - 0.75, zt - 0.1, "white")
            fa, fb = sorted((end * half, end * (half - 0.07)))
            s.box(fa, fb, -wv + 0.1, wv - 0.1, zt - 0.6, zt - 0.28, "window")
    return s


# ---------------------------------------------------------------------------
# Major vessels
# ---------------------------------------------------------------------------

def m_spirit(lng=False, key="spirit"):
    s = Ship(L(167.5), Bm(26.7), "double", taper=0.2, blunt=0.42)
    h = s.L / 2
    modern_hull(s, 6.4, 1.4, key, stripe=6.15,
                mark=(0.40 * h, 3.6, 1.9), name=(-0.35 * h, 3.9, 0.55))
    s.portal_cars(1.62)
    # upper decks are boxy and overhang the narrowing hull ends
    s.block(-h + 1.8, h - 1.8, 6.4, 8.6, wf=0.97, rect=True, panes=(0.34, 0.82))
    s.block(-h + 3.2, h - 3.2, 8.6, 10.6, wf=0.92, rect=True, panes=(0.62, 0.5))
    s.liferafts(-2.6, 2.6, 10.6, s.B / 2 * 0.92)
    s.radome(-3.6, 0.0, 12.2)
    s.block(-h + 4.0, -1.0, 10.6, 12.2, wf=0.8)                # forward wheelhouse deck
    s.block(h - 5.0, h - 3.4, 10.6, 12.2, wf=0.7, round_ends=False)
    # single raked stack towards one end, with the horizontal fin on top
    s.bcf_stack(4.4, 0.0, 10.6, 15.8, ru=1.5, rv=1.2, rake=-0.18, taper=-0.35, pipes=4)
    s.box(3.9, 6.4, -0.12, 0.12, 14.9, 15.1, "stackblue")
    # white radar mast / exhaust tower forward
    s.funnel(-2.4, 0.0, 12.2, 15.2, ru=0.45, rv=0.35, mat="white", top="white", top_h=0,
             rake=0.15, hollow=False)
    s.mast(-4.2, 12.2, 14.8)
    if lng:
        s.box(-0.8, 2.2, -1.3, 1.3, 10.6, 11.8, "steel")       # LNG tank housing
    for u in (-6.8, -5.3, 1.8, 3.2):
        s.lifeboat(u - 0.6, u + 0.6, -1, 8.6)
        s.lifeboat(u - 0.6, u + 0.6, 1, 8.6)
    return s


# Vancouver 2010 wrap layouts, per ship and per side (True = side a, v < 0).
# x positions are fractions of the half-length; boundaries are (top, bottom).
# Renaissance and Celebration follow photos of both sides; Inspiration side a
# follows a photo, side b is a best guess in the same style.
WRAPS = {
    "renaissance": {
        True: dict(x0=-0.90, l=(-0.18, -0.07), r=(0.67, 0.58), x1=0.95,
                   tl="tex_alpine", tr="tex_sitski", text="vancouver2010", ts=0.25, th=1.1,
                   es=-0.06),
        False: dict(x0=-0.92, l=(-0.63, -0.57), r=(0.43, 0.28), x1=0.96,
                    tl="tex_vineyard", tr="tex_skaters", text="britishcolumbia", ts=-0.05,
                    th=1.3, es=-0.46),
        "names": (-0.55, 0.78)},
    "celebration": {
        True: dict(x0=-0.95, l=(-0.66, -0.58), r=(0.12, 0.0), x1=0.80,
                   tl="tex_hockey", tr="tex_coast", text="vancouver2010", ts=-0.2, th=1.0,
                   es=-0.46),
        False: dict(x0=-0.92, l=(-0.45, -0.36), r=(0.62, 0.52), x1=0.95,
                    tl="tex_rainforest", tr="tex_hockeyplayer", text="britishcolumbia",
                    ts=0.09, th=1.3, es=-0.27),
        "names": (-0.8, 0.45)},
    "inspiration": {
        True: dict(x0=-0.92, l=(-0.50, -0.40), r=(0.55, 0.44), x1=0.95,
                   tl="tex_snowboard", tr="tex_orca", text="britishcolumbia", ts=0.03, th=1.3,
                   es=-0.31),
        False: dict(x0=-0.92, l=(-0.40, -0.30), r=(0.60, 0.50), x1=0.95,
                    tl="tex_aerials", tr="tex_mountains", text="vancouver2010", ts=0.15,
                    th=1.1, es=-0.17),
        "names": (-0.6, 0.75)},
}


def make_olympic_wrap(L2, lo, hi, layout):
    """Vancouver 2010 wrap (2008-10): a photo panel at each end of each
    side, bounded by slanted lime/royal/navy swooshes, white centre."""
    swoosh = ((0.0, 0.018, "white"), (0.018, 0.05, "vgreen"), (0.05, 0.075, "vblue"),
              (0.075, 0.092, "navy"))

    def paint(s, w, h, side_a):
        out = []
        area = (w > lo) & (w <= hi)
        b = np.clip((w - lo) / (hi - lo), 0, 1)
        x = s / L2
        for sa in (True, False):
            p = layout[sa]
            (lt, lb), (rt, rb) = p["l"], p["r"]
            on = area & (side_a == sa)
            xl = lt + (lb - lt) * (1 - b)          # left boundary, bottom further in
            xr = rt + (rb - rt) * (1 - b)
            wc, wh = (lo + hi) / 2, hi - lo
            lw = (max(lt, lb) - p["x0"]) * L2
            out.append((on & (x > p["x0"]) & (x < xl),
                        dict(tex=p["tl"], s=p["x0"] * L2 + lw / 2, w=wc, h=wh, width=lw)))
            rw = (p["x1"] - min(rt, rb)) * L2
            out.append((on & (x > xr) & (x < p["x1"]),
                        dict(tex=p["tr"], s=p["x1"] * L2 - rw / 2, w=wc, h=wh, width=rw)))
            for a, c, m in swoosh:
                out.append((on & (x >= xl + a) & (x < xl + c), m))
                out.append((on & (x <= xr - a) & (x > xr - c), m))
        return out
    return paint


def olympic_decals(h, layout, key):
    out = []
    for sa, tag in ((True, "a"), (False, "b")):
        p = layout[sa]
        out.append(dict(name=p["text"], s=p["ts"] * h, w=3.2, h=p["th"], mat="navy", side=tag))
        out.append(dict(name="tex_emblems", tex=True, s=p["es"] * h, w=3.4, h=1.5, width=1.5,
                        side=tag))
    for ns in layout["names"]:
        out.append(dict(name="name_" + key, s=ns * h, w=1.75, h=0.4, mat="white"))
    return out


def m_coastal(olympic=False, key="coastal", wrap="renaissance"):
    s = Ship(L(160), Bm(28.2), "double", taper=0.2, blunt=0.42)
    h = s.L / 2
    hull_windows = (4.75, 5.45, 0.9, 0.42)
    if olympic:
        lo, hi = 1.3, 6.1
        s.hull(6.2, lower="hullblack", upper="white", band=lo, boot=(0.22, "antifoul"),
               paint=make_olympic_wrap(h, lo, hi, WRAPS[wrap]), windows=hull_windows,
               decals=olympic_decals(h, WRAPS[wrap], key))
    else:
        modern_hull(s, 6.2, 1.4, key, stripe=5.95, windows=hull_windows,
                    mark=(0.35 * h, 3.3, 1.8), name=(-0.4 * h, 3.5, 0.55))
    s.portal_cars(1.6)
    # big square windows on the lower passenger deck, a near-continuous
    # strip above; both decks overhang the hull ends (the angular look)
    s.block(-h + 1.6, h - 1.6, 6.2, 8.4, wf=0.98, rect=True, panes=(0.62, 0.56))
    s.block(-h + 2.6, h - 2.6, 8.4, 10.4, wf=0.93, rect=True, panes=(0.34, 0.84))
    double_ender_top(s, h - 2.8, 10.4, deck_h=1.8, wf=0.7, bridge_len=2.2)
    s.liferafts(-3.6, -2.0, 10.4, s.B / 2 * 0.93)
    s.liferafts(2.0, 3.6, 10.4, s.B / 2 * 0.93)
    s.radome(h - 4.6, 0.6, 12.2)
    s.radome(-h + 4.6, -0.6, 12.2)
    s.block(-4.0, 4.0, 10.4, 11.6, wf=0.8, windows=False)
    # the big domed centre casing: navy louvres, light-blue outline, wave logo
    s.bcf_stack(0.0, 0.0, 11.6, 15.4, ru=2.4, rv=1.9, rake=0.0, pipes=3, louvred=True)
    s.mast(h - 4.0, 12.2, 14.6)
    s.mast(-h + 4.0, 12.2, 14.6)
    for u in (-5.2, 5.2):
        s.lifeboat(u - 0.6, u + 0.6, -1, 8.4)
        s.lifeboat(u - 0.6, u + 0.6, 1, 8.4)
    return s


def m_cclass(oakbay=False, key=None):
    s = Ship(L(139), Bm(26.0), "double", taper=0.22, blunt=0.42)
    h = s.L / 2
    key = key or ("cclass_ob" if oakbay else "cclass")
    modern_hull(s, 5.4, 1.3, key, stripe=4.0,
                mark=(0.45 * h, 2.6, 1.5), name=(-0.5 * h, 2.8, 0.5))
    s.portal_cars(1.5)
    s.block(-h + 2.2, h - 2.2, 5.4, 7.6, wf=0.95, panes=(0.5, 0.6))
    s.block(-h + 3.4, h - 3.4, 7.6, 9.4, wf=0.85)
    s.liferafts(-2.6, -1.2, 9.4, s.B / 2 * 0.85)
    s.liferafts(2.0, 3.4, 9.4, s.B / 2 * 0.85)
    double_ender_top(s, h - 3.4, 9.4, deck_h=1.6, wf=0.65, bridge_len=1.6)
    s.bcf_stack(0.6, 0.0, 9.4, 12.8, ru=1.1, rv=1.0, rake=0.0, taper=-0.05, pipes=4)
    s.mast(-h + 5.4, 11.0, 13.2)
    s.lifeboat(-3.6, -2.4, -1, 7.6)
    s.lifeboat(-3.6, -2.4, 1, 7.6)
    return s


def m_vclass(stretched=False, key="vclass_s"):
    length = 130 if stretched else 103
    s = Ship(L(length), Bm(23.0), "double", taper=0.22, blunt=0.4)
    h = s.L / 2
    z = 4.4 if stretched else 3.6
    if stretched:
        modern_hull(s, z, 1.1, key, mark=(0.4 * h, 2.3, 1.0),
                    name=(-0.45 * h, 2.4, 0.4))
    else:
        classic_hull(s, z, "vclass")
    s.block(-h + 3.0, h - 3.0, z, z + 2.2, wf=0.92)
    double_ender_top(s, h - 3.0, z + 2.2, deck_h=1.6, wf=0.6, bridge_len=1.5)
    s.block(-2.2, 2.2, z + 2.2, z + 3.2, wf=0.6, windows=False)
    if stretched:
        s.bcf_stack(0.0, 0.0, z + 3.2, z + 6.0, ru=0.9, rv=0.8, pipes=2)
    else:
        classic_funnel(s, 0.0, 0.0, z + 3.2, z + 6.0)
    return s


def m_sidney():
    s = Ship(L(102), Bm(23.0), "double", taper=0.22, blunt=0.4)
    classic_hull(s, 3.4, "sidney")
    h = s.L / 2
    s.block(-h + 3.2, h - 3.2, 3.4, 5.6, wf=0.9)
    s.block(-1.6, 1.6, 5.6, 7.2, wf=0.7)  # single central wheelhouse
    classic_funnel(s, -2.8, 0.0, 5.6, 8.6, ru=0.8, rv=0.7)
    s.mast(1.0, 7.2, 9.0)
    return s


def m_burnaby(key="burnaby"):
    s = Ship(L(129.8), Bm(23.3), "double", taper=0.22, blunt=0.4)
    h = s.L / 2
    modern_hull(s, 4.0, 1.1, key, stripe=3.75, mark=(0.25 * h, 2.2, 1.05),
                name=(-0.5 * h, 2.4, 0.4))
    s.block(-h + 3.0, h - 3.0, 4.0, 6.2, wf=0.92)
    s.block(-h + 4.5, h - 4.5, 6.2, 7.6, wf=0.7)
    double_ender_top(s, h - 4.5, 7.6, deck_h=1.4, wf=0.55, bridge_len=1.4)
    s.bcf_stack(3.6, 0.0, 7.6, 10.6, ru=1.0, rv=0.8, rake=-0.15, taper=-0.15, pipes=2)
    s.mast(1.0, 9.0, 11.2)
    return s


def m_prince_rupert():
    s = Ship(L(101.6), Bm(20.1), "single", taper=0.3)
    h = s.L / 2
    modern_hull(s, 3.6, 1.0, "rupert", sheer=1.0, mark=(0.0, 2.0, 1.0),
                name=(-0.62 * h, 2.2, 0.35))
    s.block(-h + 1.5, h - 4.5, 3.6, 5.8, wf=0.9)
    s.block(-h + 3.0, h - 5.5, 5.8, 7.4, wf=0.8)
    s.block(h - 7.5, h - 5.5, 7.4, 8.8, wf=0.7, round_ends=False)  # bridge
    s.bcf_stack(-h + 4.2, 0.0, 7.4, 10.4, ru=1.0, rv=0.7, rake=-0.2, taper=-0.1, pipes=2)
    s.mast(h - 6.5, 8.8, 10.8)
    return s


def m_north():
    """Queen of the North, classic livery (sank 2006)."""
    s = Ship(L(125), Bm(21.3), "single", taper=0.3)
    classic_hull(s, 4.0, "north", lower="red", sheer=1.0)
    h = s.L / 2
    s.block(-h + 1.5, h - 4.0, 4.0, 6.4, wf=0.92)
    s.block(-h + 2.5, h - 5.0, 6.4, 8.4, wf=0.85)
    s.block(h - 7.0, h - 5.0, 8.4, 9.8, wf=0.75, round_ends=False)
    classic_funnel(s, -2.0, 0.0, 8.4, 11.6, ru=1.1, rv=0.8)
    s.box(-2.3, -1.7, -1.2, 1.2, 11.2, 11.4, "black")          # the winged cap
    s.mast(h - 7.8, 9.8, 12.2)
    return s


def m_northern_adventure():
    s = Ship(L(116.9), Bm(19.2), "single", taper=0.3)
    h = s.L / 2
    modern_hull(s, 4.0, 1.0, "nadventure", sheer=1.0, mark=(0.1 * h, 2.1, 1.0),
                name=(-0.6 * h, 2.4, 0.35))
    s.block(-h + 1.2, h - 3.5, 4.0, 6.2, wf=0.95)
    s.block(-h + 2.2, h - 4.2, 6.2, 8.0, wf=0.88)
    s.block(h - 6.2, h - 4.2, 8.0, 9.4, wf=0.8, round_ends=False)
    # one large stack well aft (photos: Prince Rupert, Skidegate)
    s.bcf_stack(-h + 5.0, 0.0, 8.0, 11.4, ru=1.3, rv=1.05, rake=-0.2, taper=-0.25, pipes=3)
    s.mast(h - 5.2, 9.4, 11.2)
    s.radome(h - 5.8, 0.0, 9.4)
    for u in (-1.0, 0.6):
        s.lifeboat(u - 0.6, u + 0.6, -1, 6.2)
        s.lifeboat(u - 0.6, u + 0.6, 1, 6.2)
    return s


def m_northern_expedition():
    s = Ship(L(150), Bm(23.0), "single", taper=0.32)
    h = s.L / 2
    modern_hull(s, 4.6, 1.2, "nexpedition", sheer=1.2, stripe=4.35,
                mark=(0.05 * h, 2.5, 1.2), name=(-0.6 * h, 2.8, 0.4))
    s.block(-h + 1.2, h - 4.0, 4.6, 6.8, wf=0.97)
    s.block(-h + 1.8, h - 4.8, 6.8, 8.8, wf=0.92)   # cabin decks
    s.block(-h + 3.0, h - 5.6, 8.8, 10.6, wf=0.85)
    s.block(h - 7.8, h - 5.6, 10.6, 12.0, wf=0.8, round_ends=False)
    s.bcf_stack(-h + 5.0, 0.0, 10.6, 13.8, ru=1.3, rv=1.1, rake=-0.2, taper=-0.25, pipes=3)
    s.mast(h - 6.8, 12.0, 13.8)
    s.radome(h - 7.4, 0.0, 12.0)
    s.liferafts(-h + 7.0, -h + 9.0, 10.6, s.B / 2 * 0.85)
    s.lifeboat(-2.0, -0.8, -1, 6.8)
    s.lifeboat(-2.0, -0.8, 1, 6.8)
    return s


def m_pacificat():
    s = Ship(L(122), Bm(25.8), "cat", taper=0.3)
    sep = s.B / 2 - 0.9
    s.cat_hulls(1.6, sep, 0.9, lower="steel", upper="white", band=0.5)
    h = s.L / 2
    s.box(-h, h - 3.0, -s.B / 2 + 0.1, s.B / 2 - 0.1, 1.6, 3.6, "white")
    s.box(-h, h - 3.0, -s.B / 2 + 0.1, s.B / 2 - 0.1, 1.2, 1.6, "steel")
    s.box(-h, h - 3.0, -s.B / 2 + 0.1, s.B / 2 - 0.1, 2.2, 2.45, "bcfblue")
    s.block(-h + 1.0, h - 3.6, 3.6, 5.8, wf=1.0, v0=-s.B / 2 + 0.3, v1=s.B / 2 - 0.3,
            win_mat="window")
    s.block(-h + 3.0, h - 6.0, 5.8, 7.0, wf=1.0, v0=-s.B / 2 + 0.8, v1=s.B / 2 - 0.8,
            win_mat="window")
    s.box(-h + 1.5, -h + 3.0, -1.6, 1.6, 7.0, 7.8, "steel")  # exhaust housings
    return s


def m_intermediate(key="intermediate"):
    """Intermediate class (Queen of Capilano / Cumberland): tall central house
    over the car deck, open car deck at both ends, wheelhouse on top carrying
    the logo panel."""
    s = Ship(L(96), Bm(22), "double", taper=0.22, blunt=0.42)
    h = s.L / 2
    hh = 0.32 * s.L
    modern_hull(s, 2.6, 1.0, key, doors=False, rail=True, mark=False,
                name=(0.82 * h, 1.85, 0.3))
    s.cars(-h + 1.4, -hh - 0.2, -s.B / 2 + 0.6, s.B / 2 - 0.6, 2.6, seed=21)
    s.cars(hh + 0.2, h - 1.4, -s.B / 2 + 0.6, s.B / 2 - 0.6, 2.6, seed=22)
    central_house(s, hh, 2.6, 5.4, mark_w=3.7)
    s.block(-hh + 0.3, hh - 0.3, 5.4, 7.2, wf=0.95, rect=True, panes=(0.5, 0.62))
    s.block(-1.8, 1.8, 7.2, 8.8, wf=0.62, round_ends=False)      # wheelhouse
    logo_panel(s, 0.0, 0.0, 8.8, 10.0, ru=0.9)
    s.mast(-1.2, 8.8, 10.6)
    s.lifeboat(-hh + 1.0, -hh + 2.2, -1, 5.4)
    return s


def m_century():
    s = Ship(L(110), Bm(26), "double", taper=0.2, blunt=0.45)
    h = s.L / 2
    modern_hull(s, 3.2, 1.1, "century", doors=False, mark=False, name=False)
    # open car deck with the passenger deck carried on side casings
    for v0, v1 in ((-s.B / 2 + 0.2, -s.B / 2 + 1.0), (s.B / 2 - 1.0, s.B / 2 - 0.2)):
        s.block(-h + 3.0, h - 3.0, 3.2, 5.4, wf=1.0, v0=v0, v1=v1, windows=False, rail=False,
                roof=None, decals=mark(0.0, 4.3, 1.1))
    s.cars(-h + 2.0, h - 2.0, -s.B / 2 + 1.0, s.B / 2 - 1.0, 3.2, seed=7)
    s.block(-h + 3.0, h - 3.0, 5.4, 7.4, wf=0.97, round_ends=False)
    double_ender_top(s, h - 3.0, 7.4, deck_h=1.5, wf=0.6, bridge_len=1.4)
    s.bcf_stack(-1.0, 0.0, 7.4, 10.0, ru=0.8, rv=0.8, pipes=2)
    return s


def salish_art(L2, lo, hi, art):
    """Salish class hull art: the creature's head at each end of the hull,
    facing outward, body sweeping back towards midships. Salish Orca also
    has an aqua wave field along the whole lower hull. Artists credited in
    ships.py / README."""
    x0, x1 = 0.36, 0.97                      # end panels, fractions of half-length
    wc, wh = (lo + hi) / 2, hi - lo
    pw = (x1 - x0) * L2

    def paint(s, w, h, side_a):
        out = []
        if art == "orca":
            out.append((w > lo, dict(tex="tex_salish_wave", s=0.0, w=wc, h=wh,
                                     width=1.94 * L2)))
        tex = "tex_salish_" + art
        out.append(((s > x0 * L2) & (s < x1 * L2),
                    dict(tex=tex, s=(x0 + x1) / 2 * L2, w=wc, h=wh, width=pw)))
        out.append(((s < -x0 * L2) & (s > -x1 * L2),
                    dict(tex=tex + "_m", s=-(x0 + x1) / 2 * L2, w=wc, h=wh, width=pw)))
        if art == "orca":                    # a second, smaller orca in each pod
            out.append(((s > 0.12 * L2) & (s < 0.36 * L2),
                        dict(tex=tex, s=0.24 * L2, w=wc - 0.15, h=wh * 0.75,
                             width=0.24 * L2)))
            out.append(((s < -0.12 * L2) & (s > -0.36 * L2),
                        dict(tex=tex + "_m", s=-0.24 * L2, w=wc - 0.15, h=wh * 0.75,
                             width=0.24 * L2)))
        return out
    return paint


def m_salish(key="salish", art="orca"):
    s = Ship(L(107), Bm(23.5), "double", taper=0.22, blunt=0.42)
    h = s.L / 2
    # tall hull side: the artwork covers roughly half the ship's visible height
    modern_hull(s, 5.0, 1.3, key, stripe=4.78, paint=salish_art(h, 1.35, 4.62, art),
                mark=(0.0, 3.5, 0.95), name=(0.0, 2.05, 0.32))
    s.portal_cars(1.5)
    s.block(-h + 2.4, h - 2.4, 5.0, 7.0, wf=0.96)
    s.block(-h + 3.4, h - 3.4, 7.0, 8.8, wf=0.9)
    double_ender_top(s, h - 3.4, 8.8, deck_h=1.6, wf=0.66, bridge_len=1.5)
    s.box(-2.8, -0.4, -1.1, 1.1, 8.8, 10.0, "steel")           # LNG tank
    logo_panel(s, -h + 4.8, 0.0, 8.8, 11.4, ru=1.1)
    for v in (-0.9, 0.9):                                      # thin exhaust pipes
        s.funnel(1.2, v, 8.8, 11.6, ru=0.18, rv=0.18, mat="steel", top="dark", top_h=0.3)
    s.liferafts(-1.6, 1.6, 8.8, s.B / 2 * 0.9)
    return s


def m_island():
    s = Ship(L(81), Bm(17.8), "double", taper=0.2, blunt=0.5)
    h = s.L / 2
    modern_hull(s, 2.6, 1.2, "island", doors=False, rail=True, stripe=False,
                mark=False, name=False)
    s.box(-h + 1.2, h - 1.2, -s.B / 2 + 0.15, -s.B / 2 + 0.4, 2.6, 3.2, "white")
    s.cars(-h + 1.4, h - 1.4, -s.B / 2 + 0.4, s.B / 2 - 2.2, 2.6, seed=3)
    # side-mounted superstructure carries the livery line and the wordmark
    s.block(-h + 3.0, h - 3.0, 2.6, 5.0, wf=1.0, v0=s.B / 2 - 2.2, v1=s.B / 2 - 0.1,
            windows=False, decals=mark(1.8, 4.3, 0.85))
    s.block(-h + 3.6, h - 3.6, 5.0, 6.6, wf=1.0, v0=s.B / 2 - 2.0, v1=s.B / 2 - 0.2)
    s.box(-2.0, 2.0, s.B / 2 - 2.21, s.B / 2 - 0.09, 3.6, 3.75, "navy")
    logo_panel(s, 0.0, s.B / 2 - 1.0, 6.6, 8.2, ru=0.8)
    s.mast(-h + 4.2, 6.6, 8.6, v=s.B / 2 - 1.0)
    return s


# ---------------------------------------------------------------------------
# Minor / inter-island vessels (all in modern livery)
# ---------------------------------------------------------------------------

def m_bowen():
    """Bowen class (Bowen / Mayne / Powell River Queen): open car decks at both
    ends, a central house over the middle of the car deck."""
    s = Ship(L(85), Bm(21), "double", taper=0.2, blunt=0.45)
    h = s.L / 2
    hh = 0.27 * s.L
    modern_hull(s, 2.8, 1.0, "bowen", doors=False, rail=True, mark=False, name=False)
    s.cars(-h + 1.4, -hh - 0.2, -s.B / 2 + 0.6, s.B / 2 - 0.6, 2.8, seed=11)
    s.cars(hh + 0.2, h - 1.4, -s.B / 2 + 0.6, s.B / 2 - 0.6, 2.8, seed=12)
    central_house(s, hh, 2.8, 4.9, mark_w=3.85)
    s.block(-hh + 0.4, hh - 0.4, 4.9, 6.6, wf=0.9, rect=True, panes=(0.45, 0.6))
    s.block(-1.3, 1.3, 6.6, 8.0, wf=0.6, round_ends=False)       # wheelhouse
    s.bcf_stack(2.0, 0.0, 6.6, 8.7, ru=0.55, rv=0.55, rake=0.0, taper=0.0, pipes=1)
    s.mast(-1.8, 8.0, 9.6)
    return s


def m_quinsam():
    s = Ship(L(87.9), Bm(21), "double", taper=0.2, blunt=0.45)
    h = s.L / 2
    modern_hull(s, 2.8, 1.0, "quinsam", doors=False, rail=True, mark=False, name=False)
    s.cars(-h + 1.6, h - 1.6, -s.B / 2 + 0.3, s.B / 2 - 2.0, 2.8, seed=5)
    s.block(-h + 3.0, h - 3.0, 2.8, 5.0, wf=1.0, v0=s.B / 2 - 2.0, v1=s.B / 2 - 0.1,
            windows=False, decals=mark(1.5, 3.8, 1.0))
    s.block(-2.2, 2.2, 5.0, 6.6, wf=1.0, v0=s.B / 2 - 1.9, v1=s.B / 2 - 0.2)
    s.box(-h + 3.0, h - 3.0, s.B / 2 - 2.01, s.B / 2 - 0.09, 4.75, 4.9, "bcfblue")
    s.bcf_stack(-3.4, s.B / 2 - 1.0, 5.0, 7.4, ru=0.5, rv=0.5, pipes=1)
    ramp_gantries(s, 2.8)
    return s


def m_quinitsa():
    s = Ship(L(65), Bm(18), "double", taper=0.22, blunt=0.45)
    h = s.L / 2
    modern_hull(s, 2.6, 1.0, "quinitsa", doors=False, rail=True, mark=False, name=False)
    s.cars(-h + 1.4, h - 1.4, -s.B / 2 + 1.7, s.B / 2 - 0.3, 2.6, seed=9)
    s.block(-h + 2.6, h - 2.6, 2.6, 4.8, wf=1.0, v0=-s.B / 2 + 0.1, v1=-s.B / 2 + 1.7,
            windows=False, decals=mark(-1.0, 3.6, 1.0))
    s.block(-1.6, 1.6, 4.8, 6.2, wf=1.0, v0=-s.B / 2 + 0.2, v1=-s.B / 2 + 1.6)
    s.box(-h + 2.6, h - 2.6, -s.B / 2 + 0.09, -s.B / 2 + 1.71, 4.55, 4.7, "bcfblue")
    s.bcf_stack(2.6, -s.B / 2 + 0.9, 4.8, 6.8, ru=0.45, rv=0.45, pipes=1)
    ramp_gantries(s, 2.6)
    return s


def m_tclass():
    """T-class (Tachek / Quadra Queen II): full-width central house over the
    car deck, logo stack at one end of it, wheelhouse at the other."""
    s = Ship(L(49), Bm(15.5), "double", taper=0.22, blunt=0.45)
    h = s.L / 2
    hh = 0.3 * s.L
    modern_hull(s, 2.2, 0.9, "tclass", doors=False, rail=True, mark=False, name=False)
    s.cars(-h + 1.0, -hh - 0.2, -s.B / 2 + 0.4, s.B / 2 - 0.4, 2.2, seed=2)
    s.cars(hh + 0.2, h - 1.0, -s.B / 2 + 0.4, s.B / 2 - 0.4, 2.2, seed=3)
    central_house(s, hh, 2.2, 4.3, mark_w=3.25, mark_h=0.95)
    s.block(-hh + 0.3, hh - 0.6, 4.3, 5.6, wf=0.9, rect=True, panes=(0.42, 0.62))
    s.block(0.3, hh - 0.6, 5.6, 6.8, wf=0.7, round_ends=False)   # wheelhouse
    s.bcf_stack(-hh + 1.0, 0.0, 4.3, 6.3, ru=0.5, rv=0.55, rake=0.0, taper=0.0, pipes=1)
    s.mast(1.2, 6.8, 8.0)
    return s


def m_nimpkish():
    s = Ship(L(46), Bm(13), "single", taper=0.28)
    h = s.L / 2
    modern_hull(s, 2.2, 0.9, "nimpkish", sheer=0.6, rail=True, mark=False, name=False)
    s.cars(-h + 0.8, h - 5.0, -s.B / 2 + 0.4, s.B / 2 - 0.4, 2.2, seed=4)
    s.block(h - 5.0, h - 2.6, 2.2, 4.4, wf=0.9)
    s.block(h - 4.6, h - 3.0, 4.4, 5.8, wf=0.75, round_ends=False)
    s.bcf_stack(h - 5.4, 0.0, 2.2, 5.4, ru=0.4, rv=0.4, pipes=1)
    return s


# ---------------------------------------------------------------------------
# MV Coho (Black Ball Ferry Line)
# ---------------------------------------------------------------------------

def m_coho():
    """Current livery: white hull and superstructure, red band above a black
    boot-top, white funnel with a red band under a black cap. The funnel sits
    just forward of midships, the bridge well forward."""
    s = Ship(L(104.6), Bm(22), "single", taper=0.3)
    h = s.L / 2
    s.hull(3.8, lower="black", upper="white", band=0.4, sheer=1.2, deck="deck",
           boot=(0.18, "antifoul"), stripe=(0.4, 1.15, "red"), rail=False,
           decals=[dict(name="name_coho", s=-0.75 * h, w=1.35, h=0.3, mat="white")])
    s.block(-h + 1.4, h - 3.2, 3.8, 5.8, wf=0.93)
    s.block(-h + 2.4, h - 4.0, 5.8, 7.4, wf=0.82)
    s.block(h - 5.6, h - 3.8, 7.4, 8.8, wf=0.78, round_ends=False)   # bridge
    s.funnel(0.9, 0.0, 7.4, 10.8, ru=1.1, rv=0.85, mat="white", top="black", top_h=0.55,
             band=((9.7, 10.3), "red"), rake=-0.08)
    s.mast(h - 4.8, 8.8, 11.6)
    s.mast(-h + 2.2, 7.4, 9.6)
    s.lifeboat(-0.9, 0.3, -1, 7.4)
    s.lifeboat(-0.9, 0.3, 1, 7.4)
    return s


# ---------------------------------------------------------------------------
# Extra credit: the White Spot Pirate Pak, afloat
# ---------------------------------------------------------------------------

def pirate_art(L2, htop):
    """Wrap the cardboard side art round the box; mirrored so the octopus
    is always at the stern and the prow art at the bow."""
    def paint(s, w, h, side_a):
        return [(side_a == sa, dict(tex=tex, s=0.0, w=htop / 2, h=htop, width=2 * L2))
                for sa, tex in ((True, "tex_pirate"), (False, "tex_pirate_m"))]
    return paint


def pirate_deck(U, V):
    """Printed wooden deck planks (lengthwise) on the raised ends."""
    return [(np.mod(V + 0.1, 0.42) < 0.06, "deckline"),
            (np.mod(U, 2.3) < 0.05, "deckline")]


def m_piratepak():
    """White Spot Pirate Pak (cf. photos): raised printed decks at both ends
    with round holes for the drink (prow) and the dessert/coleslaw tub
    (stern), a gold chocolate coin in its slot, the kraft sail held up by the
    straw, and the open well with the burger and fries on a paper liner."""
    import pirate as P
    s = Ship(P.L, P.B, "single", taper=0.3)
    s.scale = 1.75                     # blown up to big-ferry size
    L2 = s.L / 2
    hb = s.hb
    s.hull(P.H_WELL, lower="cardboard", upper="cardboard", band=0.0, deck="deckwood",
           height_fn=P.profile, deck_paint=pirate_deck, paint=pirate_art(L2, P.H_TIP))
    s.carve(P.STERN_END, P.PROW_START, 0.16, 0.5)            # the open well
    # printed stern end: red planks under the yellow deck-edge trim
    s.solid(lambda U, V, W: [
        ((U < -L2 + 0.12) & (np.abs(V) <= hb(U)) & (W <= P.H_DECK), "red"),
        ((U < -L2 + 0.12) & (np.abs(V) <= hb(U)) & (W > P.H_DECK - 0.35) &
         (W <= P.H_DECK), "yellow"),
        ((U < -L2 + 0.12) & (np.abs(V) <= hb(U)) & (W <= 0.9), "blue")],
        None, -L2, -L2 + 0.2)
    s.carve(P.CURVE_START + 0.3, L2, 0.14, P.H_DECK)          # hollow curved prow
    # paper liner in the well
    s.solid(lambda U, V, W: (U > P.STERN_END) & (U < P.PROW_START) &
            (np.abs(V) < hb(U) - 0.16) & (W > 0.5) & (W <= 0.62), "paper",
            P.STERN_END, P.PROW_START)

    # --- prow deck: clear cup of cola with a flat lid
    cu = 3.5
    s.funnel(cu, 0.0, P.H_DECK - 1.0, P.H_DECK + 2.6, ru=1.0, rv=1.0, mat="cola", top="cola",
             top_h=0, taper=0.15, hollow=False, band=((P.H_DECK + 1.0, P.H_DECK + 1.25), "green"))
    s.funnel(cu, 0.0, P.H_DECK + 2.6, P.H_DECK + 2.9, ru=1.2, rv=1.2, mat="lid", top="lid",
             top_h=0, hollow=False)

    # --- the kraft sail across the prow deck edge, held up by the straw
    su = P.PROW_START + 0.35
    lean = -0.12                                              # sail and straw lean aft

    def sail(U, V, W):
        t = np.clip((W - P.H_DECK) / 5.6, 0, 1)
        chord = su + lean * (W - P.H_DECK)                    # line of the straw
        centre = chord - 0.9 * np.sin(np.pi * t)              # billows aft of it
        half = (s.B / 2 - 0.25) * (1 - 0.8 * t)
        notch = np.mod(W * 2.2, 1) < 0.18                     # ragged edge
        return (np.abs(U - centre) < 0.08) & (np.abs(V) < half - notch * 0.25) & \
            (W > P.H_DECK - 0.2) & (W < P.H_DECK + 5.6)
    s.solid(sail, "kraft", su - 2.0, su + 0.3)
    # the straw is the mast: threaded through holes at the foot and head of
    # the sail, so it runs along the sail's chord and pokes out above it
    s.funnel(su, 0.0, P.H_DECK - 0.4, P.H_DECK + 6.8, ru=0.1, rv=0.1, mat="black",
             top="black", top_h=0, rake=lean, hollow=False)

    # --- stern deck: black tub of coleslaw, and the gold coin in its slot
    tu = -L2 + 1.7
    s.funnel(tu, 0.0, P.H_DECK - 0.8, P.H_DECK + 0.2, ru=1.05, rv=1.05, mat="black",
             top="black", top_h=0, hollow=False)
    def slaw(U, V, W):
        mound = (((U - tu) / 0.9) ** 2 + (V / 0.9) ** 2 +
                 ((W - P.H_DECK) / 0.7) ** 2 <= 1) & (W > P.H_DECK)
        fleck = np.mod(U * 3.1 + V * 2.3 + W * 4.7, 1) < 0.14
        return [(mound, "slaw"), (mound & fleck, "carrot")]
    s.solid(slaw, None, tu - 1, tu + 1)
    s.ellipsoid(P.STERN_END - 0.7, 1.0, P.H_DECK + 0.45, 0.5, 0.07, 0.5, "gold")

    # --- the burger in the well, fries tucked in beside it
    bu, z = -0.5, 0.7                                               # riding on the fries
    s.ellipsoid(bu, 0.0, z + 0.55, 1.75, 1.75, 0.55, "bunlight")    # bottom bun
    s.ellipsoid(bu, 0.0, z + 1.1, 1.95, 1.95, 0.22, "lettuce")      # frilly lettuce
    s.funnel(bu, 0.0, z + 1.15, z + 1.4, ru=1.6, rv=1.6, mat="tomato", top="tomato", top_h=0,
             hollow=False)
    s.funnel(bu, 0.0, z + 1.4, z + 2.1, ru=1.65, rv=1.65, mat="patty", top="patty", top_h=0,
             hollow=False)
    s.ellipsoid(bu, 0.0, z + 2.15, 1.85, 1.85, 0.12, "cheese")
    s.funnel(bu, 0.0, z + 2.2, z + 4.2, ru=1.8, rv=1.8, mat="bun", top="bunlight", top_h=0.45,
             hollow=False, profile="dome")
    s.ellipsoid(bu + 0.2, -0.3, z + 4.25, 0.75, 0.55, 0.12, "pickle")  # pickle chip
    rng = np.random.RandomState(4)
    for _ in range(9):
        fu = rng.uniform(P.PROW_START - 1.6, P.PROW_START - 0.4)
        fv = rng.uniform(-1.6, 1.6)
        fz = rng.uniform(0.6, 1.6)
        s.box(fu - 0.12, fu + 0.12, fv - 0.5, fv + 0.5, fz, fz + 0.24, "fries")
    return s


# ---------------------------------------------------------------------------
# Victoria Clipper (Clipper Navigation / FRS Clipper), Seattle - Victoria
# ---------------------------------------------------------------------------

def clipper_jack(L2, top, aft_from):
    """Union Jack wrapped round the aft hull, as on both Clippers."""
    def paint(s, w, h, side_a):
        u = np.where(side_a, s, -s)               # back to hull coordinates
        aft = u < aft_from * L2
        width = (aft_from + 1.0) * L2
        out = []
        for sa, tex in ((True, "tex_union_jack"), (False, "tex_union_jack")):
            sc = (-1.0 + aft_from) / 2 * L2 * (1 if sa else -1)
            out.append((aft & (side_a == sa) & (w > 0.25),
                        dict(tex=tex, s=sc, w=top / 2 + 0.1, h=top - 0.2, width=width)))
        return out
    return paint


def m_clipper(mk=5):
    """Victoria Clipper V (Fjellstrand 52 m, 2003; Clipper since 2019) or IV
    (Fjellstrand 40 m, 1993): passenger-only aluminium catamarans. Navy hulls,
    white superstructure with long window bands, Union Jack wrapped aft."""
    length, beam = (52, 12.3) if mk == 5 else (40, 10.0)
    s = Ship(L(length), Bm(beam), "single", taper=0.36)
    h = s.L / 2
    top = 3.2
    jack_from = -0.15 if mk == 5 else 0.05
    s.hull(top, lower="navy", upper="white", band=1.7 if mk == 5 else 2.4,
           boot=(0.15, "antifoul"), stripe=(1.15, 1.35, "white") if mk == 5 else
           (2.35, 2.55, "red"), doors=False, paint=clipper_jack(h, top, jack_from),
           windows=(2.15, 2.9, 0.5, 0.86),
           decals=[dict(name="name_clipper%d" % mk, s=0.42 * h, w=2.55, h=0.38,
                        mat="navy")])
    s.carve(-h - 1, h + 1, 0.75, -1.0, 1.0)       # tunnel between the demi-hulls
    s.block(-h + 1.0, h - 2.6, top, top + 1.5, wf=0.9, panes=(0.5, 0.86),
            decals=[dict(name="tex_union_jack", tex=True, s=-0.62 * h, w=top + 0.75,
                         h=1.5, width=0.7 * h)])
    s.block(h - 5.2, h - 3.0, top + 1.5, top + 2.7, wf=0.72, round_ends=False)   # bridge
    s.mast(h - 4.0, top + 2.7, top + 4.4)
    s.radome(h - 4.6, 0.5, top + 2.7, r=0.22)
    s.liferafts(-h + 1.4, -h + 3.2, top + 1.5, s.B / 2 * 0.9)
    return s
