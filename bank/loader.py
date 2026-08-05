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


def main() -> int:
    ap = argparse.ArgumentParser(description="문항은행")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--org")
    ap.add_argument("--kind", choices=("ncs", "major"))
    ap.add_argument("--subject")
    ap.add_argument("--id")
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

    if not items:
        print("해당하는 문항이 없습니다."); return 0

    if a.id:
        it = items[0]
        print(f"[{it['id']}] {it['org']} · {it['kind']} · {it['subject']} · {it.get('difficulty','?')}")
        print(f"근거: {it.get('evidence','—')}   [{it.get('snapshot','?')}]")
        for q in it["questions"]:
            print(f"\n  발문  {re.sub('<[^>]+>', '', q['stem'])}")
            for j, c in enumerate(q["choices"], 1):
                mark = " ◀정답" if j == q["answer"] else ""
                print(f"    {'①②③④⑤'[j-1]} {re.sub('<[^>]+>', '', str(c))[:70]}{mark}")
        return 0

    nq = sum(len(i["questions"]) for i in items)
    print(f"문항묶음 {len(items)}개 · 문항 {nq}개\n")
    print(f"{'id':<30}{'기관':<14}{'과목':<10}{'난이도':<6}문항")
    for it in items:
        print(f"{it['id']:<30}{it['org']:<14}{it['subject']:<10}"
              f"{it.get('difficulty','?'):<6}{len(it['questions'])}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
