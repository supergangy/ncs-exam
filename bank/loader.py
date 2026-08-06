# -*- coding: utf-8 -*-
"""문항은행 적재기 — `bank/<기관>/<kind>_<subject>.py` 의 `ITEMS` 를 모은다.

회차는 `pick()` 으로 골라 담는다. **복사하지 않는다** — 복사하면 은행과 회차가 갈라진다.

```bash
python bank/loader.py --list
python bank/loader.py --org 서울교통공사 --kind ncs
python bank/loader.py --id ncs-comm-seoulmetro-001
```
"""
from __future__ import annotations

import argparse
import importlib.util
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
REQUIRED = ("id", "org", "kind", "subject", "area", "questions")
ID_RE = re.compile(r"^(ncs|major)-[a-z]+-[a-z0-9]+-\d{3}$")

# 사실 오류 위험도. **직무 문항은 정답이 지문 밖 사실로 정해지므로** 이 값을 반드시 단다.
#   low    실행으로 정답이 확정된다 (계산·시뮬레이션·SQL 실행)
#   mid    표준 문서·규격에서 값이 고정된다 (OSI 계층·포트 번호·격리수준 표)
#   high   교과서 서술에 의존한다. **사람이 확인해야 한다**
RISK = ("low", "mid", "high")
TAG_RE = re.compile(r"<[a-zA-Z/!]")


def _load(path: pathlib.Path) -> list[dict]:
    spec = importlib.util.spec_from_file_location(f"bank_{path.parent.name}_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(getattr(mod, "ITEMS", []))


def load_all() -> list[dict]:
    """모든 문항. **id 중복은 즉시 멈춘다** — 회차가 어느 쪽을 집을지 알 수 없다."""
    out: list[dict] = []
    seen: dict[str, str] = {}
    for p in sorted(HERE.rglob("*.py")):
        if p.name in ("loader.py", "__init__.py") or p.name.startswith("_test"):
            continue
        for it in _load(p):
            miss = [k for k in REQUIRED if not it.get(k)]
            if miss:
                raise SystemExit(f"[중단] {p.name} 의 문항에 빠진 칸: {miss}\n  {it.get('id')}")
            i = it["id"]
            if not ID_RE.match(i):
                raise SystemExit(f"[중단] id 형식이 다르다: {i}\n"
                                 f"  <ncs|major>-<과목>-<기관>-<3자리>  예) ncs-comm-seoulmetro-001")
            if i in seen:
                raise SystemExit(f"[중단] id 가 겹친다: {i}\n  {seen[i]} / {p}")
            r = it.get("risk")
            if it["kind"] == "major" and r not in RISK:
                raise SystemExit(f"[중단] 직무 문항에 risk 가 없거나 값이 다르다: {i}\n"
                                 f"  {RISK} 중 하나여야 한다 (지금 {r!r})")
            # 규칙 3-7 (`D46`·`D59`) — **발문·머리글은 평문이다.**
            # `selfcheck.py` 의 7a 검사가 회차만 보아 은행이 그대로 새어 나갔다.
            # 강조하고 싶으면 태그가 아니라 문장을 고쳐 쓴다.
            for fname, val in (("lead", it.get("lead")),
                               *(("stem", q.get("stem")) for q in it["questions"])):
                if val and TAG_RE.search(val):
                    raise SystemExit(
                        f"[중단] {fname} 에 태그가 있다 (규칙 3-7 · D46): {i}\n"
                        f"  {val}\n"
                        f"  발문은 평문이다. 굵게 잡으면 어디를 봐야 할지 미리 알려 준다.")
            seen[i] = str(p)
            it["_file"] = str(p.relative_to(HERE))
            out.append(it)
    return out


def pick(*ids: str) -> list[dict]:
    """회차가 부르는 함수. 준 순서대로 돌려준다."""
    have = {it["id"]: it for it in load_all()}
    miss = [i for i in ids if i not in have]
    if miss:
        raise SystemExit(f"[중단] 은행에 없는 id: {miss}")
    return [dict(have[i]) for i in ids]


CIRCLE = "①②③④⑤"


def _plain(html: str) -> str:
    """HTML 을 터미널에서 읽을 수 있게 편다. 표는 `|` 로 세운다."""
    s = html or ""
    s = re.sub(r'<div class="box-title">(.*?)</div>', r"\n[\1]", s)
    s = re.sub(r"<caption>(.*?)</caption>", r"\n[\1]", s)
    s = re.sub(r"<tr[^>]*>", "\n", s)   # 여는 태그도 줄을 바꾼다. 안 하면 첫 행이 제목에 붙는다
    s = re.sub(r"</tr>", "\n", s)
    # `\s*` 를 쓰면 위에서 넣은 줄바꿈까지 먹어 표가 한 줄로 도로 붙는다
    s = re.sub(r"</t[hd]>[ \t]*<t[hd][^>]*>", " | ", s)
    s = re.sub(r"<p[^>]*>", "\n", s)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<svg.*?</svg>", "[그림]", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&nbsp;", " "), ("&lt;", "<"), ("&gt;", ">"), ("&amp;", "&")):
        s = s.replace(a, b)
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in s.splitlines()]
    return "\n".join("   " + l for l in lines if l)


def show(it: dict) -> None:
    """문항 하나를 통째로 — 자료·해설·단평·출제이유까지. 검토는 이걸로 한다."""
    bar = "═" * 74
    print(f"\n{bar}\n{it['id']}   {it['org']} · {it['kind']} · {it['subject']}"
          f" · 난이도 {it.get('difficulty','?')}\n{bar}")
    print(f"근거  {it.get('evidence','—')}")
    print(f"기준  {it.get('snapshot','?')}        파일  {it.get('_file','?')}")
    if it.get("lead"):
        print(f"\n▶ 리드\n   {re.sub('<[^>]+>', '', it['lead'])}")
    if it.get("passage"):
        print(f"\n▶ 지문\n{_plain(it['passage'])}")

    for n, q in enumerate(it["questions"], 1):
        head = f"\n──── 문항 {n}" if len(it["questions"]) > 1 else ""
        if head:
            print(head)
        print(f"\n▶ 발문  [{q.get('type','?')}]\n   {re.sub('<[^>]+>', '', q['stem'])}")
        if q.get("material"):
            print(f"\n▶ 자료\n{_plain(q['material'])}")
        print("\n▶ 선지")
        for j, c in enumerate(q["choices"], 1):
            mark = "   ◀ 정답" if j == q["answer"] else ""
            print(f"   {CIRCLE[j-1]} {re.sub('<[^>]+>', '', str(c))}{mark}")
        if q.get("explain"):
            print(f"\n▶ 해설\n{_plain(q['explain'])}")
        if q.get("each"):
            print("\n▶ 선지 단평")
            for e in q["each"]:
                print(f"   {re.sub('<[^>]+>', '', str(e))}")
        why = q.get("why") or {}
        if why:
            print("\n▶ 출제 이유")
            for k in ("근거", "설계", "함정", "검증"):
                if why.get(k):
                    body = re.sub(r"<[^>]+>", "", str(why[k])).replace("**", "")
                    print(f"   [{k}] {body}")


def main() -> int:
    ap = argparse.ArgumentParser(description="문항은행")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--org")
    ap.add_argument("--kind", choices=("ncs", "major"))
    ap.add_argument("--subject")
    ap.add_argument("--id")
    ap.add_argument("--risk", choices=RISK, help="사실 오류 위험도로 추린다")
    ap.add_argument("--full", action="store_true",
                    help="추려진 문항을 전문으로 펼친다 (검토용)")
    a = ap.parse_args()

    items = load_all()
    if a.id:
        items = [i for i in items if i["id"] == a.id]
    if a.org:
        items = [i for i in items if i["org"] == a.org]
    if a.kind:
        items = [i for i in items if i["kind"] == a.kind]
    if a.subject:
        items = [i for i in items if a.subject in i["subject"]]
    if a.risk:
        items = [i for i in items if i.get("risk") == a.risk]

    if not items:
        print("해당하는 문항이 없습니다."); return 0

    if a.id:
        show(items[0])
        return 0

    if a.full:
        for it in items:
            show(it)
        return 0

    nq = sum(len(i["questions"]) for i in items)
    tally = {r: sum(1 for i in items if i.get("risk") == r) for r in RISK}
    print(f"문항묶음 {len(items)}개 · 문항 {nq}개")
    print(f"위험도  low {tally['low']} · mid {tally['mid']} · "
          f"**high {tally['high']}** (사람 확인 필요)\n")
    print(f"{'id':<30}{'기관':<14}{'과목':<12}{'난이도':<6}{'위험':<6}문항")
    for it in items:
        r = it.get("risk") or "—"
        mark = "HIGH" if r == "high" else r
        print(f"{it['id']:<30}{it['org']:<14}{it['subject']:<12}"
              f"{it.get('difficulty','?'):<6}{mark:<6}{len(it['questions'])}")
    if tally["high"]:
        print(f"\n※ high {tally['high']}건은 교과서 서술에 의존한다. "
              f"`--risk high --full` 로 펼쳐 확인하십시오.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
