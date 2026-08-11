# -*- coding: utf-8 -*-
"""후기 출제 빈도 × 은행 보유량 대조 — **다음에 무엇을 만들지 숫자로 정한다.**

    python tools/gap.py                      # 전 기관
    python tools/gap.py --org 한국철도공사
    python tools/gap.py --md > docs/GAP.md

## 왜 있는가

`reviews/report.py` 는 「후기에 무엇이 몇 건 나왔나」를 낸다.
`export_bank.py` 는 「은행에 무엇이 몇 개 있나」를 낸다.
**둘을 맞대 본 적이 없다.** 그래서 다음 문항을 감으로 만들었다.

여기서는 후기 언급 비율과 은행 보유 비율을 나란히 놓고 **모자란 쪽**을 짚는다.

## 규율

- **점유율로 견준다.** 후기 하나가 여러 영역을 언급하므로 「언급한 후기 비율」을
  그대로 쓰면 합이 100%를 넘어(코레일은 124%) 은행 비중과 맞댈 수 없다.
  분모는 **그 기관의 전체 언급 수**다. `report.py` 의 언급률(분모=후기 수)과는
  다른 수치이니, 그 값도 괄호로 함께 적어 둔다.
- 표본 5건 미만은 경향으로 읽지 않는다 (`MIN_SAMPLE`).
- **매핑되지 않은 은행 유형을 반드시 세어 보고한다.** 「0건」이 「없다」인지
  「사전에 없다」인지 구분되지 않으면 분석이 거짓말을 한다 (`D51`·`D54`).
- 후기가 한 번도 안 적은 영역의 「－」는 **은행이 과하다**는 뜻이 아니다.
  그 기관이 안 낸다는 뜻일 수도, 응시자가 안 적었다는 뜻일 수도 있다.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
DB = ROOT / "reviews" / "db.json"
BANK = ROOT / "app" / "data" / "bank.json"

MIN_SAMPLE = 5

# 후기의 영역 표기(짧은 말)와 은행의 과목명(`sj`)을 잇는다.
AREA = {
    "의사소통": "의사소통능력",
    "수리": "수리능력",
    "문제해결": "문제해결능력",
    "자원관리": "자원관리능력",
    "정보": "정보능력",
    "기술": "기술능력",
    "조직이해": "조직이해능력",
    "직업윤리": "직업윤리",
}

# 후기의 유형 11종 ← 은행 유형(`ty`) 을 잇는 낱말.
# 은행 유형이 127종으로 잘게 쪼개져 있어 낱말로 걸러 묶는다.
# 어느 것에도 안 걸린 유형은 「미매핑」으로 따로 센다 — 그게 사전의 구멍이다.
TYPE_WORDS = {
    "자료해석": ["자료해석", "증감률", "비중", "표해석", "그래프"],
    "내용일치": ["내용일치", "일치", "세부내용"],
    "추론": ["추론", "빈칸", "내용추론", "원인추론"],
    "조건추리": ["조건추리", "조건추론", "조건대조", "명제", "참거짓", "논리오류", "배정", "순서"],
    "규정적용": ["규정", "약관", "사례판정", "절차적용", "조항", "행동강령", "매뉴얼"],
    "계산": [
        "계산", "금액", "산출", "원가", "할인", "일률", "거리", "속력", "시간계산",
        "농도", "확률", "경우의", "최소공배수", "나머지", "간격", "도형", "증감",
        "진법", "규칙찾기", "곱셈", "시계", "값짝", "사양산정", "감가상각", "환율",
    ],
    "모듈": ["모듈", "기술이해", "기술선택", "기술적용", "산업재해", "관리원칙", "직업윤리"],
    "코드": ["코드", "코딩", "알고리즘", "순서도"],
    "엑셀": ["엑셀", "함수", "스프레드"],
}

# 「피셋형」·「피듈형」은 **유형이 아니라 시험 성격**이다. 응시자가 「이 시험은
# 피듈형이었다」고 적은 것이라, 같은 후기에 모듈·코드·조건추리가 함께 붙는다.
# 은행 유형과 맞대면 「피듈형 0문항」이라는 뜻 없는 구멍이 생긴다 —
# 유형 표에서 빼고 따로 센다.
STYLE = ("피셋형", "피듈형")


def load_reviews() -> list[dict]:
    if not DB.exists():
        raise SystemExit("[중단] reviews/db.json 이 없습니다.")
    return json.loads(DB.read_text(encoding="utf-8"))


def load_bank() -> dict:
    if not BANK.exists():
        raise SystemExit("[중단] app/data/bank.json 이 없습니다. tools/export_bank.py 를 먼저.")
    return json.loads(BANK.read_text(encoding="utf-8"))


def classify(ty: str) -> list[str]:
    """은행 유형 하나를 후기 유형 여러 개에 붙인다 (겹칠 수 있다)."""
    hit = [k for k, ws in TYPE_WORDS.items() if any(w in ty for w in ws)]
    return hit


def bar(v: float, width: int = 14) -> str:
    return "█" * max(0, round(v * width))


def area_table(rows: list[dict], bank_items: list[dict]) -> list[tuple]:
    """(영역, 언급 점유율, 언급 건수, 언급률, 은행 수, 은행 비중, 격차) — 격차 큰 순."""
    n = len(rows)
    said = collections.Counter()
    for r in rows:
        said.update(r.get("areas") or [])
    total_said = sum(said.values()) or 1
    have = collections.Counter(i["sj"] for i in bank_items)
    total_have = sum(have.values()) or 1

    out = []
    for short, full in AREA.items():
        share = said[short] / total_said           # 언급 점유율 — 합이 100%
        rate = said[short] / n if n else 0.0       # 언급률 — report.py 와 같은 수치
        got = have[full] / total_have              # 은행에서 차지하는 비중
        out.append((short, share, said[short], rate, have[full], got, share - got))
    return sorted(out, key=lambda x: -x[6])


def type_table(rows: list[dict], bank_items: list[dict]) -> tuple[list[tuple], int, list[str]]:
    n = len(rows)
    said = collections.Counter()
    for r in rows:
        said.update(t for t in (r.get("types") or []) if t not in STYLE)
    total_said = sum(said.values()) or 1

    have = collections.Counter()
    unmapped: list[str] = []
    for i in bank_items:
        hit = classify(i["ty"])
        if hit:
            # 한 문항이 여러 유형에 걸리면 나눠 준다 — 그래야 합이 문항 수와 같다.
            for k in hit:
                have[k] += 1 / len(hit)
        else:
            unmapped.append(f"{i['sj']}/{i['ty']}")
    total_have = sum(have.values()) or 1

    out = []
    for k in TYPE_WORDS:
        share = said[k] / total_said
        rate = said[k] / n if n else 0.0
        got = have[k] / total_have
        out.append((k, share, said[k], rate, have[k], got, share - got))
    return sorted(out, key=lambda x: -x[6]), total_have, unmapped


def render(org: str, rows: list[dict], bank_items: list[dict], md: bool) -> list[str]:
    n = len(rows)
    o: list[str] = []
    o.append(f"## {org}" if md else f"\n{'=' * 66}\n{org}")
    o.append("")
    if n < MIN_SAMPLE:
        o.append(f"후기 {n}건 — 표본이 적어 경향으로 읽지 않는다 (권장 {MIN_SAMPLE}건 이상)")
        return o
    o.append(f"후기 **{n}건** · 은행 NCS **{len(bank_items)}문항** 기준")
    o.append("")
    o.append("격차 = 후기 **언급 점유율** − 은행 보유 비중. **＋ 면 모자라다.**")
    o.append("괄호의 건수·언급률은 참고값이다 (후기 하나가 여러 영역을 언급하므로 합이 100%를 넘는다).")
    o.append("")

    if md:
        o.append("| 영역 | 후기 점유율 | 은행 보유 | 격차 |")
        o.append("|---|---|---|---|")
    for short, share, said_n, rate, have_n, got, gap in area_table(rows, bank_items):
        mark = "＋" if gap > 0.05 else ("－" if gap < -0.05 else " ")
        if md:
            o.append(f"| {short} | {share*100:.0f}% ({said_n}건·언급률 {rate*100:.0f}%) | "
                     f"{have_n}문항 ({got*100:.0f}%) | {mark}{abs(gap)*100:.0f}%p |")
        else:
            o.append(f"  {short:<8} 후기 {share*100:>3.0f}% {bar(share)}"
                     f"   은행 {got*100:>3.0f}% ({have_n:>3}) {bar(got)}"
                     f"   {mark}{abs(gap)*100:.0f}%p")

    tt, total_have, unmapped = type_table(rows, bank_items)
    o.append("")
    o.append("### 유형" if md else "\n  ── 유형 ──")
    o.append("")
    if md:
        o.append("| 유형 | 후기 점유율 | 은행 보유 | 격차 |")
        o.append("|---|---|---|---|")
    for k, share, said_n, rate, have_n, got, gap in tt:
        if said_n == 0 and have_n == 0:
            continue
        mark = "＋" if gap > 0.05 else ("－" if gap < -0.05 else " ")
        if md:
            o.append(f"| {k} | {share*100:.0f}% ({said_n}건·언급률 {rate*100:.0f}%) | "
                     f"{have_n:.0f}문항 ({got*100:.0f}%) | {mark}{abs(gap)*100:.0f}%p |")
        else:
            o.append(f"  {k:<8} 후기 {share*100:>3.0f}% {bar(share)}"
                     f"   은행 {got*100:>3.0f}% ({have_n:>4.0f}) {bar(got)}"
                     f"   {mark}{abs(gap)*100:.0f}%p")

    # 시험 성격은 유형과 견줄 것이 아니라, 그 기관 시험이 어떤 결인지 알려 주는 값이다.
    style = collections.Counter()
    for r in rows:
        style.update(t for t in (r.get("types") or []) if t in STYLE)
    if style:
        o.append("")
        o.append("시험 성격 — " + " · ".join(
            f"{k} {v}건({v / n * 100:.0f}%)" for k, v in style.most_common()))

    if unmapped:
        c = collections.Counter(unmapped)
        o.append("")
        o.append(f"⚠️ 유형 사전에 걸리지 않은 은행 문항 **{len(unmapped)}개** "
                 f"({len(c)}종) — 이만큼은 위 유형 표에 안 들어갔다")
        for t, k in c.most_common(12):
            o.append(f"     {t} ({k})")
    return o


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", help="한 기관만")
    ap.add_argument("--md", action="store_true", help="마크다운으로")
    ap.add_argument("--min", type=int, default=30, help="이 건수 이상인 기관만 (기본 30)")
    a = ap.parse_args()

    reviews = load_reviews()
    bank = load_bank()
    ncs = [i for i in bank["items"] if i["tr"] == "ncs"]

    by_org = collections.defaultdict(list)
    for r in reviews:
        by_org[r.get("org") or "미상"].append(r)

    lines: list[str] = []
    if a.md:
        lines += [
            "# 출제 빈도 × 은행 보유량 대조",
            "",
            "**표는 `python tools/gap.py --md > docs/GAP.md` 로 다시 만든다.**",
            "그 뒤 아래 「읽는 법」과 「결론」 절을 사람이 다시 붙인다 —",
            "판정은 숫자만으로 나오지 않으므로 도구가 대신 쓸 수 없다.",
            "붙이는 글은 `docs/GAP_NOTES.md` 에 있다.",
            "",
            f"후기 {len(reviews)}건 · 은행 NCS {len(ncs)}문항",
            "",
        ]

    targets = [a.org] if a.org else [
        o for o, rs in sorted(by_org.items(), key=lambda x: -len(x[1]))
        if len(rs) >= a.min
    ]
    for org in targets:
        rows = by_org.get(org)
        if not rows:
            print(f"[건너뜀] {org} — 후기가 없습니다", file=sys.stderr)
            continue
        lines += render(org, rows, ncs, a.md)

    print("\n".join(lines))


if __name__ == "__main__":
    main()
