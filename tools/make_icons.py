"""앱 아이콘을 만든다 — `app/icon.svg` 의 도형을 Pillow 로 다시 그린다.

이 기계에는 SVG 래스터라이저가 없다(ImageMagick·rsvg·inkscape 전부 없고,
PATH 의 `convert` 는 윈도우 파일시스템 변환 유틸이라 함정이다).
도안이 도형 넷뿐이라 그대로 옮겨 그리는 편이 확실하다.

손으로 만든 PNG 는 근거가 없다. 도안이 바뀌면 이걸 다시 돌린다.

    python tools/make_icons.py
    python tools/make_icons.py --check      # 만들지 않고 검사만
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

# 윈도우 콘솔 기본값은 cp949 라 「—」 하나에 스크립트가 죽는다.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "mobile" / "android" / "app" / "src" / "main" / "res"

BRAND = (28, 78, 128, 255)  # #1c4e80
WHITE = (255, 255, 255, 255)
SS = 8  # 이만큼 키워 그리고 줄인다 — 곡선과 사선을 부드럽게

# app/icon.svg 의 64 단위 좌표 그대로.
VB = 64.0
RADIUS = 14.0
BAR = (14, 15, 50, 22.5)      # 가로획
STEM = (14, 15, 21.5, 49)     # 세로획
DOT = (43, 42, 6.5)           # 원 (cx, cy, r)

LEGACY = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
# adaptive 는 108dp 캔버스에 그리고 가운데 72dp 만 확실히 보인다.
ADAPTIVE = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}
SAFE = 72 / 108  # 전경을 이 비율 안에 넣는다


def _marks(d: ImageDraw.ImageDraw, k: float, ox: float = 0, oy: float = 0) -> None:
    """흰 획 셋. k 는 64 단위 → 픽셀 배율."""
    for x0, y0, x1, y1 in (BAR, STEM):
        d.rectangle([ox + x0 * k, oy + y0 * k, ox + x1 * k, oy + y1 * k], fill=WHITE)
    cx, cy, r = DOT
    d.ellipse(
        [ox + (cx - r) * k, oy + (cy - r) * k, ox + (cx + r) * k, oy + (cy + r) * k],
        fill=WHITE,
    )


def legacy_icon(size: int) -> Image.Image:
    """옛 방식 아이콘 — 배경 둥근사각까지 한 장에 담는다."""
    big = size * SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = big / VB
    d.rounded_rectangle([0, 0, big - 1, big - 1], radius=RADIUS * k, fill=BRAND)
    _marks(d, k)
    return img.resize((size, size), Image.LANCZOS)


def adaptive_foreground(size: int) -> Image.Image:
    """전경만. 배경은 시스템이 `ic_launcher_background` 로 깔고 모양도 알아서 깎는다.

    안전영역(가운데 72dp) 안에 들어가야 해서 도안을 줄여 다시 앉힌다.
    지금 도안의 여백(21.9%)으로는 모자라 그대로 쓰면 모서리가 잘린다.
    """
    big = size * SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 획이 차지하는 범위는 x 14~49.5, y 15~49 → 가장 긴 변 35.5
    span = 35.5
    k = (big * SAFE) / span
    ox = (big - span * k) / 2 - 14 * k
    oy = (big - 34 * k) / 2 - 15 * k
    _marks(d, k, ox, oy)
    return img.resize((size, size), Image.LANCZOS)


ANYDPI = """<?xml version="1.0" encoding="utf-8"?>
<!-- Android 8+ 는 이 선언을 보고 배경/전경을 따로 받아 기기 모양대로 깎는다.
     이게 없으면 정사각 아이콘이 흰 테두리째 우겨넣어져 지저분하다. -->
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background"/>
    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>
    <monochrome android:drawable="@mipmap/ic_launcher_foreground"/>
</adaptive-icon>
"""

BG_XML = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">#1c4e80</color>
</resources>
"""


def build() -> list[Path]:
    made: list[Path] = []
    for dens, size in LEGACY.items():
        p = RES / f"mipmap-{dens}" / "ic_launcher.png"
        p.parent.mkdir(parents=True, exist_ok=True)
        legacy_icon(size).save(p)
        made.append(p)
    for dens, size in ADAPTIVE.items():
        p = RES / f"mipmap-{dens}" / "ic_launcher_foreground.png"
        adaptive_foreground(size).save(p)
        made.append(p)

    anydpi = RES / "mipmap-anydpi-v26" / "ic_launcher.xml"
    anydpi.parent.mkdir(parents=True, exist_ok=True)
    anydpi.write_text(ANYDPI, encoding="utf-8")
    made.append(anydpi)

    bg = RES / "values" / "ic_launcher_background.xml"
    bg.write_text(BG_XML, encoding="utf-8")
    made.append(bg)
    return made


def check() -> int:
    """만들어 둔 것이 쓸 만한지 본다 — 크기·모서리색·가운데가 비지 않았는지."""
    bad = 0
    for dens, size in LEGACY.items():
        p = RES / f"mipmap-{dens}" / "ic_launcher.png"
        if not p.exists():
            print(f"  ✗ 없음 {p}")
            bad += 1
            continue
        im = Image.open(p).convert("RGBA")
        if im.size != (size, size):
            print(f"  ✗ {p.name}({dens}) 크기 {im.size}, {size} 이어야 함")
            bad += 1
        # 모서리 안쪽은 브랜드색이어야 한다 (둥근 모서리라 정확히 (0,0) 은 투명)
        px = im.getpixel((size // 2, 2))
        if abs(px[0] - BRAND[0]) > 12 or abs(px[2] - BRAND[2]) > 12:
            print(f"  ✗ {p.name}({dens}) 윗변 색 {px}, 브랜드색이 아님")
            bad += 1
        # 가운데가 통째로 비어 있으면 도안이 안 그려진 것이다
        white = sum(
            1
            for x in range(size // 4, size * 3 // 4)
            for y in range(size // 4, size * 3 // 4)
            if im.getpixel((x, y))[0] > 200
        )
        if white < 10:
            print(f"  ✗ {p.name}({dens}) 가운데에 흰 획이 없음")
            bad += 1

    for dens, size in ADAPTIVE.items():
        p = RES / f"mipmap-{dens}" / "ic_launcher_foreground.png"
        if not p.exists():
            print(f"  ✗ 없음 {p}")
            bad += 1
            continue
        im = Image.open(p).convert("RGBA")
        if im.size != (size, size):
            print(f"  ✗ {p.name}({dens}) 크기 {im.size}, {size} 이어야 함")
            bad += 1
        if im.getpixel((1, 1))[3] != 0:
            print(f"  ✗ {p.name}({dens}) 전경 바깥이 투명하지 않음")
            bad += 1
        # 도안이 아예 안 그려졌으면 투명한 빈 장이 된다 — 눈으로는 배경색과 구별이 안 간다
        ink = sum(1 for px in im.getdata() if px[3] > 8) / (size * size)
        if not 0.10 < ink < 0.45:
            print(f"  ✗ {p.name}({dens}) 전경이 화면의 {ink:.1%} — 10~45% 여야 함")
            bad += 1
        # 안전영역 밖으로 삐져나오지 않았는지 — 테두리 6% 띠는 비어 있어야 한다
        edge = max(1, int(size * 0.06))
        spill = sum(
            1
            for x in range(size)
            for y in list(range(edge)) + list(range(size - edge, size))
            if im.getpixel((x, y))[3] > 8
        )
        if spill:
            print(f"  ✗ {p.name}({dens}) 안전영역 밖으로 {spill}px 삐져나옴")
            bad += 1

    for p in (RES / "mipmap-anydpi-v26" / "ic_launcher.xml",
              RES / "values" / "ic_launcher_background.xml"):
        if not p.exists():
            print(f"  ✗ 없음 {p}")
            bad += 1

    print(f"아이콘 검사 — {'통과' if bad == 0 else f'{bad}건 실패'}")
    return bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="만들지 않고 검사만")
    a = ap.parse_args()
    if not a.check:
        for f in build():
            print(f"  {f.relative_to(ROOT)}")
    sys.exit(1 if check() else 0)
