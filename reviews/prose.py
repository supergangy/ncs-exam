# -*- coding: utf-8 -*-
"""산문 본문에서 소재를 뽑는다 — `D57`.

## 왜 있는가

`ingest.parse_keywords` 는 「기억나는 문항」 같은 **양식 머리글이 있는 글만** 읽는다.
그런데 대부분은 소재를 산문으로 쓴다.

> 수리영역에서는 큰수를 나누었을때의 나머지 구하기, 도형의 넓이 구하기, 수열,
> 자료를 주고 옳은 지문고르기 등이 출제되었습니다.

원문 4,384건을 훑어 보니 소재를 말한 후기가 3,115건인데 양식으로 잡힌 것은
**484건(15.5%)** 뿐이었다. 모든 회차의 건수가 6배 넘게 과소집계였다.

## 어떻게

**① 본문을 과목 구간으로 자른다.** 이게 가장 중요하다. 「경영」·「철도법」·「전공」
구간에 들어가면 NCS 가 아니다. 이 구분을 못 하면 한국농어촌공사의
「반지름 주어지고 핵의 넓이」(구조역학)가 NCS 도형으로 잡힌다.

**② NCS 구간에서만 후보를 뽑는다.** 두 모양이 있다.

- **목록형** — `-`·`·`·`1)` 글머리표로 줄마다 하나
- **산문형** — 「A, B, C 등이 출제되었습니다」처럼 한 문장에 쉼표로 나열

**③ 정제는 `ingest` 의 것을 그대로 쓴다.** 어미 절단·보일러플레이트·잡음 목록을
따로 만들면 두 경로가 서로 다르게 정제되어 같은 소재가 갈린다.

## 정밀도를 어떻게 지키나

- 과목 구간 밖은 손대지 않는다
- 후기 서술문(「어려웠습니다」)은 `KW_TAIL` 로 떨어진다
- 메타 표현(난이도·시간·합격 등)은 `META` 로 뺀다
- 뽑은 것은 `kw_source = "prose"` 로 표시해 **양식으로 받은 것과 섞지 않는다**

```bash
python reviews/prose.py --sample 12          # 표본을 눈으로 검사
python reviews/prose.py --measure            # 회수율·건수 측정
```
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ingest import BOILERPLATE, KW_NOISE, KW_TAIL, VERB_TAIL, norm  # noqa: E402

# ── 과목 구간 표지 ──────────────────────────────────────────────────────
# 줄 하나가 거의 표지만으로 이루어졌을 때만 구간을 바꾼다.
_DECO = r"[\s\-–—=~*#>·▷▶◆■□●○★☆\[\]<>()【】「」:：]*"

NCS_MARK = re.compile(
    rf"^{_DECO}(?:ncs|엔시에스|직업기초(?:능력)?|의수문|"
    rf"의사소통(?:능력)?|수리(?:능력)?|문제해결(?:능력)?|자원관리(?:능력)?|"
    rf"정보(?:능력)?|기술(?:능력)?|조직이해(?:능력)?|직업윤리){_DECO}$", re.I)

MAJOR_MARK = re.compile(
    rf"^{_DECO}(?:전공|경영(?:학)?|경제(?:학)?|회계(?:학)?|행정(?:법|학)?|법학|민법|"
    rf"기계(?:일반)?|전기(?:일반|이론)?|전자|통신|토목(?:일반)?|건축|화학|"
    rf"전산(?:학)?|컴퓨터(?:일반)?|정보처리|데이터베이스|운영체제|네트워크|"
    rf"수리학|구조역학|응용역학|측량|재료역학|열역학|유체역학|"
    rf"철도법(?:령)?|법령|관계법령|정관|약관|장기요양보험법|국민건강보험법){_DECO}$",
    re.I)

# 「수리에서는 ~」 처럼 문장 머리에서 영역을 밝히는 경우
INLINE_AREA = re.compile(
    r"(의사소통|수리|문제해결|자원관리|정보|기술|조직이해|직업윤리)"
    r"(?:능력)?(?:\s*(?:영역|파트|과목))?\s*(?:에서(?:는)?|는|은|:|：)")

# 후기 메타 — 소재가 아니다.
# 뒤쪽 절반은 **시험 운영** 서술이다. 「문항수: 80개」·「수정테이프 사용 X」·
# 「시계 위치도 조정해줌」 같은 것이 소재로 새어 들어와 추가했다.
META = re.compile(
    r"(난이도|체감|시간\s*(?:부족|배분|안|이)|커트|컷|합격|불합격|점수|경쟁률|"
    r"면접|자기소개|스펙|공부\s*법|교재|인강|후기|응원|화이팅|파이팅|"
    r"작년|재작년|올해|상반기|하반기|채용\s*공고|접수|필기\s*시험\s*후기|"
    r"문항\s*수|문제\s*수|총\s*\d+\s*문항|\d+\s*분\s*동안|OMR|컴퓨터용|싸인펜|"
    r"수정\s*(?:테이프|액)|볼펜|신분증|고사장|시험장|입실|퇴실|대기실|화장실|"
    r"감독관|시계|책상|의자|적성\s*검사|인성\s*검사|자리\s*배치|주차)")

# 나열이 들어 있는 문장을 알리는 신호
ENUM_CUE = re.compile(r"(출제|나왔|나온|나옴|있었|기억\s*나는|기억나는|물어봤|물어본|풀었)")

BULLET = re.compile(r"^\s*(?:[-–—•*▪◦·]|\d{1,2}\s*[.)])\s*(.+)$")

# 전공 어휘. 줄 단독 표지가 없어도 이런 말이 있으면 NCS 가 아니다.
# (코레일 차량기계 후기의 「오일러 운동방정식」·「비열」이 NCS 소재로 새어 들어왔다)
MAJOR_VOCAB = re.compile(
    r"(오일러|라그란지|관성력|점성력|레이놀즈|\bRe\b|비열|열량|엔트로피|엔탈피|응력|"
    r"모멘트|반력|등분포하중|좌굴|단면2차|전단력|휨|철근|콘크리트|슬럼프|"
    r"옴의|키르히호프|페이저|역률|변압기|전동기|계전기|절연|접지|"
    r"대차|윤축|팬터그래프|가공전차선|궤도|분기기|신호기|폐색|"
    r"관계대수|정규화|트랜잭션|교착상태|페이징|스케줄링|서브넷|"
    r"수요의 ?가격탄력성|기회비용|무차별곡선|총수요|통화승수|재무상태표|감가상각)")

# 항목이 될 수 없는 말 — 영역·과목 이름 자체
AREA_ONLY = re.compile(
    r"^(?:ncs|엔시에스|직업기초(?:능력)?|의수문|전공|법령|인성검사|"
    r"의사소통|수리|문제해결|자원관리|정보|기술|조직이해|직업윤리)(?:능력)?$", re.I)

# 나열로 볼 만한 줄인지 — 아무 문장이나 쉼표로 쪼개면 조각이 쏟아진다
ENUM_SHAPE = re.compile(r"(?:[,·/、]\s*\S+){2,}")

# 조각 판정 — 이런 꼴로 끝나면 문장이 잘린 것이다
FRAGMENT_TAIL = re.compile(
    r"(?:하였고|하였으며|이고|이며|으로|로서|에서|에게|부터|까지|보다|처럼|만큼|"
    r"및|또는|와|과|의|에|을|를|이|가|은|는|도|만|\+)$")
FRAGMENT_HEAD = re.compile(r"^(?:그리고|또한|또|하지만|그런데|근데|다만|즉|예를|참고로|>)")


def _split(seg: str) -> list[str]:
    """쉼표로 자르되 **괄호 안은 건드리지 않는다.**

    「대처방안(모래주머니, 근처 공항 피신)」이 두 조각으로 갈리던 것을 막는다.
    """
    out, buf, depth = [], [], 0
    for ch in seg:
        if ch in "([{（【":
            depth += 1
        elif ch in ")]}）】":
            depth = max(0, depth - 1)
        if depth == 0 and ch in ",·/、;":
            out.append("".join(buf)); buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return [s for s in out if s.strip()]


def _clean(v: str) -> str | None:
    """`ingest` 와 같은 기준으로 다듬는다. 못 쓸 것이면 None."""
    v = re.sub(r"\s+", " ", v).strip(" \t:：·-–—*.")
    # 괄호 짝이 안 맞으면 문장이 잘린 조각이다
    if v.count("(") != v.count(")") or v.count("（") != v.count("）"):
        return None
    if FRAGMENT_HEAD.match(v) or FRAGMENT_TAIL.search(v.rstrip(" .")):
        return None
    if AREA_ONLY.match(v.strip()) or MAJOR_VOCAB.search(v):
        return None
    v = re.sub(r"\s*(?:등|등등|등이|등을|등의)\s*$", "", v)
    v = re.sub(r"\s*(?:이|가|을|를|은|는)?\s*"
               r"(?:출제(?:되었|됐|됨|되)\S*|나왔\S*|나옴|있었\S*)\s*$", "", v)
    v = v.strip(" \t:：·-–—*.")
    if not (2 <= len(v) <= 60):
        return None
    if v in KW_NOISE or META.search(v) or BOILERPLATE.search(v):
        return None
    if KW_TAIL.search(v) and not re.search(r"(인지|\?)\s*$", v):
        return None
    if VERB_TAIL.search(v):
        return None
    if not re.search(r"[가-힣A-Za-z]", v):
        return None
    # 조사·접속만 남은 조각
    if re.fullmatch(r"(그|이|저|그리고|또|또한|및|기타|추가|참고)", v):
        return None
    return v


def sections(text: str) -> list[tuple[str, list[str]]]:
    """본문을 (구간종류, 줄들) 로 자른다. 구간종류는 'ncs' · 'major' · '?'."""
    out: list[tuple[str, list[str]]] = []
    kind = "?"
    buf: list[str] = []
    for ln in norm(text).splitlines():
        s = ln.strip()
        if not s:
            continue
        if NCS_MARK.match(s):
            if buf:
                out.append((kind, buf)); buf = []
            kind = "ncs"; continue
        if MAJOR_MARK.match(s):
            if buf:
                out.append((kind, buf)); buf = []
            kind = "major"; continue
        buf.append(s)
    if buf:
        out.append((kind, buf))
    return out


def extract(text: str) -> list[str]:
    """NCS 구간에서 소재 후보를 뽑는다. 등장 순서·중복 없이."""
    found: list[str] = []
    seen: set[str] = set()

    def add(v: str | None):
        if v and v not in seen:
            seen.add(v); found.append(v)

    for kind, lines in sections(text):
        if kind == "major":
            continue                       # 전공·법령 구간은 건드리지 않는다
        for ln in lines:
            if MAJOR_VOCAB.search(ln):
                continue                   # 줄 단독 표지가 없어도 전공이면 건너뛴다
            m = BULLET.match(ln)
            if m:                          # ── 목록형
                body = m.group(1)
                # 한 줄에 여러 개인 경우만 자른다. 짧은 줄은 그 자체가 항목이다.
                parts = _split(body) if len(body) > 24 and ENUM_SHAPE.search(body) else [body]
                for p in parts:
                    add(_clean(p))
                continue

            # ── 산문형: 영역을 밝힌 줄이거나, NCS 구간에서 **나열 신호가 있는** 줄만
            inline = INLINE_AREA.search(ln)
            if not (inline or kind == "ncs"):
                continue
            if not ENUM_CUE.search(ln) and not inline:
                continue
            seg = ln[inline.end():] if inline else ln
            if ENUM_SHAPE.search(seg):
                for p in _split(seg):
                    add(_clean(p))
            elif ENUM_CUE.search(ln):
                add(_clean(seg))
    return found


# ── 점검 ────────────────────────────────────────────────────────────────

def _bodies():
    for p in sorted(pathlib.Path(HERE / "raw").rglob("*.txt")):
        yield p, p.read_text(encoding="utf-8", errors="replace")


# 정밀도 대용 지표 — 아는 소재 어휘. 여기 걸리면 「소재임이 확실한」 항목이다.
KNOWN = re.compile(
    r"사자성어|속담|맞춤법|띄어쓰기|높임|외래어|어휘|한자|접속사|문단|주제|제목|"
    r"내용\s*일치|추론|빈칸|자료\s*해석|도표|그래프|"
    r"SWOT|로직\s*트리|BCG|PEST|JIT|VRIO|브레인스토밍|채찍효과|에이전시|매트릭스|"
    r"캐시카우|테일러|인간관계론|직무기술서|카페테리아|포터|3C|간트|마인드맵|"
    r"명제|참\s*·?\s*거짓|참거짓|논리|오류|허수아비|삼단논법|조건|추리|퍼즐|"
    r"도형|넓이|둘레|면적|수열|규칙|확률|경우의\s*수|소금물|농도|일률|원가|정가|"
    r"할인|이익|진법|나머지|최대공약수|최소공배수|거리|속력|시간|간격|비율|증감|"
    r"엑셀|함수|VLOOKUP|COUNTIF|SUMIF|이진수|코드|알고리즘|순서도|데이터|"
    r"전결|결재|출장|여비|일정|우선순위|자원|예산|인원|배치|"
    r"조직도|결정|의사결정|리더십|갈등|협상|고객|불만|민원|윤리|괴롭힘|"
    r"청렴|봉사|매뉴얼|설명서|산업재해|안전|"
    # 표본 검사에서 KNOWN 이 놓친 진짜 소재들을 보강했다
    r"가치사슬|차별화\s*전략|원가\s*우위|집중화|조직\s*(?:목표|문화|구조)|경영\s*전략|"
    r"기획\s*수집\s*활용\s*관리|정보\s*(?:처리|관리)|벤치마킹|아웃소싱|"
    r"직무\s*(?:특성|분석|평가|순환)|동기\s*부여|욕구|허츠버그|매슬로|맥그리거|"
    r"델파이|명목집단|피드백|경청|프레젠테이션|보고서|기안|공문|회의록|"
    r"모두\s*고르|옳지\s*않은|적절하지\s*않은|알맞은\s*것|해결책|개선\s*방안", re.I)


def measure() -> None:
    import collections
    import json
    db = json.loads((HERE / "db.json").read_text(encoding="utf-8"))
    have = set()
    for r in db:
        k = r.get("kinds") or {}
        if any(k.get(s) == "ncs" and (v or []) for s, v in (r.get("keywords") or {}).items()):
            have.add(r.get("fingerprint"))
    n = hit = added = 0
    items: list[str] = []
    for p, body in _bodies():
        n += 1
        fp = re.match(r"\d{4}-\d{2}-\d{2}_([0-9a-f]{12})\.txt$", p.name)
        got = extract(body)
        if got:
            hit += 1; items.extend(got)
            if fp and fp.group(1) not in have:
                added += 1
    freq = collections.Counter(items)
    known = sum(1 for v in items if KNOWN.search(v))
    recur = sum(1 for v in items if freq[v] >= 2)
    solid = sum(1 for v in items if KNOWN.search(v) or freq[v] >= 2)
    print(f"원문 {n:,}건")
    print(f"  양식으로 잡힌 것            {len(have):,}건")
    print(f"  산문 추출로 뽑히는 것        {hit:,}건")
    print(f"  **새로 잡히는 것**          {added:,}건  → 합 {len(have)+added:,}건")
    print(f"\n  뽑은 소재 문구 {len(items):,}개 (후기당 {len(items)/max(hit,1):.1f}개) "
          f"· 고유 {len(freq):,}개")
    print(f"  ├ 아는 소재 어휘에 걸림      {known:>6,}개 ({known/max(len(items),1)*100:>4.0f}%)")
    print(f"  ├ 둘 이상 후기에서 반복      {recur:>6,}개 ({recur/max(len(items),1)*100:>4.0f}%)")
    print(f"  └ **둘 중 하나라도**        {solid:>6,}개 ({solid/max(len(items),1)*100:>4.0f}%) "
          f"← 정밀도 하한 대용")


def sample(k: int) -> None:
    import hashlib
    rows = [(p, extract(b)) for p, b in _bodies()]
    rows = [(p, g) for p, g in rows if g]
    idx = sorted({int(hashlib.md5(str(i).encode()).hexdigest(), 16) % len(rows)
                  for i in range(k)})
    for i in idx:
        p, g = rows[i]
        print(f"\n[{p.parent.name}] {p.name}  — {len(g)}개")
        for v in g[:12]:
            print(f"    · {v}")


def main() -> int:
    ap = argparse.ArgumentParser(description="산문 본문 소재 추출 (D57)")
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--sample", type=int, metavar="N")
    a = ap.parse_args()
    if a.measure:
        measure()
    if a.sample:
        sample(a.sample)
    if not a.measure and not a.sample:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
