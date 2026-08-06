# -*- coding: utf-8 -*-
"""오답노트 PDF — 앱에서 내보낸 목록을 인쇄본으로 굽는다.

앱(`app/`)의 오답노트에서 「PDF 용으로 내보내기」를 누르면 `wrongnote-YYYYMMDD.json`
이 내려온다. 그 파일을 여기 넣으면 **문제와 해설이 함께** 실린 PDF 가 나온다.

```bash
python tools/wrongnote_pdf.py wrongnote-20260806.json
python tools/wrongnote_pdf.py --ids major-csdb-common-003,r4_korail-06
python tools/wrongnote_pdf.py --risk high          # 검토용 — high 25건을 통째로
```

**파이프라인을 새로 만들지 않는다.** `build.py` 를 그대로 불러 쓴다 —
Jinja2 → Chrome `--print-to-pdf` → pypdf 쪽번호. 해설지 서식(`solution.html.j2`)도
그대로다. 여기서 하는 일은 **문항을 모아 블록 모양으로 세우는 것**뿐이다.
"""

from __future__ import annotations

import argparse
import datetime
import importlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402  — 경로를 넣은 뒤에 불러야 한다


class Shim:
    """`build.build_html` 이 읽는 회차 설정 자리. 오답노트는 회차가 아니므로 흉내만 낸다."""

    def __init__(self, n: int, title: str):
        self.BRAND = "NCS 기출은행"
        self.EXAM_TITLE = "오답노트"
        self.EXAM_ROUND = title
        self.TOTAL_Q = n
        self.TOTAL_MIN = 0
        self.AREAS: list[tuple[str, str, int]] = []
        self.RATIONALE_INTRO = None


def collect() -> dict[str, dict]:
    """회차와 은행의 모든 문항을 id → 블록 조각으로.

    `export_bank.py` 와 **같은 자료원**을 쓴다. 앱이 내보낸 id 가 그대로 맞아야 한다.
    """
    import tools.export_bank as ex
    r_items, _ = ex.load_rounds()
    return {it["id"]: it for it in (r_items + ex.load_bank())}


def to_blocks(items: list[dict]) -> list[dict]:
    """`build.py` 가 기대하는 블록 모양으로 세운다.

    세트문항이라도 **낱개로 편다** — 오답노트는 틀린 것만 모으므로 같은 지문의
    다른 문항이 함께 오지 않을 수 있다. 지문은 문항마다 붙인다.
    """
    blocks = []
    for no, it in enumerate(items, 1):
        q = {
            "no": no,
            "stem": it["stem"],
            "choices": list(it["choices"]),
            "answer": it["answer"],
            "material": it.get("material"),
            "type": it.get("type") or "",
            "explain": it.get("explain") or "",
            "each": list(it.get("each") or []),
            "why": None,                      # 출제 이유서는 학습자용이 아니다
        }
        blocks.append({
            "blk": no - 1,
            "area": it.get("subject") or "기타",
            "lead": it.get("lead"),
            "passage": it.get("passage"),
            "questions": [q],
            "first_no": no, "last_no": no,
            "pagebreak": False, "spread_break": False,
        })
    return blocks


def main() -> int:
    ap = argparse.ArgumentParser(description="오답노트 PDF")
    ap.add_argument("file", nargs="?", help="앱이 내보낸 wrongnote-*.json")
    ap.add_argument("--ids", help="쉼표로 나눈 문항 id")
    ap.add_argument("--risk", choices=("low", "mid", "high"),
                    help="위험도로 추려 굽는다 (검토용)")
    ap.add_argument("--title", default=None, help="표지에 넣을 이름")
    ap.add_argument("--out", default=None, help="내보낼 경로")
    a = ap.parse_args()

    have = collect()

    ids: list[str] = []
    if a.file:
        raw = json.loads(pathlib.Path(a.file).read_text(encoding="utf-8"))
        # 오답노트는 {ids:[…]}, 표시 목록은 {items:[{id…}]} 다. 둘 다 받는다
        ids = raw.get("ids") or [x["id"] for x in raw.get("items", [])]
    if a.ids:
        ids += [s.strip() for s in a.ids.split(",") if s.strip()]
    if a.risk:
        ids += [i for i, it in have.items() if it.get("risk") == a.risk]

    if not ids:
        print("[중단] 문항을 하나도 못 받았다.\n"
              "  앱의 오답노트에서 「PDF 용으로 내보내기」를 누르거나 --ids 를 준다.")
        return 1

    seen, order = set(), []
    for i in ids:                              # 순서를 지키며 중복만 제거
        if i not in seen:
            seen.add(i); order.append(i)

    miss = [i for i in order if i not in have]
    if miss:
        print(f"[중단] 은행에 없는 id 가 {len(miss)}개 있다: {miss[:5]}\n"
              "  문항을 지운 뒤에 내보낸 목록일 수 있다. "
              "`python tools/export_bank.py` 를 다시 돌려 앱을 갱신하십시오.")
        return 1

    picked = [have[i] for i in order]
    # 회차 문항이면 원래 번호대로, 은행 문항은 뒤에 — 종이에서 찾기 쉽게
    picked.sort(key=lambda it: (it.get("round") or "zz", it.get("no") or 0, it["id"]))

    title = a.title or (f"오답노트 {datetime.date.today():%Y-%m-%d}")
    blocks = to_blocks(picked)

    build.ROUND = "wrongnote"
    build.CFG = Shim(len(blocks), title)
    build.OUT = ROOT / "out" / "wrongnote"
    build.OUT.mkdir(parents=True, exist_ok=True)

    html = build.build_html(blocks, "solution")
    stem = a.out or f"오답노트_{datetime.date.today():%Y%m%d}"
    html_path = build.OUT / f"{stem}.html"
    pdf_path = build.OUT / f"{stem}.pdf"
    html_path.write_text(html, encoding="utf-8")

    build.html_to_pdf(html_path, pdf_path)
    pages = build.stamp_page_numbers(pdf_path, skip_first=0)

    by_src: dict[str, int] = {}
    for it in picked:
        by_src[it.get("round") or "문항은행"] = by_src.get(it.get("round") or "문항은행", 0) + 1

    print(f"■ {pdf_path.relative_to(ROOT)}   {pages}쪽 · {len(picked)}문항")
    for k, v in by_src.items():
        print(f"   {k:<14} {v}문항")
    print(f"   {html_path.relative_to(ROOT)}  (브라우저로 열어 미리 볼 수 있다)")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
