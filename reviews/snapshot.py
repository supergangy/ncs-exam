# -*- coding: utf-8 -*-
"""후기 인용 스냅샷 — **숫자를 언제 기준으로 셌는지 남긴다.**

## 왜 있는가

`db.json` 은 수집기가 돌 때마다 자란다. 그런데 회차 문서에는 「코레일 643건」처럼
**맨숫자**가 박혀 있었다. 2026-08-04 에 하루 만에 839건이 들어오면서 회차 문서의
모든 인용이 한꺼번에 옛것이 됐다 — `D55`.

숫자를 쫓아 계속 고치는 것은 답이 아니다. **어느 시점 기준인지 적으면** 그 숫자는
틀린 것이 아니라 재현 가능한 값이 된다. 이 모듈이 그 시점(스냅샷)을 발급한다.

## 왜 집계 함수를 여기 모으는가

`D54` 는 대조 범위를 상위 기관으로 좁힌 실수였고, 같은 날 **기관 이름을 부분문자열로
매칭해** 국가철도공단·공항철도 18건을 코레일에 섞은 실수가 또 있었다.
둘 다 **그때그때 즉석 집계를 쓴 탓**이다. 그래서 세는 방법을 한 군데로 모으고,
기관은 **정확 일치만** 받는다. 사전에 없는 이름을 주면 조용히 0을 돌려주지 않고 멈춘다.

## 세는 단위

- **후기 단위로 센다.** 한 후기에 「도형」이 세 번 나와도 1건이다.
  (소재 문구 단위로 세면 11,619개가 되어 후기 4,416건과 뒤섞인다)
- `kinds[구역] == "ncs"` 인 구역의 소재만 본다. 전공·법령 구역은 제외한다

```bash
python reviews/snapshot.py take                      # 지금 상태를 스냅샷으로 발급
python reviews/snapshot.py list                      # 발급된 스냅샷 목록
python reviews/snapshot.py verify S-20260804-ab12cd   # 그 뒤로 얼마나 자랐는지
python reviews/snapshot.py cite "도형|넓이|둘레"        # 문서에 붙일 인용문 생성
python reviews/snapshot.py cite "사자성어" --org 한국철도공사
```
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import pathlib
import re
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
DB = HERE / "db.json"
SNAPDIR = HERE / "snapshots"


# ── 적재 ────────────────────────────────────────────────────────────────

def load(path: pathlib.Path | None = None) -> list[dict]:
    rows = json.loads((path or DB).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise SystemExit("[중단] db.json 이 배열이 아니다.")
    return [r for r in rows if isinstance(r, dict)]


def known_orgs(rows: list[dict]) -> set[str]:
    return {r.get("org") for r in rows if r.get("org")}


# ── 정규 집계 ───────────────────────────────────────────────────────────

def _ncs_keywords(row: dict) -> list[str]:
    """NCS 구역의 소재 문구만 돌려준다."""
    kinds = row.get("kinds") or {}
    out = []
    for sec, kws in (row.get("keywords") or {}).items():
        if kinds.get(sec) != "ncs":
            continue
        out.extend(kws or [])
    return out


def org_count(rows: list[dict], org: str) -> int:
    """**정확 일치만.** 부분문자열 매칭은 국가철도공단을 코레일에 섞는다 (`D54`)."""
    ks = known_orgs(rows)
    if org not in ks:
        near = sorted(k for k in ks if org in k or k in org)
        raise SystemExit(f"[중단] 기관 이름이 db 에 없다: {org!r}"
                         + (f"\n  비슷한 이름: {near}" if near else ""))
    return sum(1 for r in rows if r.get("org") == org)


def topical_count(rows: list[dict], org: str | None = None) -> int:
    """**소재를 하나라도 적은** 후기 수. 비율의 분모는 반드시 이 값이다 (`D56`).

    전체 후기의 89%는 소재 구역이 없다 — 양식 없이 자유롭게 쓴 글이라
    `parse_keywords` 가 뽑을 것이 없다. 그런 글을 분모에 넣으면 모든 비율이
    **7배쯤 묽어진다.** 「코레일 후기의 5%가 도형」이라고 적었던 값의 실제는 33% 였다.
    """
    return sum(1 for r in rows
               if (org is None or r.get("org") == org) and _ncs_keywords(r))


def topic_by_org(rows: list[dict], pattern: str) -> Counter:
    """소재가 정규식에 걸리는 **후기 수**를 기관별로 센다."""
    rx = re.compile(pattern, re.I)
    c: Counter = Counter()
    for r in rows:
        if any(rx.search(k) for k in _ncs_keywords(r)):
            c[r.get("org") or "(미상)"] += 1
    return c


# ── 스냅샷 ─────────────────────────────────────────────────────────────

def _identity(row: dict) -> str:
    return (row.get("content_sig") or row.get("form_sig")
            or row.get("fingerprint") or json.dumps(row, sort_keys=True)[:64])


def digest(rows: list[dict]) -> str:
    body = "|".join(sorted(_identity(r) for r in rows))
    return hashlib.sha1(body.encode("utf-8")).hexdigest()


def snapshot_id(rows: list[dict]) -> str:
    """같은 db 면 같은 id 가 나온다. 날짜는 가장 늦은 담긴 날."""
    days = sorted((r.get("ingested_at") or "")[:10] for r in rows if r.get("ingested_at"))
    day = (days[-1] if days else _dt.date.today().isoformat()).replace("-", "")
    return f"S-{day}-{digest(rows)[:6]}"


def build(rows: list[dict]) -> dict:
    return {
        "id": snapshot_id(rows),
        "digest": digest(rows),
        "n_reviews": len(rows),
        "n_orgs": len(known_orgs(rows)),
        "orgs": dict(Counter(r.get("org") or "(미상)" for r in rows).most_common()),
        "ingested_by_day": dict(sorted(Counter(
            (r.get("ingested_at") or "?")[:10] for r in rows).items())),
        # 소재를 어디서 얻었는지 (D57). 양식은 응시자가 골라 적은 것이고 산문은 추론이다.
        "kw_source": dict(Counter(r.get("kw_source") or "?" for r in rows).most_common()),
        "n_topical": sum(1 for r in rows if _ncs_keywords(r)),
    }


def as_of(rows: list[dict], day: str) -> list[dict]:
    """그 날까지 담긴 후기만. **이미 낸 회차의 인용에 뒤늦게 라벨을 달 때 쓴다.**

    회차 문서의 숫자를 최신 db 로 계속 고치는 것은 쳇바퀴다 (`D55`).
    회차는 **만들 때의 스냅샷**을 인용하는 것이 맞고, 그 스냅샷을 여기서 되살린다.
    """
    return [r for r in rows if (r.get("ingested_at") or "")[:10] <= day]


def take(day: str | None = None) -> dict:
    rows = load()
    if day:
        rows = as_of(rows, day)
        if not rows:
            raise SystemExit(f"[중단] {day} 까지 담긴 후기가 없다.")
    snap = build(rows)
    snap["as_of"] = day
    SNAPDIR.mkdir(exist_ok=True)
    p = SNAPDIR / f"{snap['id']}.json"
    fresh = not p.exists()
    p.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[스냅샷] {snap['id']}  후기 {snap['n_reviews']:,}건 · 기관 {snap['n_orgs']}개"
          f"  {'발급' if fresh else '갱신(내용 동일)'}")
    print(f"   {p}")
    return snap


def verify(sid: str) -> int:
    p = SNAPDIR / f"{sid}.json"
    if not p.exists():
        raise SystemExit(f"[중단] 그런 스냅샷이 없다: {sid}\n  {SNAPDIR} 를 보라.")
    old = json.loads(p.read_text(encoding="utf-8"))
    new = build(load())
    same = old["digest"] == new["digest"]
    print(f"[대조] {sid} → 현재")
    print(f"   후기 {old['n_reviews']:,} → {new['n_reviews']:,}"
          f"  ({new['n_reviews'] - old['n_reviews']:+,})")
    if same:
        print("   내용 동일. 그 스냅샷으로 적은 인용은 지금도 유효하다.")
        return 0
    print("   **내용이 달라졌다.** 그 스냅샷 기준 인용은 「당시 기준」으로 읽어야 한다.")
    o, n = old.get("orgs", {}), new.get("orgs", {})
    moved = sorted(((n.get(k, 0) - v, k) for k, v in o.items()), reverse=True)
    added = [(n[k], k) for k in n if k not in o]
    for d, k in moved[:8]:
        if d: print(f"     {k:<24}{o[k]:>5} → {n.get(k,0):<5} ({d:+})")
    for v, k in sorted(added, reverse=True)[:6]:
        print(f"     {k:<24}    — → {v:<5} (새 기관)")
    return 1


def cite(pattern: str, org: str | None, day: str | None = None) -> None:
    """문서에 그대로 붙일 인용문을 만든다."""
    rows = load()
    if day:
        rows = as_of(rows, day)
    snap = build(rows)
    c = topic_by_org(rows, pattern)
    total = sum(c.values())
    ks = snap.get("kw_source") or {}
    print(f"[스냅샷] {snap['id']} · 후기 {snap['n_reviews']:,}건 기준")
    print(f"         소재 있는 후기 {snap.get('n_topical', 0):,}건 "
          f"(양식 {ks.get('form', 0):,} · 산문 {ks.get('prose', 0):,}) — D57")
    print(f"[패턴]   {pattern}\n")
    if org:
        n = c.get(org, 0)
        base = org_count(rows, org)          # 전체 후기 — 비율의 분모로 쓰면 안 된다
        topical = topical_count(rows, org)   # 소재를 적은 후기 — **이게 분모다** (D56)
        others = total - n
        share = f"{n/total*100:.0f}%" if total else "—"
        rate = f"{n/topical*100:.0f}%" if topical else "—"
        print(f"인용문 ─────────────────────────────────────────")
        print(f"  {org} {n}건 — 소재를 적은 후기 {topical}건의 {rate} · "
              f"다른 {len([k for k in c if k != org])}개 기관 {others}건 · "
              f"전체 {total}건 중 {share}  [{snap['id']} 기준]")
        print(f"────────────────────────────────────────────────")
        print(f"  참고: {org} 전체 후기는 {base}건이지만 그중 {base - topical}건은 소재를 "
              f"적지 않았다.\n        전체를 분모로 쓰면 {n/base*100:.1f}% 로 묽어진다 — "
              f"쓰지 말 것 (D56).\n")
    print(f"기관별 ({len(c)}개 기관 · 합 {total}건)   ※ 분모 = 소재를 적은 후기")
    for k, v in c.most_common():
        if k == "(미상)":
            print(f"   {k:<24}{v:>4}건"); continue
        t = topical_count(rows, k)
        print(f"   {k:<24}{v:>4}건 / 소재있음 {t:>3}건 ({v/t*100:>3.0f}%)"
              f"  · 전체 {org_count(rows, k)}건")


def main() -> int:
    ap = argparse.ArgumentParser(description="후기 인용 스냅샷")
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("take", help="지금 상태를 스냅샷으로 발급")
    t.add_argument("--asof", metavar="YYYY-MM-DD",
                   help="그 날까지 담긴 후기만. 이미 낸 회차에 뒤늦게 라벨을 달 때")
    sub.add_parser("list", help="발급된 스냅샷 목록")
    v = sub.add_parser("verify", help="스냅샷 이후 변화량"); v.add_argument("id")
    c = sub.add_parser("cite", help="문서에 붙일 인용문 생성")
    c.add_argument("pattern"); c.add_argument("--org")
    c.add_argument("--asof", metavar="YYYY-MM-DD")
    a = ap.parse_args()

    if a.cmd == "take":
        take(a.asof); return 0
    if a.cmd == "list":
        if not SNAPDIR.exists() or not any(SNAPDIR.glob("*.json")):
            print("발급된 스냅샷이 없다. `take` 를 먼저 하라."); return 0
        for p in sorted(SNAPDIR.glob("*.json")):
            s = json.loads(p.read_text(encoding="utf-8"))
            print(f"   {s['id']:<24}후기 {s['n_reviews']:>6,}건 · 기관 {s['n_orgs']:>3}개")
        return 0
    if a.cmd == "verify":
        return verify(a.id)
    if a.cmd == "cite":
        cite(a.pattern, a.org, a.asof); return 0
    return 0


if __name__ == "__main__":
    # 중단 메시지는 stderr 로 나간다. 여기까지 UTF-8 로 맞춰야 기관 이름이 안 깨진다.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
