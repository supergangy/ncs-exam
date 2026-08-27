# -*- coding: utf-8 -*-
"""brand/out 의 로고를 앱·웹·안드로이드가 읽는 자리에 심는다.

`brand/logo.py` 를 먼저 돌려 out/ 을 채운 뒤 이걸 돌린다.

아이콘은 쓰이는 자리마다 규칙이 다르다 — 한 장을 복사하면 어딘가는 깎인다.

  any        카드째 보인다. 여백 20% 로 충분하다
  maskable   런처가 **원형으로 깎는다**. 배경을 꽉 채우고 심볼은 가운데 60% 안에
  adaptive foreground  108dp 중 가운데 72dp 만 확실히 보인다. 배경은 따로 준다
  monochrome adaptive foreground 를 실루엣으로 쓴다 — 알파가 곧 형태다
"""
import pathlib
import shutil
import sys

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "brand" / "out"

CARD = (248, 250, 252)                                  # #F8FAFC
ANDROID = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
FG_RATIO = 108 / 48                                     # adaptive 캔버스는 legacy 의 2.25배

sym = Image.open(OUT / "symbol.png")


def place(size, safe, bg=None):
    """정사각 캔버스 가운데에 심볼을 safe 비율로 놓는다. bg 가 None 이면 투명."""
    im = Image.new("RGBA", (size, size), (bg + (255,)) if bg else (0, 0, 0, 0))
    inner = round(size * safe)
    k = min(inner / sym.width, inner / sym.height)
    p = sym.resize((max(1, round(sym.width * k)), max(1, round(sym.height * k))), Image.LANCZOS)
    im.paste(p, ((size - p.width) // 2, (size - p.height) // 2), p)
    return im


def card(size, safe=0.60, radius=0.2237):
    """둥근 사각형 카드 + 심볼 — legacy 런처 아이콘과 any 용."""
    from PIL import ImageDraw
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=round(size * radius), fill=CARD + (255,))
    inner = round(size * safe)
    k = min(inner / sym.width, inner / sym.height)
    p = sym.resize((round(sym.width * k), round(sym.height * k)), Image.LANCZOS)
    im.paste(p, ((size - p.width) // 2, (size - p.height) // 2), p)
    return im


done = []


def put(im_or_src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(im_or_src, pathlib.Path):
        shutil.copyfile(im_or_src, dst)
    else:
        im_or_src.save(dst, optimize=True)
    done.append(dst.relative_to(ROOT).as_posix())


# ── 웹 (배포본 app/ · 재제작 web/public/) ────────────────────────────────
for base in (ROOT / "app", ROOT / "web" / "public"):
    put(OUT / "icon.svg", base / "icon.svg")
    put(OUT / "icon-192.png", base / "icon-192.png")
    put(OUT / "icon-512.png", base / "icon-512.png")
    put(place(512, 0.60, CARD), base / "icon-maskable-512.png")   # 깎여도 남는다
    put(OUT / "favicon-32.png", base / "favicon-32.png")

# ── 안드로이드 ────────────────────────────────────────────────────────
RES = ROOT / "mobile" / "android" / "app" / "src" / "main" / "res"
for name, px in ANDROID.items():
    put(card(px), RES / ("mipmap-%s" % name) / "ic_launcher.png")
    # foreground 는 배경을 그리지 않는다 — adaptive 가 배경을 따로 얹는다
    put(place(round(px * FG_RATIO), 0.46), RES / ("mipmap-%s" % name) / "ic_launcher_foreground.png")

bg_xml = RES / "values" / "ic_launcher_background.xml"
bg_xml.write_text(
    '<?xml version="1.0" encoding="utf-8"?>\n'
    "<resources>\n"
    '    <color name="ic_launcher_background">#F8FAFC</color>\n'
    "</resources>\n", encoding="utf-8")
done.append(bg_xml.relative_to(ROOT).as_posix())

# ── Flutter web (빌드 산출 껍데기) ─────────────────────────────────────
FW = ROOT / "mobile" / "web" / "icons"
if FW.exists():
    put(OUT / "icon-192.png", FW / "Icon-192.png")
    put(OUT / "icon-512.png", FW / "Icon-512.png")
    put(place(192, 0.60, CARD), FW / "Icon-maskable-192.png")
    put(place(512, 0.60, CARD), FW / "Icon-maskable-512.png")
    put(OUT / "favicon-32.png", ROOT / "mobile" / "web" / "favicon.png")

for f in done:
    p = ROOT / f
    print("  %-62s %6.1f KB" % (f, p.stat().st_size / 1024))
print()
print("  %d개 파일" % len(done))
