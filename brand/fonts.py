# -*- coding: utf-8 -*-
"""PC 웹에 심을 폰트를 만든다 — 받기 · 필요한 글자 세기 · 잘라내기 · 배치.

## 왜 서브셋인가

이 앱은 **오프라인이 요건**이라 CDN 을 쓸 수 없다. 폰트를 저장소에 넣어야 하는데
한글 폰트 완전본은 크다 (Pretendard Variable 2,010KB · Noto Sans KR 10,171KB).
앱이 첫 로드에 받는 것이 통째로 1,736KB 인데 폰트가 그보다 크면 안 된다.

**모바일·APK 에는 넣지 않는다.** 안드로이드에는 Noto Sans KR, iOS·macOS 에는
Apple SD Gothic Neo 가 이미 있다. 아쉬운 것은 Windows(맑은 고딕)뿐이고 그게 PC 웹이다.

## 왜 폰트가 셋인가

Pretendard 는 한글·라틴 폰트여서 **한자와 ㉠~㉯ 을 갖고 있지 않다.**
그런데 ㉠~㉯ 은 NCS 「보기」 라벨로 245회, 한자는 157회 쓰인다 — 폴백에 맡기면
한 문장 안에서 자형이 튄다. 그래서 Pretendard 가 못 가진 글자만 Noto 에서 뽑아 얹는다.

    Pretendard-subset    한글 2,540자 + 라틴          447 KB
    NotoSansKR-gap       한자 108 + ㉠~㉯ + ∈≡⊃⊕─═▤   31 KB
    NotoSansMath-gap     ≒ ⋈ ⌊ ⌋                     1.2 KB   ⋈ 는 관계대수 조인이다
    IBMPlexMono 400/600  타이머·문항번호용 라틴        30 KB
                                                     ─────────
                                                      509 KB

CSS 는 `unicode-range` 를 손으로 짜지 않는다. family 를 나눠 스택에 순서대로 두면
브라우저가 글자마다 앞에서부터 찾는다 — 범위를 적다 빠뜨리는 실수가 없다.
(Math 만은 4자뿐이라 범위를 적어 「NCS Gap」에 합쳤다.)

## 문항이 늘면 다시 돌린다

서브셋 대상은 **실제로 쓰인 글자 ∪ KS X 1001 2,350자**다. 앞엣것은 지금 문항에서
세고, 뒤엣것은 앞으로 나올 글자를 위한 안전망이다. 새 회차를 넣은 뒤 이걸 다시 돌려
`--check` 로 빠진 글자가 없는지 본다.

    python brand/fonts.py            # 받기 → 자르기 → web/public/fonts 에 배치
    python brand/fonts.py --check     # 만들지 않고, 지금 폰트로 다 그릴 수 있는지만 본다
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import urllib.request

from fontTools.ttLib import TTFont

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "brand" / "fonts-src"
DST = ROOT / "web" / "public" / "fonts"

# 받을 것 — (파일명, URL, 라이선스 URL)
GETS = [
    ("PretendardVariable.woff2",
     "https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/web/variable/woff2/PretendardVariable.woff2",
     "https://raw.githubusercontent.com/orioncactus/pretendard/v1.3.9/LICENSE",
     "OFL-Pretendard.txt"),
    ("NotoSansKR.ttf",
     "https://github.com/google/fonts/raw/main/ofl/notosanskr/NotoSansKR%5Bwght%5D.ttf",
     "https://github.com/google/fonts/raw/main/ofl/notosanskr/OFL.txt",
     "OFL-NotoSansKR.txt"),
    ("NotoSansMath.ttf",
     "https://github.com/google/fonts/raw/main/ofl/notosansmath/NotoSansMath-Regular.ttf",
     "https://github.com/google/fonts/raw/main/ofl/notosansmath/OFL.txt",
     "OFL-NotoSansMath.txt"),
]

# 앱 텍스트가 있는 곳 — 여기 쓰인 글자를 전부 담는다
TEXT_FILES = ["app/data/bank.json", "app/index.html", "app/app.js", "app/app.css"]

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120"}
MATH = "≒⋈⌊⌋"                       # Noto Sans KR 에도 없어 Math 에서 뽑는 것

# 폰트에 넣지 않고 시스템에 맡기는 글자.
#   ⚐ ⚑ ✎ ✕  현재 배포본 app.js·app.css 가 UI 아이콘으로 쓰는 문자다. 폰트에 의존하면
#             기기마다 다르게 보이고 없으면 두부(□)가 된다 — **재제작 때 SVG 로 바꾼다.**
#             문항 본문에는 쓰이지 않으므로 지금은 폴백에 둔다.
#   🔍        이모지. 시스템 이모지 폰트가 그리는 것이 맞다.
ALLOW_FALLBACK = "⚐⚑✎✕🔍"


def get(url: str, dst: pathlib.Path) -> None:
    if dst.exists() and dst.stat().st_size > 1024:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=300) as r:
        dst.write_bytes(r.read())


def cmap_of(p: pathlib.Path) -> set[int]:
    s: set[int] = set()
    for t in TTFont(p)["cmap"].tables:
        s |= set(t.cmap.keys())
    return s


def used_chars() -> set[str]:
    """앱에 실제로 쓰인 글자."""
    u: set[str] = set()
    for rel in TEXT_FILES:
        u |= set((ROOT / rel).read_text(encoding="utf-8"))
    return {c for c in u if ord(c) > 31}


def ksx1001() -> set[str]:
    """KS X 1001 완성형 한글 2,350자 — 앞으로 나올 글자를 위한 안전망.

    `chr(cp).encode('euc-kr')` 로 걸러선 안 된다. 파이썬의 euc-kr 은 실제로 CP949 라
    확장 완성형 11,172자를 전부 통과시킨다. KSX 코드 영역(0xB0A1~0xC8FE)을 직접 돈다.
    """
    s: set[str] = set()
    for hi in range(0xB0, 0xC9):
        for lo in range(0xA1, 0xFF):
            try:
                s.add(bytes([hi, lo]).decode("euc-kr"))
            except UnicodeDecodeError:
                pass
    return s


def subset(src: pathlib.Path, chars: str, out: pathlib.Path) -> None:
    txt = SRC / (out.stem + ".chars.txt")
    txt.write_text(chars, encoding="utf-8")
    subprocess.run(
        [sys.executable, "-m", "fontTools.subset", str(src),
         "--text-file=" + str(txt), "--output-file=" + str(out), "--flavor=woff2",
         "--layout-features=*", "--no-hinting", "--desubroutinize"],
        check=True, capture_output=True)


def plex_latin() -> list[tuple[str, bytes]]:
    """IBM Plex Mono 는 구글이 이미 라틴만 잘라 뒀다 — 그 조각을 그대로 쓴다."""
    req = urllib.request.Request(
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&display=swap",
        headers=UA)
    css = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
    import re
    out = []
    for blk in re.findall(r"@font-face\s*\{(.*?)\}", css, re.S):
        w = re.search(r"font-weight:\s*(\d+)", blk)
        u = re.search(r"url\((https://[^)]+\.woff2)\)", blk)
        r = re.search(r"unicode-range:\s*([^;]+)", blk)
        if not (w and u and r and r.group(1).strip().startswith("U+0000-00FF")):
            continue
        out.append((w.group(1), urllib.request.urlopen(u.group(1), timeout=60).read()))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="만들지 않고 커버리지만 본다")
    args = ap.parse_args()

    used = used_chars()

    if args.check:
        have: set[int] = set()
        for f in sorted(DST.glob("*.woff2")):
            have |= cmap_of(f)
        miss = sorted(c for c in used
                      if ord(c) not in have and c not in ALLOW_FALLBACK)
        print("  앱에 쓰인 글자 %d 자 · 지금 폰트가 가진 것 %d 자" % (len(used), len(have)))
        print("  시스템에 맡긴 글자 %d 자: %s" % (len(ALLOW_FALLBACK), ALLOW_FALLBACK))
        if miss:
            print("  !! 빠진 글자 %d 자 — 다시 만들어야 한다" % len(miss))
            print("     " + "".join(miss)[:120])
            return 1
        print("  빠진 글자 없음")
        return 0

    for name, url, lic_url, lic_name in GETS:
        get(url, SRC / name)
        get(lic_url, SRC / lic_name)
        print("  받음  %-28s %8.1f KB" % (name, (SRC / name).stat().st_size / 1024))

    pre_cmap = cmap_of(SRC / "PretendardVariable.woff2")
    noto_cmap = cmap_of(SRC / "NotoSansKR.ttf")

    # 1) Pretendard — 쓰인 글자 ∪ KSX2350 중 이 폰트가 가진 것
    target = used | ksx1001()
    chars = "".join(sorted(c for c in target if ord(c) in pre_cmap))
    subset(SRC / "PretendardVariable.woff2", chars, DST / "Pretendard-subset.woff2")
    print("  잘라냄 Pretendard-subset      %8.1f KB  (%d 자)"
          % ((DST / "Pretendard-subset.woff2").stat().st_size / 1024, len(chars)))

    # 2) Noto Sans KR — Pretendard 가 못 가진 것만
    gap = "".join(sorted(c for c in used if ord(c) not in pre_cmap and ord(c) in noto_cmap))
    subset(SRC / "NotoSansKR.ttf", gap, DST / "NotoSansKR-gap.woff2")
    print("  잘라냄 NotoSansKR-gap         %8.1f KB  (%d 자)"
          % ((DST / "NotoSansKR-gap.woff2").stat().st_size / 1024, len(gap)))

    # 3) Noto Sans Math — 둘 다 없는 넷
    subset(SRC / "NotoSansMath.ttf", MATH, DST / "NotoSansMath-gap.woff2")
    print("  잘라냄 NotoSansMath-gap       %8.1f KB  (%d 자)"
          % ((DST / "NotoSansMath-gap.woff2").stat().st_size / 1024, len(MATH)))

    # 4) IBM Plex Mono — 구글 조각 그대로
    for w, data in plex_latin():
        (DST / ("IBMPlexMono-%s-latin.woff2" % w)).write_bytes(data)
        print("  받음  IBMPlexMono-%s-latin     %8.1f KB" % (w, len(data) / 1024))

    for lic in ["OFL-Pretendard.txt", "OFL-NotoSansKR.txt", "OFL-NotoSansMath.txt"]:
        (DST / lic).write_bytes((SRC / lic).read_bytes())
    get("https://raw.githubusercontent.com/IBM/plex/master/LICENSE.txt", DST / "OFL-IBMPlex.txt")

    tot = sum(f.stat().st_size for f in DST.glob("*.woff2"))
    print()
    print("  폰트 합계 %.1f KB — PC 웹에만 실린다" % (tot / 1024))

    still = sorted(c for c in used
                   if ord(c) not in pre_cmap and ord(c) not in noto_cmap and c not in MATH)
    unexpected = [c for c in still if c not in ALLOW_FALLBACK]
    print("  시스템에 맡긴 글자 %d 자: %s" % (len(still), "".join(still)))
    if unexpected:
        print("  !! 예상 밖으로 빠진 글자: %s — ALLOW_FALLBACK 을 보라" % "".join(unexpected))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
