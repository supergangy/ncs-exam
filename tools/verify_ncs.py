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
    # 나머지(논리오류·모듈·SWOT)는 개념 판정형이다. 계산으로 확정되지 않으므로 등록하지 않는다 —
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
