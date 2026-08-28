# -*- coding: utf-8 -*-
"""제6회 자가검증 — SPEC 11절의 체크리스트를 코드로 돌린다.

    python rounds/r6_seoulmetro/selfcheck.py

`build.py` 도 일부를 보지만 그것은 **다 쓴 뒤**에야 돌릴 수 있다. 이 파일은
영역 하나를 쓸 때마다 돌려서, 지금까지 쓴 것만으로 어긋난 곳을 찾는다.

계산 검증은 여기서 하지 않는다 — `verify.py` 가 따로 맡는다(r5 와 같은 규율).
여기서 보는 것은 **모양과 배치**다.
"""
from __future__ import annotations

import ast
import importlib.util
import pathlib
import re
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import importlib
CFG = importlib.import_module(f"rounds.{HERE.name}.config")

CIRC = "①②③④⑤"
# SPEC 4절이 허용한 태그만. 여기 없는 것이 나오면 렌더러가 통째로 버린다
OK_TAGS = {"p", "strong", "em", "u", "br", "div", "table", "caption", "tr", "th", "td",
           "ul", "ol", "li", "code", "sup", "sub", "span"}


def load(mod: str):
    p = HERE / "content" / f"{mod}.py"
    if not p.is_file():
        return None
    ast.parse(p.read_text(encoding="utf-8"))     # 문법 먼저
    spec = importlib.util.spec_from_file_location(mod, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    bad, warn = [], []
    answers, no = [], 0
    written = []

    for mod, area, want in CFG.AREAS:
        m = load(mod)
        if m is None:
            warn.append(f"{area} — 아직 안 썼다 ({mod}.py)")
            continue
        written.append(area)
        qs = [(b, q) for b in m.BLOCKS for q in b["questions"]]
        if len(qs) != want:
            bad.append(f"{area} — 문항 {len(qs)}개, 배정은 {want}개")

        area_ans = []
        for b, q in qs:
            no += 1
            tag = f"{no:02d} {area}"
            if b["area"] != area:
                bad.append(f"{tag} — 블록의 area 가 «{b['area']}» 다")
            if b.get("passage") and not b.get("lead"):
                bad.append(f"{tag} — passage 가 있는데 lead 가 없다 (SPEC 3절)")
            if b.get("lead") and not b.get("passage"):
                bad.append(f"{tag} — lead 가 있는데 passage 가 없다")
            if len(q["choices"]) != 5:
                bad.append(f"{tag} — choices {len(q['choices'])}개")
            if len(q["each"]) != 5:
                bad.append(f"{tag} — each {len(q['each'])}개")
            if not isinstance(q["answer"], int) or not 1 <= q["answer"] <= 5:
                bad.append(f"{tag} — answer «{q['answer']}»")
                continue
            for c in q["choices"]:
                if re.search(f"[{CIRC}]", c):
                    bad.append(f"{tag} — 선지에 원문자가 들어 있다 (렌더러가 붙인다)")
                # 선지는 순수 텍스트다 (SPEC 4절 — HTML 은 지문·자료·해설만)
                if re.search(r"<\w+[ />]", c):
                    bad.append(f"{tag} — 선지에 태그가 있다 (SPEC 4절)")
            for k, e in enumerate(q["each"]):
                if not e.startswith(CIRC[k]):
                    bad.append(f"{tag} — each[{k}] 가 «{CIRC[k]}» 로 시작하지 않는다")
            if "(정답)" not in q["each"][q["answer"] - 1]:
                bad.append(f"{tag} — 정답 자리의 each 에 (정답) 표기가 없다")
            if sum("(정답)" in e for e in q["each"]) != 1:
                bad.append(f"{tag} — (정답) 표기가 하나가 아니다")
            # 발문·리드문은 순수 텍스트 (SPEC 4-1)
            # 발문은 순수 텍스트다. 다만 `&lt;보기&gt;` 는 **엔티티**라 태그가 아니다 —
            # 기존 회차가 전부 그렇게 적는다. 엔티티를 지운 뒤에 꺾쇠를 찾는다.
            plain_stem = re.sub(r"&[a-z]+;", "", q.get("stem") or "")
            if "<" in plain_stem:
                bad.append(f"{tag} — stem 에 태그가 있다 (SPEC 4-1)")
            for html in (b.get("passage"), q.get("material"), q.get("explain")):
                for t in set(re.findall(r"<(\w+)", html or "")):
                    if t.lower() not in OK_TAGS:
                        bad.append(f"{tag} — 허용되지 않은 태그 «{t}» (SPEC 4절)")
            answers.append(q["answer"])
            area_ans.append(q["answer"])

        # 영역 안에서 한 번호가 3개 이상이면 티가 난다 (config PROFILE)
        for n, c in Counter(area_ans).items():
            if c >= 3:
                bad.append(f"{area} — 정답 {CIRC[n-1]} 이 {c}개다 (한 영역 3개 이상 금지)")

    # 3연속 금지 (SPEC 8절)
    for i in range(len(answers) - 2):
        if answers[i] == answers[i + 1] == answers[i + 2]:
            bad.append(f"{i+1}~{i+3}번 — 정답이 3연속 {CIRC[answers[i]-1]} 이다")

    print(f"   {CFG.EXAM_ROUND} — 쓴 영역 {len(written)}/{len(CFG.AREAS)} · 문항 {no}/{CFG.TOTAL_Q}")
    if answers:
        c = Counter(answers)
        print("   정답 분포 —", " ".join(f"{CIRC[k-1]}{c.get(k,0)}" for k in range(1, 6)))
        if no == CFG.TOTAL_Q:
            lo, hi = CFG.TOTAL_Q // 5 - 2, CFG.TOTAL_Q // 5 + 2
            for k in range(1, 6):
                if not lo <= c.get(k, 0) <= hi:
                    bad.append(f"정답 {CIRC[k-1]} 이 {c.get(k,0)}개 — {lo}~{hi} 밖이다")
    for w in warn:
        print("   [남음]", w)
    if bad:
        print(f"\n   지적 {len(bad)}건")
        for b in bad:
            print("     ", b)
        return 1
    print("   지적 없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
