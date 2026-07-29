# -*- coding: utf-8 -*-
"""정답 선지 분포 분석

corpus/answers.json (기관별 정답표 집계)을 읽어
균등 분포 대비 편향, 선지 위치별 경향, 회차 단위 변동폭을 산출한다.

사용법:
    python corpus/answerdist.py         # 콘솔 요약
    python corpus/answerdist.py --md    # docs/ANSWER_DISTRIBUTION.md 생성
"""
import argparse
import io
import json
import sys
from pathlib import Path
from statistics import mean

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8") \
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8" else sys.stdout

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
MARK = "①②③④⑤"


def load():
    return json.loads((ROOT / "answers.json").read_text(encoding="utf-8"))["institutions"]


def main(as_md=False):
    insts = load()
    out = []
    w = out.append if as_md else (lambda s: print(s))

    if as_md:
        w("# 정답 선지 분포 실측\n")
        w("시판 봉투모의고사의 해설편 정답표를 집계한 결과다. "
          "우리 시험의 정답 배치 규칙을 정할 때 이 수치를 기준으로 삼는다.\n")

    total_q = sum(sum(sum(c) for c in i["rounds"].values()) for i in insts)
    n_rounds = sum(len(i["rounds"]) for i in insts)
    w(f"\n집계 대상: **{total_q:,}문항 / {n_rounds}회차 / {len(insts)}개 기관**\n"
      if as_md else f"집계: {total_q:,}문항 / {n_rounds}회차 / {len(insts)}개 기관\n")

    # ── 1. 선지 개수 ──
    if as_md:
        w("\n## 1. 선지 개수는 기관마다 다르다\n")
        w("| 기관 | 선지 | 회차 문항 | 수집 회차 | 텍스트 코퍼스 |")
        w("|---|---|---|---|---|")
        for i in insts:
            w(f"| {i['org']} | **{i['choices']}지선다** | {i['per_round']}문항 | "
              f"{len(i['rounds'])}회 | {'있음' if i['in_text_corpus'] else '없음'} |")
        four = [i["org"] for i in insts if i["choices"] == 4]
        five = [i["org"] for i in insts if i["choices"] == 5]
        w(f"\n**4지선다({len(four)}곳)**: {' · '.join(four)}")
        w(f"\n**5지선다({len(five)}곳)**: {' · '.join(five)}\n")
    else:
        print("[선지 개수]")
        for i in insts:
            print(f"  {i['org']:<16} {i['choices']}지선다  {i['per_round']}문항×{len(i['rounds'])}회")

    # ── 2. 기관별 분포와 균등 대비 배율 ──
    if as_md:
        w("\n## 2. 기관별 정답 분포\n")
        w("`배율`은 균등 분포 대비 값이다. 4지선다는 25%, 5지선다는 20%가 기준(1.00).\n")
    else:
        print("\n[기관별 분포 — 괄호는 균등 대비 배율]")

    ratios = {}   # 위치(0-based) → 배율 목록
    for i in insts:
        k = i["choices"]
        tot = [sum(c[p] for c in i["rounds"].values()) for p in range(k)]
        n = sum(tot)
        unif = 1 / k
        cells = []
        for p in range(k):
            share = tot[p] / n
            r = share / unif
            ratios.setdefault(p, []).append(r)
            cells.append(f"{MARK[p]} {tot[p]}개 {share*100:.1f}% ({r:.2f})")
        if as_md:
            w(f"- **{i['org']}** ({k}지, {n}문항) — " + " · ".join(cells))
        else:
            print(f"  {i['org']:<16} " + " ".join(f"{c:>22}" for c in cells))

    # ── 3. 위치별 경향 ──
    if as_md:
        w("\n## 3. 위치별 경향 — ①번이 일관되게 적다\n")
        w("| 위치 | 기관 수 | 균등 대비 평균 배율 | 최소 | 최대 |")
        w("|---|---|---|---|---|")
    else:
        print("\n[위치별 균등 대비 배율]")
    for p in sorted(ratios):
        rs = ratios[p]
        if as_md:
            w(f"| {MARK[p]} | {len(rs)} | **{mean(rs):.2f}** | {min(rs):.2f} | {max(rs):.2f} |")
        else:
            print(f"  {MARK[p]}  n={len(rs)}  평균 {mean(rs):.2f}  범위 {min(rs):.2f}~{max(rs):.2f}")

    below = sum(1 for r in ratios[0] if r < 1.0)
    line = (f"\n**①번은 {len(ratios[0])}개 기관 중 {below}곳에서 균등 미만**이고 평균 배율 "
            f"{mean(ratios[0]):.2f}다. 즉 첫 선지가 정답일 확률을 의도적으로 낮춘다.")
    w(line if as_md else line.strip())

    mid = [p for p in ratios if 0 < p < max(ratios)]
    midavg = mean([r for p in mid for r in ratios[p]])
    line2 = (f"\n반면 가운데 선지({'·'.join(MARK[p] for p in mid)})의 평균 배율은 "
             f"{midavg:.2f}로 균등 이상이다.")
    w(line2 if as_md else line2.strip())

    # ── 4. 회차 단위 변동폭 ──
    if as_md:
        w("\n## 4. 회차 단위로는 전혀 균등하지 않다\n")
        w("| 기관 | 회차 | 최저 위치 | 최고 위치 | 최고−최저 |")
        w("|---|---|---|---|---|")
    else:
        print("\n[회차별 최저·최고 비율]")
    spreads = []
    for i in insts:
        k = i["choices"]
        for rd, c in i["rounds"].items():
            n = sum(c)
            lo, hi = min(c), max(c)
            lo_p, hi_p = c.index(lo), c.index(hi)
            sp = (hi - lo) / n * 100
            spreads.append(sp)
            if as_md:
                w(f"| {i['org']} | {rd} | {MARK[lo_p]} {lo/n*100:.1f}% | "
                  f"{MARK[hi_p]} {hi/n*100:.1f}% | {sp:.1f}%p |")
    if as_md:
        w(f"\n회차 내 최고−최저 격차는 평균 **{mean(spreads):.1f}%p**, 최대 **{max(spreads):.1f}%p**다.")
    else:
        print(f"  격차 평균 {mean(spreads):.1f}%p / 최대 {max(spreads):.1f}%p")

    if as_md:
        dst = REPO / "docs" / "ANSWER_DISTRIBUTION.md"
        dst.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"→ {dst}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", action="store_true")
    main(ap.parse_args().md)
