#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1억으로 20억 만들기 — 1화 쇼츠 영상 생성기 (모션/그래픽 강화판)

- 1080x1920 / 30fps / 20초 세로 쇼츠
- 움직이는 배경(파티클·그리드·글로우 펄스) + 캔들/상승 차트 애니메이션
- 숫자 카운트업, 네온 글로우 텍스트, 슬라이드 아이콘 카드
- Pillow로 프레임을 그려 ffmpeg(rawvideo stdin)로 인코딩
- 오디오는 assets/score_ep1.m4a (시네마틱 스코어)

사용법:  python3 scripts/build_ep1.py
결과:    shorts_ep1/1억으로20억_1화_shorts.mp4
"""
import os
import math
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ----------------------------------------------------------------------------
# 설정
# ----------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "fonts")
OUT_DIR = os.path.join(ROOT, "shorts_ep1")
ASSET_DIR = os.path.join(ROOT, "assets")
SCORE = os.path.join(ASSET_DIR, "score_ep1.m4a")
OUT_MP4 = os.path.join(OUT_DIR, "1억으로20억_1화_shorts.mp4")

W, H = 1080, 1920
FPS = 30
DURATION = 20.0
N_FRAMES = int(round(DURATION * FPS))

BG_TOP = (14, 16, 22)
BG_BOT = (6, 7, 10)
GOLD = (245, 197, 24)
GREEN = (46, 204, 113)
RED = (231, 76, 60)
WHITE = (238, 240, 245)
GREY = (150, 156, 168)
INK = (10, 11, 14)

# ----------------------------------------------------------------------------
# 폰트
# ----------------------------------------------------------------------------
_FONT_CACHE = {}
_WEIGHTS = {
    "black": "Pretendard-Black.ttf",
    "extrabold": "Pretendard-ExtraBold.ttf",
    "bold": "Pretendard-Bold.ttf",
    "semibold": "Pretendard-SemiBold.ttf",
    "medium": "Pretendard-Medium.ttf",
}


def font(size, weight="bold"):
    key = (size, weight)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(
            os.path.join(FONT_DIR, _WEIGHTS[weight]), size)
    return _FONT_CACHE[key]


# ----------------------------------------------------------------------------
# 이징 / 유틸
# ----------------------------------------------------------------------------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_out_back(t):
    t = clamp(t)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_in_out(t):
    t = clamp(t)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def lerp(a, b, t):
    return a + (b - a) * t


def seg_alpha(local_t, dur, fade_in=0.3, fade_out=0.28):
    a_in = clamp(local_t / fade_in) if fade_in > 0 else 1.0
    a_out = clamp((dur - local_t) / fade_out) if fade_out > 0 else 1.0
    return ease_in_out(a_in) * ease_in_out(a_out)


def rgba(color, a):
    return (color[0], color[1], color[2], int(round(255 * clamp(a))))


def mix(c1, c2, t):
    return tuple(int(round(lerp(c1[i], c2[i], t))) for i in range(3))


# ----------------------------------------------------------------------------
# 정적 배경 (numpy, 1회 생성)
# ----------------------------------------------------------------------------
def build_background():
    ys = np.linspace(0, 1, H)[:, None]
    grad = (np.array(BG_TOP, np.float32)[None, None, :] * (1 - ys[..., None])
            + np.array(BG_BOT, np.float32)[None, None, :] * ys[..., None])
    bg = np.repeat(grad, W, axis=1)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dv = np.sqrt((xx - W / 2) ** 2 + (yy - H / 2) ** 2) / (0.5 * math.hypot(W, H))
    vig = np.clip(1 - 0.95 * dv ** 2.2, 0.0, 1.0)
    bg *= vig[..., None]
    rng = np.random.default_rng(42)
    bg += rng.normal(0, 2.6, size=(H, W, 1)).astype(np.float32)
    return Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


_BG = None


def base_frame():
    global _BG
    if _BG is None:
        _BG = build_background()
    return _BG.copy()


# ----------------------------------------------------------------------------
# 움직이는 배경 FX (매 프레임)
# ----------------------------------------------------------------------------
_PARTS = None


def _particles():
    global _PARTS
    if _PARTS is None:
        rng = np.random.default_rng(7)
        n = 46
        _PARTS = [dict(
            x=rng.uniform(0, W),
            y=rng.uniform(0, H),
            r=rng.uniform(1.5, 5.0),
            spd=rng.uniform(10, 42),           # px/s 상승
            drift=rng.uniform(-8, 8),
            ph=rng.uniform(0, math.tau),
            a=rng.uniform(0.05, 0.22),
        ) for _ in range(n)]
    return _PARTS


def draw_bg_fx(t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # 스크롤 그리드 (아주 옅게)
    gstep = 150
    off = int((t * 14) % gstep)
    for x in range(-off, W + gstep, gstep):
        d.line([(x, 0), (x, H)], fill=rgba(GREY, 0.035), width=1)
    voff = int((t * 10) % gstep)
    for y in range(-voff, H + gstep, gstep):
        d.line([(0, y), (W, y)], fill=rgba(GREY, 0.035), width=1)

    # 떠다니는 금빛 파티클
    for p in _particles():
        y = (p["y"] - t * p["spd"]) % (H + 40) - 20
        x = (p["x"] + math.sin(t * 0.6 + p["ph"]) * p["drift"]) % W
        tw = 0.6 + 0.4 * math.sin(t * 1.3 + p["ph"])
        d.ellipse([x - p["r"], y - p["r"], x + p["r"], y + p["r"]],
                  fill=rgba(GOLD, p["a"] * tw))

    layer = layer.filter(ImageFilter.GaussianBlur(0.6))

    # 펄스하는 중앙 상단 글로우
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    pulse = 0.5 + 0.5 * math.sin(t * 1.1)
    gr = 360 + 40 * pulse
    gd.ellipse([W / 2 - gr, H * 0.32 - gr, W / 2 + gr, H * 0.32 + gr],
               fill=rgba(GOLD, 0.05 + 0.05 * pulse))
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    layer = Image.alpha_composite(glow, layer)
    return layer


# ----------------------------------------------------------------------------
# 글로우 텍스트 (네온 느낌) — sharp 레이어 + glow 레이어에 함께 그림
# ----------------------------------------------------------------------------
def glow_text(od, gd, xy, s, fnt, color, a=1.0, anchor="mm", glow_a=0.9,
              spacing=10, align="center", stroke=0):
    gd.text(xy, s, font=fnt, fill=rgba(color, a * glow_a), anchor=anchor,
            spacing=spacing, align=align)
    od.text(xy, s, font=fnt, fill=rgba(color, a), anchor=anchor, spacing=spacing,
            align=align, stroke_width=stroke,
            stroke_fill=rgba(INK, a) if stroke else None)


def text_center(d, cx, y, s, fnt, color, a=1.0, anchor="mm", spacing=10,
                align="center", stroke=0, stroke_fill=INK):
    d.text((cx, y), s, font=fnt, fill=rgba(color, a), anchor=anchor,
           spacing=spacing, align=align, stroke_width=stroke,
           stroke_fill=rgba(stroke_fill, a) if stroke else None)


def measure(d, s, fnt, spacing=10):
    bb = d.multiline_textbbox((0, 0), s, font=fnt, spacing=spacing, anchor="la")
    return bb[2] - bb[0], bb[3] - bb[1]


def pill(d, cx, cy, w, h, fill, a=1.0, radius=None):
    radius = radius if radius is not None else h // 2
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2],
                        radius=radius, fill=rgba(fill, a))


def kicker(d, cx, y, label, a=1.0, color=GOLD):
    spaced = "  ".join(list(label.replace(" ", "")))
    text_center(d, cx, y, spaced, font(34, "bold"), color, a)


def caption(d, lines, a=1.0, y_base=1500):
    fnt = font(52, "semibold")
    txt = "\n".join(lines)
    tw, th = measure(d, txt, fnt, spacing=14)
    pill(d, W / 2, y_base, tw + 88, th + 60, (0, 0, 0), a * 0.5, radius=28)
    text_center(d, W / 2, y_base, txt, fnt, WHITE, a, spacing=14)


def disclaimer(d, a=1.0):
    text_center(d, W / 2, 1858, "※ 개인 기록용 · 투자 권유 아님",
                font(26, "medium"), GREY, a * 0.7)


def progress_bar(d, t):
    p = clamp(t / DURATION)
    y = 90
    d.rounded_rectangle([60, y, W - 60, y + 6], radius=3, fill=rgba(GREY, 0.18))
    d.rounded_rectangle([60, y, 60 + (W - 120) * p, y + 6], radius=3,
                        fill=rgba(GOLD, 0.9))


# ----------------------------------------------------------------------------
# 그래픽: 캔들차트 / 상승 라인 / 아이콘
# ----------------------------------------------------------------------------
_CANDLES = None


def _candle_series(n=26, seed=11):
    global _CANDLES
    if _CANDLES is None:
        rng = np.random.default_rng(seed)
        price = 100.0
        out = []
        for i in range(n):
            drift = 1.8 + i * 0.15                     # 우상향 경향
            o = price
            c = o + rng.normal(drift, 7)
            hi = max(o, c) + abs(rng.normal(0, 4))
            lo = min(o, c) - abs(rng.normal(0, 4))
            out.append((o, hi, lo, c))
            price = c
        _CANDLES = out
    return _CANDLES


def draw_candles(od, area, t_reveal, a=1.0):
    """area=(x0,y0,x1,y1). t_reveal 0~1 로 왼쪽부터 등장."""
    x0, y0, x1, y1 = area
    series = _candle_series()
    n = len(series)
    lo = min(s[2] for s in series)
    hi = max(s[1] for s in series)
    rng = hi - lo

    def py(v):
        return y1 - (v - lo) / rng * (y1 - y0)

    cw = (x1 - x0) / n
    shown = t_reveal * n
    for i, (o, h, l, c) in enumerate(series):
        ap = clamp(shown - i)
        if ap <= 0:
            break
        cx = x0 + cw * (i + 0.5)
        up = c >= o
        col = GREEN if up else RED
        ca = a * ap * 0.5
        od.line([(cx, py(h)), (cx, py(l))], fill=rgba(col, ca), width=2)
        bt, bb = py(max(o, c)), py(min(o, c))
        if bb - bt < 2:
            bb = bt + 2
        od.rectangle([cx - cw * 0.28, bt, cx + cw * 0.28, bb], fill=rgba(col, ca))


def draw_growth(od, gd, area, progress, a=1.0, label_end=None):
    """1억→20억 상승 곡선. progress 0~1."""
    x0, y0, x1, y1 = area
    pts_src = [(0.00, 0.06), (0.14, 0.10), (0.28, 0.08), (0.42, 0.20),
               (0.55, 0.30), (0.68, 0.46), (0.80, 0.64), (0.90, 0.82),
               (1.00, 1.00)]
    full = [(x0 + px * (x1 - x0), y1 - py * (y1 - y0)) for px, py in pts_src]
    # progress 까지 보간
    seg = progress * (len(full) - 1)
    k = int(seg)
    line = full[:k + 1]
    if k < len(full) - 1:
        f = seg - k
        ax, ay = full[k]
        bx, by = full[k + 1]
        line.append((lerp(ax, bx, f), lerp(ay, by, f)))
    if len(line) >= 2:
        # 아래 면적 글로우
        poly = line + [(line[-1][0], y1), (x0, y1)]
        gd.polygon(poly, fill=rgba(GOLD, a * 0.10))
        gd.line(line, fill=rgba(GOLD, a * 0.9), width=10, joint="curve")
        od.line(line, fill=rgba(GOLD, a), width=7, joint="curve")
        ex, ey = line[-1]
        od.ellipse([ex - 13, ey - 13, ex + 13, ey + 13], fill=rgba(WHITE, a))
        gd.ellipse([ex - 22, ey - 22, ex + 22, ey + 22], fill=rgba(GOLD, a))
        if label_end and progress > 0.08:
            text_center(od, ex, ey - 54, label_end, font(60, "black"), GOLD, a,
                        anchor="mm", stroke=2)


def icon(od, kind, cx, cy, r, color, a=1.0):
    w = max(3, int(r * 0.13))
    if kind == "target":
        for rr, fa in [(r, 0.9), (r * 0.62, 0.9), (r * 0.26, 1.0)]:
            od.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                       outline=rgba(color, a * fa), width=w)
    elif kind == "search":
        rr = r * 0.66
        ox, oy = cx - r * 0.18, cy - r * 0.18
        od.ellipse([ox - rr, oy - rr, ox + rr, oy + rr],
                   outline=rgba(color, a), width=w)
        od.line([(ox + rr * 0.7, oy + rr * 0.7),
                 (cx + r * 0.72, cy + r * 0.72)], fill=rgba(color, a), width=w + 2)
    elif kind == "work":  # 월급 말고 부업 = 상승 막대
        bw = r * 0.42
        xs = [cx - r * 0.72, cx - r * 0.15, cx + r * 0.42]
        hs = [r * 0.6, r * 1.0, r * 1.5]
        for x, hh in zip(xs, hs):
            od.rounded_rectangle([x, cy + r - hh, x + bw, cy + r],
                                 radius=6, fill=rgba(color, a))
        od.line([(xs[0], cy + r - hs[0]), (xs[1], cy + r - hs[1]),
                 (xs[2], cy + r - hs[2])], fill=rgba(WHITE, a), width=w)


# ----------------------------------------------------------------------------
# 씬들  (각 씬: od=sharp, gd=glow)
# ----------------------------------------------------------------------------
def scene_hero(od, gd, t, lt, dur):
    a = seg_alpha(lt, dur, fade_in=0.28, fade_out=0.25)
    kicker(od, W / 2, 360, "전 재산 공개", a)

    # 배경 상승곡선 (은은하게)
    draw_growth(od, gd, (120, 980, W - 120, 1360),
                ease_out_cubic(clamp(lt / 1.4)), a * 0.45)

    y = lerp(760, 690, ease_out_cubic(clamp(lt / 0.6)))
    f_big = font(220, "black")
    f_arrow = font(110, "black")
    # 20억 카운트업
    val = int(round(lerp(1, 20, ease_out_cubic(clamp((lt - 0.35) / 1.1)))))
    s1, sa, s2 = "1억", "→", f"{val}억"
    w1, _ = measure(od, s1, f_big)
    wa, _ = measure(od, sa, f_arrow)
    w2, _ = measure(od, s2, f_big)
    gap = 40
    total = w1 + gap + wa + gap + w2
    x = W / 2 - total / 2
    glow_text(od, gd, (x + w1 / 2, y), s1, f_big, WHITE, a, stroke=3, glow_a=0.4)
    aa = clamp((lt - 0.25) / 0.4)
    text_center(od, x + w1 + gap + wa / 2, y, sa, f_arrow, GOLD, a * aa)
    pop = clamp((lt - 0.4) / 0.5)
    sc = lerp(0.7, 1.0, ease_out_back(pop))
    f_big2 = font(int(220 * sc), "black")
    glow_text(od, gd, (x + w1 + gap + wa + gap + w2 / 2, y), s2, f_big2, GOLD,
              a * pop, stroke=3, glow_a=1.0)

    text_center(od, W / 2, y + 185, "5년 안에, 진짜로.", font(46, "semibold"),
                GREY, a)
    caption(od, ["제 전 재산 1억입니다.", "5년 뒤 20억 만들게요."], a)


def scene_math(od, gd, t, lt, dur):
    a = seg_alpha(lt, dur)
    kicker(od, W / 2, 358, "계산해봤다", a)
    text_center(od, W / 2, 500, "매년 필요한 수익률", font(84, "medium"), GREY, a)

    # +82% 카운트업 + 글로우
    pct = int(round(lerp(0, 82, ease_out_cubic(clamp(lt / 1.0)))))
    pop = ease_out_back(clamp(lt / 0.6))
    f82 = font(int(290 * lerp(0.75, 1.0, pop)), "black")
    glow_text(od, gd, (W / 2, 710), f"+{pct}%", f82, GOLD, a * clamp(lt / 0.35),
              stroke=3, glow_a=1.0)

    # 비교 바
    bar_x, bar_w = 170, W - 340
    base_y, bar_h, bg_gap = 1100, 86, 210
    grow = ease_out_cubic(clamp((lt - 0.5) / 1.1))

    def comp_bar(label, p, mx, color, yy):
        frac = (p / mx) * grow
        d_rr = [bar_x, yy, bar_x + bar_w, yy + bar_h]
        od.rounded_rectangle(d_rr, radius=bar_h // 2, fill=rgba((255, 255, 255), a * 0.07))
        ww = max(bar_h, bar_w * frac)
        od.rounded_rectangle([bar_x, yy, bar_x + ww, yy + bar_h],
                             radius=bar_h // 2, fill=rgba(color, a))
        text_center(od, bar_x + 8, yy - 46, label, font(46, "bold"), GREY, a, anchor="lm")
        vf = font(54, "black")
        val = f"+{int(round(p * grow))}%"
        if frac >= 0.5:
            text_center(od, bar_x + ww - 28, yy + bar_h / 2, val, vf, INK, a, anchor="rm")
        else:
            text_center(od, bar_x + ww + 28, yy + bar_h / 2, val, vf, color, a, anchor="lm")

    comp_bar("워런 버핏 (장기 평균)", 20, 82, GREY, base_y)
    comp_bar("나 (목표)", 82, 82, GOLD, base_y + bg_gap)
    caption(od, ["계산해보니 연 82% 수익이 필요합니다.", "버핏도 20%인데."], a)


def scene_buffett(od, gd, t, lt, dur):
    a = seg_alpha(lt, dur)
    kicker(od, W / 2, 358, "근데 버핏이", a)

    # 배경 캔들차트 (계속 흐름)
    draw_candles(od, (130, 1180, W - 130, 1420),
                 ease_out_cubic(clamp(lt / 1.6)), a)

    text_center(od, W / 2, 560, "“", font(200, "black"), GOLD, a * 0.45)
    y1 = lerp(760, 720, ease_out_cubic(clamp(lt / 0.6)))
    glow_text(od, gd, (W / 2, y1), "돈이 적을 때가", font(90, "black"), WHITE,
              a * clamp(lt / 0.45), glow_a=0.35)
    glow_text(od, gd, (W / 2, y1 + 130), "제일 빠르다", font(90, "black"), GOLD,
              a * clamp((lt - 0.25) / 0.45), stroke=2, glow_a=0.9)
    text_center(od, W / 2, y1 + 290, "— 워런 버핏", font(46, "semibold"), GREY,
                a * clamp((lt - 0.6) / 0.6))
    caption(od, ["근데 버핏이 말했어요.", "돈 적을 때가 제일 빠르다고."], a)


def scene_plan(od, gd, t, lt, dur):
    a = seg_alpha(lt, dur, fade_in=0.32, fade_out=0.32)
    kicker(od, W / 2, 358, "그래서 전략", a)
    items = [
        ("01", "몰빵", "분산 대신 집중", GOLD, "target"),
        ("02", "아무도 안 보는 종목", "소외된 곳에 기회", GREEN, "search"),
        ("03", "월급 말고 부업", "현금흐름을 늘린다", WHITE, "work"),
    ]
    start_y, row_h = 640, 330
    for i, (num, title, desc, color, ic) in enumerate(items):
        ap = clamp((lt - (0.45 + i * 0.95)) / 0.6)
        if ap <= 0:
            continue
        ea = ease_out_cubic(ap)
        x_off = lerp(-90, 0, ea)
        ry = start_y + i * row_h
        ia = a * ap
        # 아이콘 타일
        tile = 150
        od.rounded_rectangle([140 + x_off, ry - tile / 2, 140 + x_off + tile,
                              ry + tile / 2], radius=30, fill=rgba(color, ia * 0.14))
        icon(od, ic, 140 + x_off + tile / 2, ry, tile * 0.3, color, ia)
        glow_text(od, gd, (330 + x_off, ry - 26), title, font(82, "black"),
                  WHITE, ia, anchor="lm", glow_a=0.3)
        text_center(od, 332 + x_off, ry + 52, desc, font(42, "medium"), GREY,
                    ia, anchor="lm")
    caption(od, ["몰빵. 아무도 안 보는 종목.", "그리고 월급 말고 부업."], a)


def scene_promise(od, gd, t, lt, dur):
    a = seg_alpha(lt, dur, fade_in=0.28, fade_out=0.45)
    kicker(od, W / 2, 356, "약속", a)

    # 20억 도달 상승곡선 (하이라이트)
    draw_growth(od, gd, (150, 760, W - 150, 1040),
                ease_out_cubic(clamp(lt / 1.3)), a,
                label_end="20억" if lt > 1.1 else None)

    glow_text(od, gd, (W / 2, 1180), "성공해도 공개", font(118, "black"), WHITE,
              a * clamp(lt / 0.4), stroke=2, glow_a=0.3)
    glow_text(od, gd, (W / 2, 1320), "망해도 공개", font(118, "black"), GOLD,
              a * clamp((lt - 0.25) / 0.4), stroke=2, glow_a=0.9)

    cta_a = a * clamp((lt - 0.7) / 0.6)
    pulse = 1 + 0.03 * math.sin(lt * 7)
    pw = 760 * pulse
    pill(od, W / 2, 1520, pw, 112, GOLD, cta_a, radius=56)
    text_center(od, W / 2, 1520, "2화 = 첫 종목 공개", font(56, "extrabold"),
                INK, cta_a)
    caption(od, ["성공하면 전부 공개,", "망해도 전부 공개."], a, y_base=1680)


SCENES = [
    (0.0, 2.0, scene_hero),
    (2.0, 6.0, scene_math),
    (6.0, 10.0, scene_buffett),
    (10.0, 17.0, scene_plan),
    (17.0, 20.0, scene_promise),
]


def render_frame(idx):
    t = idx / FPS
    frame = base_frame()
    frame = Image.alpha_composite(frame, draw_bg_fx(t))

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    od = ImageDraw.Draw(ov)
    for (s, e, fn) in SCENES:
        if s <= t < e or (e == DURATION and t >= s):
            fn(od, gd, t, t - s, e - s)
            break

    glow = glow.filter(ImageFilter.GaussianBlur(22))
    frame = Image.alpha_composite(frame, glow)
    frame = Image.alpha_composite(frame, ov)

    d = ImageDraw.Draw(frame)
    progress_bar(d, t)
    disclaimer(d, 1.0)
    return frame.convert("RGB")


# ----------------------------------------------------------------------------
# 인코딩
# ----------------------------------------------------------------------------
def main():
    assert os.path.exists(SCORE), f"오디오 에셋 없음: {SCORE}"
    tmp_video = os.path.join(OUT_DIR, "_video_only.mp4")
    ff = ["ffmpeg", "-nostdin", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an",
          "-c:v", "libx264", "-preset", "medium", "-crf", "18",
          "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp_video]
    print(f"[1/3] 렌더링+인코딩 ({N_FRAMES} frames)...")
    proc = subprocess.Popen(ff, stdin=subprocess.PIPE)
    for i in range(N_FRAMES):
        proc.stdin.write(render_frame(i).tobytes())
        if i % 60 == 0:
            print(f"      frame {i}/{N_FRAMES}")
    proc.stdin.close()
    assert proc.wait() == 0, "ffmpeg video 실패"

    print("[2/3] 스코어 합치기...")
    muxed = os.path.join(OUT_DIR, "_muxed.mp4")
    assert subprocess.call([
        "ffmpeg", "-nostdin", "-y", "-i", tmp_video, "-i", SCORE,
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
        "-b:a", "192k", "-shortest", "-movflags", "+faststart", muxed]) == 0, "mux 실패"

    print("[3/3] 교체...")
    os.replace(muxed, OUT_MP4)
    if os.path.exists(tmp_video):
        os.remove(tmp_video)
    print(f"완료 → {OUT_MP4}")


if __name__ == "__main__":
    main()
