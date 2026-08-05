# 문항은행 — 회차보다 먼저 쌓는다

회차를 만들 때마다 문항을 새로 쓰면 그 문항은 그 회차에만 묶인다.
여기에 먼저 쌓아 두고 **회차가 골라 가는 방식**으로 뒤집는다.

## 분류 — 세 축

```
bank/
  korail/                        ① 기관
    ncs_communication.py         ② NCS / 직무   ③ 과목
    ncs_math.py
    ncs_problem.py
    major_business.py              경영학
    major_law.py                   철도법령
  seoul_metro/
    ncs_communication.py
    major_admin.py                 행정학
  kwater/
  _common/                       기관 색이 없는 범용 문항
    ncs_communication.py
  loader.py
```

파일 이름이 곧 분류다 — `<kind>_<subject>.py`. 기관은 폴더가 맡는다.

### 과목 코드

후기 실측(`reviews/`)에서 나온 계열을 그대로 쓴다.

| 구분 | 과목 | 코드 | 후기 |
|---|---|---|---|
| NCS | 의사소통 · 수리 · 문제해결 · 자원관리 · 정보 · 기술 · 조직이해 · 직업윤리 | `ncs_communication` … | — |
| 직무 | 전기 | `major_electric` | 362 |
| | 기계 (기계일반·열역학·유체역학·재료역학) | `major_mech` | 246 |
| | 경영 (경영학·재무관리·회계학) | `major_business` | 227 |
| | 토목 (응용역학·토목시공) | `major_civil` | 172 |
| | 전산 (네트워크·운영체제·데이터베이스) | `major_cs` | 153 |
| | 건축 | `major_arch` | 114 |
| | 행정 (행정학·행정법) | `major_admin` | 48 |
| | 화학 | `major_chem` | 45 |
| | 기관 법령 | `major_law` | 철도법령 25 · 건보법 등 |

## 형식

회차 `content/*.py` 의 `BLOCKS` 와 **같은 모양**이다. 그래야 회차가 그대로 실을 수 있다.
다른 점은 은행용 메타가 붙는다는 것뿐이다.

```python
ITEMS = [
    {
        # ── 은행 메타 ──────────────────────────────
        "id": "ncs-comm-seoulmetro-001",   # 한 번 붙이면 바꾸지 않는다
        "org": "서울교통공사",
        "kind": "ncs",                      # ncs | major
        "subject": "의사소통",
        "difficulty": "중",
        "evidence": "★★ 2건 — 「열차 지연 시 대응 지문」",
        "snapshot": "S-20260804-c85013",    # 그 건수의 기준 (D55)

        # ── 회차 BLOCKS 와 동일 ─────────────────────
        "area": "의사소통능력",
        "lead": None,
        "passage": "...",
        "questions": [ {...} ],
    },
]
```

`id` 는 **고정한다.** 회차가 이 값을 참조하므로 바꾸면 어느 회차가 무엇을 썼는지 끊긴다.

## 집필 순서

`PLAYBOOK` 규칙 `1-14` 그대로 — 소재를 근거에서 고르고, **발문·선지를 먼저 쓰고**,
선지마다 근거 문단을 배정한 뒤 집필한다. 지문을 먼저 쓰면 판정 지점 없는 산문이 된다.

## 직무 문항은 검증 방식이 다르다

NCS 지문형은 **지문이 정답 근거를 통제**한다. 내가 지문을 쓰면 정답이 확정된다.
직무는 그렇지 않다 — 정답이 **지문 밖 사실**로 결정되므로 틀리면 방어할 수단이 없다.

| 갈래 | 검증 | 판단 |
|---|---|---|
| 계산형 (응용역학 모멘트 · 전기 회로 · 열역학 · 알고리즘 복잡도) | **재계산으로 확정된다** | 만든다 |
| 원리형 (경영 이론 · 자료구조 · 네트워크 계층) | 교과서 수준에서 안정적 | 만든다 |
| **법령 조문형** (철도법 제N조 · 건보법 시행령) | **조문 번호와 문구를 지어낼 수 없다.** 개정도 잦다 | **가상 규정으로 돌리거나 보류** |

법령 문항이 필요하면 `○○공사 여객운송약관` 같은 **가상 규정문**으로 만든다.
실제 법령 조문을 인용하려면 원문을 확인한 뒤에만 쓴다.

```bash
python bank/loader.py --list                        # 쌓인 문항 훑기
python bank/loader.py --org 서울교통공사 --kind ncs
python tools/prosestat.py --bank ncs_communication  # 지문 규격 대조
```

## 회차가 가져다 쓰는 법

```python
from bank.loader import pick
BLOCKS = pick("ncs-comm-seoulmetro-001", "ncs-comm-seoulmetro-004")
```

복사하지 않는다. 회차 사정으로 문항을 손봐야 하면 **은행을 고치지 말고 회차에서 덮어쓴다.**
은행은 여러 회차가 공유하므로 한 회차 때문에 고치면 다른 회차가 흔들린다.
