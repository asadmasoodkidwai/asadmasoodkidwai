# -*- coding: utf-8 -*-
"""panels.py -- builds every animated panel GIF for the profile README.

    python tools/panels.py            # writes ../assets/*.gif
Edit the CONTENT block to change text; timing/size knobs are at the bottom.
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fx import Canvas, wrap, F
from engine import Anim, save_gif

W, FPS, T, COLORS = 1200, 10.0, 10.0, 64
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

# ------------------------------------------------------------------ CONTENT
NAME = "ASAD MASOOD KIDWAI"
HERO, HERO_SUB = "THINK. QUESTION. BUILD.", "A STUDY IN CONTROLLED CHAOS"
ROLES = "COMPUTER SCIENCE STUDENT  ·  QUESTION COLLECTOR  ·  PROFESSIONAL OVERTHINKER"
WHERE = "ISLAMABAD, PK  /  FAST-NUCES  /  CURRENTLY FIGURING THINGS OUT"
ABOUT = ["I'm a Computer Science undergraduate at FAST-NUCES, interested in the intersection of "
         "artificial intelligence, mathematics, and computation.",
         "I enjoy exploring how algorithms work, experimenting with computational ideas, and building "
         "systems that apply theoretical concepts to real-world problems."]
QUOTE = "Somewhere between mathematical elegance and questionable experiments."
INTERESTS = ["Artificial Intelligence & Machine Learning", "Intelligent Agents & Reinforcement Learning",
             "Algorithms & Theoretical Computer Science", "Mathematical Optimization",
             "Network Science & Data Analysis", "Quantum Computing"]
PROJECTS = [
    dict(file="project_baadal", icon="cloud", title="BAADAL", sub="Quantum-assisted flood response planning",
         desc="Qiskit Fall Fest 2026 Hackathon. Initiated the project concept and helped guide development, "
              "suggest improvements, and contribute to implementation.",
         tags=["PYTHON", "QISKIT", "QAOA", "QAE"], link=True),
    dict(file="project_nikitis", icon="knight", title="NIKITIS", sub="Autonomous AI fighting agent",
         desc="AI agent named Nikitis, built for the Model Kombat competition and operating in a Street "
              "Fighter II emulator environment. Contributed to agent development and automated decision-making.",
         tags=["PYTHON", "AI", "GAME AUTOMATION"], link=False),
    dict(file="project_coin", icon="cube", title="COIN", sub="Crypto economy simulation",
         desc="A lightweight crypto economy simulation.",
         tags=[], link=False),
]
TOOLS = ["C++", "PYTHON", "R", "GIT", "GITHUB"]
AREAS = ["AI & ML", "ALGORITHMS", "OPTIMIZATION", "QUANTUM COMPUTING"]
MICRO = ["Coffee dependency: unverified", "Tolerance for hand-wavy explanations: high"]
EXPLORING = ["Understanding the mathematical foundations of machine learning.",
             "Exploring intelligent agents and decision-making systems.",
             "Learning more about optimization and quantum algorithms.",
             "Looking for opportunities to participate in undergraduate research."]
# Fallback GitHub numbers. Normally overridden by data/activity.json, which tools/fetch_activity.py keeps current.
ACTIVITY_STATS = [("TOTAL STARS EARNED", "0"), ("TOTAL COMMITS (LAST YEAR)", "11"), ("TOTAL PRS", "0"),
                  ("TOTAL ISSUES", "0"), ("CONTRIBUTED TO (LAST YEAR)", "0")]
ACTIVITY_LANGS = [("PYTHON", 50.92), ("C++", 24.71), ("HTML", 21.95), ("POWERSHELL", 2.11), ("BATCHFILE", 0.16), ("SHELL", 0.15)]
ACTIVITY_STREAK = [("12", "TOTAL CONTRIBUTIONS", "AUG 16, 2025 - PRESENT"), ("2", "CURRENT STREAK", "NOV 17 - NOV 18"),
                   ("2", "LONGEST STREAK", "NOV 17 - NOV 18")]
FOOT_BIG, FOOT_SMALL ="∀ QUESTIONS, ∃ MORE QUESTIONS", "AND THAT'S THE PLAN."


def _load_activity(path):
    """Overrides the ACTIVITY_* defaults above with data/activity.json (written by fetch_activity.py)."""
    global ACTIVITY_STATS, ACTIVITY_LANGS, ACTIVITY_STREAK
    if not os.path.exists(path):
        return
    import datetime
    import json
    a = json.load(open(path, encoding="utf-8"))
    today = datetime.date.today()

    def day(s, year=None):
        d = datetime.date.fromisoformat(s)
        with_year = (d.year != today.year) if year is None else year
        return d.strftime("%b %d, %Y" if with_year else "%b %d").upper()

    def span(s):
        if not s.get("days"):
            return "NONE ACTIVE"
        a0, a1 = day(s["start"]), day(s["end"])
        return a0 if a0 == a1 else "%s - %s" % (a0, a1)

    ACTIVITY_STATS = [("TOTAL STARS EARNED", str(a["stars"])), ("TOTAL COMMITS (LAST YEAR)", str(a["commits_last_year"])),
                      ("TOTAL PRS", str(a["prs"])), ("TOTAL ISSUES", str(a["issues"])),
                      ("CONTRIBUTED TO (LAST YEAR)", str(a["contributed_to"]))]
    ACTIVITY_LANGS = [(n.upper()[:12], p) for n, p in a["languages"]]
    ACTIVITY_STREAK = [(str(a["total_contributions"]), "TOTAL CONTRIBUTIONS", "%s - PRESENT" % day(a["since"], True)),
                       (str(a["current_streak"]["days"]), "CURRENT STREAK", span(a["current_streak"])),
                       (str(a["longest_streak"]["days"]), "LONGEST STREAK", span(a["longest_streak"]))]


_load_activity(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "activity.json"))
FOOT_LINE = "Curiosity drives the questions. Mathematics and computation help explore the answers."


# ------------------------------------------------------------------ layouts
def hero():
    cv = Canvas(W, 400)
    cv.text(W / 2, 34, NAME, "mono_b", 56, 255, tr=11, anchor="c", ek="head")
    x0, x1, y, cx = 230, 970, 170, W / 2
    pts = [(x0, y), (cx - 130, y), (cx - 112, y - 8), (cx - 96, y), (cx - 60, y), (cx - 50, y + 8), (cx - 40, y - 58),
           (cx - 30, y + 22), (cx - 22, y), (cx + 8, y), (cx + 24, y - 11), (cx + 40, y), (cx + 86, y), (cx + 95, y - 40),
           (cx + 104, y + 8), (cx + 110, y), (cx + 146, y), (cx + 164, y - 12), (cx + 182, y), (x1, y)]
    cv.dl.line(pts, fill=255, width=3, joint="curve")
    cv.add((x0, y - 70, x1, y + 34), "rule")
    cv.text(W / 2, 215, HERO, "mono_b", 38, 255, tr=12, anchor="c", ek="head")
    cv.text(W / 2, 272, HERO_SUB, "mono", 20, 255, tr=10, anchor="c")
    cv.text(W / 2, 318, ROLES, "mono", 16, 235, tr=2, anchor="c")
    cv.text(W / 2, 350, WHERE, "mono", 14, 200, tr=2, anchor="c")
    return cv, 16


def about():
    cv = Canvas(W, 700)
    y = cv.header(48, 34, 610, "ABOUT ME") + 30
    for p in ABOUT:
        y = cv.para(48, y, p, "mono", 21, 225, 590, 32) + 16
    qh = len(wrap(QUOTE, F("mono_i", 21), 560)) * 32
    cv.vline(48, y + 2, y + qh - 6)
    ly = cv.para(74, y, QUOTE, "mono_i", 21, 195, 560, 32)
    y = cv.header(710, 34, 442, "CURRENTLY INTERESTED IN", 20) + 30
    for it in INTERESTS:
        y = cv.para(710, y, it, "mono", 19, 225, 440, 29, bullet=">") + 11
    H = int(max(ly, y) + 40)
    return crop(cv, H), 8


def head(label):
    cv = Canvas(W, 84)
    cv.header(48, 24, W - 96, label)
    return cv, 2


def card(c, H, first):
    cv = Canvas(400, H)
    if not first:
        cv.vline(1, 26, H - 26)
    cv.icon(c["icon"], 66, 76, 84)
    cv.text(120, 44, c["title"], "mono_b", 25, 255, tr=2, ek="head")
    y = 82
    for ln in wrap(c["sub"], F("mono", 15), 262):
        cv.text(120, y, ln, "mono", 15, 185)
        y += 22
    y = max(y, 128) + 24
    y = cv.para(26, y, c["desc"], "mono", 16, 215, 350, 25) + 14
    if c["tags"]:
        y = cv.chips(26, y, c["tags"], 13, 378, pad=(11, 6), gap=8) + 22
    if c["link"]:
        cv.text(26, y, "→ VIEW PROJECT", "mono_b", 16, 255, tr=3)
        y += 28
    return cv, y + 28


def toolbox():
    cv = Canvas(W, 700)
    y = cv.header(48, 30, 640, "THE TOOLBOX", 22)
    cv.text(48, y + 28, "LANGUAGES & TOOLS", "mono", 14, 170, tr=3)
    y = cv.chips(48, y + 56, TOOLS, 20, 690, pad=(16, 9), gap=12)
    cv.text(48, y + 30, "AREAS I'M EXPLORING", "mono", 14, 170, tr=3)
    y = cv.chips(48, y + 58, AREAS, 16, 690, pad=(13, 7), gap=10) + 30
    cv.hline(48, 690, y)
    cv.text(48, y + 20, MICRO[0], "mono", 17, 205)
    ly = cv.text(48, y + 54, MICRO[1], "mono", 17, 205) and y + 84
    ey = cv.header(772, 30, 380, "CURRENTLY EXPLORING", 20) + 28
    for it in EXPLORING:
        ey = cv.para(772, ey, it, "mono", 17, 225, 380, 26, bullet=">") + 12
    H = int(max(ly, ey) + 30)
    cv.vline(724, 30, H - 30)
    return crop(cv, H), 8


def activity():
    cv = Canvas(W, 360)
    cv.header(48, 26, W - 96, "GITHUB ACTIVITY")
    cv.text(48, 100, "GITHUB STATS", "mono", 14, 170, tr=3)
    y = 134
    for lab, val in ACTIVITY_STATS:
        cv.text(48, y, lab, "mono", 16, 225)
        cv.text(388, y - 2, val, "mono_b", 20, 255, anchor="r")
        y += 38
    cv.vline(414, 96, 336)
    cv.text(440, 100, "MOST USED LANGUAGES", "mono", 14, 170, tr=3)
    shades = (255, 215, 175, 140, 110, 90)
    bx, by, bw, bh = 440, 134, 360, 16
    cv.dl.rounded_rectangle([bx, by, bx + bw, by + bh], radius=7, outline=255, width=2)
    cv.add((bx - 1, by - 1, bx + bw + 1, by + bh + 1), "chip")
    tot, x, inner = (sum(p for _, p in ACTIVITY_LANGS) or 1), bx + 4, bw - 8
    for k, (n, p) in enumerate(ACTIVITY_LANGS):
        w = max(2, int(inner * p / tot))
        cv.dt.rectangle([x, by + 4, x + (w - 1 if w <= 3 else w - 3), by + bh - 4], fill=shades[k])
        x += w
    for i, (n, p) in enumerate(ACTIVITY_LANGS):
        cx, cy = 440 + (i % 2) * 190, 180 + (i // 2) * 40
        cv.dt.rectangle([cx, cy + 5, cx + 8, cy + 13], fill=shades[i])
        cv.add((cx - 1, cy + 3, cx + 10, cy + 15), "body")
        cv.text(cx + 18, cy, "%s %.2f%%" % (n, p), "mono", 15, 225)
    cv.vline(826, 96, 336)
    cv.text(852, 100, "STREAK", "mono", 14, 170, tr=3)
    y = 128
    for num, lab, dts in ACTIVITY_STREAK:
        cv.text(852, y, num, "mono_b", 44, 255)
        lx = max(932, 852 + 27 * len(num) + 18)          # keep the label clear of big numbers
        cv.text(lx, y + 4, lab, "mono_b", 16, 255, tr=1)
        cv.text(lx, y + 32, dts, "mono", 14, 175)
        y += 74
    return cv, 4


def footer():
    cv = Canvas(W, 230)
    f = F("mono_b", 32)
    tw_ = sum(f.getlength(c) for c in FOOT_BIG) + 6 * (len(FOOT_BIG) - 1)
    cv.text(W / 2, 44, FOOT_BIG, "mono_b", 32, 255, tr=6, anchor="c", ek="head")
    cv.hline(48, W / 2 - tw_ / 2 - 30, 66)
    cv.hline(W / 2 + tw_ / 2 + 30, W - 48, 66)
    cv.text(W / 2, 108, FOOT_SMALL, "mono", 17, 200, tr=10, anchor="c")
    cv.text(W / 2, 156, FOOT_LINE, "mono_i", 16, 185, anchor="c")
    return cv, 9


def crop(cv, H):
    c2 = Canvas(cv.w, H)
    c2.txt, c2.line = cv.txt.crop((0, 0, cv.w, H)), cv.line.crop((0, 0, cv.w, H))
    from PIL import ImageDraw
    c2.dt, c2.dl = ImageDraw.Draw(c2.txt), ImageDraw.Draw(c2.line)
    c2.els = [e for e in cv.els if e["box"][3] <= H + 2]
    return c2


# ------------------------------------------------------------------ build
def build(name, cv, nfly, t_off, seed, fly_size=(34, 92)):
    cv.finish(seed)
    fl = cv.flyers(nfly, seed + 1, fly_size) if nfly else []
    a = Anim(cv, fl, t_off=t_off, T=T, fps=FPS, seed=seed)
    save_gif(a.frames(), os.path.join(OUT, name + ".gif"), FPS, COLORS)
    kb = os.path.getsize(os.path.join(OUT, name + ".gif")) / 1024
    print("  %-22s %dx%-4d els=%-2d drips=%-2d fly=%-2d %7.0f KB" % (name, cv.w, cv.h, len(cv.els), len(cv.drips), len(fl), kb))


def main(only=None):
    os.makedirs(OUT, exist_ok=True)
    jobs = []
    # t_off = when loading starts (s). Kept close together so no panel sits blank for long;
    # each one then holds for ~6 s before dropping out.
    cv, n = hero(); jobs.append(("hero", cv, n, 0.2, 3, (34, 92)))
    cv, n = about(); jobs.append(("about", cv, n, 0.5, 5, (30, 70)))
    cv, n = head("KEY PROJECTS"); jobs.append(("projects_head", cv, 1, 0.8, 7, (26, 40)))
    H = int(max(card(c, 900, i == 0)[1] for i, c in enumerate(PROJECTS)))
    for i, c in enumerate(PROJECTS):
        cv, _ = card(c, H, i == 0)
        jobs.append((c["file"], cv, 3, 1.0 + 0.15 * i, 20 + i, (26, 54)))
    cv, n = toolbox(); jobs.append(("toolbox_exploring", cv, n, 1.4, 31, (30, 66)))
    cv, n = activity(); jobs.append(("activity", cv, n, 1.7, 41, (26, 44)))
    cv, n = footer(); jobs.append(("footer", cv, n, 2.0, 51, (30, 70)))
    print("Rendering into", os.path.normpath(OUT))
    for name, cv, nf, t0, seed, fs in jobs:
        if only is None or name in only:
            build(name, cv, nf, t0, seed, fs)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
