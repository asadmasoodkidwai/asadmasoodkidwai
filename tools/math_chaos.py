#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
math_chaos.py  --  "A living mathematical system. Controlled chaos with a heartbeat."

Generates a seamlessly looping 1200x360 black-and-white GIF for a GitHub profile
README using only Python + Pillow + NumPy.

Run:      python math_chaos.py
Options:  python math_chaos.py --out my.gif --duration 9 --fps 20 --levels 16 --preview

HOW THE LOOP IS MADE SEAMLESS
  * Every element is a pure function of time t in [0, T) and is periodic in T.
  * The heartbeat is a monitor-style sweep: the trace is drawn at a fixed x for
    each beat and a bright "head" sweeps across once per loop (wrapping).
  * Symbol motion is driven by a warped clock tau(t) (so the heartbeat can speed
    up / freeze time) that is normalised so tau(T) == T. Each symbol's path is a
    closed route on a wrapped torus, so after T seconds it is exactly back home.
  * Headings / interruptions are scheduled so nothing is on screen at t = 0 / T.
"""
import argparse
import bisect
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

# =============================================================================
# CONFIG  (all times below are in seconds for a REF_DURATION-second loop; if you
# change DURATION the whole timeline is stretched/compressed automatically)
# =============================================================================
W, H = 1200, 360
FPS = 20
DURATION = 10.0
REF_DURATION = 10.0
SEED = 7
GREY_LEVELS = 16            # palette size (greys). Lower = smaller file.
OUTPUT = "math_chaos.gif"

N_SYMBOLS = 62              # total moving symbols (incl. large ghost glyphs)
N_GHOSTS = 6                # huge, very dim background glyphs
N_DUST = 170                # tiny "mathematical dust" particles
MARGIN = 120                # off-screen margin symbols travel through before wrapping
LINE_MAX = 7                # max thin connecting lines at any moment
LINE_DIST = 190             # max distance (px) for two symbols to be connected

# --- heartbeat ---------------------------------------------------------------
ECG_BASE_Y = 300            # baseline of the ECG trace
ECG_AMP = 78                # height (px) of the big "lub" spike
# (beat time, spike-size multiplier, how strongly nearby symbols react)
BEATS = [
    (0.75, 1.00, 0.6), (1.75, 1.00, 1.0), (2.75, 1.00, 0.6),
    (3.70, 1.00, 1.0),                                   # --- rhythm speeds up ---
    (4.40, 1.00, 0.6), (4.95, 1.00, 1.0), (5.45, 1.00, 0.6),
    (5.90, 1.00, 1.0), (6.40, 1.00, 0.6), (6.95, 1.00, 1.0),
    (8.20, 1.35, 2.0),                                   # sharp beat after the freeze
    (9.00, 1.00, 0.6), (9.85, 1.00, 1.0),                # gradually back to ~1 Hz
]
FRANTIC = (3.70, 6.95)      # symbols move faster during this window
FREEZE = (7.05, 8.20)       # the near-freeze; it ends ON the sharp beat

# --- headings: (text, start, duration, centre-x fraction, centre-y px,
#                drift-x px/s, drift-y px/s, style)
HEADINGS = [
    ("THINKING IN PROGRESS",               0.75, 1.55, 0.20,  62,  10,  0, "flicker"),
    ("ASSUMPTIONS UNDER REVIEW",           1.75, 1.25, 0.76, 118, -12,  2, "fade"),
    ("INTUITION IS NOT A PROOF",           2.45, 0.30, 0.42, 160,   0,  0, "blink"),
    ("THE SEARCH CONTINUES",               4.00, 1.10, 0.72,  58,   9,  0, "flicker"),
    ("UNFINISHED BUSINESS",                4.40, 0.35, 0.17, 142,   0,  0, "blink"),
    ("CURRENTLY DEBUGGING REALITY",        4.85, 0.55, 0.38,  98,  -8,  0, "fade"),
    ("NO CLOSED-FORM SOLUTION FOUND",      6.10, 0.85, 0.60,  72,  10,  0, "flicker"),
    ("SOMEWHERE BETWEEN ORDER AND CHAOS",  9.00, 0.60, 0.33,  64,   8,  0, "fade"),
    ("QUESTION EVERYTHING. INCLUDING THIS.", 9.15, 0.57, 0.68, 130,  -8,  0, "flicker"),
]

# --- interruptions: (text, start, duration, width as fraction of W, cx frac, cy px)
INTERRUPTIONS = [
    ("ERROR: INTUITION OVERFLOW",        3.25, 0.65, 0.70, 0.40, 150),
    ("CONVERGENCE NOT GUARANTEED",       5.40, 0.65, 0.90, 0.50, 125),
    ("NO SIGNAL. STILL THINKING.",       7.20, 0.95, 0.52, 0.50, 140),
    ("SYSTEM ALIVE",                     8.20, 0.65, 0.92, 0.50, 112),
]
# Spare interruptions you can swap in above:
#   "PROOF PENDING", "∀ QUESTIONS, ∃ MORE QUESTIONS", "THEOREM NOT FOUND",
#   "THINKING...", "Q.E.D. (QUESTIONABLY ESTABLISHED)", "PULSE DETECTED",
#   "COGNITIVE ACTIVITY DETECTED"

# --- moving symbols ----------------------------------------------------------
SYMBOLS = [
    "∫", "∂", "∇", "lim", "dx", "d/dx",                      # calculus
    "λ", "Σ", "det(A)", "⊗", "⟨v,w⟩",                        # linear algebra
    "P(A|B)", "E[X]", "σ²", "μ", "Var(X)",                  # probability / stats
    "∀", "∃", "∈", "⊆", "⇒", "⇔",                            # logic / sets
    "∞", "≠", "≈", "√", "π", "θ", "Ω", "Δ",                  # general
]
EXPRESSIONS = ["f(x) = x²", "lim x→∞", "∑ᵢ xᵢ", "P(A|B)", "∇²f", "det(A) ≠ 0"]
EXTRAS = ["ℝ", "∮", "∴", "∝", "ε", "ζ", "∅", "⊕", "≡", "‖x‖", "n!", "ℂ", "δ", "∏"]
GHOST_GLYPHS = ["∫", "Σ", "∞", "∇", "λ", "π", "∂", "Ω"]

# tiny equations that flash up briefly
FLASH_EQUATIONS = [
    "eⁱπ + 1 = 0", "∇×B = μ₀J", "Σ 1/n² = π²/6", "x² + y² = r²", "a² + b² = c²",
    "∀ε>0 ∃δ>0", "n! ≈ √(2πn)(n/e)ⁿ", "∮ E·dl = −dΦ/dt", "∫ e^(−x²) dx = √π",
    "ζ(s) = Σ n⁻ˢ",
]
FLASH_TIMES = [0.55, 1.30, 2.05, 3.00, 3.95, 4.65, 5.25, 5.95, 6.70, 7.45, 8.45, 8.95, 9.40]

# faint grid windows, glitch events, symbol clusters (time, centre) -------------
GRID_WINDOWS = [(1.2, 3.0), (5.0, 6.7), (8.6, 9.9)]
GLITCHES = [(1.62, "shift"), (2.92, "shift"), (3.25, "big"), (4.55, "dash"),
            (5.40, "big"), (6.62, "dash"), (8.20, "big"), (8.30, "dash"), (9.35, "dash")]
CLUSTERS = [(1.9, (880, 178)), (5.0, (330, 182)), (7.9, (1010, 160))]

# =============================================================================
# FONTS  (nothing is downloaded; drop .ttf files in ./fonts to override)
# =============================================================================
HERE = os.path.dirname(os.path.abspath(__file__))
_D = "/usr/share/fonts/truetype/dejavu/"
_D2 = "/usr/share/fonts/dejavu/"
_WIN = "C:/Windows/Fonts/"
_MAC = "/System/Library/Fonts/Supplemental/"
STYLE_PATHS = {
    "head": [
        os.path.join(HERE, "fonts", "head.ttf"),
        _D + "DejaVuSansCondensed-Bold.ttf", _D2 + "DejaVuSansCondensed-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf",
        _WIN + "ARIALNB.TTF", _WIN + "arialnb.ttf", _MAC + "Arial Narrow Bold.ttf",
        _D + "DejaVuSans-Bold.ttf", _D2 + "DejaVuSans-Bold.ttf",
        _WIN + "arialbd.ttf", _MAC + "Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc",
    ],
    "serif": [
        os.path.join(HERE, "fonts", "serif.ttf"),
        _D + "DejaVuSerif.ttf", _D2 + "DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
        _WIN + "times.ttf", _MAC + "Times New Roman.ttf", _MAC + "STIXGeneral.otf",
    ],
    "serif_italic": [
        os.path.join(HERE, "fonts", "serif_italic.ttf"),
        _D + "DejaVuSerif-Italic.ttf", _D2 + "DejaVuSerif-Italic.ttf",
        _WIN + "timesi.ttf", _MAC + "Times New Roman Italic.ttf",
    ],
    "sans": [
        os.path.join(HERE, "fonts", "sans.ttf"),
        _D + "DejaVuSans.ttf", _D2 + "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansMath-Regular.ttf",
        _WIN + "seguisym.ttf", _WIN + "arial.ttf", _MAC + "Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ],
}
for _k in STYLE_PATHS:
    STYLE_PATHS[_k] = [p for p in STYLE_PATHS[_k] if os.path.exists(p)]

_font_cache = {}


def load_font(path, size):
    size = max(6, int(size))
    key = (path, size)
    if key not in _font_cache:
        if path:
            _font_cache[key] = ImageFont.truetype(path, size)
        else:  # last-resort built-in font (Pillow >= 10.1 scales it)
            try:
                _font_cache[key] = ImageFont.load_default(size)
            except TypeError:
                _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]


def _glyph_img(font, ch):
    im = Image.new("L", (96, 96), 0)
    ImageDraw.Draw(im).text((10, 10), ch, font=font, fill=255)
    return im


_glyph_cache = {}


def has_glyph(path, ch):
    """True if the font has a real glyph for ch (not the .notdef box)."""
    if ch.isspace():
        return True
    key = (path, ch)
    if key not in _glyph_cache:
        f = load_font(path, 48)
        diff = ImageChops.difference(_glyph_img(f, ch), _glyph_img(f, "\uFFFF"))
        _glyph_cache[key] = diff.getbbox() is not None
    return _glyph_cache[key]


def pick_font(text, style_order):
    """First font path (in preference order) that contains every char of text."""
    for style in style_order:
        for p in STYLE_PATHS.get(style, []):
            if all(has_glyph(p, c) for c in set(text)):
                return p
    return None


def text_mask(text, font, tracking=0.0):
    """Render text to a tightly cropped 'L' mask. tracking = extra px between letters."""
    asc, desc = font.getmetrics()
    if tracking == 0:
        total = int(font.getlength(text)) + 16
        im = Image.new("L", (total, asc + desc + 16), 0)
        ImageDraw.Draw(im).text((8, 8), text, font=font, fill=255)
    else:
        advs = [font.getlength(c) for c in text]
        total = int(sum(advs) + tracking * (len(text) - 1)) + 16
        im = Image.new("L", (total, asc + desc + 16), 0)
        d = ImageDraw.Draw(im)
        x = 8.0
        for c, a in zip(text, advs):
            d.text((x, 8), c, font=font, fill=255)
            x += a + tracking
    bb = im.getbbox()
    return im.crop(bb) if bb else im


# =============================================================================
# small helpers
# =============================================================================
def smoothstep(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def smoothstep_np(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def h01(a, b):
    """Deterministic hash -> [0,1). Used for per-frame flicker so the loop is repeatable."""
    x = (int(a) * 374761393 + int(b) * 668265263 + 144665) & 0xFFFFFFFF
    x = ((x ^ (x >> 13)) * 1274126177) & 0xFFFFFFFF
    x ^= x >> 16
    return (x & 0xFFFF) / 65535.0


# ECG waveform = sum of Gaussians around each beat: (offset s, sigma s, amplitude)
# Lub: P-Q-R-S-T.  Dub: a second, smaller R-S-T 0.34 s later.
ECG_COMPONENTS = [
    (-0.170, 0.035, 0.11),    # P
    (-0.028, 0.010, -0.14),   # Q
    (0.000, 0.013, 1.00),     # R  (lub)
    (0.030, 0.012, -0.30),    # S
    (0.170, 0.045, 0.20),     # T
    (0.340, 0.014, 0.60),     # R' (dub)
    (0.370, 0.012, -0.16),    # S'
    (0.500, 0.050, 0.15),     # T'
]
DUB_OFFSET = 0.34
SYM_SCALES = [1.0, 1.10, 1.22, 1.36]   # size levels used when a symbol "expands"


class Path:
    """Closed, piecewise-linear route. at(tau) -> displacement from the start."""

    def __init__(self, durs, disps):
        self.durs = durs
        self.disps = disps
        self.cum = [0.0]
        for d in durs:
            self.cum.append(self.cum[-1] + d)
        self.px = [0.0]
        self.py = [0.0]
        for dx, dy in disps:
            self.px.append(self.px[-1] + dx)
            self.py.append(self.py[-1] + dy)

    def at(self, tau):
        tau = min(max(tau, 0.0), self.cum[-1])
        i = min(bisect.bisect_right(self.cum, tau) - 1, len(self.durs) - 1)
        f = (tau - self.cum[i]) / self.durs[i]
        return (self.px[i] + self.disps[i][0] * f, self.py[i] + self.disps[i][1] * f)

    def max_speed(self):
        return max(math.hypot(dx, dy) / d for (dx, dy), d in zip(self.disps, self.durs))


class Sym:
    pass


# =============================================================================
# THE SCENE
# =============================================================================
class Scene:
    def __init__(self, duration=DURATION, fps=FPS, seed=SEED, levels=GREY_LEVELS):
        self.T = float(duration)
        self.fps = fps
        self.N = int(round(self.T * fps))
        self.k = self.T / REF_DURATION
        self.levels = levels
        self.DW = W + 2 * MARGIN
        self.DH = H + 2 * MARGIN
        self.rng = random.Random(seed)
        self.seed = seed
        self._build_beats()
        self._build_clock()
        self._build_ecg()
        self._build_text()
        self._build_symbols()
        self._build_dust()
        self._build_flashes()
        self._rot_cache = {}

    # ---------------------------------------------------------------- heartbeat
    def _build_beats(self):
        k, T = self.k, self.T
        raw = [(t * k, a, r) for t, a, r in BEATS]
        self.beats = []
        for i, (t, a, r) in enumerate(raw):
            nxt = raw[(i + 1) % len(raw)][0] + (T if i + 1 == len(raw) else 0.0)
            gap = nxt - t
            sc = min(1.0, max(0.5, gap / 0.95))
            self.beats.append(dict(t=t, amp=a, react=r, sc=sc))
        # ring events: lub + dub
        self.events = []
        for b in self.beats:
            strong = b["react"] >= 1.8
            vel = 1000.0 if strong else 520.0
            wid = 140.0 if strong else 85.0
            ox = (b["t"] / T) * W
            self.events.append(dict(t=b["t"], s=b["react"], v=vel, w=wid,
                                    ox=ox, oy=ECG_BASE_Y - 45))
            td = b["t"] + DUB_OFFSET * b["sc"]
            self.events.append(dict(t=td, s=b["react"] * 0.5, v=vel * 0.82, w=wid,
                                    ox=(td / T) * W, oy=ECG_BASE_Y - 45))

    def pulse(self, t):
        """Decaying envelope after each lub (used for subtle brightness kicks)."""
        p = 0.0
        for b in self.beats:
            for sh in (-self.T, 0.0, self.T):
                d = t - (b["t"] + sh)
                if 0 <= d < 1.0:
                    p += b["amp"] ** 0.5 * math.exp(-d / 0.14)
        return min(p, 1.6)

    def prominence(self, t):
        p = 0.0
        for b in self.beats:
            if b["react"] >= 1.0:
                for sh in (-self.T, 0.0, self.T):
                    d = t - (b["t"] + sh)
                    if 0 <= d < 2.0:
                        p += math.exp(-d / 0.6) * (b["react"] / 1.0) ** 0.5
        return min(p, 1.5)

    def _build_clock(self):
        """tau(t): warped clock. Speeds up when frantic, almost stops in the freeze,
        surges on beats, bursts after the sharp beat. Normalised so tau(T) == T."""
        k, T = self.k, self.T
        dt = 0.001
        tt = np.arange(0.0, T + dt, dt)
        pulse = np.zeros_like(tt)
        for b in self.beats:
            for sh in (-T, 0.0, T):
                d = tt - (b["t"] + sh)
                pulse += np.where(d >= 0, np.exp(-np.clip(d, 0, None) / 0.14), 0.0)
        fa, fb = FRANTIC[0] * k, FRANTIC[1] * k
        ramp = 0.3 * k
        frantic = smoothstep_np((tt - fa) / ramp) * smoothstep_np((fb - tt) / ramp)
        f0, f1 = FREEZE[0] * k, FREEZE[1] * k
        in_freeze = smoothstep_np((tt - f0) / (0.2 * k)) * (tt < f1)
        freeze_factor = 1.0 - 0.97 * in_freeze
        sharp = f1
        burst = np.where(tt >= sharp, 4.0 * np.exp(-np.clip(tt - sharp, 0, None) / (0.25 * k)), 0.0)
        speed = (1.0 + 0.75 * frantic + 0.9 * np.clip(pulse, 0, 1.5)) * freeze_factor + burst
        speed = np.maximum(speed, 0.03)
        cum = np.cumsum(speed) * dt
        cum = cum - cum[0]
        scale = T / cum[-1]
        ft = np.arange(self.N + 1) / self.fps
        self.tau = np.interp(ft, tt, cum) * scale

    def _build_ecg(self):
        T = self.T
        self.SS = 2
        n = W * self.SS
        ts = np.arange(n) / n * T
        val = np.zeros(n)
        for b in self.beats:
            sc = b["sc"]
            for sh in (-T, 0.0, T):
                u = ts - (b["t"] + sh)
                for mu, sg, A in ECG_COMPONENTS:
                    val += b["amp"] * A * np.exp(-0.5 * ((u - mu * sc) / (sg * max(sc, 0.75))) ** 2)
        wob = 0.9 * np.sin(2 * np.pi * 3 * ts / T) + 0.5 * np.sin(2 * np.pi * 11 * ts / T + 1.0)
        y = np.clip(ECG_BASE_Y - ECG_AMP * val + wob, 6, H - 4)
        self.ecg_y = y                       # at 2x horizontal resolution
        self.ecg_y0 = 160                    # top of the ECG layer (screen px)
        self.ecg_h = H - self.ecg_y0
        py = (y - self.ecg_y0) * self.SS
        px = np.arange(n, dtype=float)
        pts = np.stack([px, py], axis=1)
        CH = 10 * self.SS
        self.ecg_chunks = []
        for c in range(0, n, CH):
            seg = pts[c:min(c + CH + 1, n)]
            self.ecg_chunks.append((c / self.SS + 5.0, [tuple(p) for p in seg.tolist()]))

    # ------------------------------------------------------------------- text
    def _build_text(self):
        hp = pick_font("A", ["head"])
        self.head_path = hp
        self.headings = []
        for idx, (text, s, d, cxf, cy, vx, vy, style) in enumerate(HEADINGS):
            m = text_mask(text, load_font(hp, 34), tracking=3.0)
            self.headings.append(dict(text=text, start=s * self.k, dur=d * self.k, cx=cxf * W,
                                      cy=cy, vx=vx, vy=vy, style=style, mask=m,
                                      w=m.width, h=m.height, seed=101 + idx * 17))
        self.interrupts = []
        for idx, (text, s, d, wf, cxf, cy) in enumerate(INTERRUPTIONS):
            target = wf * W
            size = 100
            for _ in range(3):
                f = load_font(hp, size)
                m = text_mask(text, f, tracking=size * 0.04)
                size = max(20, int(size * target / m.width))
            f = load_font(hp, size)
            m = text_mask(text, f, tracking=size * 0.04)
            self.interrupts.append(dict(text=text, start=s * self.k, dur=d * self.k,
                                        cx=cxf * W, cy=cy, mask=m, w=m.width, h=m.height,
                                        seed=501 + idx * 29))

    def _heading_alpha(self, h, t, fi):
        s, d = h["start"], h["dur"]
        if t < s or t > s + d:
            return 0.0
        u = t - s
        n = h01(h["seed"], fi)
        style = h["style"]
        if style == "fade":
            fin, fout = 0.45 * self.k, 0.45 * self.k
            a = smoothstep(u / fin) * smoothstep((d - u) / fout)
            return a * (0.78 + 0.22 * math.sin(2 * math.pi * 1.9 * u + h["seed"]))
        short = style == "blink"
        fin = (0.10 if short else 0.32) * self.k
        fout = (0.10 if short else 0.28) * self.k
        if u < fin:
            p = u / fin
            return 1.0 if n < 0.15 + 0.8 * p else 0.0
        if u > d - fout:
            q = (d - u) / fout
            return q * (0.55 + 0.45 * n)
        return 0.3 if n < (0.02 if short else 0.07) else 1.0

    @staticmethod
    def _slice_mask(mask, seed, fi, amount):
        a = np.array(mask)
        y = 0
        j = 0
        while y < a.shape[0]:
            hgt = 4 + int(h01(seed + j, fi) * 12)
            dx = int((h01(seed + 77 + j, fi) - 0.5) * 2 * amount)
            if h01(seed + 33 + j, fi) < 0.55:
                a[y:y + hgt] = np.roll(a[y:y + hgt], dx, axis=1)
            y += hgt
            j += 1
        return Image.fromarray(a)

    def _text_state(self, t, fi):
        draws, boxes, takeover = [], [], 0.0
        pulse = self.pulse(t)
        for h in self.headings:
            a = self._heading_alpha(h, t, fi)
            if a <= 0.01:
                continue
            u = t - h["start"]
            x = h["cx"] + h["vx"] * (u - h["dur"] / 2) - h["w"] / 2
            y = h["cy"] + h["vy"] * (u - h["dur"] / 2) - h["h"] / 2
            if u < 0.35 * self.k and h["style"] == "flicker":
                x += (h01(h["seed"] + 7, fi) - 0.5) * 6
            x = min(max(x, 28.0), W - 28.0 - h["w"])   # keep fully on-screen
            b = min(255.0, (214 + 40 * min(pulse, 1.0)) * min(a, 1.0))
            draws.append((h["mask"], x, y, b))
            boxes.append((x, y, x + h["w"], y + h["h"], min(a, 1.0), 0.8))
        for it in self.interrupts:
            s, d = it["start"], it["dur"]
            if t < s or t > s + d:
                continue
            u = t - s
            edge_in, edge_out = 0.12 * self.k, 0.14 * self.k
            tk = smoothstep(u / edge_in) * smoothstep((d - u) / (edge_out * 1.6))
            takeover = max(takeover, tk)
            n = h01(it["seed"], fi)
            mask = it["mask"]
            if u < edge_in:
                a = 1.0 if n < 0.25 + 0.7 * (u / edge_in) else 0.0
                mask = self._slice_mask(mask, it["seed"], fi, 38)
            elif u > d - edge_out:
                q = (d - u) / edge_out
                a = 1.0 if n < 0.2 + 0.8 * q else 0.0
                mask = self._slice_mask(mask, it["seed"], fi, 26)
            else:
                a = 0.5 if n < 0.04 else 1.0
            x = it["cx"] - it["w"] / 2
            y = it["cy"] - it["h"] / 2
            if a > 0:
                draws.append((mask, x, y, 255.0))
            boxes.append((x, y, x + it["w"], y + it["h"], tk, 0.92))
        return draws, boxes, takeover

    @staticmethod
    def _occl(boxes, px, py):
        f = 1.0
        for x0, y0, x1, y1, a, st in boxes:
            dx = max(x0 - 18 - px, 0.0, px - (x1 + 18))
            dy = max(y0 - 14 - py, 0.0, py - (y1 + 14))
            d = math.hypot(dx, dy)
            f *= 1.0 - st * a * (1.0 - smoothstep(d / 70.0))
        return max(f, 0.08)

    # ---------------------------------------------------------------- symbols
    def _make_path(self, kind, rng):
        T = self.T
        DW, DH = self.DW, self.DH
        for _ in range(200):
            if kind == "drift":
                nx = ny = 0
                nseg = rng.randint(3, 5)
                mag = (50, 120)
                vmax = 260
            elif kind == "cruise":
                nx = rng.choice([-1, 1])
                ny = rng.choice([0, 0, 0, -1, 1])
                nseg = rng.randint(2, 3)
                mag = (15, 60)
                vmax = 420
            elif kind == "kinky":
                nx = rng.choice([-1, 0, 1])
                ny = rng.choice([0, 0, -1, 1])
                nseg = rng.randint(4, 6)
                mag = (150, 420)
                vmax = 560
            else:  # shoot
                r_ = rng.random()
                if r_ < 0.30:                      # straight up / down
                    nx, ny = rng.choice([-1, 0, 0, 1]), rng.choice([-6, -5, -4, 4, 5, 6])
                elif r_ < 0.55:                    # diagonals
                    nx, ny = rng.choice([-4, -3, 3, 4]), rng.choice([-5, -4, 4, 5])
                else:                              # left / right
                    nx = rng.choice([-5, -4, -3, -2, 2, 3, 4, 5])
                    ny = rng.choice([-1, 0, 0, 1])
                nseg = rng.randint(2, 4)
                mag = (30, 120)
                vmax = 1100
            w = [rng.uniform(0.5, 1.6) for _ in range(nseg)]
            ws = sum(w)
            durs = [T * wi / ws for wi in w]
            share = [rng.uniform(0.4, 1.8) for _ in range(nseg)]
            ss = sum(share)
            wig = []
            for _i in range(nseg):
                ang = rng.uniform(0, 2 * math.pi)
                r = rng.uniform(*mag)
                wig.append([r * math.cos(ang), r * math.sin(ang) * (0.5 if kind == "drift" else 1.0)])
            mx = sum(v[0] for v in wig) / nseg
            my = sum(v[1] for v in wig) / nseg
            disps = []
            for i in range(nseg):
                dx = nx * DW * share[i] / ss + (wig[i][0] - mx)
                dy = ny * DH * share[i] / ss + (wig[i][1] - my)
                disps.append((dx, dy))
            path = Path(durs, disps)
            if path.max_speed() > vmax:
                continue
            if kind == "drift":
                x0 = rng.uniform(MARGIN + 260, MARGIN + W - 260)
                y0 = rng.uniform(MARGIN + 70, MARGIN + H - 70)
                ok = True
                for q in range(0, 101):
                    px, py = path.at(T * q / 100)
                    if not (0 <= x0 + px < DW and 0 <= y0 + py < DH):
                        ok = False
                        break
                if not ok:
                    continue
            else:
                x0 = rng.uniform(0, DW)
                y0 = rng.uniform(0, DH)
            return path, x0, y0
        raise RuntimeError("could not build path for " + kind)

    def _build_symbols(self):
        rng = self.rng
        T = self.T
        tokens = []   # (text, is_expr)
        for s in SYMBOLS:
            tokens.append((s, False))
        for s in EXPRESSIONS:
            tokens.append((s, True))
        for s in EXTRAS:
            tokens.append((s, False))
        # drop anything the available fonts cannot draw
        usable = []
        for text, ex in tokens:
            if pick_font(text, ["serif", "serif_italic", "sans"]):
                usable.append((text, ex))
            else:
                print("  (skipping symbol with no glyph coverage: %r)" % text)
        regular_n = N_SYMBOLS - N_GHOSTS
        pool = list(usable)
        while len(pool) < regular_n:
            pool.append(rng.choice([u for u in usable if not u[1]]))
        rng.shuffle(pool)
        pool = pool[:regular_n]
        # make sure every explicitly requested token is present
        present = {p[0] for p in pool}
        missing = [u for u in usable if u[0] not in present]
        for i, m in enumerate(missing):
            pool[i] = m

        kinds = (["drift"] * 16 + ["cruise"] * 10 + ["shoot"] * 20 + ["kinky"] * 10)
        kinds = (kinds + ["kinky"] * regular_n)[:regular_n]
        rng.shuffle(kinds)

        self.syms = []
        for (text, ex), kind in zip(pool, kinds):
            s = Sym()
            s.text = text
            s.kind = kind
            if ex:
                s.size = rng.choice([17, 20, 23, 26])
                prefs = ["serif_italic", "serif", "sans"]
            else:
                s.size = rng.choices([16, 20, 24, 30, 38, 48], [12, 20, 20, 18, 12, 8])[0]
                prefs = ["serif", "sans", "serif_italic"] if rng.random() > 0.3 else ["sans", "serif", "serif_italic"]
            if kind == "shoot":
                s.size = min(s.size, 30)
            s.font_path = pick_font(text, prefs)
            if s.size <= 24:
                s.bright = rng.uniform(95, 215)
            else:
                s.bright = rng.uniform(70, 175)
            if kind == "shoot":
                s.bright = min(235, s.bright + 25)
            s.ghost = False
            self._finish_symbol(s, rng)
            self.syms.append(s)
        for gi in range(N_GHOSTS):
            text = GHOST_GLYPHS[gi % len(GHOST_GLYPHS)]
            if not pick_font(text, ["serif", "sans"]):
                continue
            s = Sym()
            s.text = text
            s.kind = "drift" if gi % 2 == 0 else "cruise"
            s.size = rng.randint(95, 150)
            s.font_path = pick_font(text, ["serif", "sans"])
            s.bright = rng.uniform(26, 50)
            s.ghost = True
            self._finish_symbol(s, rng)
            self.syms.append(s)
        # clusters: pull some drifting (non-wrapping) symbols together at set times
        drifters = [s for s in self.syms if s.kind == "drift" and not s.ghost and s.size <= 38]
        rng.shuffle(drifters)
        for s in self.syms:
            s.cluster = None
        pos = 0
        self.clusters = []
        for ci, (ct, (cx, cy)) in enumerate(CLUSTERS):
            members = drifters[pos:pos + 6]
            pos += 6
            for s in members:
                s.cluster = ci
                s.coff = (rng.uniform(-48, 48), rng.uniform(-26, 26))
            self.clusters.append(dict(t=ct * self.k, c=(cx, cy)))
        self.syms.sort(key=lambda s: s.size)   # big/ghost glyphs drawn first
        # a few symbols are lines-eligible
        for s in self.syms:
            s.linker = (not s.ghost) and s.size <= 38

    def _finish_symbol(self, s, rng):
        T = self.T
        s.path, s.x0, s.y0 = self._make_path(s.kind, rng)
        r = rng.random()
        s.a0 = rng.uniform(-12, 12)
        s.rot = "none"
        if s.ghost:
            s.rot = "wobble"
        elif r < 0.40:
            s.rot = "spin"
            s.spin = rng.choice([-3, -2, -1, 1, 2]) if s.kind == "shoot" else rng.choice([-2, -1, 1, 1, 2])
        elif r < 0.65:
            s.rot = "wobble"
        if s.rot == "wobble":
            s.wa = rng.uniform(10, 35)
            s.wk = rng.choice([1, 2, 3])
            s.wp = rng.uniform(0, 6.28)
        s.fk = rng.choice([1, 2, 3, 4])
        s.fp = rng.uniform(0, 6.28)
        s.gain = rng.uniform(0.35, 1.0) if not s.ghost else 0.5
        s.masks = {}

    def _get_mask(self, s, lev, ang):
        key = (id(s), lev, ang)
        m = self._rot_cache.get(key)
        if m is None:
            base = s.masks.get(lev)
            if base is None:
                f = load_font(s.font_path, s.size * SYM_SCALES[lev])
                base = text_mask(s.text, f)
                s.masks[lev] = base
            m = base if ang == 0 else base.rotate(ang, resample=Image.BICUBIC, expand=True)
            self._rot_cache[key] = m
        return m

    # --------------------------------------------------------- atmosphere data
    def _build_dust(self):
        rng = random.Random(self.seed + 99)
        self.dust = []
        for _ in range(N_DUST):
            self.dust.append(dict(
                x0=rng.uniform(0, W), y0=rng.uniform(4, H - 4),
                n=rng.choice([-3, -2, -1, 1, 2, 3, 0, 1, -1]),
                amp=rng.uniform(0, 9), m=rng.choice([1, 2, 3]), ph=rng.uniform(0, 6.28),
                b=rng.uniform(40, 125), tk=rng.choice([1, 2, 3, 5]), tp=rng.uniform(0, 6.28),
                big=rng.random() < 0.10))

    def _build_flashes(self):
        rng = random.Random(self.seed + 5)
        fp = pick_font("A", ["serif_italic", "serif", "sans"])
        self.flashes = []
        usable = [e for e in FLASH_EQUATIONS if pick_font(e, ["serif", "sans", "serif_italic"])]
        for i, t in enumerate(FLASH_TIMES):
            text = usable[i % len(usable)]
            path = pick_font(text, ["serif", "sans", "serif_italic"])
            m = text_mask(text, load_font(path, 17))
            self.flashes.append(dict(t=t * self.k, dur=0.2 * self.k, mask=m,
                                     x=rng.uniform(30, W - 280), y=rng.uniform(26, 190), seed=900 + i * 13))

    # ------------------------------------------------------------------ render
    def render(self, i):
        T = self.T
        t = i / self.fps
        tau = float(self.tau[i])
        fi = i % self.N
        img = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(img)
        draws, boxes, takeover = self._text_state(t, fi)
        dimmer = 1.0 - 0.55 * takeover

        # ---- layer 1: grid, dust ------------------------------------------------
        genv = 0.0
        for a, b in GRID_WINDOWS:
            a, b = a * self.k, b * self.k
            if a <= t <= b:
                genv = max(genv, math.sin(math.pi * (t - a) / (b - a)) ** 2)
        if genv > 0.01:
            gb = int(26 * genv * dimmer)
            off = 60.0 * tau / T
            for j in range(-1, 21):
                x = int((j * 60 + off) % (W + 60)) - 0
                d.line([(x, 0), (x, H)], fill=gb)
            for j in range(0, 7):
                y = 30 + 60 * j
                d.line([(0, y), (W, y)], fill=gb)
        for p in self.dust:
            x = (p["x0"] + p["n"] * W * tau / T) % W
            y = p["y0"] + p["amp"] * math.sin(2 * math.pi * p["m"] * tau / T + p["ph"])
            b = p["b"] * (0.65 + 0.35 * math.sin(2 * math.pi * p["tk"] * t / T + p["tp"])) * dimmer
            if b < 10:
                continue
            if p["big"]:
                d.rectangle([x, y, x + 1, y + 1], fill=int(b))
            else:
                d.point((x, y), fill=int(b))

        # ---- layer 2: symbols ---------------------------------------------------
        t_events = [e for sh in (-T, 0.0, T) for e in self.events if 0 <= t - (e["t"] + sh) < 1.4]
        active = [(e, t - (e["t"] + sh)) for sh in (-T, 0.0, T) for e in self.events
                  if 0 <= t - (e["t"] + sh) < 1.4]
        gpull = []
        for c in self.clusters:
            dt = min(abs(t - c["t"] - sh) for sh in (-T, 0.0, T))
            gpull.append(0.82 * math.exp(-0.5 * (dt / (0.45 * self.k)) ** 2))
        states = []
        for s in self.syms:
            dx, dy = s.path.at(tau)
            x = (s.x0 + dx) % self.DW - MARGIN
            y = (s.y0 + dy) % self.DH - MARGIN
            if s.cluster is not None:
                g = gpull[s.cluster]
                cx, cy = self.clusters[s.cluster]["c"]
                x += g * (cx + s.coff[0] - x)
                y += g * (cy + s.coff[1] - y)
            react = 0.0
            for e, dt in active:
                ddx, ddy = x - e["ox"], y - e["oy"]
                dist = math.hypot(ddx, ddy)
                rr = e["v"] * dt
                a = e["s"] * math.exp(-dt / 0.6) * math.exp(-(((dist - rr) / e["w"]) ** 2))
                if a > 0.002:
                    react += a
                    if dist > 1:
                        sh = 18.0 * a * s.gain
                        x += ddx / dist * sh
                        y += ddy / dist * sh
            react = min(react * s.gain, 1.6)
            if x < -160 or x > W + 160 or y < -160 or y > H + 160:
                states.append(None)
                continue
            states.append((s, x, y, react))

        # thin connecting lines (behind symbols)
        gate = max(0.0, math.sin(2 * math.pi * 3 * t / T + 1.1)) ** 1.4
        if gate > 0.05:
            pts = [(st[1], st[2], st[0]) for st in states if st and st[0].linker
                   and -10 < st[1] < W + 10 and -10 < st[2] < H + 10]
            cand = []
            for a_i in range(len(pts)):
                for b_i in range(a_i + 1, len(pts)):
                    dd = math.hypot(pts[a_i][0] - pts[b_i][0], pts[a_i][1] - pts[b_i][1])
                    if dd < LINE_DIST:
                        cand.append((dd, a_i, b_i))
            cand.sort()
            for dd, a_i, b_i in cand[:LINE_MAX]:
                lb = (28 + 62 * (1 - dd / LINE_DIST)) * gate * dimmer
                lb *= min(self._occl(boxes, pts[a_i][0], pts[a_i][1]),
                          self._occl(boxes, pts[b_i][0], pts[b_i][1]))
                if lb > 10:
                    d.line([(pts[a_i][0], pts[a_i][1]), (pts[b_i][0], pts[b_i][1])], fill=int(lb))

        for st in states:
            if st is None:
                continue
            s, x, y, react = st
            b = s.bright * (0.82 + 0.18 * math.sin(2 * math.pi * s.fk * t / T + s.fp))
            b = b * dimmer * self._occl(boxes, x, y) + 120.0 * react
            if b < 8:
                continue
            b = min(b, 255.0)
            lev = min(3, int(react * 3.2))
            if s.rot == "spin":
                ang = s.a0 + 360.0 * s.spin * tau / T
            elif s.rot == "wobble":
                ang = s.a0 + s.wa * math.sin(2 * math.pi * s.wk * tau / T + s.wp)
            else:
                ang = s.a0
            aq = int(round(ang / 4.0)) * 4 % 360
            m = self._get_mask(s, lev, aq)
            img.paste(int(b), (int(x - m.width / 2), int(y - m.height / 2)), m)

        # tiny equation flashes
        for f in self.flashes:
            if f["t"] <= t <= f["t"] + f["dur"] and h01(f["seed"], fi) < 0.75:
                fb = 150 * self._occl(boxes, f["x"] + f["mask"].width / 2, f["y"]) * dimmer
                if fb > 10:
                    img.paste(int(fb), (int(f["x"]), int(f["y"])), f["mask"])

        # ---- heartbeat trace ----------------------------------------------------
        self._draw_ecg(img, t)

        # ---- layer 3: typography -----------------------------------------------
        for mask, x, y, b in draws:
            img.paste(int(b), (int(x), int(y)), mask)

        arr = np.array(img)
        arr = self._glitch(arr, i, t)
        # quantise to GREY_LEVELS (index 0 stays pure black)
        L = self.levels
        idx = ((arr.astype(np.uint16) * (L - 1) + 127) // 255).astype(np.uint8)
        out = Image.fromarray(idx, "P")
        pal = []
        for g in range(L):
            v = int(round(g * 255 / (L - 1)))
            pal += [v, v, v]
        pal += [0] * (768 - len(pal))
        out.putpalette(pal)
        return out

    def _draw_ecg(self, img, t):
        SS = self.SS
        layer = Image.new("L", (W * SS, self.ecg_h * SS), 0)
        d = ImageDraw.Draw(layer)
        xh = (t / self.T) * W
        prom = self.prominence(t)
        pulse = self.pulse(t)
        for xm, pts in self.ecg_chunks:
            dd = (xh - xm) % W
            b = 24 + (215 - 24) * math.exp(-dd / 260.0)
            if dd > W - 70:
                b *= max(0.0, (W - dd) / 70.0)
            b = min(255.0, b * (1 + 0.16 * min(prom, 1.2)))
            if b < 8:
                continue
            wdt = 4 if dd < 120 + 60 * min(prom, 1.0) else 2
            d.line(pts, fill=int(b), width=wdt)
        # sweeping head
        i0 = min(int(xh * SS), len(self.ecg_y) - 1)
        hy = (self.ecg_y[i0] - self.ecg_y0) * SS
        r = 5 + 3 * min(pulse, 1.0)
        d.ellipse([xh * SS - r * 2, hy - r * 2, xh * SS + r * 2, hy + r * 2], fill=45)
        d.ellipse([xh * SS - r, hy - r, xh * SS + r, hy + r], fill=255)
        small = layer.resize((W, self.ecg_h), Image.BOX)
        region = img.crop((0, self.ecg_y0, W, H))
        region = ImageChops.lighter(region, small)
        img.paste(region, (0, self.ecg_y0))

    def _glitch(self, arr, i, t):
        fs_per = self.fps
        for j, (gt, kind) in enumerate(GLITCHES):
            f0 = int(round(gt * self.k * fs_per))
            nfr = 3 if kind == "big" else 2
            if not (f0 <= i < f0 + nfr):
                continue
            r = random.Random(4000 + j * 31 + (i - f0))
            if kind in ("shift", "big"):
                bands = 2 if kind == "shift" else 4
                for _ in range(bands):
                    y = r.randint(8, H - 30)
                    hh = r.randint(5, 22)
                    dx = r.choice([-1, 1]) * r.randint(14, 70)
                    arr[y:y + hh] = np.roll(arr[y:y + hh], dx, axis=1)
            if kind in ("dash", "big"):
                for _ in range(r.randint(4, 9)):
                    y = r.randint(2, H - 3)
                    x = r.randint(0, W - 40)
                    ln = r.randint(30, 220)
                    v = r.randint(70, 150)
                    arr[y, x:x + ln] = np.maximum(arr[y, x:x + ln], v)
        return arr


# =============================================================================
# OUTPUT
# =============================================================================
def build_gif(out_path, duration, fps, levels, seed, preview=False):
    print("Building scene ...")
    sc = Scene(duration=duration, fps=fps, seed=seed, levels=levels)
    print("  %d frames, %d symbols, head font: %s" % (sc.N, len(sc.syms), os.path.basename(sc.head_path or "built-in")))
    frames = []
    for i in range(sc.N):
        frames.append(sc.render(i))
        if i % 25 == 0:
            print("  rendered %d/%d" % (i, sc.N))
    ms = int(round(1000.0 / fps))
    print("Saving %s ..." % out_path)
    frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=ms, loop=0,
                   optimize=False, disposal=1)
    size = os.path.getsize(out_path)
    print("Done: %s  (%.2f MB, %d frames @ %d FPS = %.1fs)" % (out_path, size / 1e6, sc.N, fps, sc.N / fps))
    if preview:
        pv = os.path.splitext(out_path)[0] + "_preview.png"
        pick = [int(sc.N * f) for f in (0.0, 0.09, 0.18, 0.33, 0.42, 0.55, 0.66, 0.76, 0.83, 0.93)]
        sheet = Image.new("L", (W, H * len(pick) // 2 + 0), 0)
        sheet = Image.new("L", (W * 2, H * ((len(pick) + 1) // 2)), 40)
        for n, fi in enumerate(pick):
            fr = frames[fi].convert("L")
            sheet.paste(fr, ((n % 2) * W, (n // 2) * H))
        sheet.save(pv)
        print("Preview sheet:", pv)
    return sc, frames


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate the 'controlled chaos with a pulse' GIF.")
    ap.add_argument("--out", default=OUTPUT)
    ap.add_argument("--duration", type=float, default=DURATION, help="loop length in seconds (8-10 recommended)")
    ap.add_argument("--fps", type=int, default=FPS)
    ap.add_argument("--levels", type=int, default=GREY_LEVELS, help="number of grey levels in the palette (fewer = smaller file)")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--preview", action="store_true", help="also write a PNG contact sheet")
    a = ap.parse_args()
    build_gif(a.out, a.duration, a.fps, a.levels, a.seed, a.preview)
