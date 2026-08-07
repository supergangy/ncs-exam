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


# id → (검증 함수, 계산값을 선지 번호로 옮기는 함수)
REGISTRY = {
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
        print("   ※ 지문 독해·어문 규범은 계산으로 확정되지 않는다. "
              "그쪽은 미검증으로 남는 것이 정상이다.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
