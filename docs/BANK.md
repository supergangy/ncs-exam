# NCS PASS 스키마 — 앱·웹 배포를 위한 설계

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

- 배포 URL: https://supergangy.github.io/ncs-pass-app/
- 소스: https://github.com/supergangy/ncs-pass-app (public)
- **옛 주소** https://supergangy.github.io/ncs-exam-app/ 는 안내 페이지만 남겼다.
  이력서·포트폴리오·PDF 에 그 주소가 박혀 있어 살려 둔다.
  안내 페이지에는 **자기 자신을 등록 해제하는 `sw.js`** 를 같이 올렸다 —
  예전에 방문한 브라우저에는 옛 워커가 남아 캐시에서 옛 앱을 계속 내주므로,
  리다이렉트 페이지만 올리면 그 화면이 보이지 않는다.
- `localStorage` 는 origin 단위다. `supergangy.github.io` 안에서 경로만 바뀌었으므로
  **기존 사용자의 학습 기록은 새 주소에서 그대로 보인다.**
- 접근 제한 없음 — 사용자 결정. `data/admin.json` 도 정적 파일이라
  URL을 알면 누구나 받을 수 있다 (`app/README.md` 에 이미 적힌 대로,
  클라이언트 암호 확인은 보안 장치가 아니다)

### 벌어졌는지 먼저 잰다

배포는 **수동 절차라 파이프라인에 묶여 있지 않다.** 문항을 늘리고 커밋해도
배포본은 그대로이고, 커밋 기록만 보면 그것을 알 수 없다.
실제로 배포본이 **540문항에서 멈춰** 있던 적이 있다(2026-08-18) —
전산직 300문항 완성과 새 두 영역이 반영되지 않았다.

```bash
python tools/deploy_check.py
```

로컬과 배포본의 문항 수·영역별 차이·`sw.js` 캐시 버전을 함께 보여 준다.
벌어져 있으면 exit 1 이다.

### 재제작 판 — `/next/` 에 나란히 둔다

React 로 다시 만든 판은 **기존 판을 덮지 않고 하위 경로에 올린다.**

| 주소 | 무엇 |
|---|---|
| `…/ncs-pass-app/` | 기존 판 (바닐라 `app/`). 쓰던 사람의 앱이다 |
| `…/ncs-pass-app/next/m/` | 재제작 **모바일** 판 |
| `…/ncs-pass-app/next/` | 재제작 **PC** 판 (아직 배선 확인 화면) |

PC 판이 끝나지 않은 동안 기존 판을 덮으면, PC 로 들어온 사람에게 배선 확인
화면이 보인다. 실기기에서 확인한 뒤 옮긴다.

`localStorage` 는 origin 단위라 **두 판이 같은 기록을 본다.** 새 판에서 푼 것이
기존 판에도 보이고 그 반대도 같다 — 옮겨 갈 때 기록이 이어진다는 뜻이기도 하다.

**루트 `sw.js` 에 한 줄을 넣었다.** scope 가 배포 루트라 `/next/` 까지 가로채는데,
stale-while-revalidate 전략이라 새로 올려도 한 박자 늦게 반영된다.

```js
if (url.pathname.includes('/next/')) return;   // 자기 워커가 맡는다
```

재제작 판의 워커는 **만들어 낸다** — Vite 가 해시 붙은 이름을 내므로 캐시 목록을
손으로 적으면 빌드마다 어긋난다. 버전도 파일 목록·크기의 해시로 정해 **올리는 것을
잊을 수 없게** 했다.

```bash
cd web && npx vite build && node tool/make_sw.mjs
```

폰트 509KB 는 install 에 담지 않는다 — PC 판만 쓰므로 모바일에서 미리 받을 이유가
없다. 요청될 때 담긴다. 배포본에서 확인한 캐시는 17개(껍데기·문항·아이콘)다.

### 다시 배포하는 법

```bash
python tools/export_bank.py                      # bank.json · admin.json 갱신
# sw.js 의 VERSION 을 올린다 — 안 올리면 옛 캐시가 계속 나간다
rm -rf /tmp/deploy && mkdir /tmp/deploy
cp -r app/* /tmp/deploy/
cd /tmp/deploy && git init -q -b main
git remote add origin https://github.com/supergangy/ncs-pass-app.git
git add -A && git commit -q -m "재배포 — <바뀐 것>"
git push -f origin main                           # 이력을 안 남기고 매번 새로 편다
```

실제 크롬(GitHub Pages, HTTPS)에서 서비스 워커가 정상 등록·활성화되고
9개 파일이 캐시되는 것을 확인했다 — `ncsbank-v3`. 내장 미리보기 브라우저가
막고 있던 바로 그 부분이다. `admin.json` 은 캐시에 없다(설계대로 관리자 모드일
때만 받는다).

## 7. Flutter 앱 — 네이티브 포팅

`app/` (PWA)과 같은 `bank.json`·`admin.json` 을 에셋으로 번들해 그대로 이식했다.
서버 델타는 없다 — 웹판과 같은 완전 오프라인 우선 구조다. 화면·저장 형식·SM-2
간격 알고리즘·검색 로직을 웹판과 1:1로 맞췄다(`mobile/lib/`).

| 층 | 파일 |
|---|---|
| 데이터 모델 | `models.dart` — `bank.json`/`admin.json` 의 축약 키를 그대로 씀 |
| 로컬 기록 | `store.dart` — `SharedPreferences` 한 칸에 JSON 하나(웹의 `localStorage` 한 칸과 동일) |
| 조회 | `repo.dart` — 웹의 `DB` 객체 |
| 화면 16개 | `screens/` — 홈·직렬·과목·문제풀이·회차 목록/상세/응시/결과·복습·오답·키워드·검색·북마크·통계·설정·더보기 |
| 앱 셸 | `main.dart` — 하단 탭 5개(홈·회차·복습·오답·더보기), 부팅 시 `Repo.load()`+`Store.load()` 완료를 기다림 |

넘어오며 새로 생긴 것 — **오답노트/북마크 내보내기가 파일 공유 시트로 바뀐다**
(`share_plus`). 데스크톱처럼 다운로드 폴더가 없으니, 내보낸 `.json`을 카카오톡이나
메일로 보내 PC로 옮긴 뒤 `tools/wrongnote_pdf.py` 에 넘기는 흐름이다.

### 겪은 문제 — Windows 사용자 이름의 한글

`C:\Users\<한글 이름>\...` 경로 밑에서는 세 군데가 차례로 막힌다.

1. AGP가 프로젝트 경로의 비 ASCII 문자를 거부한다 →
   `android/gradle.properties` 에 `android.overridePathCheck=true`
2. `jni` 패키지의 ninja/cmake 빌드가 (JVM 기반이 아니라서) pub 캐시 경로의
   한글을 못 읽는다 → `PUB_CACHE` 를 `C:\pub-cache` 로 옮긴다
3. 그래도 안 되면 — Gradle 빌드 **출력** 경로 자체(`mobile/build/...`)가
   프로젝트 위치라 여전히 한글이다. 이건 설정으로 못 고친다.
   **프로젝트 전체를 ASCII 경로로 복사해 그곳에서 빌드한다**

```powershell
robocopy "<git 저장소>\mobile" "C:\dev\ncs_bank" /MIR /XD build .dart_tool .idea .gradle .cxx Pods
```

소스는 계속 저장소 안(`mobile/`)에서 고치고, 컴파일·빌드만 `C:\dev\ncs_bank` 에서
돌린다. `flutter test` 는 이 환경(에이전트 샌드박스)에서 VM 서비스 소켓 연결이
막혀 있어 확인하지 못했다 — `flutter analyze` (0 issues)와 실제 릴리스 빌드
성공으로 갈음했다.

### APK

```powershell
flutter build apk --release
```

서명은 아직 debug 키다(`android/app/build.gradle.kts` 의 기본값 — Play 스토어에
올리려면 그때 실제 키를 만든다). 개인 설치용으로는 문제없다.

- 산출물: `build/app/outputs/flutter-apk/app-release.apk`
- 패키지 `com.supergangy.ncs_bank` · minSdk 24 · targetSdk 36
- `aapt2 dump badging` 로 라벨·권한·SDK 범위를 확인했다 — 에뮬레이터가 없어
  실제 기기 설치까지는 확인하지 못했다

## 8. 설치본에서 드러난 것 (v1.1)

기기에 깔아 보고서야 보인 것들이다. **화면을 못 보는 채로 옮긴 대가**가 여기서 나왔다.

### 표 402개가 통째로 사라져 있었다

`flutter_html` 3.x 는 `<table>` 을 **스스로 그리지 않는다.** 별도 패키지
(`flutter_html_table` 의 `TableHtmlExtension`)를 확장으로 붙여야 한다.
안 붙이면 조용히 아무것도 안 그린다 — 오류도 없다.

자료·지문에 표가 있는 문항이 **78개**였다. 표가 문제의 자료인데 표가 없으니
그 78문항은 애초에 풀 수가 없었다. 사용자가 「데이터베이스 문제 중에 테이블이
안 나와 있어서 풀 수가 없다」고 한 것이 이것이다.

### 발문·선지에서 태그를 정규식으로 벗기고 있었다

`plainText()` 가 `<[^>]+>` 를 공백으로 바꿨다. 두 가지가 망가졌다.

| 원문 | 그때 화면 | 지금 |
|---|---|---|
| `&lt;보기&gt;에서 고르면?` | `&lt;보기&gt;에서 고르면?` | `<보기>에서 고르면?` |
| `36π − 72 (cm<sup>2</sup>)` | `36π − 72 (cm 2 )` | `36π − 72 (cm²)` |
| `담당자<u>로써</u> 책임을` | `담당자로써 책임을` | 담당자<u>로써</u> 책임을 |

첫째는 보기 흉한 정도지만, 둘째는 **값이 바뀐다**. 셋째는 어문규범 문항에서
밑줄이 곧 물음이라 **무엇을 묻는지 알 수 없게** 된다 — 선지 182곳이 그랬다.

고친 방법 — 순수 텍스트가 필요한 곳(목록·검색)은 진짜 HTML 파서를 쓰고 첨자는
유니코드로 옮긴다(`mobile/lib/text.dart`). 화면에 그리는 발문·선지는 아예
`HtmlText` 로 `<u>`·`<sup>` 을 살려 그린다(`mobile/lib/html_view.dart`).

### 같은 버그가 웹판에도 살아 있었다

`app.js` 가 발문에 `esc(it.st)` 를 씌워 `&lt;` 가 이중으로 이스케이프됐다.
선지·자료·지문은 날것으로 넣고 있었는데 발문만 그랬다. 선지 단평(`ea`)도 마찬가지.
둘 다 날것으로 바꾸고 목록 미리보기는 새 `plain()` 을 쓰게 했다.
발문에는 태그가 못 들어간다(`bank/loader.py` 가 막는다).

### 검증을 어떻게 대신했나

이 환경에서는 **화면을 볼 수 없다** — Flutter 웹은 캔버스로 그려 DOM 이 없고,
`flutter test` 는 테스트 러너가 자식 VM 에 붙지 못해 못 돌린다.

그래서 순수 텍스트 로직만 Flutter 를 안 쓰는 파일(`lib/text.dart`)로 떼고,
`dart run tool/check_text.dart` 로 확인한다. 번들된 426문항의 발문·선지를
전수로 훑어 남은 태그·문자 참조가 0인지도 함께 본다.

```bash
cd mobile && dart run tool/check_text.dart      # 19건 통과 · 426문항 전수 깨끗
```

위젯 렌더링 회귀 테스트(`test/render_test.dart`)도 함께 두었다. 이 샌드박스에서는
안 돌지만 보통 환경에서는 `flutter test` 로 돈다.

## 9. 오래 쓰기 위한 것 (v1.2)

### 기록을 옮길 수 있게 됐다

이때까지 기록은 기기에만 있었고 **꺼낼 길이 없었다.** 폰을 바꾸면 그걸로 끝이다.

설정 › 기록에서 `.json` 한 장으로 내보내고 불러온다. 형식은 저장하던 blob 을
봉투로 감싼 것이라 새 필드가 늘어도 그대로 간다.

```jsonc
{ "v": 1, "app": "ncs-bank", "at": "…",
  "counts": { "att": 312, "exams": 4, "mark": 7 },   // 확인창용
  "data": { … 저장 blob 그대로 … } }
```

복원은 **통째로 덮어쓰기**다(사용자 결정). 확인창에 백업과 지금 기록의 건수를
나란히 놓고, 덮어쓰기 직전 지금 blob 을 `ncsbank.v1.prev` 로 남긴다.

여기서 걸린 것 — `share_plus` 는 `share`/`shareXFiles`/`shareUri` 셋뿐인
**내보내기 전용**이다. 파일을 되돌려 받을 수단이 앱에 없어 `file_picker` 를 넣었다.

### 검증을 또 코드로 대신했다

`lib/backup.dart` 는 **Flutter 를 쓰지 않는다.** `lib/text.dart` 와 같은 수법이다.

```bash
cd mobile && dart run tool/check_backup.dart    # 47건
```

특히 **깨진 백업을 물려도 아무것도 안 바뀌는지**를 본다. 반만 읽어 들이면
다음 저장이 못 읽은 나머지를 영영 지운다 — v1.1 에서 고친 바로 그 부류의 사고다.

### 아이콘도 코드로 만든다

이 기계에 SVG 래스터라이저가 없다. ImageMagick·rsvg·inkscape 전부 없고,
PATH 의 `convert` 는 **윈도우 파일시스템 변환 유틸**이라 `command -v convert` 로
탐지하면 거짓 양성이 난다.

`app/icon.svg` 가 도형 넷뿐이라 `tools/make_icons.py` 에서 Pillow 로 다시 그린다.
legacy 5종 + adaptive 전경 5종 + `anydpi-v26` 선언 + 배경색을 낸다.
`--check` 로 크기·모서리색·전경 면적(10~45%)·안전영역 침범을 되본다.

adaptive 를 함께 만드는 이유 — Android 8+ 는 정사각 아이콘을 흰 테두리째
스퀘어클에 우겨넣는다. 전경은 안전영역(가운데 72dp)에 맞춰 다시 앉혔다.

### 안드로이드 전용으로 정리했다

`mobile/windows/` 를 지웠다. 쓰지 않는 타깃인데 `file_picker` 의 데스크톱
플러그인이 심볼릭 링크를 요구해 **Windows 개발자 모드 없이는 `pub get` 이 막혔다.**
개발자 모드는 시스템 보안 설정이라 켜지 않는다. `ios/`·`macos/` 는 원래 없다.
