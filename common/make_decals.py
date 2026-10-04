"""Generate livery decal masks into src/decals/ (white = ink).

These are committed, so the normal build does not need these fonts. Re-run
only to tweak artwork (needs macOS system fonts):
    python src/make_decals.py
"""
import os

import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pirate  # noqa: E402
OUT = os.path.join(HERE, "decals")
FONTS = "/System/Library/Fonts/Supplemental/"


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def band(xs, ys, centre, thick):
    return np.abs(ys - centre) < thick


def wave_icon(w, h):
    """The BC Ferries 'waves': two thick S-curve bands rising left to right,
    with a thin crest line, as on the hull wordmark."""
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    x = xs / w
    y = 1 - ys / h                                    # 0 bottom .. 1 top
    m = np.zeros((h, w), dtype=bool)
    for i, (off, t) in enumerate(((0.14, 0.13), (0.46, 0.11), (0.72, 0.045))):
        c = off + 0.16 * x + 0.10 * np.sin(2 * np.pi * (x * 1.05 - 0.15))
        m |= band(x, y, c, t) & (x > 0.02 + 0.07 * i) & (x < 0.99)
    return m


def wordmark():
    """'~BCFerries' wordmark as painted on the hull sides."""
    h = 240
    f = font("Arial Bold Italic.ttf", 250)
    text = "BCFerries"
    tw = int(f.getlength(text))
    icon_w = 190
    W = icon_w + tw - 20
    im = Image.new("L", (W, h), 0)
    d = ImageDraw.Draw(im)
    # tighter tracking, like the real (condensed) logotype
    x = icon_w - 30
    for ch in text:
        d.text((x, h - 12), ch, font=f, fill=255, anchor="ls")
        x += f.getlength(ch) - 14
    im = im.crop((0, 0, min(W, int(x) + 20), h))
    arr = np.array(im) > 127
    icon = wave_icon(icon_w + 10, int(h * 0.75))
    arr[h - icon.shape[0] - 20:h - 20, :icon.shape[1]] |= icon
    return arr


def stack_logo():
    """Big white wave logo on the stacks (cf. Coastal Celebration, Spirit and
    Queen of Surrey stacks): two thick S-curved bands, tapered at both ends,
    rising gently left to right. x 0..1 left to right as seen, y 0..1 up."""
    w, h = 480, 480
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    x, y = xs / w, 1 - ys / h
    m = np.zeros((h, w), dtype=bool)
    for off in (0.30, 0.58):
        t = np.clip(np.sin(np.pi * np.clip((x - 0.08) / 0.86, 0, 1)), 0, 1) ** 0.6
        c = off + 0.12 * x + 0.10 * np.sin(2 * np.pi * (x * 1.0 - 0.05))
        m |= (np.abs(y - c) < 0.085 * t) & (x > 0.08) & (x < 0.94)
    return m


def stack_grille():
    """Horizontal louvres on the Coastal class casing (dark slats)."""
    w, h = 200, 400
    ys = np.mgrid[0:h, 0:w][0]
    return (ys % 26) < 9


# ---------------------------------------------------------------------------
# Vancouver 2010 wrap artwork (RGBA textures, drawn from scratch; composition
# follows photos of Coastal Renaissance / Celebration / Inspiration 2008-10)
# ---------------------------------------------------------------------------
TW, TH = 800, 320


def _grad(top, bottom, w=TW, h=TH):
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    g = np.array(top, np.float32) * (1 - t) + np.array(bottom, np.float32) * t
    return np.repeat(g, w, axis=1)


def _img(arr):
    a = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([a, np.full(a.shape[:2], 255, np.uint8)]))


def _limb(d, pts, width, fill):
    for a, b in zip(pts, pts[1:]):
        d.line([a, b], fill=fill, width=int(width))
    for x, y in pts:
        r = width / 2
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def _figure(d, x, y, k, suit, trim, helmet, dir=-1, pose="skate"):
    """Solid athlete silhouette, facing `dir` (-1 = left), hips at (x, y)."""
    f = lambda dx, dy: (x + dir * dx * k, y + dy * k)      # noqa: E731
    sh = f(72, -26)
    if pose == "skate":
        # back leg stretched out behind, front leg deeply bent, hand on the ice
        _limb(d, [f(0, 0), f(-48, 30), f(-96, 48)], 20 * k, suit)
        _limb(d, [f(0, 0), f(34, 34), f(8, 70)], 22 * k, suit)
        _limb(d, [sh, f(58, 20), f(70, 64)], 13 * k, suit)
        _limb(d, [sh, f(20, -34), f(-12, -26)], 12 * k, suit)
        d.line([f(-20, 80), f(40, 80)], fill=(70, 70, 80, 255), width=int(4 * k))
    else:
        # downhill tuck: knees forward, torso flat, poles under the arms
        _limb(d, [f(0, 0), f(40, 30), f(16, 64)], 22 * k, suit)
        _limb(d, [sh, f(84, 8), f(96, 0)], 12 * k, suit)
        d.line([f(96, 0), f(-60, -20)], fill=(30, 30, 30, 255), width=int(4 * k))
        d.line([f(-70, 76), f(130, 50)], fill=(20, 20, 26, 255), width=int(7 * k))
    _limb(d, [f(0, 0), sh], 30 * k, suit)                   # torso
    _limb(d, [f(10, -6), f(60, -22)], 8 * k, trim)          # suit stripe
    hx, hy = f(94, -34)
    d.ellipse([hx - 16 * k, hy - 16 * k, hx + 16 * k, hy + 16 * k], fill=helmet)


def tex_alpine():
    """Side 1, left: alpine skier in a tuck on a royal-blue field."""
    a = _grad((22, 70, 190), (40, 110, 214))
    im = _img(a)
    d = ImageDraw.Draw(im)
    d.polygon([(TW * 0.35, TH), (TW, TH * 0.72), (TW, TH)], fill=(236, 242, 250, 255))  # snow
    for i in range(40):                                                          # spray
        rx, ry = 380 + (i * 37) % 260, 190 + (i * 53) % 90
        d.ellipse([rx, ry, rx + 10, ry + 8], fill=(250, 252, 255, 255))
    _figure(d, 470, 180, 1.6, (200, 30, 36, 255), (20, 20, 26, 255), (230, 230, 235, 255),
            dir=1, pose="tuck")
    return im


def tex_sitski():
    """Side 1, right: sit-skier on a dark navy/indigo field."""
    a = _grad((18, 24, 80), (46, 44, 120))
    im = _img(a)
    d = ImageDraw.Draw(im)
    d.polygon([(0, TH * 0.75), (TW, TH * 0.45), (TW, TH), (0, TH)], fill=(170, 186, 222, 255))
    d.polygon([(0, TH * 0.85), (TW, TH * 0.62), (TW, TH), (0, TH)], fill=(226, 232, 246, 255))
    # sit-ski: bucket + single ski, athlete leaning, outrigger poles
    d.ellipse([330, 150, 470, 230], fill=(26, 26, 30, 255))
    d.polygon([(370, 170), (330, 90), (360, 80), (420, 160)], fill=(200, 30, 36, 255))
    d.ellipse([318, 60, 352, 94], fill=(230, 230, 235, 255))
    d.line([(280, 262), (560, 196)], fill=(16, 16, 20, 255), width=8)
    d.line([(330, 120), (250, 230)], fill=(30, 30, 30, 255), width=5)
    d.line([(420, 150), (520, 230)], fill=(30, 30, 30, 255), width=5)
    return im


def tex_vineyard():
    """Side 2, left: Okanagan vineyard above Vaseux Lake."""
    a = _grad((150, 200, 240), (214, 232, 246))
    im = _img(a)
    d = ImageDraw.Draw(im)
    d.polygon([(0, 70), (160, 40), (330, 64), (520, 30), (800, 60), (800, 150), (0, 150)],
              fill=(118, 140, 170, 255))                                   # far ridges
    d.polygon([(0, 110), (800, 95), (800, 150), (0, 160)], fill=(40, 120, 196, 255))  # lake
    d.polygon([(400, 100), (560, 70), (800, 80), (800, 170), (420, 150)],
              fill=(196, 170, 96, 255))                                    # dry hills
    d.polygon([(0, 150), (800, 140), (800, 320), (0, 320)], fill=(150, 170, 60, 255))
    for i in range(-20, 60):                                               # vine rows
        x0 = i * 26
        d.line([(x0, 320), (x0 + 260, 150)], fill=(72, 112, 34, 255), width=7)
    d.polygon([(0, 150), (120, 140), (60, 190), (0, 200)], fill=(40, 80, 40, 255))  # trees
    return im


def tex_skaters():
    """Side 2, right: four short-track speed skaters on a pale ground."""
    a = _grad((236, 234, 246), (208, 200, 232))
    im = _img(a)
    d = ImageDraw.Draw(im)
    suits = [(24, 30, 64), (206, 28, 36), (40, 70, 180), (206, 28, 36)]
    for i, suit in enumerate(suits):
        _figure(d, 250 + i * 165, 150 + i * 8, 1.25, suit + (255,), (240, 240, 240, 255),
                (246, 206, 30, 255), dir=-1)
    return im


def _crowd_member(d, x, y, k, jersey, skin=(232, 190, 160, 255)):
    """Celebrating player: jersey torso, raised arms, helmet."""
    _limb(d, [(x - 22 * k, y - 10 * k), (x - 44 * k, y - 60 * k)], 14 * k, jersey)
    _limb(d, [(x + 22 * k, y - 10 * k), (x + 46 * k, y - 58 * k)], 14 * k, jersey)
    d.rounded_rectangle([x - 30 * k, y - 20 * k, x + 30 * k, y + 70 * k], radius=12 * k, fill=jersey)
    d.rectangle([x - 30 * k, y + 20 * k, x + 30 * k, y + 30 * k], fill=(255, 255, 255, 255))
    d.ellipse([x - 16 * k, y - 52 * k, x + 16 * k, y - 18 * k], fill=skin)
    d.chord([x - 18 * k, y - 56 * k, x + 18 * k, y - 22 * k], 180, 360, fill=(20, 20, 24, 255))


def tex_hockey():
    """Celebration, side a: Team Canada piling in to celebrate (red jerseys)."""
    im = _img(_grad((150, 20, 26), (90, 14, 20)))
    d = ImageDraw.Draw(im)
    rng = np.random.RandomState(11)
    for row, (y, k) in enumerate(((150, 1.0), (205, 1.25), (260, 1.5))):
        for i in range(7 - row):
            x = 60 + i * (115 + row * 20) + rng.randint(-15, 15)
            _crowd_member(d, x, y + rng.randint(-10, 10), k, (206, 26, 32, 255))
    return im


def tex_coast():
    """Celebration, side a: BC coast - forest shore, sea, snowy peaks."""
    im = _img(_grad((150, 196, 236), (214, 230, 244)))
    d = ImageDraw.Draw(im)
    d.polygon([(0, 120), (120, 60), (230, 105), (380, 40), (520, 100), (660, 55), (800, 95),
               (800, 170), (0, 170)], fill=(120, 136, 164, 255))
    for x0, x1, y in ((100, 160, 70), (340, 420, 48), (620, 700, 62)):
        d.polygon([(x0, y + 26), ((x0 + x1) / 2, y - 6), (x1, y + 26)], fill=(244, 248, 252, 255))
    d.rectangle([0, 160, 800, 230], fill=(30, 96, 160, 255))
    d.rectangle([0, 230, 800, 320], fill=(22, 58, 36, 255))
    for i in range(0, 800, 28):
        h = 40 + (i * 37) % 35
        d.polygon([(i, 320), (i + 14, 320 - h - 60), (i + 28, 320)], fill=(26, 70, 42, 255))
    d.rectangle([0, 280, 800, 320], fill=(22, 58, 36, 255))
    return im


def tex_rainforest():
    """Celebration, side b: deep green coastal rainforest."""
    im = _img(_grad((34, 74, 46), (18, 46, 28)))
    d = ImageDraw.Draw(im)
    rng = np.random.RandomState(5)
    for i in range(30):
        x = rng.randint(0, 800)
        w = rng.randint(30, 60)
        d.rectangle([x, 0, x + w * 0.35, 320], fill=(70, 50, 36, 255))         # trunks
        d.polygon([(x - w, 320), (x + w * 0.17, 40 + rng.randint(0, 80)), (x + w * 1.3, 320)],
                  fill=(26 + rng.randint(0, 20), 80 + rng.randint(0, 30), 44, 255))
    for i in range(60):                                                       # ferns
        x, y = rng.randint(0, 800), rng.randint(240, 320)
        d.ellipse([x, y, x + 40, y + 16], fill=(90, 150, 60, 255))
    return im


def tex_hockeyplayer():
    """Celebration, side b: a player in red driving to the net on white ice."""
    im = _img(_grad((236, 240, 246), (210, 220, 232)))
    d = ImageDraw.Draw(im)
    _figure(d, 380, 170, 1.7, (206, 26, 32, 255), (255, 255, 255, 255), (20, 20, 24, 255),
            dir=-1)
    d.line([(200, 290), (330, 250), (360, 180)], fill=(30, 30, 30, 255), width=8)  # stick
    d.ellipse([170, 282, 196, 296], fill=(20, 20, 20, 255))                        # puck
    return im


def tex_snowboard():
    """Inspiration, side a: snowboarder in the air against a dark sky."""
    im = _img(_grad((10, 18, 44), (36, 54, 104)))
    d = ImageDraw.Draw(im)
    d.polygon([(0, 260), (800, 200), (800, 320), (0, 320)], fill=(226, 234, 246, 255))
    d.line([(300, 170), (520, 120)], fill=(230, 120, 30, 255), width=16)            # board
    _figure(d, 410, 110, 1.2, (40, 150, 200, 255), (240, 240, 240, 255),
            (240, 240, 240, 255), dir=1, pose="tuck")
    for i in range(30):
        x, y = 200 + i * 9, 200 + (i * 31) % 50
        d.ellipse([x, y, x + 6, y + 6], fill=(255, 255, 255, 255))
    return im


def tex_orca():
    """Inspiration, side a: an orca breaching in deep blue water."""
    im = _img(_grad((30, 90, 160), (10, 36, 80)))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 800, 90], fill=(150, 196, 232, 255))
    d.ellipse([260, 60, 560, 200], fill=(18, 18, 22, 255))                        # body
    d.polygon([(400, 70), (430, -10), (460, 72)], fill=(18, 18, 22, 255))         # dorsal fin
    d.ellipse([300, 130, 470, 190], fill=(244, 246, 250, 255))                    # belly
    d.ellipse([480, 90, 520, 112], fill=(244, 246, 250, 255))                     # eye patch
    for i in range(40):
        x, y = 220 + (i * 41) % 400, 180 + (i * 23) % 60
        d.ellipse([x, y, x + 14, y + 10], fill=(220, 236, 248, 255))              # spray
    return im


def tex_aerials():
    """Inspiration, side b (best guess): freestyle aerials skier inverted."""
    im = _img(_grad((80, 150, 230), (180, 214, 244)))
    d = ImageDraw.Draw(im)
    d.polygon([(0, 300), (800, 240), (800, 320), (0, 320)], fill=(236, 242, 250, 255))
    _figure(d, 400, 150, 1.4, (250, 196, 40, 255), (30, 30, 30, 255), (240, 240, 240, 255),
            dir=-1, pose="skate")
    d.line([(330, 60), (470, 40)], fill=(20, 20, 26, 255), width=7)              # skis up
    return im


def tex_mountains():
    """Inspiration, side b (best guess): Coast Mountains above Howe Sound."""
    im = _img(_grad((110, 170, 226), (200, 222, 240)))
    d = ImageDraw.Draw(im)
    d.polygon([(0, 180), (150, 50), (270, 140), (420, 20), (580, 130), (700, 60), (800, 120),
               (800, 230), (0, 230)], fill=(96, 110, 140, 255))
    for x, y in ((150, 50), (420, 20), (700, 60)):
        d.polygon([(x - 50, y + 46), (x, y), (x + 50, y + 46)], fill=(246, 248, 252, 255))
    d.rectangle([0, 220, 800, 270], fill=(40, 110, 170, 255))
    d.polygon([(0, 270), (800, 255), (800, 320), (0, 320)], fill=(30, 74, 46, 255))
    return im


# ---------------------------------------------------------------------------
# Salish class hull art. Simplified, sprite-scale renderings of the real
# liveries (credited in the vehicle descriptions and README):
#   Salish Orca   - Darlene Gait (Esquimalt Nation)
#   Salish Eagle  - John Marston (Stz'uminus First Nation)
#   Salish Raven  - Thomas Cannell (Musqueam)
#   Salish Heron  - Maynard Johnny Jr. (Kwakwaka'wakw / Coast Salish)
# Each end panel faces right (towards that end of the ship); the model
# mirrors it for the opposite end.
# ---------------------------------------------------------------------------
SW, SH = 800, 300
CLEAR = (0, 0, 0, 0)


def _ovoid(d, box, outer, inner=None, pad=0.22):
    x0, y0, x1, y1 = box
    r = min(x1 - x0, y1 - y0) * 0.45
    d.rounded_rectangle(box, radius=r, fill=outer)
    if inner:
        px, py = (x1 - x0) * pad, (y1 - y0) * pad
        d.rounded_rectangle([x0 + px, y0 + py, x1 - px, y1 - py], radius=r * 0.6, fill=inner)


def _eye(d, cx, cy, w, h, line, white=(255, 255, 255, 255)):
    _ovoid(d, [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], line, white, pad=0.16)
    d.ellipse([cx - w * 0.17, cy - h * 0.24, cx + w * 0.17, cy + h * 0.24], fill=line)


def _uform(d, x, y, w, h, color, gap):
    """Formline U-form: a thick U opening upward (gap = negative space)."""
    d.rounded_rectangle([x, y, x + w, y + h], radius=w * 0.35, fill=color)
    d.rounded_rectangle([x + w * 0.22, y - 2, x + w * 0.78, y + h * 0.62], radius=w * 0.2,
                        fill=gap)


def _bez(*pts, n=24):
    """Points along a chain of cubic Bezier segments (p0 c1 c2 p1 c1 c2 p2 ...)."""
    out = []
    for k in range(0, len(pts) - 1, 3):
        p0, c1, c2, p1 = (np.array(q, np.float32) for q in pts[k:k + 4])
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(tuple((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * c1 +
                             3 * (1 - t) * t ** 2 * c2 + t ** 3 * p1))
    out.append(tuple(pts[-1]))
    return out


def _trigon(d, a, b, c, fill, bulge=0.25):
    """Formline trigon: a triangle with inward-curving sides (negative space)."""
    a, b, c = (np.array(q, np.float32) for q in (a, b, c))
    m = (a + b + c) / 3
    pts = []
    for p, q in ((a, b), (b, c), (c, a)):
        mid = (p + q) / 2 + (m - (p + q) / 2) * bulge
        pts += _bez(tuple(p), tuple(mid), tuple(mid), tuple(q), n=8)[:-1]
    d.polygon(pts, fill=fill)


def tex_salish_eagle():
    """Eagle (after John Marston's Salish Eagle livery): maroon formline,
    white negative space, black eye; head and hooked beak at the right,
    long feathered body sweeping back to the left."""
    im = Image.new("RGBA", (SW, SH), CLEAR)
    d = ImageDraw.Draw(im)
    M, W_, K, G = (124, 24, 38, 255), (255, 255, 255, 255), (22, 20, 24, 255), (126, 128, 134, 255)
    body = _bez((10, 160), (60, 70), (300, 50), (470, 60),            # back
                (560, 20), (700, 30), (740, 110),                    # crown
                (790, 140), (800, 210), (760, 250),                  # hooked beak
                (740, 215), (720, 220), (690, 230),                  # under the beak
                (560, 270), (240, 280), (10, 160))
    d.polygon(body, fill=M)
    # feathers: slanted white negative-space feather forms with trigon gaps
    for k in range(4):
        x = 50 + k * 105
        d.polygon(_bez((x, 220), (x + 10, 150), (x + 60, 100), (x + 110, 90),
                       (x + 80, 130), (x + 50, 180), (x + 40, 225), (x + 20, 230), (x + 5, 228),
                       (x, 220)), fill=W_)
        _trigon(d, (x + 50, 232), (x + 100, 226), (x + 80, 256), W_)
    # head: brow formline, big eye ovoid, mouth line, white beak split
    d.arc([470, 50, 720, 240], 205, 335, fill=W_, width=12)
    _ovoid(d, [520, 90, 690, 190], K, W_, pad=0.16)
    d.ellipse([570, 112, 640, 168], fill=K)
    d.line(_bez((600, 215), (660, 222), (700, 218), (740, 200)), fill=W_, width=10)
    _trigon(d, (740, 150), (780, 175), (745, 205), W_)
    d.polygon(_bez((0, 268), (120, 262), (260, 272), (380, 282), (260, 296), (100, 296),
                   (0, 290)), fill=G)
    return im


def tex_salish_raven():
    """Raven (after Thomas Cannell's Salish Raven livery): navy formline on
    white; head and long beak at the right end, the ship's name sits in the
    white ovoid of the head, wing feathers sweep back as long tapering forms."""
    im = Image.new("RGBA", (SW, SH), CLEAR)
    d = ImageDraw.Draw(im)
    N, W_ = (22, 34, 76, 255), (255, 255, 255, 255)
    head = _bez((470, 140), (500, 40), (640, 20), (720, 70),
                (760, 95), (800, 120), (800, 132),                   # beak tip
                (760, 140), (720, 160), (680, 190),
                (600, 250), (500, 230), (470, 140))
    d.polygon(head, fill=N)
    _ovoid(d, [520, 80, 680, 170], N, W_, pad=0.12)                  # name ovoid
    d.line([(690, 118), (792, 127)], fill=W_, width=7)               # beak split
    # sweeping wing: three long tapering feathers reaching back left
    for k, (y0, y1) in enumerate(((60, 110), (120, 170), (180, 230))):
        f = _bez((480, y0 + 10), (360, y0 - 20 - 10 * k), (180, y0 - 30), (0 + 40 * k, y0 + 20),
                 (160, y1 - 10), (340, y1 + 10), (480, y1))
        d.polygon(f, fill=N)
        _trigon(d, (300, y0 + 18), (420, y0 + 28), (380, y1 - 8), W_, 0.35)
    return im


def tex_salish_orca():
    """Orca (after Darlene Gait's Salish Orca livery): black formline body
    with grey, teal, red and purple ovoids, white belly, leaping right."""
    im = Image.new("RGBA", (SW, SH), CLEAR)
    d = ImageDraw.Draw(im)
    K, W_ = (20, 22, 28, 255), (255, 255, 255, 255)
    body = _bez((120, 170), (220, 70), (520, 60), (700, 120),
                (760, 140), (790, 160), (760, 190),
                (640, 250), (300, 260), (120, 170))
    d.polygon(body, fill=K)
    d.polygon(_bez((360, 80), (380, 20), (420, 0), (450, 10), (440, 50), (470, 80), (360, 80)),
              fill=K)                                                # dorsal fin
    d.polygon(_bez((130, 170), (60, 110), (10, 110), (0, 130), (60, 170), (60, 180), (0, 220),
                   (20, 240), (80, 220), (130, 175)), fill=K)        # flukes
    d.polygon(_bez((300, 225), (420, 200), (600, 205), (720, 180), (620, 240), (420, 255),
                   (300, 225)), fill=W_)                             # belly
    _ovoid(d, [250, 110, 380, 190], (130, 132, 140, 255), (60, 170, 170, 255))
    _ovoid(d, [430, 100, 560, 180], (190, 50, 50, 255), (120, 60, 140, 255))
    _ovoid(d, [610, 110, 700, 160], K, W_, pad=0.18)                 # eye
    d.ellipse([640, 122, 672, 148], fill=K)
    d.ellipse([560, 90, 610, 112], fill=W_)                          # eye patch
    return im


def tex_salish_heron():
    """Heron (after Maynard Johnny Jr.'s Salish Heron livery): navy formline
    with royal and light blue, orange, red and yellow; long yellow bill
    reaching right, body built from ovoids and U-forms behind."""
    im = Image.new("RGBA", (SW, SH), CLEAR)
    d = ImageDraw.Draw(im)
    Nv, Bl, Lb, O, R, Y = ((24, 36, 110, 255), (40, 96, 200, 255), (90, 170, 230, 255),
                           (240, 136, 30, 255), (206, 44, 40, 255), (250, 196, 40, 255))
    d.polygon(_bez((20, 160), (60, 40), (360, 30), (500, 90), (560, 130), (560, 220),
                   (460, 270), (200, 290), (40, 260), (20, 160)), fill=Nv)       # body
    _ovoid(d, [70, 80, 230, 220], Bl, O, pad=0.2)
    _ovoid(d, [110, 120, 190, 180], R, Y, pad=0.25)
    for k in range(3):
        x = 260 + k * 80
        d.rounded_rectangle([x, 70, x + 66, 200], radius=26, fill=Lb)
        d.rounded_rectangle([x + 14, 70, x + 52, 150], radius=16, fill=Nv)
    d.polygon(_bez((480, 120), (540, 40), (600, 30), (650, 60), (660, 110), (600, 150),
                   (540, 170), (500, 160), (490, 140), (480, 120)), fill=Nv)    # head
    _ovoid(d, [565, 60, 635, 110], Nv, (255, 255, 255, 255), pad=0.15)
    d.ellipse([590, 72, 614, 98], fill=Nv)
    d.polygon(_bez((640, 70), (720, 70), (780, 80), (800, 88), (780, 96), (720, 104),
                   (640, 104)), fill=Y)                                          # long bill
    d.polygon(_bez((420, 230), (480, 250), (520, 290), (560, 300), (500, 300), (440, 280),
                   (420, 230)), fill=R)
    return im


def tex_salish_wave():
    """Salish Orca: the aqua wave field with white curling crests."""
    w, h = 1600, 300
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    top = 110 + 40 * np.sin(xs / 140) + 20 * np.sin(xs / 47)
    a = np.zeros((h, w, 4), np.uint8)
    field = ys > top
    a[field] = (118, 206, 204, 255)
    a[field & (ys > top + 60)] = (80, 180, 186, 255)
    crest = (ys > top - 14) & (ys <= top) | ((ys > top + 30) & (ys < top + 40) &
                                             (np.sin(xs / 25) > 0.6))
    a[crest] = (255, 255, 255, 255)
    return Image.fromarray(a)


def tex_union_jack():
    """Union Jack (2:1), for the Victoria Clipper livery."""
    w, h = 600, 300
    im = Image.new("RGBA", (w, h), (1, 33, 105, 255))
    d = ImageDraw.Draw(im)
    W_, R = (255, 255, 255, 255), (200, 16, 46, 255)
    d.line([(0, 0), (w, h)], fill=W_, width=60)
    d.line([(0, h), (w, 0)], fill=W_, width=60)
    # counterchanged red saltire (offset diagonals)
    d.line([(0, -10), (w / 2, h / 2 - 10)], fill=R, width=20)
    d.line([(w / 2, h / 2 + 10), (w, h + 10)], fill=R, width=20)
    d.line([(0, h + 10), (w / 2, h / 2 + 10)], fill=R, width=20)
    d.line([(w / 2, h / 2 - 10), (w, -10)], fill=R, width=20)
    d.rectangle([w / 2 - 50, 0, w / 2 + 50, h], fill=W_)
    d.rectangle([0, h / 2 - 50, w, h / 2 + 50], fill=W_)
    d.rectangle([w / 2 - 30, 0, w / 2 + 30, h], fill=R)
    d.rectangle([0, h / 2 - 30, w, h / 2 + 30], fill=R)
    return im


# ---------------------------------------------------------------------------
# Airline artwork
# ---------------------------------------------------------------------------
MAPLE = [(0, -1.0), (0.09, -0.80), (0.25, -0.88), (0.21, -0.55), (0.40, -0.70), (0.43, -0.62),
         (0.63, -0.66), (0.55, -0.45), (0.60, -0.42), (0.44, -0.27), (0.48, -0.17),
         (0.06, -0.21), (0.08, 0.20), (0.02, 0.20), (0.02, 0.40), (-0.02, 0.40), (-0.02, 0.20),
         (-0.08, 0.20), (-0.06, -0.21), (-0.48, -0.17), (-0.44, -0.27), (-0.60, -0.42),
         (-0.55, -0.45), (-0.63, -0.66), (-0.43, -0.62), (-0.40, -0.70), (-0.21, -0.55),
         (-0.25, -0.88), (-0.09, -0.80)]


def _leaf(d, cx, cy, size, fill):
    d.polygon([(cx + x * size, cy + y * size) for x, y in MAPLE], fill=fill)


def tex_ac_rondelle():
    """Air Canada 2017 rondelle: red ring with a red maple leaf, on clear."""
    n = 400
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    red = (214, 24, 42, 255)
    d.ellipse([20, 20, n - 20, n - 20], outline=red, width=34)
    _leaf(d, n / 2, n / 2 + 40, 175, red)
    return im


def tex_alaska_face():
    """Alaska Airlines tail: the smiling Inuk face framed by a white fur
    parka ruff (simplified), on clear (the fin itself is navy)."""
    w, h = 300, 400
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fur = (240, 240, 236, 255)
    for k in range(36):                                   # fur ruff, tufted edge
        a = k / 36 * 2 * np.pi
        x, y = 150 + 128 * np.cos(a), 205 + 168 * np.sin(a)
        d.ellipse([x - 26, y - 26, x + 26, y + 26], fill=fur)
    d.ellipse([28, 42, 272, 368], fill=fur)
    d.ellipse([70, 100, 230, 320], fill=(1, 42, 92, 255))  # dark hood interior
    d.ellipse([88, 128, 212, 304], fill=(208, 150, 112, 255))  # face
    d.arc([106, 160, 146, 190], 200, 340, fill=(40, 30, 30, 255), width=7)   # smiling eyes
    d.arc([154, 160, 194, 190], 200, 340, fill=(40, 30, 30, 255), width=7)
    d.polygon([(146, 190), (154, 190), (158, 226), (142, 226)], fill=(176, 118, 86, 255))
    d.arc([118, 222, 182, 272], 20, 160, fill=(150, 40, 40, 255), width=8)   # smile
    d.ellipse([92, 214, 118, 236], fill=(220, 120, 110, 255))                 # cheeks
    d.ellipse([182, 214, 208, 236], fill=(220, 120, 110, 255))
    return im


def tex_emblems():
    """Vancouver 2010 'Ilanaaq' inukshuk and Paralympic emblem, side by side."""
    w, h = 300, 220
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # inukshuk: blocks in green / blue / red / yellow
    d.rectangle([40, 150, 62, 200], fill=(0, 150, 90, 255))
    d.rectangle([88, 150, 110, 200], fill=(0, 110, 190, 255))
    d.rectangle([30, 118, 120, 146], fill=(0, 110, 190, 255))
    d.rectangle([48, 76, 102, 114], fill=(0, 150, 90, 255))
    d.rectangle([20, 50, 130, 72], fill=(220, 40, 40, 255))
    d.ellipse([58, 12, 92, 46], fill=(250, 190, 20, 255))
    # paralympic emblem: blue swoop figure over green hills
    d.rectangle([180, 40, 270, 200], fill=(240, 244, 250, 255))
    d.polygon([(190, 180), (230, 130), (262, 180)], fill=(0, 150, 90, 255))
    d.ellipse([210, 60, 244, 94], fill=(0, 110, 190, 255))
    d.polygon([(200, 140), (226, 96), (250, 104), (230, 150)], fill=(0, 110, 190, 255))
    return im


# ---------------------------------------------------------------------------
# Pirate Pak side art (current White Spot design, cf. photos). The canvas
# spans the whole hull side, stern on the left, from the waterline (bottom)
# to the tip of the prow (top). The wall top follows the hull sheer.
# ---------------------------------------------------------------------------
PW, PH = 1000, 400


def _u(x):
    return x / PW * pirate.L - pirate.L / 2


def _wall_top(x):
    return PH * (1 - float(pirate.profile(_u(x))) / pirate.H_TIP)


def _x(u):
    return (u + pirate.L / 2) / pirate.L * PW


def tex_pirate():
    im = Image.new("RGBA", (PW, PH), (200, 66, 40, 255))
    d = ImageDraw.Draw(im)
    wall = PH * pirate.H_WELL / pirate.H_TIP           # well wall height in px
    y = lambda f: PH - wall * f                       # noqa: E731  (0 = waterline)
    # planks
    for f in np.arange(0.24, 0.8, 0.07):
        d.line([(0, y(f)), (PW, y(f))], fill=(160, 44, 30, 255), width=3)
    for x in range(0, PW, 90):
        d.line([(x, y(0.24)), (x, y(0.78))], fill=(170, 50, 34, 255), width=2)
    # bow: rising prow painted in the wave / yellow scheme
    d.polygon([(_x(pirate.CURVE_START) - 40, PH), (PW, _wall_top(PW - 1) + 30), (PW, PH)],
              fill=(40, 120, 200, 255))
    for i in range(6):
        cx, cy = PW * (0.84 + i * 0.03), PH * (0.25 + i * 0.1)
        d.arc([cx - 40, cy - 30, cx + 40, cy + 30], 180, 360, fill=(255, 255, 255, 255), width=8)
    # rail zone along the well, stripe below it
    x0, x1 = _x(pirate.STERN_END), _x(pirate.PROW_START)
    d.rectangle([x0, y(0.93), x1, y(0.80)], fill=(150, 40, 28, 255))
    for x in range(int(x0) + 8, int(x1), 26):
        d.rectangle([x, y(0.92), x + 9, y(0.81)], fill=(250, 196, 40, 255))
    d.rectangle([0, y(0.80), _x(pirate.CURVE_START), y(0.77)], fill=(250, 196, 40, 255))
    # stern windows (arched, blue panes)
    for x in (150, 215):
        d.rectangle([x, y(0.72), x + 44, y(0.45)], fill=(250, 196, 40, 255))
        d.rectangle([x + 7, y(0.68), x + 37, y(0.49)], fill=(70, 150, 220, 255))
    # cannon ports and portholes
    for i, x in enumerate(range(300, 760, 78)):
        if i % 3 == 1:
            d.ellipse([x, y(0.70), x + 52, y(0.44)], fill=(250, 196, 40, 255))
            d.ellipse([x + 9, y(0.66), x + 43, y(0.48)], fill=(60, 140, 214, 255))
        else:
            d.rectangle([x, y(0.70), x + 52, y(0.44)], fill=(120, 30, 20, 255))
            d.rectangle([x, y(0.74), x + 52, y(0.70)], fill=(250, 196, 40, 255))
            d.ellipse([x + 12, y(0.64), x + 40, y(0.50)], fill=(30, 30, 34, 255))
            d.ellipse([x + 19, y(0.61), x + 33, y(0.53)], fill=(90, 90, 96, 255))
    # crests
    for x in (560, 800):
        d.polygon([(x, y(0.78)), (x + 44, y(0.78)), (x + 44, y(0.55)), (x + 22, y(0.44)),
                   (x, y(0.55))], fill=(40, 90, 190, 255))
        d.rectangle([x + 16, y(0.76), x + 28, y(0.52)], fill=(250, 196, 40, 255))
    # lower yellow stripe and blue waves along the waterline
    d.rectangle([0, y(0.27), PW, y(0.23)], fill=(250, 196, 40, 255))
    d.rectangle([0, y(0.23), PW, PH], fill=(40, 120, 200, 255))
    for x in range(-40, PW, 70):
        d.arc([x, y(0.21), x + 80, y(0.02)], 190, 330, fill=(255, 255, 255, 255), width=7)
    # the pink octopus at the stern
    d.ellipse([24, y(0.84), 124, y(0.42)], fill=(240, 120, 150, 255))
    for ex in (52, 84):
        d.ellipse([ex, y(0.72), ex + 18, y(0.62)], fill=(255, 255, 255, 255))
        d.ellipse([ex + 5, y(0.70), ex + 13, y(0.64)], fill=(20, 20, 20, 255))
    for i in range(5):
        x0 = 20 + i * 28
        d.arc([x0, y(0.50), x0 + 60, y(0.12)], 60, 250, fill=(240, 120, 150, 255), width=12)
    # White Spot badge
    d.rounded_rectangle([140, y(0.21), 250, y(0.06)], radius=12, fill=(255, 255, 255, 255))
    d.rectangle([152, y(0.16), 238, y(0.11)], fill=(200, 30, 40, 255))
    # big bolted porthole discs on the raised end sections
    for u in (-6.2, -4.6, 3.1):
        cx, cy = _x(u), (_wall_top(_x(u)) + y(0.80)) / 2 + 4
        r = (y(0.80) - _wall_top(_x(u))) * 0.36
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(150, 150, 200, 255))
        d.ellipse([cx - r * 0.7, cy - r * 0.7, cx + r * 0.7, cy + r * 0.7], fill=(186, 190, 230, 255))
        d.regular_polygon((cx, cy, r * 0.3), 6, fill=(120, 120, 170, 255))
    # yellow trim along the (stepped) top edge, then cut away above it
    a = np.array(im)
    for x in range(PW):
        t = int(_wall_top(x))
        a[t:t + 14, x, :3] = (250, 196, 40)
        a[t + 14:t + 17, x, :3] = (120, 60, 30)
        a[:max(0, t), x, 3] = 0
    # vertical trim at the steps up to the end decks
    for u in (pirate.STERN_END, pirate.PROW_START):
        xs = int(_x(u))
        a[int(_wall_top(xs + (4 if u > 0 else -4))):int(y(0.77)), xs - 7:xs + 7, :3] = (250, 196, 40)
    return Image.fromarray(a)


def logo_panel():
    """Just the wave icon, for the navy logo panels on Salish/Island class."""
    return wave_icon(300, 220)


def text_mask(txt, font_name, size=120, pad=8, index=0):
    if font_name.endswith(".ttc") and not os.path.exists(os.path.join(FONTS, font_name)):
        f = ImageFont.truetype("/System/Library/Fonts/" + font_name, size, index=index)
    else:
        f = ImageFont.truetype(os.path.join(FONTS, font_name), size, index=index)
    w = int(f.getlength(txt)) + pad * 2
    im = Image.new("L", (w, int(size * 1.25)), 0)
    ImageDraw.Draw(im).text((pad, int(size * 1.0)), txt, font=f, fill=255, anchor="ls")
    a = np.array(im) > 127
    rows = np.nonzero(a.any(1))[0]
    return a[max(rows[0] - pad, 0):rows[-1] + pad]


LOGOS = os.path.join(HERE, "logos")


def _logo(key, x0=None, x1=None):
    """Official logo (common/logos, from fetch_logos.py) as RGBA, optionally
    cut to columns [x0, x1) and trimmed."""
    im = Image.open(os.path.join(LOGOS, key + ".png")).convert("RGBA")
    if x0 is not None or x1 is not None:
        im = im.crop((x0 or 0, 0, x1 or im.width, im.height))
    return im.crop(im.getbbox())


def _logo_rows(key, y0, y1):
    im = Image.open(os.path.join(LOGOS, key + ".png")).convert("RGBA")
    im = im.crop((0, y0, im.width, y1))
    return im.crop(im.getbbox())


def _mask(im, pad_h=0.0):
    """Alpha of a logo as a white-on-black mask (optionally padded top and
    bottom by pad_h of the height, e.g. to sit the wave icon on a stack)."""
    a = np.array(im)[..., 3] > 127
    if pad_h:
        p = int(a.shape[0] * pad_h)
        a = np.pad(a, ((p, p), (int(p * 0.3), int(p * 0.3))))
    return a


def main():
    os.makedirs(OUT, exist_ok=True)
    decals = {
        "wordmark": _mask(_logo("bcferries")),
        "bcf_icon": _mask(_logo("bcferries", 0, 362)),
        "stack_logo": _mask(_logo("bcferries", 0, 362), pad_h=0.35),
        "stack_grille": stack_grille(),
        "logo_panel": _mask(_logo("bcferries", 0, 362), pad_h=0.15),
        "vancouver2010": _mask(_logo_rows("vancouver2010", 1228, 1345)),
        "britishcolumbia": text_mask("British Columbia", "Avenir Next.ttc", index=5),
        "departures": text_mask("DEPARTURES", "Avenir Next.ttc", index=0),
        "arrivals": text_mask("ARRIVALS", "Avenir Next.ttc", index=0),
        "landsend": text_mask("LANDS END café", "Georgia.ttf"),
        "otterbay": text_mask("Otter Bay · Pender Island", "Avenir Next.ttc", index=0),
        "ac_title": _mask(_logo("aircanada", 0, 1700)),
        "ac_express": _mask(_logo("aircanada_express", 450)),
        "alaska": _mask(_logo("alaska")),
        "horizon": _mask(_logo("horizon", 0, 1905)),
        "westjet": _mask(_logo("westjet", 0, 1580)),
        "thestand": text_mask("THE STAND", "Georgia Bold.ttf"),
        "publicmarket": text_mask("PUBLIC MARKET", "Arial Black.ttf"),
        "fishchips": text_mask("FISH & CHIPS", "Arial Black.ttf"),
    }
    names = {
        "spirit": "Spirit of British Columbia", "coastal": "Coastal Renaissance",
        "cclass": "Queen of Coquitlam", "cclass_ob": "Queen of Oak Bay",
        "salish": "Salish Orca", "island": "Island Discovery",
        "nexpedition": "Northern Expedition", "nadventure": "Northern Adventure",
        "burnaby": "Queen of Burnaby", "vclass_s": "Queen of Vancouver",
        "rupert": "Queen of Prince Rupert", "intermediate": "Queen of Capilano",
        "bowen": "Bowen Queen", "century": "Skeena Queen", "quinsam": "Quinsam",
        "quinitsa": "Quinitsa", "tclass": "Tachek", "nimpkish": "Nimpkish",
        "coho": "COHO", "vclass": "Queen of Victoria", "sidney": "Sidney",
        "north": "Queen of the North", "pacificat": "PacifiCat Explorer",
        "spirit_vi": "Spirit of Vancouver Island", "coastal_insp": "Coastal Inspiration",
        "coastal_cel": "Coastal Celebration", "cclass_cow": "Queen of Cowichan",
        "cclass_alb": "Queen of Alberni", "cclass_sur": "Queen of Surrey",
        "salish_eagle": "Salish Eagle", "salish_raven": "Salish Raven",
        "salish_heron": "Salish Heron",
        "clipper5": "VICTORIA CLIPPER V", "clipper4": "VICTORIA CLIPPER IV",
        "burnaby_nan": "Queen of Nanaimo", "burnaby_nw": "Queen of New Westminster",
        "intermediate_cum": "Queen of Cumberland", "vclass_s_vic": "Queen of Victoria",
    }
    for k, n in names.items():
        fnt = "Arial Bold.ttf" if k in ("coho", "clipper5", "clipper4") else "Georgia Italic.ttf"
        decals["name_" + k] = text_mask(n, fnt)
    textures = {"tex_alpine": tex_alpine(), "tex_sitski": tex_sitski(),
                "tex_vineyard": tex_vineyard(), "tex_skaters": tex_skaters(),
                "tex_emblems": tex_emblems(), "tex_hockey": tex_hockey(),
                "tex_coast": tex_coast(), "tex_rainforest": tex_rainforest(),
                "tex_hockeyplayer": tex_hockeyplayer(), "tex_snowboard": tex_snowboard(),
                "tex_orca": tex_orca(), "tex_aerials": tex_aerials(),
                "tex_mountains": tex_mountains(),
                "tex_salish_wave": tex_salish_wave(), "tex_union_jack": tex_union_jack(),
                "tex_ac_rondelle": _logo("aircanada", 1700), "tex_alaska_face": tex_alaska_face(),
                "tex_ac_express_rondelle": _logo("aircanada_express", 0, 450),
                "tex_wj_leaf": _logo("westjet", 1585),
                "tex_vancouver2010": _logo("vancouver2010")}
    for k, f in (("eagle", tex_salish_eagle), ("raven", tex_salish_raven),
                 ("orca", tex_salish_orca), ("heron", tex_salish_heron)):
        im = f()
        textures["tex_salish_" + k] = im
        textures["tex_salish_" + k + "_m"] = im.transpose(Image.FLIP_LEFT_RIGHT)
    textures["tex_pirate"] = tex_pirate()
    textures["tex_pirate_m"] = textures["tex_pirate"].transpose(Image.FLIP_LEFT_RIGHT)
    for k, im in textures.items():
        im.save(os.path.join(OUT, k + ".png"))
        print(k, im.size)
    for k, a in decals.items():
        Image.fromarray((a * 255).astype(np.uint8)).save(os.path.join(OUT, k + ".png"))
        print(k, a.shape)


if __name__ == "__main__":
    main()
