# -*- coding: utf-8 -*-
"""NCS PASS 로고 자산을 원본 JPG 한 장에서 만든다.

원본(`로고.jpg`)은 **흰 캔버스 위에 연회색 둥근 사각형 카드, 그 안에 파랑→보라 심볼**이다.
카드색 #F8FAFC 과 캔버스 흰색은 채도가 거의 같아 알파 마스크로 분리되지 않는다.
그래서 **심볼만 채도로 뽑고, 카드는 새로 그린다.** 어떤 크기로 내도 모서리가 선명하다.

내는 것
  symbol.png        심볼만 투명 — 헤더·워터마크용
  icon-{512,192}.png  둥근 사각형 카드 + 심볼 — 앱 아이콘 (PWA·APK)
  favicon-{32,16}.png 파비콘
  icon.svg          카드는 벡터, 심볼은 임베드 — 확대에 강하다
"""
import base64
import io
import pathlib

from PIL import Image, ImageDraw, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)

SRC = ROOT / "logo-src.jpg"
BG = (243, 243, 255)            # 원본 배경 실측값 — 알파 되돌릴 때 이 색을 뺀다
CARD = (248, 250, 252)          # #F8FAFC — 새로 그릴 카드색 (시안 slate-50)
SAT_LO, SAT_HI = 40, 110        # 채도 임계. 배경·그림자는 12~14, 심볼은 130~150 이다
                                # 12 로 잡으면 원본 드롭섀도가 얼룩으로 딸려 온다


def symbol(src):
    """채도로 심볼만 뽑는다. 배경(흰·연회색)은 채도가 0에 가깝다."""
    im = src.convert("RGB")
    w, h = im.size
    px = im.load()
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    op = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            sat = max(r, g, b) - min(r, g, b)
            if sat <= SAT_LO or min(r, g, b) > 210:
                continue
            a = 255 if sat >= SAT_HI else round((sat - SAT_LO) / (SAT_HI - SAT_LO) * 255)
            # 경계 픽셀은 흰색이 섞여 밝다 — 알파로 나눠 원래 색을 되돌린(un-premultiply) 값
            f = a / 255
            op[x, y] = (
                max(0, min(255, round((r - BG[0] * (1 - f)) / f))),
                max(0, min(255, round((g - BG[1] * (1 - f)) / f))),
                max(0, min(255, round((b - BG[2] * (1 - f)) / f))),
                a,
            )
    return out.crop(out.getbbox())


def card(size, sym, pad_ratio=0.20, radius_ratio=0.2237):
    """둥근 사각형 카드 위에 심볼을 얹는다.

    radius 0.2237 은 iOS 앱 아이콘의 squircle 근사값이다 — 원본 카드와 같은 느낼.
    """
    s = size
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=round(s * radius_ratio), fill=CARD + (255,))

    inner = round(s * (1 - pad_ratio * 2))
    k = min(inner / sym.width, inner / sym.height)
    p = sym.resize((round(sym.width * k), round(sym.height * k)), Image.LANCZOS)
    im.paste(p, ((s - p.width) // 2, (s - p.height) // 2), p)
    return im


def svg(sym, size=512, radius=114):
    """카드는 벡터, 심볼은 base64 PNG. 아이콘 한 장으로 어디든 쓴다."""
    buf = io.BytesIO()
    sym.save(buf, "PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()

    pad = round(size * 0.20)
    inner = size - pad * 2
    k = min(inner / sym.width, inner / sym.height)
    w, h = round(sym.width * k), round(sym.height * k)
    x, y = (size - w) // 2, (size - h) // 2
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">\n'
        '  <rect width="%d" height="%d" rx="%d" fill="#F8FAFC"/>\n'
        '  <image x="%d" y="%d" width="%d" height="%d" '
        'xlink:href="data:image/png;base64,%s" '
        'xmlns:xlink="http://www.w3.org/1999/xlink"/>\n'
        "</svg>\n"
    ) % (size, size, size, size, size, size, radius, x, y, w, h, b64)


src = Image.open(SRC)
sym = symbol(src)
sym.save(OUT / "symbol.png", optimize=True)

made = [("symbol.png", sym.size)]
for s in (512, 192):
    f = "icon-%d.png" % s
    card(s, sym).save(OUT / f, optimize=True)
    made.append((f, (s, s)))

for s in (32, 16):
    f = "favicon-%d.png" % s
    # 작은 크기는 여백을 줄여야 심볼이 보인다
    card(s * 8, sym, pad_ratio=0.10).resize((s, s), Image.LANCZOS).save(OUT / f)
    made.append((f, (s, s)))

(OUT / "icon.svg").write_text(svg(sym), encoding="utf-8")
made.append(("icon.svg", "vector"))

for f, size in made:
    p = OUT / f
    print("  %-16s %-12s %6.1f KB" % (f, size, p.stat().st_size / 1024))
