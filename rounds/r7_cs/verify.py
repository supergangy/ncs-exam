# -*- coding: utf-8 -*-
"""전산 제1회 문항의 답을 **다시 구해** 문항과 대조한다.

    python rounds/r7_cs/verify.py

규율은 `rounds/r6_seoulmetro/verify.py` 와 같다.

* **선지 번호를 계산 함수 안에 적지 않는다.** 계산은 값을 내고, 그 값을 선지
  번호로 옮기는 일은 따로 한다. 그래야 `tools/reorder_choices.py` 로 선지를
  섞어도 검증이 따라온다.

## 이 파일이 다른 회차보다 무거운 이유

NCS 지문형은 지문이 정답 근거를 통제한다. 지문만 맞으면 정답이 확정된다.
**전산 전공은 그렇지 않다.** 정답이 지문 밖 사실로 정해지므로 틀리면 막을
수단이 계산밖에 없다. 은행 300건이 그 규율로 불일치 0 을 지켰다
(`tools/verify_cs.py`).

그래서 40문항 가운데 **34문항**을 여기서 다시 구한다. SQL 은 sqlite 로 돌리고,
정규형은 폐포로 후보키를 구해 판정하고, 스케줄러·클럭·은행원 알고리즘·스위치는
실제로 굴리고, 서브네팅과 단편화는 셈을 다시 한다.

검증기를 두지 않은 여섯은 **계산으로 확정되지 않는 것**이다 —

    20 캡슐화 · 21 DHCP 포트 · 27 UML · 34 자바 생성자 순서   (표준 4)
    38 전자봉투 · 40 웹취약점 대책                            (개념 2)

표준 넷은 RFC·JLS·UML 명세에 값이 고정돼 있어 사람이 문서로 확인했다.
개념 둘은 과목당 하나를 넘기지 않는다는 규칙(README 4절)에 든다.
"""
from __future__ import annotations

import hashlib
import heapq
import importlib
import importlib.util
import itertools
import math
import pathlib
import sqlite3
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CIRC = "①②③④⑤"
ok: list[str] = []
bad: list[str] = []


def load(mod: str):
    p = HERE / "content" / f"{mod}.py"
    spec = importlib.util.spec_from_file_location(mod, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def index() -> dict[int, dict]:
    """문항 번호 → 문항. **작성 순서**로 매긴다 (r6 와 같다)."""
    cfg = importlib.import_module(f"rounds.{HERE.name}.config")
    out, no = {}, 0
    for mod, _area, _n in cfg.AREAS:
        for b in load(mod).BLOCKS:
            for q in b["questions"]:
                no += 1
                out[no] = q
    return out


Q = index()


def check(no: int, label: str, why: str = "") -> None:
    """계산이 내놓은 **선지 문구**가 정답 선지와 같은 자리인가."""
    want = Q[no]["answer"]
    ch = Q[no]["choices"]
    got = ch.index(label) + 1 if label in ch else 0
    line = f"{no:02d}  기대 {CIRC[want-1]} · 계산 {CIRC[got-1] if got else '선지에 없다'}  「{label}」"
    (ok if got == want else bad).append(line + (f"  ({why})" if why else ""))


def check_claims(no: int, truth: list[bool], why: str = "") -> None:
    """선지 다섯의 참·거짓을 통째로 본다 — **참이 정확히 하나**여야 한다."""
    want = Q[no]["answer"]
    trues = [i + 1 for i, t in enumerate(truth) if t]
    if len(trues) != 1:
        bad.append(f"{no:02d}  참인 선지가 {len(trues)}개다 — {trues} ({why})")
    elif trues[0] != want:
        bad.append(f"{no:02d}  기대 {CIRC[want-1]} · 참인 것은 {CIRC[trues[0]-1]} ({why})")
    else:
        ok.append(f"{no:02d}  선지 다섯의 참·거짓이 모두 맞는다 ({why})")


# ── 함수 종속 도구 (verify_cs.py 와 같은 것) ─────────────────────────

def closure(fds: list[tuple[set, set]], seed) -> set[str]:
    X = set(seed)
    changed = True
    while changed:
        changed = False
        for left, right in fds:
            if left <= X and not right <= X:
                X |= right
                changed = True
    return X


def candidate_keys(attrs: set[str], fds: list[tuple[set, set]]) -> list[set]:
    keys: list[set] = []
    for n in range(1, len(attrs) + 1):
        for combo in itertools.combinations(sorted(attrs), n):
            c = set(combo)
            if any(k < c for k in keys):
                continue                       # 이미 더 작은 키를 품었다
            if closure(fds, c) == attrs:
                keys.append(c)
    return keys


def key_label(keys: list[set]) -> str:
    names = ["".join(sorted(k)) for k in keys]
    return ", ".join(sorted(names, key=lambda s: (len(s), s)))


# ══ 전자계산기구조 ═══════════════════════════════════════════════════

# ── 01 2단계 캐시 ─────────────────────────────────────────────────
amat = 1 + 0.10 * (8 + 0.20 * 60)
check(1, f"{amat:.2f}ns", "L1 1ns + 미스 10% × (L2 8ns + 미스 20% × 60ns)")

# ── 02 8비트 2의 보수 뺄셈 ────────────────────────────────────────
x, y = -96, -45                                # -96 - 45 = -96 + (-45)
ux, uy = x % 256, y % 256
low = (ux + uy) % 256
over = (ux >> 7) == (uy >> 7) != (low >> 7)    # 부호가 같은 둘을 더해 부호가 바뀌면 넘친 것
bits = format(low, "08b")
check(2, f"{bits[:4]} {bits[4:]} · 오버플로 {'발생' if over else '없음'}",
      f"{ux} + {uy} = {ux + uy}, 하위 8비트 {low}")


# ══ 운영체제 ════════════════════════════════════════════════════════

# ── 03 HRN ────────────────────────────────────────────────────────
JOBS = {"A": (10, 5), "B": (15, 10), "C": (9, 3), "D": (20, 20)}
ratio = {k: (w + s) / s for k, (w, s) in JOBS.items()}
pick3 = max(ratio, key=ratio.get)
check(3, f"{pick3} · {ratio[pick3]:.2f}",
      " · ".join(f"{k} {v:.2f}" for k, v in ratio.items()))

# ── 04 클럭(2차 기회) ─────────────────────────────────────────────
FRAMES = ["P1", "P2", "P3", "P4"]
refbit = [1, 1, 0, 1]
ptr, spun = 0, 0
while refbit[ptr] and spun < 2 * len(FRAMES):
    refbit[ptr] = 0
    ptr = (ptr + 1) % len(FRAMES)
    spun += 1
check(4, f"{FRAMES[ptr]} · 프레임 {(ptr + 1) % len(FRAMES)}",
      f"{spun}칸 지나 프레임 {ptr} 에서 멈춘다")

# ── 05 은행원 알고리즘 — 선지 다섯을 모두 굴린다 ──────────────────
TOTAL = (9, 6, 8)
ALLOC = {"P1": (1, 1, 2), "P2": (2, 1, 2), "P3": (3, 2, 1), "P4": (1, 1, 2)}
NEED_MAX = {"P1": (4, 3, 3), "P2": (3, 2, 2), "P3": (7, 4, 5), "P4": (2, 2, 4)}
AVAIL = tuple(TOTAL[i] - sum(a[i] for a in ALLOC.values()) for i in range(3))
assert AVAIL == (2, 1, 1), f"가용 자원이 어긋난다 — {AVAIL}"


def is_safe(seq: list[str]) -> bool:
    work = list(AVAIL)
    for p in seq:
        need = [NEED_MAX[p][i] - ALLOC[p][i] for i in range(3)]
        if any(need[i] > work[i] for i in range(3)):
            return False
        for i in range(3):
            work[i] += ALLOC[p][i]
    return True


check_claims(5, [is_safe([t.strip() for t in c.split("→")])
                 for c in Q[5]["choices"]], f"가용 {AVAIL} 에서 출발")

# ── 06 계수 세마포어 ──────────────────────────────────────────────
sem, waiting = 3, 0
for op in "PPPPPVVP":
    if op == "P":
        sem -= 1
        if sem < 0:
            waiting += 1
    else:
        sem += 1
        if sem <= 0:
            waiting -= 1
check(6, f"{'−' if sem < 0 else ''}{abs(sem)} · {waiting}개", "P 6회 · V 2회")


# ══ 데이터베이스론 ══════════════════════════════════════════════════

# ── 07 BCNF ───────────────────────────────────────────────────────
A7 = set("ABCD")
F7 = [(set("AB"), set("C")), (set("C"), set("D")), (set("D"), set("B"))]
keys7 = candidate_keys(A7, F7)
prime7 = set().union(*keys7)
viol7 = [(l, r) for l, r in F7 if closure(F7, l) != A7]          # 왼쪽이 슈퍼키가 아니다
bad3nf = [(l, r) for l, r in viol7 if not r <= prime7]           # 3NF 까지 깨는 것
nf7 = "BCNF" if not viol7 else ("제3정규형" if not bad3nf else "제2정규형")
label7 = f"{nf7} · " + ", ".join(f"{''.join(sorted(l))} → {''.join(sorted(r))}"
                                 for l, r in viol7)
check(7, label7, f"후보키 {key_label(keys7)} · 기본속성 {''.join(sorted(prime7))}")

# ── 08·09·14 SQL — sqlite 로 실제로 돌린다 ────────────────────────
db = sqlite3.connect(":memory:")
db.executescript("""
CREATE TABLE dept(code TEXT, name TEXT);
INSERT INTO dept VALUES ('D1','영업'),('D2','개발'),('D3','총무'),('D4','인사');
CREATE TABLE emp(no INT, name TEXT, code TEXT, pay INT);
INSERT INTO emp VALUES (1,'김대리','D1',300),(2,'이주임','D1',250),
                       (3,'박과장','D2',400),(4,'최사원','D2',350);

CREATE TABLE staff(no INT, name TEXT, team TEXT, bonus INT);
INSERT INTO staff VALUES (1,'김대리','영업',100),(2,'이주임','영업',NULL),
                         (3,'박과장','개발',200),(4,'최사원','개발',300),
                         (5,'정주임','개발',NULL),(6,'한사원','총무',NULL);

CREATE TABLE crew(no INT, name TEXT, boss INT);
INSERT INTO crew VALUES (1,'김부장',NULL),(2,'이대리',1),(3,'박과장',1),(4,'최사원',2);
""")


def rows(sql: str) -> int:
    return len(db.execute(sql).fetchall())


on8 = rows("SELECT * FROM dept LEFT JOIN emp"
           " ON dept.code = emp.code AND emp.pay >= 300")
where8 = rows("SELECT * FROM dept LEFT JOIN emp"
              " ON dept.code = emp.code WHERE emp.pay >= 300")
check(8, f"㉠ {on8}행 · ㉡ {where8}행", "조건을 ON 에 둘 때와 WHERE 에 둘 때")

cnt, cntcol, avg = db.execute(
    "SELECT COUNT(*), COUNT(bonus), AVG(bonus) FROM staff").fetchone()
check(9, f"{cnt} · {cntcol} · {avg:g}", f"SUM 은 {db.execute('SELECT SUM(bonus) FROM staff').fetchone()[0]}")

notin = rows("SELECT name FROM crew WHERE no NOT IN (SELECT boss FROM crew)")
notex = rows("SELECT name FROM crew e"
             " WHERE NOT EXISTS (SELECT 1 FROM crew m WHERE m.boss = e.no)")
check(14, f"㉠ {notin}행 · ㉡ {notex}행", "부질의에 NULL 이 섞였을 때")

# ── 10 후보키를 모두 ──────────────────────────────────────────────
A10 = set("ABCDE")
F10 = [(set("A"), set("BC")), (set("CD"), set("E")),
       (set("B"), set("D")), (set("E"), set("A"))]
check(10, key_label(candidate_keys(A10, F10)), "폐포로 구한 후보키")

# ── 11 충돌 직렬가능성 ────────────────────────────────────────────
SCHED = [("T1", "r", "A"), ("T2", "r", "A"), ("T1", "w", "B"),
         ("T3", "r", "B"), ("T2", "w", "A"), ("T3", "w", "A")]
edges: set[tuple[str, str]] = set()
for i, (t1, o1, x1) in enumerate(SCHED):
    for t2, o2, x2 in SCHED[i + 1:]:
        if t1 != t2 and x1 == x2 and "w" in (o1, o2):
            edges.add((t1, t2))
TXS = sorted({t for t, _, _ in SCHED})
orders = [list(p) for p in itertools.permutations(TXS)
          if all(p.index(a) < p.index(b) for a, b in edges)]
if not orders:
    label11 = "충돌 직렬가능하지 않다"
elif len(orders) > 1:
    label11 = "충돌 직렬가능하며, 동치 직렬 순서가 둘 이상이다"
else:
    label11 = f"충돌 직렬가능하며, 동치 직렬 순서는 {' → '.join(orders[0])} 이다"
check(11, label11, f"선행 그래프 {sorted(edges)}")

# ── 12 B+트리 ─────────────────────────────────────────────────────
RECS, FAN, FILL = 350_000, 100, 0.7
per = int(FAN * FILL)
leaves = math.ceil(RECS / per)
level, nodes = 1, leaves
while nodes > 1:
    nodes = math.ceil(nodes / per)
    level += 1
check(12, f"{leaves:,}개 · 높이 {level}", f"노드당 {per}개")

# ── 13 관계대수는 집합, SQL 은 다중집합 ───────────────────────────
R13 = [(1, "x"), (1, "y"), (2, "x"), (3, "z")]
S13 = [("x", "p"), ("x", "q"), ("y", "p"), ("w", "r")]
joined = [(a, b, c) for a, b in R13 for b2, c in S13 if b == b2]
check(13, f"㉠ {len({t[0] for t in joined})}행 · ㉡ {len(joined)}행",
      f"자연조인 {len(joined)}행")


# ══ 데이터통신 ══════════════════════════════════════════════════════

# ── 15 비트 스터핑 ────────────────────────────────────────────────
DATA = "0111" "1111" "0111" "1110" "0111" "11"
assert len(DATA) == 22, f"데이터 길이가 어긋난다 — {len(DATA)}"
sent, run, stuffed = [], 0, 0
for bit in DATA:
    sent.append(bit)
    if bit == "1":
        run += 1
        if run == 5:
            sent.append("0")
            stuffed += 1
            run = 0
    else:
        run = 0
check(15, f"{stuffed}개 삽입 · {len(sent)}비트 전송", f"원본 {len(DATA)}비트")

# ── 16 나이퀴스트 + 64-QAM ────────────────────────────────────────
baud = 2 * 3000
bits_per_symbol = int(math.log2(64))
check(16, f"{baud * bits_per_symbol:,}bps",
      f"보율 {baud} × 심볼당 {bits_per_symbol}비트")


# ══ 네트워크 ════════════════════════════════════════════════════════

# ── 17 VLSM ───────────────────────────────────────────────────────
TEAMS = [("영업팀", 100), ("개발팀", 50), ("총무팀", 25), ("인사팀", 10)]
base, plan = 0, {}
for team, hosts in TEAMS:                       # 이미 큰 순으로 놓았다
    size = 2
    while size - 2 < hosts:
        size *= 2
    plan[team] = (base, 32 - (size.bit_length() - 1))
    base += size
start, pref = plan["인사팀"]
check(17, f"192.168.100.{start}/{pref} · {256 - base}개",
      " · ".join(f"{t} .{s}/{p}" for t, (s, p) in plan.items()))

# ── 18 송신 가능 바이트 ───────────────────────────────────────────
check(18, f"{min(12000, 8000) - 5000:,}바이트", "min(cwnd, rwnd) − 미확인")

# ── 19 다익스트라 ─────────────────────────────────────────────────
LINKS = {("A", "B"): 2, ("A", "C"): 5, ("B", "C"): 1, ("B", "D"): 7,
         ("C", "D"): 3, ("C", "E"): 8, ("D", "E"): 2, ("D", "F"): 6,
         ("E", "F"): 1}


def shortest(links: dict, src: str, dst: str) -> int:
    adj: dict[str, list[tuple[str, int]]] = {}
    for (u, v), w in links.items():
        adj.setdefault(u, []).append((v, w))
        adj.setdefault(v, []).append((u, w))
    dist = {src: 0}
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, math.inf):
            continue
        for v, w in adj.get(u, []):
            if d + w < dist.get(v, math.inf):
                dist[v] = d + w
                heapq.heappush(pq, (d + w, v))
    return dist.get(dst, -1)


cut = {k: v for k, v in LINKS.items() if k != ("D", "E")}
check(19, f"{shortest(LINKS, 'A', 'F')} · {shortest(cut, 'A', 'F')}",
      "정상 · D–E 끊긴 뒤")

# ── 22 스위치 MAC 학습 ────────────────────────────────────────────
PORT = {"A": 1, "B": 2, "C": 3, "D": 4}
mac: dict[str, int] = {}
flood = 0
for src, dst in [("A", "B"), ("B", "A"), ("C", "A"), ("D", "C")]:
    mac[src] = PORT[src]                        # 보내는 쪽을 배운다
    if dst not in mac:                          # 받는 쪽을 모르면 뿌린다
        flood += 1
check(22, f"{flood}개 · {len(mac)}개", "프레임 넷을 차례로")

# ── 23 슬라이딩 윈도 이용률 ───────────────────────────────────────
tf = 10_000 / 10_000_000 * 1000                 # ms
cycle = tf + 2 * 10
check(23, f"{min(1.0, 4 * tf / cycle) * 100:.1f}%",
      f"전송 {tf:g}ms · 한 바퀴 {cycle:g}ms")

# ── 24 IPv4 단편화 ────────────────────────────────────────────────
TOTAL_LEN, HDR, MTU = 4000, 20, 1500
payload = TOTAL_LEN - HDR
per_frag = (MTU - HDR) // 8 * 8                 # 데이터는 8의 배수
offs, done = [], 0
while done < payload:
    offs.append(done // 8)
    done += min(per_frag, payload - done)
check(24, f"{len(offs)}개 · {offs[-1]:,}", f"조각당 {per_frag}바이트")


# ══ 소프트웨어공학 ══════════════════════════════════════════════════

# ── 25 문장·분기 커버리지 ─────────────────────────────────────────
CASES = [(True, True), (True, False), (False, True), (False, False)]


def touched_stmts(a: bool, b: bool) -> set:
    s = {"x=0", "print"}
    if a:
        s.add("x=1")
    if b:
        s.add("x=x+1")
    return s


def touched_branches(a: bool, b: bool) -> set:
    return {("if1", a), ("if2", b)}


def fewest(cover, universe) -> int:
    for k in range(1, len(CASES) + 1):
        for combo in itertools.combinations(CASES, k):
            if set().union(*(cover(*c) for c in combo)) == universe:
                return k
    return 0


all_s = set().union(*(touched_stmts(*c) for c in CASES))
all_b = set().union(*(touched_branches(*c) for c in CASES))
check(25, f"문장 {fewest(touched_stmts, all_s)}개 · 분기 {fewest(touched_branches, all_b)}개",
      f"문장 {len(all_s)}개 · 분기 {len(all_b)}갈래를 덮는 최소 케이스")

# ── 26 PERT ───────────────────────────────────────────────────────
TASK = {"A": (2, 4, 12), "B": (3, 6, 9), "C": (1, 4, 7), "D": (4, 7, 16)}
PRE = {"A": [], "B": [], "C": ["A", "B"], "D": ["C"]}
te = {k: (o + 4 * m + p) / 6 for k, (o, m, p) in TASK.items()}
finish: dict[str, float] = {}


def ends(k: str) -> float:
    if k not in finish:
        finish[k] = max((ends(x) for x in PRE[k]), default=0) + te[k]
    return finish[k]


check(26, f"{max(ends(k) for k in TASK):g}일",
      " · ".join(f"{k} {v:g}" for k, v in te.items()))

# ── 28 스텁·드라이버 ──────────────────────────────────────────────
TREE = {"M1": ["M2", "M3", "M4"], "M2": ["M5", "M6"], "M3": [],
        "M4": ["M7"], "M5": [], "M6": [], "M7": []}
stubs = len(TREE) - 1                           # 최상위를 뺀 모든 모듈
drivers = sum(1 for kids in TREE.values() if kids)   # 잎이 아닌 모듈
check(28, f"스텁 {stubs}개 · 드라이버 {drivers}개", f"모듈 {len(TREE)}개")


# ══ 프로그래밍언어 ══════════════════════════════════════════════════

# ── 29 포인터 산술 ────────────────────────────────────────────────
arr = [10, 20, 30, 40, 50]
at = 0 + 2                                      # p = a; p = p + 2
check(29, f"{arr[at]} {arr[at - 1] + arr[at + 1]}", "*p · *(p−1) + p[1]")

# ── 30 2차원 배열 ─────────────────────────────────────────────────
grid = [[i * 4 + j for j in range(4)] for i in range(3)]
check(30, str(sum(grid[i][3 - i] for i in range(3))), "부대각선의 합")

# ── 31 재귀 반환값 ────────────────────────────────────────────────
memo: dict[int, int] = {}


def rec(n: int) -> int:
    if n <= 1:
        return 1
    if n not in memo:
        memo[n] = rec(n - 1) + rec(n - 2) + 1
    return memo[n]


check(31, str(rec(6)), " · ".join(f"f({n})={rec(n)}" for n in range(7)))

# ── 32 후위 표기식 ────────────────────────────────────────────────
OPS = {"+": lambda a, b: a + b, "-": lambda a, b: a - b,
       "*": lambda a, b: a * b, "/": lambda a, b: a // b}
stack: list[int] = []
deepest = 0
for tok in "9 3 / 2 5 * + 4 -".split():
    if tok in OPS:
        rhs, lhs = stack.pop(), stack.pop()
        stack.append(OPS[tok](lhs, rhs))
    else:
        stack.append(int(tok))
    deepest = max(deepest, len(stack))
check(32, f"{stack[0]} · {deepest}개", "스택을 실제로 굴렸다")

# ── 33 선택 정렬 ──────────────────────────────────────────────────
N33 = 8
check(33, f"비교 {N33 * (N33 - 1) // 2}회 · 교환 {N33 - 1}회", "훑기 7번")

# ── 35 8비트 오버플로 ─────────────────────────────────────────────
uc = (200 + 100) % 256
sc = (100 + 100) % 256
if sc >= 128:
    sc -= 256
check(35, f"{uc} {'−' if sc < 0 else ''}{abs(sc)}", "unsigned · signed")


# ══ 정보보안 ════════════════════════════════════════════════════════

# ── 36 디피-헬만 ──────────────────────────────────────────────────
P36, G36, a36, b36 = 23, 5, 6, 15
pubA, pubB = pow(G36, a36, P36), pow(G36, b36, P36)
assert (pubA, pubB) == (8, 19), f"공개값이 어긋난다 — {pubA}, {pubB}"
k1, k2 = pow(pubB, a36, P36), pow(pubA, b36, P36)
assert k1 == k2, "두 사람의 값이 다르다"
check(36, str(k1), f"A={pubA} · B={pubB}")

# ── 37 CBC 오류 전파 — 실제로 복호해 어긋난 블록을 센다 ───────────
IV = 0x1122334455667788
CIPHER = [0x1111111111111111, 0x2222222222222222, 0x3333333333333333,
          0x4444444444444444, 0x5555555555555555]


def block_decrypt(c: int) -> int:
    """블록 암호를 흉내 낸다. **한 비트만 달라도 결과가 통째로 달라지면** 된다."""
    return int.from_bytes(hashlib.sha256(c.to_bytes(8, "big")).digest()[:8], "big")


def cbc_decrypt(cs: list[int]) -> list[int]:
    prev, out = IV, []
    for c in cs:
        out.append(block_decrypt(c) ^ prev)
        prev = c
    return out


clean = cbc_decrypt(CIPHER)
flipped = list(CIPHER)
flipped[2] ^= 1                                 # C3 의 한 비트를 뒤집는다
broken = cbc_decrypt(flipped)
check(37, ", ".join(f"P{i+1}" for i in range(len(CIPHER)) if clean[i] != broken[i]),
      "C3 한 비트를 뒤집고 다시 복호했다")

# ── 39 RBAC ───────────────────────────────────────────────────────
ROLE = {"조회자": {"읽기"},
        "편집자": {"읽기", "쓰기"},
        "관리자": {"읽기", "쓰기", "삭제", "권한부여"}}
ACTIVE = [("김대리", "조회자"), ("이주임", "편집자"),
          ("박과장", "관리자"), ("최사원", "조회자")]
check(39, ", ".join(u for u, r in ACTIVE if "쓰기" in ROLE[r]),
      "맡은 역할이 아니라 **켠 역할**로 판정")


# ── 보고 ──────────────────────────────────────────────────────────
UNVERIFIED = {20: "캡슐화 (표준)", 21: "DHCP 포트 (표준 · RFC 2131)",
              27: "UML 다이어그램 (표준 · UML 2.x)", 34: "자바 생성자 순서 (표준 · JLS)",
              38: "전자봉투 (개념)", 40: "웹취약점 대책 (개념)"}
seen = {int(line[:2]) for line in ok + bad}
missing = sorted(set(Q) - seen - set(UNVERIFIED))

print(f"   전산 제1회 계산 검증 — 확인 {len(ok)}건 · 어긋남 {len(bad)}건"
      f" · 검증기 없음 {len(UNVERIFIED)}건 / 전체 {len(Q)}문항")
for line in ok:
    print("     ", line)
print("\n   [검증기 없음] 계산으로 확정되지 않는 문항")
for no, why in sorted(UNVERIFIED.items()):
    print(f"      {no:02d}  {why}")
if missing:
    print("\n   [빠짐] 검증기도 없고 면제 목록에도 없다 —", missing)
if bad:
    print()
    for line in bad:
        print("   [어긋남]", line)
raise SystemExit(1 if bad or missing else 0)
