# -*- coding: utf-8 -*-
"""banner.py -- neon + blood version of math_chaos.gif  ->  ../assets/banner.gif
Uses the scene from ../../math_chaos.py (or ./math_chaos.py next to this file) and post-processes
each frame: cool-white neon halo on bright elements, dark-red blood ONLY on the ECG outline.
    python tools/banner.py [--fps 16.667] [--duration 9.96] [--colors 64]
"""
import argparse, os, sys
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")):
    if os.path.exists(os.path.join(p, "math_chaos.py")):
        sys.path.insert(0, p); break
import math_chaos as mc
from engine import save_gif, HALO, RED, h01

OUT = os.path.join(HERE, "..", "assets", "banner.gif")


class Banner(mc.Scene):
    def _draw_ecg(self, img, t):
        tmp = Image.new("L", img.size, 0)
        super()._draw_ecg(tmp, t)
        self._ecg = np.asarray(tmp, np.float32) / 255
        img.paste(ImageChops.lighter(img, tmp))

    def setup(self):
        r = np.random.RandomState(21)
        g = (r.rand(self.N // 1 + 3, 1) * 0).astype(np.uint8)
        nz = np.asarray(Image.fromarray((r.rand(3, mc.W // 18 + 3) * 255).astype(np.uint8)).resize((mc.W, 1), Image.BICUBIC), np.float32)[0] / 255
        self.stain_x = np.clip((nz - 0.66) / 0.07, 0, 1)
        xs = sorted(r.choice(np.arange(40, mc.W - 40), 14, replace=False))
        self.drips = [(int(x), int(r.randint(14, 50)), int(r.choice([2, 3]))) for x in xs]

    def render2(self, i):
        base = np.asarray(self.render(i).convert("L"), np.float32) / 255
        ecg = self._ecg
        s_pix = np.clip(self.stain_x[None, :] * ecg / np.maximum(base, 1e-3), 0, 1) * (ecg > 0.02)
        white = base * (1 - s_pix)
        red = base * s_pix
        # drips hang from the trace, as bright as the trace is at that x
        dr = Image.new("L", (mc.W, mc.H), 0); d = ImageDraw.Draw(dr)
        for x, ln, w in self.drips:
            col = ecg[:, x]
            ys = np.nonzero(col > 0.12)[0]
            if not len(ys):
                continue
            y = int(ys.max()); b = float(col[y])
            if h01(x, i // 3) < 0.04:
                continue
            d.line([(x, y + 1), (x, y + ln * 0.6)], fill=int(235 * b), width=w)
            d.line([(x, y + ln * 0.6), (x, y + ln)], fill=int(235 * b), width=max(1, w - 1))
            d.ellipse([x - w, y + ln - w, x + w, y + ln + w], fill=int(255 * b))
        red = np.clip(red + np.asarray(dr, np.float32) / 255, 0, 1)
        bright = Image.fromarray((np.where(white > 0.5, white, 0) * 255).astype(np.uint8))   # only bright things glow
        h1 = np.asarray(bright.filter(ImageFilter.GaussianBlur(2.0)), np.float32) / 255
        h2 = np.asarray(bright.filter(ImageFilter.GaussianBlur(9)), np.float32) / 255
        halo = np.clip(0.8 * h1 + 1.8 * h2, 0, 1) * 0.95
        rg = np.asarray(Image.fromarray((red * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4)), np.float32) / 255
        out = np.empty((mc.H, mc.W, 3), np.float32)
        for c in range(3):
            out[..., c] = white * 255 + halo * HALO[c] + red * RED[c] + rg * (52 if c == 0 else 4)
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fps", type=float, default=12.5)           # 80 ms frames
    ap.add_argument("--duration", type=float, default=9.92)      # = 124 frames, exact loop
    ap.add_argument("--colors", type=int, default=48)            # 4.1 MB; 64 colours = 4.4 MB
    a = ap.parse_args()
    sc = Banner(duration=a.duration, fps=a.fps, levels=256)
    sc.setup()
    print("rendering", sc.N, "frames")
    frames = [sc.render2(i) for i in range(sc.N)]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    save_gif(frames, OUT, a.fps, a.colors)
    print("wrote", os.path.normpath(OUT), "%.2f MB" % (os.path.getsize(OUT) / 1e6))
