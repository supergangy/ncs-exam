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


# id → (검증 함수, 계산값을 선지 번호로 옮기는 함수)
#   검증 함수는 (계산값, 사람이 읽을 설명) 을 돌려준다.
#   **선지 번호를 함수 안에 적지 않는다** — 계산과 배치를 갈라 두어야
#   선지 순서를 바꿔도 검증이 따라온다.
REGISTRY = {
    "major-csdb-common-001": (v_csdb_001, lambda nf: {1: 1, 2: 2, 3: 3}[nf]),
    "major-csdb-common-002": (v_csdb_002, lambda n: {1: 1, 2: 2, 3: 3, 4: 4, 7: 5}[n]),
    "major-csdb-common-003": (v_csdb_003, lambda n: {0: 1, 1: 2, 2: 3, 3: 4, 4: 5}[n]),
    "major-csdb-common-004": (v_csdb_004, lambda s: {
        "Dirty Read": 1, "Non-repeatable Read": 2, "Phantom Read": 3}[s]),
    "major-csdb-common-005": (v_csdb_005, lambda h: {2: 1, 3: 2, 4: 3, 5: 4, 6: 5}[h]),
    "major-csdb-common-006": (v_csdb_006, lambda v: {"3NF만족_BCNF위반": 3}[v]),
    "major-csdb-common-007": (v_csdb_007, lambda i: {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}[i]),
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
    for it in items:
        q = it["questions"][0]
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
        print(f"   {'✔' if ok else '✘'} {it['id']:<28}{mark}")
        print(f"      {note}")

    print(f"\n검증 {len(items) - unver}건 · 불일치 {bad}건 · 미검증 {unver}건")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
