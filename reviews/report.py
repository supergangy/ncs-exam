# -*- coding: utf-8 -*-
"""필기후기 DB → 기관별 최신 출제경향 보고서.

    python reviews/report.py                       # 전 기관 요약
    python reviews/report.py --org 건보            # 한 기관만
    python reviews/report.py --md > docs/RECENT_TRENDS.md

후기는 주관적 기억이므로 **표본 수를 항상 함께 낸다.** 2건짜리 경향은 경향이 아니다.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB = Path(__file__).resolve().parent / "db.json"

# 표본이 이보다 적으면 경향으로 읽지 말라고 표시한다.
MIN_SAMPLE = 5


def load() -> list[dict]:
    if not DB.exists():
        raise SystemExit("[중단] db.json 이 없습니다. reviews/ingest.py 로 먼저 적재하십시오.")
    return json.loads(DB.read_text(encoding="utf-8"))


def freq(rows: list[dict], key: str) -> list[tuple[str, int]]:
    c = Counter()
    for r in rows:
        v = r.get(key)
        c.update(v if isinstance(v, list) else ([v] if v else []))
    return c.most_common()


def bar(n: int, total: int, width: int = 18) -> str:
    return "█" * max(1, round(n / total * width)) if total else ""


def section(org: str, rows: list[dict], md: bool) -> list[str]:
    rows = sorted(rows, key=lambda r: r.get("date") or "", reverse=True)
    n = len(rows)
    dates = [r["date"] for r in rows if r.get("date")]
    span = f"{dates[-1]} ~ {dates[0]}" if dates else "시행일 미상"

    out = []
    h = f"## {org}" if md else f"\n{'=' * 60}\n{org}"
    out.append(h)
    out.append("")
    caveat = "" if n >= MIN_SAMPLE else \
        f"  ⚠️ 표본 {n}건 — 경향으로 읽기에 부족하다 (권장 {MIN_SAMPLE}건 이상)"
    out.append(f"후기 **{n}건** · {span}{caveat}")
    out.append("")

    q = Counter(r["total_q"] for r in rows if r.get("total_q"))
    m = Counter(r["total_min"] for r in rows if r.get("total_min"))
    if q or m:
        out.append(f"- **시험 구성** — "
                   + " · ".join(f"{k}문항({v})" for k, v in q.most_common(3))
                   + " / " + " · ".join(f"{k}분({v})" for k, v in m.most_common(3)))

    for label, key in (("영역", "areas"), ("출제 유형", "types"), ("소재", "topics")):
        f = freq(rows, key)
        if not f:
            continue
        out.append("")
        out.append(f"### {label}")
        out.append("")
        if md:
            out.append(f"| {label} | 언급 | 비율 |")
            out.append("|---|---|---|")
            for k, v in f:
                out.append(f"| {k} | {v} | {v / n * 100:.0f}% |")
        else:
            for k, v in f:
                out.append(f"  {k:<14} {v:>3}건 {bar(v, n)}")

    # 응시자가 직접 적은 출제 소재. 이 절이 후기에서 가장 값어치 있다.
    kw = defaultdict(Counter)
    for r in rows:
        for area, ws in (r.get("keywords") or {}).items():
            kw[area].update(ws)
    if kw:
        out.append("")
        out.append("### 출제 키워드 (응시자 기재)")
        out.append("")
        for area in sorted(kw, key=lambda a: -sum(kw[a].values())):
            items = [f"{w}" + (f" ×{c}" if c > 1 else "") for w, c in kw[area].most_common()]
            if md:
                out.append(f"- **{area}** — {' · '.join(items)}")
            else:
                out.append(f"  [{area}]")
                for chunk in (items[i:i + 4] for i in range(0, len(items), 4)):
                    out.append("    " + " · ".join(chunk))

    for label, key in (("체감 난이도", "difficulty"), ("시간 압박", "time_pressure")):
        f = freq(rows, key)
        if f:
            out.append("")
            out.append(f"- **{label}** — " + " · ".join(f"{k} {v}건" for k, v in f))

    out.append("")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", help="기관 약칭. 생략하면 전 기관")
    ap.add_argument("--md", action="store_true", help="마크다운으로 출력")
    args = ap.parse_args()

    rows = load()
    if args.org:
        rows = [r for r in rows if r["org"] == args.org]
        if not rows:
            raise SystemExit(f"[중단] '{args.org}' 후기가 없습니다.")

    by_org = defaultdict(list)
    for r in rows:
        by_org[r["org"]].append(r)

    lines = []
    if args.md:
        lines += [
            "# 필기후기 기반 최신 출제경향",
            "",
            "실제 시행 시험 응시자 후기를 기관별로 집계한 것이다. "
            "`reviews/report.py` 가 `reviews/db.json` 에서 자동 생성한다.",
            "",
            "**시판 모의고사 실측(`docs/INSTITUTION_PROFILES.md`)보다 신뢰도가 높다.** "
            "다만 후기는 주관적 기억이고 표본이 작으므로, 각 절의 후기 건수를 먼저 본다.",
            "",
            f"수집 총계: **{len(rows)}건 / {len(by_org)}개 기관**",
            "",
        ]

    for org in sorted(by_org, key=lambda o: -len(by_org[o])):
        lines += section(org, by_org[org], args.md)

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
