# -*- coding: utf-8 -*-
"""법제처 법령 파일에서 조문 본문을 뽑고, 문항의 인용을 원문과 대조한다.

뽑은 본문은 `bank/_law/` 에 둔다. **`corpus/` 에 두면 안 된다** — 그쪽은
커밋 전 원문 혼입 검사가 막는 경로다. 법령은 저작권법 제7조에 따라
보호받지 못하는 저작물이라 저장소에 그대로 두어도 된다.

**왜 필요한가** — 조문 번호와 문구는 지어낼 수 없다(bank/README.md).
그런데 law.go.kr 은 JS 로 그려서 WebFetch 로 본문이 잡히지 않고, 검색 결과의
요약문은 LLM 이 다시 쓴 것이라 믿을 수 없다(한 번은 부당이득 조문 번호를
스스로 뒤집었다). 그래서 **사용자가 내려받은 파일**을 원본으로 삼는다.

내려받은 파일은 확장자가 `.doc` 이지만 실제로는 **RTF** 다. 한글은
`ansicpg1252` 라 `\\uNNNN?` 로 들어 있고, 머리에 Photoshop 이미지가 붙어 있다.

    # 1) 본문 뽑기
    python tools/law_text.py extract "노인장기요양보험법(...).doc" > bank/_law/ltci.txt

    # 2) 조문 하나 보기
    python tools/law_text.py article bank/_law/ltci.txt 40

    # 3) 문항의 인용이 원문과 같은지 대조 (핵심)
    python tools/law_text.py check bank/_law/_all.txt --round r5_nhis

`check` 는 공백을 지우고 원문 전체에서 찾는다. **한 글자만 달라도 걸린다.**
굵게(`<strong>`)·생략(`…`)·문단 기호는 걷어내고 비교하므로, 편집상의 강조는
통과하고 문구를 고친 것은 통과하지 못한다.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HANGUL = re.compile(r"[가-힣]")
HEAD = re.compile(r"^제(\d+)조(의\d+)?\(")
# 인용 판별용 — 줄 시작에 걸리지 않는다. HTML 자료는 한 줄로 이어져 있다.
CITED = re.compile(r"제\d+조(?:의\d+)?\([^)]{2,30}\)")
# 조문 인용으로 볼 최소 길이. 짧은 조각은 우연히 일치할 수 있다.
MIN_FRAGMENT = 14


# ── 1. RTF → 텍스트 ──────────────────────────────────────────────────
def rtf_to_text(raw: str) -> str:
    """최소한만 처리한다 — \\uNNNN? · \\'XX · \\par · {\\*..} 무시."""
    out: list[str] = []
    i, n = 0, len(raw)
    depth, skip_depth = 0, None
    while i < n:
        c = raw[i]
        if c == "{":
            depth += 1
            if raw.startswith(r"{\*", i) and skip_depth is None:
                skip_depth = depth
            i += 1
            continue
        if c == "}":
            if skip_depth is not None and depth == skip_depth:
                skip_depth = None
            depth -= 1
            i += 1
            continue
        if skip_depth is not None:
            i += 1
            continue
        if c == "\\":
            m = re.match(r"\\u(-?\d+)\s?", raw[i:])
            if m:
                cp = int(m.group(1))
                out.append(chr(cp + 65536 if cp < 0 else cp))
                i += m.end()
                if i < n and raw[i] not in "\\{}":
                    i += 1               # 대체 문자 하나를 건너뛴다
                continue
            m = re.match(r"\\'([0-9a-fA-F]{2})", raw[i:])
            if m:
                out.append(bytes([int(m.group(1), 16)]).decode("cp1252", "replace"))
                i += m.end()
                continue
            m = re.match(r"\\(par|line|page)\b\s?", raw[i:])
            if m:
                out.append("\n")
                i += m.end()
                continue
            m = re.match(r"\\([a-zA-Z]+)(-?\d+)?[ ]?", raw[i:])
            if m:
                i += m.end()
                continue
            if i + 1 < n:
                out.append(raw[i + 1])
                i += 2
                continue
            i += 1
            continue
        out.append(c)
        i += 1
    txt = re.sub(r"[ \t]+", " ", "".join(out))
    return re.sub(r"\n{3,}", "\n\n", txt).strip()


def clean(txt: str) -> str:
    """이미지 바이너리 잔재를 걷어낸다 — 한글 비율이 낮은 줄은 버린다."""
    keep = []
    for ln in txt.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        han = len(HANGUL.findall(ln))
        if han and han / len(ln) >= 0.25:
            keep.append(ln)
    return "\n".join(keep)


# ── 2. 조문 하나 꺼내기 ──────────────────────────────────────────────
def article(text: str, no: str) -> list[str]:
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        m = HEAD.match(ln)
        if m and m.group(1) == no and not m.group(2):
            start = i
            break
    if start is None:
        return []
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if HEAD.match(lines[j]):
            end = j
            break
    return lines[start:end]


# ── 3. 문항의 인용을 원문과 대조 ─────────────────────────────────────
def fragments(html: str) -> list[str]:
    """인용문에서 편집 흔적을 걷어내고 문장 조각으로 자른다.

    **블록 경계를 먼저 개행으로 바꾼다.** 안 그러면 다음 호의 번호나 다음 조의
    제목이 앞 문장에 딸려 붙어 원문과 안 맞는다 — 실제로 그렇게 오탐이 났다.
    각주(`class="note"`)는 집필자가 쓴 말이므로 아예 뺀다.
    """
    t = re.sub(r'<p class="note">.*?</p>', " ", html, flags=re.S)
    t = re.sub(r"</(?:p|div|tr|li)>|<br\s*/?>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = (t.replace("&lt;", "<").replace("&gt;", ">")
          .replace("&nbsp;", " ").replace("　", " "))
    out = []
    for seg in re.split(r"[.。]\s|\n", t):
        seg = re.sub(r"^\s*[①-⑮]\s*", "", seg.strip())
        seg = re.sub(r"^\d+(?:의\d+)?\.\s*", "", seg)
        # 호 번호가 문장 끝에 남는 경우도 잘라 낸다 (「… 장기요양급여  3」)
        seg = re.sub(r"\s+\d+(?:의\d+)?$", "", seg).strip()
        # 생략(…)이 든 조각은 원문과 이어지지 않으므로 대조 대상이 아니다.
        # 꺾쇠(<)가 남았으면 제목 줄이라 역시 뺀다.
        if len(seg) >= MIN_FRAGMENT and "…" not in seg and "<" not in seg:
            out.append(seg)
    return out


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


TITLE = re.compile(r'<div class="box-title">(.*?)</div>', re.S)
LAW_NAME = re.compile(r"[가-힣]{2,}(?:법|법률)\b")


def cites_statute(box: str, law_n: str) -> bool:
    """이 박스가 **실제 법령을 인용한 것**인가.

    조 번호 꼴(`제57조(…)`)만으로는 가릴 수 없다. 가상 규정도 법령 형식을
    그대로 흉내 내기 때문이다(r1_public 의 가상 규정 22조각이 그렇게 걸렸다).

    그래서 **박스 제목에 법령명을 밝혔고, 그 법령명이 원문에 실제로 있는
    경우**만 대조한다. 출처를 밝히는 것이 검증의 조건이 되는 셈이라
    규율로도 맞다 — 밝히지 않은 인용은 애초에 검증할 수 없다.
    """
    if not CITED.search(re.sub(r"<[^>]+>", "", box)):
        return False
    m = TITLE.search(box)
    if not m:
        return False
    title = re.sub(r"<[^>]+>", "", m.group(1)).replace("&lt;", "").replace("&gt;", "")
    return any(norm(name) in law_n for name in LAW_NAME.findall(title))


def check_round(law: str, round_tag: str) -> int:
    import importlib

    law_n = norm(law)
    cfg = importlib.import_module(f"rounds.{round_tag}.config")
    bad = tot = 0
    for mod, area, _n in cfg.AREAS:
        m = importlib.import_module(f"rounds.{round_tag}.content.{mod}")
        for b in m.BLOCKS:
            fields = [("지문", b.get("passage") or "")]
            fields += [(f"{q.get('type', '')} 자료", q.get("material") or "")
                       for q in b["questions"]]
            for name, html in fields:
                if not html:
                    continue
                # **박스 단위로 가른다.** 한 자료 안에 법령 박스와 「고시로 정한
                # 사항」 안내 박스가 나란히 오는 일이 있다 — 안내는 조문이 아니라
                # 원문에 없는 것이 정상이므로 통째로 대조하면 오탐이 난다.
                for box in re.split(r'(?=<div class="box">)', html):
                    if not cites_statute(box, law_n):
                        continue      # 실제 법령 인용이 아닌 박스는 건너뛴다
                    for f in fragments(box):
                        fn = norm(f)
                        if len(fn) < MIN_FRAGMENT:
                            continue
                        tot += 1
                        if fn not in law_n:
                            bad += 1
                            print(f"  [어긋남] {area} {name}: {f[:66]}")
    print(f"\n조문 조각 {tot}개 대조 · 원문에 없는 것 {bad}개")
    if tot == 0:
        print("  ※ 이 회차에는 조문을 인용한 자료가 없다.")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("extract", help="법령 .doc(RTF) → 본문 텍스트")
    p1.add_argument("src")
    p2 = sub.add_parser("article", help="조문 하나를 꺼낸다")
    p2.add_argument("txt")
    p2.add_argument("no")
    p3 = sub.add_parser("check", help="문항의 인용을 원문과 대조한다")
    p3.add_argument("txt")
    p3.add_argument("--round", required=True)
    a = ap.parse_args()

    if a.cmd == "extract":
        raw = pathlib.Path(a.src).read_text(encoding="latin-1")
        print(clean(rtf_to_text(raw)))
        return 0
    text = pathlib.Path(a.txt).read_text(encoding="utf-8")
    if a.cmd == "article":
        lines = article(text, a.no)
        if not lines:
            print(f"제{a.no}조를 찾지 못했다.")
            return 1
        print("\n".join(lines))
        return 0
    return check_round(text, a.round)


if __name__ == "__main__":
    raise SystemExit(main())
