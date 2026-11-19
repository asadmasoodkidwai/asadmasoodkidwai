# -*- coding: utf-8 -*-
"""fx.py -- drawing toolkit for the neon / blood profile panels.

A Canvas holds two static layers:
  txt  : glyph pixels (white, never stained)
  line : OUTLINES only (brackets, rules, chip borders, icons, ECG)  <- blood lives here
and a list of "elements" (bounding boxes) that the engine reveals with a heartbeat sweep.
"""
import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
D = "/usr/share/fonts/truetype/dejavu/"
_C = {
    "mono": ["mono.ttf", D + "DejaVuSansMono.ttf", "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
             "C:/Windows/Fonts/consola.ttf", "/System/Library/Fonts/Menlo.ttc"],
    "mono_b": ["mono_b.ttf", D + "DejaVuSansMono-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf",
               "C:/Windows/Fonts/consolab.ttf", "/System/Library/Fonts/Menlo.ttc"],
    "mono_i": ["mono_i.ttf", D + "DejaVuSansMono-Oblique.ttf", "/usr/share/fonts/dejavu/DejaVuSansMono-Oblique.ttf",
               "C:/Windows/Fonts/consolai.ttf", "/System/Library/Fonts/Menlo.ttc"],
    "math": ["math.ttf", D + "DejaVuSerif-Italic.ttf", "/usr/share/fonts/dejavu/DejaVuSerif-Italic.ttf",
             "C:/Windows/Fonts/timesi.ttf"],
}
PATH = {k: next((p for p in ([os.path.join(HERE, v[0])] + v[1:]) if os.path.exists(p)), None) for k, v in _C.items()}
_fc = {}
GLYPHS = ["∫", "∂", "∇", "λ", "Σ", "∞", "π", "θ", "Ω", "Δ", "∀", "∃", "≈", "√", "μ", "σ²", "ε", "⊗", "∈", "⇒",
          "lim", "dx", "P(A|B)", "E[X]", "∇²f", "det(A)", "Var(X)", "f(x)=x²"]


def F(kind, size):
    key = (kind, int(size))
    if key not in _fc:
        p = PATH[kind]
        _fc[key] = ImageFont.truetype(p, int(size)) if p else ImageFont.load_default(int(size))
    return _fc[key]


def tw(f, t, tr=0):
    return f.getlength(t) if not tr else sum(f.getlength(c) for c in t) + tr * max(len(t) - 1, 0)


def wrap(t, f, maxw):
    out, cur = [], ""
    for w in t.split():
        trial = (cur + " " + w).strip()
        if f.getlength(trial) <= maxw:
            cur = trial
        else:
            out.append(cur)
            cur = w
    return out + ([cur] if cur else [])


def hit(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def glyph_mask(ch, size):
    f = F("math", size)
    im = Image.new("L", (int(f.getlength(ch)) + 24, int(size * 1.6) + 16), 0)
    ImageDraw.Draw(im).text((12, 8), ch, font=f, fill=255)
    return im.crop(im.getbbox())


def _outline(fn, S=170, thick=5):
    a = Image.new("L", (S, S), 0)
    fn(ImageDraw.Draw(a))
    return ImageChops.subtract(a, a.filter(ImageFilter.MinFilter(thick)))


def make_icon(name):
    import math
    S, c = 170, 85
    if name == "cloud":
        def sil(d):
            d.ellipse([22, 58, 70, 106], fill=255); d.ellipse([46, 34, 112, 100], fill=255)
            d.ellipse([86, 50, 138, 102], fill=255); d.rounded_rectangle([40, 70, 120, 106], radius=18, fill=255)
        ic = _outline(sil)
        d = ImageDraw.Draw(ic)
        for x in (52, 80, 108):
            d.line([(x, 118), (x - 10, 146)], fill=255, width=4)
        return ic
    if name == "knight":
        def sil(d):
            d.polygon([(46, 142), (46, 126), (62, 104), (60, 84), (42, 78), (38, 62), (66, 32), (78, 20), (86, 38),
                       (102, 40), (122, 64), (124, 102), (112, 126), (122, 142)], fill=255)
        ic = _outline(sil)
        ImageDraw.Draw(ic).ellipse([76, 52, 86, 62], fill=255)
        return ic
    ic = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(ic)
    if name == "cube":
        pts = [(c + 64 * math.cos(math.radians(60 * i - 90)), c + 64 * math.sin(math.radians(60 * i - 90))) for i in range(6)]
        d.polygon(pts, outline=255, width=4)
        for i in (1, 3, 5):
            d.line([(c, c), pts[i]], fill=255, width=3)
    elif name == "coin":
        d.ellipse([c - 66, c - 66, c + 66, c + 66], outline=255, width=5)
        d.ellipse([c - 48, c - 48, c + 48, c + 48], outline=255, width=2)
        d.arc([c - 26, c - 26, c + 26, c + 26], 40, 320, fill=255, width=5)
        d.line([(c, c - 38), (c, c + 38)], fill=255, width=3)
    return ic


class Canvas:
    def __init__(s, w, h):
        s.w, s.h = w, h
        s.txt = Image.new("L", (w, h), 0)
        s.line = Image.new("L", (w, h), 0)
        s.dt, s.dl = ImageDraw.Draw(s.txt), ImageDraw.Draw(s.line)
        s.els = []

    # -- registration --------------------------------------------------------
    def add(s, box, kind="body"):
        x0, y0, x1, y1 = box
        s.els.append(dict(box=(max(0, int(x0)), max(0, int(y0)), min(s.w, int(x1) + 1), min(s.h, int(y1) + 1)), kind=kind))

    # -- primitives ----------------------------------------------------------
    def text(s, x, y, t, kind, size, fill=255, tr=0, anchor="l", reg=True, ek="body"):
        f = F(kind, size)
        w = tw(f, t, tr)
        x = x - w / 2 if anchor == "c" else (x - w if anchor == "r" else x)
        if tr:
            cx = x
            for ch in t:
                s.dt.text((cx, y), ch, font=f, fill=fill)
                cx += f.getlength(ch) + tr
        else:
            s.dt.text((x, y), t, font=f, fill=fill)
        if reg:
            s.add((x - 4, y, x + w + 4, y + size * 1.28), ek)
        return x, w

    def para(s, x, y, t, kind, size, fill, maxw, lh, bullet=None):
        f = F(kind, size)
        ind = f.getlength(bullet + " ") if bullet else 0
        for i, ln in enumerate(wrap(t, f, maxw - ind)):
            if bullet and i == 0:
                s.text(x, y, bullet, "mono_b", size, 255, reg=False)
            s.text(x + ind, y, ln, kind, size, fill)
            y += lh
        return y

    def header(s, x, y, w, label, size=24):
        h = int(size * 1.3)
        s.dl.line([(x + 9, y), (x, y), (x, y + h), (x + 9, y + h)], fill=255, width=2)
        x0, t = s.text(x + size + 8, y + 3, label, "mono_b", size, 255, tr=4, reg=False)
        s.dl.line([(x0 + t + 18, y + h // 2), (x + w, y + h // 2)], fill=255, width=2)
        s.add((x - 2, y - 2, x + w + 2, y + h + 2), "head")
        return y + h

    def chips(s, x, y, items, size, maxx, pad=(14, 7), gap=10):
        f = F("mono_b", size)
        rh = size * 1.28 + 2 * pad[1]
        cx, cy = x, y
        for t in items:
            w = tw(f, t, 2) + 2 * pad[0]
            if cx + w > maxx and cx > x:
                cx, cy = x, cy + rh + gap
            s.dl.rounded_rectangle([cx, cy, cx + w, cy + rh], radius=9, outline=255, width=2)
            s.text(cx + pad[0], cy + pad[1] - 1, t, "mono_b", size, 255, tr=2, reg=False)
            s.add((cx - 1, cy - 1, cx + w + 1, cy + rh + 1), "chip")
            cx += w + gap
        return cy + rh

    def vline(s, x, y0, y1):
        s.dl.line([(x, y0), (x, y1)], fill=255, width=2)
        s.add((x - 3, y0, x + 3, y1), "rule")

    def hline(s, x0, x1, y):
        s.dl.line([(x0, y), (x1, y)], fill=255, width=2)
        s.add((x0, y - 3, x1, y + 3), "rule")

    def icon(s, name, cx, cy, size=104):
        ic = make_icon(name)
        ic = ic.resize((size, size), Image.LANCZOS)
        x, y = int(cx - size / 2), int(cy - size / 2)
        s.line.paste(ImageChops.lighter(s.line.crop((x, y, x + size, y + size)), ic), (x, y))
        s.add((x, y, x + size, y + size), "icon")

    # -- finish: float layers, load order, blood -------------------------------
    def finish(s, seed):
        s.els.sort(key=lambda e: (e["box"][1] // 14, e["box"][0]))
        s.txt_f = np.asarray(s.txt, np.float32) / 255
        s.line_f = np.asarray(s.line, np.float32) / 255
        rs, r = np.random.RandomState(seed), random.Random(seed)
        g = (rs.rand(s.h // 18 + 3, s.w // 18 + 3) * 255).astype(np.uint8)
        nz = np.asarray(Image.fromarray(g).resize((s.w, s.h), Image.BICUBIC), np.float32) / 255
        s.stain = (np.clip((nz - 0.70) / 0.06, 0, 1) * (s.line_f > 0.05)).astype(np.float32)
        L = s.line_f > 0.5
        b1 = np.zeros_like(L); b1[:-1] = L[1:]
        b2 = np.zeros_like(L); b2[:-2] = L[2:]
        cand = np.argwhere(L & ~b1 & ~b2 & (s.stain > 0.45))
        idx = list(range(len(cand)))
        r.shuffle(idx)
        s.drips, taken = [], []
        for k in idx:
            y, x = int(cand[k][0]), int(cand[k][1])
            if any(abs(x - tx) < 44 and abs(y - ty) < 24 for tx, ty in taken):
                continue
            ln = min(r.randint(12, 56), s.h - y - 8)
            if ln < 9:
                continue
            col = np.maximum(s.txt_f[y + 1:y + 1 + ln, x], s.line_f[y + 4:y + 4 + ln, x][:ln] if y + 4 + ln <= s.h else 0)
            stop = np.argwhere(np.atleast_1d(col) > 0.1)
            if len(stop):
                ln = int(stop[0][0]) - 3
            ei = next((i for i, e in enumerate(s.els) if e["box"][0] <= x <= e["box"][2] and e["box"][1] - 2 <= y <= e["box"][3] + 2), None)
            if ln < 9 or ei is None:
                continue
            if s.els[ei]["kind"] == "chip" and y < s.els[ei]["box"][3] - 5:
                continue                      # chips only bleed from their bottom border, never across the label
            taken.append((x, y))
            s.drips.append(dict(x=x, y=y, len=ln, w=r.choice([2, 3, 3]), el=ei))
            if len(taken) >= s.w // 62:
                break
        return s

    def flyers(s, n, seed, size=(34, 92)):
        r = random.Random(seed)
        boxes = [(e["box"][0] - 22, e["box"][1] - 14, e["box"][2] + 22, e["box"][3] + 14) for e in s.els]
        R = max(s.w, s.h) * 0.75 + 140
        out, placed = [], []
        for _ in range(n * 40):
            if len(out) >= n:
                break
            ch = r.choice(GLYPHS)
            sz = r.randint(*size) if len(ch) <= 2 else r.randint(22, 38)
            m = glyph_mask(ch, sz)
            x, y = r.uniform(10, s.w - m.width - 10), r.uniform(6, max(7, s.h - m.height - 6))
            bx = (x - 12, y - 10, x + m.width + 12, y + m.height + 10)
            if any(hit(bx, b) for b in boxes + placed):
                continue
            placed.append(bx)
            a, b = r.uniform(0, 6.283), r.uniform(0, 6.283)
            out.append(dict(ch=ch, size=sz, cx=x + m.width / 2, cy=y + m.height / 2,
                            din=(np.cos(a), np.sin(a)), dout=(np.cos(b), np.sin(b)), R=R,
                            rin=r.uniform(-340, 340), rout=r.uniform(-240, 240),
                            bright=r.uniform(0.40, 0.95), delay=r.uniform(0, 1.0), dur=r.uniform(0.9, 1.4),
                            xdelay=r.uniform(0, 0.25)))
        return out
