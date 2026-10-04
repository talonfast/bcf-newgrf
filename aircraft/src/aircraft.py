"""
Aircraft on the ship voxel renderer.

Local coordinates: u along the fuselage (+u = nose), v spanwise, w up; all
in OpenTTD world units (w in height units, as for ships). Real dimensions
in metres are converted with M (length scale) and D_EX (cross-section
exaggeration: real fuselages would be a couple of pixels thick).
"""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "common"))

import numpy as np

import render
from render import Ship, SCALE, decal_mask, decal_size, texture_ids, ASPECT

M = 0.32          # world units per metre along/across
D_EX = 1.9        # fuselage / nacelle / fin thickness exaggeration


class Aircraft(Ship):
    def __init__(self, length_m, span_m, dia_m):
        L, span = length_m * M, span_m * M
        super().__init__(L, span + 1.0, "double", taper=0.05, blunt=1.0)
        self.scale = 1.0 / SCALE                 # model units are world units
        self.wake = False
        self.ground_shadow = False
        self.R = dia_m * M * D_EX / 2
        self.wc = self.R + 0.6                  # fuselage centreline height (gear down)
        self.top_z = self.wc + self.R
        self.span = span
        self.weather = 0.0
        self.flat_mats = ("wingrey",)

    def _top(self):
        return self.top_z + 1.0

    # --- geometry --------------------------------------------------------
    def radius(self, U):
        L, R = self.L, self.R
        nl, tl = self.nose_len, self.tail_len
        r = np.full(U.shape, R, np.float32)
        qn = np.clip((U - (L / 2 - nl)) / nl, 0, 1)
        r = np.where(qn > 0, R * np.sqrt(np.clip(1 - qn ** 2.2, 0, 1)), r)
        qt = np.clip(((-L / 2 + tl) - U) / tl, 0, 1)
        r = np.where(qt > 0, R * (1 - 0.82 * qt), r)
        return r

    def centre(self, U):
        L, tl = self.L, self.tail_len
        qt = np.clip(((-L / 2 + tl) - U) / tl, 0, 1)
        return self.wc + 0.75 * self.R * qt

    def fuselage(self, nose_len=0.13, tail_len=0.24, body="acwhite", belly=None,
                 window_band=0.28, door_u=()):
        self.nose_len, self.tail_len = nose_len * self.L, tail_len * self.L
        L, R = self.L, self.R

        def fn(U, V, W):
            r = self.radius(U)
            c = self.centre(U)
            dz = W - c
            inside = (V ** 2 + dz ** 2 <= r ** 2) & (np.abs(U) <= L / 2)
            out = [(inside, body)]
            if belly:
                out.append((inside & (dz < -0.35 * r), belly))
            side = inside & (np.abs(V) > 0.72 * r)
            cabin = (U < L / 2 - self.nose_len * 1.05) & (U > -L / 2 + self.tail_len * 0.95)
            win = side & cabin & (np.abs(dz - window_band * R) < 0.09 * R + 0.05) & \
                (np.mod(U, 0.55) < 0.28)
            out.append((win, "window"))
            for du in door_u:                        # passenger doors
                out.append((side & (np.abs(U - du * L / 2) < 0.18) & (dz > -0.35 * R) &
                            (dz < 0.55 * R) & (np.abs(np.abs(U - du * L / 2) - 0.16) < 0.04), "nacgrey"))
            # cockpit: windscreen panes on the skin only (front and side windows),
            # with frames between the panes
            skin = inside & (V ** 2 + dz ** 2 > (r - 0.14) ** 2)
            un = (U - (L / 2 - self.nose_len)) / self.nose_len          # 0..1 along the nose
            band = (dz > 0.18 * R) & (dz < 0.5 * R)
            front = skin & band & (un > 0.55) & (un < 0.82) & (np.abs(V) < 0.62 * r)
            side_w = skin & band & (un > 0.32) & (un <= 0.55) & (np.abs(V) > 0.45 * r)
            panes = (front | side_w) & ~(np.abs(np.mod(U, 0.42) - 0.21) < 0.03)
            out.append((panes, "acblack"))
            return out
        self.solid(fn, None, -L / 2, L / 2)
        return self

    def wing(self, root_u, root_chord, tip_chord, sweep_deg, dihedral=0.03, z_rel=-0.45,
             mat="wingrey", winglet=None, high=False, thick=0.11):
        """Swept wing: leading edge at root_u (on the centreline), spanning
        +-span/2. winglet: None, 'blended', 'scimitar', 'raked'."""
        R, half = self.R, self.span / 2
        t = np.tan(np.radians(sweep_deg))
        wz0 = self.wc + (0.75 * R if high else z_rel * R)

        def fn(U, V, W):
            av = np.abs(V)
            f = np.clip(av / half, 0, 1)
            le = root_u - t * av
            chord = root_chord + (tip_chord - root_chord) * f
            zc = wz0 + dihedral * av
            th = np.maximum(thick * chord, 0.24)
            m = (av <= half) & (U <= le) & (U >= le - chord) & (np.abs(W - zc) <= th / 2)
            out = [(m, mat)]
            if winglet in ("blended", "scimitar"):
                wl = (av > half - 0.1) & (av <= half + 0.05) & (U <= le) & (U >= le - tip_chord) & \
                    (W > zc) & (W <= zc + 0.9 * tip_chord + 0.4)
                out.append((wl, mat))
                if winglet == "scimitar":
                    dn = (av > half - 0.1) & (av <= half + 0.05) & (U <= le) & \
                        (U >= le - tip_chord * 0.6) & (W < zc) & (W >= zc - 0.4 * tip_chord - 0.2)
                    out.append((dn, mat))
            return out
        self.solid(fn, None, root_u - root_chord - t * half - 1, root_u + 1)
        self.wing_params = (root_u, root_chord, tip_chord, t, wz0, dihedral)
        return self

    def wing_at(self, v):
        root_u, rc, tc, t, wz0, dih = self.wing_params
        f = abs(v) / (self.span / 2)
        return root_u - t * abs(v), rc + (tc - rc) * f, wz0 + dih * abs(v)

    def engines(self, v_frac=0.34, dia_m=3.0, len_m=5.0, mat="acwhite", lip="nacgrey",
                prop=False, above=False, swoosh=None):
        """Pod engines under (or, for turboprops, through) the wing."""
        for side in (-1, 1):
            v = side * v_frac * self.span / 2
            le, chord, zw = self.wing_at(v)
            r = dia_m * M * D_EX / 2 * 0.62
            ln = len_m * M
            uc = le + (0.35 * ln if not prop else -0.1 * chord + 0.1 * ln)
            zc = zw - (r + 0.12 if not above else -0.05)

            def fn(U, V, W, v=v, r=r, ln=ln, uc=uc, zc=zc):
                q = np.clip((U - uc) / (ln / 2), -1, 1)
                rr = r * np.where(q < 0, 1 - 0.35 * q ** 2, 1.0)
                m = (np.abs(U - uc) <= ln / 2) & ((V - v) ** 2 + (W - zc) ** 2 <= rr ** 2)
                out = [(m, mat)]
                if swoosh:                       # sweep across the aft nacelle
                    q2 = (uc + ln / 2 - U) / ln
                    out.append((m & (q2 > 0.45) & ((W - zc) < r * (1.6 * q2 - 1.0)), swoosh))
                out += [(m & (U > uc + ln / 2 - 0.25), lip),
                       (m & (U > uc + ln / 2 - 0.12) & ((V - v) ** 2 + (W - zc) ** 2 <= (0.6 * rr) ** 2),
                        "acblack")]
                if prop:
                    up = uc + ln / 2 + 0.15
                    blades = (np.abs(U - up) < 0.07) & \
                        (((np.abs(V - v) < 0.12) & (np.abs(W - zc) < 1.9 * r)) |
                         ((np.abs(W - zc) < 0.12) & (np.abs(V - v) < 1.9 * r)))
                    out.append((blades, "acblack"))
                    out.append(((np.abs(U - up - 0.15) < 0.15) & ((V - v) ** 2 + (W - zc) ** 2 < 0.3 ** 2),
                                "acblack"))
                return out
            self.solid(fn, None, uc - ln / 2 - 0.3, uc + ln / 2 + 0.6)
        return self

    def fin(self, height_m, root_chord_m, tip_chord_m, sweep_deg, mat="acwhite", logo=None,
            paint=None):
        """Vertical fin at the tail. logo = (texture name, u_centre_frac, w_centre_frac, h_frac)."""
        L, R = self.L, self.R
        H, rc, tc = height_m * M * D_EX, root_chord_m * M, tip_chord_m * M   # fin drawn taller to match the thick fuselage
        t = np.tan(np.radians(sweep_deg))
        u_te = -L / 2 + 0.2
        u_le0 = u_te + rc
        z0 = self.centre(np.array([u_te + rc * 0.5]))[0] + self.radius(np.array([u_te + rc * 0.5]))[0] * 0.6
        self.top_z = max(self.top_z, z0 + H)
        th = max(0.3, 0.22 * D_EX)

        def fn(U, V, W):
            f = np.clip((W - z0) / H, 0, 1)
            le = u_le0 - t * (W - z0)
            chord = rc + (tc - rc) * f
            m = (W > z0 - 0.4) & (W <= z0 + H) & (U <= le) & (U >= le - chord) & (np.abs(V) <= th / 2)
            out = [(m, mat)]
            if paint:
                out += [(m & pm, pn) for pm, pn in paint(U, V, W, z0, H, le, chord)]
            if logo:
                name, uf, wf, hf = logo
                hh = hf * H
                iw, ih = decal_size(name)
                s = np.where(V < 0, U, -U)
                uc = u_le0 - t * wf * H - (rc + (tc - rc) * wf) * (1 - uf)
                for sgn in (1, -1):
                    ids = texture_ids(name, s, W, sgn * uc, z0 + wf * H, hh, hh * iw / ih * ASPECT * 1.6)
                    side = (V < 0) if sgn == 1 else (V >= 0)
                    out.append((m & side, ids))
            return out
        self.solid(fn, None, u_te - 0.5, u_le0 + 1.0)
        self.fin_params = (u_te, rc, z0, H, t)
        return self

    def stabiliser(self, span_m, root_chord_m, sweep_deg, t_tail=False, mat="acwhite"):
        u_te, rc_f, z0, H, tf = self.fin_params
        half = span_m * M / 2
        rc = root_chord_m * M
        t = np.tan(np.radians(sweep_deg))
        zs = (z0 + H - 0.1) if t_tail else self.centre(np.array([u_te + 0.4]))[0]
        u_le = (u_te + rc_f - tf * H + 0.2) if t_tail else u_te + rc + 0.3

        def fn(U, V, W):
            av = np.abs(V)
            le = u_le - t * av
            chord = rc * (1 - 0.55 * av / half)
            return [((av <= half) & (U <= le) & (U >= le - chord) & (np.abs(W - zs - 0.05 * av) <= 0.13), mat)]
        self.solid(fn, None, u_le - rc - t * half - 0.5, u_le + 0.5)
        return self

    def title(self, name, u_frac, w_frac, h, mat, side_u=None):
        """Text on both fuselage sides, centred at u_frac of half length forward."""
        L, R = self.L, self.R
        iw, ih = decal_size(name)
        width = h * iw / ih * ASPECT * 1.6

        def fn(U, V, W):
            r = self.radius(U)
            dz = W - self.centre(U)
            surf = (V ** 2 + dz ** 2 <= r ** 2) & (np.abs(V) > 0.6 * r)
            s = np.where(V < 0, U, -U)
            uc = u_frac * L / 2
            m = surf & (((V < 0) & decal_mask(name, s, W, uc, self.wc + w_frac * R, h, width=width)) |
                        ((V >= 0) & decal_mask(name, s, W, -uc, self.wc + w_frac * R, h, width=width)))
            return [(m, mat)]
        self.solid(fn, None, -L / 2, L / 2)
        return self

    def roundel(self, name, u_frac, w_frac, h):
        L, R = self.L, self.R
        iw, ih = decal_size(name)

        def fn(U, V, W):
            r = self.radius(U)
            dz = W - self.centre(U)
            surf = (V ** 2 + dz ** 2 <= r ** 2) & (np.abs(V) > 0.6 * r)
            s = np.where(V < 0, U, -U)
            out = []
            for sgn, side in ((1, V < 0), (-1, V >= 0)):
                ids = texture_ids(name, s, W, sgn * u_frac * L / 2, self.wc + w_frac * R, h,
                                  h * iw / ih * ASPECT * 1.6)
                out.append((surf & side, ids))
            return out
        self.solid(fn, None, -L / 2, L / 2)
        return self

    def paint(self, fn_paint):
        """Arbitrary fuselage paint: fn_paint(U, V, W, dz, r) -> [(mask, mat)]."""
        L = self.L

        def fn(U, V, W):
            r = self.radius(U)
            dz = W - self.centre(U)
            surf = (V ** 2 + dz ** 2 <= r ** 2)
            return [(surf & m, n) for m, n in fn_paint(U, V, W, dz, r)]
        self.solid(fn, None, -L / 2, L / 2)
        return self

    def gear(self, nose_u_frac=0.78, main_u=None):
        """Undercarriage: nose leg and two main bogies, tyres dark."""
        L, R = self.L, self.R
        mu = main_u if main_u is not None else self.wing_params[0] - self.wing_params[1] * 0.75
        legs = [(nose_u_frac * L / 2, 0.0), (mu, -0.55 * R), (mu, 0.55 * R)]
        for u, v in legs:
            zb = self.centre(np.array([u]))[0] - self.radius(np.array([u]))[0] * 0.9
            self.box(u - 0.06, u + 0.06, v - 0.06, v + 0.06, 0.25, zb, "nacgrey")
            self.box(u - 0.25, u + 0.25, v - 0.18, v + 0.18, 0.0, 0.42, "tyre")
        return self


# ---------------------------------------------------------------------------
# Liveries
# ---------------------------------------------------------------------------

def air_canada(a, express=False):
    a.fin_logo = ("tex_ac_rondelle", 0.55, 0.5, 0.62)
    if express:
        a.title("ac_express", 0.20, 0.45, 0.62, "acblack")
    else:
        a.title("ac_title", 0.42, 0.62, 0.42, "acblack")
        a.roundel("tex_ac_rondelle", 0.70, 0.05, 0.42)


def alaska_paint(L):
    """Alaska's current livery (see the 787-9): a swoosh that starts as a
    point near the wing trailing edge at window height and widens aft until
    it covers the whole fuselage at the tail - royal blue on top, bright
    teal in the middle, turquoise underneath."""
    def fn(U, V, W, dz, r):
        x = (U + L / 2) / L                          # 0 tail .. 1 nose
        t = np.clip((0.56 - x) / 0.44, 0, 1)         # 0 at the swoosh tip .. 1 at the tail
        top = (0.15 + 0.95 * t ** 0.7) * r           # upper edge rises towards the tail
        bot = (0.15 - 1.3 * t ** 0.55) * r           # lower edge sweeps under the belly
        sw = (x < 0.56) & (dz <= top) & (dz >= bot)
        f = (dz - bot) / np.maximum(top - bot, 1e-3)  # 0 bottom .. 1 top of the swoosh
        return [(sw, "asturq"), (sw & (f > 0.42), "asmid"), (sw & (f > 0.8), "asroyal")]
    return fn


def alaska_fin(U, V, W, z0, H, le, chord):
    """Aurora tail: navy at the top and leading edge, royal blue, then teal
    streaks sweeping up and back from the root."""
    f = np.clip((W - z0) / H, 0, 1)
    x = (le - U) / np.maximum(chord, 1e-3)           # 0 leading edge .. 1 trailing edge
    streak = np.abs(x - (0.25 + 0.9 * (1 - f))) < 0.22
    return [(f < 0.8, "asroyal"), (streak & (f < 0.7), "asmid"),
            ((np.abs(x - (0.55 + 0.9 * (1 - f))) < 0.16) & (f < 0.55), "asturq"),
            ((f > 0.75) | (x < 0.1), "asnavy")]


def westjet_fin(U, V, W, z0, H, le, chord):
    f = (W - z0) / H
    x = (le - U) / np.maximum(chord, 1e-3)
    return [(np.abs(x - (0.95 - 0.8 * f)) < 0.13, "wjlight"),
            (np.abs(x - (1.25 - 0.8 * f)) < 0.07, "wjlight")]


# ---------------------------------------------------------------------------
# Types. Real dimensions (m) from manufacturer data, rounded.
# ---------------------------------------------------------------------------

def _jet(length, span, dia, root_u_frac, rc, tc, sweep, eng_dia, eng_len, eng_v, fin_h, fin_rc,
         fin_tc, fin_sweep, stab_span, stab_rc, winglet, airline, doors=(0.78, -0.82), eng_mat=None,
         title=None):
    a = Aircraft(length, span, dia)
    L = a.L
    body = "acwhite"
    a.fuselage(body=body, door_u=doors)
    a.wing(root_u_frac * L / 2, rc * M, tc * M, sweep, winglet=winglet)
    fin_mat = {"ac": "acblack", "as": "asnavy", "wj": "wjteal"}[airline]
    if airline == "ac":
        air_canada(a, express=False)
        a.fin(fin_h, fin_rc, fin_tc, fin_sweep, mat=fin_mat, logo=a.fin_logo)
    elif airline == "as":
        a.paint(alaska_paint(L))
        a.title("alaska", 0.56, 0.05, 1.35, "asnavy")
        if title == "horizon":
            a.title("horizon", 0.18, -0.3, 0.3, "asnavy")
        a.fin(fin_h, fin_rc, fin_tc, fin_sweep, mat=fin_mat, paint=alaska_fin)
    else:
        a.title("westjet", 0.40, 0.45, 0.55, "wjteal")
        a.fin(fin_h, fin_rc, fin_tc, fin_sweep, mat=fin_mat, logo=("tex_wj_leaf", 0.55, 0.5, 0.6))
    a.stabiliser(stab_span, stab_rc, fin_sweep - 3, mat=body)
    a.engines(eng_v, eng_dia, eng_len, mat=eng_mat or ("acblack" if airline == "ac" else "acwhite"),
              lip="nacgrey", swoosh="asturq" if airline == "as" else None)
    a.gear()
    return a


def b787_9(airline="ac"):
    return _jet(62.8, 60.1, 5.77, 0.18, 11.0, 2.4, 32, 3.6, 7.0, 0.32, 9.0, 9.0, 3.4, 40,
                19.0, 5.0, "raked", airline, doors=(0.82, 0.35, -0.1, -0.86), eng_mat="acwhite")


def b777_300er():
    return _jet(73.9, 64.8, 6.2, 0.16, 12.0, 2.6, 31.6, 4.2, 7.6, 0.32, 9.8, 9.6, 3.6, 40,
                21.0, 5.5, "raked", "ac", doors=(0.84, 0.45, 0.0, -0.45, -0.86), eng_mat="acwhite")


def a220_300():
    return _jet(38.7, 35.1, 3.7, 0.12, 7.0, 1.6, 25, 2.3, 4.5, 0.34, 6.5, 6.0, 2.4, 38,
                11.0, 3.2, None, "ac")


def b737_max8(airline="ac"):
    return _jet(39.5, 35.9, 3.76, 0.14, 7.2, 1.6, 25, 2.4, 4.6, 0.33, 7.4, 6.6, 2.2, 38,
                14.4, 3.4, "scimitar", airline)


def b737_max9():
    return _jet(42.2, 35.9, 3.76, 0.14, 7.2, 1.6, 25, 2.4, 4.6, 0.33, 7.4, 6.6, 2.2, 38,
                14.4, 3.4, "scimitar", "as")


def b737_900er():
    return _jet(42.1, 35.8, 3.76, 0.14, 7.2, 1.6, 25, 2.0, 4.2, 0.33, 7.4, 6.6, 2.2, 38,
                14.4, 3.4, "blended", "as")


def b737_800_wj():
    return _jet(39.5, 35.8, 3.76, 0.14, 7.2, 1.6, 25, 2.0, 4.2, 0.33, 7.4, 6.6, 2.2, 38,
                14.4, 3.4, "blended", "wj")


def a321():
    return _jet(44.5, 35.8, 3.95, 0.12, 7.0, 1.6, 25, 2.2, 4.4, 0.33, 6.6, 6.0, 2.2, 38,
                12.5, 3.2, "blended", "ac", doors=(0.82, 0.25, -0.2, -0.86))


def e175():
    return _jet(31.7, 28.6, 3.0, 0.12, 5.6, 1.4, 24, 1.7, 3.4, 0.32, 6.0, 5.4, 2.0, 40,
                10.0, 2.8, "blended", "as", title="horizon")


def dash8_400():
    """Q400 / Dash 8-400: long thin fuselage, high straight wing, T-tail,
    turboprop nacelles with six-blade props (shown as two blades crossed)."""
    a = Aircraft(32.8, 28.4, 2.7)
    L = a.L
    a.fuselage(nose_len=0.11, tail_len=0.26, door_u=(0.8, -0.8))
    a.wing(0.12 * L / 2, 3.0 * M, 1.4 * M, 3, dihedral=0.02, high=True, thick=0.15)
    air_canada(a, express=True)
    a.fin(6.6, 5.6, 3.0, 35, mat="acblack", logo=("tex_ac_rondelle", 0.55, 0.45, 0.55))
    a.stabiliser(8.0, 2.4, 10, t_tail=True, mat="acblack")
    a.engines(0.28, 2.1, 6.0, mat="acwhite", lip="nacgrey", prop=True, above=True)
    a.gear(nose_u_frac=0.8, main_u=0.0)
    return a
