# -*- coding: utf-8 -*-
"""아이콘이 **선언한 대로 있는지** 본다.

    python brand/check.py

## 왜 필요한가

아이콘은 `brand/logo.py` → `brand/deploy.py` 를 거쳐 **커밋된 산출물**로 남는다
(`brand/out/` 은 gitignore 다). 그래서 파일 하나가 빠지거나 크기가 어긋나도
빌드는 통과하고, **런처 아이콘이 두부가 되어서야** 안다.

옛 `tools/make_icons.py --check` 이 이 자리를 지키고 있었다. 2026-08-27
`72cc40c`(이름·로고 교체)에서 그 파일이 `brand/` 로 옮겨지며 사라졌는데
**워크플로만 그대로 남아** APK CI 가 「No such file」로 죽고 있었다.
그 상태를 나흘 동안 아무도 몰랐다 — 검사가 검사되지 않은 셈이다.

## 여기서 못 보는 것

가운데 안전 영역(maskable 60% · adaptive 72dp/108dp)이 지켜졌는지는 **눈으로
봐야 한다.** 알파를 세어 짐작할 수는 있지만, 그 판정이 틀리면 오히려 손이 간다.
규칙은 `brand/deploy.py` 머리말이 적어 두었고, 여기서는 **있는지와 크기**만 본다.
그 둘이 실제로 깨졌던 것이다.
"""
from __future__ import annotations

import json
import pathlib
import sys

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parent.parent

ok = 0
bad: list[str] = []


def check(what: str, cond: bool) -> None:
    global ok
    if cond:
        ok += 1
    else:
        bad.append(what)


def size_of(p: pathlib.Path) -> tuple[int, int] | None:
    try:
        with Image.open(p) as im:
            return im.size
    except Exception:
        return None


# ── 웹 — 매니페스트가 선언한 것이 실제로 있나 ───────────────────────
#    선언과 파일이 갈리면 설치한 PWA 의 아이콘이 빈칸이 된다.
for man in ("manifest.webmanifest", "m-manifest.webmanifest"):
    mp = ROOT / "web" / "public" / man
    check(f"{man} 이 있다", mp.is_file())
    if not mp.is_file():
        continue
    icons = json.loads(mp.read_text(encoding="utf-8")).get("icons", [])
    check(f"{man} 에 아이콘 선언이 있다", bool(icons))
    for i in icons:
        src = (i.get("src") or "").lstrip("./")
        want = i.get("sizes", "")
        p = mp.parent / src
        if not p.is_file():
            bad.append(f"{man} 이 가리키는 {src} 가 없다")
            continue
        ok += 1
        got = size_of(p)
        if want and "x" in want and got:
            w, h = (int(x) for x in want.split("x"))
            check(f"{src} 가 {want} 다 (실제 {got[0]}x{got[1]})", got == (w, h))
    # 런처가 원형으로 깎는 자리에 쓸 것이 선언되어 있나
    check(f"{man} 에 maskable 이 있다",
          any("maskable" in (i.get("purpose") or "") for i in icons))

# ── 웹 — 매니페스트 밖에서 쓰는 것 ──────────────────────────────────
for name, want in (("icon.svg", None), ("favicon-32.png", (32, 32))):
    p = ROOT / "web" / "public" / name
    check(f"web/public/{name} 이 있다", p.is_file())
    if p.is_file() and want:
        check(f"{name} 이 {want[0]}x{want[1]} 다", size_of(p) == want)

# ── 옛 바닐라 판 — 아직 서버에 있다 (deploy_web.py 의 KEEP) ─────────
for name in ("icon-192.png", "icon-512.png", "icon.svg"):
    check(f"app/{name} 이 있다", (ROOT / "app" / name).is_file())

# ── 안드로이드 — 밀도마다 한 벌씩 ───────────────────────────────────
#    하나만 빠져도 그 밀도의 기기에서 기본 아이콘(플러터 로고)이 나온다.
RES = ROOT / "mobile" / "android" / "app" / "src" / "main" / "res"
DENSITY = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
for d, px in DENSITY.items():
    for stem in ("ic_launcher", "ic_launcher_foreground"):
        p = RES / f"mipmap-{d}" / f"{stem}.png"
        check(f"{d}/{stem}.png 이 있다", p.is_file())
        if not p.is_file():
            continue
        got = size_of(p)
        # foreground 는 108dp 판이라 legacy(48dp 기준)보다 크다
        want = px if stem == "ic_launcher" else round(px * 108 / 48)
        check(f"{d}/{stem}.png 이 {want}x{want} 다 (실제 {got})", got == (want, want))

# adaptive 아이콘은 XML 이 두 겹을 가리킨다. 그 XML 이 없으면 legacy 로 떨어진다
check("mipmap-anydpi-v26/ic_launcher.xml 이 있다",
      (RES / "mipmap-anydpi-v26" / "ic_launcher.xml").is_file())
check("values/ic_launcher_background.xml 이 있다",
      (RES / "values" / "ic_launcher_background.xml").is_file())

print(f"   아이콘 검사 — 통과 {ok}건 · 지적 {len(bad)}건")
for b in bad:
    print(f"     ✘ {b}")
if bad:
    print("\n   `python brand/logo.py && python brand/deploy.py` 로 다시 만든다.")
raise SystemExit(1 if bad else 0)
