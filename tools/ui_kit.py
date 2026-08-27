# -*- coding: utf-8 -*-
"""UI 명세 도면을 그리는 부품 — `make_ui_spec.py` 가 쓴다.

## 디자인 방향 — 「차분한 골격 + 생생한 액센트」

Figma 2026 트렌드 13가지를 전부 쓰면 안 된다. 이것은 **공부 도구**이고
집중이 목적이며 텍스트(지문·선지)가 주인공이다.

| 취함 | 어떻게 |
|---|---|
| 대담한 타이포그래피 | 발문 20/700 대 메타 11/400 — **위계를 크게 벌린다** |
| 다크 모드 | 토큰을 두 벌로 둔다. 나중에 얹지 않는다 |
| 게임화 | 진도 링 · 연속일 · 정답률에만 |
| 모션 | 채점 순간과 문항 전환에만 |

| 버림 | 왜 |
|---|---|
| 3D·몰입형, 실험적 탐색 | 시험 앱에서 길을 잃으면 안 된다 |
| 생생한 배경색, 맥시멀리즘 | 지문을 못 읽는다. 색은 **액센트에만** |
| 뉴모피즘 | 대비가 낮아 접근성에 나쁘다 |

첫 판은 회색 상자에 각진 모서리였다. 와이어프레임으로는 맞지만
**이 이미지가 Build 의 입력**이라 그 톤이 그대로 결과가 된다.
그래서 목업 수준으로 올린다 — 테두리로 나누지 않고 여백과 그림자로 나눈다.
"""
from __future__ import annotations

W = 1600
FONT = "Pretendard, Malgun Gothic, 맑은 고딕, -apple-system, sans-serif"
MONO = "SF Mono, Consolas, D2Coding, monospace"

# ── 토큰 ─────────────────────────────────────────────────────────────
INK, MUTE, FAINT = "#0f172a", "#64748b", "#94a3b8"
LINE, HAIR = "#e2e8f0", "#f1f5f9"
BG, SURF = "#f6f7f9", "#ffffff"
ACC, ACC_BG, ACC_LN = "#6366f1", "#eef2ff", "#c7d2fe"
OK, OK_BG = "#0f7b4f", "#ecfdf5"
BAD, BAD_BG = "#c2334d", "#fff1f2"
WARN, WARN_BG = "#a45a12", "#fffbeb"
VIVID = "#5b21b6"          # 게임화 액센트 — 진도·연속일에만

R, RS = 16, 11
DEFS = (
    "<filter id='sh' x='-30%' y='-30%' width='160%' height='170%'>"
    "<feDropShadow dx='0' dy='1' stdDeviation='1' flood-opacity='.04'/>"
    "<feDropShadow dx='0' dy='8' stdDeviation='14' flood-opacity='.07'/></filter>"
    "<linearGradient id='pg' x1='0' y1='0' x2='1' y2='0'>"
    f"<stop offset='0' stop-color='{ACC}'/><stop offset='1' stop-color='{VIVID}'/>"
    "</linearGradient>"
    "<marker id='ah' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='6' "
    f"markerHeight='6' orient='auto-start-reverse'><path d='M0,0 L10,5 L0,10 z' "
    f"fill='{WARN}'/></marker>"
)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(s):
    out = []
    for i, part in enumerate(s.split("**")):
        if not part:
            continue
        out.append(f"<tspan font-weight='700' fill='{INK}'>{esc(part)}</tspan>"
                   if i % 2 else esc(part))
    return "".join(out)


def t(x, y, s, size=13, fill=INK, anchor="start", weight="400", font=None,
      ls=None):
    f = font or FONT
    sp = f" letter-spacing='{ls}'" if ls else ""
    return (f"<text x='{x}' y='{y}' font-family='{f}' font-size='{size}' "
            f"fill='{fill}' text-anchor='{anchor}' font-weight='{weight}'{sp}>"
            f"{_inline(s)}</text>")


def box(x, y, w, h, fill=SURF, stroke=None, r=RS, sw=1, dash=None, shadow=False):
    st = f" stroke='{stroke}' stroke-width='{sw}'" if stroke else ""
    d = f" stroke-dasharray='{dash}'" if dash else ""
    fx = " filter='url(#sh)'" if shadow else ""
    return (f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='{r}' "
            f"fill='{fill}'{st}{d}{fx}/>")


def card(x, y, w, h, title=None, sub=None, fill=SURF, shadow=True):
    o = [box(x, y, w, h, fill, None, R, shadow=shadow)]
    if title:
        o.append(t(x + 22, y + 34, title, 14, INK, weight="700"))
    if sub:
        o.append(t(x + 22, y + 55, sub, 11.5, FAINT))
    return "".join(o)


def zone(x, y, w, h, label, sub=None):
    """구획 — 점선으로만 표시하고 채우지 않는다."""
    o = [box(x, y, w, h, HAIR, LINE, RS, dash="5 4")]
    o.append(t(x + 16, y + 27, label, 12.5, MUTE, weight="700"))
    if sub:
        o.append(t(x + 16, y + 46, sub, 11, FAINT))
    return "".join(o)


def pill(x, y, label, w=None, fill=SURF, tc=INK, stroke=LINE, h=34, size=12.5):
    w = w or len(label) * 13 + 30
    st = stroke if fill == SURF else None
    return (box(x, y, w, h, fill, st, h / 2)
            + t(x + w / 2, y + h / 2 + 4.6, label, size, tc, "middle", "600")), w


def bar(x, y, w, pct, h=8, tone=None):
    """진도 막대 — 게임화 액센트."""
    return (box(x, y, w, h, HAIR, None, h / 2)
            + box(x, y, max(h, w * pct), h, tone or "url(#pg)", None, h / 2))


def ring(cx, cy, r, pct, label, sub=None):
    """진도 링 — 성취가 드러나는 곳에만 색을 쓴다."""
    import math
    c = 2 * math.pi * r
    o = [f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='{HAIR}' "
         f"stroke-width='9'/>",
         f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='url(#pg)' "
         f"stroke-width='9' stroke-linecap='round' stroke-dasharray='{c*pct:.1f} {c:.1f}' "
         f"transform='rotate(-90 {cx} {cy})'/>",
         t(cx, cy + 6, label, 26, INK, "middle", "700", MONO)]
    if sub:
        o.append(t(cx, cy + 26, sub, 11, FAINT, "middle"))
    return "".join(o)


def note(x, y, w, lines, tone=ACC):
    bg = {ACC: ACC_BG, WARN: WARN_BG, BAD: BAD_BG, OK: OK_BG}.get(tone, BG)
    h = 24 + len(lines) * 20
    o = [box(x, y, w, h, bg, None, RS),
         f"<rect x='{x}' y='{y+14}' width='3' height='{h-28}' rx='1.5' fill='{tone}'/>"]
    for i, ln in enumerate(lines):
        hd = ln.startswith("*")
        o.append(t(x + 18, y + 28 + i * 20, ln.lstrip("*"), 12,
                   tone if hd else MUTE, weight="700" if hd else "400"))
    return "".join(o), h


def arrow(x1, y1, x2, y2, tone=WARN):
    return (f"<path d='M{x1},{y1} L{x2},{y2}' stroke='{tone}' stroke-width='1.6' "
            f"marker-end='url(#ah)' fill='none'/>")


def head(title, subtitle, tag="NCS PASS · 웹 UI 명세"):
    return "".join([
        box(0, 0, W, 96, SURF, None, 0),
        f"<rect x='0' y='95' width='{W}' height='1' fill='{LINE}'/>",
        f"<rect x='44' y='32' width='5' height='32' rx='2.5' fill='url(#pg)'/>",
        t(64, 48, title, 22, INK, weight="700", ls="-.4"),
        t(64, 70, subtitle, 12.5, FAINT),
        t(W - 44, 58, tag, 12, FAINT, "end"),
    ])


def svg(body, h):
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{h}' "
            f"viewBox='0 0 {W} {h}'><defs>{DEFS}</defs>"
            f"<rect width='{W}' height='{h}' fill='{BG}'/>{body}</svg>")


def hline(x, y, w, color=None):
    """구분선 — 카드 안에서 머리말과 본문을 가른다."""
    return f"<rect x='{x}' y='{y}' width='{w}' height='1' fill='{color or LINE}'/>"


def dot(x, y, size=16, fill="url(#pg)"):
    """앱 마크 — 그라디언트 사각형."""
    return (f"<rect x='{x}' y='{y}' width='{size}' height='{size}' "
            f"rx='{size*0.3:.1f}' fill='{fill}'/>")
