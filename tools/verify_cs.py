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
