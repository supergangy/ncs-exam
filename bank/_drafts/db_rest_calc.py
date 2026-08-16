# -*- coding: utf-8 -*-
"""데이터베이스론 +20 가운데 **아직 안 쓴 14문항의 검산.**

021~026(SQL 6문항)은 이미 `major_cs_database.py` 에 들어갔다. 남은 것은
정규화 3 · 인덱스 3 · 트랜잭션 3 · 관계대수 2 · 회복 2 · 질의최적화 1 이다.

**검산은 끝났고 값은 아래 출력 그대로다.** 다음에 이어 쓸 때 다시 재지 않는다 —
집필과 `tools/verify_cs.py` 등록만 하면 된다.

```bash
python bank/_drafts/db_rest_calc.py
```

| 번호 | 문항 | 정답 | 오답 경로 |
|---|---|---|---|
| 27 | BCNF 판정 | 3NF ○ · BCNF ✗ (위반 강사→과목 1건) | 후보키 강학·과학 |
| 29 | 무손실+종속성보존 | AB/BCD · ABC/CD | AB/ACD 종속성 깨짐 · AD/BCD 손실 |
| 30 | B+트리 분할 | 3회 · 높이 2 | |
| 33 | 교착 탐지 | T1→T2→T3→T1 | T4·T5 는 사이클 밖 |
| 34 | 타임스탬프 규약 | T1·T2 롤백 | T3 만 생존 |
| 37 | 세미/안티조인 | 세미 2 | 안티 3 · 내부 4 |
| 38 | REDO/UNDO | REDO {T3} · UNDO {T2,T4} | T1 은 체크포인트 앞 커밋 |

아직 검산하지 않은 것 — 28(4NF 다치종속) · 31(해시 vs B+트리) · 32(커버링 인덱스) ·
35(write skew) · 36(관계대수↔SQL 동치) · 39(WAL 위반) · 40(조인 순서, `db_sql.py` 에 일부).
"""
import itertools
import sqlite3

BAR = "=" * 66


# ────────────────────────────────── 함수 종속 도구
def closure(attrs, fds):
    """attrs 의 폐포. fds 는 [(왼쪽집합, 오른쪽집합)]."""
    cur = set(attrs)
    changed = True
    while changed:
        changed = False
        for lhs, rhs in fds:
            if lhs <= cur and not rhs <= cur:
                cur |= rhs
                changed = True
    return cur


def candidate_keys(R, fds):
    keys = []
    for r in range(1, len(R) + 1):
        for c in itertools.combinations(sorted(R), r):
            s = set(c)
            if closure(s, fds) == R and not any(k < s for k in keys):
                keys.append(s)
    return keys


def prime_attrs(R, fds):
    return set().union(*candidate_keys(R, fds)) if R else set()


def bcnf_violations(R, fds):
    """BCNF 위반 = 왼쪽이 초키가 아닌 비자명 종속."""
    bad = []
    for lhs, rhs in fds:
        if rhs <= lhs:
            continue                       # 자명
        if closure(lhs, fds) != R:
            bad.append((lhs, rhs))
    return bad


def third_nf_ok(R, fds):
    pa = prime_attrs(R, fds)
    for lhs, rhs in fds:
        if rhs <= lhs or closure(lhs, fds) == R:
            continue
        if not (rhs - lhs) <= pa:
            return False
    return True


print(BAR)
print("27  BCNF 판정 — 3NF 이지만 BCNF 가 아닌 고전 사례")
# 수강(학생, 과목, 강사): (학생,과목)→강사, 강사→과목
R = set("학과강")  # 학=학생 과=과목 강=강사
FDS = [({"학", "과"}, {"강"}), ({"강"}, {"과"})]
ck = candidate_keys(R, FDS)
print(f"   후보키 {[''.join(sorted(k)) for k in ck]}")
print(f"   주요 속성 {sorted(prime_attrs(R, FDS))}")
print(f"   3NF 만족? {third_nf_ok(R, FDS)}")
v = bcnf_violations(R, FDS)
print(f"   BCNF 위반 {[(''.join(sorted(a)), ''.join(sorted(b))) for a, b in v]}")
print("   → 3NF 이나 BCNF 아님. 위반은 강사→과목 하나")

print("\n" + BAR)
print("29  무손실 분해 + 종속성 보존 동시 판정")
# R(A,B,C,D), A→B, B→C, C→D 를 여러 방식으로 쪼갠다
R2 = set("ABCD")
F2 = [({"A"}, {"B"}), ({"B"}, {"C"}), ({"C"}, {"D"})]


def lossless(R, fds, r1, r2):
    """두 조각으로 나눌 때 무손실 = 공통 속성이 어느 한쪽의 초키."""
    common = r1 & r2
    if not common:
        return False
    cl = closure(common, fds)
    return r1 <= cl or r2 <= cl


def preserved(fds, parts):
    """각 종속이 조각 하나 안에 담기나(단순 판정)."""
    lost = []
    for lhs, rhs in fds:
        if not any((lhs | rhs) <= p for p in parts):
            lost.append((lhs, rhs))
    return lost


for label, parts in [
    ("AB / BCD", [set("AB"), set("BCD")]),
    ("AB / ACD", [set("AB"), set("ACD")]),
    ("ABC / CD", [set("ABC"), set("CD")]),
    ("AD / BCD", [set("AD"), set("BCD")]),
]:
    ll = lossless(R2, F2, parts[0], parts[1])
    lost = preserved(F2, parts)
    tag = "무손실" if ll else "손실"
    keep = "보존" if not lost else f"깨짐{[(''.join(sorted(a)),''.join(sorted(b))) for a,b in lost]}"
    print(f"   {label:<10} {tag} · 종속성 {keep}")
print("   → 「무손실이면서 종속성도 보존」은 AB / BCD 와 ABC / CD 둘")

print("\n" + BAR)
print("30  B+트리 삽입과 분할 — 차수 4(키 최대 3개)")


class Node:
    def __init__(self, leaf=True):
        self.keys, self.kids, self.leaf = [], [], leaf


def insert(root, key, order, stat):
    """아주 단순한 B+트리. 분할 횟수만 정확히 세면 된다."""
    maxk = order - 1

    def ins(n, k):
        if n.leaf:
            n.keys.append(k); n.keys.sort()
        else:
            i = 0
            while i < len(n.keys) and k >= n.keys[i]:
                i += 1
            ins(n.kids[i], k)
            if len(n.kids[i].keys) > maxk:
                split(n, i)

    def split(parent, i):
        node = parent.kids[i]
        mid = len(node.keys) // 2
        up = node.keys[mid]
        right = Node(node.leaf)
        if node.leaf:
            right.keys = node.keys[mid:]
            node.keys = node.keys[:mid]
        else:
            right.keys = node.keys[mid + 1:]
            right.kids = node.kids[mid + 1:]
            node.keys = node.keys[:mid]
            node.kids = node.kids[:mid + 1]
        parent.keys.insert(i, up); parent.kids.insert(i + 1, right)
        stat["split"] += 1

    ins(root, key)
    if len(root.keys) > maxk:                 # 루트 분할
        new = Node(False); new.kids = [root]
        split(new, 0)
        stat["height"] += 1
        return new
    return root


stat = {"split": 0, "height": 1}
root = Node()
seq = [10, 20, 30, 40, 50, 60, 70, 80]
for k in seq:
    root = insert(root, k, 4, stat)
print(f"   차수 4 에 {seq} 를 차례로 넣으면")
print(f"   분할 {stat['split']}회 · 높이 {stat['height']}")

print("\n" + BAR)
print("33  대기 그래프로 교착 탐지")
WAIT = {"T1": ["T2"], "T2": ["T3"], "T3": ["T1", "T4"], "T4": [], "T5": ["T3"]}


def find_cycle(g):
    seen, stack = set(), []

    def dfs(u):
        seen.add(u); stack.append(u)
        for v in g.get(u, []):
            if v in stack:
                return stack[stack.index(v):] + [v]
            if v not in seen:
                r = dfs(v)
                if r:
                    return r
        stack.pop()
        return None

    for u in g:
        if u not in seen:
            r = dfs(u)
            if r:
                return r
    return None


cyc = find_cycle(WAIT)
print(f"   대기 관계 {WAIT}")
print(f"   사이클 {' → '.join(cyc) if cyc else '없음'}")
print("   → 교착에 걸린 것은 T1·T2·T3. T4·T5 는 사이클 밖")

print("\n" + BAR)
print("34  타임스탬프 순서 규약 — 되돌려지는 트랜잭션")
# (시각, 트랜잭션, 연산, 대상). TS 는 번호가 작을수록 먼저.
OPS = [("T1", "R", "A"), ("T2", "W", "A"), ("T1", "W", "A"),
       ("T2", "R", "B"), ("T3", "W", "B"), ("T2", "W", "B")]
TS = {"T1": 1, "T2": 2, "T3": 3}
rts, wts, aborted = {}, {}, []
for t, op, x in OPS:
    if t in aborted:
        continue
    if op == "R":
        if TS[t] < wts.get(x, 0):
            aborted.append(t); continue
        rts[x] = max(rts.get(x, 0), TS[t])
    else:
        if TS[t] < rts.get(x, 0) or TS[t] < wts.get(x, 0):
            aborted.append(t); continue
        wts[x] = TS[t]
print(f"   연산 {OPS}")
print(f"   되돌려진 트랜잭션 {aborted}")

print("\n" + BAR)
print("37  세미조인·안티조인")
S = """
CREATE TABLE 사원(사번 TEXT, 부서 TEXT);
CREATE TABLE 참여(사번 TEXT, 과제 TEXT);
INSERT INTO 사원 VALUES ('E1','D1'),('E2','D1'),('E3','D2'),('E4','D2'),('E5',NULL);
INSERT INTO 참여 VALUES ('E1','P1'),('E1','P2'),('E3','P1'),('E3','P3');
"""
c = sqlite3.connect(":memory:"); c.executescript(S)
for label, q in [
    ("세미조인 (참여가 있는 사원)",
     "SELECT COUNT(*) FROM 사원 WHERE 사번 IN (SELECT 사번 FROM 참여)"),
    ("안티조인 (참여가 없는 사원)",
     "SELECT COUNT(*) FROM 사원 WHERE 사번 NOT IN (SELECT 사번 FROM 참여)"),
    ("내부조인 (행이 불어난다)",
     "SELECT COUNT(*) FROM 사원 JOIN 참여 USING(사번)"),
]:
    print(f"   {label:<26} {c.execute(q).fetchone()[0]}")
c.close()
print("   → 세미조인은 행을 불리지 않는다(2). 내부조인은 3으로 불어난다")

print("\n" + BAR)
print("38  체크포인트 이후 REDO / UNDO 집합")
LOG = [
    "<T1 start>", "<T1, A, 100, 200>", "<T1 commit>",
    "<T2 start>", "<T2, B, 50, 80>",
    "<checkpoint {T2}>",
    "<T3 start>", "<T3, C, 10, 30>", "<T3 commit>",
    "<T2, D, 5, 15>",
    "<T4 start>", "<T4, E, 1, 7>",
    "-- 여기서 장애 --",
]
undo, redo, started = set(), set(), set()
after_ckpt = False
for line in LOG:
    if line.startswith("<checkpoint"):
        after_ckpt = True
        started |= {"T2"}          # 체크포인트 시점의 활성 목록
        undo |= {"T2"}
        continue
    if "start>" in line:
        t = line.split()[0].strip("<")
        started.add(t); undo.add(t)
    elif "commit>" in line:
        t = line.split()[0].strip("<")
        undo.discard(t); redo.add(t)
print("   로그:")
for l in LOG:
    print(f"     {l}")
print(f"   REDO {sorted(redo)}   UNDO {sorted(undo)}")
print("   → T1 은 체크포인트 앞에서 커밋돼 REDO 대상이 아니다(무시)")
redo.discard("T1")
print(f"   최종 REDO {sorted(redo)} · UNDO {sorted(undo)}")
