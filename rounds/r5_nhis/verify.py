# -*- coding: utf-8 -*-
"""r5_nhis 계산형 문항의 답을 **다시 구해** 문항과 대조한다.

`tools/verify_ncs.py` 는 `ncs-*` 공통 문항만 다룬다(139건). 회차 문항은
지금까지 어느 회차도 기계 검증을 받지 않았다 — 이 파일이 그 첫 번째다.

규율은 `verify_ncs.py` 와 같다.

* **선지 번호를 계산 함수 안에 적지 않는다.** 계산은 값을 내고, 그 값을
  선지 번호로 옮기는 일은 따로 한다. 그래야 `reorder_choices.py` 로
  선지를 섞어도 검증이 따라온다.
* 지문 독해·어문 규범은 계산으로 확정되지 않으므로 다루지 않는다.

    python rounds/r5_nhis/verify.py
"""
from __future__ import annotations

import pathlib
import sys
from fractions import Fraction as F
from itertools import permutations

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ── 자료 (문항 지문에서 옮겨 적는다 — 고치면 여기도 고쳐야 어긋남이 잡힌다) ──
PAY = {2021: 8_420, 2022: 9_180, 2023: 10_190, 2024: 11_310}   # 요양급여비용(억)

LIMIT = {1: 2_069_900, 2: 1_869_600, 3: 1_455_800,             # 장기요양 월 한도
         4: 1_455_000, 5: 1_249_000}
COPAY, RELIEF = F(15, 100), F(40, 100)                          # 본인부담률 · 감경폭

VISIT_BASE = 45_000                                             # 방문요양 1회
ADD = {"야간": F(30, 100), "휴일": F(30, 100), "심야": F(50, 100)}

GRADE = [(1, 95, None), (2, 75, 95), (3, 60, 75),               # 등급판정 구간
         (4, 51, 60), (5, 45, 51)]                              # (등급, 이상, 미만)

APPLY = {  # 건강생활 지원금 신청자 — 나이 · 체납월 · 검진(년 전) · 월평균 걷기(만 보)
    "갑": (42, 0, 1, 24), "을": (68, 0, 3, 15), "병": (70, 0, 2, 13),
    "정": (35, 2, 1, 32), "무": (51, 0, 1, 31),
}


# ── 계산 ────────────────────────────────────────────────────────────
def v_growth() -> list[float]:
    """24·25 증감률 — 전년 대비 %."""
    yr = sorted(PAY)
    return [round((PAY[b] - PAY[a]) / PAY[a] * 100, 1)
            for a, b in zip(yr, yr[1:])]


def v_combo26() -> set[str]:
    """26 <보기> 조합형 — 옳은 보기의 라벨 집합."""
    yr = sorted(PAY)
    gaps = [PAY[b] - PAY[a] for a, b in zip(yr, yr[1:])]
    ok = set()
    if gaps == sorted(gaps) and len(set(gaps)) == len(gaps):
        ok.add("ㄱ")                                   # 증가액이 매년 커짐
    if all(g >= 1_000 for g in gaps):
        ok.add("ㄴ")                                   # 매년 1,000억 이상
    if PAY[2024] < PAY[2021] * F(3, 2):
        ok.add("ㄷ")                                   # 1.5배에 못 미침
    if sum(PAY.values()) > 40_000:
        ok.add("ㄹ")                                   # 합 4조 초과
    return ok


def v_over(used: int, grade: int) -> int:
    """41 월 한도 초과액."""
    return max(0, used - LIMIT[grade])


def v_burden(used: int, grade: int, relief: bool = False) -> F:
    """42 본인부담 총액 — 한도 안은 부담률, 초과분은 전액."""
    inside = min(used, LIMIT[grade])
    rate = COPAY * (1 - RELIEF) if relief else COPAY
    return inside * rate + v_over(used, grade)


def v_relief_rate() -> F:
    """43 감경 후 본인부담률."""
    return COPAY * (1 - RELIEF)


def v_visit(*kinds: str) -> F:
    """44 방문요양 급여비용 — 가산은 중복 없이 가장 높은 하나만."""
    top = max((ADD[k] for k in kinds), default=F(0))
    return VISIT_BASE * (1 + top)


def v_grade(score: int) -> int | None:
    """45 등급 판정 — 「이상 ~ 미만」."""
    for g, lo, hi in GRADE:
        if score >= lo and (hi is None or score < hi):
            return g
    return None


def _walk_ok(age: int, walk: int) -> bool:
    return walk >= (12 if age >= 65 else 20)


def v_eligible() -> set[str]:
    """46 지원금 대상 — 세 요건을 모두 갖춘 사람."""
    return {n for n, (age, due, exam, walk) in APPLY.items()
            if due == 0 and exam <= 2 and _walk_ok(age, walk)}


def v_payout() -> int:
    """47 지급 총액 — 30만 보 이상이면 90,000원."""
    return sum(90_000 if APPLY[n][3] >= 30 else 60_000 for n in v_eligible())


def v_missing(who: str) -> set[str]:
    """48 모자란 요건."""
    age, due, exam, walk = APPLY[who]
    miss = set()
    if due: miss.add("체납")
    if exam > 2: miss.add("검진")
    if not _walk_ok(age, walk): miss.add("걷기")
    return miss


def v_tour() -> list[tuple[str, ...]]:
    """49·50 순회 순서 — 조건 넷을 모두 만족하는 순열."""
    return [p for p in permutations("ABCDE")
            if p[0] == "A"                                   # A 가 첫째
            and p.index("C") == p.index("E") + 1             # C 는 E 바로 다음
            and p[-1] == "D"                                 # D 가 마지막
            and p.index("B") < p.index("E")]                 # B 가 E 보다 먼저


def v_tour_relaxed() -> list[tuple[str, ...]]:
    """51 마지막 조건을 뺐을 때."""
    return [p for p in permutations("ABCDE")
            if p[0] == "A"
            and p.index("C") == p.index("E") + 1
            and p[-1] == "D"]


def v_true50() -> set[str]:
    """50 <보기> 조합형 — 유일해에 비추어 옳은 보기."""
    (order,) = v_tour()
    day = {s: i + 1 for i, s in enumerate(order)}
    ok = set()
    if day["B"] < day["C"]:                       ok.add("ㄱ")
    if abs(day["B"] - day["E"]) == 1:             ok.add("ㄴ")
    if day["B"] - day["A"] > 1:                   ok.add("ㄷ")
    if day["C"] == 4:                             ok.add("ㄹ")
    return ok


# ── 문항이 주장하는 값 ──────────────────────────────────────────────
CASES = [
    ("24·25 증감률(%)",       v_growth(),                    [9.0, 11.0, 11.0]),
    ("26 옳은 보기",           v_combo26(),                   {"ㄱ", "ㄷ"}),
    ("41 한도 초과액",         v_over(1_680_000, 4),          225_000),
    ("42 본인부담 총액",       v_burden(1_680_000, 4),        F(443_250)),
    ("43 감경 후 부담률(%)",   v_relief_rate() * 100,         F(9)),
    ("44 일요일 22시 급여비",  v_visit("야간", "휴일", "심야"), F(67_500)),
    ("45 60점의 등급",         v_grade(60),                   3),
    ("46 지원 대상",           v_eligible(),                  {"갑", "병", "무"}),
    ("47 지급 총액",           v_payout(),                    210_000),
    ("48 을에게 모자란 것",    v_missing("을"),               {"검진"}),
    ("49 순회 순서(유일해)",   v_tour(),                      [tuple("ABECD")]),
    ("50 옳은 보기",           v_true50(),                    {"ㄱ", "ㄴ", "ㄹ"}),
    ("51 조건 하나를 뺀 경우수", len(v_tour_relaxed()),        2),
]


def main() -> int:
    bad = 0
    for name, got, want in CASES:
        ok = got == want
        bad += not ok
        mark = "✔" if ok else "✘"
        print(f"   {mark} {name:22} {got}" + ("" if ok else f"   ← 문항은 {want}"))
    print()
    print(f"검증 {len(CASES)}건 · 불일치 {bad}건")
    if not bad:
        print("   ※ 지문 독해·어휘·모듈 개념 문항은 계산으로 확정되지 않아 여기서 다루지 않는다.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
