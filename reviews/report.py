# -*- coding: utf-8 -*-
"""필기후기 DB → 기관별 최신 출제경향 보고서.

    python reviews/report.py                       # 전 기관 요약
    python reviews/report.py --org 건보            # 한 기관만
    python reviews/report.py --md > docs/RECENT_TRENDS.md

후기는 주관적 기억이므로 **표본 수를 항상 함께 낸다.** 2건짜리 경향은 경향이 아니다.
"""
from __future__ import annotations

import argparse
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


UNKNOWN_TERM = "시기 미상"


def term_of(r: dict) -> str:
    """시행 시기. 제목의 「2026 상반기」를 우선하고, 없으면 작성일에서 추정한다."""
    if r.get("term"):
        return r["term"]
    d = r.get("date")
    if d:
        y, m = int(d[:4]), int(d[5:7])
        return f"{y} {'상반기' if m <= 8 else '하반기'}"
    return UNKNOWN_TERM


def term_key(t: str) -> tuple:
    """시기 정렬 키. 문자열로 비교하면 한글 「시기 미상」이 숫자보다 뒤로 가

    가장 최신으로 잡힌다. 미상은 언제나 맨 뒤(가장 오래된 것)로 보낸다.
    """
    return (0, t) if t == UNKNOWN_TERM else (1, t)


def matrix(rows: list[dict]) -> list[str]:
    """기관 × 시행 시기 수집 현황. 어디가 비었는지 한눈에 본다."""
    cells = Counter((r["org"], term_of(r)) for r in rows)
    orgs = sorted({o for o, _ in cells}, key=lambda o: -sum(
        v for (oo, _), v in cells.items() if oo == o))
    terms = sorted({t for _, t in cells}, key=term_key, reverse=True)

    w = max(len(o) for o in orgs) + 2
    out = ["", "기관 × 시행 시기 수집 현황", ""]
    out.append(" " * w + "".join(f"{t:>12}" for t in terms) + f"{'합계':>8}")
    for o in orgs:
        row = [cells.get((o, t), 0) for t in terms]
        out.append(f"{o:<{w}}" + "".join(f"{(str(n) + '건' if n else '·'):>12}"
                                         for n in row) + f"{sum(row):>7}건")
    out.append("")
    out.append("  표본 5건 미만인 칸은 경향으로 읽지 않는다.")

    # 전공 계열별 현황. 전기·전산·토목처럼 직렬이 갈리면 전공 후기도 갈린다.
    maj = Counter((r["org"], r["major"]) for r in rows if r.get("major"))
    if maj:
        out.append("")
        out.append("전공 후기가 함께 담긴 건")
        out.append("")
        for (o, m), n in maj.most_common():
            out.append(f"  {o:<16} {m:<6} {n}건")
        out.append("")
        out.append("  전공은 NCS 모의고사 대상이 아니다. 직렬별 참고용으로만 쌓는다.")
    out.append("")
    return out


def brief(org: str, rows: list[dict]) -> list[str]:
    """회차 설계용 **소재 브리프**.

    후기가 정확한 것만 낸다 — 응시자가 직접 적은 출제 소재, 체감 난이도·시간 압박,
    그리고 유형이 바뀌었다는 신호.

    문항 수·세트 비율·지문 길이·유형 분포 같은 **구조 지표는 내지 않는다.**
    그건 시판본 895문항을 전수 분석한 docs/INSTITUTION_PROFILES.md 가 훨씬 정확하다.
    후기는 주관적 기억이고 표본도 작다.
    """
    # 시기가 확인된 것 중 최신을 기준으로 삼는다. 전부 미상이면 시기를 나누지 않는다.
    known = {term_of(r) for r in rows} - {UNKNOWN_TERM}
    latest = max(known, key=term_key) if known else UNKNOWN_TERM
    cur = [r for r in rows if term_of(r) == latest] if known else list(rows)

    kw = defaultdict(Counter)
    for r in cur:
        for area, ws in (r.get("keywords") or {}).items():
            kw[area].update(ws)
    diff = Counter(r["difficulty"] for r in cur if r.get("difficulty"))
    tp = Counter(r["time_pressure"] for r in cur if r.get("time_pressure"))

    head_term = latest if known else "전 기간(시행 시기 미상)"
    out = ["", "=" * 62, f"{org} — {head_term} 소재 브리프 (후기 {len(cur)}건)", "=" * 62, ""]
    if len(cur) < MIN_SAMPLE:
        out.append(f"⚠️ 표본 {len(cur)}건. 소재를 확정하기 전에 후기를 더 모으십시오.")
        out.append("")
    n_unknown = sum(1 for r in rows if term_of(r) == UNKNOWN_TERM)
    if known and n_unknown:
        out.append(f"※ 시행 시기를 모르는 후기 {n_unknown}건은 빠졌습니다. "
                   "같은 글을 다시 담으면 게시일이 채워집니다.")
        out.append("")

    # 절마다 NCS·전공·법률 중 무엇인지 저장돼 있다. 갈래를 섞으면
    # 「전기이론」이 NCS 영역처럼 보여 모의고사 설계를 오염시킨다.
    kind_of = {}
    for r in cur:
        kind_of.update(r.get("kinds") or {})

    def block(title, want, note=""):
        picked = [a for a in kw if kind_of.get(a, "기타") == want]
        if not picked:
            return
        out.append(f"■ {title}{note}")
        out.append("")
        for area in sorted(picked, key=lambda a: -sum(kw[a].values())):
            out.append(f"  [{area}]")
            items = [w + (f" ×{c}" if c > 1 else "") for w, c in kw[area].most_common()]
            for chunk in (items[i:i + 3] for i in range(0, len(items), 3)):
                out.append("    " + " · ".join(chunk))
        out.append("")

    if kw:
        block("NCS 소재 후보", "ncs", " — 모의고사에 그대로 골라 쓰면 된다.")
        block("전공 소재", "major", " — NCS 모의고사 대상이 아니다. 직렬별 참고용.")
        block("직무시험(법률) 소재", "law", " — NCS 모의고사 대상이 아니다.")
        block("분류 미상", "기타", " — lexicon.py 의 갈래 판정을 손볼 후보.")
    else:
        out.append("■ 소재 후보 — 없음. 「기억 나는 문항 / 출제 키워드」 절이 있는 후기를 모으십시오.")
        out.append("")

    majors = Counter(r["major"] for r in cur if r.get("major"))
    if majors:
        out.append("■ 전공 계열 — " + " · ".join(f"{m} {n}건" for m, n in majors.most_common()))
        out.append("")

    if diff or tp:
        out.append("■ 체감 — 후기로만 알 수 있는 것")
        if diff:
            out.append("  난이도  " + " · ".join(f"{k} {v}건" for k, v in diff.most_common()))
        if tp:
            out.append("  시간    " + " · ".join(f"{k} {v}건" for k, v in tp.most_common()))
        out.append("")

    # 유형이 바뀌었다는 언급. 코퍼스가 낡았다는 경보다.
    hits = sum(1 for r in cur if r.get("change_signal"))
    if hits:
        out.append(f"■ ⚠️ 유형 변화 신호 {hits}건 — 「기존과 다르다」는 언급이 있습니다.")
        out.append("   구조 지표(docs/INSTITUTION_PROFILES.md)가 낡았을 수 있으니 함께 검토하십시오.")
        out.append("")

    # 시기가 확인된 것끼리만 비교한다. 미상 뭉치와 견주면 의미 없는 diff가 나온다.
    prev = sorted(known - {latest}, key=term_key, reverse=True)
    if prev:
        old = [r for r in rows if term_of(r) == prev[0]]
        old_k = {w for r in old for ws in (r.get("keywords") or {}).values() for w in ws}
        new_k = {w for r in cur for ws in (r.get("keywords") or {}).values() for w in ws}
        out.append(f"■ 직전 시기({prev[0]}, {len(old)}건) 대비 소재 변화")
        out.append(f"  새로 나온 소재  {' · '.join(sorted(new_k - old_k)) or '없음'}")
        out.append(f"  이어지는 소재   {' · '.join(sorted(new_k & old_k)) or '없음'}")
        out.append("")

    out.append("─" * 62)
    out.append("문항 수 · 세트 비율 · 지문 길이 · 유형 분포 같은 **구조 지표는 여기서 내지 않는다.**")
    out.append("후기는 주관적 기억이고 표본이 작다. 구조는 시판본 895문항을 전수 분석한")
    out.append("docs/INSTITUTION_PROFILES.md 와 각 회차의 config.py PROFILE 을 쓴다.")
    out.append("")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", help="기관 약칭. 생략하면 전 기관")
    ap.add_argument("--md", action="store_true", help="마크다운으로 출력")
    ap.add_argument("--matrix", action="store_true", help="기관 × 시행 시기 수집 현황")
    ap.add_argument("--brief", metavar="기관",
                    help="그 기관의 최신 시기 소재 브리프 (구조 지표는 코퍼스를 쓴다)")
    args = ap.parse_args()

    if args.matrix:
        print("\n".join(matrix(load())))
        return 0
    if args.brief:
        rs = [r for r in load() if r["org"] == args.brief]
        if not rs:
            raise SystemExit(f"[중단] '{args.brief}' 후기가 없습니다.")
        print("\n".join(brief(args.brief, rs)))
        return 0

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
