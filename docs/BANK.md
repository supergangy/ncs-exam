# 기출은행 스키마 — 앱·웹 배포를 위한 설계

봉투모의고사 PDF는 중간 산출물이다. 목표는 **문항을 방대하게 쌓아
유형·키워드별로 한 문제씩 풀 수 있는 앱과 웹**이다.

이 문서는 그 데이터 모델과 옮겨가는 순서를 정한다. 문항 집필 규칙은 `PLAYBOOK.md`,
회차 사양은 각 `rounds/<회차>/README.md` 가 계속 맡는다.

---

## 0. 무엇을 보고 정했나

상용 앱 하나를 분석했다 — `com.odapnote.hangooksa` v1.19.3(한국사 오답노트).
Flutter + Firebase(Auth·Firestore·Analytics) + Play Billing, 46MB.
문항 **2,050** · 유형 **226** · 키워드 **2,474** · 시대 **23** · 단원 **165** 규모다.

배운 것과, 그대로 따르지 않은 것.

| 저쪽 설계 | 판단 |
|---|---|
| **선지마다 유형·해설을 따로 붙였다** (`ct1~ct5` · `cc1~cc5`) | **따른다.** 이게 「유형별 한 문제씩」의 핵심이다 — 5지선다 한 문항은 실제로 **5개 지식 조각**이다 |
| 선지를 `pc1~pc5` **와이드 컬럼**으로 펼쳤다 | **따르지 않는다.** 아래 1절 참조 |
| 문제를 **이미지**(`7001.png`)로 저장 | **따르지 않는다.** 우리는 텍스트 + 인라인 SVG다 |
| 무거운 콘텐츠는 원격 URL (`type_summary`) | **따른다.** 앱에는 인덱스만 |
| 집계를 미리 저장 (`keyword.c` · `type.count`) | **따른다.** 런타임 집계 안 함 |
| 사용자 진도는 **별도 로컬 SQLite** | **따른다.** 콘텐츠 DB와 섞지 않는다 |
| **오답노트 PDF가 유료 기능** | 우리는 **이미 갖고 있다** — Jinja2 → Chrome → PDF |

### 선지를 정규화하는 이유

저쪽이 와이드 컬럼을 쓴 것은 5지선다가 고정이고 **모바일 오프라인 단일행 읽기**가
가장 잦은 질의였기 때문이다. 합리적인 선택이다.

우리의 대표 질의는 다르다. **「이 유형의 선지만 모아 보기」** 가 핵심 기능이므로
선지가 검색 단위다. 와이드면 `ct1~ct5` 다섯 컬럼에 각각 색인을 걸고 `UNION` 을
써야 한다. 행으로 정규화하면 `JOIN` 하나다. 규모도 걸림돌이 아니다 —
2,000문항 × 5 = **선지 1만 행**이면 SQLite 에서 아무것도 아니다.

---

## 1. 스키마

콘텐츠 DB(읽기 전용으로 배포)와 사용자 DB(기기 로컬)를 **분리**한다.

### 1-A. 콘텐츠 DB

```sql
-- 회차 --------------------------------------------------------------
CREATE TABLE round (
  id          INTEGER PRIMARY KEY,
  tag         TEXT    NOT NULL UNIQUE,   -- 'r4_korail'
  org         TEXT    NOT NULL,          -- '한국철도공사'
  title       TEXT    NOT NULL,
  total_q     INTEGER NOT NULL,
  total_min   INTEGER NOT NULL,
  snapshot_id TEXT,                      -- 근거 스냅샷 (D55) 'S-20260803-e69ff1'
  built_at    TEXT
);

-- 지문·자료 : 세트문항이 공유한다 -------------------------------------
CREATE TABLE passage (
  id     INTEGER PRIMARY KEY,
  kind   TEXT NOT NULL CHECK (kind IN ('passage','material')),
  title  TEXT,
  body   TEXT NOT NULL,       -- 허용 태그만 (SPEC 4절)
  figure TEXT                 -- 인라인 SVG
);

-- 유형 : reviews/cluster.py 산출이 씨앗 -------------------------------
CREATE TABLE type (
  id                INTEGER PRIMARY KEY,
  name              TEXT NOT NULL UNIQUE,
  area              TEXT NOT NULL,       -- 8영역 중 하나
  parent_id         INTEGER REFERENCES type(id),
  n_items           INTEGER NOT NULL DEFAULT 0,   -- 미리 계산
  evidence_n        INTEGER,             -- 이 유형을 말한 후기 건수
  evidence_snapshot TEXT,                -- 그 건수의 기준 스냅샷 (D55)
  cluster_rep       TEXT                 -- 군집 대표 문구
);

-- 문항 ---------------------------------------------------------------
CREATE TABLE item (
  id         INTEGER PRIMARY KEY,
  round_id   INTEGER REFERENCES round(id),
  no         INTEGER NOT NULL,
  area       TEXT    NOT NULL,
  type_id    INTEGER REFERENCES type(id),
  passage_id INTEGER REFERENCES passage(id),
  lead       TEXT,
  stem       TEXT    NOT NULL,           -- **평문.** 태그 금지 (규칙 3-7 · D46)
  figure     TEXT,                       -- 인라인 SVG
  answer     INTEGER NOT NULL CHECK (answer BETWEEN 1 AND 5),
  score      REAL    NOT NULL DEFAULT 1,
  difficulty TEXT,
  UNIQUE (round_id, no)
);

-- 선지 : **행으로 정규화** -------------------------------------------
CREATE TABLE choice (
  id        INTEGER PRIMARY KEY,
  item_id   INTEGER NOT NULL REFERENCES item(id) ON DELETE CASCADE,
  ord       INTEGER NOT NULL CHECK (ord BETWEEN 1 AND 5),
  text      TEXT    NOT NULL,
  is_answer INTEGER NOT NULL DEFAULT 0,
  explain   TEXT,                        -- 이 선지가 왜 맞고/틀린지  ← (b)에서 채운다
  trap      TEXT,                        -- 어떤 오해가 이 선지로 오는가
  type_id   INTEGER REFERENCES type(id), -- **선지별 유형**
  UNIQUE (item_id, ord)
);

-- <보기> 조합형의 ㄱㄴㄷ ---------------------------------------------
CREATE TABLE proposition (
  id      INTEGER PRIMARY KEY,
  item_id INTEGER NOT NULL REFERENCES item(id) ON DELETE CASCADE,
  label   TEXT    NOT NULL,              -- 'ㄱ'
  text    TEXT    NOT NULL,
  truth   INTEGER,                       -- 1 참 / 0 거짓
  UNIQUE (item_id, label)
);

-- 해설 · 출제 이유서 --------------------------------------------------
CREATE TABLE explanation (
  item_id INTEGER PRIMARY KEY REFERENCES item(id) ON DELETE CASCADE,
  body    TEXT NOT NULL
);
CREATE TABLE rationale (                 -- 네 칸
  item_id INTEGER PRIMARY KEY REFERENCES item(id) ON DELETE CASCADE,
  basis   TEXT,   -- 근거
  design  TEXT,   -- 설계
  trap    TEXT,   -- 함정
  verify  TEXT    -- 검증
);

-- 키워드 : 다대다 -----------------------------------------------------
CREATE TABLE keyword (
  id      INTEGER PRIMARY KEY,
  text    TEXT NOT NULL UNIQUE,
  n_items INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE item_keyword (
  item_id    INTEGER NOT NULL REFERENCES item(id) ON DELETE CASCADE,
  keyword_id INTEGER NOT NULL REFERENCES keyword(id),
  PRIMARY KEY (item_id, keyword_id)
);

CREATE INDEX idx_item_type    ON item(type_id);
CREATE INDEX idx_item_area    ON item(area, type_id);
CREATE INDEX idx_choice_type  ON choice(type_id);
CREATE INDEX idx_choice_item  ON choice(item_id, ord);
CREATE INDEX idx_ik_keyword   ON item_keyword(keyword_id);
```

### 1-B. 사용자 DB (기기 로컬 · 서버로 올리지 않아도 동작)

```sql
CREATE TABLE attempt (
  id         INTEGER PRIMARY KEY,
  item_id    INTEGER NOT NULL,
  chosen     INTEGER,                    -- 고른 선지 (미제출이면 NULL)
  correct    INTEGER NOT NULL,
  elapsed_ms INTEGER,
  at         TEXT    NOT NULL
);
CREATE TABLE wrong_note (
  item_id       INTEGER PRIMARY KEY,
  wrong_count   INTEGER NOT NULL DEFAULT 1,
  last_wrong_at TEXT,
  resolved_at   TEXT,
  memo          TEXT
);
CREATE TABLE srs (                       -- 간격 반복
  item_id  INTEGER PRIMARY KEY,
  ease     REAL    NOT NULL DEFAULT 2.5,
  interval INTEGER NOT NULL DEFAULT 0,
  due      TEXT
);
CREATE INDEX idx_attempt_item ON attempt(item_id, at);
CREATE INDEX idx_srs_due      ON srs(due);
```

### 1-C. 핵심 질의가 한 줄이 되는지 확인

```sql
-- 유형별로 아직 안 푼 문항 하나
SELECT i.* FROM item i
  LEFT JOIN attempt a ON a.item_id = i.id
 WHERE i.type_id = :type AND a.id IS NULL
 ORDER BY RANDOM() LIMIT 1;

-- 키워드별
SELECT i.* FROM item i
  JOIN item_keyword k ON k.item_id = i.id
 WHERE k.keyword_id = :kw;

-- **유형별 선지만 모아 보기** — 정규화한 값이 여기서 나온다
SELECT i.stem, c.ord, c.text, c.explain FROM choice c
  JOIN item i ON i.id = c.item_id
 WHERE c.type_id = :type;

-- 오답노트 PDF 대상
SELECT i.* FROM item i
  JOIN wrong_note w ON w.item_id = i.id
 WHERE w.resolved_at IS NULL ORDER BY w.wrong_count DESC;
```

---

## 2. 지금 있는 것 / 없는 것

`content/*.py` 를 실측했다 — **전체 140문항**(r1 50 · r2·r3·r4 각 30).

| 스키마 칸 | 지금 상태 |
|---|---|
| `item.stem` `choice.text` `item.answer` | ✔ 140문항 전부 |
| `item.area` `item.lead` `item.figure` `passage.*` | ✔ |
| `explanation.body` | ✔ (`explain`) |
| `rationale.*` 네 칸 | **90문항만.** r1의 50문항은 없다 |
| `item.type_id` | **없다.** `reviews/cluster.py` 산출을 씨앗으로 붙인다 |
| `item_keyword` | **없다.** 같은 산출에서 |
| `choice.explain` `choice.trap` | **없다** ← 이게 (b) |
| `item.difficulty` `item.score` | 없다 (회차 `PROFILE` 에 회차 단위로만) |
| `proposition.*` | 조합형 문항의 `<보기>` 가 지문 안 HTML로 들어가 있어 **분해 필요** |

### `choice.explain` 은 절반이 자동으로 나온다

`why["함정"]` 이 이미 선지를 번호로 지목한다 — 「② 480m 가 첫 번째 만남의 위치다」,
「①·③은 지문에 나오지만 일부만 덮는다」.

| 함정이 지목한 선지 수 | 문항 |
|---|---|
| 4~5개 | 15 |
| 2~3개 | 30 |
| 1개 | 26 |
| 0개 | 69 (대부분 r1) |

**2개 이상 지목이 45문항** — `why` 를 가진 90문항의 절반이다.
`①②③④⑤` 를 기준으로 문장을 쪼개면 초안이 나오고, 사람이 다듬는다.
나머지는 새로 쓴다. **없던 것을 만드는 게 아니라 쪼개는 일이다.**

---

## 3. 옮겨가는 순서

각 단계는 앞 단계 없이 시작하지 않는다.

| 단 | 할 일 | 산출 | 상태 |
|---|---|---|---|
| **1** | `tools/export_bank.py` — 회차와 은행을 훑어 내보낸다 | `app/data/bank.json` 292문항 549KB | **됐다** |
| **2** | 유형 붙이기 | 문항의 `type` 을 그대로 썼다 — 전산 62종 · NCS 83종 | **됐다** |
| **3** | 키워드 다대다 | 과목별 용어 사전으로 305개 | **됐다** |
| **4** | `choice.explain` 분해 | **필요 없었다** — `each` 가 이미 선지별 단평이다 | **됐다** |
| **5** | 화면 (유형 목록 → 문항 → 채점 → 해설) | `app/` PWA | **됐다** |
| **6** | 앱 — 콘텐츠 번들 + 기록 로컬 + 오답노트 PDF | PWA + `tools/wrongnote_pdf.py` | **됐다** |
| **7** | 회차 모드 — 타이머·OMR·제출 후 채점 | `app/` `#/exams`~`#/result` | **됐다** |
| **8** | Flutter 이식 · 배포 | — | 남았다 |

### 하면서 달라진 것

- **SQLite 를 쓰지 않았다.** 292문항이 JSON 으로 549KB 라 브라우저가 통째로 안는다.
  `sql.js` 를 얹으면 wasm 1.5MB 가 콘텐츠보다 커진다. 2,000문항쯤에서 다시 본다
- **`choice.explain` 을 새로 쓸 필요가 없었다.** 문항마다 `each` 로 선지 단평을
  이미 달아 왔다. 설계 문서가 「없다」고 적은 것은 **회차 140문항만 보고 센 값**이었다
- **관리자 자료를 파일 단위로 갈랐다.** 위험도·출제이유서를 `admin.json` 으로 빼서
  학습자 payload 에 아예 넣지 않는다 (`app/README.md`)
- **회차 문항 번호의 근거를 `AREAS` 로 옮겼다.** 처음엔 알파벳순 glob 으로 읽었는데
  `build.py` 는 `config.py` 의 선언 순서를 쓴다. 지금은 우연히 같지만 파일 이름을
  다르게 붙인 회차가 생기면 **앱 번호가 인쇄본과 조용히 어긋난다.** 문항 수도
  `AREAS` 기대값과 대조해 다르면 멈춘다
- **오답노트 PDF 는 파이프라인을 새로 만들지 않았다.** `build.py` 를 불러
  `solution.html.j2` 그대로 굽는다 — `tools/wrongnote_pdf.py`

**1~3단은 지금 할 수 있다.** 4단은 문항이 더 쌓인 뒤가 싸다 — 회차마다 30문항씩
늘어나는데 지금 분해하면 같은 일을 회차마다 되풀이한다.

### 되돌릴 수 있게

`bank.db` 는 **파생물**이다. 진실은 계속 `content/*.py` 다.
`export_bank.py` 를 언제든 다시 돌려 DB를 재생성할 수 있어야 하고,
DB를 손으로 고치지 않는다. `reviews/db.json` ↔ `--rebuild` 와 같은 관계다.

---

## 4. 배포 형태

| 층 | 선택 | 왜 |
|---|---|---|
| 콘텐츠 | SQLite 파일 하나 | 2,000문항이면 몇 MB. 서버 DB가 필요 없다 |
| 웹 | 파이썬(FastAPI/Flask) + 같은 SQLite 읽기 전용 | 이미 파이썬 저장소다 |
| 앱 | Flutter + 번들 SQLite 씨앗 + 서버 델타 | 한국사 앱과 같은 구조. iOS/Android 한 코드 |
| 회원·결제 | 나중에. **없이도 동작해야 한다** | 오프라인 우선 |
| PDF | **기존 파이프라인 재사용** | 오답노트 PDF가 남들의 과금 지점이다 |

---

## 5. 넘지 않는 선

- **문항은 자작만 올린다.** 기출 복원은 하지 않는다. 후기에서 가져오는 것은
  **소재**이고, 지문·선지·수치는 전부 새로 쓴다 (`SPEC.md` 2절)
- 분석 대상 앱의 **문제·선지·해설은 열지 않았다.** 스키마와 필드명까지만 봤다.
  남의 콘텐츠는 저작물이다
- 근거 건수를 적을 때는 **스냅샷 ID를 함께** 적는다 (`D55`),
  비율의 분모는 **소재를 적은 후기**다 (`D56`)

## 6. 배포 — 공개 저장소로 분리

`app/` 의 산출물만 별도 **공개** 저장소로 옮겨 GitHub Pages 로 띄운다.
집필·검증 파이프라인(`bank/`·`reviews/`·`tools/`)이 있는 이 저장소는 계속 비공개다.

- 배포 URL: https://supergangy.github.io/ncs-exam-app/
- 소스: https://github.com/supergangy/ncs-exam-app (public)
- 접근 제한 없음 — 사용자 결정. `data/admin.json` 도 정적 파일이라
  URL을 알면 누구나 받을 수 있다 (`app/README.md` 에 이미 적힌 대로,
  클라이언트 암호 확인은 보안 장치가 아니다)

### 다시 배포하는 법

```bash
python tools/export_bank.py                      # bank.json · admin.json 갱신
# sw.js 의 VERSION 을 올린다 — 안 올리면 옛 캐시가 계속 나간다
rm -rf /tmp/deploy && mkdir /tmp/deploy
cp -r app/* /tmp/deploy/
cd /tmp/deploy && git init -q -b main
git remote add origin https://github.com/supergangy/ncs-exam-app.git
git add -A && git commit -q -m "재배포 — <바뀐 것>"
git push -f origin main                           # 이력을 안 남기고 매번 새로 편다
```

실제 크롬(GitHub Pages, HTTPS)에서 서비스 워커가 정상 등록·활성화되고
9개 파일이 캐시되는 것을 확인했다 — `ncsbank-v3`. 내장 미리보기 브라우저가
막고 있던 바로 그 부분이다. `admin.json` 은 캐시에 없다(설계대로 관리자 모드일
때만 받는다).
