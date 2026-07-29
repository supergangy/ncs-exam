# -*- coding: utf-8 -*-
"""기관별 출제 프로파일 산출

corpus/rounds.json 레지스트리를 읽어 회차를 기관별로 묶고,
발문 유형·세트 비율·자료 구조·분량을 기관 단위로 집계한다.

사용법:
    python corpus/profile.py            # 콘솔 요약
    python corpus/profile.py --md       # docs/INSTITUTION_PROFILES.md 갱신용 마크다운
"""
import argparse
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import CIRCLED, classify_stem, extract_stem, parse_dump, split_questions  # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent


def area_of(qno, areas, names):
    if not areas:
        return "미상"
    acc = 0
    for i, n in enumerate(areas):
        acc += n
        if qno <= acc:
            return names[i]
    return names[-1]


def collect():
    reg = json.loads((ROOT / "rounds.json").read_text(encoding="utf-8"))
    items = []
    for src in reg["sources"]:
        path = REPO / src["file"]
        if not path.exists():
            print(f"[건너뜀] {src['file']} 없음")
            continue
        pages = parse_dump(path)
        rounds = src["rounds"]
        for i, rd in enumerate(rounds):
            start = rd["page"]
            end = (rounds[i + 1]["page"] - 1) if i + 1 < len(rounds) else max(pages)
            body = "\n".join(pages.get(p, "") for p in range(start, end + 1))
            seq = split_questions(body, rd["total"])
            leads = {}
            for mk in seq:
                if mk["kind"] == "LEAD":
                    for q in range(mk["a"], mk["b"] + 1):
                        leads[q] = len(mk["text"])
            for mk in seq:
                if mk["kind"] != "Q":
                    continue
                t = mk["text"]
                stem = extract_stem(t)
                ci = min([t.find(c) for c in CIRCLED if t.find(c) >= 0] or [len(t)])
                items.append({
                    "book": src["book"], "style": src["style"], "org": rd["org"],
                    "round": rd["round"], "no": mk["a"],
                    "area": area_of(mk["a"], rd.get("areas"), rd.get("names")),
                    "type": classify_stem(stem),
                    "chars": ci + leads.get(mk["a"], 0),
                    "shared": mk["a"] in leads,
                    "table": bool(re.search(r"(?m)[<\[]\s*표|^\s*구분\s+\S+\s+\S+", t)),
                    "graph": bool(re.search(r"그\s*래\s*프|[<\[]\s*그\s*림", t)),
                    "bogi": bool(re.search(r"[<\[]\s*보\s*기\s*[>\]]", t)),
                    "jogeon": bool(re.search(r"[<\[]\s*(조\s*건|정\s*보|상\s*황|자\s*료)\s*\d?\s*[>\]]", t)),
                    "footnote": len(re.findall(r"(?m)^\s*(?:※|\*|씨)\s*\S", t)),
                })
    return reg, items


def pct(part, whole):
    return f"{part/whole*100:.0f}%" if whole else "–"


def main(as_md=False):
    reg, items = collect()
    by_org = defaultdict(list)
    for r in items:
        by_org[r["org"]].append(r)

    spec = reg["org_exam_spec"]
    order = sorted(by_org, key=lambda o: -len(by_org[o]))
    out = []
    w = out.append if as_md else (lambda s: print(s))

    if as_md:
        w("# 기관별 출제 프로파일\n")
        w("시판 봉투모의고사를 기관별로 묶어 집계한 출제 경향이다. "
          "우리 문항을 특정 기관색에 맞출 때 이 표를 기준으로 삼는다.\n")
        w(f"수집 총계: **{len(items)}문항 / {len(by_org)}개 기관 / "
          f"{sum(len(s['rounds']) for s in reg['sources'])}회차**\n")

    # ── 개요 표 ──
    if as_md:
        w("\n## 1. 기관별 시험 구성\n")
        w("| 기관 | 회차 | 수집 문항 | 시험 구성 | 문항/시간 | 문항당 |")
        w("|---|---|---|---|---|---|")
        for o in order:
            rounds = sorted({r["round"] for r in by_org[o]})
            sp = spec.get(o, {})
            tot, mins = sp.get("total"), sp.get("minutes")
            per = f"{mins*60/tot:.0f}초" if isinstance(tot, int) and mins else "–"
            w(f"| **{o}** | {len(rounds)}회 | {len(by_org[o])} | {sp.get('ncs','–')} "
              f"| {tot}문항/{mins}분 | {per} |")
    else:
        print("=" * 78)
        print(f"수집 {len(items)}문항 / {len(by_org)}개 기관")
        print("=" * 78)
        for o in order:
            rounds = sorted({r["round"] for r in by_org[o]})
            print(f"  {o:<18} {len(by_org[o]):>4}문항  회차 {rounds}")

    # ── 발문 유형 ──
    if as_md:
        w("\n## 2. 기관별 발문 유형 분포\n")
        w("상위 6개 유형만 표기했다. 분류기가 못 잡은 '기타'는 제외하지 않고 그대로 뒀다.\n")
    else:
        print("\n[기관별 발문 유형]")
    for o in order:
        sub = by_org[o]
        c = Counter(r["type"] for r in sub)
        top = " · ".join(f"{k} {v/len(sub)*100:.0f}%" for k, v in c.most_common(6))
        w(f"- **{o}** — {top}" if as_md else f"  {o:<18} {top}")

    # ── 구조 지표 ──
    if as_md:
        w("\n## 3. 기관별 구조 지표\n")
        w("| 기관 | 세트문항 | 표 | 그래프 | `<보기>` | `<조건>` | 각주/회차 | 본문 중앙값 |")
        w("|---|---|---|---|---|---|---|---|")
    else:
        print("\n[구조 지표]  세트 / 표 / 그래프 / 보기 / 조건 / 각주(회차당) / 본문중앙값")
    for o in order:
        sub = by_org[o]
        n = len(sub)
        nr = len({r["round"] for r in sub})
        ch = sorted(r["chars"] for r in sub if r["chars"] > 0)
        row = (pct(sum(r["shared"] for r in sub), n), pct(sum(r["table"] for r in sub), n),
               pct(sum(r["graph"] for r in sub), n), pct(sum(r["bogi"] for r in sub), n),
               pct(sum(r["jogeon"] for r in sub), n),
               f"{sum(r['footnote'] for r in sub)/nr:.1f}",
               f"{median(ch):.0f}자" if ch else "–")
        if as_md:
            w(f"| **{o}** | " + " | ".join(row) + " |")
        else:
            print(f"  {o:<18} " + " ".join(f"{x:>7}" for x in row))

    # ── 영역별(구성 확인된 기관만) ──
    known = [o for o in order if any(r["area"] != "미상" for r in by_org[o])]
    if as_md:
        w("\n## 4. 영역별 분량·구조 (영역 구성이 확인된 기관)\n")
        w("| 기관 | 영역 | 문항 | 본문 중앙값 | 세트 | 표 | `<보기>` |")
        w("|---|---|---|---|---|---|---|")
    else:
        print("\n[영역별]")
    for o in known:
        sub = by_org[o]
        for an in dict.fromkeys(r["area"] for r in sub if r["area"] != "미상"):
            s2 = [r for r in sub if r["area"] == an]
            ch = sorted(r["chars"] for r in s2 if r["chars"] > 0)
            row = (str(len(s2)), f"{median(ch):.0f}자" if ch else "–",
                   pct(sum(r["shared"] for r in s2), len(s2)),
                   pct(sum(r["table"] for r in s2), len(s2)),
                   pct(sum(r["bogi"] for r in s2), len(s2)))
            if as_md:
                w(f"| {o} | {an} | " + " | ".join(row) + " |")
            else:
                print(f"  {o:<16}{an:<8} " + " ".join(f"{x:>7}" for x in row))

    # ── 유형(피듈 vs 피셋) ──
    if as_md:
        w("\n## 5. 피듈형 vs 피셋형\n")
        w("| 구분 | 문항 | 세트 | 표 | `<보기>` | 각주/회차 | 본문 중앙값 |")
        w("|---|---|---|---|---|---|---|")
    else:
        print("\n[유형 대조]")
    for st in dict.fromkeys(r["style"] for r in items):
        sub = [r for r in items if r["style"] == st]
        nr = len({(r["org"], r["round"]) for r in sub})
        ch = sorted(r["chars"] for r in sub if r["chars"] > 0)
        row = (str(len(sub)), pct(sum(r["shared"] for r in sub), len(sub)),
               pct(sum(r["table"] for r in sub), len(sub)),
               pct(sum(r["bogi"] for r in sub), len(sub)),
               f"{sum(r['footnote'] for r in sub)/nr:.1f}",
               f"{median(ch):.0f}자" if ch else "–")
        if as_md:
            w(f"| **{st}** | " + " | ".join(row) + " |")
        else:
            print(f"  {st:<14} " + " ".join(f"{x:>7}" for x in row))

    if as_md:
        dst = REPO / "docs" / "INSTITUTION_PROFILES.md"
        dst.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"→ {dst}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", action="store_true")
    main(ap.parse_args().md)
