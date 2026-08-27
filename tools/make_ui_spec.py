# -*- coding: utf-8 -*-
"""웹 UI 설명서를 SVG 로 그린다 — Google AI Studio Build 에 넣을 입력물.

## 왜 손으로 SVG 를 쓰나

2026년 지침이 한 점에서 일치한다 — 와이어프레임은 **UI 컴포넌트·접근성·
동작을 명시**해야 하고, 입력·토글·결과·로직에 각각 주석이 있어야 한다.
그림만 넣으면 모델이 빈칸을 자유롭게 채운다.

Excalidraw 는 손그림 톤이라 모델이 「스케치」로 읽고 자유도를 크게 준다.
여기서는 **치수와 상태를 그대로 따르게 하는 도면**이 필요하다. 그리고 이
저장소는 이미 인라인 SVG 로 문항의 도형을 그리므로 새 의존성이 들지 않는다.

**입력의 시각 품질이 곧 출력의 품질이다.** 첫 판을 회색 와이어프레임으로
그렸다가 「옛날 홈페이지 같다」는 지적을 받았다. 지금은 목업 수준으로 그린다 —
디자인 방향은 `ui_kit.py` 머리말에 적었다.

    python tools/make_ui_spec.py            # docs/ui/*.svg + *.png
    python tools/make_ui_spec.py --svg      # SVG 만 (Chrome 없이)
    python tools/make_ui_spec.py --only 01-layout
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "ui"
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from tools.ui_kit import (  # noqa: E402
    ACC, ACC_BG, BAD, BAD_BG, FAINT, HAIR, INK, LINE, MONO, MUTE, OK, OK_BG,
    R, RS, SURF, VIVID, W, WARN, WARN_BG,
    arrow, bar, box, card, dot, head, hline, note, pill, ring, svg, t,
    zone,
)


def s1_layout() -> str:
    o = [head("레이아웃 골격", "브레이크포인트 3단계 · 3단 구성 · 상주 머리말")]
    X, Y, BW, BH = 44, 128, 1000, 470

    o.append(t(X, Y - 14, "데스크톱  ≥ 1280", 13, MUTE, weight="700"))
    o.append(t(X + 170, Y - 14, "하단 고정 바를 두지 않는다", 12, WARN, weight="700"))
    o.append(card(X, Y, BW, BH))

    # 앱 머리말
    o.append(box(X, Y, BW, 62, SURF, None, R))
    o.append(f"<rect x='{X}' y='{Y+61}' width='{BW}' height='1' fill='{LINE}'/>")
    o.append(f"<rect x='{X+24}' y='{Y+22}' width='18' height='18' rx='5' "
             f"fill='url(#pg)'/>")
    o.append(t(X + 50, Y + 37, "NCS PASS", 15, INK, weight="700", ls="-.3"))
    o.append(t(X + 126, Y + 37, "v1.9.0", 11.5, FAINT, font=MONO))
    o.append(t(X + 180, Y + 37, "764문항", 11.5, FAINT, font=MONO))
    cx = X + 300
    for lb, on in [("문항", True), ("회차", False), ("복습", False),
                   ("오답", False), ("정보", False)]:
        c, w = pill(cx, Y + 15, lb, 72, ACC if on else SURF,
                    "#fff" if on else MUTE, None if on else LINE, 32)
        o.append(c)
        cx += w + 8
    o.append(box(X + BW - 132, Y + 15, 108, 32, HAIR, None, 16))
    o.append(t(X + BW - 78, Y + 36, "🔍  검색", 12, FAINT, "middle"))

    # 3단
    o.append(zone(X + 20, Y + 82, 214, BH - 104, "좌 · 내비", "영역 → 유형"))
    o.append(zone(X + 250, Y + 82, 500, BH - 104, "중앙 · 문항",
                  "지문 · 발문 · 선지 · 해설"))
    o.append(zone(X + 766, Y + 82, 214, BH - 104, "우 · 번호판", "이동 · 제출"))
    for cx_, lb in [(X + 127, "240"), (X + 500, "가변 · 최소 560"), (X + 873, "260")]:
        o.append(t(cx_, Y + BH - 42, lb, 11, FAINT, "middle", font=MONO))

    # 제출 버튼 자리
    o.append(box(X + 782, Y + 372, 182, 46, ACC, None, RS))
    o.append(t(X + 873, Y + 400, "제출하고 채점", 13.5, "#fff", "middle", "700"))
    o.append(arrow(X + 762, Y + 340, X + 800, Y + 366))
    o.append(t(X + 756, Y + 336, "화면에 붙이지 않는다 — 가려질 수 없다",
               11.5, WARN, "end", "700"))

    # 태블릿 · 모바일
    TX = 1078
    o.append(t(TX, Y - 14, "태블릿  768~1279", 13, MUTE, weight="700"))
    o.append(card(TX, Y, 228, 176))
    o.append(box(TX, Y, 228, 40, SURF, None, R))
    o.append(f"<rect x='{TX}' y='{Y+39}' width='228' height='1' fill='{LINE}'/>")
    o.append(t(TX + 16, Y + 25, "≡   NCS PASS", 11.5, MUTE, weight="600"))
    o.append(zone(TX + 14, Y + 52, 136, 110, "문항"))
    o.append(zone(TX + 158, Y + 52, 56, 110, "번호"))

    o.append(t(TX, Y + 212, "모바일  < 768", 13, MUTE, weight="700"))
    o.append(card(TX, Y + 226, 228, 238))
    o.append(box(TX, Y + 226, 228, 40, SURF, None, R))
    o.append(t(TX + 16, Y + 251, "NCS PASS", 12, INK, weight="700"))
    o.append(box(TX + 14, Y + 276, 200, 30, HAIR, None, 15))
    o.append(t(TX + 114, Y + 296, "◀    12 / 40    ▶", 11, MUTE, "middle",
               font=MONO))
    o.append(zone(TX + 14, Y + 314, 200, 102, "문항 · 1단"))
    o.append(box(TX, Y + 424, 228, 40, SURF, None, R))
    o.append(f"<rect x='{TX}' y='{Y+424}' width='228' height='1' fill='{LINE}'/>")
    o.append(t(TX + 114, Y + 449, "하단 탭 — 유일한 고정 요소", 10.5, FAINT,
               "middle"))
    o.append(t(TX, Y + 486, "번호판은 바텀시트로 열고 제출도 그 안에 둔다",
               11, WARN, weight="600"))

    # 규칙
    n3, _ = note(X, Y + BH + 30, 1000, [
        "*지켜야 할 것",
        "· 화면 아래에 고정하는 요소는 **모바일 하단 탭 하나뿐**이다",
        "· 머리말은 늘 보인다 — 버전과 문항 수를 상주시킨다",
        "· 접힐 때 **문항 본문의 최소 폭 560을 먼저 지킨다.** 좌 내비 → 서랍, "
        "번호판 → 시트 순으로 접는다",
        "· 표·SVG 는 가로 스크롤 컨테이너에 담아 본문이 밀리지 않게 한다",
    ])
    o.append(n3)

    n4, _ = note(X, Y + BH + 152, 1000, [
        "*지금 코드의 결함 — 이래서 새로 만든다",
        "· app.css 261·277·314행이 모두 position: fixed; bottom: 0 이다. "
        "셋이 서로 덮어 **제출 버튼이 안 눌린다**",
        "· @media 질의가 다크모드 하나뿐이라 화면 폭 분기가 없다. PC 에서도 좁은 칼럼이다",
    ], BAD)
    o.append(n4)
    return svg("".join(o), 830)



# ── 2. 문제풀이 ──────────────────────────────────────────────────────
def s2_solve() -> str:
    # 구획만 그리지 않고 **실제 내용을 채운다** — Build 가 밀도까지 따라오게.
    o = [head("문제풀이", "선지 5상태 · 번호판 · 제출 조건 · 게임화 지표")]
    Y = 128

    # ── 좌 내비 ──
    LX, LW = 44, 264
    o.append(card(LX, Y, LW, 620))
    o.append(t(LX + 22, Y + 34, "수리능력", 15, INK, weight="700"))
    o.append(t(LX + 22, Y + 56, "자료해석(비중·비교)", 11.5, FAINT))
    o.append(bar(LX + 22, Y + 74, LW - 44, 0.42))
    o.append(t(LX + 22, Y + 100, "42 / 100 문항", 11, MUTE, font=MONO))
    o.append(t(LX + LW - 22, Y + 100, "정답률 68%", 11, VIVID, "end", "700",
               MONO))
    cx = LX + 22
    for lb, on in [("전체", True), ("안 푼 것", False), ("틀린 것", False)]:
        c, w = pill(cx, Y + 118, lb, None, ACC_BG if on else SURF,
                    ACC if on else MUTE, None if on else LINE, 28, 11.5)
        o.append(c)
        cx += w + 6
    for i, (lb, n_, on) in enumerate([("자료해석", 42, True), ("응용수리", 38, False),
                                      ("규칙찾기", 12, False), ("확률·경우", 8, False)]):
        yy = Y + 166 + i * 46
        o.append(box(LX + 14, yy, LW - 28, 38, ACC_BG if on else SURF,
                     None if on else LINE, RS))
        o.append(t(LX + 30, yy + 24, lb, 12.5, ACC if on else INK,
                   weight="700" if on else "400"))
        o.append(t(LX + LW - 30, yy + 24, str(n_), 11.5,
                   ACC if on else FAINT, "end", font=MONO))
    n, _ = note(LX + 14, Y + 366, LW - 28, [
        "*0건인 유형은",
        "흐리게 두고 누를 수",
        "없게 한다. 감추지",
        "않는다 — 유형이",
        "사라진 줄 안다.",
    ])
    o.append(n)

    # ── 중앙 문항 ──
    CX, CW = 332, 780
    o.append(card(CX, Y, CW, 620))
    o.append(t(CX + 26, Y + 34, "수리능력 · 자료해석(비중·비교)", 11.5, FAINT))
    o.append(t(CX + CW - 26, Y + 34, "12 / 40", 12, ACC, "end", "700", MONO))
    # 자료
    o.append(box(CX + 26, Y + 52, CW - 52, 118, HAIR, None, RS))
    o.append(t(CX + 44, Y + 78, "〈표〉 등급별 인정자 수", 11.5, MUTE, weight="700"))
    hdr = ["등급", "1등급", "2등급", "3등급", "4등급", "5등급", "계"]
    val = ["인정자", "48", "92", "301", "412", "147", "1,000"]
    for i, (a, b) in enumerate(zip(hdr, val)):
        xx = CX + 44 + i * 98
        o.append(t(xx, Y + 106, a, 11.5, FAINT))
        o.append(t(xx, Y + 130, b, 12.5, INK, weight="600", font=MONO))
    o.append(t(CX + 44, Y + 156, "가로가 넘치면 이 상자만 스크롤한다",
               10.5, FAINT))
    # 발문 — 대담한 타이포
    o.append(t(CX + 26, Y + 216, "4등급 인정자가 전체에서", 20, INK,
               weight="700", ls="-.3"))
    o.append(t(CX + 26, Y + 244, "차지하는 비중은?", 20, INK, weight="700",
               ls="-.3"))
    # 선지
    opts = [
        ("①", "30.1%", SURF, LINE, INK, "기본", 1),
        ("②", "34.7%", ACC_BG, ACC, ACC, "고름 — 테두리 2", 2),
        ("③", "41.2%", OK_BG, OK, OK, "정답 (채점 후)", 2),
        ("④", "45.9%", BAD_BG, BAD, BAD, "내가 고른 오답", 2),
        ("⑤", "71.3%", SURF, HAIR, FAINT, "채점 후 잠김", 1),
    ]
    for i, (num, v, f, st, tc, desc, sw) in enumerate(opts):
        yy = Y + 274 + i * 54
        o.append(box(CX + 26, yy, 470, 44, f, st, RS, sw))
        o.append(t(CX + 48, yy + 28, num, 14, tc, weight="700"))
        o.append(t(CX + 76, yy + 28, v, 14, tc, weight="600"))
        o.append(t(CX + 516, yy + 28, desc, 11.5, FAINT))
    n2, _ = note(CX + 26, Y + 548, CW - 52, [
        "*선지 — 터치 목표 44 이상. 키보드 1~5 로 고르고 ← → 로 이동",
    ])
    o.append(n2)

    # ── 우 번호판 ──
    RX, RW = 1136, 420
    o.append(card(RX, Y, RW, 620))
    o.append(t(RX + 22, Y + 34, "문항 번호", 13.5, INK, weight="700"))
    o.append(t(RX + RW - 22, Y + 34, "고른 것 9 / 40", 11, FAINT, "end",
               font=MONO))
    st = [(SURF, LINE, FAINT), (ACC_BG, ACC, ACC), (OK_BG, OK, OK),
          (BAD_BG, BAD, BAD), (WARN_BG, WARN, WARN)]
    for i in range(20):
        r, c = divmod(i, 5)
        f, sk, tc = st[i % 5]
        bx, by = RX + 22 + c * 74, Y + 56 + r * 58
        o.append(box(bx, by, 62, 46, f, sk, RS))
        o.append(t(bx + 31, by + 30, str(i + 1), 13, tc, "middle", "700",
                   MONO))
    for i, (lb, (f, sk, tc)) in enumerate(zip(
            ["안 품", "고름", "맞음", "틀림", "표시함"], st)):
        yy = Y + 306 + i * 30
        o.append(box(RX + 22, yy, 20, 20, f, sk, 6))
        o.append(t(RX + 52, yy + 15, lb, 11.5, MUTE))
    # 제출
    o.append(box(RX + 22, Y + 470, RW - 44, 52, ACC, None, RS))
    o.append(t(RX + RW / 2, Y + 502, "제출하고 채점", 14.5, "#fff", "middle",
               "700"))
    o.append(box(RX + 22, Y + 532, RW - 44, 40, SURF, LINE, RS))
    o.append(t(RX + RW / 2, Y + 558, "나가기 · 진행은 저장됨", 12, MUTE,
               "middle"))
    o.append(arrow(RX + RW / 2, Y + 448, RX + RW / 2, Y + 466))
    o.append(t(RX + RW / 2, Y + 442, "하나라도 고르면 활성", 11.5, WARN,
               "middle", "700"))

    n3, _ = note(44, Y + 640, 1512, [
        "*제출 버튼 — 이 화면에서 가장 중요한 규칙",
        "· 누르면 **그때 비로소** 채점하고 att 에 기록한다. 오답노트와 복습에도 이때 들어간다",
        "· 중간에 나가는 것은 오답이 아니다. 진행만 저장하고 기록은 남기지 않는다",
        "· 채점 후에는 선지를 잠근다. 정답·내가 고른 오답을 색과 **테두리 굵기로 함께** 표시한다",
    ], WARN)
    o.append(n3)
    return svg("".join(o), 880)



# ── 3. 태블릿 · 모바일 ───────────────────────────────────────────────
def s3_responsive() -> str:
    # 같은 문제풀이 화면을 좁은 폭에서 어떻게 접는지. 실제 폭 비율로 그린다.
    o = [head("태블릿 · 모바일", "같은 화면을 접는 순서 — 내비 → 서랍 · 번호판 → 시트")]
    Y = 132
    OPT = [("①", "30.1%", SURF, LINE, INK, 1), ("②", "34.7%", ACC_BG, ACC, ACC, 2),
           ("③", "41.2%", SURF, LINE, INK, 1), ("④", "45.9%", SURF, LINE, INK, 1),
           ("⑤", "71.3%", SURF, LINE, INK, 1)]

    # ══ 태블릿 ══
    TX, TW = 44, 700
    o.append(t(TX, Y - 16, "태블릿  768~1279  ·  2단", 13, MUTE, weight="700"))
    o.append(card(TX, Y, TW, 690))
    o.append(box(TX, Y, TW, 54, SURF, None, R))
    o.append(hline(TX, Y + 53, TW))
    o.append(t(TX + 22, Y + 34, "≡", 17, MUTE, weight="700"))
    o.append(t(TX + 48, Y + 33, "NCS PASS", 14, INK, weight="700"))
    o.append(t(TX + 118, Y + 33, "v1.9.0", 10.5, FAINT, font=MONO))
    o.append(t(TX + TW - 22, Y + 33, "12 / 40", 12, ACC, "end", "700", MONO))

    o.append(t(TX + 22, Y + 82, "수리능력 · 자료해석", 11, FAINT))
    o.append(box(TX + 22, Y + 94, TW - 200, 84, HAIR, None, RS))
    o.append(t(TX + 38, Y + 118, "〈표〉 등급별 인정자 수", 11, MUTE, weight="700"))
    for i, (a, b) in enumerate(zip(["1등급", "2등급", "3등급", "4등급", "계"],
                                   ["48", "92", "301", "412", "1,000"])):
        xx = TX + 38 + i * 92
        o.append(t(xx, Y + 140, a, 10.5, FAINT))
        o.append(t(xx, Y + 160, b, 11.5, INK, weight="600", font=MONO))
    o.append(t(TX + 22, Y + 212, "4등급 인정자가 전체에서", 18, INK, weight="700",
               ls="-.3"))
    o.append(t(TX + 22, Y + 238, "차지하는 비중은?", 18, INK, weight="700", ls="-.3"))
    for i, (num, v, f, sk, tc, sw) in enumerate(OPT):
        yy = Y + 266 + i * 50
        o.append(box(TX + 22, yy, TW - 200, 42, f, sk, RS, sw))
        o.append(t(TX + 42, yy + 27, num, 13, tc, weight="700"))
        o.append(t(TX + 68, yy + 27, v, 13, tc, weight="600"))

    NX = TX + TW - 166
    o.append(box(NX, Y + 94, 144, 414, HAIR, None, RS))
    o.append(t(NX + 14, Y + 118, "번호", 11.5, MUTE, weight="700"))
    st4 = [(SURF, LINE, FAINT), (ACC_BG, ACC, ACC), (OK_BG, OK, OK),
           (BAD_BG, BAD, BAD)]
    for i in range(16):
        r, c = divmod(i, 4)
        f, sk, tc = st4[i % 4]
        bx, by = NX + 12 + c * 32, Y + 132 + r * 42
        o.append(box(bx, by, 28, 34, f, sk, 7))
        o.append(t(bx + 14, by + 22, str(i + 1), 10, tc, "middle", "700", MONO))
    o.append(box(NX + 12, Y + 362, 120, 44, ACC, None, RS))
    o.append(t(NX + 72, Y + 390, "제출", 13, "#fff", "middle", "700"))
    o.append(t(NX + 72, Y + 428, "가려지지 않는다", 10, WARN, "middle", "700"))

    n, _ = note(TX + 22, Y + 530, TW - 44, [
        "*좌 내비는 햄버거(≡) → 서랍으로 접는다",
        "· 번호판은 남기되 좁힌다 — 4열 그리드",
        "· 본문이 560 아래로 내려가면 번호판도 접는다",
    ])
    o.append(n)

    # ══ 모바일 ══
    MX, MW = 780, 360
    o.append(t(MX, Y - 16, "모바일  < 768  ·  1단", 13, MUTE, weight="700"))
    o.append(card(MX, Y, MW, 690))
    o.append(box(MX, Y, MW, 50, SURF, None, R))
    o.append(hline(MX, Y + 49, MW))
    o.append(dot(MX + 18, Y + 17, 16))
    o.append(t(MX + 42, Y + 31, "NCS PASS", 13, INK, weight="700"))
    o.append(t(MX + MW - 18, Y + 31, "12 / 40", 11, ACC, "end", "700", MONO))

    o.append(box(MX + 16, Y + 62, MW - 32, 38, HAIR, None, 19))
    o.append(t(MX + 34, Y + 86, "◀", 12, MUTE))
    o.append(t(MX + MW / 2, Y + 86, "번호판 열기", 12, ACC, "middle", "700"))
    o.append(t(MX + MW - 34, Y + 86, "▶", 12, MUTE, "end"))

    o.append(t(MX + 16, Y + 124, "수리능력 · 자료해석", 10.5, FAINT))
    o.append(box(MX + 16, Y + 136, MW - 32, 60, HAIR, None, RS))
    o.append(t(MX + 32, Y + 158, "〈표〉 등급별 인정자 수", 10.5, MUTE, weight="700"))
    o.append(t(MX + 32, Y + 180, "가로 스크롤  →", 10, FAINT))
    o.append(t(MX + 16, Y + 226, "4등급 인정자가", 17, INK, weight="700", ls="-.3"))
    o.append(t(MX + 16, Y + 250, "전체에서 차지하는", 17, INK, weight="700", ls="-.3"))
    o.append(t(MX + 16, Y + 274, "비중은?", 17, INK, weight="700", ls="-.3"))
    for i, (num, v, f, sk, tc, sw) in enumerate(OPT):
        yy = Y + 298 + i * 52
        o.append(box(MX + 16, yy, MW - 32, 44, f, sk, RS, sw))
        o.append(t(MX + 36, yy + 28, num, 13, tc, weight="700"))
        o.append(t(MX + 62, yy + 28, v, 13.5, tc, weight="600"))

    o.append(box(MX, Y + 626, MW, 64, SURF, None, R))
    o.append(hline(MX, Y + 626, MW))
    for i, lb in enumerate(["문항", "회차", "복습", "오답", "정보"]):
        cx = MX + 40 + i * 70
        on = i == 0
        o.append(box(cx - 12, Y + 642, 24, 24, ACC_BG if on else HAIR, None, 7))
        o.append(t(cx, Y + 680, lb, 10.5, ACC if on else FAINT, "middle",
                   "700" if on else "400"))
    o.append(t(MX + MW / 2, Y + 712, "화면에 고정되는 유일한 요소", 10.5, WARN,
               "middle", "700"))

    # ══ 모바일 — 시트 열림 ══
    SX = 1176
    o.append(t(SX, Y - 16, "모바일  ·  번호판 시트", 13, MUTE, weight="700"))
    o.append(card(SX, Y, MW, 690))
    o.append(box(SX, Y, MW, 50, SURF, None, R))
    o.append(t(SX + 18, Y + 31, "NCS PASS", 13, INK, weight="700"))
    o.append(box(SX + 16, Y + 66, MW - 32, 196, HAIR, None, RS))
    o.append(t(SX + MW / 2, Y + 168, "본문 — 어둡게 덮는다", 11, FAINT, "middle"))

    SY = Y + 274
    o.append(box(SX, SY, MW, 416, SURF, None, R, shadow=True))
    o.append(box(SX + MW / 2 - 22, SY + 12, 44, 5, LINE, None, 2.5))
    o.append(t(SX + 20, SY + 46, "문항 번호", 13.5, INK, weight="700"))
    o.append(t(SX + MW - 20, SY + 46, "고른 것 9 / 40", 10.5, FAINT, "end",
               font=MONO))
    st5 = [(SURF, LINE, FAINT), (ACC_BG, ACC, ACC), (OK_BG, OK, OK),
           (BAD_BG, BAD, BAD), (WARN_BG, WARN, WARN)]
    for i in range(20):
        r, c = divmod(i, 5)
        f, sk, tc = st5[i % 5]
        bx, by = SX + 20 + c * 64, SY + 62 + r * 48
        o.append(box(bx, by, 54, 40, f, sk, 8))
        o.append(t(bx + 27, by + 26, str(i + 1), 11.5, tc, "middle", "700", MONO))
    o.append(box(SX + 20, SY + 272, MW - 40, 50, ACC, None, RS))
    o.append(t(SX + MW / 2, SY + 303, "제출하고 채점", 14, "#fff", "middle", "700"))
    o.append(box(SX + 20, SY + 332, MW - 40, 40, SURF, LINE, RS))
    o.append(t(SX + MW / 2, SY + 358, "닫기", 12, MUTE, "middle"))
    o.append(t(SX + MW / 2, SY + 396, "제출은 시트 안 — 탭과 겹치지 않는다", 10.5,
               WARN, "middle", "700"))

    n3, _ = note(44, Y + 726, 1492, [
        "*접는 순서 — 폭이 줄 때 이 차례로 버린다",
        "· 1순위 **좌 내비** → 햄버거 서랍. 문항을 읽는 데 없어도 된다",
        "· 2순위 **번호판** → 바텀시트. 이동은 위쪽 ◀ ▶ 로 대신한다",
        "· **문항 본문은 마지막까지 지킨다.** 최소 폭 560 아래로는 글자만 줄이고 접지 않는다",
        "· 터치 목표는 어느 폭에서든 44 이상. 모바일 선지 높이 44 를 지킨다",
    ])
    o.append(n3)
    return svg("".join(o), 1000)


SCREENS = {"01-layout": s1_layout, "02-solve": s2_solve,
           "03-responsive": s3_responsive}


def to_png(p: pathlib.Path) -> bool:
    import build
    chrome = build.find_chrome()
    if not chrome:
        return False
    m = re.search(r"height='(\d+)'", p.read_text(encoding="utf-8"))
    h = int(m.group(1)) if m else 1020
    png = p.with_suffix(".png")
    with tempfile.TemporaryDirectory() as prof:
        subprocess.run([
            chrome, "--headless=new", "--disable-gpu", "--no-first-run",
            f"--user-data-dir={prof}", f"--window-size={W},{h}",
            "--default-background-color=ffffffff", "--hide-scrollbars",
            "--force-device-scale-factor=1.5",
            f"--screenshot={png}", p.as_uri(),
        ], capture_output=True, timeout=120)
    return png.exists()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--svg", action="store_true")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in SCREENS.items():
        if a.only and name not in a.only:
            continue
        p = OUT / f"{name}.svg"
        p.write_text(fn(), encoding="utf-8")
        msg = f"[생성] {p.relative_to(ROOT)}"
        if not a.svg and to_png(p):
            msg += f"  +  {p.with_suffix('.png').name}"
        print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
