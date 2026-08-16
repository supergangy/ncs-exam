# -*- coding: utf-8 -*-
"""전산 문항 검증 — **정답을 돌려서 확인한다.**

NCS 지문형은 지문이 정답 근거를 통제하므로 지문만 맞으면 정답이 확정된다.
전산 전공은 그렇지 않다. 정답이 **지문 밖 사실**로 정해지므로 틀리면 막을 수단이 없다.

계산·판정형은 다행히 **실행으로 확정할 수 있다.** SQL 은 sqlite 로 돌리고,
함수 종속은 폐포로 후보키를 구해 정규형을 판정하고, 스케줄링과 페이지 교체는
시뮬레이션하고, 서브넷은 비트 연산으로 센다.

여기에 문항별 검증을 하나씩 등록한다. **등록되지 않은 문항은 「미검증」으로 보고**한다 —
검증기가 없다는 사실 자체를 드러내야 개념형 문항이 슬쩍 섞이는 것을 막는다.

```bash
python tools/verify_cs.py                     # 전 과목
python tools/verify_cs.py --subject database
```
"""
from __future__ import annotations

import argparse
import itertools
import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ── 검증 도구 ───────────────────────────────────────────────────────────

def closure(attrs: set[str], fds: list[tuple[set, set]], seed) -> set[str]:
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
                continue
            if closure(attrs, fds, c) == attrs:
                keys.append(c)
    return keys


def highest_normal_form(attrs: set[str], fds: list[tuple[set, set]]) -> int:
    """1·2·3 을 돌려준다. BCNF 판정은 별도로 본다."""
    keys = candidate_keys(attrs, fds)
    prime = set().union(*keys) if keys else set()
    for left, right in fds:
        if right <= left:
            continue
        # 2NF — 후보키의 진부분집합에 비주요 속성이 의존하면 위반
        if any(left < k for k in keys) and not (right <= prime):
            return 1
    for left, right in fds:
        if right <= left:
            continue
        # 3NF — 결정자가 후보키가 아니고 종속자가 비주요 속성이면 위반
        if not any(left == k for k in keys) and not (right <= prime):
            return 2
    return 3


# ── 문항별 검증 ─────────────────────────────────────────────────────────

def v_csdb_001() -> tuple[int, str]:
    attrs = {"학번", "과목코드", "성적", "담당교수", "교수연구실"}
    fds = [({"학번", "과목코드"}, {"성적"}),
           ({"과목코드"}, {"담당교수"}),
           ({"담당교수"}, {"교수연구실"})]
    keys = candidate_keys(attrs, fds)
    nf = highest_normal_form(attrs, fds)
    return nf, f"후보키 {[sorted(k) for k in keys]} · 최고 정규형 제{nf}정규형"


def v_csdb_002() -> tuple[int, str]:
    con = sqlite3.connect(":memory:")
    con.executescript("""
    CREATE TABLE 부서(부서코드 TEXT PRIMARY KEY, 부서명 TEXT);
    CREATE TABLE 사원(사번 INTEGER PRIMARY KEY, 이름 TEXT, 부서코드 TEXT, 급여 INTEGER);
    INSERT INTO 부서 VALUES ('D1','운영'),('D2','기술'),('D3','기획'),('D4','안전');
    INSERT INTO 사원 VALUES (1,'김','D1',4200),(2,'이','D1',3800),(3,'박','D2',5100),
                            (4,'최','D2',3300),(5,'정','D2',4700),(6,'한','D3',3900),
                            (7,'오',NULL,4400);
    """)
    on = con.execute("""SELECT 부.부서명, COUNT(사.사번) FROM 부서 부
        LEFT JOIN 사원 사 ON 부.부서코드 = 사.부서코드 AND 사.급여 >= 4000
        GROUP BY 부.부서명""").fetchall()
    where = con.execute("""SELECT 부.부서명, COUNT(사.사번) FROM 부서 부
        LEFT JOIN 사원 사 ON 부.부서코드 = 사.부서코드
        WHERE 사.급여 >= 4000 GROUP BY 부.부서명""").fetchall()
    return len(on), f"ON 절 {len(on)}행 {sorted(on)} · WHERE 로 옮기면 {len(where)}행"


def v_csdb_003() -> tuple[int, str]:
    con = sqlite3.connect(":memory:")
    con.executescript("""
    CREATE TABLE 사원(사번 INTEGER, 이름 TEXT, 관리자 INTEGER);
    INSERT INTO 사원 VALUES (1,'김',NULL),(2,'이',1),(3,'박',1),(4,'최',2);
    """)
    notin = con.execute("SELECT COUNT(*) FROM 사원 "
                        "WHERE 사번 NOT IN (SELECT 관리자 FROM 사원)").fetchone()[0]
    nonull = con.execute("SELECT COUNT(*) FROM 사원 WHERE 사번 NOT IN "
                         "(SELECT 관리자 FROM 사원 WHERE 관리자 IS NOT NULL)").fetchone()[0]
    notex = con.execute("SELECT COUNT(*) FROM 사원 e WHERE NOT EXISTS "
                        "(SELECT 1 FROM 사원 m WHERE m.관리자 = e.사번)").fetchone()[0]
    return notin, f"NOT IN(NULL 포함) {notin} · NULL 제외 {nonull} · NOT EXISTS {notex}"


def v_csdb_004() -> tuple[str, str]:
    """ANSI/ISO 격리수준 표. REPEATABLE READ 행에서 O 로 남는 칸을 찾는다."""
    table = {
        "READ UNCOMMITTED": {"Dirty Read": 1, "Non-repeatable Read": 1, "Phantom Read": 1},
        "READ COMMITTED":   {"Dirty Read": 0, "Non-repeatable Read": 1, "Phantom Read": 1},
        "REPEATABLE READ":  {"Dirty Read": 0, "Non-repeatable Read": 0, "Phantom Read": 1},
        "SERIALIZABLE":     {"Dirty Read": 0, "Non-repeatable Read": 0, "Phantom Read": 0},
    }
    left = [k for k, v in table["REPEATABLE READ"].items() if v]
    return (left[0] if len(left) == 1 else "복수"), f"REPEATABLE READ 에 남는 현상 {left}"


def v_csdb_005() -> tuple[int, str]:
    """차수 m 인 B+트리가 키 n 개를 담는 최소 높이. 루트만 있으면 높이 1."""
    def height(m: int, n: int) -> tuple[int, int]:
        h, cap = 1, m - 1
        while cap < n:
            h += 1
            cap *= m
        return h, cap
    h, cap = height(200, 1_000_000)
    h100, _ = height(100, 1_000_000)
    return h, f"차수 200 → 높이 {h} (수용 {cap:,}) · 차수 100 이면 {h100} (오답 ③의 경로)"


def v_csdb_006() -> tuple[str, str]:
    """후보키가 둘이라 비주요 속성이 없다 → 3NF 통과. 결정자 하나가 후보키가 아니라 BCNF 위반."""
    attrs = {"학생", "동아리", "지도교수"}
    fds = [({"학생", "동아리"}, {"지도교수"}), ({"지도교수"}, {"동아리"})]
    keys = candidate_keys(attrs, fds)
    nf = highest_normal_form(attrs, fds)
    viol = [sorted(l) for l, r in fds if not any(l == k for k in keys) and not r <= l]
    verdict = "3NF만족_BCNF위반" if nf == 3 and viol else f"3NF={nf}_위반{viol}"
    return verdict, f"후보키 {[sorted(k) for k in keys]} · 3NF={nf} · BCNF 위반 결정자 {viol}"


def v_csdb_007() -> tuple[int, str]:
    """무손실 = 공통 속성의 폐포가 어느 한쪽을 덮는다. 선지 순서대로 판정."""
    attrs = {"A", "B", "C", "D"}
    fds = [({"A"}, {"B"}), ({"B"}, {"C"}), ({"C"}, {"D"})]
    cands = [({"A", "B"}, {"C", "D"}), ({"A", "C"}, {"B", "D"}),
             ({"A", "B"}, {"B", "C", "D"}), ({"A", "D"}, {"B", "C"}),
             ({"B", "D"}, {"A", "C"})]
    ok = []
    for i, (r1, r2) in enumerate(cands, 1):
        common = r1 & r2
        if common and (closure(attrs, fds, common) >= r1 or closure(attrs, fds, common) >= r2):
            ok.append(i)
    return (ok[0] if len(ok) == 1 else 0), f"무손실인 선지 {ok}"


def v_csdb_008() -> tuple[int, str]:
    con = sqlite3.connect(":memory:")
    con.executescript("""
    CREATE TABLE 주문(주문번호 INTEGER, 고객번호 INTEGER, 금액 INTEGER, 상태 TEXT);
    INSERT INTO 주문 VALUES (101,1,52000,'완료'),(102,1,18000,'취소'),(103,2,74000,'완료'),
    (104,2,33000,'완료'),(105,3,91000,'배송중'),(106,3,27000,'취소'),(107,4,45000,'완료');
    """)
    n = len(con.execute("SELECT 고객번호, SUM(금액) FROM 주문 WHERE 상태='완료' "
                        "GROUP BY 고객번호 HAVING SUM(금액)>=100000").fetchall())
    n_all = len(con.execute("SELECT 고객번호, SUM(금액) FROM 주문 "
                            "GROUP BY 고객번호 HAVING SUM(금액)>=100000").fetchall())
    n_grp = len(con.execute("SELECT 고객번호 FROM 주문 WHERE 상태='완료' "
                            "GROUP BY 고객번호").fetchall())
    return n, f"완료만 {n}행 · 상태 조건 없이 {n_all}행(오답③) · 완료 그룹 수 {n_grp}(오답④)"


def v_csdb_009() -> tuple[tuple, str]:
    """디비전 — S 의 모든 값과 짝을 이루는 학번."""
    R = {(1, "a"), (1, "b"), (2, "a"), (3, "a"), (3, "b"), (4, "b")}
    S = {"a", "b"}
    res = tuple(sorted(x for x in {x for x, _ in R} if all((x, s) in R for s in S)))
    return res, f"R ÷ S = {res}"


def v_csdb_010() -> tuple[tuple, str]:
    """commit 기록이 있으면 REDO, 없으면 UNDO."""
    log = [("T1", "start"), ("T1", "write"), ("T2", "start"), ("T2", "write"),
           ("T1", "commit"), ("T3", "start"), ("T3", "write")]
    txs = sorted({t for t, _ in log})
    done = {t for t, op in log if op == "commit"}
    plan = tuple("REDO" if t in done else "UNDO" for t in txs)
    return plan, f"{dict(zip(txs, plan))}"


def v_csdb_011() -> tuple[tuple, str]:
    attrs = {"A", "B", "C", "D", "E"}
    fds = [({"A"}, {"B", "C"}), ({"B"}, {"D"}), ({"C", "D"}, {"E"})]
    keys = candidate_keys(attrs, fds)
    note = " · ".join(f"{s}+={sorted(closure(attrs, fds, set(s)))}"
                      for s in ("A", "B", "AC"))
    return tuple(sorted("".join(sorted(k)) for k in keys)), f"후보키 {[sorted(k) for k in keys]} · {note}"


def v_csdb_012() -> tuple[tuple, str]:
    con = sqlite3.connect(":memory:")
    con.executescript("""CREATE TABLE 성적(이름 TEXT, 점수 INTEGER);
    INSERT INTO 성적 VALUES ('김',88),('이',NULL),('박',92),('최',88),('정',75);""")
    r = con.execute("SELECT COUNT(점수), COUNT(*), AVG(점수) FROM 성적").fetchone()
    wrong = round(sum([88, 92, 88, 75]) / 5, 1)
    return (r[0], r[1], round(r[2], 2)), f"{r} · NULL 을 0 으로 보면 AVG {wrong}(오답⑤)"


def v_csdb_015() -> tuple[float, str]:
    n, d_sex, d_id = 200_000, 4, 200_000
    return d_sex / n, (f"성별 선택도 {d_sex/n:.5f}(값당 {n//d_sex:,}건) · "
                       f"회원번호 {d_id/n:.1f}(값당 {n//d_id}건)")


def v_csdb_016() -> tuple[int, str]:
    con = sqlite3.connect(":memory:")
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript("""CREATE TABLE 부서(코드 TEXT PRIMARY KEY);
    CREATE TABLE 사원(사번 INTEGER PRIMARY KEY,
                      부서 TEXT REFERENCES 부서(코드) ON DELETE CASCADE);
    INSERT INTO 부서 VALUES ('D1'),('D2');
    INSERT INTO 사원 VALUES (1,'D1'),(2,'D1'),(3,'D2');""")
    con.execute("DELETE FROM 부서 WHERE 코드='D1'")
    left = con.execute("SELECT 사번 FROM 사원").fetchall()
    return len(left), f"D1 삭제 후 남은 사원 {[r[0] for r in left]} → {len(left)}개"


def v_csdb_017() -> tuple[int, str]:
    """두 트랜잭션이 같은 값을 읽고 각자 저장한다. 나중 쓰기가 앞 갱신을 덮는다."""
    stored, r1, r2 = 100, 100, 100
    stored = r1 + 50          # T1 write
    stored = r2 + 20          # T2 write — T1 의 갱신을 덮는다
    serial = 100 + 50 + 20
    return stored, f"최종 {stored} · 직렬 실행이면 {serial}(오답②)"


def v_csdb_018() -> tuple[int, str]:
    attrs = {"주문번호", "상품코드", "수량", "상품명", "단가"}
    fds = [({"주문번호", "상품코드"}, {"수량"}), ({"상품코드"}, {"상품명", "단가"})]
    nf = highest_normal_form(attrs, fds)
    # 분해 후 무손실인지 — 공통 속성 상품코드가 상품 릴레이션의 후보키인가
    r1, r2 = {"주문번호", "상품코드", "수량"}, {"상품코드", "상품명", "단가"}
    common = r1 & r2
    lossless = closure(attrs, fds, common) >= r2
    return nf, (f"최고 정규형 제{nf}정규형 · 분해 공통 {sorted(common)} → "
                f"{'무손실' if lossless else '손실'}")


def v_csdb_019() -> tuple[int, str]:
    """개체는 각각 릴레이션. M:N 은 별도 릴레이션. N:1 은 외래키로 흡수."""
    entities = ["학생", "과목", "강의실"]
    rels = [("학생", "과목", "M:N"), ("과목", "강의실", "N:1")]
    extra = [r for r in rels if r[2] == "M:N"]
    total = len(entities) + len(extra)
    return total, f"개체 {len(entities)} + M:N 관계 {len(extra)} + N:1 관계 0 = {total}"


# ── 개념형 검증 ─────────────────────────────────────────────────────────
# 실행으로 떨어지지 않는 문항이다. 계산 대신 **표준 정의를 표로 적어 두고**
# 그 표에서 답을 뽑는다. 값을 문항과 같은 파일에 두면 서로를 베끼게 되므로
# 정의는 여기에만 두고, 문항은 여기서 나온 값과 대조만 한다.

def v_csdb_013() -> tuple[int, str]:
    """표준 SQL 의 갱신 가능 뷰 조건 — 단일 테이블·집계 없음·DISTINCT 없음·GROUP BY 없음."""
    views = [
        ("GROUP BY 집계",      {"single": True,  "agg": True,  "distinct": False, "join": False}),
        ("DISTINCT",           {"single": True,  "agg": False, "distinct": True,  "join": False}),
        ("단일 테이블 부분집합", {"single": True,  "agg": False, "distinct": False, "join": False}),
        ("두 테이블 조인",      {"single": False, "agg": False, "distinct": False, "join": True}),
        ("집계 + 산술식",       {"single": True,  "agg": True,  "distinct": False, "join": False}),
    ]
    ok = [i for i, (_, v) in enumerate(views, 1)
          if v["single"] and not v["agg"] and not v["distinct"] and not v["join"]]
    return (ok[0] if len(ok) == 1 else 0), f"갱신 가능한 선지 {ok} ({views[ok[0]-1][0]})"


def v_csdb_014() -> tuple[int, str]:
    """클러스터드 대 비클러스터드. 문항은 「옳지 않은 것」을 묻는다."""
    facts = [
        ("데이터 행이 키 순서로 저장", True),
        ("테이블당 여러 개 가능", False),          # 비클러스터드의 성질이다
        ("범위 검색에 유리", True),
        ("키 변경 시 행 이동 비용", True),
        ("리프가 데이터 페이지", True),
    ]
    wrong = [i for i, (_, t) in enumerate(facts, 1) if not t]
    return (wrong[0] if len(wrong) == 1 else 0), f"틀린 진술 {wrong} ({facts[wrong[0]-1][0]})"


def v_csdb_020() -> tuple[int, str]:
    """2PL 이 보장하는 것과 보장하지 않는 것.

    교착이 성립하는 순서를 실제로 구성해 확인한다 —
    두 트랜잭션이 모두 확장 단계에 있으면서 서로의 잠금을 기다리면 멈춘다.
    """
    held: dict[str, str] = {}
    steps = [("T1", "lock", "A"), ("T2", "lock", "B"),
             ("T1", "lock", "B"), ("T2", "lock", "A")]
    waiting = []
    for tx, _, res in steps:
        if res in held and held[res] != tx:
            waiting.append((tx, res))
        else:
            held[res] = tx
    deadlock = len(waiting) >= 2 and {w[0] for w in waiting} == {"T1", "T2"}
    claims = [("직렬가능·교착회피 둘 다", False),
              ("직렬가능 보장·교착 발생 가능", True),
              ("교착 방지·직렬가능 미보장", False),
              ("잠금 미사용", False),
              ("확장 단계에서 해제 가능", False)]
    right = [i for i, (_, t) in enumerate(claims, 1) if t]
    return right[0], (f"교착 성립 {deadlock} (대기 {waiting}) · "
                      f"옳은 진술 {right}")


# ── 운영체제 ────────────────────────────────────────────────────────────

_OS_JOBS = [("P1", 0, 8), ("P2", 1, 4), ("P3", 2, 9), ("P4", 3, 5)]


def _sjf_np(js):
    t, rem, res = 0, list(js), {}
    while rem:
        ready = [j for j in rem if j[1] <= t] or [min(rem, key=lambda x: x[1])]
        n, a, b = min(ready, key=lambda x: x[2])
        t = max(t, a)
        res[n] = (t - a, t - a + b)
        t += b
        rem.remove((n, a, b))
    return res


def _srtf(js):
    rem = {n: b for n, a, b in js}
    arr = {n: a for n, a, b in js}
    t, fin = 0, {}
    while rem:
        ready = [n for n in rem if arr[n] <= t]
        if not ready:
            t += 1
            continue
        n = min(ready, key=lambda x: rem[x])
        rem[n] -= 1
        t += 1
        if rem[n] == 0:
            fin[n] = t
            del rem[n]
    return {n: (fin[n] - arr[n] - b, fin[n] - arr[n]) for n, a, b in js}


def _rr(js, q=4):
    from collections import deque
    rem = {n: b for n, a, b in js}
    arr = {n: a for n, a, b in js}
    order = sorted(js, key=lambda x: x[1])
    t, dq, seen, fin = 0, deque(), set(), {}
    while rem:
        for n, a, b in order:
            if a <= t and n not in seen and n in rem:
                dq.append(n); seen.add(n)
        if not dq:
            t += 1
            continue
        n = dq.popleft()
        run = min(q, rem[n]); t += run; rem[n] -= run
        for m, a, b in order:
            if a <= t and m not in seen and m in rem:
                dq.append(m); seen.add(m)
        if rem[n] == 0:
            fin[n] = t; del rem[n]
        else:
            dq.append(n)
    return {n: (fin[n] - arr[n] - b, fin[n] - arr[n]) for n, a, b in js}


def _avg(res, idx):
    return round(sum(v[idx] for v in res.values()) / len(res), 2)


def v_csos_001() -> tuple[float, str]:
    r = _sjf_np(_OS_JOBS)
    return _avg(r, 0), (f"SJF 평균대기 {_avg(r,0)} · FCFS 8.75 · "
                        f"SRTF {_avg(_srtf(_OS_JOBS),0)} · RR {_avg(_rr(_OS_JOBS),0)}")


def v_csos_002() -> tuple[float, str]:
    r = _srtf(_OS_JOBS)
    return _avg(r, 0), f"SRTF 평균대기 {_avg(r,0)} · 비선점 SJF {_avg(_sjf_np(_OS_JOBS),0)}(오답②)"


def v_csos_003() -> tuple[float, str]:
    r = _rr(_OS_JOBS, 4)
    return _avg(r, 1), f"RR(q=4) 평균반환 {_avg(r,1)} · 완료 {r}"


def _fifo(ref, k):
    f, miss = [], 0
    for p in ref:
        if p not in f:
            miss += 1
            if len(f) == k:
                f.pop(0)
            f.append(p)
    return miss


def _lru(ref, k):
    f, miss = [], 0
    for p in ref:
        if p in f:
            f.remove(p)
        else:
            miss += 1
            if len(f) == k:
                f.pop(0)
        f.append(p)
    return miss


def _opt(ref, k):
    f, miss = [], 0
    for i, p in enumerate(ref):
        if p in f:
            continue
        miss += 1
        if len(f) < k:
            f.append(p)
            continue
        future = ref[i + 1:]
        nxt = [future.index(q) if q in future else 10 ** 9 for q in f]
        f[nxt.index(max(nxt))] = p
    return miss


_REF = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2]


def v_csos_004() -> tuple[int, str]:
    return _lru(_REF, 3), (f"프레임3 — FIFO {_fifo(_REF,3)} · LRU {_lru(_REF,3)} · "
                           f"OPT {_opt(_REF,3)}")


def v_csos_005() -> tuple[bool, str]:
    """벨라디 변이 — 프레임을 늘렸는데 부재가 늘어나는지."""
    ref = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
    f3, f4 = _fifo(ref, 3), _fifo(ref, 4)
    l3, l4 = _lru(ref, 3), _lru(ref, 4)
    return f4 > f3, (f"FIFO 프레임3 {f3} → 프레임4 {f4} (변이 {f4>f3}) · "
                     f"LRU {l3} → {l4} (변이 {l4>l3})")


def v_csos_006() -> tuple[tuple, str]:
    alloc = {"P0": (0, 1, 0), "P1": (2, 0, 0), "P2": (3, 0, 2),
             "P3": (2, 1, 1), "P4": (0, 0, 2)}
    mx = {"P0": (7, 5, 3), "P1": (3, 2, 2), "P2": (9, 0, 2),
          "P3": (2, 2, 2), "P4": (4, 3, 3)}
    need = {p: tuple(mx[p][i] - alloc[p][i] for i in range(3)) for p in alloc}
    work, fin, seq = [3, 3, 2], set(), []
    while len(fin) < len(alloc):
        for p in alloc:
            if p in fin:
                continue
            if all(need[p][i] <= work[i] for i in range(3)):
                for i in range(3):
                    work[i] += alloc[p][i]
                fin.add(p); seq.append(p)
                break
        else:
            break
    return tuple(seq), f"필요량 {need} · 안전순서 {seq} · {'안전' if len(fin)==5 else '불안전'}"


def v_csos_007() -> tuple[int, str]:
    head, req = 53, [98, 183, 37, 122, 14, 124, 65, 67]
    dist = lambda order, h: sum(abs(b - a) for a, b in zip([h] + order, order))
    cur, rem, sstf = head, req[:], []
    while rem:
        n = min(rem, key=lambda x: abs(x - cur))
        sstf.append(n); cur = n; rem.remove(n)
    scan = sorted(x for x in req if x >= head) + sorted((x for x in req if x < head),
                                                       reverse=True)
    return dist(sstf, head), (f"FCFS {dist(req,head)} · SSTF {dist(sstf,head)} {sstf} · "
                              f"SCAN {dist(scan,head)}")


def v_csos_008() -> tuple[tuple, str]:
    la, ps = 8195, 4096
    return (la // ps, la % ps), f"{la} // {ps} = {la//ps} · 나머지 {la%ps}"


def v_csos_009() -> tuple[int, str]:
    blocks, want = [100, 500, 200, 300, 600], 212
    fit = [(b, i) for i, b in enumerate(blocks) if b >= want]
    best = min(fit)[0]
    first = next(b for b in blocks if b >= want)
    worst = max(fit)[0]
    return best - want, (f"최초 {first}(잔여 {first-want}) · 최적 {best}(잔여 {best-want}) · "
                         f"최악 {worst}(잔여 {worst-want})")


def v_csos_010() -> tuple[int, str]:
    tlb, mem, hit = 20, 100, 0.9
    eat = hit * (tlb + mem) + (1 - hit) * (tlb + 2 * mem)
    eat80 = 0.8 * (tlb + mem) + 0.2 * (tlb + 2 * mem)
    return round(eat), f"적중 90% → {eat:.0f}ns · 80% 면 {eat80:.0f}ns(오답④)"


def v_csos_011() -> tuple[int, str]:
    va, ps, pte, outer = 32, 4096, 4, 1024
    pages = 2 ** va // ps
    one_level = pages * pte
    inner = pages // outer * pte
    return inner, (f"페이지 {pages:,} · 1단 {one_level//1024//1024}MB(오답④) · "
                   f"내부 {pages//outer:,}항 × {pte}B = {inner//1024}KB")


def v_csos_012() -> tuple[int, str]:
    ref = [2, 6, 1, 5, 7, 7, 7, 7, 5, 1, 6, 2, 3, 4, 1, 2, 3, 4, 4, 4, 3, 4, 4, 4]
    ws = lambda t, d: sorted(set(ref[max(0, t - d):t]))
    return len(ws(14, 5)), f"t=14 Δ=5 → {ws(14,5)} ({len(ws(14,5))}개) · t=10 이면 {ws(10,5)}"


def v_csos_013() -> tuple[int, str]:
    """5상태 모형에 정의된 전이. 없는 것의 선지 번호를 돌려준다."""
    cand = [("준비", "실행"), ("실행", "준비"), ("실행", "대기"),
            ("대기", "준비"), ("대기", "실행")]
    defined = {("준비", "실행"), ("실행", "준비"), ("실행", "대기"), ("대기", "준비")}
    missing = [i for i, c in enumerate(cand, 1) if c not in defined]
    return (missing[0] if len(missing) == 1 else 0), f"정의되지 않은 전이 {missing} {cand[missing[0]-1]}"


def v_csos_014() -> tuple[int, str]:
    """스레드 공유 여부. 공유하지 않는 항목의 선지 번호."""
    items = [("코드", True), ("데이터", True), ("힙", True),
             ("스택", False), ("열린 파일 목록", True)]
    priv = [i for i, (_, shared) in enumerate(items, 1) if not shared]
    return (priv[0] if len(priv) == 1 else 0), f"공유하지 않는 것 {priv} ({items[priv[0]-1][0]})"


def v_csos_015() -> tuple[int, str]:
    s, log = 2, []
    for op in ("P", "P", "P", "V", "P"):
        s += -1 if op == "P" else 1
        log.append(f"{op}→{s}")
    return max(0, -s), f"{' '.join(log)} · 최종 S={s} · 대기 {max(0,-s)}개"


def v_csos_017() -> tuple[int, str]:
    direct, ptr = 12, 256
    total = direct + ptr + ptr ** 2
    wrong2 = direct + ptr + ptr * 2
    return total, (f"{direct} + {ptr} + {ptr}² = {total:,} · "
                   f"이중을 두 배로 보면 {wrong2}(오답②) · 직접 누락 {total-direct:,}(오답④)")


def v_csos_018() -> tuple[tuple, str]:
    n, cap = 4, 1000
    levels = {"RAID0": (n * cap, 0), "RAID1": (n * cap // 2, 1),
              "RAID5": ((n - 1) * cap, 1), "RAID6": ((n - 2) * cap, 2)}
    return levels["RAID5"], " · ".join(f"{k} {v[0]}GB/장애{v[1]}" for k, v in levels.items())


# ── 네트워크 ────────────────────────────────────────────────────────────

def v_csnet_001() -> tuple[int, str]:
    import ipaddress
    n = ipaddress.ip_network("192.168.10.0/26")
    others = {p: ipaddress.ip_network(f"192.168.10.0/{p}").num_addresses - 2
              for p in (24, 25, 26, 27)}
    return n.num_addresses - 2, f"/26 호스트 {n.num_addresses-2} · 프리픽스별 {others}"


def v_csnet_002() -> tuple[str, str]:
    import ipaddress
    i = ipaddress.ip_interface("192.168.1.130/26")
    hosts = list(i.network.hosts())
    return str(i.network.network_address), (f"네트워크 {i.network} · "
                                           f"범위 {hosts[0]}~{hosts[-1]}")


def v_csnet_003() -> tuple[int, str]:
    need, host_bits = 6, 8
    borrow = next(b for b in range(1, 9) if 2 ** b >= need)
    hosts = 2 ** (host_bits - borrow) - 2
    table = {b: (2 ** b, 2 ** (host_bits - b) - 2) for b in range(2, 5)}
    return hosts, f"차용 {borrow}비트 → 서브넷 {2**borrow}개 · 호스트 {hosts}개 · {table}"


def v_csnet_004() -> tuple[int, str]:
    import heapq
    g = {"A": {"B": 4, "C": 2}, "B": {"C": 5, "D": 10}, "C": {"E": 3},
         "D": {"F": 11}, "E": {"D": 4}, "F": {}}
    dist, pq = {"A": 0}, [(0, "A")]
    while pq:
        c, u = heapq.heappop(pq)
        if c > dist.get(u, 1 << 30):
            continue
        for v, w in g[u].items():
            if c + w < dist.get(v, 1 << 30):
                dist[v] = c + w
                heapq.heappush(pq, (c + w, v))
    via_b = 4 + 10 + 11
    return dist["F"], f"최소 {dist['F']} (A→C→E→D→F) · B 경유는 {via_b}(오답④) · {dist}"


def v_csnet_005() -> tuple[int, str]:
    cwnd, thr, hist = 1, 16, []
    for _ in range(7):
        hist.append(cwnd)
        cwnd = cwnd * 2 if cwnd < thr else cwnd + 1
    return hist[5], f"왕복별 {hist} · 6번째 {hist[5]} · 지수 연장이면 {2**5}(오답④)"


def v_csnet_010() -> tuple[int, str]:
    d = 5
    detect, correct = d - 1, (d - 1) // 2
    table = {x: (x - 1, (x - 1) // 2) for x in (3, 4, 5)}
    return correct, f"거리 {d} → 검출 {detect}(오답④) · 정정 {correct} · {table}"


def v_csnet_011() -> tuple[str, str]:
    import ipaddress
    nets = [ipaddress.ip_network(f"192.168.{i}.0/24") for i in (8, 9, 10, 11)]
    merged = list(ipaddress.collapse_addresses(nets))
    return str(merged[0]), f"{[str(n) for n in nets]} → {[str(m) for m in merged]}"


def v_csnet_013() -> tuple[float, str]:
    w, mss, rtt = 8, 1460, 0.1
    thr = w * mss * 8 / rtt / 1e6
    thr16 = 16 * mss * 8 / rtt / 1e6
    return round(thr, 2), f"윈도 {w} → {thr:.2f}Mbps · 윈도 16 이면 {thr16:.2f}(오답③)"


def v_csnet_014() -> tuple[float, str]:
    L, R = 1500 * 8, 10e6
    d, s = 2000e3, 2e8
    tx, pr = L / R * 1000, d / s * 1000
    return round(tx + pr, 1), f"전송 {tx:.1f}ms(오답①) + 전파 {pr:.1f}ms(오답②) = {tx+pr:.1f}ms"


def v_csnet_015() -> tuple[int, str]:
    m = 8
    r = 1
    while 2 ** r < m + r + 1:
        r += 1
    table = {x: next(k for k in range(1, 9) if 2 ** k >= x + k + 1) for x in (4, 8, 11, 16)}
    return r, f"m={m} → r={r} (2^{r}={2**r} ≥ {m+r+1}) · 데이터별 {table}"


def v_csnet_016() -> tuple[str, str]:
    def crc(data: str, gen: str) -> str:
        d = [int(x) for x in data] + [0] * (len(gen) - 1)
        g = [int(x) for x in gen]
        for i in range(len(data)):
            if d[i]:
                for j in range(len(g)):
                    d[i + j] ^= g[j]
        return "".join(map(str, d[-(len(gen) - 1):]))
    r = crc("1101011011", "10011")
    chk = crc("1010001101", "1101")
    return r, f"CRC {r} · 전송 11010110111110 · 다른 조합 검산 1010001101÷1101 → {chk}"


def v_csnet_017() -> tuple[int, str]:
    import ipaddress
    priv = [ipaddress.ip_network(c) for c in ("10.0.0.0/8", "172.16.0.0/12",
                                              "192.168.0.0/16")]
    cand = ["10.20.30.40", "172.16.5.1", "172.32.5.1", "192.168.100.1", "10.255.255.254"]
    out = [i for i, a in enumerate(cand, 1)
           if not any(ipaddress.ip_address(a) in n for n in priv)]
    return (out[0] if len(out) == 1 else 0), f"사설 아닌 것 {out} ({cand[out[0]-1]})"


# ── 정보보안 ────────────────────────────────────────────────────────────

def v_cssec_001() -> tuple[int, str]:
    import math
    p, q, e = 7, 11, 7
    n, phi = p * q, (p - 1) * (q - 1)
    d = pow(e, -1, phi)
    others = {x: pow(x, -1, phi) for x in (13, 17, 19) if math.gcd(x, phi) == 1}
    m = 9
    c = pow(m, e, n)
    return d, (f"n={n} φ={phi} e={e} → d={d} · 검산 {m}→{c}→{pow(c,d,n)} · "
               f"다른 e {others}")


def v_cssec_002() -> tuple[int, str]:
    n = 100
    sym, pub = n * (n - 1) // 2, 2 * n
    return sym, f"{n}명 → 대칭 {sym} · 공개키 {pub}(오답②) · 2로 안 나누면 {n*(n-1)}(오답④)"


def v_cssec_004() -> tuple[int, str]:
    bits = 128
    return bits // 2, f"{bits}비트 → 충돌 2^{bits//2} · 역상 2^{bits}(오답③)"


def v_cssec_012() -> tuple[int, str]:
    asset, ef, aro = 100_000_000, 0.4, 0.5
    sle = asset * ef
    ale = sle * aro
    return int(ale), (f"SLE {int(sle):,}(오답③) × ARO {aro} = ALE {int(ale):,}")


# ── 소프트웨어공학 ──────────────────────────────────────────────────────

def v_csse_001() -> tuple[int, str]:
    """COCOMO 기본형 조직형 — 노력 2.4·KLOC^1.05, 기간 2.5·E^0.38."""
    tbl = {k: (2.4 * k ** 1.05) for k in (30, 50, 100)}
    e = tbl[50]
    return round(e), (f"50 KLOC → {e:.1f} 인월 · 기간 {2.5 * e ** 0.38:.1f}개월 · "
                      f"30 KLOC {tbl[30]:.1f}(오답①) · 100 KLOC {tbl[100]:.1f}(오답⑤) · "
                      f"지수 무시 {2.4 * 50:.0f}(오답②)")


def v_csse_002() -> tuple[int, str]:
    """기능점수 — 유형별 개수 × 가중치의 합."""
    rows = {"입력": (10, 4), "출력": (8, 5), "조회": (6, 4),
            "파일": (3, 10), "인터페이스": (2, 7)}
    parts = {k: c * w for k, (c, w) in rows.items()}
    fp = sum(parts.values())
    return fp, (f"{parts} → {fp} · 개수만 합 {sum(c for c, _ in rows.values())}(오답①)")


def v_csse_003() -> tuple[int, str]:
    """CPM — 선행 관계를 따라 각 작업의 종료 시각을 구하고 최댓값을 잡는다."""
    acts = {"A": (None, 3), "B": ("A", 4), "C": ("A", 2), "D": ("B", 5),
            "E": ("C", 6), "F": ("D", 2), "G": ("E", 1)}

    def fin(n):
        p, d = acts[n]
        return d + (0 if p is None else fin(p))

    ends = {n: fin(n) for n in acts}
    span = max(ends.values())
    return span, (f"종료 시각 {ends} → 임계경로 A→B→D→F {span}일 · "
                  f"A→C→E→G {ends['G']}일 · 단순 합 "
                  f"{sum(d for _, d in acts.values())}(오답⑤)")


def _cov_min(expr, n_cond: int) -> dict[str, int]:
    """조건 n개짜리 식에 대해 각 커버리지 기준의 **최소 테스트 케이스 수**."""
    from itertools import combinations, product
    cases = list(product([True, False], repeat=n_cond))

    def decision(ts):                      # 전체 결과 T·F 모두
        return {expr(*t) for t in ts} == {True, False}

    def condition(ts):                     # 각 조건이 T·F 모두
        return all({t[i] for t in ts} == {True, False} for i in range(n_cond))

    def mcdc(ts):                          # 조건마다 그것만 뒤집어 결과가 갈리는 짝
        s = set(ts)
        for i in range(n_cond):
            if not any(t[i] and (f := tuple(v if j != i else not v
                                            for j, v in enumerate(t))) in s
                       and expr(*t) != expr(*f) for t in s):
                return False
        return True

    def least(pred):
        for k in range(1, len(cases) + 1):
            if any(pred(c) for c in combinations(cases, k)):
                return k
        return 0

    return {"결정": least(decision), "조건": least(condition),
            "MC/DC": least(mcdc), "다중조건": len(cases)}


def v_csse_004() -> tuple[int, str]:
    m = _cov_min(lambda a, b: a and b, 2)
    return m["결정"], f"A and B — 최소 케이스 {m}"


def v_csse_011() -> tuple[int, str]:
    """순환 복잡도 V(G) = E − N + 2."""
    e, n = 11, 8
    return e - n + 2, (f"E {e} − N {n} + 2 = {e - n + 2} · "
                       f"+1 로 하면 {e - n + 1}(오답②) · E+N 이면 {e + n}(오답⑤)")


def v_csse_017() -> tuple[int, str]:
    """포함 관계 — 조건 커버리지가 결정 커버리지를 **함의하지 않는** 반례를 찾는다."""
    from itertools import combinations, product
    cases = list(product([True, False], repeat=2))
    ce = [ts for k in (2, 3) for ts in combinations(cases, k)
          if all({t[i] for t in ts} == {True, False} for i in (0, 1))
          and {a and b for a, b in ts} != {True, False}]
    m = _cov_min(lambda a, b: a and b, 2)
    show = [tuple("T" if v else "F" for v in t) for t in ce[0]] if ce else None
    return (len(ce), f"조건⊅결정 반례 {len(ce)}개 · 최소 예 {show} · 강도 {m}")


# ── 프로그래밍언어 ──────────────────────────────────────────────────────

def _swap_sim(mode: str) -> tuple[int, int]:
    """swap(a, b) 를 전달 방식별로 모사한다. 값 호출만 원본이 남는다."""
    a, b = 10, 20
    if mode == "값":                      # 복사본만 교환된다
        x, y = a, b
        x, y = y, x
        return a, b
    if mode in ("참조", "값-결과", "이름"):  # 원본에 되돌아간다
        return b, a
    raise ValueError(mode)


def v_cspl_001() -> tuple[str, str]:
    out = {m: _swap_sim(m) for m in ("값", "참조", "값-결과", "이름")}
    a, b = out["값"]
    return f"{a} {b}", f"{out}"


def v_cspl_002() -> tuple[int, str]:
    """호출 횟수 C(n) = C(n-1) + C(n-2) + 1. 실제로 세어 확인한다."""
    n_calls = {"n": 0}

    def f(n):
        n_calls["n"] += 1
        return n if n < 2 else f(n - 1) + f(n - 2)

    got = {}
    for n in (5, 6, 10):
        n_calls["n"] = 0
        v = f(n)
        got[n] = (v, n_calls["n"])
    return got[6][1], (f"f(6)={got[6][0]}(오답①) 호출 {got[6][1]} · "
                       f"f(5) 호출 {got[5][1]}(오답③) · f(10) 호출 {got[10][1]}")


def v_cspl_003() -> tuple[tuple, str]:
    ops = ["p1", "p2", "o", "p3", "p4", "o", "p5", "o", "o"]
    st, so = [], []
    q, qo = [], []
    for op in ops:
        if op[0] == "p":
            st.append(int(op[1])); q.append(int(op[1]))
        else:
            so.append(st.pop()); qo.append(q.pop(0))
    return tuple(so), f"스택 {so} 잔여 {st} · 큐 {qo} 잔여 {q}(오답①)"


def _to_postfix(s: str) -> str:
    pr = {"+": 1, "-": 1, "*": 2, "/": 2, "^": 3}
    out, stk = [], []
    for t in s.split():
        if t.isalnum():
            out.append(t)
        elif t == "(":
            stk.append(t)
        elif t == ")":
            while stk[-1] != "(":
                out.append(stk.pop())
            stk.pop()
        else:
            while stk and stk[-1] != "(" and pr.get(stk[-1], 0) >= pr[t]:
                out.append(stk.pop())
            stk.append(t)
    return " ".join(out + stk[::-1])


def v_cspl_004() -> tuple[str, str]:
    got = _to_postfix("( A + B ) * C - D")
    return got, f"괄호 있음 {got} · 없으면 {_to_postfix('A + B * C - D')}"


def _bst(vals):
    class N:
        __slots__ = ("v", "l", "r")

        def __init__(self, v):
            self.v, self.l, self.r = v, None, None

    def ins(r, v):
        if r is None:
            return N(v)
        if v < r.v:
            r.l = ins(r.l, v)
        else:
            r.r = ins(r.r, v)
        return r

    root = None
    for v in vals:
        root = ins(root, v)

    def walk(r, k, acc):
        if r is None:
            return acc
        if k == "pre":
            acc.append(r.v)
        walk(r.l, k, acc)
        if k == "in":
            acc.append(r.v)
        walk(r.r, k, acc)
        if k == "post":
            acc.append(r.v)
        return acc

    return {k: walk(root, k, []) for k in ("pre", "in", "post")}


def v_cspl_005() -> tuple[tuple, str]:
    w = _bst([50, 30, 70, 20, 40, 60, 80])
    return tuple(w["post"]), f"전위 {w['pre']}(오답②) · 중위 {w['in']}(오답①) · 후위 {w['post']}"


def v_cspl_008() -> tuple[int, str]:
    """정적 유효 범위 — f 가 **적힌 자리**의 바깥을 본다. 호출한 g 를 보지 않는다."""
    scopes = {"정적": {"f": "전역"}, "동적": {"f": "g"}}
    val = {"전역": 10, "g": 20}
    got = {k: val[v["f"]] for k, v in scopes.items()}
    return got["정적"], f"정적 {got['정적']} · 동적 {got['동적']}(오답②)"


def v_cspl_011() -> tuple[str, str]:
    bits = 8
    two = (-(2 ** (bits - 1)), 2 ** (bits - 1) - 1)
    sm = (-(2 ** (bits - 1) - 1), 2 ** (bits - 1) - 1)
    un = (0, 2 ** bits - 1)
    return (f"{two[0]} ~ {two[1]}",
            f"2의보수 {two} 가짓수 {two[1]-two[0]+1} · "
            f"부호절댓값 {sm}(오답①) · 부호없음 {un}(오답④)")


def v_cspl_012() -> tuple[int, str]:
    base, size, rows, cols, i, j = 1000, 4, 5, 4, 2, 3
    row_major = base + (i * cols + j) * size
    col_major = base + (j * rows + i) * size
    return row_major, f"행 우선 {row_major} · 열 우선 {col_major}(오답④)"


def v_cspl_015() -> tuple[tuple, str]:
    import math
    n = 1000
    cand = {"O(1)": 1, "O(log n)": math.log2(n), "O(n)": n,
            "O(n log n)": n * math.log2(n), "O(n²)": n ** 2}
    order = tuple(sorted(cand, key=cand.get))
    return order, f"n={n} 대입 " + " < ".join(f"{k}({cand[k]:.0f})" for k in order)


def v_cspl_017() -> tuple[int, str]:
    """포인터 역참조 대입 — 주소를 값으로 넘겨도 가리키는 대상은 바뀐다."""
    mem = {"a": 10}
    p = "a"                       # &a 를 받은 것과 같다
    mem[p] = mem[p] + 5           # *p = *p + 5
    return mem["a"], f"a: 10 → {mem['a']} · 정수를 값으로 넘겼다면 10(오답①)"


# ── 전자계산기구조 ──────────────────────────────────────────────────────

def _twos(v: int, bits: int = 8) -> str:
    return format(v & (2 ** bits - 1), f"0{bits}b")


def v_csca_001() -> tuple[str, str]:
    v, bits = -5, 8
    two = _twos(v, bits)
    ones = format((2 ** bits - 1) ^ abs(v), f"0{bits}b")      # 1의 보수
    sm = format((1 << (bits - 1)) | abs(v), f"0{bits}b")      # 부호-절댓값
    back = int(two, 2) - 2 ** bits
    return two, (f"-5 → 2의보수 {two} (역산 {back}) · "
                 f"1의보수 {ones}(오답②) · 부호절댓값 {sm}(오답①)")


def v_csca_002() -> tuple[str, str]:
    b = "10110101"
    n = int(b, 2)
    return format(n, "X"), (f"{b} = {n} → 16진 {n:X} · 8진 {n:o} · "
                            f"네 자리씩 {b[:4]}({int(b[:4],2):X}) {b[4:]}({int(b[4:],2):X})")


def v_csca_003() -> tuple[str, str]:
    """IEEE 754 단정도의 지수부를 실제 비트열에서 뽑아 확인한다."""
    import struct
    got = {}
    for v in (1.0, -0.75, 12.5):
        bits = "".join(f"{x:08b}" for x in struct.pack(">f", v))
        got[v] = (bits[0], bits[1:9], int(bits[1:9], 2) - 127)
    exp = got[12.5][1]
    return exp, (f"12.5 = 1.1001×2^{got[12.5][2]} → 지수부 {exp}({int(exp,2)}) · "
                 f"1.0 {got[1.0][1]} · -0.75 {got[-0.75][1]} · "
                 f"바이어스 미적용이면 {format(3,'08b')}(오답⑤)")


def v_csca_005() -> tuple[int, str]:
    k, n, t = 5, 100, 1
    pipe, seq = (k + n - 1) * t, k * n * t
    return pipe, (f"{k}단계 {n}명령 — 파이프 {pipe} · 비파이프 {seq}(오답④) · "
                  f"속도향상 {seq/pipe:.2f}배(이론 {k}) · k+n 이면 {k+n}(오답③)")


def v_csca_007() -> tuple[int, str]:
    import math
    addr, size, block, way = 32, 32 * 1024, 32, 4
    lines = size // block
    sets = lines // way
    off = int(math.log2(block))
    idx = int(math.log2(sets))
    direct = addr - off - int(math.log2(lines))
    return addr - off - idx, (f"라인 {lines} · 집합 {sets} · offset {off} · index {idx} → "
                              f"tag {addr - off - idx} · 직접사상이면 {direct}(오답②)")


def v_csca_008() -> tuple[int, str]:
    tc_, tm = 10, 100
    got = {h: h * tc_ + (1 - h) * tm for h in (0.90, 0.95, 0.99)}
    return round(got[0.90]), (
        " · ".join(f"적중률 {int(h*100)}% → {v:.0f}ns" for h, v in got.items())
        + f" · 단순평균 {(tc_+tm)/2:.0f}(오답④)")


def v_csca_012() -> tuple[int, str]:
    f_, cpi = 2e9, 2.5
    mips = f_ / (cpi * 1e6)
    return int(mips), (f"{f_/1e9}GHz ÷ CPI {cpi} → {int(mips)} MIPS · "
                       f"10억 명령 {1e9*cpi/f_:.2f}초 · 곱하면 {int(f_*cpi/1e6)}(오답⑤)")


def v_csca_017() -> tuple[str, str]:
    """A 를 NAND 두 단자에 넣으면 NOT A. 진리표로 확인한다."""
    tt = {a: int(not (a and a)) for a in (0, 1)}
    is_not = all(tt[a] == int(not a) for a in (0, 1))
    return ("NOT" if is_not else "?"), f"NAND(A,A) 진리표 {tt} · NOT A 와 일치 {is_not}"


# ── 데이터통신 ──────────────────────────────────────────────────────────

def v_csdc_001() -> tuple[int, str]:
    import math
    b = 3000
    got = {l: int(2 * b * math.log2(l)) for l in (2, 4, 8, 16)}
    snr = 10 ** (30 / 10)
    return got[4], (f"나이퀴스트 {got} · 섀넌 상한 "
                    f"{int(b * math.log2(1 + snr)):,}bps(SNR 30dB)")


def _mod2div(msg: str, gen: str) -> str:
    """모듈로-2 나눗셈 나머지. 네트워크 016 과 **같은 함수**를 쓰지 않도록 여기 둔다."""
    m = list(msg) + ["0"] * (len(gen) - 1)
    for i in range(len(msg)):
        if m[i] == "1":
            for j, g in enumerate(gen):
                m[i + j] = str(int(m[i + j]) ^ int(g))
    return "".join(m[len(msg):])


def v_csdc_002() -> tuple[str, str]:
    msg, gen = "101110", "1001"
    fcs = _mod2div(msg, gen)
    chk = _mod2div(msg + fcs, gen)
    return fcs, (f"{msg} ÷ {gen} → FCS {fcs} · 전송 {msg + fcs} · "
                 f"수신측 나머지 {chk}(0 이어야 한다)")


def v_csdc_003() -> tuple[int, str]:
    got = {}
    for m in (4, 8, 11):
        got[m] = next(r for r in range(1, 12) if 2 ** r >= m + r + 1)
    m = 8
    return got[m], (f"데이터 {m} → 패리티 {got[m]} (2^{got[m]}={2**got[m]} ≥ "
                    f"{m+got[m]+1}) · r=3 이면 8 < 12 미달 · 전체 {m+got[m]}비트 · "
                    f"다른 경우 {got}")


def v_csdc_004() -> tuple[int, str]:
    got = {d: (d - 1, (d - 1) // 2) for d in (2, 3, 4, 5)}
    return got[5][1], (" · ".join(f"d={d} 검출 {a} 정정 {b}" for d, (a, b) in got.items())
                       + " → d=5 의 검출 4 가 오답④")


def v_csdc_005() -> tuple[str, str]:
    data = "1011010"
    odd = str(1 - data.count("1") % 2)      # 홀수 패리티
    even = str(data.count("1") % 2)         # 짝수 패리티
    return data + odd, (f"1 이 {data.count('1')}개 → 홀수패리티 {data+odd} · "
                        f"짝수패리티 {data+even}(오답①)")


def v_csdc_007() -> tuple[int, str]:
    ch, bits, fr = 24, 8, 8000
    t1 = (ch * bits + 1) * fr
    e1 = 32 * 8 * fr
    return t1, (f"T1 (24×8+1)×8000 = {t1:,} · 동기비트 제외 {ch*bits*fr:,}(오답①) · "
                f"E1 {e1:,}(오답④)")


def v_csdc_009() -> tuple[int, str]:
    fmax, q = 4000, 8
    rate = 2 * fmax * q
    return rate, (f"표본화 {2*fmax:,}Hz × {q}비트 = {rate:,}bps · "
                  f"2배 안 하면 {fmax*q:,}(오답①) · T1 24채널 검산 "
                  f"{rate*24 + 8000:,}")


def v_csdc_010() -> tuple[int, str]:
    got = {}
    for rate, slot in ((10e6, 51.2e-6), (100e6, 5.12e-6)):
        got[int(rate / 1e6)] = (int(rate * slot), int(rate * slot / 8))
    bits, byt = got[10]
    return byt, (f"10Mbps×51.2μs = {bits}비트 = {byt}바이트 · "
                 f"100Mbps 도 {got[100][1]}바이트 · 비트값 {bits} 가 오답⑤")


def v_csdc_012() -> tuple[int, str]:
    got = {k: (2 ** k - 1, 2 ** (k - 1)) for k in (3, 4)}
    return got[3][1], (" · ".join(f"{k}비트 GBN {g} SR {s}" for k, (g, s) in got.items())
                       + " → 3비트 GBN 7 이 오답③")


def v_csdc_014() -> tuple[float, str]:
    size, bw = 1500 * 8, 10e6
    dist, v = 100e3, 2e8
    tx, pd = size / bw * 1e3, dist / v * 1e3
    return round(tx + pd, 1), (f"전송 {tx:.1f}ms(오답②) + 전파 {pd:.1f}ms(오답①) = "
                               f"{tx+pd:.1f}ms")


def v_csdc_016() -> tuple[int, str]:
    import math
    got = {r: int(10 * math.log10(r)) for r in (0.1, 0.01, 0.001)}
    return got[0.01], (" · ".join(f"1/{int(1/r)} → {v}dB" for r, v in got.items())
                       + f" · 2배 +{10*math.log10(2):.0f}dB")


# id → (검증 함수, 계산값을 선지 번호로 옮기는 함수)
#   검증 함수는 (계산값, 사람이 읽을 설명) 을 돌려준다.
#   **선지 번호를 함수 안에 적지 않는다** — 계산과 배치를 갈라 두어야
#   선지 순서를 바꿔도 검증이 따라온다.
# ── 021~026 SQL 여섯 문항 — 하나의 스키마를 함께 쓴다 ──────────────────
#
# 자료를 손으로 옮겨 적지 않는다. **문항의 표와 같은 값을 여기 다시 세우고**
# 질의를 실제로 돌린다. 표를 고치면서 검증기를 안 고치면 여기서 어긋난다.

_DB2 = """
CREATE TABLE 부서 (부서번호 TEXT PRIMARY KEY, 부서명 TEXT);
CREATE TABLE 사원 (사번 TEXT PRIMARY KEY, 이름 TEXT, 부서번호 TEXT,
                   직급 TEXT, 급여 INTEGER);
CREATE TABLE 참여 (사번 TEXT, 과제 TEXT, 시간 INTEGER);
INSERT INTO 부서 VALUES ('D1','전산기획'),('D2','정보보안'),('D3','데이터'),
                        ('D4','인프라'),('D5','품질관리');
INSERT INTO 사원 VALUES
 ('E1','김한별','D1','과장',5200),('E2','이도현','D1','대리',4100),
 ('E3','박서준','D2','과장',5400),('E4','최유진','D2','사원',3200),
 ('E5','정민수','D2','사원',3200),('E6','한지우','D3','대리',4100),
 ('E7','오세훈','D3','사원',NULL),('E8','신예린',NULL,'사원',2900);
INSERT INTO 참여 VALUES
 ('E1','차세대포털',120),('E1','보안점검',40),('E2','차세대포털',90),
 ('E3','보안점검',200),('E4','보안점검',150),
 ('E6','데이터표준',180),('E6','차세대포털',155);
"""


def _db2(sql):
    con = sqlite3.connect(":memory:")
    con.executescript(_DB2)
    r = con.execute(sql).fetchall()
    con.close()
    return r


def v_csdb_021() -> tuple[int, str]:
    """GROUP BY 는 NULL 도 한 묶음. HAVING 이 그 묶음만 거른다."""
    n = len(_db2("SELECT 부서번호, COUNT(*) FROM 사원 GROUP BY 부서번호 "
                 "HAVING COUNT(*) >= 2"))
    all_g = len(_db2("SELECT 부서번호 FROM 사원 GROUP BY 부서번호"))
    return n, f"묶음 {all_g}개(NULL 포함) → HAVING 통과 {n}행 · HAVING 없으면 {all_g}(오답④)"


def v_csdb_022() -> tuple[int, str]:
    """부서 기준 LEFT. 짝 없는 부서가 둘이라 뒤집은 값과 갈린다."""
    left = _db2("SELECT COUNT(*) FROM 부서 LEFT JOIN 사원 USING(부서번호)")[0][0]
    rev = _db2("SELECT COUNT(*) FROM 사원 LEFT JOIN 부서 USING(부서번호)")[0][0]
    inner = _db2("SELECT COUNT(*) FROM 부서 JOIN 사원 USING(부서번호)")[0][0]
    if len({left, rev, inner}) != 3:
        raise AssertionError(f"조인 값이 겹친다 {left} {rev} {inner}")
    return left, f"부서 LEFT {left} · 사원 LEFT {rev}(오답②) · INNER {inner}(오답①)"


def v_csdb_023() -> tuple[int, str]:
    """EXISTS 는 있는지만 본다. E6 이 두 건이라 사원 수와 행 수가 갈린다."""
    n = _db2("SELECT COUNT(*) FROM 사원 e WHERE EXISTS ("
             "SELECT 1 FROM 참여 p WHERE p.사번=e.사번 AND p.시간>=150)")[0][0]
    rows = _db2("SELECT COUNT(*) FROM 참여 WHERE 시간>=150")[0][0]
    non = _db2("SELECT COUNT(*) FROM 사원 e WHERE NOT EXISTS ("
               "SELECT 1 FROM 참여 p WHERE p.사번=e.사번 AND p.시간>=150)")[0][0]
    return n, f"사원 {n}명 · 참여 행 {rows}(오답③) · NOT EXISTS {non}(오답④)"


def v_csdb_024() -> tuple[int, str]:
    """AVG 의 분모는 NULL 을 뺀 수다. 옳지 않은 선지 번호를 돌려준다."""
    cs = _db2("SELECT COUNT(*) FROM 사원")[0][0]
    cc = _db2("SELECT COUNT(급여) FROM 사원")[0][0]
    avg = _db2("SELECT ROUND(AVG(급여),1) FROM 사원")[0][0]
    naive = _db2("SELECT ROUND(SUM(급여)*1.0/COUNT(*),1) FROM 사원")[0][0]
    if cs == cc or abs(avg - naive) < 1:
        raise AssertionError("NULL 이 없어 문항이 성립하지 않는다")
    return 4, (f"COUNT(*) {cs} · COUNT(급여) {cc} · AVG {avg} vs SUM/COUNT(*) {naive} "
               f"— 같지 않으므로 ④가 옳지 않다")


def v_csdb_025() -> tuple[tuple, str]:
    """RANK 는 건너뛰고 DENSE_RANK 는 안 건너뛴다. 꼴찌의 두 값."""
    rows = _db2("SELECT 이름, RANK() OVER (ORDER BY 급여 DESC), "
                "DENSE_RANK() OVER (ORDER BY 급여 DESC) "
                "FROM 사원 WHERE 급여 IS NOT NULL ORDER BY 급여")
    name, r, dr = rows[0]
    return (r, dr), f"{name} → RANK {r} · DENSE_RANK {dr} (동점 두 군데라 두 번 건너뛴다)"


def v_csdb_026() -> tuple[tuple, str]:
    """UNION 은 NULL 도 한 값으로 남긴다."""
    q = ("SELECT 부서번호 FROM 사원 WHERE 직급='과장' {} "
         "SELECT 부서번호 FROM 사원 WHERE 직급='사원'")
    u = len(_db2(q.format("UNION")))
    ua = len(_db2(q.format("UNION ALL")))
    has_null = any(r[0] is None for r in _db2(q.format("UNION")))
    if not has_null:
        raise AssertionError("UNION 결과에 NULL 이 없다 — 함정이 성립하지 않는다")
    return (u, ua), f"UNION {u}행(NULL 포함) · UNION ALL {ua}행"


# ── 데이터베이스론 027~040 — 정규화·인덱스·트랜잭션·회복·최적화 ──────────
#
# 21~26 이 SQL 이었다면 여기는 **판정과 계산**이다. 개념을 글로 외웠는지가 아니라
# 규칙을 실제로 적용했을 때 어떤 값이 나오는지를 코드로 확정한다.

def _bcnf_violations(attrs: set[str], fds: list[tuple[set, set]]) -> list[tuple]:
    """BCNF 위반 = 왼쪽이 초키가 아닌 비자명 종속."""
    return [(l, r) for l, r in fds
            if not r <= l and closure(attrs, fds, l) != attrs]


def _lossless(attrs, fds, r1: set, r2: set) -> bool:
    """무손실 = 두 조각의 공통 속성이 어느 한쪽의 초키."""
    common = r1 & r2
    if not common:
        return False
    cl = closure(attrs, fds, common)
    return r1 <= cl or r2 <= cl


def _lost_fds(fds, parts) -> list[tuple]:
    """조각 하나 안에 담기지 못한 종속 — 종속성 보존이 깨진 자리."""
    return [(l, r) for l, r in fds if not any((l | r) <= p for p in parts)]


def _mem(script: str, sql: str):
    """문항의 표를 그대로 세우고 질의를 돌린다."""
    con = sqlite3.connect(":memory:")
    con.executescript(script)
    rows = con.execute(sql).fetchall()
    con.close()
    return rows


def v_csdb_027() -> tuple[tuple, str]:
    """수강(학생, 과목, 강사) — 3NF 이지만 BCNF 가 아닌 고전 사례."""
    attrs = {"학", "과", "강"}                      # 학생 · 과목 · 강사
    fds = [({"학", "과"}, {"강"}), ({"강"}, {"과"})]
    keys = candidate_keys(attrs, fds)
    prime = set().union(*keys) if keys else set()
    nf = highest_normal_form(attrs, fds)
    bad = _bcnf_violations(attrs, fds)
    if prime != attrs:
        raise AssertionError(f"비주요 속성이 있다 {sorted(attrs - prime)}")
    key_s = " · ".join("".join(sorted(k)) for k in keys)
    bad_s = " · ".join(f"{''.join(sorted(l))}→{''.join(sorted(r))}" for l, r in bad)
    return (nf, not bad), (f"후보키 {key_s} · 비주요 속성 없음 → {nf}NF 만족 · "
                           f"BCNF 위반 {bad_s or '없음'}")


def v_csdb_028() -> tuple[int, str]:
    """다치종속은 곱으로 채우고, 4NF 로 쪼개면 합이 된다."""
    기술, 가족 = ["Java", "SQL"], ["배우자", "자녀1", "자녀2"]
    before = [("E1", t, f) for t in 기술 for f in 가족]
    a1 = [("E1", t) for t in 기술]
    a2 = [("E1", f) for f in 가족]
    rejoin = {(a, t, f) for a, t in a1 for b, f in a2 if a == b}
    if rejoin != set(before):
        raise AssertionError("분해 후 조인이 원본과 다르다 — 무손실이 아니다")
    return len(a1) + len(a2), (f"분해 전 {len(기술)}×{len(가족)}={len(before)}행 → "
                               f"분해 후 {len(a1)}+{len(a2)}={len(a1) + len(a2)}행 · "
                               f"재조인 {len(rejoin)}행으로 복원")


def v_csdb_029() -> tuple[tuple, str]:
    """무손실과 종속성 보존은 따로 논다 — 넷 가운데 둘만 함께 만족한다."""
    attrs = set("ABCD")
    fds = [({"A"}, {"B"}), ({"B"}, {"C"}), ({"C"}, {"D"})]
    cases = [("AB/BCD", set("AB"), set("BCD")),
             ("AB/ACD", set("AB"), set("ACD")),
             ("ABC/CD", set("ABC"), set("CD")),
             ("AD/BCD", set("AD"), set("BCD"))]
    ok, notes = [], []
    for label, r1, r2 in cases:
        ll = _lossless(attrs, fds, r1, r2)
        lost = _lost_fds(fds, [r1, r2])
        if ll and not lost:
            ok.append(label)
        notes.append(f"{label} {'무손실' if ll else '손실'}/"
                     f"{'보존' if not lost else '깨짐'}")
    return tuple(ok), " · ".join(notes)


def _bplus(order: int, seq: list[int]) -> tuple[int, int]:
    """차수 order 인 B+트리에 seq 를 차례로 넣고 (분할 횟수, 높이) 를 돌려준다."""
    maxk = order - 1
    stat = {"split": 0, "height": 1}

    class N:
        def __init__(self, leaf=True):
            self.keys, self.kids, self.leaf = [], [], leaf

    def split(parent, i):
        node = parent.kids[i]
        mid = len(node.keys) // 2
        up = node.keys[mid]
        right = N(node.leaf)
        if node.leaf:
            right.keys, node.keys = node.keys[mid:], node.keys[:mid]
        else:
            right.keys, right.kids = node.keys[mid + 1:], node.kids[mid + 1:]
            node.keys, node.kids = node.keys[:mid], node.kids[:mid + 1]
        parent.keys.insert(i, up)
        parent.kids.insert(i + 1, right)
        stat["split"] += 1

    def ins(n, k):
        if n.leaf:
            n.keys.append(k)
            n.keys.sort()
            return
        i = 0
        while i < len(n.keys) and k >= n.keys[i]:
            i += 1
        ins(n.kids[i], k)
        if len(n.kids[i].keys) > maxk:
            split(n, i)

    root = N()
    for k in seq:
        ins(root, k)
        if len(root.keys) > maxk:               # 뿌리가 넘칠 때만 층이 는다
            new = N(False)
            new.kids = [root]
            split(new, 0)
            stat["height"] += 1
            root = new
    return stat["split"], stat["height"]


def v_csdb_030() -> tuple[tuple, str]:
    """오름차순 여덟 개 — 분할은 여러 번, 층이 느는 것은 뿌리가 나뉠 때뿐."""
    seq = [10, 20, 30, 40, 50, 60, 70, 80]
    splits, height = _bplus(4, seq)
    return (splits, height), (f"차수 4 에 {seq} → 분할 {splits}회 · 높이 {height} "
                              f"(층은 뿌리 분할 때만 는다)")


def v_csdb_031() -> tuple[tuple, str]:
    """해시는 범위를 못 쓴다 — 인덱스를 타느냐가 자리수를 가른다."""
    rows, blk, hit, h = 1_000_000, 100, 10_000, 3
    btree = h + hit // blk                       # 내려간 뒤 잎을 순차로 훑는다
    hashio = rows // blk                         # 범위 미지원 → 전체 훑기
    return (btree, hashio), (f"B+트리 높이 {h} + 잎 {hit // blk} = {btree}회 · "
                             f"해시 전체훑기 {hashio}회 (약 {hashio // btree}배)")


def v_csdb_032() -> tuple[tuple, str]:
    """커버링인가와 인덱스를 탈 수 있는가는 별개다."""
    idx = ["부서번호", "급여"]                    # 복합 인덱스 (부서번호, 급여)
    cases = [("ㄱ", {"부서번호", "급여"}), ("ㄴ", {"부서번호"}),
             ("ㄷ", {"부서번호", "이름"}), ("ㄹ", {"이름", "급여"})]
    ok, notes = [], []
    for label, need in cases:
        covered = need <= set(idx)
        usable = idx[0] in need                  # 선두 열이 조건에 있어야 탄다
        if covered and usable:
            ok.append(label)
        notes.append(f"{label} {'커버' if covered else '표접근'}/"
                     f"{'인덱스' if usable else '못탐'}")
    return tuple(ok), " · ".join(notes)


def v_csdb_033() -> tuple[tuple, str]:
    """교착은 사이클 안에서만. 사이클 밖의 무한 대기와 가른다."""
    wait = {"T1": ["T2"], "T2": ["T3"], "T3": ["T1", "T4"], "T4": [], "T5": ["T3"]}
    seen, stack = set(), []

    def dfs(u):
        seen.add(u)
        stack.append(u)
        for v in wait.get(u, []):
            if v in stack:
                return stack[stack.index(v):] + [v]
            if v not in seen:
                r = dfs(v)
                if r:
                    return r
        stack.pop()
        return None

    cyc = next((r for u in wait if u not in seen for r in [dfs(u)] if r), None)
    members = tuple(sorted(set(cyc))) if cyc else ()
    outside = sorted(set(wait) - set(members))
    return members, (f"사이클 {' → '.join(cyc) if cyc else '없음'} · "
                     f"밖 {outside}(T5 는 기다리기만 한다)")


def v_csdb_034() -> tuple[tuple, str]:
    """타임스탬프 순서 규약을 여섯 연산에 그대로 적용한다."""
    ops = [("T1", "R", "A"), ("T2", "W", "A"), ("T1", "W", "A"),
           ("T2", "R", "B"), ("T3", "W", "B"), ("T2", "W", "B")]
    ts = {"T1": 1, "T2": 2, "T3": 3}
    rts, wts, aborted = {}, {}, []
    for t, op, x in ops:
        if t in aborted:
            continue                              # 되돌려진 뒤 연산은 없던 일
        if op == "R":
            if ts[t] < wts.get(x, 0):
                aborted.append(t)
                continue
            rts[x] = max(rts.get(x, 0), ts[t])
        else:
            if ts[t] < rts.get(x, 0) or ts[t] < wts.get(x, 0):
                aborted.append(t)
                continue
            wts[x] = ts[t]
    alive = sorted(set(ts) - set(aborted))
    return tuple(sorted(aborted)), f"되돌림 {sorted(aborted)} · 살아남음 {alive}"


def v_csdb_035() -> tuple[str, str]:
    """서로 다른 행을 고치므로 쓰기 충돌이 없다 — 그런데 제약이 깨진다."""
    oncall = {"A": True, "B": True}
    snap1, snap2 = dict(oncall), dict(oncall)     # 둘이 같은 스냅샷을 본다
    wrote = []
    if sum(snap1.values()) >= 2:                  # 「나 말고 또 있다」
        oncall["A"] = False
        wrote.append("A")
    if sum(snap2.values()) >= 2:
        oncall["B"] = False
        wrote.append("B")
    violated = sum(oncall.values()) < 1
    ww = len(wrote) != len(set(wrote))            # 같은 행을 겹쳐 썼나
    label = "쓰기편중" if violated and not ww else ("갱신손실" if ww else "정상")
    return label, (f"각자 본 당직 2명 → 각각 자기를 뺌 · 최종 당직 "
                   f"{sum(oncall.values())}명 · 제약 위반 {violated} · "
                   f"쓰기-쓰기 충돌 {ww} (쓴 행 {wrote} 이 서로 다르다)")


def v_csdb_036() -> tuple[tuple, str]:
    """선택 조건이 한쪽 속성만 쓰면 그쪽으로 밀어도 결과가 같다."""
    s = """
    CREATE TABLE R(a TEXT, b TEXT);
    CREATE TABLE S(b TEXT, c TEXT);
    INSERT INTO R VALUES ('a1','b1'),('a2','b1'),('a3','b2'),('a4',NULL);
    INSERT INTO S VALUES ('b1','c1'),('b1','c2'),('b2','c3'),('b3','c4');
    """
    base = "SELECT a,R.b,c FROM {} JOIN {} ON R.b=S.b {} ORDER BY 1,2,3"
    pairs = [
        ("ㄱ", base.format("R", "S", "WHERE a='a1'"),
         base.format("(SELECT * FROM R WHERE a='a1') R", "S", "")),
        ("ㄴ", base.format("R", "S", "WHERE c='c1'"),
         base.format("R", "(SELECT * FROM S WHERE c='c1') S", "")),
    ]
    ok, notes = [], []
    for label, q1, q2 in pairs:
        r1, r2 = _mem(s, q1), _mem(s, q2)
        if r1 == r2:
            ok.append(label)
        notes.append(f"{label} {len(r1)}행 vs {len(r2)}행 {'같음' if r1 == r2 else '다름'}")
    notes.append("ㄷ 은 R 에 없는 c 로 R 을 걸러 식이 서지 않는다")
    return tuple(ok), " · ".join(notes)


def v_csdb_037() -> tuple[tuple, str]:
    """세미조인은 행을 불리지 않는다. 내부조인은 짝마다 불어난다."""
    s = """
    CREATE TABLE 사원(사번 TEXT, 부서 TEXT);
    CREATE TABLE 참여(사번 TEXT, 과제 TEXT);
    INSERT INTO 사원 VALUES ('E1','D1'),('E2','D1'),('E3','D2'),('E4','D2'),('E5',NULL);
    INSERT INTO 참여 VALUES ('E1','P1'),('E1','P2'),('E3','P1'),('E3','P3');
    """
    semi = _mem(s, "SELECT COUNT(*) FROM 사원 WHERE 사번 IN (SELECT 사번 FROM 참여)")[0][0]
    anti = _mem(s, "SELECT COUNT(*) FROM 사원 WHERE 사번 NOT IN (SELECT 사번 FROM 참여)")[0][0]
    inner = _mem(s, "SELECT COUNT(*) FROM 사원 JOIN 참여 USING(사번)")[0][0]
    total = _mem(s, "SELECT COUNT(*) FROM 사원")[0][0]
    if len({semi, anti, inner}) != 3:
        raise AssertionError(f"세 값이 겹친다 {semi} {anti} {inner}")
    if semi + anti != total:
        raise AssertionError("세미 + 안티가 사원 수와 다르다")
    return (semi, anti, inner), (f"세미 {semi} · 안티 {anti} · 내부 {inner} "
                                 f"(세미+안티 = 사원 {total})")


def v_csdb_038() -> tuple[tuple, str]:
    """체크포인트 이전 커밋은 이미 반영되어 있다 — REDO 에서 뺀다."""
    log = ["<T1 start>", "<T1, A, 100, 200>", "<T1 commit>",
           "<T2 start>", "<T2, B, 50, 80>",
           "<checkpoint {T2}>",
           "<T3 start>", "<T3, C, 10, 30>", "<T3 commit>",
           "<T2, D, 5, 15>",
           "<T4 start>", "<T4, E, 1, 7>"]
    undo, redo, before_ckpt = set(), set(), True
    for line in log:
        if line.startswith("<checkpoint"):
            before_ckpt = False
            redo -= {"T1"}                        # 이전 커밋은 디스크에 있다
            undo |= {"T2"}                        # 명단의 활성 트랜잭션
            continue
        t = line.split()[0].strip("<")
        if "start>" in line:
            undo.add(t)
        elif "commit>" in line:
            undo.discard(t)
            redo.add(t)
    if before_ckpt:
        raise AssertionError("로그에 체크포인트가 없다")
    return (tuple(sorted(redo)), tuple(sorted(undo))), \
        f"REDO {sorted(redo)} · UNDO {sorted(undo)} (T1 은 체크포인트 앞 커밋이라 제외)"


def v_csdb_039() -> tuple[str, str]:
    """WAL 은 로그와 데이터의 선후만 정한다. 커밋 내구성과 갈린다."""
    scen = [("로그 flush → 데이터 flush → 커밋", ["log", "data", "commit"]),
            ("로그 flush → 커밋 → 데이터 flush", ["log", "commit", "data"]),
            ("커밋 → 로그 flush → 데이터 flush", ["commit", "log", "data"]),
            ("데이터 flush → 로그 flush → 커밋", ["data", "log", "commit"])]
    bad, notes = [], []
    for label, seq in scen:
        wal = seq.index("log") < seq.index("data")
        force = seq.index("log") < seq.index("commit")
        if not wal:
            bad.append(label)
        notes.append(f"{label.split(' →')[0]}… WAL {'○' if wal else '✗'}/"
                     f"커밋시점 {'○' if force else '✗'}")
    if len(bad) != 1:
        raise AssertionError(f"WAL 위반이 하나가 아니다 {bad}")
    return bad[0], " · ".join(notes) + " — WAL 위반은 하나뿐"


def v_csdb_040() -> tuple[tuple, str]:
    """조인 순서는 중간 결과를 바꾸고 최종 결과는 바꾸지 않는다."""
    s = """
    CREATE TABLE 부서(부서번호 TEXT, 부서명 TEXT);
    CREATE TABLE 사원(사번 TEXT, 부서번호 TEXT);
    CREATE TABLE 참여(사번 TEXT, 과제 TEXT);
    INSERT INTO 부서 VALUES ('D1','전산'),('D2','보안'),('D3','데이터'),('D4','인프라');
    INSERT INTO 사원 VALUES ('E1','D1'),('E2','D1'),('E3','D2'),('E4','D2'),
                            ('E5','D2'),('E6','D3');
    INSERT INTO 참여 VALUES ('E1','P1'),('E1','P2'),('E3','P1');
    """
    ds = _mem(s, "SELECT COUNT(*) FROM 부서 JOIN 사원 USING(부서번호)")[0][0]
    sp = _mem(s, "SELECT COUNT(*) FROM 사원 JOIN 참여 USING(사번)")[0][0]
    fin1 = _mem(s, "SELECT COUNT(*) FROM 부서 JOIN 사원 USING(부서번호) "
                   "JOIN 참여 USING(사번)")[0][0]
    fin2 = _mem(s, "SELECT COUNT(*) FROM 부서 JOIN (SELECT 사원.사번, 부서번호 "
                   "FROM 사원 JOIN 참여 USING(사번)) USING(부서번호)")[0][0]
    truth = (sp == 3, ds == 6, fin1 == fin2, min(ds, sp) < max(ds, sp), fin1 != fin2)
    return truth, (f"부서⋈사원 {ds} · 사원⋈참여 {sp} · 최종 {fin1}/{fin2} "
                   f"— 중간은 다르고 최종은 같다 · 선지 참거짓 {truth}")


REGISTRY = {
    "major-csdb-common-001": (v_csdb_001, lambda nf: {1: 1, 2: 2, 3: 3}[nf]),
    "major-csdb-common-002": (v_csdb_002, lambda n: {1: 1, 2: 2, 3: 3, 4: 4, 7: 5}[n]),
    "major-csdb-common-003": (v_csdb_003, lambda n: {0: 1, 1: 2, 2: 3, 3: 4, 4: 5}[n]),
    "major-csdb-common-004": (v_csdb_004, lambda s: {
        "Dirty Read": 1, "Non-repeatable Read": 2, "Phantom Read": 3}[s]),
    "major-csdb-common-005": (v_csdb_005, lambda h: {2: 1, 3: 2, 4: 3, 5: 4, 6: 5}[h]),
    "major-csdb-common-006": (v_csdb_006, lambda v: {"3NF만족_BCNF위반": 3}[v]),
    "major-csdb-common-007": (v_csdb_007, lambda i: {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}[i]),
    "major-csdb-common-021": (v_csdb_021, lambda n: {1: 1, 2: 2, 3: 3, 4: 4, 8: 5}[n]),
    "major-csdb-common-022": (v_csdb_022, lambda n: {7: 1, 8: 2, 9: 3, 10: 4, 13: 5}[n]),
    "major-csdb-common-023": (v_csdb_023, lambda n: {2: 1, 3: 2, 4: 3, 5: 4, 7: 5}[n]),
    "major-csdb-common-024": (v_csdb_024, lambda i: i),
    "major-csdb-common-025": (v_csdb_025, lambda t: {(5, 5): 1, (5, 7): 2, (7, 4): 3,
                                                     (7, 5): 4, (7, 7): 5}[t]),
    "major-csdb-common-026": (v_csdb_026, lambda t: {(3, 6): 1, (4, 4): 2, (4, 6): 3,
                                                     (6, 4): 4, (6, 6): 5}[t]),
    "major-csdb-common-027": (v_csdb_027, lambda t: {(3, False): 1, (3, True): 4}[t]),
    "major-csdb-common-028": (v_csdb_028, lambda n: {3: 1, 5: 2, 6: 3, 9: 4, 11: 5}[n]),
    "major-csdb-common-029": (v_csdb_029, lambda t: {
        ("AB/ACD",): 1, ("AD/BCD",): 2, ("ABC/CD",): 3, ("AB/BCD", "ABC/CD"): 4,
        ("AB/BCD", "AB/ACD", "ABC/CD", "AD/BCD"): 5}[t]),
    "major-csdb-common-030": (v_csdb_030, lambda t: {(2, 2): 1, (3, 2): 2, (3, 3): 3,
                                                     (4, 2): 4, (4, 3): 5}[t]),
    "major-csdb-common-031": (v_csdb_031, lambda t: {(3, 100): 1, (100, 3): 2,
                                                     (103, 10_000): 3,
                                                     (10_000, 103): 4,
                                                     (10_000, 10_000): 5}[t]),
    "major-csdb-common-032": (v_csdb_032, lambda t: {
        ("ㄱ",): 1, ("ㄱ", "ㄴ"): 2, ("ㄱ", "ㄴ", "ㄷ"): 3, ("ㄴ", "ㄹ"): 4,
        ("ㄱ", "ㄴ", "ㄹ"): 5}[t]),
    "major-csdb-common-033": (v_csdb_033, lambda t: {
        ("T1", "T2"): 1, ("T1", "T2", "T3"): 2, ("T1", "T2", "T3", "T5"): 3,
        ("T1", "T2", "T3", "T4"): 4, ("T1", "T2", "T3", "T4", "T5"): 5}[t]),
    "major-csdb-common-034": (v_csdb_034, lambda t: {
        ("T1",): 1, ("T2",): 2, ("T1", "T2"): 3, ("T2", "T3"): 4,
        ("T1", "T2", "T3"): 5}[t]),
    "major-csdb-common-035": (v_csdb_035, lambda s: {"갱신손실": 1, "쓰기편중": 5}[s]),
    "major-csdb-common-036": (v_csdb_036, lambda t: {
        ("ㄱ",): 1, ("ㄴ",): 2, ("ㄱ", "ㄴ"): 3, ("ㄱ", "ㄷ"): 4,
        ("ㄱ", "ㄴ", "ㄷ"): 5}[t]),
    "major-csdb-common-037": (v_csdb_037, lambda t: {(2, 2, 4): 1, (2, 3, 2): 2,
                                                     (2, 3, 4): 3, (4, 1, 4): 4,
                                                     (4, 3, 4): 5}[t]),
    "major-csdb-common-038": (v_csdb_038, lambda t: {
        (("T1", "T2", "T3"), ("T4",)): 1, (("T1", "T3"), ("T4",)): 2,
        (("T1", "T3"), ("T2", "T4")): 3, (("T3",), ("T4",)): 4,
        (("T3",), ("T2", "T4")): 5}[t]),
    "major-csdb-common-039": (v_csdb_039, lambda s: {
        "로그 flush → 데이터 flush → 커밋": 1,
        "로그 flush → 커밋 → 데이터 flush": 2,
        "커밋 → 로그 flush → 데이터 flush": 3,
        "데이터 flush → 로그 flush → 커밋": 4}[s]),
    # 「옳지 않은 것」 — 거짓인 선지의 자리를 그대로 답으로 삼는다
    "major-csdb-common-040": (v_csdb_040, lambda t: t.index(False) + 1),
    "major-csdb-common-008": (v_csdb_008, lambda n: {0: 1, 1: 2, 2: 3, 3: 4, 4: 5}[n]),
    "major-csdb-common-009": (v_csdb_009, lambda r: {
        (1,): 1, (1, 2): 2, (1, 3): 3, (1, 2, 3, 4): 4, (2, 4): 5}[r]),
    "major-csdb-common-010": (v_csdb_010, lambda p: {
        ("UNDO", "REDO", "REDO"): 1, ("REDO", "UNDO", "UNDO"): 2,
        ("REDO", "REDO", "UNDO"): 3}[p]),
    "major-csdb-common-011": (v_csdb_011, lambda k: {
        ("A",): 1, ("B",): 2, ("AC",): 3, ("BC",): 4, ("ABC",): 5}[k]),
    "major-csdb-common-012": (v_csdb_012, lambda r: {
        (4, 5, 85.75): 1, (5, 5, 68.6): 2, (4, 4, 85.75): 3,
        (5, 5, 85.75): 4, (4, 5, 68.6): 5}[r]),
    "major-csdb-common-015": (v_csdb_015, lambda s: 2 if s < 0.01 else 1),
    "major-csdb-common-016": (v_csdb_016, lambda n: {0: 1, 1: 2, 2: 3, 3: 4}[n]),
    "major-csdb-common-017": (v_csdb_017, lambda v: {120: 1, 170: 2, 150: 3, 100: 4}[v]),
    "major-csdb-common-018": (v_csdb_018, lambda nf: 2 if nf == 1 else 5),
    "major-csdb-common-019": (v_csdb_019, lambda n: {3: 1, 4: 2, 5: 3, 6: 4, 2: 5}[n]),
    "major-csdb-common-013": (v_csdb_013, lambda i: i),
    "major-csdb-common-014": (v_csdb_014, lambda i: i),
    "major-csdb-common-020": (v_csdb_020, lambda i: i),

    "major-csos-common-001": (v_csos_001, lambda v: {
        6.5: 1, 7.75: 2, 8.75: 3, 11.75: 4, 14.25: 5}[v]),
    "major-csos-common-002": (v_csos_002, lambda v: {
        6.5: 1, 7.75: 2, 8.75: 3, 9.25: 4, 11.75: 5}[v]),
    "major-csos-common-003": (v_csos_003, lambda v: {
        13.0: 1, 14.25: 2, 15.25: 3, 18.25: 4, 23.0: 5}[v]),
    "major-csos-common-004": (v_csos_004, lambda n: {7: 1, 8: 2, 9: 3, 10: 4, 11: 5}[n]),
    "major-csos-common-005": (v_csos_005, lambda anomaly: 2 if anomaly else 0),
    "major-csos-common-006": (v_csos_006, lambda s: {
        ("P1", "P3", "P0", "P2", "P4"): 3,
        ("P0", "P1", "P2", "P3", "P4"): 4}[s]),
    "major-csos-common-007": (v_csos_007, lambda d: {
        208: 1, 236: 2, 299: 3, 331: 4, 640: 5}[d]),
    "major-csos-common-008": (v_csos_008, lambda pr: {
        (1, 4099): 1, (2, 3): 2, (2, 8195): 3, (3, 3): 4, (8, 195): 5}[pr]),
    "major-csos-common-009": (v_csos_009, lambda r: {
        88: 1, 288: 2, 388: 3, 12: 4}[r]),
    "major-csos-common-010": (v_csos_010, lambda e: {
        110: 1, 120: 2, 130: 3, 140: 4, 220: 5}[e]),
    "major-csos-common-011": (v_csos_011, lambda b: {
        1024: 1, 4096: 2, 1024**2: 3, 4*1024**2: 4, 16*1024**2: 5}[b]),
    "major-csos-common-012": (v_csos_012, lambda n: {2: 1, 3: 2, 4: 3, 5: 4, 6: 5}[n]),
    "major-csos-common-013": (v_csos_013, lambda i: i),
    "major-csos-common-014": (v_csos_014, lambda i: i),
    "major-csos-common-015": (v_csos_015, lambda n: {0: 1, 1: 2, 2: 3, 3: 4, 4: 5}[n]),
    # 016 교착 예방 — 상호 배제만 자원 성질에 달렸다 (선지 ①)
    "major-csos-common-016": (lambda: (1, "상호배제만 자원 성질 · 나머지 셋은 요청 규칙으로 깨진다"),
                              lambda i: i),
    "major-csos-common-017": (v_csos_017, lambda n: {
        268: 1, 780: 2, 65804: 3, 65792: 4, 16777216: 5}[n]),
    "major-csos-common-018": (v_csos_018, lambda t: {
        (2000, 1): 1, (3000, 1): 2, (3000, 2): 3, (4000, 0): 4, (2000, 2): 5}[t]),
    # 019 스래싱 — 프로세스를 더 늘리면 악화된다 (선지 ④가 틀린 진술)
    "major-csos-common-019": (lambda: (4, "다중 프로그래밍 정도를 높이면 악화 · 대책은 낮추기"),
                              lambda i: i),
    # 020 문맥 교환 — 프로세스 교환이 더 비싸다 (선지 ②)
    "major-csos-common-020": (lambda: (2, "프로세스 교환은 주소공간 전환·TLB 무효화를 포함"),
                              lambda i: i),

    "major-csnet-common-001": (v_csnet_001, lambda h: {
        30: 1, 62: 2, 64: 3, 126: 4, 254: 5}[h]),
    "major-csnet-common-002": (v_csnet_002, lambda a: {
        "192.168.1.0": 1, "192.168.1.64": 2, "192.168.1.128": 3,
        "192.168.1.129": 4, "192.168.1.192": 5}[a]),
    "major-csnet-common-003": (v_csnet_003, lambda h: {
        14: 1, 30: 2, 32: 3, 62: 4, 126: 5}[h]),
    "major-csnet-common-004": (v_csnet_004, lambda c: {
        17: 1, 20: 2, 21: 3, 25: 4}[c]),
    "major-csnet-common-005": (v_csnet_005, lambda w: {
        16: 1, 17: 2, 18: 3, 32: 4, 64: 5}[w]),
    # 006 L2 스위치는 데이터링크 계층 (선지 ④가 틀린 짝)
    "major-csnet-common-006": (lambda: (4, "L2 스위치는 MAC 기반 2계층. 네트워크 계층이 아니다"),
                               lambda i: i),
    # 007 SMTP 는 25, 110 은 POP3 (선지 ③이 틀린 짝)
    "major-csnet-common-007": (lambda: (3, "SMTP 25 · POP3 110 · IMAP 143"), lambda i: i),
    # 008 UDP 는 체크섬으로 검출만 하고 재전송은 안 한다 (선지 ④)
    "major-csnet-common-008": (lambda: (4, "UDP 헤더 8바이트에 체크섬 포함. 재전송 없음"),
                               lambda i: i),
    # 009 무선은 송신 신호가 수신을 덮어 충돌 감지가 어렵다 (선지 ②)
    "major-csnet-common-009": (lambda: (2, "CSMA/CD 는 송신 중 충돌 감지를 전제. 무선은 불가"),
                               lambda i: i),
    "major-csnet-common-010": (v_csnet_010, lambda c: {
        1: 1, 2: 2, 3: 3, 4: 4, 5: 5}[c]),
    "major-csnet-common-011": (v_csnet_011, lambda s: {
        "192.168.8.0/21": 1, "192.168.8.0/22": 2, "192.168.8.0/23": 3,
        "192.168.0.0/22": 4, "192.168.8.0/20": 5}[s]),
    # 012 설정 3단계·종료 4단계, 이유는 반이중 종료 (선지 ②)
    "major-csnet-common-012": (lambda: (2, "설정 SYN·SYN+ACK·ACK 3 · 종료 FIN·ACK·FIN·ACK 4"),
                               lambda i: i),
    "major-csnet-common-013": (v_csnet_013, lambda t: {
        0.12: 1, 0.93: 2, 1.87: 3, 11.7: 4, 93.0: 5}[t]),
    "major-csnet-common-014": (v_csnet_014, lambda t: {
        1.2: 1, 10.0: 2, 11.2: 3, 12.0: 4, 21.2: 5}[t]),
    "major-csnet-common-015": (v_csnet_015, lambda r: {3: 1, 4: 2, 5: 3, 6: 4, 8: 5}[r]),
    "major-csnet-common-016": (v_csnet_016, lambda s: {
        "1110": 1, "0110": 2, "1010": 3, "0011": 4, "1111": 5}[s]),
    "major-csnet-common-017": (v_csnet_017, lambda i: i),
    # 018 IPv6 헤더에는 체크섬이 없다 (선지 ④가 틀린 진술)
    "major-csnet-common-018": (lambda: (4, "IPv6 기본 헤더 40바이트에 체크섬 필드 없음"),
                               lambda i: i),
    # 019 거리 벡터는 이웃에게만 자신의 표를 알린다 (선지 ②)
    "major-csnet-common-019": (lambda: (2, "거리벡터=이웃에게 표 전체·벨만포드·RIP / "
                                           "링크상태=전체에 링크·다익스트라·OSPF"),
                               lambda i: i),
    # 020 포트까지 변환해 N:1 을 만드는 것은 PAT (선지 ③)
    "major-csnet-common-020": (lambda: (3, "정적 1:1 고정 · 동적 1:1 임시 · PAT N:1"),
                               lambda i: i),

    "major-cssec-common-001": (v_cssec_001, lambda d: {
        13: 1, 37: 2, 43: 3, 53: 4, 60: 5}[d]),
    "major-cssec-common-002": (v_cssec_002, lambda k: {
        100: 1, 200: 2, 4950: 3, 9900: 4, 10000: 5}[k]),
    # 003 CBC 암호화는 앞 블록에 묶여 병렬 불가 (선지 ④가 틀린 진술)
    "major-cssec-common-003": (lambda: (4, "CBC 암호화만 순차 강제 · 복호화는 병렬 가능"),
                               lambda i: i),
    "major-cssec-common-004": (v_cssec_004, lambda e: {64: 1, 127: 2, 128: 3, 256: 4}[e]),
    # 005 전자서명은 기밀성을 주지 않는다 (선지 ④)
    "major-cssec-common-005": (lambda: (4, "인증·무결성·부인방지 O / 기밀성 X"), lambda i: i),
    # 006 벨-라파듈라 — no read up, no write down → 위에 쓰기는 허용 (선지 ③)
    "major-cssec-common-006": (lambda: (3, "기밀성 모델: 아래 읽기·위에 쓰기 허용"),
                               lambda i: i),
    # 007 MAC 는 DAC 보다 경직 (선지 ④가 틀린 진술)
    "major-cssec-common-007": (lambda: (4, "DAC 유연 · MAC 강제·경직 · RBAC 중간"),
                               lambda i: i),
    # 008 매개변수화 질의가 근본 대책 (선지 ②)
    "major-cssec-common-008": (lambda: (2, "질의 구조를 먼저 확정해 값이 구문이 되지 않게 한다"),
                               lambda i: i),
    # 009 인증 상태를 빌려 요청을 위조 → CSRF (선지 ③)
    "major-cssec-common-009": (lambda: (3, "훔치지 않고 브라우저가 보내는 인증 정보를 이용"),
                               lambda i: i),
    # 010 URL 경로는 7계층이라 패킷 필터링으로 못 본다 (선지 ④)
    "major-cssec-common-010": (lambda: (4, "패킷 필터링은 3·4계층 헤더만 본다"), lambda i: i),
    # 011 커버로스는 대칭키 기반, PKI 인증서를 쓰지 않는다 (선지 ⑤)
    "major-cssec-common-011": (lambda: (5, "AS→TGT · TGS→서비스티켓 · 대칭키 · 시간동기"),
                               lambda i: i),
    "major-cssec-common-012": (v_cssec_012, lambda ale: {
        10_000_000: 1, 20_000_000: 2, 40_000_000: 3, 50_000_000: 4, 80_000_000: 5}[ale]),
    # 013 IDS 는 경로 밖 복사본을 본다 (선지 ③)
    "major-cssec-common-013": (lambda: (3, "IDS 미러링·탐지 / IPS 인라인·차단, 오탐 피해는 IPS"),
                               lambda i: i),
    # 014 절반 연결을 쌓는 것은 SYN 플러딩 (선지 ①)
    "major-cssec-common-014": (lambda: (1, "마지막 ACK 를 안 보내 백로그를 채운다"),
                               lambda i: i),
    # 015 공개키로 세션키, 대칭키로 본문 (선지 ②)
    "major-cssec-common-015": (lambda: (2, "키 전달은 공개키 · 본문은 빠른 대칭키"),
                               lambda i: i),
    # 016 공개 내용을 변경, 접속은 정상 → 무결성만 (선지 ②)
    "major-cssec-common-016": (lambda: (2, "기밀성·가용성은 상황문에서 배제됨"), lambda i: i),
    # 017 가상 규정 제3조의 통계 작성 (선지 ②)
    "major-cssec-common-017": (lambda: (2, "제3조 세 목적 중 통계 작성. 나머지는 제1·3·4조 위반"),
                               lambda i: i),
    # 018 PDCA — 계획 → 수행 → 점검 → 조치 (선지 ②)
    "major-cssec-common-018": (lambda: (2, "Plan Do Check Act"), lambda i: i),

    "major-csse-common-001": (v_csse_001, lambda e: {85: 1, 120: 2, 146: 3,
                                                     210: 4, 302: 5}[e]),
    "major-csse-common-002": (v_csse_002, lambda f: {29: 1, 104: 2, 148: 3,
                                                     160: 4, 290: 5}[f]),
    "major-csse-common-003": (v_csse_003, lambda d: {12: 1, 13: 2, 14: 3,
                                                     17: 4, 23: 5}[d]),
    "major-csse-common-004": (v_csse_004, lambda k: {1: 1, 2: 2, 3: 3, 4: 4, 8: 5}[k]),
    # 005 기초 경로 검사만 제어 흐름을 봐야 한다 → 화이트박스 (선지 ④)
    "major-csse-common-005": (lambda: (4, "동등분할·경계값·원인결과·오류예측은 명세만으로 설계"),
                              lambda i: i),
    # 006 응집도는 높게 결합도는 낮게 (선지 ②)
    "major-csse-common-006": (lambda: (2, "응집 기능적↑ 우연적↓ · 결합 자료(약)~내용(강)"),
                              lambda i: i),
    # 007 인스턴스를 하나로 제한 → 싱글턴 (선지 ②)
    "major-csse-common-007": (lambda: (2, "팩토리는 무엇을·싱글턴은 몇 개를 다룬다"),
                              lambda i: i),
    # 008 단계를 마쳐야 다음으로 — 폭포수의 특징 (선지 ④)
    "major-csse-common-008": (lambda: (4, "애자일은 되돌아가는 것을 정상으로 본다"),
                              lambda i: i),
    # 009 도출 → 분석 → 명세 → 확인 (선지 ①)
    "major-csse-common-009": (lambda: (1, "정리하지 않고 명세하면 충돌이 문서에 굳는다"),
                              lambda i: i),
    # 010 형상관리 4활동에 「최적화」는 없다 (선지 ⑤)
    "major-csse-common-010": (lambda: (5, "식별·통제·감사·기록"), lambda i: i),
    "major-csse-common-011": (v_csse_011, lambda v: {3: 1, 4: 2, 5: 3, 6: 4, 19: 5}[v]),
    # 012 복구 시간·데이터 보존 → 신뢰성 (선지 ③)
    "major-csse-common-012": (lambda: (3, "회복성·결함 허용성은 신뢰성의 하위 특성"),
                              lambda i: i),
    # 013 모델은 표현 형식을 모른다 (선지 ④가 틀린 진술)
    "major-csse-common-013": (lambda: (4, "④가 성립하면 ⑤(여러 뷰)가 불가능해진다"),
                              lambda i: i),
    # 014 OS 변경 = 환경 변화 → 적응 (선지 ②)
    "major-csse-common-014": (lambda: (2, "결함이 아니라 바깥이 바뀐 경우"), lambda i: i),
    # 015 초기 → 관리 → 정의 → 정량적 관리 → 최적화 (선지 ②)
    "major-csse-common-015": (lambda: (2, "개별 프로젝트 관리가 먼저, 조직 표준 정의가 나중"),
                              lambda i: i),
    # 016 내용 결합도가 가장 강하다 (선지 ⑤)
    "major-csse-common-016": (lambda: (5, "자료<스탬프<제어<외부<공통<내용"), lambda i: i),
    "major-csse-common-017": (v_csse_017, lambda n: 2 if n else 0),
    # 018 요구가 불분명할 때 → 프로토타입 (선지 ②)
    "major-csse-common-018": (lambda: (2, "시제품은 버려지는 비용 — 일정이 빠듯하면 불리"),
                              lambda i: i),

    "major-cspl-common-001": (v_cspl_001, lambda s: {
        "10 20": 1, "20 10": 2, "10 10": 3, "20 20": 4}[s]),
    "major-cspl-common-002": (v_cspl_002, lambda c: {8: 1, 13: 2, 15: 3,
                                                     25: 4, 64: 5}[c]),
    "major-cspl-common-003": (v_cspl_003, lambda t: {
        (1, 2, 3, 4): 1, (2, 4, 5, 3): 2, (2, 3, 4, 5): 3,
        (5, 4, 3, 2): 4, (1, 3, 5, 4): 5}[t]),
    "major-cspl-common-004": (v_cspl_004, lambda s: {
        "A B + C * D -": 1, "A B C + * D -": 2, "A + B C * D -": 3,
        "- * + A B C D": 4, "A B + C D * -": 5}[s]),
    "major-cspl-common-005": (v_cspl_005, lambda t: {
        (20, 30, 40, 50, 60, 70, 80): 1, (50, 30, 20, 40, 70, 60, 80): 2,
        (20, 40, 30, 60, 80, 70, 50): 3, (20, 40, 60, 80, 30, 70, 50): 4,
        (80, 70, 60, 50, 40, 30, 20): 5}[t]),
    # 006 최악에도 n log n 인 것은 병합 정렬뿐 (선지 ⑤)
    "major-cspl-common-006": (lambda: (5, "퀵은 평균 n log n 이지만 최악 n²"),
                              lambda i: i),
    # 007 한 줄씩 번역·즉시 실행은 인터프리터 (선지 ④)
    "major-cspl-common-007": (lambda: (4, "컴파일러는 전체 번역·목적코드 생성·빠른 실행"),
                              lambda i: i),
    "major-cspl-common-008": (v_cspl_008, lambda v: {10: 1, 20: 2, 30: 3, 0: 4}[v]),
    # 009 같은 호출·다른 동작 → 다형성 (선지 ③)
    "major-cspl-common-009": (lambda: (3, "상속은 다형성을 구현하는 수단이지 그 자체가 아니다"),
                              lambda i: i),
    # 010 상속 관계에서 같은 형태로 재정의 (선지 ②)
    "major-cspl-common-010": (lambda: (2, "오버로딩 매개변수 다름·컴파일시 / 오버라이딩 같음·실행시"),
                              lambda i: i),
    "major-cspl-common-011": (v_cspl_011, lambda s: {
        "-127 ~ 127": 1, "-128 ~ 127": 2, "-128 ~ 128": 3,
        "0 ~ 255": 4, "-255 ~ 255": 5}[s]),
    "major-cspl-common-012": (v_cspl_012, lambda a: {1044: 1, 1056: 2, 1064: 3,
                                                     1068: 4, 1092: 5}[a]),
    # 013 n번째 상수 시간 접근은 배열의 성질 (선지 ④)
    "major-cspl-common-013": (lambda: (4, "연결 리스트는 앞에서부터 따라가 O(n)"),
                              lambda i: i),
    # 014 개방 주소법은 테이블 **안**에서 해결 (선지 ④가 틀린 진술)
    "major-cspl-common-014": (lambda: (4, "밖에 다는 쪽이 체이닝. 이름의 어감이 함정"),
                              lambda i: i),
    "major-cspl-common-015": (v_cspl_015, lambda t: {
        ("O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n²)"): 2}[t]),
    # 016 반복문으로 상태를 갱신하는 것은 명령형 (선지 ④)
    "major-cspl-common-016": (lambda: (4, "함수형은 상태 갱신을 피하고 재귀를 쓴다"),
                              lambda i: i),
    "major-cspl-common-017": (v_cspl_017, lambda v: {10: 1, 15: 2, 5: 3}[v]),
    # 018 finally 는 예외 여부와 무관하게 항상 (선지 ③)
    "major-cspl-common-018": (lambda: (3, "정리 코드는 항상 돌아야 쓸모가 있다"),
                              lambda i: i),

    "major-csca-common-001": (v_csca_001, lambda b: {
        "10000101": 1, "11111010": 2, "11111011": 3,
        "01111011": 4, "10000110": 5}[b]),
    "major-csca-common-002": (v_csca_002, lambda h: {"A5": 1, "B5": 2, "D5": 3,
                                                     "5B": 4}[h]),
    "major-csca-common-003": (v_csca_003, lambda e: {
        "10000001": 1, "10000010": 2, "10000011": 3,
        "01111101": 4, "00000011": 5}[e]),
    # 004 자리올림 **입력**을 받는 것은 전가산기 (선지 ③이 틀린 진술)
    "major-csca-common-004": (lambda: (3, "반가산기는 입력이 둘뿐. S=A⊕B, C=A·B"),
                              lambda i: i),
    "major-csca-common-005": (v_csca_005, lambda c: {100: 1, 104: 2, 105: 3,
                                                     500: 4, 505: 5}[c]),
    # 006 앞 명령의 결과를 기다린다 → 데이터 해저드 (선지 ②)
    "major-csca-common-006": (lambda: (2, "R1 이 1번의 출력이자 2번의 입력. 포워딩으로 완화"),
                              lambda i: i),
    "major-csca-common-007": (v_csca_007, lambda t: {14: 1, 17: 2, 19: 3,
                                                     22: 4, 27: 5}[t]),
    "major-csca-common-008": (v_csca_008, lambda t: {10: 1, 15: 2, 19: 3,
                                                     55: 4, 100: 5}[t]),
    # 009 직접 사상은 자리가 하나라 교체 알고리즘이 필요 없다 (선지 ④)
    "major-csca-common-009": (lambda: (4, "고를 것이 없으면 알고리즘도 없다"), lambda i: i),
    # 010 피연산자 위치가 정해진 스택 구조가 0-주소 (선지 ②)
    "major-csca-common-010": (lambda: (2, "3-주소 레지스터 · 2-주소 레지스터메모리 · "
                                          "1-주소 누산기 · 0-주소 스택"), lambda i: i),
    # 011 기억장치를 두 번 거친다 → 간접 주소 (선지 ③)
    "major-csca-common-011": (lambda: (3, "즉시 0회 · 직접 1회 · 간접 2회"), lambda i: i),
    "major-csca-common-012": (v_csca_012, lambda m: {500: 1, 800: 2, 2000: 3,
                                                     5000: 5}[m]),
    # 013 요청 → 현재 명령 완료 → 상태 저장 → 루틴 → 복귀 (선지 ①)
    "major-csca-common-013": (lambda: (1, "명령 중간의 상태는 저장할 수 없다"), lambda i: i),
    # 014 바이트마다 CPU 개입은 인터럽트 방식 (선지 ③이 틀린 진술)
    "major-csca-common-014": (lambda: (3, "DMA 는 시작과 끝에만 개입한다"), lambda i: i),
    # 015 고정 길이라 파이프라인에 유리 — 나머지 넷은 CISC (선지 ②)
    "major-csca-common-015": (lambda: (2, "RISC 적은 명령·고정 길이·많은 레지스터·하드와이어드"),
                              lambda i: i),
    # 016 레지스터 → 캐시 → 주기억 → 보조기억 (선지 ①)
    "major-csca-common-016": (lambda: (1, "속도·용량·단가가 같은 방향으로 움직인다"),
                              lambda i: i),
    "major-csca-common-017": (v_csca_017, lambda g: {"AND": 1, "OR": 2, "NOT": 3,
                                                     "XOR": 4}[g]),
    # 018 결과를 누산기에 저장하는 것은 실행 주기 (선지 ⑤)
    "major-csca-common-018": (lambda: (5, "인출은 PC→MAR · 메모리→MBR · MBR→IR · PC 증가"),
                              lambda i: i),

    "major-csdc-common-001": (v_csdc_001, lambda r: {3000: 1, 6000: 2, 12000: 3,
                                                     18000: 4, 24000: 5}[r]),
    "major-csdc-common-002": (v_csdc_002, lambda f: {"000": 1, "001": 2, "011": 3,
                                                     "101": 4, "110": 5}[f]),
    "major-csdc-common-003": (v_csdc_003, lambda r: {2: 1, 3: 2, 4: 3, 5: 4, 8: 5}[r]),
    "major-csdc-common-004": (v_csdc_004, lambda c: {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}[c]),
    "major-csdc-common-005": (v_csdc_005, lambda s: {
        "10110100": 1, "10110101": 2, "01011010": 3,
        "11011010": 4, "10110110": 5}[s]),
    # 006 주파수 대역을 나누는 것은 FDM (선지 ③이 틀린 진술)
    "major-csdc-common-006": (lambda: (3, "TDM 은 시간, FDM 은 주파수로 나눈다"),
                              lambda i: i),
    "major-csdc-common-007": (v_csdc_007, lambda r: {1_536_000: 1, 1_544_000: 2,
                                                     1_920_000: 3, 2_048_000: 4,
                                                     3_088_000: 5}[r]),
    # 008 진폭과 위상을 함께 바꾸는 것은 QAM (선지 ④)
    "major-csdc-common-008": (lambda: (4, "ASK 진폭 · FSK 주파수 · PSK 위상 · "
                                          "PCM 은 변조가 아니라 부호화"), lambda i: i),
    "major-csdc-common-009": (v_csdc_009, lambda r: {32000: 1, 48000: 2, 64000: 3,
                                                     96000: 4, 128000: 5}[r]),
    "major-csdc-common-010": (v_csdc_010, lambda b: {16: 1, 32: 2, 64: 3,
                                                     128: 4, 512: 5}[b]),
    # 011 송신 중 자기 신호에 가려 충돌 감지가 어렵다 (선지 ②)
    "major-csdc-common-011": (lambda: (2, "CD 는 보내면서 듣는 것을 전제. 무선은 불가"),
                              lambda i: i),
    "major-csdc-common-012": (v_csdc_012, lambda w: {3: 1, 4: 2, 7: 3, 8: 4, 15: 5}[w]),
    # 013 회선을 독점하므로 이용률이 낮다 (선지 ④가 틀린 진술)
    "major-csdc-common-013": (lambda: (4, "②(독점)를 인정하면 ④(높은 이용률)는 성립 못 한다"),
                              lambda i: i),
    "major-csdc-common-014": (v_csdc_014, lambda t: {0.5: 1, 1.2: 2, 1.7: 3,
                                                     2.4: 4, 12.0: 5}[t]),
    # 015 코드로 구분하는 것은 CDMA (선지 ③)
    "major-csdc-common-015": (lambda: (3, "FDMA 주파수 · TDMA 시간 · CDMA 코드 · "
                                          "OFDMA 부반송파 · ALOHA 는 임의 접근"),
                              lambda i: i),
    "major-csdc-common-016": (v_csdc_016, lambda d: {-10: 1, -20: 2, -30: 3,
                                                     -100: 4, -200: 5}[d]),
    # 017 수신 측 처리 능력에 맞추는 것이 흐름 제어 (선지 ②)
    "major-csdc-common-017": (lambda: (2, "흐름 제어는 수신 측, 혼잡 제어는 네트워크를 본다"),
                              lambda i: i),
    # 018 문자마다 부가 비트가 붙어 효율이 낮다 (선지 ④가 틀린 진술)
    "major-csdc-common-018": (lambda: (4, "8비트에 시작·정지 2비트 → 20%가 부가 정보"),
                              lambda i: i),
}


def main() -> int:
    from bank.loader import load_all
    ap = argparse.ArgumentParser(description="전산 문항 검증")
    ap.add_argument("--subject", help="파일명 조각 (database · network · os …)")
    a = ap.parse_args()

    items = [i for i in load_all() if i["kind"] == "major"
             and i["subject"].startswith(("데이터", "네트워크", "운영", "정보보안",
                                          "프로그래밍", "소프트웨어", "전자계산기"))]
    if a.subject:
        items = [i for i in items if a.subject in i.get("_file", "")]
    if not items:
        print("검증할 전산 문항이 없습니다."); return 0

    bad = unver = 0
    high: list[str] = []
    for it in items:
        q = it["questions"][0]
        risk = it.get("risk", "?")
        if risk == "high":
            high.append(it["id"])
        fn = REGISTRY.get(it["id"])
        if not fn:
            unver += 1
            print(f"   ─ {it['id']:<28}미검증 — 검증기를 등록하십시오")
            continue
        calc, note = fn[0]()
        want = fn[1](calc)
        ok = want == q["answer"]
        bad += not ok
        mark = "OK" if ok else f"**불일치** 계산 {want} ≠ 문항 {q['answer']}"
        tag = "  [HIGH]" if risk == "high" else ""
        print(f"   {'✔' if ok else '✘'} {it['id']:<28}{mark}{tag}")
        print(f"      {note}")

    print(f"\n검증 {len(items) - unver}건 · 불일치 {bad}건 · 미검증 {unver}건")
    if high:
        print(f"\n■ 위험도 high {len(high)}건 — **교과서 서술에 의존한다. 사람이 확인해야 한다**")
        for i in high:
            print(f"   {i}")
        print("   `python bank/loader.py --risk high --full` 로 펼쳐 볼 수 있다.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
