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

def solve_unique(people, positions, rules) -> tuple[list, str]:
    """규칙을 만족하는 배치를 모두 찾는다. **하나가 아니면 문항이 성립하지 않는다.**"""
    ok = [dict(zip(people, p)) for p in permutations(positions, len(people))
          if all(r(dict(zip(people, p))) for r in rules)]
    return ok, f"가능한 배치 {len(ok)}가지"


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
