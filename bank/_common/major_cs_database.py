# -*- coding: utf-8 -*-
"""전산직 — 데이터베이스론

**기관 색이 옅은 과목이다.** 정규화 판정이나 LEFT JOIN 동작은 코레일이든 한전이든
같으므로 `_common` 에 두고 어느 회차든 가져다 쓴다. 기관별 차이는 출제 범위와
난이도에서 나므로, 회차가 고를 때 조절한다.

## 검증

전산 계산·판정형은 **돌려서 확정한다.** `tools/verify_cs.py` 가 이 파일의 문항을
실제로 계산해 정답과 대조한다 — SQL 은 sqlite 로 실행하고, 함수 종속은
폐포(closure)로 후보키를 구해 정규형을 판정한다.

```bash
python tools/verify_cs.py --subject database
```

집필은 `PLAYBOOK` 규칙 `1-14` 순서를 따른다.
"""

ITEMS = [
    # ─────────────────────────────────────────────────────────────
    # 001 정규화 판정
    #   후보키 {학번, 과목코드} — 폐포로 확인
    #   과목코드 → 담당교수 가 부분 함수 종속이라 2NF 위반
    #   담당교수 → 교수연구실 는 이행 종속이나, 2NF 에서 이미 걸린다
    #   → 제1정규형까지만 만족
    # ─────────────────────────────────────────────────────────────
    {
        "id": "major-csdb-common-001",
        "org": "공통",
        "kind": "major",
        "subject": "데이터베이스론",
        "difficulty": "중",
        "evidence": "전산 후기 153건 계열. 정규화는 전산직 필기의 고정 출제 항목",
        "snapshot": "S-20260804-c85013",

        "area": "데이터베이스론",
        "lead": None,
        "passage": None,
        "questions": [
            {
                "type": "정규화",
                "stem": "다음 릴레이션이 만족하는 가장 높은 정규형은?",
                "material": (
                    '<div class="box"><div class="box-title">&lt;릴레이션 R&gt;</div>'
                    "<p>R(<u class=\"ref\">학번</u>, <u class=\"ref\">과목코드</u>, "
                    "성적, 담당교수, 교수연구실)</p>"
                    '<div class="box-title">&lt;함수 종속&gt;</div>'
                    "<p>(학번, 과목코드) → 성적</p>"
                    "<p>과목코드 → 담당교수</p>"
                    "<p>담당교수 → 교수연구실</p>"
                    '<p class="note">※ 한 과목은 한 교수가 담당하고, 한 교수는 한 연구실을 쓴다.</p>'
                    "</div>"
                ),
                "choices": ["제1정규형", "제2정규형", "제3정규형", "보이스·코드 정규형", "제4정규형"],
                "answer": 1,
                "explain": (
                    "<p>먼저 후보키를 구한다. (학번, 과목코드)의 폐포가 전체 속성을 덮고, "
                    "어느 한쪽만으로는 덮지 못하므로 <strong>후보키는 (학번, 과목코드)</strong> 하나다.</p>"
                    "<p><strong>과목코드 → 담당교수</strong>는 후보키의 <strong>일부</strong>에만 "
                    "의존한다. 부분 함수 종속이 있으므로 <strong>제2정규형을 만족하지 못한다.</strong></p>"
                    "<p>담당교수 → 교수연구실은 이행 종속이라 제3정규형에도 걸리지만, "
                    "정규형은 낮은 단계부터 차례로 판정하므로 답은 제1정규형이다.</p>"
                    "<p>모든 속성이 원자값이므로 제1정규형은 만족한다.</p>"
                ),
                "each": [
                    "① (정답) 원자값 조건은 충족하고, 부분 함수 종속 때문에 제2정규형에서 막힌다.",
                    "② 과목코드 → 담당교수가 부분 함수 종속이다. 제2정규형이 아니다.",
                    "③ 제2정규형을 만족해야 판정할 수 있는 단계다.",
                    "④ 모든 결정자가 후보키여야 한다. 과목코드와 담당교수 둘 다 후보키가 아니다.",
                    "⑤ 다치 종속을 다루는 단계로, 앞 단계를 통과한 뒤에 본다.",
                ],
                "why": {
                    "근거": "전산 후기 153건 계열. 정규화는 공기업 전산직 필기의 고정 항목이다",
                    "설계": "**부분 함수 종속과 이행 종속을 함께 넣었다.** 이행 종속만 보면 "
                            "제2정규형(②)으로 답하게 되므로, 낮은 단계부터 차례로 판정하는지를 묻는다",
                    "함정": "② 가 대표 오답이다. 담당교수 → 교수연구실이라는 **이행 종속이 눈에 먼저 "
                            "들어와** 제3정규형 위반으로 읽고 제2정규형을 고르게 된다. "
                            "부분 함수 종속을 먼저 봐야 한다",
                    "검증": "속성 폐포를 계산해 후보키가 (학번, 과목코드) 하나임을 확인하고, "
                            "세 함수 종속을 후보키와 대조해 부분 종속 1건·이행 종속 1건을 특정했다. "
                            "`tools/verify_cs.py --subject database` 로 재현된다",
                },
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────
    # 002 LEFT JOIN — ON 절 조건 대 WHERE 절 조건
    #   sqlite 실행 결과: ON 절이면 4행, WHERE 로 옮기면 2행
    # ─────────────────────────────────────────────────────────────
    {
        "id": "major-csdb-common-002",
        "org": "공통",
        "kind": "major",
        "subject": "데이터베이스론",
        "difficulty": "중상",
        "evidence": "전산 후기 153건 계열. SQL 결과 판정은 필기 단골",
        "snapshot": "S-20260804-c85013",

        "area": "데이터베이스론",
        "lead": None,
        "passage": None,
        "questions": [
            {
                "type": "SQL",
                "stem": "다음 질의의 결과 행 수는?",
                "material": (
                    '<div class="box"><div class="box-title">&lt;부서&gt;</div>'
                    '<table class="data">'
                    "<tr><th>부서코드</th><th>부서명</th></tr>"
                    "<tr><td>D1</td><td>운영</td></tr>"
                    "<tr><td>D2</td><td>기술</td></tr>"
                    "<tr><td>D3</td><td>기획</td></tr>"
                    "<tr><td>D4</td><td>안전</td></tr>"
                    "</table>"
                    '<div class="box-title">&lt;사원&gt;</div>'
                    '<table class="data">'
                    "<tr><th>사번</th><th>이름</th><th>부서코드</th><th>급여</th></tr>"
                    "<tr><td>1</td><td>김</td><td>D1</td><td>4200</td></tr>"
                    "<tr><td>2</td><td>이</td><td>D1</td><td>3800</td></tr>"
                    "<tr><td>3</td><td>박</td><td>D2</td><td>5100</td></tr>"
                    "<tr><td>4</td><td>최</td><td>D2</td><td>3300</td></tr>"
                    "<tr><td>5</td><td>정</td><td>D2</td><td>4700</td></tr>"
                    "<tr><td>6</td><td>한</td><td>D3</td><td>3900</td></tr>"
                    "<tr><td>7</td><td>오</td><td>NULL</td><td>4400</td></tr>"
                    "</table>"
                    '<div class="box-title">&lt;질의&gt;</div>'
                    "<p><code>SELECT 부.부서명, COUNT(사.사번)</code></p>"
                    "<p><code>FROM 부서 부 LEFT JOIN 사원 사</code></p>"
                    "<p><code>&nbsp;&nbsp;ON 부.부서코드 = 사.부서코드 AND 사.급여 &gt;= 4000</code></p>"
                    "<p><code>GROUP BY 부.부서명</code></p>"
                    "</div>"
                ),
                "choices": ["1개", "2개", "3개", "4개", "7개"],
                "answer": 4,
                "explain": (
                    "<p>급여 조건이 <strong>ON 절</strong>에 있다. 조인 단계에서만 걸리므로 "
                    "짝을 찾지 못한 부서도 <strong>LEFT JOIN 규칙에 따라 남는다.</strong></p>"
                    '<table class="data">'
                    "<tr><th>부서</th><th>급여 4000 이상인 사원</th><th>COUNT</th></tr>"
                    "<tr><td>운영</td><td>김(4200)</td><td>1</td></tr>"
                    "<tr><td>기술</td><td>박(5100), 정(4700)</td><td>2</td></tr>"
                    "<tr><td>기획</td><td>없음</td><td>0</td></tr>"
                    "<tr><td>안전</td><td>없음</td><td>0</td></tr>"
                    "</table>"
                    "<p>네 부서가 모두 남아 <strong>4행</strong>이다. "
                    "COUNT(사.사번)은 NULL을 세지 않으므로 기획과 안전은 0이 된다.</p>"
                    "<p>같은 조건을 <strong>WHERE 절로 옮기면</strong> 짝이 없는 행이 걸러져 "
                    "운영·기술만 남고 <strong>2행</strong>이 된다. 이 차이가 이 문항의 핵심이다.</p>"
                ),
                "each": [
                    "① 부서 하나로 줄어들 조건이 없다.",
                    "② 급여 조건을 WHERE 절에 두었을 때의 결과다. ON 절과 혼동하면 여기로 온다.",
                    "③ 사원이 한 명이라도 있는 부서만 센 값이다. 안전(D4)은 사원 자체가 없다.",
                    "④ (정답) ON 절 조건이므로 네 부서가 모두 남는다.",
                    "⑤ 사원 표의 행 수다. GROUP BY 결과와 무관하다.",
                ],
                "why": {
                    "근거": "전산 후기 153건 계열. SQL 결과 판정은 필기 단골 유형이다",
                    "설계": "**ON 절과 WHERE 절의 차이 하나만** 묻도록 나머지를 단순하게 두었다. "
                            "사원이 없는 부서(안전)와 부서가 없는 사원(오)을 함께 넣어 "
                            "LEFT JOIN 방향까지 확인하게 했다",
                    "함정": "② 가 대표 오답이다. 급여 조건을 **필터로 읽으면** 조건을 만족하는 사원이 "
                            "있는 부서만 남는다고 보게 된다. ③ 은 사원이 있는 부서만 센 값이라 "
                            "안전(D4)을 빠뜨린 경우다",
                    "검증": "sqlite 로 두 질의를 실제 실행했다 — ON 절은 4행(운영1·기술2·기획0·안전0), "
                            "WHERE 절로 옮기면 2행이다. `tools/verify_cs.py --subject database` 로 재현된다",
                },
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────
    # 003 서브쿼리와 NULL — NOT IN 에 NULL 이 섞이면 결과가 비는 고전
    #   실행: NOT IN → 0행 · NULL 제외하면 2행 · NOT EXISTS → 2행
    # ─────────────────────────────────────────────────────────────
    {
        "id": "major-csdb-common-003",
        "org": "공통",
        "kind": "major",
        "subject": "데이터베이스론",
        "difficulty": "상",
        "evidence": "전산 후기 153건 계열. NULL 처리는 SQL 문항의 대표 함정",
        "snapshot": "S-20260804-c85013",

        "area": "데이터베이스론",
        "lead": None,
        "passage": None,
        "questions": [
            {
                "type": "SQL",
                "stem": "다음 질의의 결과로 옳은 것은?",
                "material": (
                    '<div class="box"><div class="box-title">&lt;사원&gt;</div>'
                    '<table class="data">'
                    "<tr><th>사번</th><th>이름</th><th>관리자</th></tr>"
                    "<tr><td>1</td><td>김</td><td>NULL</td></tr>"
                    "<tr><td>2</td><td>이</td><td>1</td></tr>"
                    "<tr><td>3</td><td>박</td><td>1</td></tr>"
                    "<tr><td>4</td><td>최</td><td>2</td></tr>"
                    "</table>"
                    '<div class="box-title">&lt;질의&gt;</div>'
                    "<p><code>SELECT COUNT(*) FROM 사원</code></p>"
                    "<p><code>WHERE 사번 NOT IN (SELECT 관리자 FROM 사원)</code></p>"
                    "</div>"
                ),
                "choices": ["0", "1", "2", "3", "4"],
                "answer": 1,
                "explain": (
                    "<p>서브쿼리가 돌려주는 값은 <code>{NULL, 1, 1, 2}</code>다.</p>"
                    "<p><code>사번 NOT IN (NULL, 1, 2)</code>는 "
                    "<code>사번 &lt;&gt; NULL AND 사번 &lt;&gt; 1 AND 사번 &lt;&gt; 2</code>로 풀린다. "
                    "<strong>NULL과의 비교는 참도 거짓도 아닌 UNKNOWN</strong>이므로, "
                    "AND로 묶인 조건 전체가 참이 될 수 없다.</p>"
                    "<p>어떤 행도 WHERE를 통과하지 못해 <strong>0</strong>이 나온다.</p>"
                    "<p>서브쿼리에 <code>WHERE 관리자 IS NOT NULL</code>을 붙이거나 "
                    "<code>NOT EXISTS</code>로 바꾸면 3과 4가 남아 <strong>2</strong>가 된다.</p>"
                ),
                "each": [
                    "① (정답) NULL과의 비교가 UNKNOWN이라 어떤 행도 조건을 만족하지 못한다.",
                    "② 관리자로 지정된 적 없는 사번을 하나만 센 값이다.",
                    "③ NULL을 걸러 냈을 때의 결과다. 3과 4가 남는다. NOT EXISTS로 바꿔도 같다.",
                    "④ NULL을 무시하고 1만 제외했을 때 나오는 값이다.",
                    "⑤ 전체 행 수다. NOT IN 조건이 없을 때의 결과다.",
                ],
                "why": {
                    "근거": "전산 후기 153건 계열. NULL 처리는 SQL 문항의 대표 함정이다",
                    "설계": "**관리자 열에 NULL을 딱 하나 넣었다.** 이 한 칸이 결과를 2에서 0으로 "
                            "바꾼다. 표가 네 행뿐이라 수작업으로 따라갈 수 있고, "
                            "그래서 오히려 NULL을 건너뛰고 세게 된다",
                    "함정": "③ 이 대표 오답이다. 관리자로 등록된 적 없는 사번을 눈으로 세면 "
                            "3과 4가 나와 **2**가 된다. 이것이 `NOT EXISTS` 의 결과이기도 해서 "
                            "두 구문이 같다고 알고 있으면 더 확신하게 된다",
                    "검증": "sqlite 로 세 형태를 모두 실행했다 — `NOT IN`(NULL 포함) 0, "
                            "`NOT IN`(NULL 제외) 2, `NOT EXISTS` 2. "
                            "`tools/verify_cs.py --subject database` 로 재현된다",
                },
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────
    # 004 트랜잭션 격리수준 — 표준 정의로 고정
    # ─────────────────────────────────────────────────────────────
    {
        "id": "major-csdb-common-004",
        "org": "공통",
        "kind": "major",
        "subject": "데이터베이스론",
        "difficulty": "중",
        "evidence": "전산 후기 153건 계열. 격리수준은 고정 출제 항목",
        "snapshot": "S-20260804-c85013",

        "area": "데이터베이스론",
        "lead": None,
        "passage": None,
        "questions": [
            {
                "type": "트랜잭션",
                "stem": "REPEATABLE READ 격리수준에서 발생할 수 있는 이상 현상은?",
                "material": (
                    '<p class="note">※ ANSI/ISO SQL 표준이 정의한 네 가지 격리수준을 기준으로 한다.</p>'
                ),
                "choices": [
                    "Dirty Read",
                    "Non-repeatable Read",
                    "Phantom Read",
                    "세 가지 모두 발생하지 않는다",
                    "Dirty Read와 Non-repeatable Read",
                ],
                "answer": 3,
                "explain": (
                    '<table class="data">'
                    "<tr><th>격리수준</th><th>Dirty Read</th><th>Non-repeatable Read</th>"
                    "<th>Phantom Read</th></tr>"
                    "<tr><td>READ UNCOMMITTED</td><td>O</td><td>O</td><td>O</td></tr>"
                    "<tr><td>READ COMMITTED</td><td>X</td><td>O</td><td>O</td></tr>"
                    "<tr><td>REPEATABLE READ</td><td>X</td><td>X</td><td>O</td></tr>"
                    "<tr><td>SERIALIZABLE</td><td>X</td><td>X</td><td>X</td></tr>"
                    "</table>"
                    "<p>REPEATABLE READ는 <strong>읽은 행에 공유 잠금을 유지</strong>해 같은 행을 "
                    "다시 읽었을 때 값이 달라지는 일을 막는다. 잠금이 걸리는 대상은 "
                    "<strong>이미 읽은 행</strong>이므로, 조건에 맞는 행이 새로 삽입되는 것은 막지 못한다.</p>"
                    "<p>같은 조건으로 두 번 조회했을 때 행 수가 달라지는 현상이 Phantom Read다.</p>"
                ),
                "each": [
                    "① READ UNCOMMITTED에서만 발생한다. 커밋되지 않은 값을 읽는 현상이다.",
                    "② READ COMMITTED까지 발생하고 REPEATABLE READ에서 막힌다.",
                    "③ (정답) 읽은 행은 잠기지만 새로 삽입되는 행은 막지 못한다.",
                    "④ SERIALIZABLE에 해당한다.",
                    "⑤ 둘 다 REPEATABLE READ에서 막힌다.",
                ],
                "why": {
                    "근거": "전산 후기 153건 계열. 격리수준 표는 고정 출제 항목이다",
                    "설계": "네 수준 가운데 **한 칸만 O로 남는 REPEATABLE READ**를 물었다. "
                            "표를 외웠는지가 아니라 **잠금 대상이 행이라는 점**을 아는지가 갈린다",
                    "함정": "④ 가 대표 오답이다. REPEATABLE READ라는 이름이 「반복해서 읽어도 같다」로 "
                            "읽혀 모든 이상 현상이 막힌다고 보게 된다. 이름이 보장하는 것은 "
                            "**이미 읽은 행**에 한정된다",
                    "검증": "ANSI/ISO SQL 표준의 격리수준 정의표와 대조했다. "
                            "REPEATABLE READ 행에서 O가 남는 칸은 Phantom Read 하나다",
                },
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────
    # 005 B+트리 높이 — 차수 200 · 레코드 100만 → 3
    #   h=1 199 · h=2 39,800 · h=3 7,960,000 ≥ 1,000,000
    # ─────────────────────────────────────────────────────────────
    {
        "id": "major-csdb-common-005",
        "org": "공통",
        "kind": "major",
        "subject": "데이터베이스론",
        "difficulty": "중상",
        "evidence": "전산 후기 153건 계열. 인덱스 구조는 저장·탐색 비용과 함께 출제된다",
        "snapshot": "S-20260804-c85013",

        "area": "데이터베이스론",
        "lead": None,
        "passage": None,
        "questions": [
            {
                "type": "인덱스",
                "stem": "레코드 100만 건을 저장할 때 필요한 B+트리의 최소 높이는?",
                "material": (
                    '<div class="box"><div class="box-title">&lt;조건&gt;</div>'
                    "<p>1. 트리의 차수는 200이다.</p>"
                    "<p>2. 한 노드는 최대 199개의 키와 200개의 자식을 가진다.</p>"
                    "<p>3. 모든 노드가 최대로 채워진 경우를 가정한다.</p>"
                    '<p class="note">※ 루트 하나만 있는 경우를 높이 1로 센다.</p>'
                    "</div>"
                ),
                "choices": ["2", "3", "4", "5", "6"],
                "answer": 2,
                "explain": (
                    "<p>높이별로 담을 수 있는 키의 최대 개수를 쌓아 올린다.</p>"
                    '<table class="data">'
                    "<tr><th>높이</th><th>최대 키 개수</th></tr>"
                    "<tr><td>1</td><td>199</td></tr>"
                    "<tr><td>2</td><td>199 × 200 = 39,800</td></tr>"
                    "<tr><td>3</td><td>39,800 × 200 = 7,960,000</td></tr>"
                    "</table>"
                    "<p>높이 2로는 39,800건까지만 담긴다. 100만 건을 담으려면 "
                    "<strong>높이 3</strong>이 필요하고, 이때 796만 건까지 수용한다.</p>"
                    "<p>차수가 커질수록 높이가 낮아지는 것이 B+트리를 쓰는 이유다. "
                    "높이가 곧 디스크 접근 횟수이기 때문이다.</p>"
                ),
                "each": [
                    "① 39,800건까지만 담긴다. 100만에 크게 못 미친다.",
                    "② (정답) 796만 건까지 수용하므로 100만 건을 담을 수 있는 최소 높이다.",
                    "③ 높이 3으로 충분하다. 차수를 100 이하로 잡았을 때 나오는 값이다.",
                    "④ 이진 탐색 트리처럼 차수를 작게 잡았을 때의 값이다.",
                    "⑤ 같은 이유로 과대 추정한 값이다.",
                ],
                "why": {
                    "근거": "전산 후기 153건 계열. 인덱스 구조는 탐색 비용과 함께 출제된다",
                    "설계": "**차수를 200으로 크게 잡았다.** 차수가 작으면 높이 계산이 이진 트리 "
                            "감각과 비슷해지는데, 크게 잡아야 「높이 3에 796만 건」이라는 "
                            "B+트리의 성질이 드러난다",
                    "함정": "③ 4가 대표 오답이다. 차수를 100으로 잘못 잡으면 높이 4가 나온다"
                            "(99 → 9,900 → 990,000 → 9,900만). **99만은 100만에 못 미쳐** "
                            "한 단계가 더 필요해지는데, 이 경계를 지나치기 쉽다",
                    "검증": "높이를 1부터 올리며 수용량을 곱해 100만을 넘는 첫 높이를 찾았다 — "
                            "199 · 39,800 · 7,960,000. 차수 100·50 으로도 계산해 "
                            "오답 ③의 경로를 확인했다",
                },
            },
        ],
    },
]
