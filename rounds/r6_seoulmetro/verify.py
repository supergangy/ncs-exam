# -*- coding: utf-8 -*-
"""제6회 계산형 문항의 답을 **다시 구해** 문항과 대조한다.

    python rounds/r6_seoulmetro/verify.py

규율은 `rounds/r5_nhis/verify.py` 와 같다.

* **선지 번호를 계산 함수 안에 적지 않는다.** 계산은 값을 내고, 그 값을 선지
  번호로 옮기는 일은 따로 한다. 그래야 `tools/reorder_choices.py` 로 선지를
  섞어도 검증이 따라온다.
* 지문 독해·어문 규범·모듈 개념은 계산으로 확정되지 않으므로 다루지 않는다.

## 이 파일이 있는 이유

집필 중에 손으로 두 건을 잡았다.

  05  선지 ④가 **실제로 참**이라 정답이 둘이었다 (1,431+1,395+810 = 3,636 < 4,000)
  24  해설은 ㄹ을 틀렸다 하고 정답은 ㄹ을 넣었다. 게다가 「ㄱ, ㄷ」 선지가 아예 없었다

둘 다 **선지의 참·거짓을 하나씩 따져 보면** 바로 드러난다. 그래서 자료해석·
조합형은 정답만이 아니라 **선지 다섯의 참·거짓을 모두** 확인한다.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
from datetime import date
from itertools import combinations, permutations

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CIRC = "①②③④⑤"
ok, bad = [], []


def load(mod: str):
    p = HERE / "content" / f"{mod}.py"
    spec = importlib.util.spec_from_file_location(mod, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# 문항 번호 → 문항. **작성 순서**로 매긴다.
#   시험지의 최종 번호는 `layout.py` 가 면을 채우며 같은 영역 안에서 바꿀 수 있다.
#   여기서 검사하는 것은 **문항 자체**이므로 라벨이 최종 번호와 한둘 어긋나도
#   검사 대상은 정확하다. 최종 번호는 빌드 로그의 `[정답순서]` 를 본다.
def index() -> dict[int, dict]:
    import importlib
    cfg = importlib.import_module(f"rounds.{HERE.name}.config")
    out, no = {}, 0
    for mod, _area, _n in cfg.AREAS:
        for b in load(mod).BLOCKS:
            for q in b["questions"]:
                no += 1
                out[no] = q
    return out


Q = index()


def check(no: int, got, why: str = "") -> None:
    """`got` 이 문항의 정답 선지 번호와 같은가"""
    want = Q[no]["answer"]
    line = f"{no:02d}  기대 {CIRC[want-1]} · 계산 {CIRC[got-1] if 1 <= got <= 5 else got}"
    (ok if got == want else bad).append(line + (f"  ({why})" if why else ""))


def check_claims(no: int, truth: list[bool], why: str = "") -> None:
    """선지 다섯의 참·거짓을 통째로 본다 — **참이 정확히 하나**여야 한다.

    05 처럼 정답이 둘이 되는 사고는 이 검사로만 잡힌다.
    """
    want = Q[no]["answer"]
    trues = [i + 1 for i, t in enumerate(truth) if t]
    if len(trues) != 1:
        bad.append(f"{no:02d}  참인 선지가 {len(trues)}개다 — {trues} ({why})")
    elif trues[0] != want:
        bad.append(f"{no:02d}  기대 {CIRC[want-1]} · 참인 것은 {CIRC[trues[0]-1]} ({why})")
    else:
        ok.append(f"{no:02d}  선지 다섯의 참·거짓이 모두 맞는다 ({why})")


# ── 05 자료해석 — 선지 다섯을 모두 따진다 ──────────────────────────
y25 = {"편의점": 1240, "식음료": 1160, "생활용품": 800, "기타": 800}
y26 = {"편의점": 1431, "식음료": 1395, "생활용품": 810, "기타": 864}
s25, s26 = sum(y25.values()), sum(y26.values())
assert (s25, s26) == (4000, 4500), "표의 합계가 어긋난다"
up = {k: y26[k] - y25[k] for k in y25}
check_claims(5, [
    max(up, key=up.get) == "편의점",                                  # ①
    y25["생활용품"] / s25 > .20 and y26["생활용품"] / s26 > .20,      # ②
    y26["편의점"] / s26 > y25["편의점"] / s25,                        # ③
    (s26 - y26["기타"]) > 4000,                                       # ④
    up["식음료"] / y25["식음료"] < up["편의점"] / y25["편의점"],       # ⑤
], "구성비·증가액·증가율")

# ── 06 거리·속력·시간 ─────────────────────────────────────────────
run = 12 / 36 * 60 + 9 / 27 * 60          # 분
stop = 6 * 30 / 60
arrive = 9 * 60 + run + stop              # 09:00 기준 분
mm = f"{int(arrive // 60):02d}시 {int(arrive % 60):02d}분"
check(6, Q[6]["choices"].index(mm) + 1 if mm in Q[6]["choices"] else 0, mm)

# ── 07 요금 → 최대 거리 ───────────────────────────────────────────
def fare(km: float) -> int:
    if km <= 10:
        return 1400
    import math
    return 1400 + 100 * math.ceil((km - 10) / 5)

far = max(k for k in range(11, 41) if fare(k) == 1700)
lab = f"{far}km"
check(7, Q[7]["choices"].index(lab) + 1 if lab in Q[7]["choices"] else 0, lab)

# ── 08 두 배차가 겹치는 횟수 ──────────────────────────────────────
from math import gcd
step = 8 * 12 // gcd(8, 12)
times = [t for t in range(step, 120 + 1, step)]      # 06:00 「보다 뒤」 ~ 08:00 「까지」
lab = f"{len(times)}번"
check(8, Q[8]["choices"].index(lab) + 1 if lab in Q[8]["choices"] else 0,
      f"{step}분마다 · {len(times)}번")

# ── 09 배치 (완전탐색) ────────────────────────────────────────────
def place_ok(a: dict) -> bool:
    return (a["C"] == "종착" and a["D"] == "신설"
            and a["A"] != a["B"] and a["E"] != a["A"]
            and sum(v == "신설" for v in a.values()) == 2
            and sum(v == "환승" for v in a.values()) == 2
            and sum(v == "종착" for v in a.values()) == 1)


who = "ABCDE"
sols = []
for combo in permutations("신설신설환승환승종착"[:0] or ["신설", "신설", "환승", "환승", "종착"]):
    a = dict(zip(who, combo))
    if place_ok(a) and a not in sols:
        sols.append(a)
if len(sols) != 1:
    bad.append(f"09  조건을 만족하는 배치가 {len(sols)}가지다 — 하나여야 한다")
else:
    s = sols[0]
    txt = ("신설역 " + "·".join(sorted(k for k in who if s[k] == "신설"))
           + " / 환승역 " + "·".join(sorted(k for k in who if s[k] == "환승"))
           + " / 종착역 " + "".join(k for k in who if s[k] == "종착"))
    check(9, Q[9]["choices"].index(txt) + 1 if txt in Q[9]["choices"] else 0, txt)

# ── 10 순서 (완전탐색) ────────────────────────────────────────────
orders = []
for p in permutations("가나다라마"):
    i = {c: k for k, c in enumerate(p)}
    if (i["나"] < i["가"] and i["다"] == 4
            and i["라"] == i["나"] - 1
            and i["가"] < i["마"] < i["다"]):
        orders.append(p)
if len(orders) != 1:
    bad.append(f"10  가능한 순서가 {len(orders)}가지다 — 하나여야 한다")
else:
    third = orders[0][2]
    check(10, Q[10]["choices"].index(third) + 1 if third in Q[10]["choices"] else 0,
          "".join(orders[0]))

# ── 11 정기권 <보기> ──────────────────────────────────────────────
PASS, TRIP, CAP = 55000, 1400, 44
g11 = {"ㄱ": PASS / CAP < TRIP, "ㄴ": PASS / 30 > TRIP, "ㄷ": False, "ㄹ": False}
true11 = ", ".join(k for k, v in g11.items() if v)
check(11, Q[11]["choices"].index(true11) + 1 if true11 in Q[11]["choices"] else 0, true11)

# ── 12 날짜 ───────────────────────────────────────────────────────
HOLI = {date(2026, 3, 1), date(2026, 5, 5), date(2026, 5, 25)}
d = date(2026, 3, 2)
for _ in range(3):
    d = date.fromordinal(d.toordinal() + 28)
while d in HOLI:
    d = date.fromordinal(d.toordinal() + 1)
lab = f"{d.month}월 {d.day}일"
check(12, Q[12]["choices"].index(lab) + 1 if lab in Q[12]["choices"] else 0, lab)

# ── 21 직접비 ─────────────────────────────────────────────────────
DIRECT = {"보수 장비 임차료": 3200, "현장 출장 여비": 480, "투입 인력 인건비": 5400}
INDIRECT = {"사업장 화재보험료": 620, "사무용품 구입비": 150, "업무용 통신비": 240}
lab = f"{sum(DIRECT.values()):,}천 원"
check(21, Q[21]["choices"].index(lab) + 1 if lab in Q[21]["choices"] else 0, lab)

# ── 22 인력 배치 ──────────────────────────────────────────────────
STAFF = {                       # 야간 · 교육 · 근속 · 자격증
    "A": (False, True, 5, True), "B": (True, True, 3, False),
    "C": (True, False, 4, True), "D": (True, True, 2, True),
    "E": (True, True, 6, True),  "F": (True, True, 1, False),
}
pool = [k for k, (n, e, y, _c) in STAFF.items() if n and e and y >= 2]
picks = [c for c in combinations(pool, 3) if sum(STAFF[k][3] for k in c) >= 2]
if len(picks) != 1:
    bad.append(f"22  조건을 만족하는 조합이 {len(picks)}가지다 — {picks}")
else:
    lab = ", ".join(picks[0])
    check(22, Q[22]["choices"].index(lab) + 1 if lab in Q[22]["choices"] else 0, lab)

# ── 23 비용 비교 ──────────────────────────────────────────────────
N, DAYS = 40, 3
cost = {
    "가": N * DAYS * 12000,
    "나": N * DAYS * 14000 * 0.85 if N >= 30 else N * DAYS * 14000,
    "다": 500000 * DAYS,
    "라": N * DAYS * 13000 * 0.9 if DAYS >= 3 else N * DAYS * 13000,
    "마": N * DAYS * 11000 + 120000,
}
best = min(cost, key=cost.get)
check(23, Q[23]["choices"].index(best) + 1 if best in Q[23]["choices"] else 0,
      f"{best} {cost[best]:,.0f}원")

# ── 24 시간대별 인원 ──────────────────────────────────────────────
TASKS = [("승강장", 9 * 60, 10 * 60 + 30, 3), ("환기", 10 * 60, 12 * 60, 2),
         ("안전문", 13 * 60, 15 * 60, 4), ("조명", 14 * 60 + 30, 16 * 60, 2)]
need = lambda t: sum(n for _n2, s, e, n in TASKS if s <= t < e)
peak = max(need(t) for t in range(9 * 60, 16 * 60))
morning = [t for t in range(9 * 60, 12 * 60) if need(t) == 5]
afternoon = [t for t in range(13 * 60, 16 * 60) if need(t) == 6]
g24 = {
    "ㄱ": len(morning) > 0,
    "ㄴ": need(10 * 60 + 15) == peak,
    "ㄷ": len(afternoon) == 30,
    "ㄹ": peak <= 5,
}
true24 = ", ".join(k for k, v in g24.items() if v)
check(24, Q[24]["choices"].index(true24) + 1 if true24 in Q[24]["choices"] else 0,
      f"최대 {peak}명 · {true24}")

# ── 25 순서도 ─────────────────────────────────────────────────────
total = sum(n for n in range(1, 11) if n % 3)
lab = str(total)
check(25, Q[25]["choices"].index(lab) + 1 if lab in Q[25]["choices"] else 0, lab)

# ── 26 배열 첨자 ──────────────────────────────────────────────────
K = [40, 15, 27, 8, 33]                 # 자리 1..5
A, B = K[3 - 1], K[5 - 1]
C = K.index(max(K)) + 1                 # 자리 번호 (1부터)
lab = str(A + B - C)
check(26, Q[26]["choices"].index(lab) + 1 if lab in Q[26]["choices"] else 0, lab)

# ── 32 매뉴얼 — 같은 코드가 몇 번 떴나 ────────────────────────────
hits = 1 + 2                            # 처음 + 두 역
step32 = "운행 중지 후 정비고 입고" if hits >= 3 else "수동 개폐 후 계속 운행"
want32 = [i for i, c in enumerate(Q[32]["choices"], 1) if "정비고" in c]
check(32, want32[0] if step32.startswith("운행 중지") and want32 else 0,
      f"{hits}회 → {step32}")

# ── 36 결재 — 전결권자의 한 단계 아래 ─────────────────────────────
LADDER = ["팀장", "부장", "처장", "본부장"]
LIMIT = [(1000, "팀장"), (3000, "부장"), (5000, "처장"), (10**9, "본부장")]
amount = 4800
holder = next(who for cap, who in LIMIT if amount <= cap)
signer = LADDER[LADDER.index(holder) - 1]           # 긴급 → 한 단계 아래
want36 = [i for i, c in enumerate(Q[36]["choices"], 1)
          if c.startswith(signer) and "사후 보고" in c]
check(36, want36[0] if want36 else 0, f"{holder} 전결 → {signer} 선결재")


# ── 보고 ──────────────────────────────────────────────────────────
print(f"   제6회 계산 검증 — 확인 {len(ok)}건 · 어긋남 {len(bad)}건")
for line in ok:
    print("     ", line)
if bad:
    print()
    for line in bad:
        print("   [어긋남]", line)
raise SystemExit(1 if bad else 0)
