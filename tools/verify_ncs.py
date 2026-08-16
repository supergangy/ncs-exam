# -*- coding: utf-8 -*-
"""NCS 문항 검증 — 계산으로 정답을 다시 구해 문항과 대조한다.

직무 문항(`verify_cs.py`)과 목적은 같지만 대상이 다르다.

| 갈래 | 어떻게 확정하나 |
|---|---|
| **수리 계산형** | 다시 계산한다 — 거리·농도·일률·확률·나머지 |
| **조건추리** | **전수 탐색으로 답이 하나뿐인지** 확인한다 |
| 지문 독해 | 지문이 근거를 통제하므로 여기서 다루지 않는다 |
| 어문 규범 | 규범 자료와 대조. 계산이 아니라 사람이 본다 |

`verify_cs.py` 와 같은 규율이다 — **선지 번호를 검증 함수 안에 적지 않는다.**
계산과 배치를 갈라 두어야 선지 순서를 바꿔도 검증이 따라온다.

```bash
python tools/verify_ncs.py
python tools/verify_ncs.py --subject math
```
"""

from __future__ import annotations

import argparse
import math
import pathlib
import sys
from fractions import Fraction as F
from itertools import permutations

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ── 규정적용 (bank/_common/ncs_rule.py) ─────────────────────────────────
#
# 가상 규정의 배수·비율·한도를 **여기 다시 적고** 답을 계산한다.
# 규정을 고치면서 해설만 안 고치는 사고를 잡는다.

# ○○공사 여객운송약관(가상)의 수치
_MULT_NOTICKET, _MULT_DISCOUNT, _MULT_HELD = 30, 10, 30
_REFUND = {"1일전": 0.00, "1시간이내": 0.05, "출발후": 0.15}
_DELAY = ((20, 40, 0.125), (40, 60, 0.25), (60, 10**9, 0.50))
# 정기승차권 규정(가상)
_PASS_TRIPS, _PASS_DC = 44, {"일반": 0.45, "학생": 0.60}
# 위임전결규정(가상) — (상한, 전결권자)
_DELEG = ((5_000_000, "팀장"), (20_000_000, "부장"),
          (100_000_000, "본부장"), (float("inf"), "사장"))


def _deleg(amount: float) -> str:
    for cap, who in _DELEG:
        if amount <= cap:
            return who
    raise AssertionError


def v_rule_surcharge() -> tuple[int, str]:
    fare = 2700
    total = fare + fare * _MULT_NOTICKET
    return (total, f"기준 {fare:,} + 부가 {fare*_MULT_NOTICKET:,}"
                   f"({_MULT_NOTICKET}배) = {total:,}원")


def v_rule_exempt() -> tuple[int, str]:
    """부가운임을 받지 않는 경우의 선지 번호. 제12조 제3항 단서 하나뿐."""
    cases = {
        1: _MULT_NOTICKET,      # 승차권 없음
        2: _MULT_DISCOUNT,      # 할인 자격 없음
        3: _MULT_HELD,          # 소지했으나 미확인
        4: 0,                   # 스스로 신고 → 단서로 면제
        5: _MULT_NOTICKET,      # 적발
    }
    free = [k for k, v in cases.items() if v == 0]
    assert len(free) == 1, f"면제는 하나여야 한다: {free}"
    return (free[0], f"배수 {cases} → 면제는 {free[0]}번(제3항 단서)")


def v_rule_refund() -> tuple[int, str]:
    paid, r = 28000, _REFUND["1시간이내"]
    back = int(paid * (1 - r))
    return (back, f"{paid:,} × (1 − {r}) = {back:,}원 "
                  f"(출발 후 {int(paid*(1-_REFUND['출발후'])):,}원과 다름)")


def v_rule_delay() -> tuple[int, str]:
    paid, late = 28000, 45
    rate = next(r for lo, hi, r in _DELAY if lo <= late < hi)
    return (int(paid * rate), f"{late}분 → {rate:.1%} → {int(paid*rate):,}원 "
                              f"(구간 {[(lo,hi,r) for lo,hi,r in _DELAY]})")


def _pass_fare(base: int, kind: str) -> int:
    raw = base * _PASS_TRIPS * (1 - _PASS_DC[kind])
    return int(raw // 100 * 100)  # 100원 미만 버림


def v_rule_pass_adult() -> tuple[int, str]:
    n = _pass_fare(1450, "일반")
    raw = 1450 * _PASS_TRIPS * (1 - _PASS_DC["일반"])
    return (n, f"1,450 × {_PASS_TRIPS} × 0.55 = {raw:,.0f} → 절사 {n:,}원")


def v_rule_pass_student() -> tuple[int, str]:
    n = _pass_fare(1450, "학생")
    raw = 1450 * _PASS_TRIPS * (1 - _PASS_DC["학생"])
    return (n, f"1,450 × {_PASS_TRIPS} × 0.40 = {raw:,.0f} → 절사 {n:,}원 "
               f"(일반 {_pass_fare(1450,'일반'):,}원과 차 "
               f"{_pass_fare(1450,'일반')-n:,}원)")


def v_rule_pass_abuse() -> tuple[int, str]:
    """정기권 규정 제5조 → 약관 제12조 제2항(10배). 30배가 아니다."""
    fare = 1350
    total = fare + fare * _MULT_DISCOUNT
    return (total, f"제5조가 가리킨 제2항 = {_MULT_DISCOUNT}배 → "
                   f"{fare:,} + {fare*_MULT_DISCOUNT:,} = {total:,}원 "
                   f"(30배로 보면 {fare+fare*30:,}원)")


def v_rule_deleg_amount() -> tuple[str, str]:
    amt = 12_000_000
    return (_deleg(amt), f"{amt:,}원 → {_deleg(amt)}")


def v_rule_deleg_public() -> tuple[str, str]:
    """제8조 제1항 — 금액과 무관하게 외부 공표 사항은 본부장."""
    amt = 3_000_000
    return ("본부장", f"금액만 보면 {_deleg(amt)}, 대외 공표라 제8조 제1항으로 본부장")


def v_rule_deleg_split() -> tuple[str, str]:
    """제8조 제3항 — 같은 목적은 합한 금액으로."""
    a, b = 14_000_000, 9_000_000
    return (_deleg(a + b), f"따로 보면 {_deleg(a)}·{_deleg(b)}, "
                           f"합 {a+b:,}원 → {_deleg(a+b)}")


def v_rule_deleg_acting() -> tuple[str, str]:
    """제8조 제2항 — 차상위자가 대결. 본부장의 위는 사장."""
    order = [w for _, w in _DELEG]
    i = order.index("본부장")
    return (order[i + 1], f"직위 순서 {order} → 본부장의 차상위는 {order[i+1]}")


def v_rule_group_fare() -> tuple[int, str]:
    n, fare = 34, 8400
    dc = 0.15 if n >= 50 else (0.10 if n >= 30 else 0.0)
    total = int(n * fare * (1 - dc))
    return (total, f"{n} × {fare:,} = {n*fare:,} × (1 − {dc}) = {total:,}원 "
                   f"(초과분만 할인하면 {int(30*fare*0.9 + 4*fare):,}원)")


def v_rule_group_rate() -> tuple[int, str]:
    """제3항 — 실제 승차 인원으로 센다. 예약 52 가 아니라 실승차 48."""
    booked, rode = 52, 48
    dc = 0.15 if rode >= 50 else (0.10 if rode >= 30 else 0.0)
    return (int(dc * 100), f"예약 {booked} 아니라 실승차 {rode} → {dc:.0%} "
                           f"(예약 기준이면 15%)")


def v_rule_gift() -> tuple[int, str]:
    """행동강령 — 한도를 넘는 사례의 선지 번호."""
    LIMIT_FOOD, LIMIT_FLOWER = 30000, 50000
    cases = {
        1: True,                        # 일률 제공 기념품
        2: 28000 <= LIMIT_FOOD,         # 식사 2만 8천
        3: 70000 <= LIMIT_FLOWER,       # 조화 7만 → 한도 초과
        4: True,                        # 4촌 신고·회피
        5: True,                        # 일률 제공 기념품
    }
    bad = [k for k, ok in cases.items() if not ok]
    assert len(bad) == 1, f"어긋나는 것이 하나여야 한다: {bad}"
    return (bad[0], f"판정 {cases} → 어긋나는 것 {bad[0]}번 "
                    f"(조화 70,000 > 한도 {LIMIT_FLOWER:,})")


def v_rule_travel() -> tuple[int, str]:
    fare, days, nights = 59800 * 2, 3, 2
    raw = fare + 25000 * days + 50000 * nights
    total = -(-raw // 1000) * 1000  # 1,000원 미만 올림
    return (total, f"운임 {fare:,} + 일비 {25000*days:,}(3일) + "
                   f"숙박 {50000*nights:,}(2박) = {raw:,} → 절상 {total:,}원")


# ── 자료해석 ────────────────────────────────────────────────────────────
#
# 문항의 표를 **여기 다시 적고** 답을 계산한다. 표와 해설이 어긋나면 여기서 잡힌다.
# 표를 고치면 이쪽도 고쳐야 하고, 안 고치면 불일치로 뜬다 — 그게 목적이다.

def _rate(new, old):
    return (new - old) / old * 100


def v_share_rail() -> tuple[float, str]:
    d = {"도시철도": 2814, "시내버스": 3960, "택시": 1122, "철도": 504}
    tot = sum(d.values())
    p = d["도시철도"] / tot * 100
    return (p, f"2,814 ÷ {tot:,} = {p:.1f}%")


def v_best_growth() -> tuple[str, str]:
    d = {"A": (1250, 1400), "B": (860, 989), "C": (2100, 2331),
         "D": (430, 500), "E": (1580, 1706)}
    r = {k: _rate(v[1], v[0]) for k, v in d.items()}
    amt = {k: v[1] - v[0] for k, v in d.items()}
    best = max(r, key=r.get)
    return (best, f"증가율 " + " · ".join(f"{k} {v:.1f}%" for k, v in r.items())
            + f" → {best} / 증가량 1위는 {max(amt, key=amt.get)}(다른 곳)")


def v_bad_chart() -> tuple[int, str]:
    """표를 그래프로 옮긴 넷 가운데 어긋난 것. 선지 번호를 돌려준다."""
    tbl = {"1분기": 320, "2분기": 480, "3분기": 560, "4분기": 400}
    charts = {
        1: {"1분기": 320, "2분기": 480, "3분기": 560, "4분기": 400},
        2: {"1분기": 320, "2분기": 480, "3분기": 560, "4분기": 400},
        3: {"1분기": 320, "2분기": 560, "3분기": 480, "4분기": 400},
        4: {"1분기": 320, "2분기": 480, "3분기": 560, "4분기": 400},
    }
    bad = [i for i, c in charts.items() if c != tbl]
    assert len(bad) == 1, f"어긋난 그래프가 하나여야 한다: {bad}"
    return (bad[0], f"㉠~㉣ 가운데 표와 다른 것은 {bad[0]}번뿐 "
                    f"(2·3분기가 뒤바뀜)")


def v_blank_sum() -> tuple[int, str]:
    known = {"수도권": 428, "중부": 315, "호남": 267, "강원": 156}
    tot = 1520
    x = tot - sum(known.values())
    return (x, f"{tot:,} − {sum(known.values()):,} = {x}")


def v_blank_avg() -> tuple[int, str]:
    known = [231, 258, 240, 262]
    avg, n = 246, 5
    x = avg * n - sum(known)
    return (x, f"{avg} × {n} − {sum(known)} = {x} "
               f"(다시 평균 {(sum(known)+x)/n:.1f})")


def v_cross_seats() -> tuple[int, str]:
    cap = {"전동차": 160, "무궁화": 72, "새마을": 56}
    run = {"전동차": 12, "무궁화": 8, "새마을": 5}
    per = {k: cap[k] * run[k] for k in cap}
    return (sum(per.values()),
            " + ".join(f"{v:,}" for v in per.values()) + f" = {sum(per.values()):,}")


def v_unit_thousand() -> tuple[int, str]:
    return (1449 * 1000, "표 단위가 천 명 → 1,449 × 1,000 = 1,449,000명")


def v_wavg_fare() -> tuple[int, str]:
    w = [(1250, 1400), (860, 1900), (430, 2600)]
    tot_n = sum(n for n, _ in w)
    tot_v = sum(n * p for n, p in w)
    wa = tot_v / tot_n
    naive = sum(p for _, p in w) / len(w)
    return (round(wa), f"{tot_v:,} ÷ {tot_n:,} = {wa:.1f} → {round(wa):,}원 "
                       f"(단순평균 {naive:.0f}원과 다름)")


def v_rank_moved() -> tuple[int, str]:
    y23 = {"가": 820, "나": 940, "다": 760, "라": 1120, "마": 680}
    y24 = {"가": 965, "나": 918, "다": 812, "라": 1150, "마": 742}
    rk = lambda d: {k: i + 1 for i, (k, _) in
                    enumerate(sorted(d.items(), key=lambda x: -x[1]))}
    a, b = rk(y23), rk(y24)
    moved = [k for k in y23 if a[k] != b[k]]
    return (len(moved), f"{a} → {b} · 바뀐 역 {moved} = {len(moved)}곳")


def v_amt_vs_rate() -> tuple[tuple[str, str], str]:
    d = {"A": (4200, 4620), "B": (680, 850), "C": (1500, 1680)}
    amt = {k: v[1] - v[0] for k, v in d.items()}
    rt = {k: _rate(v[1], v[0]) for k, v in d.items()}
    a, r = max(amt, key=amt.get), max(rt, key=rt.get)
    return ((a, r), f"증가량 {amt} → {a} / 증가율 "
                    + " · ".join(f"{k} {v:.1f}%" for k, v in rt.items()) + f" → {r}")


def v_index() -> tuple[float, str]:
    base, cur = 2480, 2852
    p = cur / base * 100
    return (p, f"{cur:,} ÷ {base:,} × 100 = {p:.1f}")


def v_share_down() -> tuple[tuple[str, str], str]:
    a, b = (312, 1560), (378, 2100)
    pa, pb = a[0] / a[1] * 100, b[0] / b[1] * 100
    return (("늘" if b[0] > a[0] else "줄", "늘" if pb > pa else "줄"),
            f"수 {a[0]} → {b[0]} · 비중 {pa:.1f}% → {pb:.1f}% "
            f"(전체는 {_rate(b[1], a[1]):.1f}% 늘어 더 빠르다)")


def v_comp_wrong() -> tuple[int, str]:
    """구성비 표에 대한 다섯 주장 가운데 틀린 것. 선지 번호를 돌려준다."""
    d = {"정기": 42.5, "일반": 31.0, "청소년": 14.2, "경로": 9.8, "기타": 2.5}
    assert round(sum(d.values()), 1) == 100.0, "구성비 합이 100이어야 한다"
    claims = {
        1: d["정기"] == max(d.values()),
        2: d["정기"] >= d["일반"] * 1.5,
        3: d["청소년"] + d["경로"] < d["일반"],
        4: d["정기"] <= 50,
        5: d["경로"] > d["기타"] * 3,
    }
    wrong = [i for i, ok in claims.items() if not ok]
    assert len(wrong) == 1, f"틀린 주장이 하나여야 한다: {wrong}"
    return (wrong[0], f"주장별 판정 {claims} → 틀린 것 {wrong[0]}번 "
                      f"(정기/일반 = {d['정기']/d['일반']:.3f}배, 1.5 미만)")


def v_dec_pair() -> tuple[tuple[str, str], str]:
    d = {"가": (520, 468), "나": (340, 289), "다": (780, 702), "라": (150, 120)}
    amt = {k: v[0] - v[1] for k, v in d.items()}
    rt = {k: -_rate(v[1], v[0]) for k, v in d.items()}
    return ((max(amt, key=amt.get), max(rt, key=rt.get)),
            f"감소량 {amt} / 감소율 "
            + " · ".join(f"{k} {v:.1f}%" for k, v in rt.items()))


def v_cumulative() -> tuple[int, str]:
    cum = {2022: 1240, 2023: 2760, 2024: 4520}
    y23 = cum[2023] - cum[2022]
    y24 = cum[2024] - cum[2023]
    return (y24 - y23, f"당해 실적 2023 {y23:,} · 2024 {y24:,} → 차이 {y24-y23}")


def v_rate_times_cap() -> tuple[str, str]:
    d = {"A": (1200, 0.82), "B": (900, 0.91), "C": (1500, 0.68)}
    use = {k: round(c * r) for k, (c, r) in d.items()}
    best = max(use, key=use.get)
    rate_best = max(d, key=lambda k: d[k][1])
    return (best, f"실제 인원 {use} → {best} "
                  f"(이용률 1위는 {rate_best} 로 다르다)")


def v_wavg_score() -> tuple[float, str]:
    g = [(120, 78.5), (40, 91.0)]
    tot_n = sum(n for n, _ in g)
    p = sum(n * m for n, m in g) / tot_n
    naive = sum(m for _, m in g) / len(g)
    return (p, f"{sum(n*m for n,m in g):,.0f} ÷ {tot_n} = {p:.3f} "
               f"(평균의 평균 {naive:.2f}와 다름)")


def v_cagr() -> tuple[float, str]:
    s, e, yrs = 2000, 2420, 2
    p = ((e / s) ** (1 / yrs) - 1) * 100
    half = _rate(e, s) / yrs
    return (p, f"({e:,}/{s:,})^(1/{yrs}) − 1 = {p:.1f}% "
               f"(전체 {_rate(e, s):.1f}% 의 절반 {half:.1f}% 가 아니다)")


def v_congestion() -> tuple[int, str]:
    cap, sets, cong = 160, 10, 1.35
    n = round(cap * sets * cong)
    return (n, f"{cap} × {cong} × {sets} = {n:,}명 (혼잡도 = 승차 ÷ 정원)")


def v_pp_vs_pct() -> tuple[tuple[float, float], str]:
    a, b = 24.0, 30.0
    return ((round(b - a, 1), round(_rate(b, a), 1)),
            f"차이 {b-a:.1f}%p · 증가율 {_rate(b, a):.1f}% "
            f"(나중 값으로 나누면 {(b-a)/b*100:.1f}% 로 틀린다)")


# ── 수리 ────────────────────────────────────────────────────────────────

def v_tunnel() -> tuple[float, str]:
    train, tunnel, v = 200, 1300, 25
    return ((tunnel + train) / v,
            f"({tunnel}+{train})/{v} = {(tunnel+train)/v:.0f}초 · "
            f"터널만 {tunnel/v:.0f}(오답①) · 열차만 {train/v:.0f}")


def v_pass() -> tuple[float, str]:
    la, lb, va, vb = 150, 250, 20, 30
    face = (la + lb) / (va + vb)
    same = (la + lb) / abs(va - vb)
    return face, f"마주 {face:.0f}초 · 같은 방향 {same:.0f}초(오답⑤)"


def v_harmonic() -> tuple[float, str]:
    a, b = 60, 40
    return 2 * a * b / (a + b), f"조화 {2*a*b/(a+b):.0f} · 산술 {(a+b)/2:.0f}(오답④)"


def v_mix() -> tuple[float, str]:
    aw, ap, bw, bp = 200, 8, 300, 13
    salt = aw * ap / 100 + bw * bp / 100
    got = salt / (aw + bw) * 100
    return got, f"소금 {salt:.0f}g/{aw+bw}g = {got:.1f}% · 단순평균 {(ap+bp)/2}(오답②)"


def v_dilute() -> tuple[float, str]:
    w, p, add = 400, 15, 100
    salt = w * p / 100
    return salt / (w + add) * 100, f"소금 {salt:.0f}g 고정 · {w}→{w+add}g → {p}%→{salt/(w+add)*100:.0f}%"


def v_work_two() -> tuple[F, str]:
    a, b = 12, 18
    got = 1 / (F(1, a) + F(1, b))
    return got, f"1/(1/{a}+1/{b}) = {got} = {float(got):.1f}일 · 날수 평균 {(a+b)/2:.0f}(오답⑤)"


def v_work_join() -> tuple[F, str]:
    A, B, solo = 15, 10, 3
    rest = 1 - F(solo, A)
    total = solo + rest / (F(1, A) + F(1, B))
    return total, (f"{solo}일 → {F(solo,A)} 완료 · 남은 {rest} ÷ {F(1,A)+F(1,B)} "
                   f"= {rest/(F(1,A)+F(1,B))} → 총 {total} = {float(total):.1f}일")


def v_margin() -> tuple[F, str]:
    cost, mark, disc = 20000, F(30, 100), F(20, 100)
    sale = cost * (1 + mark) * (1 - disc)
    rate = (sale - cost) / cost * 100
    return rate, (f"{cost} → 정가 {int(cost*(1+mark))} → 판매 {int(sale)} · "
                  f"이익 {int(sale-cost)}원 = {rate}% · 30−20 = 10(오답④)")


def v_undiscount() -> tuple[F, str]:
    final, d1, d2 = 25200, F(10, 100), F(30, 100)
    got = final / ((1 - d1) * (1 - d2))
    naive = F(final) / (1 - d1 - d2)
    return got, f"{final}/(0.9×0.7) = {got} · 할인율을 더하면 {naive}(오답④)"


def v_growth() -> tuple[F, str]:
    old, new = 2500, 2900
    return (F(new - old, old) * 100,
            f"({new}−{old})/{old} = {F(new-old,old)*100}% · "
            f"분모를 새 값으로 하면 {float(F(new-old,new)*100):.1f}%(오답①)")


def v_lattice() -> tuple[int, str]:
    r, c = 3, 4
    return (math.comb(r + c, r),
            f"C({r+c},{r}) = {math.comb(r+c,r)} · 중간점 경유 "
            f"{math.comb(4,2)*math.comb(3,1)}(오답②) · 곱하면 {r*c}(오답①)")


def v_round_table() -> tuple[int, str]:
    n = 6
    return (math.factorial(n - 1),
            f"({n}−1)! = {math.factorial(n-1)} · 일렬 {math.factorial(n)}(오답⑤) · "
            f"이웃 {math.factorial(n-2)*2}(오답①)")


def v_atleast_woman() -> tuple[int, str]:
    m, w, k = 5, 4, 3
    tot, allm = math.comb(m + w, k), math.comb(m, k)
    exact1 = math.comb(w, 1) * math.comb(m, 2)
    return tot - allm, (f"C(9,3) {tot} − 남자만 {allm} = {tot-allm} · "
                        f"여자 정확히 1명 {exact1}(오답②) · 전체 {tot}(오답⑤)")


def v_atleast_defect() -> tuple[F, str]:
    p, n = F(1, 10), 3
    got = 1 - (1 - p) ** n
    return got, (f"1−(9/10)³ = {got} · 모두 정상 {(1-p)**n}(오답⑤) · "
                 f"모두 불량 {p**n}(오답④) · 더하면 {p*n}(오답①)")


def v_bayes() -> tuple[F, str]:
    pa = F(1, 2) * F(3, 5)
    pb = F(1, 2) * F(1, 5)
    return pa / (pa + pb), (f"P(A∩빨) {pa} · P(빨) {pa+pb} → {pa/(pa+pb)} · "
                            f"A 안 빨강비율 {F(3,5)}(오답④)")


def v_same_color() -> tuple[F, str]:
    r, b = 5, 3
    tot = math.comb(r + b, 2)
    same = math.comb(r, 2) + math.comb(b, 2)
    return F(same, tot), (f"({math.comb(r,2)}+{math.comb(b,2)})/{tot} = {F(same,tot)} · "
                          f"다른 색 {F(tot-same,tot)}(오답③) · 합 {F(same,tot)+F(tot-same,tot)}")


def v_modpow() -> tuple[int, str]:
    base, exp, mod = 7, 100, 5
    cyc = [pow(base, k, mod) for k in range(1, 6)]
    return pow(base, exp, mod), f"주기 {cyc[:4]} · {exp}%4=0 → 마지막 {pow(base,exp,mod)}"


def v_lcm_time() -> tuple[int, str]:
    a, b, c = 12, 18, 30
    l = math.lcm(a, b, c)
    return 6 + l // 60, (f"lcm({a},{b},{c}) = {l}분 = {l//60}시간 → 06시 + {l//60} = "
                         f"{6+l//60}시 · 최대공약수는 {math.gcd(a,math.gcd(b,c))}분")


def v_seq() -> tuple[int, str]:
    s = [2, 6, 12, 20, 30]
    d = [s[i + 1] - s[i] for i in range(len(s) - 1)]
    nxt = s[-1] + d[-1] + 2
    formula = len(s) + 1
    return nxt, (f"차 {d} → 다음 차 {d[-1]+2} → {nxt} · "
                 f"n(n+1) 로도 {formula}×{formula+1} = {formula*(formula+1)}")


def v_clock() -> tuple[float, str]:
    h, m = 3, 40
    ang = abs(30 * h - 5.5 * m)
    small = min(ang, 360 - ang)
    return small, (f"|30×{h} − 5.5×{m}| = {ang:.0f}도 (작은 쪽 {small:.0f}) · "
                   f"시침 고정이면 {abs(30*h - 6*m):.0f}(오답①)")


# ── 조건추리 — 전수 탐색으로 **답이 하나뿐인지** 확인한다 ────────────────
#
# 해가 둘 이상이면 문항이 성립하지 않는다. 검증기가 그것부터 본다.

def _unique(people, slots, rules, ask):
    """규칙을 만족하는 배치를 모두 찾고, **하나뿐일 때만** 물어본 값을 돌려준다."""
    ok = [dict(zip(people, p)) for p in permutations(slots, len(people))
          if all(r(dict(zip(people, p))) for r in rules)]
    if len(ok) != 1:
        raise AssertionError(f"해가 {len(ok)}가지다 — 문항이 성립하지 않는다: {ok[:4]}")
    return ask(ok[0]), ok[0]


def v_floor():
    people, slots = list("ABCDE"), [1, 2, 3, 4, 5]
    rules = [lambda m: m["A"] > m["B"], lambda m: m["C"] == 5,
             lambda m: m["D"] == 1, lambda m: m["E"] == 3]
    who, sol = _unique(people, slots, rules,
                       lambda m: next(k for k, v in m.items() if v == 4))
    return who, f"해 1가지 {sol} → 4층은 {who}"


def v_duty():
    days = ["월", "화", "수", "목", "금"]
    i = days.index
    rules = [lambda m: m["A"] == "수", lambda m: m["C"] == "월",
             lambda m: i(m["E"]) == i(m["B"]) - 1]
    who, sol = _unique(list("ABCDE"), days, rules,
                       lambda m: next(k for k, v in m.items() if v == "화"))
    return who, f"해 1가지 {sol} → 화요일은 {who}"


def v_dept():
    depts = ["기획", "운영", "안전", "기술"]
    rules = [lambda m: m["을"] == "기획",
             lambda m: m["병"] not in ("운영", "안전"),
             lambda m: m["정"] == "운영"]
    who, sol = _unique(list("갑을병정"), depts, rules,
                       lambda m: next(k for k, v in m.items() if v == "기술"))
    return who, f"해 1가지 {sol} → 기술팀은 {who}"


def v_race():
    rules = [lambda m: m["C"] == 5, lambda m: m["E"] == m["A"] + 1,
             lambda m: m["D"] == 2]
    who, sol = _unique(list("ABCDE"), [1, 2, 3, 4, 5], rules,
                       lambda m: next(k for k, v in m.items() if v == 3))
    return who, f"해 1가지 {sol} → 3등은 {who}"


def v_liar():
    """한 명만 참을 말한다. 후보를 넣어 참인 진술 수를 센다."""
    cnt = {}
    for c in "갑을병정":
        s = {"갑": c != "갑", "을": c == "병", "병": c == "정", "정": c != "정"}
        cnt[c] = sum(s.values())
    ones = [c for c, n in cnt.items() if n == 1]
    if len(ones) != 1:
        raise AssertionError(f"참이 하나인 경우가 {len(ones)}가지다: {ones}")
    return ones[0], f"참인 진술 수 {cnt} → 한 명만 참인 경우는 {ones[0]}"


def v_qualify():
    """지원 자격 — 세 조건을 모두 넘긴 사람이 하나뿐인지 표로 대조한다."""
    C = {"갑": (2, True, True), "을": (5, False, True), "병": (4, True, False),
         "정": (3, True, True), "무": (6, True, False)}
    ok = [k for k, (y, lic, edu) in C.items() if y >= 3 and lic and edu]
    if len(ok) != 1:
        raise AssertionError(f"자격을 갖춘 사람이 {len(ok)}명이다: {ok}")
    fail = {k: ("경력" if y < 3 else "자격증" if not lic else "교육")
            for k, (y, lic, edu) in C.items() if k not in ok}
    return ok[0], f"충족 {ok[0]} · 탈락 사유 {fail}"


def v_cause():
    """지연이 뛴 주에 **함께 뛴 항목**이 하나뿐인지 본다."""
    W = {"지연": [4, 5, 18, 4], "이용객": [82, 84, 83, 85],
         "정비지연": [1, 2, 1, 2], "안전문고장": [0, 1, 11, 0]}
    spike = W["지연"].index(max(W["지연"]))
    moved = [k for k, v in W.items() if k != "지연"
             and v[spike] >= 3 * (sum(v) - v[spike]) / 3]
    if moved != ["안전문고장"]:
        raise AssertionError(f"함께 뛴 항목이 {moved} 다")
    return "안전문고장", (f"{spike+1}주차 지연 {W['지연'][spike]}건 · "
                          f"함께 뛴 항목 {moved} · 나머지는 주마다 거의 같다")


# ── 자원관리 ────────────────────────────────────────────────────────────

def v_weighted():
    C = {"갑": (85, 70, 90), "을": (78, 88, 80), "병": (90, 75, 72),
         "정": (72, 92, 85), "무": (88, 80, 78)}
    W = (0.5, 0.3, 0.2)
    s_ = {k: round(sum(a * b for a, b in zip(v, W)), 1) for k, v in C.items()}
    eq = {k: round(sum(v) / 3, 1) for k, v in C.items()}
    return max(s_, key=s_.get), f"가중 {s_} 1위 {max(s_,key=s_.get)} · 단순평균 1위 {max(eq,key=eq.get)}"


def v_quote():
    Q = {"A": (120000, 0.10, 15000), "B": (135000, 0.15, 0), "C": (128000, 0.05, 10000)}
    t = {k: unit * 5 * (1 - d) + ship for k, (unit, d, ship) in Q.items()}
    return min(t, key=t.get), " · ".join(f"{k} {int(v):,}" for k, v in t.items())


def v_bus():
    best = min(((120000 * a + 80000 * b, a, b)
                for a in range(10) for b in range(12) if 45 * a + 25 * b >= 160))
    return best[0], f"45인승 {best[1]}대 + 25인승 {best[2]}대 = {best[0]:,}원"


def v_sched():
    T = {"A": (None, 2), "B": ("A", 3), "C": ("A", 1), "D": ("B", 2), "E": ("C", 4)}

    def fin(n):
        p, d = T[n]
        return d + (0 if p is None else fin(p))

    ends = {n: fin(n) for n in T}
    return max(ends.values()), f"종료 {ends} → {max(ends.values())}시간 · 단순 합 {sum(d for _, d in T.values())}"


def v_meeting():
    busy = {"A": {9, 10, 14}, "B": {10, 11, 15}, "C": {9, 11, 16}, "D": {14, 15}}
    free = [h for h in range(9, 18) if all(h not in v for v in busy.values())]
    two = [h for h in range(9, 17)
           if all(h not in v and h + 1 not in v for v in busy.values())]
    if len(two) != 1:
        raise AssertionError(f"2시간 연속 가능한 시작이 {two} 다")
    return two[0], f"모두 비는 시각 {free} · 2시간 연속 시작 {two}"


def v_pack():
    from itertools import combinations
    it = {"가": (3, 4), "나": (2, 6), "다": (5, 2), "라": (4, 3)}
    best = max(((sum(it[x][1] for x in c), tuple(sorted(c)))
                for r in range(1, 5) for c in combinations(it, r)
                if sum(it[x][0] for x in c) <= 10))
    return best[1], f"최대 이익 {best[0]} 조합 {best[1]} · 부피당 이익 " +         str({k: round(v[1] / v[0], 2) for k, v in it.items()})


def v_overtime():
    base = 12000
    night, holi = 3, 4
    total = base * 1.5 * night + base * 1.5 * holi
    over = base * 1.5 * 8 + base * 2 * 2          # 휴일 10시간이었다면
    return int(total), f"평일 {int(base*1.5*night):,} + 휴일 {int(base*1.5*holi):,} = {int(total):,}원 · 휴일 10시간이면 {int(over):,}"


def v_trip():
    d, per, lodge, rail = 3, 25000, 70000, 47500
    tot = per * d + lodge * (d - 1) + rail * 2
    return tot, f"일비 {per*d:,} + 숙박 {lodge*(d-1):,}(2박) + 교통 {rail*2:,} = {tot:,}원 · 3박이면 {tot+lodge:,}"


def v_reorder():
    daily, lead, safety = 40, 5, 60
    return daily * lead + safety, f"{daily}×{lead} + {safety} = {daily*lead+safety}개 · 안전재고 없으면 {daily*lead}"


def v_import():
    usd, rate, qty, tariff = 250, 1340, 40, 0.08
    krw = usd * rate * qty
    return int(krw * (1 + tariff)), f"환산 {krw:,} · 관세 포함 {int(krw*(1+tariff)):,}원"


def v_exec():
    b, q = 4800, (980, 1240, 1140)
    used = sum(q)
    return (round(used / b * 100), b - used), f"집행 {used}/{b} = {used/b*100:.0f}% · 잔액 {b-used}만 원"


def v_deprec():
    cost, life, salvage, years = 3200, 5, 400, 3
    per = (cost - salvage) / life
    return int(cost - per * years), f"연 {per:.0f}만 × {years}년 = {per*years:.0f}만 상각 · 장부가 {cost-per*years:.0f}만"


def v_buyrent():
    buy, keep, rent = 240, 5, 25
    n = next(m for m in range(1, 60) if buy + keep * m < rent * m)
    even = buy / (rent - keep)
    return n, f"손익분기 {even:.0f}개월(같아짐) · 유리해지는 것은 {n}개월째부터"


def v_staff():
    import math
    shifts, per, days, work = 3, 4, 7, 5
    need = shifts * per * days / work
    return math.ceil(need), f"{shifts}×{per}×{days}÷{work} = {need} → {math.ceil(need)}명 · 교대만 세면 {shifts*per}명"


def v_order():
    D = ["월", "화", "수", "목", "금"]
    T = {"A": ("금", 2), "B": ("수", 1), "C": ("목", 3), "D": ("수", 2)}
    order = sorted(T, key=lambda k: (D.index(T[k][0]), -T[k][1]))
    return order[0], f"마감 임박순(동률은 오래 걸리는 것 먼저) → {order}"


def v_room():
    R = {"가": (20, True, True, False), "나": (12, True, True, True),
         "다": (18, True, True, True), "라": (25, False, True, True)}
    ok = [k for k, (cap, beam, vid, free) in R.items()
          if cap >= 15 and beam and vid and free]
    if len(ok) != 1:
        raise AssertionError(f"조건을 만족하는 회의실이 {ok} 다")
    return ok[0], f"충족 {ok[0]} · 탈락 " + str(
        {k: ("예약" if not v[3] else "수용" if v[0] < 15 else "빔프로젝터")
         for k, v in R.items() if k not in ok})


# ── 정보 · 조직이해 · 기술 ──────────────────────────────────────────────

SHEET = [("김", "영업", 320, "서울"), ("이", "기술", 480, "부산"),
         ("박", "영업", 510, "서울"), ("최", "기술", 275, "대구"),
         ("정", "영업", 620, "서울"), ("한", "안전", 390, "부산")]


def v_sumif():
    got = sum(r[2] for r in SHEET if r[1] == "영업")
    return got, f"영업 합 {got:,} · 전체 합 {sum(r[2] for r in SHEET):,}(오답⑤)"


def v_countif():
    got = sum(1 for r in SHEET if r[2] >= 400)
    return got, f">=400 인 것 {got}개 · 전체 {len(SHEET)}개(오답⑤)"


def v_averageif():
    v = [r[2] for r in SHEET if r[3] == "서울"]
    return round(sum(v) / len(v)), f"서울 {v} 평균 {sum(v)/len(v):.1f} · 합 {sum(v):,}(오답①)"


def v_rank():
    names = [r[0] for r in sorted(SHEET, key=lambda r: -r[2])]
    return names.index("정") + 1, f"내림차순 {names} → 정 {names.index('정')+1}위"


def v_sumifs():
    got = sum(r[2] for r in SHEET if r[1] == "영업" and r[3] == "서울")
    return got, f"영업∩서울 {got:,} · 이 자료에서는 SUMIF 와 같다"


def v_mid():
    t = "KR-2026-A031-N"
    return t[3:7], f"{t} · 4번째부터 4글자 = {t[3:7]} · LEFT2 {t[:2]} · RIGHT1 {t[-1]}"


def v_nested_if():
    v = 480
    g = "A" if v >= 600 else "B" if v >= 450 else "C" if v >= 300 else "D"
    return g, f"{v} → 600 미만이고 450 이상 → {g}"


def v_code():
    reg = {"서울": "SL", "부산": "BS", "대구": "DG"}
    it = {"레일": "RL", "침목": "SP", "전선": "CB"}
    return f"{reg['부산']}2026{it['침목']}B", "부산 BS + 2026 + 침목 SP + B등급"


def v_decode():
    reg = {"SL": "서울", "BS": "부산", "DG": "대구"}
    it = {"RL": "레일", "SP": "침목", "CB": "전선"}
    c = "DG2025CBA"
    got = (reg[c[:2]], c[2:6], it[c[6:8]], c[8])
    return got, f"{c} → {got[0]}·{got[1]}·{got[2]}·{got[3]}등급"


def v_deleg():
    amt = 1200
    who = next((w for lim, w in [(300, "팀장"), (1000, "처장"), (5000, "본부장")]
                if amt < lim), "사장")
    return who, f"{amt}만 원 → {who} (1,000 ≤ {amt} < 5,000)"


def v_timezone():
    import datetime
    seoul = datetime.datetime(2026, 3, 10, 15, 0)
    ny = seoul + datetime.timedelta(hours=-5 - 9)
    ld = seoul + datetime.timedelta(hours=0 - 9)
    return (ny.day, ny.hour), f"뉴욕 {ny:%m/%d %H:%M} · 런던 {ld:%m/%d %H:%M}(오답③)"


def v_ups():
    tot = sum(w * n for w, n in [(450, 2), (120, 3), (85, 4)])
    need = tot * 1.3
    pick = next(c for c, lim in [(1, 1100), (1.5, 1650), (2, 2200),
                                 (3, 3300), (5, 5500)] if lim >= need)
    return pick, (f"총 {tot}W × 1.3 = {need:.0f}W → {pick}kVA · "
                  f"여유율을 빼면 1.5kVA 로 보인다")


def v_disks():
    import math
    total = 1.2 * 6 + 0.18 * 10 + 0.024 * 50
    return math.ceil(total / 2.4), (f"{total:.1f}GB ÷ 2.4 = {total/2.4:.2f} → "
                                    f"{math.ceil(total/2.4)}장 (반올림하면 4장)")


def v_bribe():
    """가상 규정 제5조 제2항 — 예외에 드는 것이 하나뿐인지 본다."""
    cases = [("7만 원 선물", None), ("1인 4만 원 식사", (4, 3)),
             ("행사 일률 기념품", "제1호"), ("8만 원 화환", (8, 5)),
             ("무이자 대출", None)]
    ok = [i for i, (_, c) in enumerate(cases, 1)
          if c == "제1호" or (isinstance(c, tuple) and c[0] <= c[1])]
    if len(ok) != 1:
        raise AssertionError(f"허용되는 것이 {ok} 다 — 문항이 성립하지 않는다")
    return ok[0], f"허용 {cases[ok[0]-1][0]} · 나머지는 예외 없음 또는 한도 초과"


# ── 명제 — 작은 세계를 전부 만들어 필연인지 본다 ─────────────────────────

def _entails(names, premises, conclusion, n=4):
    import itertools
    for a in itertools.product([0, 1], repeat=len(names) * n):
        W = {p: {j for j in range(n) if a[i * n + j]}
             for i, p in enumerate(names)}
        if all(pr(W) for pr in premises) and not conclusion(W):
            return False, {k: sorted(v) for k, v in W.items()}
    return True, None


def v_syllogism():
    """신입 → 교육 → 배지. 이어 붙인 결론만 참이고 역·이는 아니다."""
    N = ["신입", "교육", "배지"]
    pre = [lambda W: W["신입"] <= W["교육"], lambda W: W["교육"] <= W["배지"]]
    good, _ = _entails(N, pre, lambda W: W["신입"] <= W["배지"])
    bad1, c1 = _entails(N, pre, lambda W: W["교육"] <= W["신입"])
    bad2, c2 = _entails(N, pre, lambda W: W["배지"] <= W["신입"])
    if not good or bad1 or bad2:
        raise AssertionError("함의 관계가 예상과 다르다")
    return "신입→배지", f"이어 붙인 결론 참 · 역 둘 다 반례 있음 {c1} / {c2}"


def v_existential():
    """∃(정비∩야간), 야간→자격 ⊨ ∃(정비∩야간) 은 전제 그대로. 전칭은 안 나온다."""
    N = ["정비", "야간", "자격"]
    pre = [lambda W: bool(W["정비"] & W["야간"]), lambda W: W["야간"] <= W["자격"]]
    good, _ = _entails(N, pre, lambda W: bool(W["정비"] & W["야간"]))
    bad, c = _entails(N, pre, lambda W: W["정비"] <= W["자격"])
    if not good or bad:
        raise AssertionError("함의 관계가 예상과 다르다")
    return "∃(정비∩야간)", f"존재 결론 참 · 전칭(모든 정비사→자격) 반례 {c}"


def v_contrapositive():
    """p→q 에서 참인 것은 대우뿐. 역·이는 반례가 있다."""
    import itertools
    def tt(prem, con):
        for vals in itertools.product([0, 1], repeat=2):
            v = dict(zip("pq", vals))
            if all(f(v) for f in prem) and not con(v):
                return False, v
        return True, None
    imp = lambda v: (not v["p"]) or v["q"]
    ok, _ = tt([imp, lambda v: not v["q"]], lambda v: not v["p"])
    r1, c1 = tt([imp, lambda v: v["q"]], lambda v: v["p"])
    r2, c2 = tt([imp, lambda v: not v["p"]], lambda v: not v["q"])
    if not ok or r1 or r2:
        raise AssertionError("대우 관계가 예상과 다르다")
    return "대우", f"대우 참 · 후건 긍정 반례 {c1} · 전건 부정 반례 {c2}"


# ── 서울교통공사 (bank/seoul_metro/ncs_math.py) ─────────────────────────
#
# 후기가 수치까지 적어 놓은 소재라 값을 지어내지 않았다. 오답 경로도 여기서
# 함께 재현해, 선지 다섯 값이 서로 다른지까지 검증이 지킨다 (규칙 `4-14`).

_SM_A = dict(qty=10_000, cost=10_000, price=20_000, defect=4, sell=98)
_SM_B = dict(qty=15_000, cost=12_000, price=20_000, defect=5, sell=96)
_SM_FIXED = 150_000_000


def v_sm_profit() -> tuple[int, str]:
    """순이익 = 매출 − 원가 − 고정비. **매출은 판매수량, 원가는 생산 전량**이다."""
    P = (_SM_A, _SM_B)
    good = lambda p: p["qty"] * F(100 - p["defect"], 100)
    sold = lambda p: good(p) * F(p["sell"], 100)
    rev = sum(sold(p) * p["price"] for p in P)
    cost = sum(p["qty"] * p["cost"] for p in P)
    net = rev - cost - _SM_FIXED
    if net.denominator != 1:
        raise AssertionError(f"순이익이 정수가 아니다: {net}")
    # 오답 경로 재현
    merged = sum(p["qty"] * F(100 - p["defect"] - (100 - p["sell"]), 100) * p["price"]
                 for p in P) - cost - _SM_FIXED          # 두 비율을 합산 차감
    no_sell = sum(good(p) * p["price"] for p in P) - cost - _SM_FIXED
    cost_sold = rev - sum(sold(p) * p["cost"] for p in P) - _SM_FIXED
    no_defect = sum(p["qty"] * F(p["sell"], 100) * p["price"]
                    for p in P) - cost - _SM_FIXED
    vals = [int(net), int(merged), int(no_sell), int(cost_sold), int(no_defect)]
    if len(set(vals)) != 5:
        raise AssertionError(f"선지 값이 겹친다: {vals}")
    return int(net), (
        f"매출 {int(rev):,} − 원가 {int(cost):,} − 고정비 {_SM_FIXED:,} = {int(net):,}원 · "
        f"비율 합산 {int(merged):,}(오답①) · 판매율 미적용 {int(no_sell):,}(오답③) · "
        f"원가를 판매분에만 {int(cost_sold):,}(오답④) · 불량률 미적용 {int(no_defect):,}(오답⑤)")


def v_sm_commute() -> tuple[int, str]:
    """도착 시각(분). 승강장에 닿은 시각이 아니라 **다음 배차 시각**에 떠난다."""
    m = lambda h, mi: h * 60 + mi
    lines = (dict(first=m(7, 2), gap=5, stops=9), dict(first=m(7, 5), gap=7, stops=4))
    hm = lambda v: f"{v // 60:02d}:{v % 60:02d}"

    def ride(wait=True, tr_walk=True, stops=(9, 4), full_gap=False):
        t, w = m(7, 12) + 8, []
        for i, ln in enumerate(lines):
            if full_gap:
                t += ln["gap"]
            elif wait:
                k = max(0, -(-(t - ln["first"]) // ln["gap"]))
                dep = ln["first"] + k * ln["gap"]
                w.append(dep - t)
                t = dep
            t += stops[i] * 2
            if i == 0 and tr_walk:
                t += 4
        return t + 5, w

    ans, waits = ride()
    others = [ride(wait=False)[0], ride(tr_walk=False)[0],
              ride(stops=(10, 5))[0], ride(full_gap=True)[0]]
    if len({ans, *others}) != 5:
        raise AssertionError(f"선지 시각이 겹친다: {[ans, *others]}")
    return ans, (
        f"대기 {waits[0]}분·{waits[1]}분 → {hm(ans)} · "
        f"대기 무시 {hm(others[0])}(오답②) · 환승도보 누락 {hm(others[1])}(오답①) · "
        f"역 개수로 셈 {hm(others[2])}(오답④) · 대기를 배차간격으로 {hm(others[3])}(오답⑤)")


def v_sm_roles() -> tuple[int, str]:
    """기획 1명 + 디자인 1명. 겸임 불가이므로 겹치는 인원을 뺀다. 전수로 센다."""
    plan, design = ("김", "박", "이", "정", "최"), ("이", "정", "최", "한")
    both, roster = set(plan) & set(design), set(plan) | set(design)
    n = sum(1 for p in plan for d in design if p != d)
    if n != len(plan) * len(design) - len(both):
        raise AssertionError(f"식과 전수 결과가 다르다: {n}")
    comb = len(roster) * (len(roster) - 1) // 2
    if len({n, len(plan) * len(design), comb,
            (len(plan) - len(both)) * len(design),
            len(plan) * (len(design) - len(both))}) != 5:
        raise AssertionError("선지 값이 겹친다")
    return n, (f"{len(plan)}×{len(design)}−{len(both)} = {n}가지 (전수 일치) · "
               f"겸임 무시 {len(plan) * len(design)}(오답⑤) · "
               f"조합 C({len(roster)},2)={comb}(오답③)")


def v_sm_liar() -> tuple[str, str]:
    """다섯 진술 가운데 참이 하나뿐인 경우를 전수로 찾는다."""
    P = ("김", "이", "박", "최", "정")
    # (말한 사람 순서대로) eq = 「그 사람이 맡았다」 · ne = 「그 사람은 맡지 않았다」
    S = (("eq", "이"), ("eq", "김"), ("eq", "최"), ("ne", "김"), ("ne", "박"))
    holds = lambda k, t, last: (last == t) if k == "eq" else (last != t)
    cnt = {l: sum(1 for k, t in S if holds(k, t, l)) for l in P}
    sols = [l for l, n in cnt.items() if n == 1]
    if len(sols) != 1:
        raise AssertionError(f"참이 하나뿐인 해가 유일하지 않다: {sols}")
    # 지목 빈도로 찍히지 않는지 — 정답이 최다 지목 대상이면 안 된다
    named = {x: sum(1 for _, t in S if t == x) for x in P}
    if named[sols[0]] == max(named.values()):
        raise AssertionError("정답이 최다 지목 대상이라 빈도로 찍힌다")
    return sols[0], (f"참인 진술 수 " + " · ".join(f"{l}{cnt[l]}" for l in P) +
                     f" → {sols[0]} 하나뿐 · 최다 지목은 "
                     f"{max(named, key=named.get)}({max(named.values())}회, 오답①)")


def v_sm_triad() -> tuple[int, str]:
    """적대 개수의 홀짝으로 안정·불안정. 불안정 가운데 적대 1개가 정답."""
    CH = (("우호", "우호", "우호"), ("우호", "우호", "적대"),
          ("우호", "적대", "적대"), ("적대", "적대", "적대"),
          ("적대", "우호", "적대"))
    host = [c.count("적대") for c in CH]
    unstable = [i + 1 for i, h in enumerate(host) if h % 2 == 1]
    worst = [i for i in unstable if host[i - 1] == 1]
    if len(worst) != 1:
        raise AssertionError(f"적대 1개인 불안정 조합이 유일하지 않다: {worst}")
    return worst[0], (f"적대 개수 {host} · 홀수(불안정) {unstable} · "
                      f"그 가운데 1개는 {worst[0]}번 · 적대 3개인 {unstable[-1]}번이 오답④")


def v_sm_signal() -> tuple[str, str]:
    """현시 한도 · 선행 열차 · 승강장 45km/h 세 규칙을 모두 통과하는 열차."""
    SIG = {"정지": None, "경계": 25, "주의": 45, "감속": 65, "진행": None}
    PLAT = 45
    CASES = (("A", "정지", 20, False, False), ("B", "경계", 30, False, False),
             ("C", "주의", 40, True, False), ("D", "감속", 60, False, True),
             ("E", "진행", 40, False, True))
    ok, blocked = [], []
    for name, sig, spd, ahead, plat in CASES:
        lim = SIG[sig]
        why = []
        if sig == "정지":
            why.append("정지 현시")
        if lim is not None and spd > lim:
            why.append(f"{spd}>{lim}")
        if ahead:
            why.append("선행 열차")
        if plat and spd > PLAT:
            why.append(f"승강장 {spd}>{PLAT}")
        (ok if not why else blocked).append(name if not why else f"{name} {'·'.join(why)}")
    if len(ok) != 1:
        raise AssertionError(f"진입 가능한 열차가 하나가 아니다: {ok}")
    return ok[0], f"통과 {ok[0]} 하나 · 막힌 이유 " + " / ".join(blocked)


def v_sm_passcode() -> tuple[str, str]:
    """월2 + 일2 + 요일코드1. 기준일 요일에서 날짜 차이만큼 옮긴다."""
    import datetime
    KOR = "월화수목금토일"
    base, target = datetime.date(2026, 7, 1), datetime.date(2026, 7, 18)
    gap = (target - base).days
    wd = (base.weekday() + gap) % 7
    if wd != target.weekday():
        raise AssertionError("요일 계산이 달력과 어긋난다")
    pw = f"{target.month:02d}{target.day:02d}{wd + 1}"
    others = {f"{target.month:02d}{target.day:02d}{base.weekday() + 1}",   # 기준일 요일
              f"{target.month:02d}{target.day:02d}{wd}",                    # 코드 0부터
              f"{target.month:02d}{target.day:02d}{(wd + 1) % 7 + 1}",      # 차이 18일
              f"{target.day:02d}{target.month:02d}{wd + 1}"}                # 자리 바꿈
    if len(others | {pw}) != 5:
        raise AssertionError("선지 값이 겹친다")
    return pw, (f"{base} {KOR[base.weekday()]} → {gap}일 뒤 · {gap} mod 7 = {gap % 7} → "
                f"{KOR[wd]}(코드 {wd + 1}) → {pw}")


def v_sm_ge() -> tuple[int, str]:
    """GE 매트릭스 — 점수를 구간으로 옮긴 뒤 분류한다. 어긋난 선지 번호를 돌려준다."""
    band = lambda v: "높음" if v >= 3.7 else ("낮음" if v <= 2.3 else "중간")
    rule = {("높음", "높음"): "투자·성장", ("높음", "중간"): "투자·성장",
            ("중간", "높음"): "투자·성장", ("높음", "낮음"): "선택적 유지",
            ("낮음", "높음"): "선택적 유지", ("중간", "중간"): "선택적 유지",
            ("낮음", "낮음"): "수확·철수", ("낮음", "중간"): "수확·철수",
            ("중간", "낮음"): "수확·철수"}
    S = {"A": (4.2, 3.9), "B": (4.0, 2.0), "C": (3.0, 3.2), "D": (2.1, 2.8)}
    cls = {k: rule[(band(a), band(b))] for k, (a, b) in S.items()}
    if cls["D"] != "수확·철수":
        raise AssertionError(f"D 분류가 예상과 다르다: {cls['D']}")
    if [k for k, v in cls.items() if v == "투자·성장"] != ["A"]:
        raise AssertionError("투자·성장이 A 하나가 아니다")
    return 4, ("분류 " + " · ".join(f"{k} {v}" for k, v in cls.items()) +
               " · ④가 D를 선택적 유지라 했으나 낮음·중간이라 수확·철수")


def v_sm_ushape() -> tuple[int, str]:
    """U자형 배치 전후 지표. 어긋난 선지(자료에 없는 원인)를 돌려준다."""
    move = (120 - 45) / 120 * 100
    lead = (6.0 - 4.2) / 6.0 * 100
    per = (12 / 8, 12 / 6)
    if not (move > 60 and abs(lead - 30) < 1e-9 and per == (1.5, 2.0)):
        raise AssertionError(f"지표가 예상과 다르다: {move} {lead} {per}")
    return 4, (f"이동거리 {move:.1f}% 감소 · 리드타임 {lead:.1f}% 감소 · "
               f"인원당 공정 {per[0]}→{per[1]} · ④의 6시그마는 자료에 없다")


# ── 논리오류 · 모듈적용 · 매뉴얼 — 판정 규칙을 표로 두고 적용한다 ────────
#
# 계산으로 안 떨어진다고 손을 놓으면 오답이 그대로 남는다. 정의를 **표로 적어
# 두고** 상황의 특징과 대조하면, 정의를 고치는 순간 어긋남이 드러난다.
# 참인 선지가 하나뿐인지(_only)까지 확인해야 「우연히 맞는」 것을 막는다.

def _only(cands: dict) -> int:
    """참인 것이 하나뿐인지 확인하고 그 번호를 돌려준다."""
    hit = [k for k, v in cands.items() if v]
    if len(hit) != 1:
        raise AssertionError(f"참인 선지가 하나가 아니다: {hit}")
    return hit[0]


def v_prob_hasty() -> tuple[int, str]:
    """표본 3건으로 전체를 결론 지었다 — 성급한 일반화."""
    sample = 3
    kinds = ["성급한 일반화", "인신공격", "허수아비 공격", "순환 논증", "흑백 논리"]
    feature = [sample <= 5, False, False, False, False]
    n = _only(dict(zip(range(1, 6), feature)))
    return n, f"표본 {sample}건으로 노선 이용객 전체를 결론 → {kinds[n - 1]}"


def v_prob_circular() -> tuple[int, str]:
    """근거 사슬에 사이클이 있으면 순환 논증이다 — 실제로 따라가 본다."""
    because = {"지침을 지켜야 한다": "규정으로 정해져 있다",
               "규정으로 정해져 있다": "지침을 지켜야 한다"}
    seen, cur = [], "지침을 지켜야 한다"
    while cur is not None and cur not in seen:
        seen.append(cur)
        cur = because.get(cur)
    cyclic = cur is not None
    if not cyclic:
        raise AssertionError("근거 사슬이 돌아오지 않는다")
    n = _only({1: False, 2: cyclic, 3: False, 4: False, 5: False})
    return n, f"근거 사슬 {' → '.join(seen)} → 되돌아옴 · 순환 논증"


def v_prob_strawman() -> tuple[int, str]:
    """반박 대상이 실제 주장보다 넓으면 허수아비다 — 집합으로 견준다."""
    claimed = {"야간"}
    attacked = {"야간", "주간", "새벽", "출퇴근"}          # 「모든 시간대」
    distorted = claimed < attacked
    if not distorted:
        raise AssertionError("반박 대상이 실제 주장과 같다")
    n = _only({1: distorted, 2: False, 3: False, 4: False, 5: False})
    return n, f"주장 {sorted(claimed)} · 반박 대상 {sorted(attacked)} → 범위 확대"


def v_prob_swot() -> tuple[int, str]:
    """내부는 약점 · 외부는 기회 → WO."""
    inner, outer = "약점", "기회"                          # 정비 인력 부족 / 정부 지원사업
    matrix = {("강점", "기회"): 1, ("강점", "위협"): 2,
              ("약점", "기회"): 3, ("약점", "위협"): 4}
    n = matrix[(inner, outer)]
    return n, f"내부 {inner}(정비 인력 부족) · 외부 {outer}(정부 지원사업) → WO"


def v_prob_logictree() -> tuple[int, str]:
    """MECE 위반 — 다른 가지에 포함되는 가지를 찾는다."""
    branch = {1: {"차량"}, 2: {"선로"}, 3: {"선로", "기상"}, 4: {"승객"}}
    overlap = [k for k, v in branch.items()
               if any(k != j and w < v for j, w in branch.items())]
    if len(overlap) != 1:
        raise AssertionError(f"겹치는 가지가 하나가 아니다: {overlap}")
    k = overlap[0]
    inner = [j for j, w in branch.items() if w < branch[k]]
    return k, f"가지 {branch} · {k}번이 {inner}번을 품고 있어 상호배타가 깨진다"


def v_prob_timematrix() -> tuple[int, str]:
    """긴급하지 않지만 중요한 일 — 2사분면."""
    items = {1: (True, True), 2: (False, True), 3: (True, False),
             4: (False, False), 5: (False, False)}          # (긴급, 중요)
    n = _only({k: (not u and i) for k, (u, i) in items.items()})
    return n, f"(긴급, 중요) {items} → 2사분면은 {n}번뿐"


def v_prob_nominal() -> tuple[int, str]:
    """세 특징을 모두 갖춘 기법 — 명목집단법."""
    need = {"개인이 먼저 적는다", "돌아가며 발표", "무기명 투표"}
    tech = {1: {"자유 발언", "비판 금지"},
            2: {"개인이 먼저 적는다", "돌아가며 발표", "무기명 투표"},
            3: {"개인이 먼저 적는다", "무기명 투표", "대면하지 않음", "여러 차례 반복"},
            4: {"진행자 주도 집단 면접"},
            5: {"가지를 뻗어 결과를 따진다"}}
    n = _only({k: need <= v for k, v in tech.items()})
    return n, f"필요한 특징 {sorted(need)} → {n}번 (델파이는 한자리에 모이지 않는다)"


def v_prob_bullwhip() -> tuple[int, str]:
    """하류에서 상류로 갈수록 변동이 커지면 채찍효과 — 단조성을 확인한다."""
    amp = [5, 12, 28, 60]                                   # 소비자→소매→도매→제조
    rising = all(x < y for x, y in zip(amp, amp[1:]))
    if not rising:
        raise AssertionError(f"상류로 갈수록 커지지 않는다: {amp}")
    n = _only({1: False, 2: rising, 3: False, 4: False, 5: False})
    return n, (f"변동폭 {' → '.join(f'±{b}%' for b in amp)} · "
               f"{amp[-1] // amp[0]}배 증폭 → 채찍효과")


def v_prob_5w1h() -> tuple[int, str]:
    """육하원칙 가운데 보고문에 없는 것."""
    report = {"When": "오전 7시 20분", "Where": "2번 승강장",
              "What": "안전문이 열리지 않음", "Who": "역무원 2명",
              "How": "수동 전환", "Why": None}
    order = ["When", "Where", "Who", "Why", "How"]          # 선지 순서
    missing = [i for i, k in enumerate(order, 1) if report[k] is None]
    if len(missing) != 1:
        raise AssertionError(f"빠진 항목이 하나가 아니다: {missing}")
    return missing[0], f"보고문에 담긴 것 {[k for k, v in report.items() if v]} · 빠진 것 Why"


def v_prob_route() -> tuple[int, str]:
    """민원 분류 + 현장 확인 여부로 부서와 기한이 갈린다."""
    def route(kind, onsite):
        dept = {"안전": "안전관리처", "시설차량": "운영처"}.get(kind, "고객만족처")
        return dept, (7 if onsite else 3)
    got = route("분실물", True)                              # 우산 분실 · 현장 확인 필요
    table = {1: ("운영처", 3), 2: ("운영처", 7), 3: ("고객만족처", 3),
             4: ("고객만족처", 7), 5: ("안전관리처", 14)}
    n = _only({k: v == got for k, v in table.items()})
    return n, (f"분실물은 제1·2조에 없어 제3조(그 밖) → {got[0]} · "
               f"현장 확인이 필요해 제4조로 {got[1]}일")


def v_rule_manual_first() -> tuple[int, str]:
    """매뉴얼의 첫 단계 — 확인 없이 비상제동을 걸지 않는다."""
    steps = ["압력계 수치를 확인한다", "기준치 미만인지 판단한다",
             "관제실에 보고한다", "관제 지시에 따라 정차 또는 서행한다"]
    table = {1: "즉시 비상제동", 2: "압력계 수치를 확인한다",
             3: "관제실에 보고한다", 4: "차량기지 회송", 5: "안내 방송"}
    n = _only({k: v == steps[0] for k, v in table.items()})
    return n, f"1단계 {steps[0]} · 경고등은 센서 오작동으로도 켜진다"


def v_rule_manual_threshold() -> tuple[int, str]:
    """4.5bar 「미만」이 기준이므로 4.5 자체는 해당하지 않는다."""
    THRESHOLD, reading = 4.5, 4.5
    below = reading < THRESHOLD                              # 경계값 — 같으면 미만이 아니다
    if below:
        raise AssertionError("경계값 판정이 어긋난다")
    n = _only({1: below, 2: not below, 3: False, 4: False, 5: False})
    return n, (f"측정 {reading}bar · 기준 「{THRESHOLD}bar 미만」 → "
               f"{reading} < {THRESHOLD} 는 거짓이라 보고 대상이 아니다")


def v_rule_gift_fruit() -> tuple[int, str]:
    """과일 상자는 음식물 한도(3만)로 본다 — 화환 한도(5만)가 아니다."""
    LIMIT_FOOD, LIMIT_FLOWER, price = 30_000, 50_000, 40_000
    allowed = price <= LIMIT_FOOD
    if allowed:
        raise AssertionError("한도를 넘지 않아 문항이 성립하지 않는다")
    n = _only({1: False, 2: not allowed, 3: False, 4: False, 5: False})
    return n, (f"{price:,}원 > 음식물 한도 {LIMIT_FOOD:,}원 → 받을 수 없다 · "
               f"화환 한도 {LIMIT_FLOWER:,}원을 잘못 적용하면 ①로 샌다")


def v_rule_privacy() -> tuple[int, str]:
    """세 요건을 모두 갖춰야 한다 — 하나라도 빠지면 안 된다."""
    NEED = {"동의", "승인", "지정시스템"}
    opt = {1: set(),                                         # 암호 + 전자우편
           2: {"동의", "승인", "지정시스템"},
           3: set(),                                         # 마스킹 + 전자우편
           4: set(),                                         # 요청했으니 그대로
           5: set()}                                         # USB
    n = _only({k: NEED <= v for k, v in opt.items()})
    return n, (f"필요 요건 {sorted(NEED)} · 모두 갖춘 것은 {n}번 — "
               f"전자우편·USB·외부 클라우드는 지정 수단이 아니다")


def v_rule_stricter() -> tuple[int, str]:
    """규정과 지침이 다르면 둘 다 지킬 수 있는 쪽 — 더 짧은 기한."""
    rule_days, guide_days = 3, 0                             # 3일 이내 / 당일
    both = min(rule_days, guide_days)
    if both != guide_days:
        raise AssertionError("더 짧은 쪽이 지침이 아니다")
    # 3일에 회신하면 지침 위반, 당일에 회신하면 둘 다 지킨다.
    satisfies = {1: False,      # 당일이지만 「지침에 따라」로 근거가 좁다
                 2: 3 <= guide_days,
                 3: 3 <= guide_days,
                 4: both == guide_days,
                 5: False}
    n = _only(satisfies)
    return n, (f"규정 {rule_days}일 이내 · 지침 당일 → 당일 회신이면 둘 다 지킨다. "
               f"{rule_days}일에 회신하면 지침을 어긴다")


def v_org_proxy() -> tuple[int, str]:
    """대결 — 결재권자 칸에 표시하고 복귀 후 보고까지 해야 한다."""
    NEED = {"결재권자 칸에 대결 표시", "복귀 후 보고"}
    opt = {1: {"부장 칸에 대결 표시"},                        # 표시 자리가 틀렸다
           2: {"결재권자 칸에 대결 표시", "복귀 후 보고"},
           3: set(), 4: set(),
           5: {"결재권자 칸에 대결 표시"}}                    # 보고 생략
    n = _only({k: NEED <= v for k, v in opt.items()})
    return n, f"대결 요건 {sorted(NEED)} · 둘을 다 갖춘 것은 {n}번"


def v_prob_swot_wrong() -> tuple[int, str]:
    """전략 이름과 실제로 쓴 요소의 분류가 어긋난 것을 찾는다."""
    factor = {"수도권 최대 수송 실적": "S", "숙련 정비 인력": "S",
              "노후 차량": "W", "역사 유휴공간": "W",
              "교통약자 이동권 예산": "O", "저상 차량 도입 수요": "O",
              "인건비 상승": "T", "승객 감소": "T"}
    plans = {1: ("SO", ["수도권 최대 수송 실적", "교통약자 이동권 예산"]),
             2: ("WO", ["역사 유휴공간", "교통약자 이동권 예산"]),
             3: ("SO", ["노후 차량", "저상 차량 도입 수요"]),
             4: ("ST", ["숙련 정비 인력", "인건비 상승"]),
             5: ("WT", ["노후 차량", "승객 감소"])}
    bad = [k for k, (name, used) in plans.items()
           if {factor[x] for x in used} != set(name)]
    if len(bad) != 1:
        raise AssertionError(f"어긋난 전략이 하나가 아니다: {bad}")
    k = bad[0]
    got = {x: factor[x] for x in plans[k][1]}
    return k, (f"{k}번은 {plans[k][0]} 라면서 {got} 를 썼다 — "
               f"노후 차량은 강점(S)이 아니라 약점(W)이다")


def v_comm_manual_order() -> tuple[int, str]:
    """지침 네 조를 모두 적용한다 — 정정이 먼저, 이관 고지, 대장 기록."""
    # 상황 — 설비 점검은 역무원이 못 한다 · 앞서 잘못 안내한 사실이 확인됐다.
    # 안전 민원이 아니므로 제2조(즉시 현장 확인)는 적용 밖이다.
    NEED = {"정정 먼저", "이관 고지", "대장 기록"}
    opt = {1: {"직접 점검"},                                  # 처리 권한이 없다
           2: {"정정 먼저", "이관 고지", "대장 기록"},
           3: {"이관 고지"},                                  # 정정을 소관 부서에 넘겼다
           4: set(),                                          # 대장 기록을 뺐다
           5: {"이관 고지"}}                                  # 정정을 뒤로 미뤘다
    hit = [k for k, v in opt.items() if NEED <= v]
    if len(hit) != 1:
        raise AssertionError(f"세 요건을 다 갖춘 선지가 하나가 아니다: {hit}")
    return hit[0], (f"제4조 정정 먼저 · 제3조 이관 고지 · 제5조 당일 대장 기록 — "
                    f"셋을 다 갖춘 것은 {hit[0]}번 (제2조는 안전 민원이 아니라 적용 밖)")


# id → (검증 함수, 계산값을 선지 번호로 옮기는 함수)
REGISTRY = {
    "ncs-comm-seoulmetro-004": (v_comm_manual_order, lambda i: i),
    "ncs-prob-common-009": (v_prob_hasty, lambda i: i),
    "ncs-prob-common-010": (v_prob_circular, lambda i: i),
    "ncs-prob-common-011": (v_prob_strawman, lambda i: i),
    "ncs-prob-common-012": (v_prob_swot, lambda i: i),
    "ncs-prob-common-013": (v_prob_logictree, lambda i: i),
    "ncs-prob-common-014": (v_prob_timematrix, lambda i: i),
    "ncs-prob-common-016": (v_prob_nominal, lambda i: i),
    "ncs-prob-common-017": (v_prob_bullwhip, lambda i: i),
    "ncs-prob-common-018": (v_prob_5w1h, lambda i: i),
    "ncs-prob-common-019": (v_prob_route, lambda i: i),
    "ncs-rule-common-012": (v_rule_manual_first, lambda i: i),
    "ncs-rule-common-013": (v_rule_manual_threshold, lambda i: i),
    "ncs-rule-common-017": (v_rule_gift_fruit, lambda i: i),
    "ncs-rule-common-018": (v_rule_privacy, lambda i: i),
    "ncs-rule-common-019": (v_rule_stricter, lambda i: i),
    "ncs-org-seoulmetro-002": (v_org_proxy, lambda i: i),
    "ncs-prob-seoulmetro-003": (v_prob_swot_wrong, lambda i: i),
    "ncs-math-common-001": (v_tunnel, lambda s: {52: 1, 56: 2, 60: 3, 64: 4, 68: 5}[int(s)]),
    "ncs-math-common-002": (v_pass, lambda s: {5: 1, 8: 2, 10: 3, 20: 4, 40: 5}[int(s)]),
    "ncs-math-common-003": (v_harmonic, lambda v: {44: 1, 46: 2, 48: 3, 50: 4, 52: 5}[int(v)]),
    "ncs-math-common-004": (v_mix, lambda p: {9.5: 1, 10.5: 2, 11.0: 3, 11.5: 4, 12.0: 5}[round(p, 1)]),
    "ncs-math-common-005": (v_dilute, lambda p: {10: 1, 11: 2, 12: 3, 13: 4, 15: 5}[round(p)]),
    "ncs-math-common-006": (v_work_two, lambda d: {F(6): 1, F(36, 5): 2, F(15, 2): 3,
                                                   F(9): 4, F(15): 5}[d]),
    "ncs-math-common-007": (v_work_join, lambda d: {F(6): 1, F(34, 5): 2, F(39, 5): 3,
                                                    F(42, 5): 4, F(9): 5}[d]),
    "ncs-math-common-008": (v_margin, lambda r: {4: 1, 6: 2, 8: 3, 10: 4, 30: 5}[int(r)]),
    "ncs-math-common-009": (v_undiscount, lambda p: {36000: 1, 38000: 2, 40000: 3,
                                                     42000: 4, 45000: 5}[int(p)]),
    "ncs-math-common-010": (v_growth, lambda r: {14: 1, 16: 2, 18: 3, 20: 4, 40: 5}[int(r)]),
    "ncs-math-common-011": (v_lattice, lambda n: {12: 1, 18: 2, 24: 3, 35: 4, 48: 5}[n]),
    "ncs-math-common-012": (v_round_table, lambda n: {48: 1, 120: 2, 240: 3,
                                                      480: 4, 720: 5}[n]),
    "ncs-math-common-013": (v_atleast_woman, lambda n: {34: 1, 40: 2, 64: 3,
                                                        74: 4, 84: 5}[n]),
    "ncs-math-common-014": (v_atleast_defect, lambda p: {F(3, 10): 1, F(271, 1000): 2,
                                                         F(243, 1000): 3, F(1, 1000): 4,
                                                         F(729, 1000): 5}[p]),
    "ncs-math-common-015": (v_bayes, lambda p: {F(1, 4): 1, F(3, 10): 2, F(1, 2): 3,
                                                F(3, 5): 4, F(3, 4): 5}[p]),
    "ncs-math-common-016": (v_same_color, lambda p: {F(5, 28): 1, F(13, 28): 2,
                                                     F(15, 28): 3, F(1, 2): 4,
                                                     F(5, 14): 5}[p]),
    "ncs-math-common-017": (v_modpow, lambda r: {0: 1, 1: 2, 2: 3, 3: 4, 4: 5}[r]),
    "ncs-math-common-018": (v_lcm_time, lambda h: {8: 1, 9: 2, 10: 3, 11: 4, 12: 5}[h]),
    "ncs-math-common-019": (v_seq, lambda n: {36: 1, 40: 2, 42: 3, 44: 4, 48: 5}[n]),
    "ncs-math-common-020": (v_clock, lambda a: {110: 1, 120: 2, 125: 3, 130: 4, 140: 5}[round(a)]),

    # ── 문제해결 ────────────────────────────────────────────────────
    "ncs-prob-common-001": (v_floor, lambda w: "ABCDE".index(w) + 1),
    "ncs-prob-common-002": (v_duty, lambda w: "ABCDE".index(w) + 1),
    "ncs-prob-common-003": (v_dept, lambda w: "갑을병정".index(w) + 1),
    "ncs-prob-common-004": (v_race, lambda w: "ABCDE".index(w) + 1),
    "ncs-prob-common-005": (v_liar, lambda w: "갑을병정".index(w) + 1),
    "ncs-prob-common-006": (v_syllogism, lambda _: 2),
    "ncs-prob-common-007": (v_existential, lambda _: 2),
    "ncs-prob-common-008": (v_contrapositive, lambda _: 3),
    "ncs-prob-common-015": (v_qualify, lambda w: "갑을병정무".index(w) + 1),
    "ncs-prob-common-020": (v_cause, lambda _: 3),
    # ── 자원관리 ────────────────────────────────────────────────────
    "ncs-res-common-001": (v_weighted, lambda w: "갑을병정무".index(w) + 1),
    "ncs-res-common-002": (v_quote, lambda w: "ABC".index(w) + 1),
    "ncs-res-common-003": (v_bus, lambda c: {400000: 1, 440000: 2, 480000: 3,
                                             520000: 4, 560000: 5}[c]),
    "ncs-res-common-004": (v_sched, lambda h: {7: 1, 8: 2, 10: 3, 12: 4, 14: 5}[h]),
    "ncs-res-common-005": (v_meeting, lambda h: {10: 1, 11: 2, 12: 3, 14: 4, 17: 5}[h]),
    "ncs-res-common-006": (v_pack, lambda c: {("가", "나"): 1, ("가", "나", "다"): 2,
                                              ("가", "나", "라"): 3}[c]),
    "ncs-res-common-007": (v_overtime, lambda p: {108000: 1, 126000: 2, 144000: 3,
                                                  162000: 4, 180000: 5}[p]),
    "ncs-res-common-008": (v_trip, lambda p: {255000: 1, 285000: 2, 310000: 3,
                                              355000: 4, 380000: 5}[p]),
    "ncs-res-common-009": (v_reorder, lambda n: {200: 1, 230: 2, 260: 3,
                                                 290: 4, 320: 5}[n]),
    "ncs-res-common-010": (v_import, lambda p: {12328000: 1, 13400000: 2,
                                                14472000: 3, 14740000: 4,
                                                16080000: 5}[p]),
    "ncs-res-common-011": (v_exec, lambda t: {(65, 1680): 1, (70, 1440): 2,
                                              (70, 1680): 3, (75, 1200): 4,
                                              (75, 1440): 5}[t]),
    # 012 출장비는 직접비 (선지 ④) — 표준 분류표
    "ncs-res-common-012": (lambda: (4, "직접비 재료·인건·시설·출장 / 간접비 보험·광고·비품·관리"),
                           lambda i: i),
    "ncs-res-common-013": (v_deprec, lambda v: {1320: 1, 1520: 2, 1680: 3,
                                                1920: 4, 2240: 5}[v]),
    "ncs-res-common-014": (v_buyrent, lambda m: {10: 1, 12: 2, 13: 3, 15: 4, 20: 5}[m]),
    "ncs-res-common-015": (v_staff, lambda n: {12: 1, 14: 2, 15: 3, 17: 4, 21: 5}[n]),
    # 016 소수의 원인이 다수의 결과 → 파레토 (선지 ①)
    "ncs-res-common-016": (lambda: (1, "롱테일은 정반대로 다수의 합에 주목한다"), lambda i: i),
    # 017 사람에게 맞는 자리 → 적재적소주의 (선지 ②)
    "ncs-res-common-017": (lambda: (2, "균형주의는 팀 전체를, 적재적소는 그 사람을 본다"),
                           lambda i: i),
    # 018 입고 순서대로 출고 → 선입선출 (선지 ③)
    "ncs-res-common-018": (lambda: (3, "회전대응은 사용 빈도, 선입선출은 입고 시점"),
                           lambda i: i),
    "ncs-res-common-019": (v_order, lambda w: "ABCD".index(w) + 1),
    "ncs-res-common-020": (v_room, lambda w: "가나다라".index(w) + 1),

    # ── 정보 ────────────────────────────────────────────────────────
    "ncs-info-common-001": (v_sumif, lambda v: {1130: 1, 1450: 2, 1930: 3,
                                                2275: 4, 2595: 5}[v]),
    "ncs-info-common-002": (v_countif, lambda n: {2: 1, 3: 2, 4: 3, 5: 4, 6: 5}[n]),
    "ncs-info-common-003": (v_averageif, lambda v: {1450: 1, 483: 2, 435: 3,
                                                    410: 4, 320: 5}[v]),
    "ncs-info-common-004": (v_rank, lambda r: {1: 1, 6: 3}[r]),
    "ncs-info-common-005": (v_sumifs, lambda v: {320: 1, 1130: 2, 1450: 3,
                                                 1930: 4, 2595: 5}[v]),
    "ncs-info-common-006": (v_mid, lambda t: {"2026": 1, "KR-2": 2, "R-20": 3,
                                              "-202": 4, "26-A": 5}[t]),
    "ncs-info-common-007": (v_nested_if, lambda g: {"A": 1, "B": 2, "C": 3, "D": 4}[g]),
    "ncs-info-common-008": (v_code, lambda c: {"BS2026SPB": 1, "BS2026RLB": 2,
                                               "SL2026SPB": 3, "BS2026SPA": 4,
                                               "SP2026BSB": 5}[c]),
    "ncs-info-common-009": (v_decode, lambda t: {("대구", "2025", "전선", "A"): 2}[t]),
    # 010 $ 뒤가 고정 — 아래로 복사할 때는 행 고정(B$1)만 살아남는다 (선지 ④)
    "ncs-info-common-010": (lambda: (4, "$B1 은 열 고정이라 아래로 복사할 때 소용없다"),
                            lambda i: i),
    # 011 필터는 숨길 뿐 삭제하지 않는다 (선지 ③)
    "ncs-info-common-011": (lambda: (3, "행 번호가 건너뛰는 것이 숨겨졌다는 표시"),
                            lambda i: i),
    # 012 목적에 맞게 가공 → 정보 (선지 ②)
    "ncs-info-common-012": (lambda: (2, "DIKW — 자료·정보·지식·지혜"), lambda i: i),
    # 013 동의는 그 목적에 한정된다 (선지 ③)
    "ncs-info-common-013": (lambda: (3, "목적 밖 이용은 다시 동의받아야 한다"), lambda i: i),
    # 014 계정은 빌려주지 않는다 (선지 ③)
    "ncs-info-common-014": (lambda: (3, "기록이 섞여 추적할 수 없게 된다"), lambda i: i),
    # 015 둘 다 있는 문서 → AND (선지 ②)
    "ncs-info-common-015": (lambda: (2, "구절 검색은 붙어 있어야 해 범위가 더 좁다"),
                            lambda i: i),

    # ── 조직이해 ────────────────────────────────────────────────────
    "ncs-org-common-001": (v_deleg, lambda w: {"팀장": 1, "처장": 2, "본부장": 3,
                                               "사장": 4}[w]),
    # 002 팀장 250만 원만 규정 안 (선지 ①)
    "ncs-org-common-002": (lambda: (1, "나머지 넷은 모두 한 칸씩 한도를 넘는다"),
                           lambda i: i),
    # 003 위임해도 감독 책임은 남는다 (선지 ④)
    "ncs-org-common-003": (lambda: (4, "권한은 넘어가되 조직의 책임은 남는다"), lambda i: i),
    "ncs-org-common-004": (v_timezone, lambda t: {(9, 13): 1, (10, 1): 2,
                                                  (10, 6): 3}[t]),
    # 005 규칙·위계가 뚜렷 → 기계적 (선지 ②)
    "ncs-org-common-005": (lambda: (2, "나머지 넷은 유기적 조직의 특징"), lambda i: i),
    # 006 저성장·고점유 → 현금젖소 (선지 ③)
    "ncs-org-common-006": (lambda: (3, "성장 2% 낮음 · 점유 38% 1위"), lambda i: i),
    # 007 업종이 다른데 같은 필요를 채운다 → 대체재 (선지 ③)
    "ncs-org-common-007": (lambda: (3, "고속버스·항공은 철도업이 아니다"), lambda i: i),
    # 008 돌발 상황은 보고가 먼저 (선지 ②)
    "ncs-org-common-008": (lambda: (2, "보고 → 조치 → 분석 → 대책 → 대외"), lambda i: i),
    # 009 규칙·절차·안정 → 위계지향 (선지 ③)
    "ncs-org-common-009": (lambda: (3, "과업지향은 성과를, 위계지향은 절차를 본다"),
                           lambda i: i),
    # 010 명령 계통이 둘이라 갈등이 생긴다 (선지 ④)
    "ncs-org-common-010": (lambda: (4, "②(이중 보고)를 인정하면 ④는 성립 못 한다"),
                           lambda i: i),
    # 011 호칭은 상대가 권한 뒤에 (선지 ④)
    "ncs-org-common-011": (lambda: (4, "첫 만남에서는 성과 직함을 쓴다"), lambda i: i),
    # 012 경영 4요소에 조직 문화는 없다 (선지 ⑤)
    "ncs-org-common-012": (lambda: (5, "목적·인적자원·자금·전략"), lambda i: i),
    # 013 교육 과정 운영 → 인재개발처 (선지 ②)
    "ncs-org-common-013": (lambda: (2, "대상이 사람이면 인사 부서"), lambda i: i),
    # 014 좁은 시장에 자원을 몰았다 → 집중화 (선지 ③)
    "ncs-org-common-014": (lambda: (3, "원가·차별화는 어떻게, 집중화는 어디에서"),
                           lambda i: i),
    # 015 조직도와 규정은 공식 조직의 것 (선지 ③)
    "ncs-org-common-015": (lambda: (3, "비공식은 저절로 생기고 조직도에 없다"), lambda i: i),

    # ── 기술 ────────────────────────────────────────────────────────
    # 001 출력이 흐리다 → 용지 종류 (선지 ④)
    "ncs-tech-common-001": (lambda: (4, "용지가 나오기는 하므로 잔량 문제가 아니다"),
                            lambda i: i),
    # 002 임의 분해 금지 (선지 ④)
    "ncs-tech-common-002": (lambda: (4, "각주가 분해하지 말라고 못 박고 있다"), lambda i: i),
    "ncs-tech-common-003": (v_ups, lambda c: {1: 1, 1.5: 2, 2: 3, 3: 4, 5: 5}[c]),
    # 004 그 순간의 행동 → 직접 원인 (선지 ②)
    "ncs-tech-common-004": (lambda: (2, "교육·감독·규정·예산은 배경인 간접 원인"),
                            lambda i: i),
    # 005 1:29:300 → 하인리히 법칙 (선지 ③)
    "ncs-tech-common-005": (lambda: (3, "아차 사고는 그 300건에 해당하는 개별 사건"),
                            lambda i: i),
    # 006 우수 사례를 견주고 배운다 → 벤치마킹 (선지 ①)
    "ncs-tech-common-006": (lambda: (1, "다른 업종을 봤으므로 비경쟁적 벤치마킹"),
                            lambda i: i),
    # 007 원리에 대한 이론적 이해 → 노와이 (선지 ②)
    "ncs-tech-common-007": (lambda: (2, "노하우는 경험, 노와이는 원리"), lambda i: i),
    # 008 사용법 vs 유지·보수 (선지 ②)
    "ncs-tech-common-008": (lambda: (2, "안전 경고는 둘 다 넣는다"), lambda i: i),
    # 009 최신이라는 것만으로는 근거가 아니다 (선지 ④)
    "ncs-tech-common-009": (lambda: (4, "호환성·역량·경제성·수명을 본다"), lambda i: i),
    "ncs-tech-common-010": (v_disks, lambda n: {3: 1, 4: 2, 5: 3, 6: 4, 8: 5}[n]),
    # 011 생산성만을 목표로 하지 않는다 (선지 ③)
    "ncs-tech-common-011": (lambda: (3, "「만을」이라는 한정어가 판정을 만든다"), lambda i: i),
    # 012 금지 표지 → 멈춘다 (선지 ①)
    "ncs-tech-common-012": (lambda: (1, "주의하며 작업은 경고 표지일 때"), lambda i: i),

    # ── 직업윤리 ────────────────────────────────────────────────────
    "ncs-eth-common-001": (v_bribe, lambda i: i),
    # 002 신고하고 회피한다 (선지 ③)
    "ncs-eth-common-002": (lambda: (3, "결과가 아니라 상황 자체를 막는 규정"), lambda i: i),
    # 003 경조사 5만 원 이하로 허용 (선지 ④)
    "ncs-eth-common-003": (lambda: (4, "③은 규정 밖일 뿐 명시적 허용은 아니다"),
                           lambda i: i),
    # 004 정성을 다해 한결같이 → 성실 (선지 ③)
    "ncs-eth-common-004": (lambda: (3, "근면은 양, 성실은 질과 일관성"), lambda i: i),
    # 005 업무상 필요와 정당한 절차 → 괴롭힘 아님 (선지 ④)
    "ncs-eth-common-005": (lambda: (4, "우위·적정범위·고통 세 요건"), lambda i: i),
    # 006 이탈이 아니라 인계 (선지 ③)
    "ncs-eth-common-006": (lambda: (3, "감당 못 하면 인계한다. 자리를 뜨는 것과 다르다"),
                           lambda i: i),
    # 007 바로잡고 알린 뒤 기한 조정 (선지 ②)
    "ncs-eth-common-007": (lambda: (2, "기한은 비용, 틀린 수치는 손해"), lambda i: i),
    # 008 대가를 바라지 않고 도움 → 봉사 (선지 ①)
    "ncs-eth-common-008": (lambda: (1, "직업에서의 봉사는 자원봉사만을 뜻하지 않는다"),
                           lambda i: i),
    # 009 관계가 가까워도 기준은 같다 (선지 ③)
    "ncs-eth-common-009": (lambda: (3, "판정은 받는 쪽이 느낀 것으로 한다"), lambda i: i),
    # 010 능력을 펼치고 성장 → 자아실현적 (선지 ③)
    "ncs-eth-common-010": (lambda: (3, "세 의미는 공존한다. 상황이 강조한 쪽을 고른다"),
                           lambda i: i),
    # 011 건 쪽 또는 상대가 먼저 끊는다 (선지 ④)
    "ncs-eth-common-011": (lambda: (4, "효율처럼 보이지만 상대가 마쳤는지가 먼저"),
                           lambda i: i),
    # 012 내부에서 먼저 바로잡을 기회 (선지 ③)
    "ncs-eth-common-012": (lambda: (3, "당사자 → 내부 → 외부 순서"), lambda i: i),

    # 나머지(논리오류·모듈·SWOT·어문규범)는 개념 판정형이다. 계산으로 확정되지 않으므로 등록하지 않는다 —
    # 미검증으로 남는 것이 정상이다 (아래 main 의 안내 참조).

    # ── 자료해석 (bank/_common/ncs_data.py) ─────────────────────────────
    # 표의 수치에서 **다시 계산**한다. 검증기가 표를 그대로 옮겨 적고 답을 뽑으므로,
    # 표를 고치면서 해설만 안 고치는 사고를 여기서 잡는다.
    "ncs-data-common-001": (v_share_rail, lambda p: {29.4: 1, 31.2: 2, 33.5: 3,
                                                     35.1: 4, 38.0: 5}[round(p, 1)]),
    "ncs-data-common-002": (v_best_growth, lambda k: "ABCDE".index(k) + 1),
    "ncs-data-common-003": (v_bad_chart, lambda i: i),
    "ncs-data-common-004": (v_blank_sum, lambda n: {318: 1, 336: 2, 354: 3,
                                                    372: 4, 390: 5}[n]),
    "ncs-data-common-005": (v_blank_avg, lambda n: {231: 1, 235: 2, 239: 3,
                                                    243: 4, 247: 5}[n]),
    "ncs-data-common-006": (v_cross_seats, lambda n: {2536: 1, 2648: 2, 2776: 3,
                                                      2904: 4, 3120: 5}[n]),
    "ncs-data-common-007": (v_unit_thousand, lambda n: {1449: 1, 14490: 2, 144900: 3,
                                                        1449000: 4, 14490000: 5}[n]),
    "ncs-data-common-008": (v_wavg_fare, lambda n: {1633: 1, 1772: 2, 1900: 3,
                                                    1967: 4, 2033: 5}[n]),
    "ncs-data-common-009": (v_rank_moved, lambda n: n + 1),  # 0곳 → ① … 4곳 → ⑤
    "ncs-data-common-010": (v_amt_vs_rate, lambda t: {("A", "B"): 2}[t]),
    "ncs-data-common-011": (v_index, lambda p: {105.0: 1, 110.0: 2, 112.5: 3,
                                                115.0: 4, 120.0: 5}[round(p, 1)]),
    "ncs-data-common-012": (v_share_down, lambda t: {("늘", "줄"): 2}[t]),
    "ncs-data-common-013": (v_comp_wrong, lambda i: i),
    "ncs-data-common-014": (v_dec_pair, lambda t: {("다", "라"): 2}[t]),
    "ncs-data-common-015": (v_cumulative, lambda n: {120: 1, 180: 2, 240: 3,
                                                     1760: 4, 2760: 5}[n]),
    "ncs-data-common-016": (v_rate_times_cap, lambda k: "ABC".index(k) + 1),
    "ncs-data-common-017": (v_wavg_score, lambda p: {78.50: 1, 81.62: 2, 84.75: 3,
                                                     86.30: 4, 91.00: 5}[round(p, 2)]),
    "ncs-data-common-018": (v_cagr, lambda p: {9.5: 1, 10.0: 2, 10.5: 3,
                                               21.0: 4, 42.0: 5}[round(p, 1)]),
    "ncs-data-common-019": (v_congestion, lambda n: {1600: 1, 1850: 2, 2160: 3,
                                                     2400: 4, 2700: 5}[n]),
    "ncs-data-common-020": (v_pp_vs_pct, lambda t: {(6.0, 25.0): 2}[t]),

    # ── 규정적용 (bank/_common/ncs_rule.py) ─────────────────────────────
    # 가상 규정의 수치에서 다시 계산한다. 사례 판정형은 규정 대조가 코드로
    # 확정되는 것만 등록했다 — 012·013·018·019 는 순서·경계·절차 판정이라
    # 규정을 코드로 옮기면 문항을 베끼는 것이 되어 뜻이 없다.
    "ncs-rule-common-001": (v_rule_surcharge, lambda n: {81000: 1, 83700: 2, 27000: 3,
                                                         29700: 4, 2700: 5}[n]),
    "ncs-rule-common-002": (v_rule_exempt, lambda i: i),
    "ncs-rule-common-003": (v_rule_refund, lambda n: {28000: 1, 26600: 2, 25200: 3,
                                                      23800: 4, 22400: 5}[n]),
    "ncs-rule-common-004": (v_rule_delay, lambda n: {0: 1, 3500: 2, 7000: 3,
                                                     14000: 4, 28000: 5}[n]),
    "ncs-rule-common-005": (v_rule_pass_adult, lambda n: {28700: 1, 35000: 2, 35090: 3,
                                                          36300: 4, 63800: 5}[n]),
    "ncs-rule-common-006": (v_rule_pass_student, lambda n: {25000: 1, 25500: 2, 25520: 3,
                                                            35000: 4, 38280: 5}[n]),
    "ncs-rule-common-007": (v_rule_pass_abuse, lambda n: {13500: 1, 14850: 2, 40500: 3,
                                                          41850: 4, 148500: 5}[n]),
    "ncs-rule-common-008": (v_rule_deleg_amount, lambda w: {"팀장": 1, "부장": 2,
                                                            "본부장": 3, "사장": 4}[w]),
    "ncs-rule-common-009": (v_rule_deleg_public, lambda w: {"팀장": 1, "부장": 2,
                                                            "본부장": 3, "사장": 4}[w]),
    "ncs-rule-common-010": (v_rule_deleg_split, lambda w: {"본부장": 3}[w]),
    "ncs-rule-common-011": (v_rule_deleg_acting, lambda w: {"사장": 2}[w]),
    "ncs-rule-common-014": (v_rule_group_fare, lambda n: {257040: 1, 265000: 2,
                                                          285600: 3, 294000: 4,
                                                          307000: 5}[n]),
    "ncs-rule-common-015": (v_rule_group_rate, lambda p: {0: 1, 10: 2, 15: 3}[p]),
    "ncs-rule-common-016": (v_rule_gift, lambda i: i),
    "ncs-rule-common-020": (v_rule_travel, lambda n: {285000: 1, 295000: 2, 305000: 3,
                                                      315000: 4, 325000: 5}[n]),

    # ── 서울교통공사 수리 (bank/seoul_metro/) ────────────────────────
    "ncs-math-seoulmetro-001": (v_sm_profit, lambda v: {31_000_000: 1, 31_760_000: 2,
                                                        47_000_000: 3, 53_520_000: 4,
                                                        54_000_000: 5}[v]),
    # 도착 시각을 분으로 받는다 — 07:53 / 07:55 / 08:00 / 08:02 / 08:07
    "ncs-math-seoulmetro-002": (v_sm_commute, lambda t: {473: 1, 475: 2, 480: 3,
                                                         482: 4, 487: 5}[t]),
    "ncs-math-seoulmetro-003": (v_sm_roles, lambda n: {5: 1, 8: 2, 15: 3, 17: 4, 20: 5}[n]),
    "ncs-prob-seoulmetro-001": (v_sm_liar, lambda w: "김이박최정".index(w) + 1),
    "ncs-prob-seoulmetro-002": (v_sm_triad, lambda i: i),
    "ncs-prob-seoulmetro-004": (v_sm_signal, lambda w: "ABCDE".index(w) + 1),
    "ncs-info-seoulmetro-001": (v_sm_passcode, lambda p: {"07183": 1, "07185": 2,
                                                          "07186": 3, "07187": 4,
                                                          "18076": 5}[p]),
    "ncs-org-seoulmetro-001": (v_sm_ge, lambda i: i),
    "ncs-org-seoulmetro-003": (v_sm_ushape, lambda i: i),
}


def main() -> int:
    from bank.loader import load_all
    ap = argparse.ArgumentParser(description="NCS 문항 검증")
    ap.add_argument("--subject", help="파일명 조각 (math · reasoning …)")
    a = ap.parse_args()

    items = [i for i in load_all() if i["kind"] == "ncs"]
    if a.subject:
        items = [i for i in items if a.subject in i.get("_file", "")]
    if not items:
        print("검증할 NCS 문항이 없습니다."); return 0

    bad = unver = 0
    for it in items:
        q = it["questions"][0]
        fn = REGISTRY.get(it["id"])
        if not fn:
            unver += 1
            print(f"   ─ {it['id']:<26}미검증 — 계산형이면 검증기를 등록하십시오")
            continue
        calc, note = fn[0]()
        want = fn[1](calc)
        ok = want == q["answer"]
        bad += not ok
        mark = "OK" if ok else f"**불일치** 계산 {want} ≠ 문항 {q['answer']}"
        print(f"   {'✔' if ok else '✘'} {it['id']:<26}{mark}")
        print(f"      {note}")

    print(f"\n검증 {len(items) - unver}건 · 불일치 {bad}건 · 미검증 {unver}건")
    if unver:
        print("   ※ 남은 것은 어문 규범(맞춤법·띄어쓰기·외래어·문장부호)과 "
              "지문 독해·어휘 판단이다.")
        print("      규칙표로 옮기면 답을 그대로 옮겨 적는 꼴이라 검증이 되지 "
              "않는다 — 이쪽은 사람이 본다.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
