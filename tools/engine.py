# -*- coding: utf-8 -*-
"""engine.py -- turns a finished fx.Canvas into a looping neon GIF.

Timeline (T seconds, seamless): blank until t_off -> elements load one after another, each
revealed by a travelling ECG trace -> hold (headings flicker/flash, blood drips run) ->
elements drop out and glyphs fly away -> blank -> loop.
"""
import hashlib
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from fx import glyph_mask

FLICK = [(1.0, 0), (0.15, 0), (1.0, 1), (0.45, 0), (1.0, 1), (0.8, 0), (1.0, 0)]
RED = (118.0, 4.0, 12.0)           # dark blood red
HALO = (150.0, 200.0, 255.0)       # cool white neon halo


def h01(a, b):
    x = (int(a) * 374761393 + int(b) * 668265263 + 144665) & 0xFFFFFFFF
    x = ((x ^ (x >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((x ^ (x >> 16)) & 0xFFFF) / 65535.0


def ease_out(u):
    return 1 - (1 - min(max(u, 0.0), 1.0)) ** 3


def ease_in(u):
    return min(max(u, 0.0), 1.0) ** 2.2


def ecg_f(u):
    g = lambda m, s, a: a * np.exp(-0.5 * ((u - m) / s) ** 2)
    return g(.12, .03, .10) + g(.27, .008, -.15) + g(.30, .011, 1.0) + g(.33, .009, -.30) + g(.52, .011, .55) + g(.70, .04, .18)


class Anim:
    def __init__(s, cv, flyers, t_off, T=10.0, fps=10.0, seed=1, exit_len=0.9):
        s.cv, s.fl, s.t_off, s.T, s.fps = cv, flyers, t_off, T, fps
        s.N = int(round(T * fps))
        s.Tx = T - exit_len
        rs = np.random.RandomState(seed)
        n = len(cv.els)
        step = min(0.11, 1.3 / max(n - 1, 1))
        for k, e in enumerate(cv.els):
            w = e["box"][2] - e["box"][0]
            e["s"] = t_off + k * step
            e["d"] = min(0.95, max(0.3, 0.25 + w / 1300 * 0.8))
            e["die"] = s.Tx + rs.rand() * (exit_len - 0.3)
        heads = [i for i, e in enumerate(cv.els) if e["kind"] == "head"]
        s.flicks = []
        for j, i in enumerate(heads):
            t1 = t_off + 3.0 + 0.8 * j + rs.rand() * 0.4
            for ts in (t1, t1 + 3.4):
                if ts + 0.6 < s.Tx - 0.1:
                    s.flicks.append((i, ts))
        s.big = {}

    # ---------------------------------------------------------------- state
    def state(s, t, i):
        cv = s.cv
        vis = np.zeros((cv.h, cv.w), np.float32)
        boosts, reveal_t = [], {}
        for idx, e in enumerate(cv.els):
            x0, y0, x1, y1 = e["box"]
            if t < e["s"] or t >= e["die"]:
                continue
            p = min(1.0, (t - e["s"]) / e["d"])
            hx = x1 if p >= 1 else int(x0 + (x1 - x0) * p)
            a = 0.0 if (t > e["die"] - 0.2 and h01(idx, i) < 0.4) else 1.0
            for fi, ts in s.flicks:
                if fi == idx:
                    k = int((t - ts) * s.fps + 1e-6)
                    if 0 <= k < len(FLICK):
                        a *= FLICK[k][0]
                        if FLICK[k][1]:
                            boosts.append(e["box"])
            vis[y0:y1, x0:hx] = a
            if p < 1:
                vis[y0:y1, max(x0, hx - 30):hx] *= 0.55 + 0.45 * h01(idx + 7, i)
        return vis, boosts

    def trace(s, t):
        im = Image.new("L", (s.cv.w, s.cv.h), 0)
        d = ImageDraw.Draw(im)
        for e in s.cv.els:
            if t < e["s"] or t > e["s"] + e["d"] + 0.3 or t >= e["die"]:
                continue
            x0, y0, x1, y1 = e["box"]
            p = min(1.0, (t - e["s"]) / e["d"])
            hx = x0 + (x1 - x0) * p
            fade = 1.0 if p < 1 else max(0.0, 1 - (t - e["s"] - e["d"]) / 0.3)
            ym, A, P = (y0 + y1) / 2, min(26.0, (y1 - y0) * 0.9 + 6), min(150.0, max(60.0, (x1 - x0) / 1.6))
            xs = np.arange(max(x0, hx - 230), hx + 0.1, 2.0)
            if len(xs) < 2:
                continue
            ys = ym - A * ecg_f(((xs - x0) % P) / P)
            for c in range(0, len(xs) - 1, 12):
                seg = list(zip(xs[c:c + 13], ys[c:c + 13]))
                if len(seg) < 2:
                    continue
                b = fade * max(0.0, 1 - (hx - xs[c]) / 230) ** 1.3
                if b > 0.04:
                    d.line(seg, fill=int(255 * b), width=2)
            if p < 1:
                yh = ym - A * float(ecg_f(((hx - x0) % P) / P))
                d.ellipse([hx - 3, yh - 3, hx + 3, yh + 3], fill=255)
        return np.asarray(im, np.float32) / 255

    def drips(s, t):
        im = Image.new("L", (s.cv.w, s.cv.h), 0)
        d = ImageDraw.Draw(im)
        for dr in s.cv.drips:
            e = s.cv.els[dr["el"]]
            x0, y0, x1, y1 = e["box"]
            if t >= e["die"] or e["s"] > t:
                continue
            te = e["s"] + e["d"] * (dr["x"] - x0) / max(1, x1 - x0)
            g = min(1.0, max(0.0, (t - te - 0.15) / 1.0))
            g = 1 - (1 - g) ** 2
            if g <= 0:
                continue
            if t > e["die"] - 0.2 and h01(dr["x"], int(t * 100)) < 0.4:
                continue
            L = max(1, int(dr["len"] * g))
            x, y, w = dr["x"], dr["y"] + 1, dr["w"]
            d.line([(x, y), (x, y + int(L * 0.6))], fill=235, width=w)
            d.line([(x, y + int(L * 0.6)), (x, y + L)], fill=235, width=max(1, w - 1))
            if g > 0.85:
                d.ellipse([x - w, y + L - w, x + w, y + L + w], fill=255)
        return np.asarray(im, np.float32) / 255

    def flyers(s, t):
        cv = s.cv
        im = Image.new("L", (cv.w, cv.h), 0)
        for f in s.fl:
            fs = s.t_off + f["delay"]
            fe, ls = fs + f["dur"], s.Tx + f["xdelay"]
            if t < fs:
                continue
            for back, br in ((0.0, 1.0), (1.0, 0.42), (2.0, 0.2)):
                tt = t - back / s.fps
                if tt < fs:
                    continue
                if tt < fe:
                    u = ease_out((tt - fs) / f["dur"]); moving = u < 0.999
                    dx, dy, rot = f["din"][0] * f["R"] * (1 - u), f["din"][1] * f["R"] * (1 - u), f["rin"] * (1 - u)
                elif tt >= ls:
                    u = ease_in((tt - ls) / 0.75); moving = True
                    if u >= 1:
                        continue
                    dx, dy, rot = f["dout"][0] * f["R"] * u, f["dout"][1] * f["R"] * u, f["rout"] * u
                else:
                    dx = dy = rot = 0.0; moving = False
                if back and not moving:
                    continue
                key = (f["ch"], f["size"], int(round(rot / 6.0)) * 6 % 360)
                m = s.big.get(key)
                if m is None:
                    base = glyph_mask(f["ch"], f["size"])
                    m = s.big[key] = base.rotate(key[2], resample=Image.BICUBIC, expand=True) if key[2] else base
                im.paste(int(255 * f["bright"] * br), (int(f["cx"] + dx - m.width / 2), int(f["cy"] + dy - m.height / 2)), m)
        return np.asarray(im, np.float32) / 255

    # -------------------------------------------------------------- compose
    def compose(s, vis, tr, dr, fl, boosts):
        cv = s.cv
        lf = cv.line_f * vis
        white = np.clip(cv.txt_f * vis + lf * (1 - cv.stain) + tr + fl, 0, 1)
        red = np.clip(lf * cv.stain + dr, 0, 1)
        wi = Image.fromarray((white * 255).astype(np.uint8))
        h1 = np.asarray(wi.filter(ImageFilter.GaussianBlur(2.2)), np.float32) / 255
        h2 = np.asarray(wi.filter(ImageFilter.GaussianBlur(10)), np.float32) / 255
        halo = np.clip(0.85 * h1 + 1.9 * h2, 0, 1) * 0.95
        for (x0, y0, x1, y1) in boosts:
            m = np.zeros_like(white); m[max(0, y0 - 6):y1 + 6, x0:x1] = 1
            b = Image.fromarray((white * m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(7))
            halo = np.clip(halo + 1.6 * np.asarray(b, np.float32) / 255, 0, 1)
        rg = np.asarray(Image.fromarray((red * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4)), np.float32) / 255
        out = np.empty((cv.h, cv.w, 3), np.float32)
        for c in range(3):
            out[..., c] = white * 255 + halo * HALO[c] + red * RED[c] + rg * (52 if c == 0 else 4)
        return np.clip(out, 0, 255).astype(np.uint8)

    def frames(s):
        out, prev, pkey = [], None, None
        for i in range(s.N):
            t = i / s.fps
            vis, boosts = s.state(t, i)
            tr, dr, fl = s.trace(t), s.drips(t), s.flyers(t)
            key = hashlib.md5(vis.tobytes() + tr.tobytes() + dr.tobytes() + fl.tobytes() + repr(boosts).encode()).hexdigest()
            if key != pkey:
                prev = Image.fromarray(s.compose(vis, tr, dr, fl, boosts), "RGB")
                pkey = key
            out.append(prev)
        return out


def palette_from(frames, colors=96):
    """Median-cut palette from sample frames, with rare red pixels up-weighted so blood survives."""
    picks = frames[::max(1, len(frames) // 14)]
    px = np.concatenate([np.asarray(f).reshape(-1, 3) for f in picks])
    bright = px[px.max(1) > 12]
    redy = px[(px[:, 0] > px[:, 1] + 30)]
    px = np.concatenate([bright[::4], np.repeat(redy, 12, axis=0) if len(redy) else bright[:1]])
    side = int(math.ceil(math.sqrt(len(px))))
    buf = np.zeros((side * side, 3), np.uint8)
    buf[:len(px)] = px
    sheet = Image.fromarray(buf.reshape(side, side, 3), "RGB")
    return sheet.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)


def save_gif(frames, path, fps, colors=96):
    pal = palette_from(frames, colors)
    p = pal.getpalette()[:colors * 3]
    dark = min(range(colors), key=lambda k: p[3 * k] + p[3 * k + 1] + p[3 * k + 2])
    p[3 * dark:3 * dark + 3] = [0, 0, 0]                    # background must be pure #000000
    pal.putpalette(p + [0] * (768 - len(p)))
    cache, q = {}, []
    for f in frames:
        k = id(f)
        if k not in cache:
            cache[k] = f.quantize(palette=pal, dither=Image.Dither.NONE)
        q.append(cache[k])
    q[0].save(path, save_all=True, append_images=q[1:], duration=int(round(1000 / fps)), loop=0, disposal=1, optimize=False)
