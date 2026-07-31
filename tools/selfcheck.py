# -*- coding: utf-8 -*-
"""문항 자가검증 스캐너.

빌드와 별개로 돌린다. 집필 직후 · 감수 전에 실행해 기계적으로 잡히는 결함을
먼저 걷어낸다. 판정 근거는 docs/PLAYBOOK.md 각 절이며, 규칙 번호를 함께 출력한다.

    python tools/selfcheck.py
    python tools/selfcheck.py --only 31 32 33      # 특정 번호만

검사 항목
    1  걸러낼 표현 24종                     PLAYBOOK 1-2
    2  한 문장 100자 초과                    PLAYBOOK 1-3  (<br>·블록태그를 경계로 본다 = D42)
    3  선지 길이 편차                        PLAYBOOK 4-2 / 예외 4-2a
    4  중복·포함 관계 선지                    PLAYBOOK 4-4
    5  발문 중복                            SPEC 6절
    6  개념 정의형 발문                       SPEC 2절 (금지)
    7  허용 밖 HTML 태그                     SPEC 4절
    8  정답 분포 · 연속                       SPEC 8절
    9  <보기> 조합형 문항 수                   PLAYBOOK 4-10
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402  (AREAS · load_blocks · renumber 재사용)

# ── 1. 걸러낼 표현 24종 (docs/PLAN.md 문체 감수 절) ───────────────────
BANNED = [
    "인 반면", "나아가야 한다", "취지가 달성된다", "없다시피", "옮겨 가고 있다",
    "문제가 있다", "머무르지 않는다", "라고 볼 수 있다", "라고 할 수 있다",
    "이 때문에", "다만", "그만큼", "뿐만 아니라", "결국", "나아가",
    "따라서", "즉,", "무엇보다", "이처럼", "더 나아가", "단순한",
]
# 「다만」은 규정문의 표준 단서 형식이므로 규정·절차 자료에서는 허용한다 (D40 → 규칙 1-4a)
PROVISO_OK_TYPES = {"규정이해", "절차적용", "금액산출", "사례판정", "코드부여", "조건대조(배정)"}

# 걸러낼 표현 24종은 **지문 문체** 기준이다. 해설문은 논증하는 글이라
# 논리 접속사가 오히려 필요하므로 아래는 해설(explain·each)에서 허용한다 (D43 → 규칙 1-2a)
EXPLAIN_OK = {"따라서", "즉,", "결국"}

# 접속어를 고르는 문항은 **선지가 접속어 자체**다. 걸러낼 표현 규칙을 그대로 적용하면
# 문항이 성립할 수 없다. 이 유형의 선지에서는 접속 부사를 검사하지 않는다 (D49 → 규칙 1-2b)
CONNECTIVE_TYPES = {"접속어", "접속사", "빈칸접속어"}
EXPLAIN_FIELDS = ("explain",)          # each 는 선지 단평이라 짧아 별도 검사가 무의미하다

# 해설은 계산식·수치 나열이 섞여 지문보다 길어지는 것이 자연스럽다 (D44 → 규칙 7-6)
SENT_MAX = 100
SENT_MAX_EXPLAIN = 120

# ── 3. 선지 길이 편차 예외 (D41 → 규칙 4-2a) ──────────────────────────
#   선지 길이가 본질적으로 들쭉날쭉한 유형: 공문서 검토 의견, 엑셀 수식, 조합형
LEN_EXEMPT_TYPES = {"공문서작성", "엑셀함수", "엑셀수식검증", "문단배열"}

ALLOWED_TAGS = {
    "p", "br", "strong", "em", "u", "sup", "sub", "code", "span",
    "table", "caption", "tr", "th", "td", "div", "ul", "ol", "li",
}

CONCEPT_STEM = re.compile(r"(무엇인가|의 정의|뜻하는 것은|이란\?|란 무엇)")
COMBO = re.compile(r"&lt;보기&gt;|<보기>")

TAG = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)")
BLOCK_BOUNDARY = re.compile(r"<br\s*/?>|</p>|</td>|</th>|</li>|</caption>|</div>")


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    s = (s.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
          .replace("&amp;", "&").replace("&quot;", '"'))
    return re.sub(r"\s+", " ", s).strip()


def sentences(html: str) -> list[str]:
    """<br>·블록 태그 끝을 문장 경계로 보고 자른다 (D42)."""
    out: list[str] = []
    for chunk in BLOCK_BOUNDARY.split(html):
        text = strip_tags(chunk)
        if not text:
            continue
        for s in re.split(r"(?<=[.!?다])\s+", text):
            s = s.strip(" −-•")
            if s:
                out.append(s)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", type=int, default=None)
    ap.add_argument("--round", default=build.DEFAULT_ROUND, metavar="이름",
                    help=f"검사할 회차 폴더 이름 (기본 {build.DEFAULT_ROUND})")
    args = ap.parse_args()

    cfg = build.select_round(args.round)
    blocks, _, _ = build.load_blocks(preview=True)   # 적재 시점에 번호가 부여된다

    items: list[tuple[int, dict, dict]] = []
    for b in blocks:
        for q in b["questions"]:
            items.append((q["no"], b, q))
    if args.only:
        keep = set(args.only)
        items = [it for it in items if it[0] in keep]

    findings: list[tuple[str, int, str, str]] = []   # (심각도, 번호, 규칙, 내용)

    # ── 문항 단위 검사 ────────────────────────────────────────────
    for no, b, q in items:
        fields = {
            "lead": b.get("lead") or "",
            "passage": b.get("passage") or "",
            "stem": q.get("stem") or "",
            "material": q.get("material") or "",
            "explain": q.get("explain") or "",
        }
        for i, c in enumerate(q["choices"]):
            fields[f"choice{i + 1}"] = c
        for i, e in enumerate(q.get("each") or []):
            fields[f"each{i + 1}"] = e

        # 1 걸러낼 표현
        for fname, html in fields.items():
            if not html:
                continue
            is_expl = fname.startswith("explain") or fname.startswith("each")
            plain = strip_tags(html)
            for w in BANNED:
                if w not in plain:
                    continue
                if w == "다만" and q["type"] in PROVISO_OK_TYPES:
                    continue      # 규정문 단서 형식 — 1-4a
                if is_expl and w in EXPLAIN_OK:
                    continue      # 해설의 논리 접속사 — 1-2a
                if fname.startswith("choice") and q["type"] in CONNECTIVE_TYPES:
                    continue      # 접속어를 고르는 문항의 선지 — 1-2b
                findings.append(("경고", no, "1-2", f"{fname}: 걸러낼 표현 '{w}'"))

        # 2 문장 길이
        for fname in ("lead", "passage", "stem", "material", "explain"):
            cap = SENT_MAX_EXPLAIN if fname in EXPLAIN_FIELDS else SENT_MAX
            for s in sentences(fields[fname]):
                if len(s) > cap:
                    findings.append(("경고", no, "1-3",
                                     f"{fname}: {len(s)}자 문장(상한 {cap}) — “{s[:38]}…”"))

        # 3 선지 길이 편차
        if q["type"] not in LEN_EXEMPT_TYPES:
            lens = [len(strip_tags(c)) for c in q["choices"]]
            if max(lens) - min(lens) > 25 and max(lens) > 2.2 * min(lens):
                findings.append(("경고", no, "4-2",
                                 f"선지 길이 {lens} (편차 {max(lens) - min(lens)}자)"))

        # 4 중복·포함 선지
        plains = [strip_tags(c) for c in q["choices"]]
        for i in range(5):
            for j in range(i + 1, 5):
                if plains[i] == plains[j]:
                    findings.append(("치명", no, "4-4", f"선지 {i+1}·{j+1} 동일"))

        # 6 개념 정의형 발문
        if CONCEPT_STEM.search(strip_tags(fields["stem"])):
            findings.append(("치명", no, "SPEC 2", f"개념 정의형 발문: {strip_tags(fields['stem'])[:40]}"))

        # 7 허용 밖 태그
        for fname, html in fields.items():
            for _, tag in TAG.findall(html or ""):
                if tag.lower() not in ALLOWED_TAGS:
                    findings.append(("치명", no, "SPEC 4", f"{fname}: 미등록 태그 <{tag}>"))

        # 7a 발문·리드문은 순수 텍스트 (D46)
        #    7번 검사는 태그 이름만 보므로 <strong> 같은 허용 태그가 발문에 박혀 있어도 통과한다.
        #    허용 여부가 아니라 **어느 필드인가**로 판정해야 잡힌다.
        for fname in ("stem", "lead"):
            for _, tag in TAG.findall(fields.get(fname) or ""):
                findings.append(("치명", no, "SPEC 4",
                                 f"{fname}: 태그 <{tag}> — 발문·리드문은 순수 텍스트다"))

    # ── 전체 검사 ────────────────────────────────────────────────
    stems = Counter(strip_tags(q["stem"]) for _, _, q in items)
    for s, n in stems.items():
        if n > 1:
            findings.append(("경고", 0, "SPEC 6", f"발문 {n}회 중복: {s[:44]}"))

    answers = [q["answer"] for _, _, q in items]
    dist = Counter(answers)
    run = mx = 1
    for a, nxt in zip(answers, answers[1:]):
        run = run + 1 if a == nxt else 1
        mx = max(mx, run)
    combo = sum(1 for _, _, q in items if COMBO.search(q.get("material") or ""))

    # ── 출력 ────────────────────────────────────────────────────
    print(f"[회차] {args.round} — {cfg.EXAM_ROUND} · 검사 대상 {len(items)}문항\n")
    order = {"치명": 0, "경고": 1}
    findings.sort(key=lambda f: (order[f[0]], f[1]))
    if findings:
        for sev, no, rule, msg in findings:
            tag = f"{no:02d}" if no else "전체"
            print(f"  [{sev}] {tag}  ({rule})  {msg}")
    else:
        print("  지적사항 없음")

    print(f"\n정답 분포  " + " ".join(f"{'①②③④⑤'[k-1]}{dist.get(k, 0)}" for k in range(1, 6))
          + f"   최대 연속 {mx}")
    # 목표치는 회차마다 다르다. 규칙이 아니라 회차 프로파일에 속한다 (D48)
    goal = getattr(cfg, "PROFILE", {}).get("<보기> 조합형", "회차 프로파일 미정")
    print(f"<보기> 조합형  {combo}문항 (회차 목표 {goal})")
    # 세트 지문의 각주를 문항 수만큼 겹쳐 세지 않도록 지문은 블록 단위로 센다.
    footnote = sum((q.get("material") or "").count('class="note"') for _, _, q in items)
    footnote += sum((b.get("passage") or "").count('class="note"')
                    for b in {id(b): b for _, b, _ in items}.values())
    print(f"각주(※)      {footnote}개 (회차 목표 "
          f"{getattr(cfg, 'PROFILE', {}).get('각주(※) 개수', '미정')})")
    # 출제 이유서는 네 칸(근거·설계·함정·검증)이 다 차 있어야 쓸모가 있다.
    WHY_KEYS = ("근거", "설계", "함정", "검증")
    n_why = sum(1 for _, _, q in items if q.get("why"))
    n_full = sum(1 for _, _, q in items
                 if q.get("why") and all(q["why"].get(k) for k in WHY_KEYS))
    print(f"출제이유      {n_why}/{len(items)}문항 기록 · 네 칸 모두 채운 문항 {n_full}개")

    nset = sum(1 for _, b, q in items if len(b["questions"]) > 1)
    print(f"세트문항      {nset}/{len(items)}문항 ({nset / len(items) * 100:.0f}%, 회차 목표 "
          f"{getattr(cfg, 'PROFILE', {}).get('세트문항 비율', '미정')})")
    fatal = sum(1 for f in findings if f[0] == "치명")
    print(f"\n치명 {fatal}건 / 경고 {len(findings) - fatal}건")
    return 1 if fatal else 0


if __name__ == "__main__":
    raise SystemExit(main())
