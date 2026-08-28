# -*- coding: utf-8 -*-
# 데이터베이스론 07~14 (전산 1회)
#
# 근거 — README 2절. 후기 28건(20.4%) → 8문항. 네트워크와 함께 가장 큰 몫이다.
#
# 배분 — 정규화 2 · SQL 3 · 트랜잭션 1 · 인덱스 1 · 관계대수 1.
#   블루프린트(`bank/BLUEPRINT_cs.md`)의 20문항 비율을 8로 줄인 것이다.
#
#   07 정규화   — BCNF. 은행은 최고 정규형·무손실 분해를 묻는데 여기는 **위배 종속**을 짚는다
#   08 SQL     — 외부조인 조건을 ON 에 두느냐 WHERE 에 두느냐. 실무에서 가장 자주 깨지는 곳이다
#   09 SQL     — NULL 과 집계함수. COUNT(*) 와 COUNT(열) 이 다르다
#   10 정규화   — 후보키를 **모두** 구한다. 은행은 하나만 묻는다
#   11 트랜잭션 — 충돌 직렬가능성. 선행 그래프를 그려야 풀린다
#   12 인덱스   — B+트리 리프 수와 높이. 채움률이 열쇠다
#   13 관계대수 — 관계대수는 집합이고 SQL 은 다중집합이다
#   14 SQL     — NOT IN 과 NOT EXISTS 는 NULL 앞에서 갈라진다
#
# 여덟 문항 모두 `verify.py` 가 sqlite 로 돌리거나 폐포·선행 그래프로 다시 구한다.
#
# 정답 — ③ ④ ② ④ ⑤ ④ ② ①
BLOCKS = [
    # ═══════════════════════════════════════════════════════════════
    # 07 BCNF
    #   R(A,B,C,D) · AB→C, C→D, D→B
    #   후보키 AB · AC · AD → 네 속성이 모두 prime 이라 3NF 는 만족
    #   C, D 는 슈퍼키가 아니므로 C→D, D→B 가 BCNF 위배
    # ═══════════════════════════════════════════════════════════════
    {
        "area": "데이터베이스론",
        "lead": None,
        "passage": None,
        "questions": [
            {
                "type": "정규화",
                "stem": "이 릴레이션이 만족하는 가장 높은 정규형과, BCNF를 위배하는 함수 종속은?",
                "material": (
                    '<div class="box">'
                    '<div class="box-title">&lt;릴레이션 R&gt;</div>'
                    "<p>R(A, B, C, D)</p>"
                    "<p>함수 종속 : AB → C, C → D, D → B</p>"
                    '<p class="note">※ 위 세 종속과 그로부터 유도되는 것 말고 다른 종속은 없다.</p>'
                    "</div>"
                ),
                "choices": [
                    "제2정규형 · AB → C",
                    "제2정규형 · C → D, D → B",
                    "제3정규형 · C → D, D → B",
                    "제3정규형 · C → D 만",
                    "BCNF · 위배하는 종속이 없다",
                ],
                "answer": 3,
                "explain": (
                    "<p>먼저 후보키를 구한다. 폐포를 하나씩 잡아 보면</p>"
                    '<table class="data">'
                    "<tr><th>속성 집합</th><th>폐포</th><th>후보키인가</th></tr>"
                    "<tr><td>AB</td><td>AB → C → D … ABCD</td><td>○</td></tr>"
                    "<tr><td>AC</td><td>AC → D(C→D) → B(D→B) … ABCD</td><td>○</td></tr>"
                    "<tr><td>AD</td><td>AD → B(D→B) → C(AB→C) … ABCD</td><td>○</td></tr>"
                    "<tr><td>A · BC · BD</td><td>전체가 되지 않는다</td><td>×</td></tr>"
                    "</table>"
                    "<p>후보키가 AB · AC · AD 이므로 <strong>A · B · C · D 네 속성이 모두 "
                    "기본속성(prime)</strong>이다.</p>"
                    "<p>제3정규형은 「모든 종속의 오른쪽이 기본속성이거나, 왼쪽이 슈퍼키」를 요구한다. "
                    "C → D 의 D도, D → B 의 B도 기본속성이므로 <strong>3NF는 만족한다.</strong></p>"
                    "<p>BCNF는 더 엄하다. <strong>왼쪽이 슈퍼키여야만</strong> 한다. "
                    "C의 폐포는 CDB로 A가 빠지고, D의 폐포는 DB뿐이다. 둘 다 슈퍼키가 아니므로 "
                    "<strong>C → D 와 D → B 가 BCNF를 위배</strong>한다.</p>"
                ),
                "each": [
                    "① AB는 후보키이므로 AB → C 는 어느 정규형도 위배하지 않는다.",
                    "② 위배 종속은 맞지만 정규형이 틀렸다. 오른쪽 D·B가 모두 기본속성이라 "
                    "3NF까지는 올라간다.",
                    "③ (정답) 3NF는 만족하고, 왼쪽이 슈퍼키가 아닌 C → D · D → B 가 BCNF를 위배한다.",
                    "④ D → B 도 함께 위배한다. D의 폐포는 DB로 ABCD가 되지 못한다.",
                    "⑤ BCNF라면 위배 종속이 없어야 한다. C의 폐포에 A가 없다.",
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # 08 외부조인 조건의 자리
    #   ON  : D1 김 / D2 박·최 / D3 NULL / D4 NULL = 5행
    #   WHERE: 김·박·최 = 3행
    # ═══════════════════════════════════════════════════════════════
    {
        "area": "데이터베이스론",
        "lead": None,
        "passage": None,
        "questions": [
            {
                "type": "SQL",
                "stem": "조건을 ON에 둔 ㉠과 WHERE에 둔 ㉡의 결과 행 수는?",
                "material": (
                    '<div class="box">'
                    '<div class="box-title">&lt;부서&gt;</div>'
                    '<table class="data">'
                    "<tr><th>부서코드</th><th>부서명</th></tr>"
                    "<tr><td>D1</td><td>영업</td></tr>"
                    "<tr><td>D2</td><td>개발</td></tr>"
                    "<tr><td>D3</td><td>총무</td></tr>"
                    "<tr><td>D4</td><td>인사</td></tr>"
                    "</table>"
                    '<div class="box-title">&lt;사원&gt;</div>'
                    '<table class="data">'
                    "<tr><th>사번</th><th>이름</th><th>부서코드</th><th>급여</th></tr>"
                    "<tr><td>1</td><td>김대리</td><td>D1</td><td>300</td></tr>"
                    "<tr><td>2</td><td>이주임</td><td>D1</td><td>250</td></tr>"
                    "<tr><td>3</td><td>박과장</td><td>D2</td><td>400</td></tr>"
                    "<tr><td>4</td><td>최사원</td><td>D2</td><td>350</td></tr>"
                    "</table>"
                    '<div class="box-title">&lt;질의&gt;</div>'
                    "<p>㉠ SELECT * FROM 부서 LEFT JOIN 사원<br>"
                    "&nbsp;&nbsp;&nbsp;&nbsp;ON 부서.부서코드 = 사원.부서코드 <strong>AND 사원.급여 &gt;= 300</strong>;</p>"
                    "<p>㉡ SELECT * FROM 부서 LEFT JOIN 사원<br>"
                    "&nbsp;&nbsp;&nbsp;&nbsp;ON 부서.부서코드 = 사원.부서코드<br>"
                    "&nbsp;&nbsp;&nbsp;&nbsp;<strong>WHERE 사원.급여 &gt;= 300</strong>;</p>"
                    "</div>"
                ),
                "choices": [
                    "㉠ 3행 · ㉡ 3행", "㉠ 3행 · ㉡ 5행", "㉠ 5행 · ㉡ 5행", "㉠ 5행 · ㉡ 3행", "㉠ 6행 · ㉡ 3행",
                ],
                "answer": 4,
                "explain": (
                    "<p>조건을 <strong>어디에 두느냐</strong>가 결과를 바꾼다.</p>"
                    "<p>㉠ 은 조건이 ON에 있다. 조건은 <strong>짝을 맺을 때만</strong> 쓰이고, "
                    "짝을 못 맺은 왼쪽 행은 그대로 NULL을 달고 남는다.</p>"
                    '<table class="data">'
                    "<tr><th>부서</th><th>㉠ 결과</th><th>㉡ 결과</th></tr>"
                    "<tr><td>D1 영업</td><td>김대리(300) — 1행</td><td>김대리 — 1행</td></tr>"
                    "<tr><td>D2 개발</td><td>박과장·최사원 — 2행</td><td>박과장·최사원 — 2행</td></tr>"
                    "<tr><td>D3 총무</td><td>NULL — 1행</td><td>걸러짐</td></tr>"
                    "<tr><td>D4 인사</td><td>NULL — 1행</td><td>걸러짐</td></tr>"
                    "<tr><td>합</td><td><strong>5행</strong></td><td><strong>3행</strong></td></tr>"
                    "</table>"
                    "<p>㉡ 은 조인을 다 한 뒤 WHERE로 거른다. 짝을 못 맺은 D3·D4는 급여가 "
                    "NULL이라 <code>NULL &gt;= 300</code> 이 참이 되지 못하고 사라진다. "
                    "<strong>WHERE에 오른쪽 표의 조건을 쓰면 외부조인이 사실상 내부조인이 된다.</strong></p>"
                ),
                "each": [
                    "① ㉠ 이 3행이 되려면 조건이 ON이 아니라 WHERE에 있어야 한다.", "② 두 값이 뒤바뀌었다. 행이 더 많이 남는 쪽은 조건을 ON에 둔 ㉠ 이다.", "③ ㉡ 의 D3·D4는 급여가 NULL이다. NULL과의 비교는 참이 되지 않아 걸러진다.", "④ (정답) ㉠ 은 D3·D4가 NULL 행으로 남아 5행, ㉡ 은 그 둘이 걸러져 3행이다.", "⑤ 6행은 조건을 아예 걸지 않은 왼쪽 외부조인의 행 수다"
                    "(D1 2행 + D2 2행 + D3 1행 + D4 1행).",
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # 09 NULL 과 집계함수
    #   COUNT(*)=6 · COUNT(성과급)=3 · SUM=600 · AVG=600/3=200
    # ═══════════════════════════════════════════════════════════════
    {
        "area": "데이터베이스론",
        "lead": None,
        "passage": None,
        "questions": [
            {
                "type": "SQL",
                "stem": "다음 질의의 결과로 옳은 것은?",
                "material": (
                    '<div class="box">'
                    '<div class="box-title">&lt;사원&gt;</div>'
                    '<table class="data">'
                    "<tr><th>사번</th><th>이름</th><th>부서</th><th>성과급</th></tr>"
                    "<tr><td>1</td><td>김대리</td><td>영업</td><td>100</td></tr>"
                    "<tr><td>2</td><td>이주임</td><td>영업</td><td>NULL</td></tr>"
                    "<tr><td>3</td><td>박과장</td><td>개발</td><td>200</td></tr>"
                    "<tr><td>4</td><td>최사원</td><td>개발</td><td>300</td></tr>"
                    "<tr><td>5</td><td>정주임</td><td>개발</td><td>NULL</td></tr>"
                    "<tr><td>6</td><td>한사원</td><td>총무</td><td>NULL</td></tr>"
                    "</table>"
                    '<div class="box-title">&lt;질의&gt;</div>'
                    "<p>SELECT COUNT(*), COUNT(성과급), AVG(성과급) FROM 사원;</p>"
                    "</div>"
                ),
                "choices": [
                    "3 · 3 · 200", "6 · 3 · 200", "6 · 3 · 100", "6 · 3 · 600", "6 · 6 · 100",
                ],
                "answer": 2,
                "explain": (
                    "<p>세 함수가 NULL을 저마다 다르게 다룬다.</p>"
                    '<table class="data">'
                    "<tr><th>함수</th><th>세는 것</th><th>값</th></tr>"
                    "<tr><td>COUNT(*)</td><td><strong>행</strong>을 센다. NULL도 행이다</td>"
                    "<td>6</td></tr>"
                    "<tr><td>COUNT(성과급)</td><td>그 열의 <strong>NULL 아닌 값</strong>을 센다</td>"
                    "<td>3</td></tr>"
                    "<tr><td>AVG(성과급)</td><td>NULL을 <strong>아예 빼고</strong> 평균</td>"
                    "<td>600 ÷ 3 = 200</td></tr>"
                    "</table>"
                    "<p>AVG는 NULL을 0으로 보지 않는다. 분모도 3이지 6이 아니다. "
                    "「모르는 값」과 「0」은 다른 것이라 평균에 끌어들이지 않는다.</p>"
                ),
                "each": [
                    "① COUNT(*)는 6이다. NULL이 든 행도 행으로 센다.", "② (정답) 6 · 3 · 200. AVG의 분모는 NULL을 뺀 3이다.", "③ 100은 AVG를 600 ÷ 6 으로 구한 값이다. NULL을 0으로 보고 분모에 넣었다.", "④ 600은 AVG가 아니라 SUM(성과급)의 값이다.", "⑤ COUNT(성과급)은 6이 될 수 없다. 값이 있는 행은 셋뿐이다.",
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # 10 후보키를 모두 구한다
    #   R(A,B,C,D,E) · A→BC, CD→E, B→D, E→A
    #   A · E · BC · CD 넷
    # ═══════════════════════════════════════════════════════════════
    {
        "area": "데이터베이스론",
        "lead": None,
        "passage": None,
        "questions": [
            {
                "type": "정규화",
                "stem": "이 릴레이션의 후보키를 모두 고른 것은?",
                "material": (
                    '<div class="box">'
                    '<div class="box-title">&lt;릴레이션 R&gt;</div>'
                    "<p>R(A, B, C, D, E)</p>"
                    "<p>함수 종속 : A → BC, CD → E, B → D, E → A</p>"
                    "</div>"
                ),
                "choices": [
                    "A, E",
                    "A, E, BC",
                    "A, E, CD",
                    "A, E, BC, CD",
                    "A, B, E, BC, CD",
                ],
                "answer": 4,
                "explain": (
                    "<p>폐포를 구해 전체 속성이 나오는지 본다.</p>"
                    '<table class="data">'
                    "<tr><th>집합</th><th>폐포를 넓히는 과정</th><th>결과</th></tr>"
                    "<tr><td>A</td><td>A → BC → D(B→D) → E(CD→E)</td>"
                    "<td>ABCDE <strong>○</strong></td></tr>"
                    "<tr><td>E</td><td>E → A → BC → D → E</td>"
                    "<td>ABCDE <strong>○</strong></td></tr>"
                    "<tr><td>BC</td><td>BC → D(B→D) → E(CD→E) → A(E→A)</td>"
                    "<td>ABCDE <strong>○</strong></td></tr>"
                    "<tr><td>CD</td><td>CD → E → A → BC</td>"
                    "<td>ABCDE <strong>○</strong></td></tr>"
                    "<tr><td>B</td><td>B → D. 여기서 멈춘다</td><td>BD ×</td></tr>"
                    "<tr><td>C · D · BD</td><td>넓어지지 않는다</td><td>×</td></tr>"
                    "</table>"
                    "<p>후보키는 <strong>A · E · BC · CD 넷</strong>이다. "
                    "A나 E를 품은 두 속성 집합(AB · CE …)은 더 작은 후보키를 안고 있으므로 "
                    "최소성을 잃어 후보키가 아니다.</p>"
                ),
                "each": [
                    "① BC와 CD도 후보키다. 둘 다 폐포가 ABCDE까지 넓어진다.",
                    "② CD가 빠졌다. CD → E → A → BC 로 전체가 된다.",
                    "③ BC가 빠졌다. B → D 를 쓰면 CD를 얻고, 거기서 E와 A로 이어진다.",
                    "④ (정답) A · E · BC · CD 넷이다.",
                    "⑤ B는 후보키가 아니다. B의 폐포는 BD에서 멈춘다 — C가 없으면 "
                    "CD → E 를 쓸 수 없다.",
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # 11 충돌 직렬가능성
    #   S: r1(A) r2(A) w1(B) r3(B) w2(A) w3(A)
    #   r1(A)-w2(A): T1→T2 / r2(A)-w3(A),w2(A)-w3(A): T2→T3
    #   r1(A)-w3(A): T1→T3 / w1(B)-r3(B): T1→T3
    #   비순환 → 직렬가능, 위상 순서는 T1 → T2 → T3 하나뿐
    # ═══════════════════════════════════════════════════════════════
    {
        "area": "데이터베이스론",
        "lead": None,
        "passage": None,
        "questions": [
            {
                "type": "트랜잭션",
                "stem": "이 스케줄에 대한 판정으로 옳은 것은?",
                "material": (
                    '<div class="box">'
                    '<div class="box-title">&lt;스케줄 S&gt;</div>'
                    '<table class="data">'
                    "<tr><th>시각</th><th>1</th><th>2</th><th>3</th><th>4</th>"
                    "<th>5</th><th>6</th></tr>"
                    "<tr><td>T1</td><td>read(A)</td><td></td><td>write(B)</td>"
                    "<td></td><td></td><td></td></tr>"
                    "<tr><td>T2</td><td></td><td>read(A)</td><td></td><td></td>"
                    "<td>write(A)</td><td></td></tr>"
                    "<tr><td>T3</td><td></td><td></td><td></td><td>read(B)</td>"
                    "<td></td><td>write(A)</td></tr>"
                    "</table>"
                    '<p class="note">※ 같은 자료를 다루는 두 연산 가운데 적어도 하나가 write이면 '
                    "충돌한다.</p>"
                    "</div>"
                ),
                "choices": [
                    "충돌 직렬가능하지 않다", "충돌 직렬가능하며, 동치 직렬 순서는 T2 → T1 → T3 이다", "충돌 직렬가능하며, 동치 직렬 순서는 T3 → T1 → T2 이다", "충돌 직렬가능하며, 동치 직렬 순서가 둘 이상이다", "충돌 직렬가능하며, 동치 직렬 순서는 T1 → T2 → T3 이다",
                ],
                "answer": 5,
                "explain": (
                    "<p>충돌하는 짝을 찾아 선행 그래프의 화살표를 그린다.</p>"
                    '<table class="data">'
                    "<tr><th>앞선 연산</th><th>뒤선 연산</th><th>자료</th><th>화살표</th></tr>"
                    "<tr><td>T1 read(A) · 1</td><td>T2 write(A) · 5</td><td>A</td>"
                    "<td>T1 → T2</td></tr>"
                    "<tr><td>T1 read(A) · 1</td><td>T3 write(A) · 6</td><td>A</td>"
                    "<td>T1 → T3</td></tr>"
                    "<tr><td>T1 write(B) · 3</td><td>T3 read(B) · 4</td><td>B</td>"
                    "<td>T1 → T3</td></tr>"
                    "<tr><td>T2 read(A) · 2</td><td>T3 write(A) · 6</td><td>A</td>"
                    "<td>T2 → T3</td></tr>"
                    "<tr><td>T2 write(A) · 5</td><td>T3 write(A) · 6</td><td>A</td>"
                    "<td>T2 → T3</td></tr>"
                    "</table>"
                    "<p>화살표는 T1 → T2, T1 → T3, T2 → T3 뿐이다. "
                    "<strong>순환이 없으므로 충돌 직렬가능</strong>하다.</p>"
                    "<p>들어오는 화살표가 없는 것은 T1, T1을 뺀 뒤 없는 것은 T2다. "
                    "순서는 <strong>T1 → T2 → T3 하나로 정해진다.</strong></p>"
                ),
                "each": [
                    "① 선행 그래프에 순환이 없다. T3에서 나가는 화살표가 하나도 없다.", "② T1 read(A)가 T2 write(A)보다 앞서므로 T1이 먼저다.", "③ T3은 T1의 write(B)를 읽었다. T1보다 앞설 수 없다.", "④ 세 화살표가 세 트랜잭션을 한 줄로 꿴다. 위상 순서는 하나뿐이다.", "⑤ (정답) T1 → T2 → T3.",
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # 12 B+트리 리프 수와 높이
    #   35만 건 / 리프당 70개 = 5,000 리프
    #   5000 → ceil(5000/70)=72 → ceil(72/70)=2 → 1 (루트)
    #   레벨 4
    # ═══════════════════════════════════════════════════════════════
    {
        "area": "데이터베이스론",
        "lead": None,
        "passage": None,
        "questions": [
            {
                "type": "인덱스",
                "stem": "이 인덱스의 리프 노드 개수와 트리의 높이는?",
                "material": (
                    '<div class="box">'
                    '<div class="box-title">&lt;인덱스 조건&gt;</div>'
                    "<p>레코드 350,000건에 B+트리 인덱스를 만든다.</p>"
                    "<p>노드 하나는 자식(또는 엔트리)을 최대 100개까지 담을 수 있고, "
                    "평균 <strong>70%</strong>가 차 있다.</p>"
                    '<p class="note">※ 모든 레코드가 리프에 하나씩 엔트리를 갖는다.</p>'
                    '<p class="note">※ 높이는 루트를 포함한 레벨 수로 센다.</p>'
                    "</div>"
                ),
                "choices": [
                    "3,500개 · 높이 3",
                    "3,500개 · 높이 4",
                    "5,000개 · 높이 3",
                    "5,000개 · 높이 4",
                    "5,000개 · 높이 5",
                ],
                "answer": 4,
                "explain": (
                    "<p>노드가 70% 차 있으므로 실제로 담기는 것은 100 × 0.7 = "
                    "<strong>70개</strong>다.</p>"
                    "<p>리프 노드 수 = 350,000 ÷ 70 = <strong>5,000개</strong></p>"
                    '<table class="data">'
                    "<tr><th>레벨</th><th>노드 수</th><th>셈</th></tr>"
                    "<tr><td>1 (리프)</td><td>5,000</td><td>350,000 ÷ 70</td></tr>"
                    "<tr><td>2</td><td>72</td><td>5,000 ÷ 70 → 올림</td></tr>"
                    "<tr><td>3</td><td>2</td><td>72 ÷ 70 → 올림</td></tr>"
                    "<tr><td>4 (루트)</td><td>1</td><td>2 ÷ 70 → 올림</td></tr>"
                    "</table>"
                    "<p>레벨이 4개이므로 <strong>높이는 4</strong>다. 레벨 3에 노드가 2개만 "
                    "있어도 그 둘을 묶을 루트가 필요하다.</p>"
                ),
                "each": [
                    "① 3,500개는 노드를 100% 채운다고 본 값이다(350,000 ÷ 100). "
                    "높이 3도 그 가정에서 나온다.",
                    "② 리프 수가 3,500이면 그 위는 35 → 1 이라 높이가 3이다. 두 값이 서로 맞지 않는다.",
                    "③ 레벨 3에 노드가 2개 남는다. 루트가 하나 더 필요하다.",
                    "④ (정답) 리프 5,000개, 레벨 4개.",
                    "⑤ 레벨 4에서 이미 노드가 1개(루트)다. 더 올라갈 곳이 없다.",
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # 13 관계대수는 집합, SQL 은 다중집합
    #   R ⋈ S = 5행 (1x·1x·1y·2x·2x 중 실제로는 (1,x,p)(1,x,q)(1,y,p)(2,x,p)(2,x,q))
    #   π_A → {1, 2} = 2행 / SQL SELECT A → 5행
    # ═══════════════════════════════════════════════════════════════
    {
        "area": "데이터베이스론",
        "lead": None,
        "passage": None,
        "questions": [
            {
                "type": "관계대수",
                "stem": "㉠과 ㉡의 결과 행 수를 바르게 짝지은 것은?",
                "material": (
                    '<div class="box">'
                    '<div class="box-title">&lt;릴레이션&gt;</div>'
                    '<table class="data">'
                    "<tr><th colspan='2'>R</th><th></th><th colspan='2'>S</th></tr>"
                    "<tr><th>A</th><th>B</th><th></th><th>B</th><th>C</th></tr>"
                    "<tr><td>1</td><td>x</td><td></td><td>x</td><td>p</td></tr>"
                    "<tr><td>1</td><td>y</td><td></td><td>x</td><td>q</td></tr>"
                    "<tr><td>2</td><td>x</td><td></td><td>y</td><td>p</td></tr>"
                    "<tr><td>3</td><td>z</td><td></td><td>w</td><td>r</td></tr>"
                    "</table>"
                    '<div class="box-title">&lt;질의&gt;</div>'
                    "<p>㉠ π<sub>A</sub>(R ⋈ S) &nbsp;— 관계대수</p>"
                    "<p>㉡ SELECT A FROM R NATURAL JOIN S; &nbsp;— SQL</p>"
                    "</div>"
                ),
                "choices": [
                    "㉠ 2행 · ㉡ 2행", "㉠ 2행 · ㉡ 5행", "㉠ 3행 · ㉡ 5행", "㉠ 5행 · ㉡ 2행", "㉠ 5행 · ㉡ 5행",
                ],
                "answer": 2,
                "explain": (
                    "<p>먼저 자연조인 R ⋈ S 를 B로 맞춘다.</p>"
                    '<table class="data">'
                    "<tr><th>R의 행</th><th>맞는 S의 행</th><th>나오는 행 수</th></tr>"
                    "<tr><td>(1, x)</td><td>(x, p) · (x, q)</td><td>2</td></tr>"
                    "<tr><td>(1, y)</td><td>(y, p)</td><td>1</td></tr>"
                    "<tr><td>(2, x)</td><td>(x, p) · (x, q)</td><td>2</td></tr>"
                    "<tr><td>(3, z)</td><td>없다</td><td>0</td></tr>"
                    "<tr><td>합</td><td></td><td><strong>5</strong></td></tr>"
                    "</table>"
                    "<p>여기서 A만 뽑으면 1, 1, 1, 2, 2 다.</p>"
                    "<p><strong>관계대수의 릴레이션은 집합이다.</strong> π는 중복을 없애므로 "
                    "㉠ 은 {1, 2} — <strong>2행</strong>이다.</p>"
                    "<p><strong>SQL의 테이블은 다중집합이다.</strong> SELECT는 DISTINCT를 "
                    "붙이지 않는 한 중복을 그대로 두므로 ㉡ 은 <strong>5행</strong>이다.</p>"
                ),
                "each": [
                    "① ㉡ 에 DISTINCT가 없다. SQL은 중복을 지우지 않는다.", "② (정답) 관계대수의 π는 집합 연산이라 2행, SQL은 다중집합이라 5행이다.", "③ A에 남는 값은 1과 2뿐이다. (3, z)는 짝이 없어 조인에서 빠졌다.", "④ 두 값이 뒤바뀌었다. 중복을 지우는 쪽은 관계대수다.", "⑤ ㉠ 이 5행이 되려면 관계대수가 다중집합을 다뤄야 한다.",
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # 14 NOT IN 과 NOT EXISTS — NULL 앞에서 갈라진다
    #   관리자사번 집합에 NULL 이 있어 NOT IN 은 0행
    #   NOT EXISTS 는 상관 부질의라 박과장·최사원 2행
    # ═══════════════════════════════════════════════════════════════
    {
        "area": "데이터베이스론",
        "lead": None,
        "passage": None,
        "questions": [
            {
                "type": "SQL",
                "stem": "두 질의의 결과 행 수를 바르게 짝지은 것은?",
                "material": (
                    '<div class="box">'
                    '<div class="box-title">&lt;사원&gt;</div>'
                    '<table class="data">'
                    "<tr><th>사번</th><th>이름</th><th>관리자사번</th></tr>"
                    "<tr><td>1</td><td>김부장</td><td>NULL</td></tr>"
                    "<tr><td>2</td><td>이대리</td><td>1</td></tr>"
                    "<tr><td>3</td><td>박과장</td><td>1</td></tr>"
                    "<tr><td>4</td><td>최사원</td><td>2</td></tr>"
                    "</table>"
                    '<div class="box-title">&lt;질의&gt;</div>'
                    "<p>㉠ SELECT 이름 FROM 사원<br>"
                    "&nbsp;&nbsp;&nbsp;&nbsp;WHERE 사번 <strong>NOT IN</strong> "
                    "(SELECT 관리자사번 FROM 사원);</p>"
                    "<p>㉡ SELECT 이름 FROM 사원 e<br>"
                    "&nbsp;&nbsp;&nbsp;&nbsp;WHERE <strong>NOT EXISTS</strong> "
                    "(SELECT 1 FROM 사원 m WHERE m.관리자사번 = e.사번);</p>"
                    '<p class="note">※ 두 질의 모두 「부하 직원이 없는 사원」을 뽑으려 한 것이다.</p>'
                    "</div>"
                ),
                "choices": [
                    "㉠ 0행 · ㉡ 2행", "㉠ 0행 · ㉡ 0행", "㉠ 2행 · ㉡ 0행", "㉠ 2행 · ㉡ 2행", "㉠ 4행 · ㉡ 2행",
                ],
                "answer": 1,
                "explain": (
                    "<p>부질의가 내놓는 관리자사번 집합은 {NULL, 1, 1, 2} 다.</p>"
                    "<p>㉠ <code>사번 NOT IN (NULL, 1, 2)</code> 는 "
                    "<code>사번 &lt;&gt; NULL AND 사번 &lt;&gt; 1 AND 사번 &lt;&gt; 2</code> 로 풀린다. "
                    "<strong><code>사번 &lt;&gt; NULL</code> 은 참도 거짓도 아닌 UNKNOWN</strong>이라 "
                    "AND 로 묶인 전체가 결코 참이 되지 못한다. WHERE는 참인 행만 남기므로 "
                    "<strong>0행</strong>이다.</p>"
                    '<table class="data">'
                    "<tr><th>사번</th><th>㉠ NOT IN</th><th>㉡ NOT EXISTS</th></tr>"
                    "<tr><td>1 김부장</td><td>UNKNOWN</td><td>이대리·박과장이 있다 → 거짓</td></tr>"
                    "<tr><td>2 이대리</td><td>UNKNOWN</td><td>최사원이 있다 → 거짓</td></tr>"
                    "<tr><td>3 박과장</td><td>UNKNOWN</td><td>없다 → <strong>참</strong></td></tr>"
                    "<tr><td>4 최사원</td><td>UNKNOWN</td><td>없다 → <strong>참</strong></td></tr>"
                    "</table>"
                    "<p>㉡ 은 행을 하나씩 대조하는 상관 부질의다. "
                    "<code>m.관리자사번 = e.사번</code> 은 NULL 행에서 그냥 맞지 않을 뿐이라 "
                    "결과를 어지럽히지 않는다. <strong>2행</strong>이다.</p>"
                ),
                "each": [
                    "① (정답) ㉠ 은 NULL 때문에 0행, ㉡ 은 박과장·최사원 2행이다.", "② ㉡ 은 NULL에 걸리지 않는다. 부질의가 「맞는 행이 있느냐」만 보기 때문이다.", "③ 두 값이 뒤바뀌었다. NULL에 무너지는 쪽은 NOT IN 이다.", "④ 부질의 결과에 NULL이 없었다면 ㉠ 도 2행이 됐을 것이다. "
                    "여기서는 김부장의 관리자사번이 NULL이다.", "⑤ 4행은 조건을 아예 걸지 않은 행 수다.",
                ],
            },
        ],
    },
]
