#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1억으로 20억 만들기 — 1화 쇼츠 영상 생성기 (재현형)

- 해상도 1080x1920 / 30fps / 20초 세로 쇼츠
- Pillow로 프레임을 그려 ffmpeg(rawvideo stdin)로 인코딩
- 오디오는 기존 1화 mp4의 시네마틱 스코어를 재활용
- 한글 폰트: fonts/Pretendard-*.ttf

사용법:
    python3 scripts/build_ep1.py
결과:
    shorts_ep1/1억으로20억_1화_shorts.mp4
"""
import os
import math
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ----------------------------------------------------------------------------
# 설정
# ----------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "fonts")
OUT_DIR = os.path.join(ROOT, "shorts_ep1")
ASSET_DIR = os.path.join(ROOT, "assets")
SCORE = os.path.join(ASSET_DIR, "score_ep1.m4a")               # 오디오(스코어) 에셋
OUT_MP4 = os.path.join(OUT_DIR, "1억으로20억_1화_shorts.mp4")   # 최종 출력

W, H = 1080, 1920
FPS = 30
DURATION = 20.0
N_FRAMES = int(round(DURATION * FPS))

# 색상 (어둡고 시네마틱 + 골드 액센트)
BG_TOP = (14, 16, 22)
BG_BOT = (6, 7, 10)
GOLD = (245, 197, 24)        # 돈/버핏 액센트
GREEN = (46, 204, 113)       # 성장
RED = (231, 76, 60)          # 리스크
WHITE = (238, 240, 245)
GREY = (150, 156, 168)
INK = (10, 11, 14)

# ----------------------------------------------------------------------------
# 폰트 로더
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
        path = os.path.join(FONT_DIR, _WEIGHTS[weight])
        _FONT_CACHE[key] = ImageFont.truetype(path, size)
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


def seg_alpha(local_t, dur, fade_in=0.35, fade_out=0.3):
    """씬 내부에서 콘텐츠의 전체 투명도(0~1) — 깔끔한 컷 인/아웃."""
    a_in = clamp(local_t / fade_in) if fade_in > 0 else 1.0
    a_out = clamp((dur - local_t) / fade_out) if fade_out > 0 else 1.0
    return ease_in_out(a_in) * ease_in_out(a_out)


def rgba(color, a):
    return (color[0], color[1], color[2], int(round(255 * clamp(a))))


# ----------------------------------------------------------------------------
# 배경 (정적 — numpy로 1회 생성)
# ----------------------------------------------------------------------------
def build_background():
    ys = np.linspace(0, 1, H)[:, None]
    top = np.array(BG_TOP, dtype=np.float32)
    bot = np.array(BG_BOT, dtype=np.float32)
    grad = top[None, None, :] * (1 - ys[..., None]) + bot[None, None, :] * ys[..., None]
    bg = np.repeat(grad, W, axis=1)  # (H, W, 3)

    # 중앙 상단의 부드러운 골드 글로우
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W * 0.5, H * 0.34
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (H * 0.55)
    glow = np.clip(1 - d, 0, 1) ** 2.2
    bg[..., 0] += glow * 26
    bg[..., 1] += glow * 21
    bg[..., 2] += glow * 6

    # 비네트
    dv = np.sqrt((xx - W / 2) ** 2 + (yy - H / 2) ** 2) / (0.5 * math.hypot(W, H))
    vig = np.clip(1 - 0.9 * dv ** 2.2, 0.0, 1.0)
    bg *= vig[..., None]

    # 아주 미세한 필름 그레인(정적)
    rng = np.random.default_rng(42)
    grain = rng.normal(0, 3.0, size=(H, W, 1)).astype(np.float32)
    bg += grain

    bg = np.clip(bg, 0, 255).astype(np.uint8)
    return Image.fromarray(bg, "RGB")


_BG = None


def bg_frame():
    global _BG
    if _BG is None:
        _BG = build_background()
    return _BG.copy()


# ----------------------------------------------------------------------------
# 그리기 헬퍼 (모두 RGBA 오버레이에 그린 뒤 합성)
# ----------------------------------------------------------------------------
def text_center(draw, cx, y, s, fnt, color, a=1.0, anchor="mm", spacing=10,
                align="center", stroke=0, stroke_fill=INK):
    draw.text((cx, y), s, font=fnt, fill=rgba(color, a), anchor=anchor,
              spacing=spacing, align=align, stroke_width=stroke,
              stroke_fill=rgba(stroke_fill, a) if stroke else None)


def measure(draw, s, fnt, spacing=10):
    bb = draw.multiline_textbbox((0, 0), s, font=fnt, spacing=spacing, anchor="la")
    return bb[2] - bb[0], bb[3] - bb[1]


def pill(draw, cx, cy, w, h, fill, a=1.0, radius=None):
    radius = radius if radius is not None else h // 2
    x0, y0 = cx - w / 2, cy - h / 2
    draw.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=radius, fill=rgba(fill, a))


def kicker(draw, cx, y, label, a=1.0, color=GOLD):
    """상단 작은 라벨 (· 로 자간)"""
    spaced = "  ".join(list(label.replace(" ", "")))
    fnt = font(34, "bold")
    text_center(draw, cx, y, spaced, fnt, color, a)


def caption(draw, lines, a=1.0, y_base=1500):
    """하단 내레이션 자막 — 알약 배경 + 흰 글씨 (쇼츠 UI 피해서 배치)"""
    fnt = font(52, "semibold")
    txt = "\n".join(lines)
    tw, th = measure(draw, txt, fnt, spacing=14)
    pad_x, pad_y = 44, 30
    pill(draw, W / 2, y_base, tw + pad_x * 2, th + pad_y * 2, (0, 0, 0), a * 0.5,
         radius=28)
    text_center(draw, W / 2, y_base, txt, fnt, WHITE, a, spacing=14)


def disclaimer(draw, a=1.0):
    fnt = font(26, "medium")
    text_center(draw, W / 2, 1858, "※ 개인 기록용 · 투자 권유 아님", fnt, GREY, a * 0.7)


def progress_bar(draw, t):
    """상단 아주 얇은 진행 바 (에디토리얼 감성)"""
    p = clamp(t / DURATION)
    y = 90
    draw.rounded_rectangle([60, y, W - 60, y + 6], radius=3, fill=rgba(GREY, 0.18))
    draw.rounded_rectangle([60, y, 60 + (W - 120) * p, y + 6], radius=3,
                           fill=rgba(GOLD, 0.9))


# ----------------------------------------------------------------------------
# 씬들
# ----------------------------------------------------------------------------
def scene_hero(ov, t, lt, dur):
    """0-2s: 1억 → 20억 히어로"""
    d = ImageDraw.Draw(ov)
    a = seg_alpha(lt, dur, fade_in=0.3, fade_out=0.25)
    kicker(d, W / 2, 360, "전 재산 공개", a)

    # "1억" → "20억"
    rise = ease_out_back(lt / 0.7)
    y = lerp(900, 820, ease_out_cubic(lt / 0.6))
    f_big = font(230, "black")
    f_arrow = font(120, "black")
    # 1억 (왼쪽), 화살표, 20억 (오른쪽) — 가로 배치
    s1, s2, sa = "1억", "20억", "→"
    w1, _ = measure(d, s1, f_big)
    w2, _ = measure(d, s2, f_big)
    wa, _ = measure(d, sa, f_arrow)
    gap = 44
    total = w1 + gap + wa + gap + w2
    x = W / 2 - total / 2
    text_center(d, x + w1 / 2, y, s1, f_big, WHITE, a, stroke=3)
    ax = x + w1 + gap + wa / 2
    text_center(d, ax, y, sa, f_arrow, GOLD, a * clamp((lt - 0.3) / 0.4))
    # 20억은 골드로 "팝"
    pop = clamp((lt - 0.45) / 0.5)
    sc = lerp(0.6, 1.0, ease_out_back(pop))
    f_big2 = font(int(230 * sc), "black")
    text_center(d, x + w1 + gap + wa + gap + w2 / 2, y, s2, f_big2, GOLD,
                a * pop, stroke=3)

    sub = font(46, "semibold")
    text_center(d, W / 2, y + 190, "5년 안에, 진짜로.", sub, GREY, a)
    caption(d, ["제 전 재산 1억입니다.", "5년 뒤 20억 만들게요."], a)


def scene_math(ov, t, lt, dur):
    """2-6s: 연 +82% vs 버핏 +20% 비교 바"""
    d = ImageDraw.Draw(ov)
    a = seg_alpha(lt, dur)
    kicker(d, W / 2, 360, "계산해봤다", a)

    big = font(96, "medium")
    text_center(d, W / 2, 520, "매년 필요한 수익률", big, GREY, a)
    f82 = font(300, "black")
    pop = ease_out_back(clamp(lt / 0.7))
    f82s = font(int(300 * lerp(0.7, 1.0, pop)), "black")
    text_center(d, W / 2, 720, "+82%", f82s, GOLD, a * clamp(lt / 0.4), stroke=3)

    # 비교 바
    bar_x = 170
    bar_w = W - bar_x * 2
    base_y = 1100
    bar_h = 86
    gap = 210
    grow = ease_out_cubic(clamp((lt - 0.5) / 1.1))

    def comp_bar(label, pct, maxpct, color, yy, val_a):
        frac = (pct / maxpct) * grow
        d.rounded_rectangle([bar_x, yy, bar_x + bar_w, yy + bar_h], radius=bar_h // 2,
                            fill=rgba((255, 255, 255), a * 0.07))
        ww = max(bar_h, bar_w * frac)
        d.rounded_rectangle([bar_x, yy, bar_x + ww, yy + bar_h], radius=bar_h // 2,
                            fill=rgba(color, a))
        lf = font(46, "bold")
        text_center(d, bar_x + 8, yy - 46, label, lf, GREY, a, anchor="lm")
        vf = font(54, "black")
        val = f"+{int(round(pct * grow))}%"
        # 채워진 막대가 충분히 길면 안쪽(잉크), 짧으면 바깥 오른쪽(막대 색)
        if frac >= 0.5:
            text_center(d, bar_x + ww - 28, yy + bar_h / 2, val, vf, INK,
                        a * val_a, anchor="rm")
        else:
            text_center(d, bar_x + ww + 28, yy + bar_h / 2, val, vf, color,
                        a * val_a, anchor="lm")

    comp_bar("워런 버핏 (장기 평균)", 20, 82, GREY, base_y, grow)
    comp_bar("나 (목표)", 82, 82, GOLD, base_y + gap, grow)

    caption(d, ["계산해보니 연 82% 수익이 필요합니다.", "버핏도 20%인데."], a)


def scene_buffett(ov, t, lt, dur):
    """6-10s: 버핏의 반전"""
    d = ImageDraw.Draw(ov)
    a = seg_alpha(lt, dur)
    kicker(d, W / 2, 360, "근데 버핏이", a)

    q = font(90, "black")
    y1 = lerp(760, 720, ease_out_cubic(clamp(lt / 0.6)))
    mark = font(200, "black")
    text_center(d, W / 2, 560, "“", mark, rgba(GOLD, 1)[:3], a * 0.5)
    text_center(d, W / 2, y1, "돈이 적을 때가", q, WHITE, a * clamp(lt / 0.45))
    text_center(d, W / 2, y1 + 130, "제일 빠르다", q, GOLD,
                a * clamp((lt - 0.25) / 0.45), stroke=2)

    attr = font(46, "semibold")
    text_center(d, W / 2, y1 + 300, "— 워런 버핏", attr, GREY,
                a * clamp((lt - 0.6) / 0.6))

    caption(d, ["근데 버핏이 말했어요.", "돈 적을 때가 제일 빠르다고."], a)


def scene_plan(ov, t, lt, dur):
    """10-17s: 전략 3가지 스태거"""
    d = ImageDraw.Draw(ov)
    a = seg_alpha(lt, dur, fade_in=0.35, fade_out=0.35)
    kicker(d, W / 2, 360, "그래서 전략", a)

    items = [
        ("01", "몰빵", "분산 대신 집중", GOLD),
        ("02", "아무도 안 보는 종목", "소외된 곳에 기회", GREEN),
        ("03", "월급 말고 부업", "현금흐름을 늘린다", WHITE),
    ]
    start_y = 640
    row_h = 320
    for i, (num, title, desc, color) in enumerate(items):
        appear = clamp((lt - (0.5 + i * 0.9)) / 0.6)
        if appear <= 0:
            continue
        ea = ease_out_cubic(appear)
        x_off = lerp(-70, 0, ea)
        ry = start_y + i * row_h
        ia = a * appear

        # 번호 뱃지
        nf = font(60, "black")
        d.rounded_rectangle([150 + x_off, ry - 70, 150 + x_off + 120, ry + 70],
                            radius=28, fill=rgba(color, ia * 0.18))
        text_center(d, 150 + x_off + 60, ry, num, nf, color, ia)

        tf = font(84, "black")
        text_center(d, 310 + x_off, ry - 26, title, tf, WHITE, ia, anchor="lm")
        df = font(42, "medium")
        text_center(d, 312 + x_off, ry + 52, desc, df, GREY, ia, anchor="lm")

    caption(d, ["몰빵. 아무도 안 보는 종목.", "그리고 월급 말고 부업."], a)


def scene_promise(ov, t, lt, dur):
    """17-20s: 약속 + CTA"""
    d = ImageDraw.Draw(ov)
    a = seg_alpha(lt, dur, fade_in=0.3, fade_out=0.45)
    kicker(d, W / 2, 360, "약속", a)

    bigf = font(128, "black")
    text_center(d, W / 2, 720, "성공해도 공개", bigf, WHITE,
                a * clamp(lt / 0.4), stroke=2)
    text_center(d, W / 2, 880, "망해도 공개", bigf, GOLD,
                a * clamp((lt - 0.25) / 0.4), stroke=2)

    # CTA 알약
    cta_a = a * clamp((lt - 0.7) / 0.6)
    pill(d, W / 2, 1120, 760, 112, GOLD, cta_a, radius=56)
    text_center(d, W / 2, 1120, "2화 = 첫 종목 공개", font(56, "extrabold"),
                INK, cta_a)
    text_center(d, W / 2, 1270, "구독하고 같이 지켜보기", font(46, "semibold"),
                GREY, cta_a)

    caption(d, ["성공하면 전부 공개,", "망해도 전부 공개."], a)


# 타임라인: (시작, 끝, 함수)
SCENES = [
    (0.0, 2.0, scene_hero),
    (2.0, 6.0, scene_math),
    (6.0, 10.0, scene_buffett),
    (10.0, 17.0, scene_plan),
    (17.0, 20.0, scene_promise),
]


def render_frame(idx):
    t = idx / FPS
    img = bg_frame()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for (s, e, fn) in SCENES:
        if s <= t < e or (e == DURATION and t >= s):
            fn(ov, t, t - s, e - s)
            break
    img = Image.alpha_composite(img.convert("RGBA"), ov)

    # 상시 요소
    d = ImageDraw.Draw(img)
    progress_bar(d, t)
    disclaimer(d, 1.0)
    return img.convert("RGB")


# ----------------------------------------------------------------------------
# 인코딩
# ----------------------------------------------------------------------------
def main():
    assert os.path.exists(SCORE), f"오디오 에셋 없음: {SCORE}"
    tmp_video = os.path.join(OUT_DIR, "_video_only.mp4")

    ff = [
        "ffmpeg", "-nostdin", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        tmp_video,
    ]
    print(f"[1/3] 프레임 렌더링 + 인코딩 ({N_FRAMES} frames)...")
    proc = subprocess.Popen(ff, stdin=subprocess.PIPE)
    for i in range(N_FRAMES):
        proc.stdin.write(render_frame(i).tobytes())
        if i % 60 == 0:
            print(f"      frame {i}/{N_FRAMES}")
    proc.stdin.close()
    rc = proc.wait()
    assert rc == 0, f"ffmpeg video 인코딩 실패 rc={rc}"

    print("[2/3] 스코어(오디오) 합치기...")
    muxed = os.path.join(OUT_DIR, "_muxed.mp4")
    mux = [
        "ffmpeg", "-nostdin", "-y",
        "-i", tmp_video,
        "-i", SCORE,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        muxed,
    ]
    rc = subprocess.call(mux)
    assert rc == 0, f"mux 실패 rc={rc}"

    print("[3/3] 최종 파일로 교체...")
    os.replace(muxed, OUT_MP4)
    if os.path.exists(tmp_video):
        os.remove(tmp_video)
    print(f"완료 → {OUT_MP4}")


if __name__ == "__main__":
    main()
