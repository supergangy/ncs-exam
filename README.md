# NCS 봉투모의고사

시판 봉투모의고사를 분석해 만드는 **NCS 직업기초능력평가 모의고사** 제작 프로젝트.
Python으로 문항 데이터를 관리하고, HTML 템플릿을 거쳐 **문제집·해설집 PDF 2종**을 생성한다.

## 회차

기관마다 문항 수와 영역 구성이 다르므로 **회차별 폴더**로 나눈다.
빌드기·조판기·스캐너·플레이북은 회차와 무관하게 한 벌만 유지한다.

| 회차 | 기관 | 사양 | 상태 |
|---|---|---|---|
| [`r1_public`](rounds/r1_public/README.md) | 범용 공기업 (`○○공사`) | 50문항 / 60분 · 8영역 · 피듈형 | **완성** — 문제집 30쪽 / 해설집 25쪽 |
| [`r2_nhis`](rounds/r2_nhis/README.md) | 국민건강보험공단 | 60문항 / 60분 · 의사소통·수리·문제해결 각 20 | 설계 완료, 집필 대기 |

```bash
python build.py                      # 기본 회차(r1_public)
python build.py --round r2_nhis      # 다른 회차
```

회차별 사양·블루프린트·이력은 각 `rounds/<회차>/README.md`, 기계가 읽는 값은 `config.py`에 있다.

### 제작 순서 — 후기 먼저, 판단은 사용자가

```
① 후기를 담는다          「수집기 켜기」 바로가기
② 제작 차수 시작
③ 신뢰도를 먼저 분석한다   python reviews/report.py --consensus <기관>
④ 소재를 확인한다         python reviews/report.py --brief <기관>
⑤ 제작 계획서를 쓴다      신뢰도 순으로 정리 → 문항 배치안        ← 집필 전에
⑥ 계획서를 제시하고 승인을 받는다                              ← 건너뛰지 않는다
⑦ 집필 → selfcheck → 감수 → 확인
```

**③이 먼저다.** 후기가 많아지면 **몇 명이 독립적으로 같은 말을 했는가**가 그 정보의 무게다.
`--consensus` 가 겹치는 소재를 신뢰도 순(높음 3건↑ / 중간 2건 / 낮음 1건)으로 정렬하고,
체감 난이도·문항 수 같은 수치는 **응답자 중 다수 비율**로 낸다.
「제주도 애견 파크」와 「반려견 놀이공원」처럼 표현이 달라도 같은 소재면 묶어서 센다.

**⑤ 계획서에 담을 것** — 신뢰도 높은 소재부터 어느 영역 몇 번에 배치할지,
기존 설계와 충돌하는 지점, 확정할 것과 보류할 것.

**⑥을 반드시 거친다.** 계획서를 표로 보이고 **「이러이러한 내용이 있는데 어떤 식으로 할까요?」로 묻는다.**
설계 변경을 집필자가 확정하지 않는다. 표본이 작을 때 무엇을 경향으로 볼지는 판단이 들어가는 문제다.

### 새 회차를 추가할 때

1. `rounds/<이름>/config.py` — `BRAND` · `EXAM_TITLE` · `EXAM_ROUND` · `FILE_TAG` · `TOTAL_Q` · `TOTAL_MIN` · `AREAS` · `PROFILE`
2. `rounds/<이름>/content/` — `AREAS`에 적은 모듈 이름대로 파일 생성
3. `rounds/<이름>/README.md` — 그 회차의 프로파일과 블루프린트

`PROFILE`에는 **기관마다 달라지는 목표치**를 담는다. 세트문항 비율, 각주 개수, `<보기>` 개수,
지문 중앙값 같은 것들이다. 플레이북의 규칙과 달리 이 값들은 회차 소속이다(`D48`).

## 다른 컴퓨터에서 이어서 작업하기

```bash
git clone https://github.com/<계정>/ncs-exam.git
cd ncs-exam
pip install jinja2 pypdf reportlab
python build.py
```

`out/<회차>/` 에 문제집·해설집 PDF가 생성되면 환경 구성이 끝난 것이다.

### 사전 요구사항

- **Python 3.10+**
- **Chrome 또는 Edge** — HTML을 PDF로 변환할 때 헤드리스 모드로 사용한다.
  `build.py` 상단 `CHROME_CANDIDATES` 에 등록된 경로를 순서대로 탐색하므로, 다른 위치에 설치돼 있으면 그 목록에 경로를 추가한다.
- **한글 폰트** — 맑은 고딕(발문·선지), 바탕(지문). Windows 기본 폰트라 별도 설치가 필요 없다.
  macOS·Linux에서는 `templates/*.j2` 의 `font-family` 를 Noto Sans KR / Noto Serif KR 등으로 바꿔야 한다.

### 작업을 이어가기 전에 읽을 것

1. **[`docs/PLAYBOOK.md`](docs/PLAYBOOK.md) — 작업별 참조서.** 지문·자료·발문·선지·오답·조건추리·해설을 만들 때 각 절의 `사전 준비 → 규칙 → 자가검증`을 그대로 따른다. 실제 발생한 결함 39건이 규칙과 연결돼 있다. **문항을 만들기 전에 반드시 해당 절을 펼친다.**
2. [`SPEC.md`](SPEC.md) — 데이터 스키마, 허용 HTML, 분량·난이도·정답분포·지면배치 기준
3. [`docs/PLAN.md`](docs/PLAN.md) — 50문항 블루프린트, 감수 13항목, 문체 감수 기준
4. [`docs/CORPUS_ANALYSIS.md`](docs/CORPUS_ANALYSIS.md) — 시판본 실측 수치. **0절의 신뢰도 등급을 먼저 볼 것**
5. [`WORKLOG.md`](WORKLOG.md) — 시간순 이력(무엇을 왜 했는지)

## 폴더 구조

```
├─ build.py              회차 선택 + 검증 + 렌더 + PDF + 쪽번호 + 자동 로그
├─ layout.py             펼침면 기준 조판기 (지문/문항 좌우 분리 · 여백 채움)
├─ SPEC.md               집필 스펙 (스키마 · 허용 HTML · 강조 기준 · 분량)
├─ WORKLOG.md            작업 로그 (진행 현황표 + 시간순 기록, append-only)
├─ rounds/               ★ 회차별로 달라지는 것만 여기 둔다
│  ├─ r1_public/         범용 공기업 50문항
│  │  ├─ config.py          기관명 · 문항수 · 시간 · 영역 배분 · PROFILE
│  │  ├─ README.md          회차 사양 · 블루프린트 · 제작 이력
│  │  └─ content/           a1_communication.py … a8_ethics.py
│  └─ r2_nhis/           국민건강보험공단 60문항
│     ├─ config.py
│     ├─ README.md
│     └─ content/           c1_communication.py · c2_math.py · c3_problem.py
├─ tools/selfcheck.py    자가검증 스캐너 (집필 직후 · 감수 전에 실행)
├─ corpus/               시판본 분석 파이프라인 (원문·추출본은 커밋하지 않음)
├─ reviews/              필기후기 → 기관별·시기별 출제경향 DB (후기 원문은 커밋하지 않음)
│  └─ report.py --brief <기관>     최신 시행분 소재 브리프 (NCS/전공/법률 분리)
├─ 수집기 켜기.bat                 더블클릭 — 후기 수집기 실행
├─ 후기 현황 보기.bat              더블클릭 — 수집 현황 + 소재 브리프
├─ 바탕화면 바로가기 만들기.bat     최초 1회 — 위 둘을 바탕화면에 등록
├─ templates/            exam.html.j2 / solution.html.j2 (회차 무관)
├─ docs/
│  ├─ PLAYBOOK.md           작업별 참조서 — 집필 전에 펼친다
│  ├─ PLAN.md               1회 분석 · 설계 · 감수 이력 전문
│  ├─ CORPUS_ANALYSIS.md    시판본 실측 수치 (0절 신뢰도 등급 먼저 볼 것)
│  ├─ INSTITUTION_PROFILES.md  기관별 출제 비율 — 새 회차 설계의 출발점
│  └─ ANSWER_DISTRIBUTION.md   기관별 정답 분포
├─ logs/<회차>/          빌드 로그 (실행마다 자동 생성)
└─ out/<회차>/           생성된 PDF
```

## 빌드

```bash
python build.py --preview   # 미완성 상태로 현재까지 작성된 문항만 빌드
python build.py             # 50문항 완성 후 최종 빌드
```

문항을 쓰거나 고친 뒤에는 **빌드 전에** 자가검증 스캐너를 돌린다. 치명 0건이 통과 조건이다.

```bash
python tools/selfcheck.py
```

### 고쳐 가며 확인할 때 — `--html`

문구를 손볼 때마다 PDF를 굽지 않는다. `--html` 은 블록 높이 실측과 펼침면 재배치까지 평소대로 하고
**PDF 변환과 쪽번호 스탬프만 건너뛴다.** 훨씬 빠르고, 빌드 로그도 `WORKLOG.md` 에 쌓이지 않는다.

```bash
python build.py --html
```

`out/exam.html` 을 브라우저로 열어 글자·볼드·밑줄을 확인하고, **실제 쪽나눔은 Ctrl+P
(A4 · 배율 100% · 여백 없음) 인쇄 미리보기**로 본다. 쪽번호는 PDF 후처리라 HTML에는 찍히지 않는다.
확정되면 그때 `python build.py` 로 PDF 2종을 만든다.

실행하면 다음을 자동으로 수행한다.

1. `content/*.py` 를 순서대로 적재하고 문항 번호 01~50을 부여 (세트 리드문의 `[NN~NN]` 도 자동 교정)
2. 구조 검증 — 선택지 5개, 정답 1~5, 선지별 단평 5개, 중복 선택지, 정답 분포, 3연속 동일 정답
3. HTML 렌더 → Chrome 헤드리스로 PDF 변환 → 쪽번호 스탬프
4. `logs/build_*.log` 생성 및 `WORKLOG.md` 에 `[빌드]` 항목 자동 추가

## 문항 추가 방법

`content/<영역>.py` 의 `BLOCKS` 리스트에 블록을 추가한다. 블록 하나는 지문 1개와 거기 딸린 문항 1~2개다.

```python
{
    "area": "정보능력",
    "lead": "[28~29] 다음 자료를 보고 물음에 답하시오.",  # 단독 문항이면 None
    "passage": "<p>...</p>",                              # 세트 공유 지문, 없으면 None
    "questions": [{
        "type": "자료해석",
        "stem": "...",
        "material": "<table class=\"data\">...</table>",  # 문항 전용 자료
        "choices": [...5개...],
        "answer": 3,
        "explain": "<p>...</p>",
        "each": [...5개, ①~⑤ 단평...],
    }],
}
```

허용 HTML 태그와 클래스는 `SPEC.md` 4절에 고정돼 있다. **텍스트 필드는 이스케이프 책임이 작성자에게 있다** (`<` → `&lt;`).

## 품질 기준

문항을 추가하거나 고칠 때는 아래를 지킨다. 근거는 `docs/PLAN.md`에 있다.

- 모든 문항은 **업무 상황 → 자료 분석 → 추론 → 의사결정** 흐름을 갖는다. 개념 정의를 묻지 않는다.
- 계산·조건추리 문항은 **Python으로 전수 재계산·전수 탐색해 정답 유일성을 확인**한 뒤 확정한다.
  오답 선지도 실제 오류 경로에서 그 값이 재현되는지 검증한다.
- 지문은 AI 문투를 배제한다. 걸러낼 표현 24종과 채택 문체는 `docs/PLAN.md`의 문체 감수 절 참고.
- 정답은 ①~⑤에 고르게 배치하고 3연속 동일 정답을 만들지 않는다.

## 저작권

- 모든 지문·자료·문항은 **새로 작성한 창작물**이다. 통계는 문항 구성을 위해 재구성한 가상 자료다.
- 설계 근거로 참고한 시판 봉투모의고사의 원문·추출 텍스트는 이 저장소에 포함하지 않는다.
  `.gitignore` 에서 `ref_dump.txt`, `scratchpad/` 를 차단하고 있다.
