# -*- coding: utf-8 -*-
"""문항을 앱이 읽는 하나의 JSON 으로 내보낸다.

`rounds/*/content/*.py` 와 `bank/**/*.py` 를 훑어 `app/data/bank.json` 을 만든다.
**진실은 계속 파이썬 파일이다.** 이 산출물은 파생물이고, 언제든 다시 만들 수 있어야
한다 (`docs/BANK.md` 3절 「되돌릴 수 있게」).

```bash
python tools/export_bank.py            # 만들고 요약 출력
python tools/export_bank.py --check    # 만들지 않고 문제만 점검
```

한국사 앱과 같은 **완전 내장형**이다 — 앱은 이 파일 하나를 안고 배포되고,
서버에서 문제를 받아오지 않는다.
"""

from __future__ import annotations

import argparse
import importlib
import json
import pathlib
import re
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# `qtypes` 다 — `types` 로 두면 `bank/` 가 `sys.path[0]` 일 때 표준 라이브러리를 가린다
from bank import qtypes as bank_types  # noqa: E402  — 경로를 넣은 뒤에 불러야 한다

OUT = ROOT / "app" / "data" / "bank.json"
OUT_ADMIN = ROOT / "app" / "data" / "admin.json"
# Flutter 판도 같은 파일을 쓴다. **여기 함께 쓰지 않으면 조용히 어긋난다** —
# 실제로 8월 12일부터 앱만 526문항에 멈춰 있었다(웹판은 540). 손으로 맞추는
# 단계는 문서에도 없었고 빠뜨려도 아무도 알려 주지 않는다.
OUT_MOBILE = ROOT / "mobile" / "assets" / "data"
# Flutter 판의 「PDF로 풀기」가 쓰는 것. 웹판은 PDF 를 오려 낼 수단이 없어 안 쓴다.
OUT_EXAMS = ROOT / "mobile" / "assets" / "exams"


def export_exam_pdfs(tags):
    """회차 문제집 PDF 와 문항 지도를 앱 자산으로 옮긴다.

    다섯 회차를 합쳐 4.6MB 라 **APK 에 그냥 넣는다.** 분석한 PSAT 앱은 회차당
    3~5MB 라 R2 에서 내려받지만, 우리는 그 값을 치르면서까지 「지하철에서
    풀려야 한다」는 원칙을 깰 이유가 없다.

    지도가 없는 회차는 건너뛴다 — `build.py` 를 아직 안 돌린 것이다.
    """
    import shutil
    OUT_EXAMS.mkdir(parents=True, exist_ok=True)
    kept, skipped, total = [], [], 0
    for tag in tags:
        d = ROOT / "out" / tag
        pdfs = [p for p in d.glob("*문제*.pdf") if not p.name.startswith("_")]
        pmap = d / "page_map.json"
        if not pdfs or not pmap.exists():
            skipped.append(tag)
            continue
        pdf = sorted(pdfs)[0]
        shutil.copy2(pdf, OUT_EXAMS / f"{tag}.pdf")
        shutil.copy2(pmap, OUT_EXAMS / f"{tag}.map.json")
        total += pdf.stat().st_size + pmap.stat().st_size
        kept.append(tag)

    # 남은 찌꺼기를 치운다 — 회차 이름이 바뀌면 옛 파일이 APK 에 계속 실린다.
    want = {f"{t}.pdf" for t in kept} | {f"{t}.map.json" for t in kept}
    for p in OUT_EXAMS.iterdir():
        if p.is_file() and p.name not in want:
            p.unlink()

    print(f"\n■ {OUT_EXAMS.relative_to(ROOT)}  {total / 1048576:,.1f}MB   "
          f"(PDF로 풀기 — {len(kept)}회차)")
    if skipped:
        print(f"   건너뜀: {', '.join(skipped)} — build.py 를 먼저 돌린다")

# ── 직렬 ────────────────────────────────────────────────────────────────
# 전산 8과목은 직렬 문항이고, 나머지는 직렬을 가리지 않는 NCS 다.
CS_SUBJECTS = (
    "데이터베이스론", "운영체제", "네트워크", "데이터통신",
    "프로그래밍언어", "전자계산기구조", "정보보안", "소프트웨어공학",
)
TRACKS = [
    {"id": "cs", "name": "전산직", "sub": "직무 전공"},
    {"id": "ncs", "name": "NCS 직업기초", "sub": "직업기초능력"},
]

# 은행은 `의사소통`, 회차는 `의사소통능력` 으로 적어 왔다. 같은 것이므로 합친다.
SUBJECT_ALIAS = {
    "의사소통": "의사소통능력", "수리": "수리능력", "문제해결": "문제해결능력",
    "자원관리": "자원관리능력", "정보": "정보능력", "기술": "기술능력",
    "조직이해": "조직이해능력",
}

# ── 키워드 사전 ─────────────────────────────────────────────────────────
# **자동 추출하지 않는다.** 문항 본문에서 명사를 긁으면 「경우」「다음」 같은 것이
# 함께 올라온다. 과목마다 실제로 시험에 나오는 용어만 손으로 적고, 본문에 그 말이
# 있는 문항에만 붙인다. 별칭은 `|` 로 잇는다 — 표기가 갈리는 말이 많다.
VOCAB: dict[str, tuple[str, ...]] = {
    "데이터베이스론": (
        "정규화", "제1정규형|1NF", "제2정규형|2NF", "제3정규형|3NF", "BCNF",
        "함수 종속|함수종속", "후보키", "기본키", "외래키", "슈퍼키",
        "이상 현상|삽입 이상|삭제 이상|갱신 이상", "무손실 분해|무손실",
        "트랜잭션", "ACID", "격리 수준|격리수준", "커밋|COMMIT", "롤백|ROLLBACK",
        "교착|데드락", "로킹|잠금", "회복|REDO|UNDO", "체크포인트",
        "인덱스", "B+트리|B트리", "클러스터드|군집 인덱스", "선택도",
        "SQL", "JOIN|조인", "OUTER JOIN|외부 조인", "GROUP BY", "HAVING",
        "서브쿼리|부속질의", "NULL", "집계 함수|집계함수",
        "뷰|VIEW", "관계대수", "디비전|나눗셈 연산", "ER 모델|ER모델|개체관계",
        "카디널리티",
    ),
    "운영체제": (
        "프로세스", "스레드", "문맥 교환|컨텍스트 스위칭",
        "스케줄링", "FCFS", "SJF", "라운드 로빈|RR", "우선순위 스케줄링",
        "선점|비선점", "기아 현상|기아", "에이징",
        "교착 상태|교착|데드락", "은행원 알고리즘", "상호 배제|상호배제",
        "임계 구역|임계구역", "세마포어", "뮤텍스", "동기화",
        "페이징", "세그먼테이션", "가상 메모리|가상메모리", "페이지 부재|페이지 폴트",
        "페이지 교체|페이지교체", "LRU", "FIFO", "LFU", "벨라디|벨라디 변이",
        "워킹 셋|워킹셋", "스래싱", "단편화|내부 단편화|외부 단편화",
        "최초 적합|최적 적합|최악 적합", "TLB",
        "디스크 스케줄링|디스크스케줄링", "SCAN|엘리베이터", "SSTF",
        "파일 시스템|파일시스템", "아이노드|i-node",
        "논리 주소|물리 주소", "페이지 번호|오프셋", "RAID", "패리티", "미러링",
    ),
    "네트워크": (
        "OSI", "TCP/IP", "물리 계층|데이터링크 계층|네트워크 계층|전송 계층|응용 계층",
        "IP 주소|IP주소", "서브넷|서브네팅|서브넷 마스크", "CIDR", "사설 IP|사설망",
        "IPv4", "IPv6", "NAT", "PAT",
        "라우팅", "다익스트라", "거리 벡터|링크 상태", "RIP", "OSPF", "BGP",
        "TCP", "UDP", "3-way|스리웨이|3웨이", "혼잡 제어|혼잡제어",
        "흐름 제어|흐름제어", "슬라이딩 윈도우", "포트 번호|포트번호",
        "HTTP", "HTTPS", "DNS", "DHCP", "ARP", "ICMP", "FTP", "SMTP",
        "MAC 주소", "스위치", "라우터", "허브", "게이트웨이",
        "CRC", "해밍|해밍 코드", "패리티",
        "호스트", "네트워크 주소", "브로드캐스트", "프리픽스|접두",
        "경로 요약|슈퍼네팅|요약 주소|요약한 주소|주소 요약", "최소 비용|최단 경로",
        "혼잡 윈도|혼잡윈도", "슬로 스타트|느린 시작", "혼잡 회피",
        "처리율|throughput", "왕복 시간|RTT", "전송 시간|전파 지연",
        "프레임", "CSMA/CD", "CSMA/CA", "무선 LAN|무선랜",
    ),
    "데이터통신": (
        "나이퀴스트", "섀넌", "대역폭", "채널 용량|채널용량", "신호 준위|신호준위",
        "변조", "ASK", "FSK", "PSK", "QAM", "PCM", "표본화", "양자화",
        "다중화", "TDM", "FDM", "CDM", "T1", "E1",
        "오류 검출|오류검출", "CRC", "해밍 거리|해밍거리", "해밍 코드|해밍코드",
        "FCS|검사 비트", "생성 다항식|생성다항식", "모듈로-2|모듈로 2",
        "패리티", "체크섬", "전진 오류 정정|FEC", "ARQ",
        "CSMA/CD", "CSMA/CA", "이더넷", "충돌", "최소 프레임|프레임 크기",
        "슬라이딩 윈도우", "되돌아가기|GBN", "선택적 재전송|SR",
        "회선 교환|회선교환", "패킷 교환|패킷교환", "가상 회선|데이터그램",
        "전송 지연|전파 지연", "데시벨|dB", "감쇠",
        "FDMA", "TDMA", "CDMA", "OFDMA", "ALOHA",
        "동기식|비동기식", "흐름 제어|흐름제어",
    ),
    "프로그래밍언어": (
        "값 호출|call by value", "참조 호출|call by reference", "값-결과 호출",
        "이름 호출", "포인터", "역참조",
        "재귀", "피보나치", "반복문", "호출 횟수|호출 수", "함수 호출",
        "스택", "큐", "덱", "연결 리스트|연결리스트", "배열",
        "트리", "이진 탐색 트리|BST", "순회|전위|중위|후위",
        "해시", "충돌", "체이닝", "개방 주소법|선형 조사",
        "정렬", "버블 정렬", "선택 정렬", "삽입 정렬", "퀵 정렬", "병합 정렬", "힙 정렬",
        "시간 복잡도|복잡도", "빅오|O(n)",
        "컴파일러", "인터프리터", "목적 코드|목적코드",
        "유효 범위|유효범위|스코프", "전역 변수|지역 변수",
        "객체지향|객체 지향", "캡슐화", "상속", "다형성", "추상화", "정보 은닉",
        "오버로딩", "오버라이딩",
        "2의 보수|2의보수", "자료형", "오버플로",
        "함수형", "예외 처리|예외처리", "finally",
    ),
    "전자계산기구조": (
        "2의 보수|2의보수", "1의 보수|1의보수", "부호-절댓값|부호 절댓값",
        "진법|16진|8진|2진", "부동소수점", "IEEE 754", "바이어스", "정규화",
        "논리 게이트|논리게이트", "AND", "OR", "NOT", "NAND", "NOR", "XOR",
        "반가산기", "전가산기", "진리표", "드모르간",
        "파이프라인", "해저드", "포워딩", "분기 예측|분기예측",
        "캐시", "적중률", "직접 사상|직접사상", "집합 연관|연관 사상",
        "태그|인덱스|오프셋", "교체 알고리즘",
        "기억장치 계층|계층 구조", "레지스터", "주기억장치", "보조기억장치",
        "명령어 형식|명령어형식", "0-주소|1-주소|2-주소|3-주소", "누산기",
        "주소 지정|주소지정", "즉시 주소|직접 주소|간접 주소|상대 주소",
        "인터럽트", "DMA", "MAR", "MBR", "IR", "PC",
        "MIPS", "CPI", "클럭", "RISC", "CISC", "마이크로프로그램|하드와이어드",
    ),
    "정보보안": (
        "기밀성", "무결성", "가용성", "CIA",
        "대칭키|대칭 키", "공개키|비대칭", "RSA", "AES", "DES",
        "세션키|세션 키", "하이브리드", "키 분배|키분배",
        "운용 모드|운용모드", "ECB", "CBC", "CTR", "블록 암호|블록암호",
        "해시", "SHA", "MD5", "충돌|생일 공격", "전자서명|디지털 서명",
        "접근 통제|접근통제", "DAC", "MAC", "RBAC", "벨-라파듈라|벨라파듈라",
        "인증", "커버로스|Kerberos", "다중 인증|2단계 인증",
        "방화벽", "패킷 필터링", "IDS", "IPS", "DMZ",
        "SQL 인젝션|SQL인젝션", "XSS", "CSRF", "매개변수화 질의",
        "DDoS", "SYN 플러딩", "스니핑", "스푸핑",
        "위험 분석|위험분석", "SLE", "ALE", "ARO", "ISMS", "PDCA",
        "개인정보", "가명처리|가명 처리", "익명처리",
    ),
    "소프트웨어공학": (
        "폭포수", "애자일", "프로토타입", "나선형", "스크럼",
        "요구공학|요구 공학", "도출|분석|명세|확인",
        "응집도", "결합도", "모듈", "디자인 패턴|GoF",
        "싱글턴", "팩토리|팩토리 메서드", "옵서버", "어댑터", "빌더", "프로토타입 패턴",
        "MVC", "아키텍처",
        "테스트", "블랙박스|블랙 박스", "화이트박스|화이트 박스",
        "동등 분할", "경계값 분석|경계값", "기초 경로|기초경로",
        "커버리지", "구문 커버리지", "결정 커버리지", "조건 커버리지", "MC/DC",
        "순환 복잡도|순환복잡도",
        "형상 관리|형상관리", "베이스라인", "버전 관리|버전관리",
        "COCOMO", "기능점수|FP", "CPM", "임계 경로|임계경로", "PERT",
        "CMMI", "품질 특성|품질특성", "신뢰성", "사용성", "이식성",
        "유지보수", "적응|수정|완전화|예방",
    ),
}
# NCS 는 과목이 아니라 능력 영역이라 용어 사전을 따로 두지 않는다.
# 유형(`type`) 자체가 이미 「사자성어」「맞춤법」처럼 충분히 좁다.

_ALIAS = {}          # 표시할 대표 이름 → 정규식
for _subj, _terms in VOCAB.items():
    for _t in _terms:
        _parts = _t.split("|")
        _ALIAS.setdefault(_parts[0], set()).update(_parts)

TAG = re.compile(r"<[^>]+>")


def plain(s: str | None) -> str:
    """태그를 지우되 **붙여 쓰지 않는다** — 표 셀이 한 낱말로 뭉치면 안 된다."""
    if not s:
        return ""
    return re.sub(r"\s+", " ", TAG.sub(" ", s)).strip()


def keywords_of(subject: str, text: str) -> list[str]:
    """과목 사전에 있는 말 가운데 본문에 실제로 나온 것만."""
    terms = VOCAB.get(subject)
    if not terms:
        return []
    hit = []
    for t in terms:
        head, *rest = t.split("|")
        for form in (head, *rest):
            if form.lower() in text.lower():
                hit.append(head)
                break
    return hit


# ── 읽어 들이기 ─────────────────────────────────────────────────────────

def load_bank() -> list[dict]:
    from bank.loader import load_all
    out = []
    for it in load_all():
        q = it["questions"][0]
        subj = SUBJECT_ALIAS.get(it["subject"], it["subject"])
        track = "cs" if subj in CS_SUBJECTS else "ncs"
        out.append({
            "id": it["id"],
            "src": "bank",
            "track": track,
            "subject": subj,
            "type": q.get("type") or "기타",
            "org": it.get("org") or "공통",
            "difficulty": it.get("difficulty"),
            "risk": it.get("risk"),
            "evidence": it.get("evidence"),
            "snapshot": it.get("snapshot"),
            "lead": it.get("lead"),
            "passage": it.get("passage"),
            "material": q.get("material"),
            "stem": q["stem"],
            "choices": list(q["choices"]),
            "answer": q["answer"],
            "each": list(q.get("each") or []),
            "explain": q.get("explain"),
            "why": q.get("why") or {},
        })
    return out


def load_rounds() -> tuple[list[dict], list[dict]]:
    """회차 문항과 회차 메타.

    **`CFG.AREAS` 에 선언된 순서로 읽는다.** `build.py` 의 `load_blocks` 가 그렇게
    읽으므로 알파벳순으로 훑으면 앱의 문항 번호가 **인쇄본과 조용히 어긋난다.**
    회차 모드는 번호가 곧 정답 위치라 이 어긋남이 치명적이다.
    """
    items: list[dict] = []
    rounds: list[dict] = []

    for rd in sorted(p.name for p in (ROOT / "rounds").iterdir() if p.is_dir()):
        cdir = ROOT / "rounds" / rd / "content"
        if not cdir.is_dir():
            continue
        cfg = importlib.import_module(f"rounds.{rd}.config")
        areas = getattr(cfg, "AREAS", None)
        if not areas:
            raise SystemExit(f"[중단] {rd}/config.py 에 AREAS 가 없다")
        org = (getattr(cfg, "BRAND", "") or "").replace(" 채용대비", "").strip() or "공통"

        no = 0
        area_n: list[list] = []
        for mod_name, area, expected in areas:
            path = cdir / f"{mod_name}.py"
            if not path.exists():
                # 아직 안 쓴 영역. 회차를 통째로 빼지 않고 있는 것만 싣는다
                continue
            m = importlib.import_module(f"rounds.{rd}.content.{mod_name}")
            got = 0
            for b in getattr(m, "BLOCKS", []):
                for q in b.get("questions", []):
                    no += 1
                    got += 1
                    items.append({
                        "id": f"{rd}-{no:02d}",
                        "src": "round",
                        "round": rd,
                        "no": no,
                        "track": "ncs",
                        # 영역은 **설정이 진실이다.** 본문의 area 키를 믿지 않는다
                        "subject": area,
                        "type": q.get("type") or "기타",
                        "org": org,
                        "difficulty": None,
                        "risk": None,
                        "evidence": None,
                        "snapshot": None,
                        "lead": b.get("lead"),
                        "passage": b.get("passage"),
                        "material": q.get("material"),
                        "stem": q["stem"],
                        "choices": list(q["choices"]),
                        "answer": q["answer"],
                        "each": list(q.get("each") or []),
                        "explain": q.get("explain"),
                        "why": q.get("why") or {},
                    })
            if got != expected:
                raise SystemExit(
                    f"[중단] {rd} · {area} 문항 수가 설계와 다르다 — "
                    f"{got}개 (AREAS 는 {expected}개)\n"
                    f"  build.py 와 같은 규율이다. 설계를 고치거나 문항을 맞춘다.")
            area_n.append([area, got])

        if not items or not area_n:
            continue                     # 설정만 있고 문항이 없는 회차 (r5_nhis)
        rounds.append({
            "tag": rd,
            "title": getattr(cfg, "EXAM_ROUND", rd),
            "brand": getattr(cfg, "BRAND", ""),
            "org": org,
            "n": no,
            "min": getattr(cfg, "TOTAL_MIN", 0),
            "areas": area_n,
        })
        # 설계 총량과도 대조한다
        want = getattr(cfg, "TOTAL_Q", no)
        if no != want:
            raise SystemExit(f"[중단] {rd} 총 문항 {no}개인데 TOTAL_Q 는 {want}다")

    return items, rounds


# ── 점검 ────────────────────────────────────────────────────────────────

def check(items: list[dict]) -> list[str]:
    """앱에서 터질 것을 미리 잡는다. 정답 범위·선지 수·id 중복."""
    bad = []
    seen = set()
    for it in items:
        i = it["id"]
        if i in seen:
            bad.append(f"id 중복 {i}")
        seen.add(i)
        n = len(it["choices"])
        if n < 2:
            bad.append(f"{i} 선지가 {n}개")
        if not 1 <= it["answer"] <= n:
            bad.append(f"{i} 정답 {it['answer']} 이 선지 {n}개를 벗어난다")
        if it["each"] and len(it["each"]) != n:
            bad.append(f"{i} 선지 {n}개인데 each {len(it['each'])}개")
        if not plain(it["stem"]):
            bad.append(f"{i} 발문이 비었다")
    return bad


# ── 내보내기 ────────────────────────────────────────────────────────────

def build(items: list[dict], rounds: list[dict]) -> tuple[dict, dict]:
    # 지문은 **한 벌만** 담고 문항이 가리킨다. 세트문항이 같은 지문을 공유한다.
    passages: list[dict] = []
    pindex: dict[str, int] = {}

    kw_count: Counter[str] = Counter()
    for it in items:
        body = " ".join([
            plain(it["stem"]), " ".join(plain(c) for c in it["choices"]),
            plain(it.get("explain")), plain(it.get("material")),
            " ".join(plain(e) for e in it.get("each") or []),
        ])
        it["_kw"] = keywords_of(it["subject"], body)
        kw_count.update(it["_kw"])

    kw_list = [{"t": t, "n": n} for t, n in sorted(kw_count.items(),
                                                   key=lambda x: (-x[1], x[0]))]
    kw_id = {k["t"]: i for i, k in enumerate(kw_list)}

    out_items = []
    admin_items: dict[str, dict] = {}
    for it in items:
        pid = None
        if it.get("passage"):
            key = it["passage"]
            if key not in pindex:
                pindex[key] = len(passages)
                passages.append({"body": key, "lead": it.get("lead")})
            pid = pindex[key]
        o = {
            "id": it["id"], "tr": it["track"], "sj": it["subject"],
            "ty": it["type"], "og": it["org"],
            "st": it["stem"], "ch": it["choices"], "an": it["answer"],
            "kw": sorted(kw_id[k] for k in it["_kw"]),
        }
        if pid is not None:
            o["pg"] = pid
        for src, dst in (("material", "mt"), ("explain", "ex"), ("difficulty", "df"),
                         ("lead", "ld")):
            if it.get(src) and not (src == "lead" and pid is not None):
                o[dst] = it[src]
        if it.get("each"):
            o["ea"] = it["each"]
        # 회차 꼬리표는 **학습자 payload 에 둔다** — 회차 모드가 이걸로 문항을 모은다
        if it.get("round"):
            o["rd"] = it["round"]
            o["no"] = it["no"]
        out_items.append(o)

        # ── 관리자 전용 ── **본체에 넣지 않는다.**
        # 위험도·근거·출제이유서는 별도 파일로 빼고, 관리자 모드일 때만 받아 온다.
        # 학습자가 받는 payload 에는 아예 들어 있지 않다.
        adm = {}
        for src, dst in (("risk", "rk"), ("evidence", "ev"), ("snapshot", "sn")):
            if it.get(src):
                adm[dst] = it[src]
        if it.get("why"):
            adm["wy"] = it["why"]
        if adm:
            admin_items[it["id"]] = adm

    # 유형 어휘 검사 — **여기서 멈춘다.** 오타가 새 유형으로 굳는 것을 막는다.
    # 표기가 갈려 `조건추리`/`조건추론` 이 두 줄로 나뉘고 문항 수가 반씩 쪼개진 적이 있다.
    unknown = sorted({(i["sj"], i["ty"]) for i in out_items
                      if not bank_types.known(i["sj"], i["ty"])})
    if unknown:
        print("\n[중단] 유형 사전(bank/qtypes.py)에 없는 유형이 있습니다:")
        for sj, ty in unknown:
            n = sum(1 for i in out_items if i["sj"] == sj and i["ty"] == ty)
            print(f"   {sj}/{ty}  ({n}문항)")
        print("   → 오타인지 먼저 보고, 정말 새 유형이면 GROUPS 에 넣으십시오.")
        raise SystemExit(1)

    # 분류 트리 — 런타임 집계를 하지 않는다 (한국사 앱과 같은 판단)
    # `g` 는 대유형이다. 세부 유형은 그대로 두고 앱이 묶어 보이는 데 쓴다 —
    # 세부만 늘어놓으면 NCS 127종 가운데 67종이 1문항짜리라 고를 값이 없다.
    subjects, types = [], []
    for tr in ("cs", "ncs"):
        for sj in sorted({i["sj"] for i in out_items if i["tr"] == tr}):
            n = sum(1 for i in out_items if i["tr"] == tr and i["sj"] == sj)
            subjects.append({"tr": tr, "n": sj, "c": n})
            for ty in sorted({i["ty"] for i in out_items
                              if i["tr"] == tr and i["sj"] == sj}):
                types.append({"tr": tr, "sj": sj, "n": ty,
                              "g": bank_types.group_of(sj, ty),
                              "c": sum(1 for i in out_items if i["tr"] == tr
                                       and i["sj"] == sj and i["ty"] == ty)})

    return {
        "v": 1,
        "n": len(out_items),
        "rounds": rounds,
        "tracks": [dict(t, c=sum(1 for i in out_items if i["tr"] == t["id"]))
                   for t in TRACKS],
        "subjects": subjects,
        "types": types,
        "keywords": kw_list,
        "passages": passages,
        "items": out_items,
    }, {"v": 1, "n": len(admin_items), "items": admin_items}


def main() -> int:
    ap = argparse.ArgumentParser(description="문항을 앱용 JSON 으로 내보낸다")
    ap.add_argument("--check", action="store_true", help="쓰지 않고 점검만")
    a = ap.parse_args()

    r_items, rounds = load_rounds()
    items = r_items + load_bank()
    bad = check(items)
    if bad:
        print(f"[중단] 문항에 문제가 {len(bad)}건 있다")
        for b in bad[:20]:
            print(f"   {b}")
        return 1

    data, admin = build(items, rounds)
    if a.check:
        print(f"점검 통과 — 문항 {data['n']}건 · 문제 없음")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    OUT_ADMIN.write_text(json.dumps(admin, ensure_ascii=False, separators=(",", ":")),
                         encoding="utf-8")
    # Flutter 판에 그대로 복사한다. 웹판과 같은 파일을 써야 1:1 대응이 유지된다.
    import shutil
    OUT_MOBILE.mkdir(parents=True, exist_ok=True)
    for src in (OUT, OUT_ADMIN):
        shutil.copy2(src, OUT_MOBILE / src.name)

    kb = OUT.stat().st_size / 1024
    kb_a = OUT_ADMIN.stat().st_size / 1024

    print(f"■ {OUT.relative_to(ROOT)}  {kb:,.0f}KB   (학습자가 받는 것)")
    print(f"■ {(OUT_MOBILE / OUT.name).relative_to(ROOT)}  같은 파일   (Flutter 판)")
    print(f"■ {OUT_ADMIN.relative_to(ROOT)}  {kb_a:,.0f}KB   "
          f"(위험도·출제이유서 {admin['n']}건 — 관리자 모드에서만 받는다)")
    print(f"   문항 {data['n']}건 · 지문 {len(data['passages'])}개 · "
          f"키워드 {len(data['keywords'])}개")
    for t in data["tracks"]:
        print(f"\n   {t['name']} {t['c']}건")
        for s in data["subjects"]:
            if s["tr"] != t["id"]:
                continue
            tys = [x for x in data["types"] if x["tr"] == t["id"] and x["sj"] == s["n"]]
            print(f"      {s['n']:<12} {s['c']:>3}문항  유형 {len(tys)}종")
    print(f"\n   회차 {len(data['rounds'])}개")
    for r in data["rounds"]:
        cons = " · ".join(f"{a}{n}" for a, n in r["areas"])
        print(f"      {r['tag']:<12} {r['title']:<14} {r['n']:>2}문항/{r['min']}분   {cons}")

    export_exam_pdfs([r["tag"] for r in data["rounds"]])

    top = ", ".join(f"{k['t']}({k['n']})" for k in data["keywords"][:12])
    print(f"\n   키워드 상위: {top}")
    no_kw = sum(1 for i in data["items"] if not i["kw"] and i["tr"] == "cs")
    if no_kw:
        print(f"   ※ 전산 문항 가운데 키워드가 안 붙은 것 {no_kw}건 — 사전을 넓혀야 한다")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
