# -*- coding: utf-8 -*-
"""소재 문구 군집 — **사전을 손으로 늘리는 일을 대신한다.**

## 왜 있는가

소재 추출은 `lexicon.py` 의 표제어 528개에 `text.find()` 로 부분문자열을 맞춘다.
사전에 없는 표현은 걸리지 않으므로 **「0건」이 「없다」인지 「사전에 없다」인지 구분되지 않는다**
(`D51` · `D54`). 그리고 고유 문구 3,749개 중 **96%가 딱 한 번만 등장한다** —
빈도로 등급을 매기면 이 긴 꼬리가 전부 「★ 단일 증언」으로 묻힌다.

군집은 그 꼬리를 묶는다. 「SWOT」·「SWOT 문제」·「SWOT 표 제시」·「SWOT 전략에 맞는 선지
고르기」는 사전에 SWOT 하나만 있어도 걸리지만, 「20면채 주사위 문제」(오타)·「20면체
주사위 1대1 단판승 확률」·「주사위」는 표기가 갈려 따로 세어진다. 묶으면 한 유형이 된다.

## 방법

**문자 n-gram TF-IDF (2~4) + 코사인 거리 + 평균연결 병합군집.**

형태소 분석기를 쓰지 않는다. 문자 n-gram 은 한국어 짧은 구절에서 조사·어미 변화와
오타에 강하고, 사전도 모델 다운로드도 필요 없다. 문장 임베딩을 쓰면 뜻이 다르고
표기가 같은 것까지 가릴 수 있지만, 지금 목적(표기 변형 묶기)에는 이것으로 충분하다.

임계값은 **눈으로 재서 0.62** 로 잡았다. 0.45 는 너무 잘게 남고, 0.70 부터 서로 다른
소재가 붙기 시작한다. `--threshold` 로 바꿀 수 있다.

```bash
python reviews/cluster.py                              # 전체 · 크기 2 이상
python reviews/cluster.py --org 한국철도공사 --min-size 3
python reviews/cluster.py --new-only                   # 사전에 없는 것만 = 유형 후보
python reviews/cluster.py --asof 2026-08-03 --out docs/TYPES.md
```
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

THRESHOLD = 0.62   # 눈으로 재서 고른 값. 위쪽 docstring 참조
NGRAM = (2, 4)


# ── 재료 ────────────────────────────────────────────────────────────────

def phrases(rows: list[dict]) -> dict[str, dict]:
    """NCS 소재 문구 → {등장 수, 기관 집합}. `snapshot._ncs_keywords` 와 같은 기준."""
    out: dict[str, dict] = {}
    for r in rows:
        kinds = r.get("kinds") or {}
        org = r.get("org") or "(미상)"
        for sec, kws in (r.get("keywords") or {}).items():
            if kinds.get(sec) != "ncs":
                continue
            for k in kws or []:
                s = re.sub(r"\s+", " ", str(k)).strip()
                if not (2 <= len(s) <= 60):
                    continue
                d = out.setdefault(s, {"n": 0, "orgs": collections.Counter()})
                d["n"] += 1
                d["orgs"][org] += 1
    return out


def current_key(word: str, org: str | None) -> str:
    """**지금** `report.py` 가 소재를 묶는 방식 그대로.

    `report._cluster` 는 `TOPICS` 사전을 먼저 보지만 그 사전은 라벨이 2개뿐이라
    사실상 걸리지 않고, **공백을 지운 완전일치**로 떨어진다. 그래서 「사자성어」·
    「사자성어 문제」·「사자성어 맞추기」가 서로 다른 소재 3개로 세어진다.
    고유 문구의 96%가 단일 증언인 진짜 이유가 이것이다.

    군집의 값은 이 기준과 비교해야 드러난다 — 몇 개의 「단일 증언」이 한 유형으로
    합쳐지고, 그래서 몇 개가 ★ 에서 ★★★ 로 올라가는가.
    """
    try:
        import report
        return report._cluster(word, org or "_공통")[0]
    except Exception:
        return "".join(word.split())


def tier(n: int) -> str:
    return "★★★" if n >= 3 else ("★★" if n == 2 else "★")


# ── 군집 ────────────────────────────────────────────────────────────────

def cluster(texts: list[str], threshold: float = THRESHOLD):
    import numpy as np
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.feature_extraction.text import TfidfVectorizer

    X = TfidfVectorizer(analyzer="char_wb", ngram_range=NGRAM,
                        min_df=1, sublinear_tf=True).fit_transform(texts)
    # 문구 수가 4천 안쪽이라 정사각 거리행렬(≈56MB)을 그대로 쓴다.
    # 만 개를 넘기면 kNN 그래프 + 연결요소로 바꿔야 한다.
    D = 1.0 - (X @ X.T).toarray()
    np.fill_diagonal(D, 0.0)
    return AgglomerativeClustering(metric="precomputed", linkage="average",
                                   distance_threshold=threshold,
                                   n_clusters=None).fit_predict(D)


def build(rows: list[dict], threshold: float, org: str | None) -> list[dict]:
    ph = phrases(rows)
    if org:
        # **그 기관 안에서만** 센다. 다른 기관 등장 수를 더하면 기관별 근거가 부풀려진다.
        ph = {k: {"n": v["orgs"][org], "orgs": collections.Counter({org: v["orgs"][org]})}
              for k, v in ph.items() if v["orgs"].get(org)}
    texts = sorted(ph)
    if len(texts) < 2:
        return []
    labels = cluster(texts, threshold)

    groups: dict[int, list[str]] = collections.defaultdict(list)
    for t, c in zip(texts, labels):
        groups[int(c)].append(t)

    out = []
    for c, mem in groups.items():
        hits = sum(ph[m]["n"] for m in mem)
        orgs: collections.Counter = collections.Counter()
        for m in mem:
            orgs.update(ph[m]["orgs"])
        # 대표 문구 — 가장 많이 등장한 것, 같으면 가장 짧은 것 (군더더기가 적다)
        rep = sorted(mem, key=lambda m: (-ph[m]["n"], len(m)))[0]
        # 지금 방식으로는 이 군집이 몇 개의 별개 소재로 세어지는가
        cur = collections.Counter()
        for m in mem:
            cur[current_key(m, org)] += ph[m]["n"]
        out.append({"rep": rep, "members": sorted(mem, key=lambda m: (-ph[m]["n"], m)),
                    "size": len(mem), "hits": hits, "orgs": orgs.most_common(),
                    "n_cur": len(cur), "best_cur": max(cur.values()),
                    "promoted": tier(hits) != tier(max(cur.values()))})
    out.sort(key=lambda g: (-g["hits"], -g["size"], g["rep"]))
    return out


# ── 보고 ────────────────────────────────────────────────────────────────

def render(groups: list[dict], *, snap: str, org: str | None, threshold: float,
           min_size: int, new_only: bool, limit: int) -> str:
    sel = [g for g in groups if g["size"] >= min_size]
    if new_only:
        sel = [g for g in sel if g["promoted"]]
    promoted = [g for g in groups if g["size"] >= min_size and g["promoted"]]
    L = ["# 소재 군집 — 유형 후보", "",
         f"- 스냅샷 `{snap}`" + (f" · 기관 **{org}**" if org else " · 전체 기관"),
         f"- 문자 n-gram TF-IDF {NGRAM} · 평균연결 · 임계 **{threshold}**",
         f"- 군집 **{len(groups):,}개** 중 표기 {min_size}가지 이상 **{len(sel):,}개**"
         + (" · **등급이 오르는 것만**" if new_only else ""), "",
         f"> 지금 `report.py` 는 **공백을 지운 완전일치**로 소재를 묶는다. 그래서 "
         f"「사자성어」·「사자성어 문제」·「사자성어 맞추기」가 서로 다른 소재 3개로 세어진다.",
         f"> 군집으로 합치면 표기 {min_size}가지 이상 묶인 것 중 **{len(promoted)}개가 신뢰도 등급이 오른다** "
         f"— 묻혀 있던 단일 증언이 ★★ · ★★★ 로 올라온다.", "",
         "| 후기 | 표기 | 지금 묶음 | 등급 | 대표 문구 | 기관 |",
         "|---|---|---|---|---|---|"]
    for g in sel[:limit]:
        arrow = f"{tier(g['best_cur'])} → **{tier(g['hits'])}**" if g["promoted"] else tier(g["hits"])
        orgs = " ".join(f"{o} {n}" for o, n in g["orgs"][:3])
        L.append(f"| {g['hits']} | {g['size']} | {g['n_cur']}개로 쪼개짐 | {arrow} "
                 f"| {g['rep'][:38]} | {orgs} |")
    L += ["", "---", "", "## 군집 내용", ""]
    for g in sel[:limit]:
        arrow = (f"**{tier(g['best_cur'])} → {tier(g['hits'])} 승급**"
                 if g["promoted"] else f"{tier(g['hits'])} (등급 변화 없음)")
        L.append(f"### {g['rep'][:56]}  — 후기 {g['hits']}건 · 표기 {g['size']}가지")
        L.append(f"지금은 {g['n_cur']}개 소재로 쪼개져 최대 {g['best_cur']}건 · {arrow}")
        for m in g["members"]:
            L.append(f"- {m}")
        L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="소재 문구 군집으로 유형 후보 뽑기")
    ap.add_argument("--org")
    ap.add_argument("--threshold", type=float, default=THRESHOLD)
    ap.add_argument("--min-size", type=int, default=2)
    ap.add_argument("--new-only", action="store_true", help="사전에 없는 군집만")
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--asof", metavar="YYYY-MM-DD")
    ap.add_argument("--out", metavar="FILE")
    a = ap.parse_args()

    import snapshot
    rows = snapshot.load()
    if a.asof:
        rows = snapshot.as_of(rows, a.asof)
    if a.org:
        snapshot.org_count(rows, a.org)      # 정확 일치 가드 (D54)
    snap = snapshot.snapshot_id(rows)

    groups = build(rows, a.threshold, a.org)
    text = render(groups, snap=snap, org=a.org, threshold=a.threshold,
                  min_size=a.min_size, new_only=a.new_only, limit=a.limit)
    if a.out:
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        print(f"[출력] {p}  ({len(text):,}자)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
