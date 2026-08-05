# -*- coding: utf-8 -*-
"""지문 규격 검사 — **시판본 실측을 기준으로 우리 지문을 잰다.**

## 왜 있는가

사용자가 4회 인쇄본을 보고 「문장 길이들이 너무 짧다」고 지적했다. 재어 보니
우리 지문의 문장 중앙값이 30~37자인데 시판본은 **54자**였다. 절반이다.

「감으로 길게 쓰자」는 다음에 또 흔들린다. 그래서 **시판본을 자로 삼는다.**
`corpus/raw/pset_9-20_ocr.txt` (피셋형 9~20회, IBK 기업은행 고난도 포함)에서
지문 **199개 · 문장 2,483개**를 뽑아 잰 값이 아래 `SPEC` 이다.

## 무엇이 진짜 차이였나

처음에 3개 지문만 보고 「25자 이하가 0%」라고 단정했다가, 199개로 넓히니
**12.3%** 였다. **짧은 문장이 없는 것이 아니다.**

진짜 차이는 **긴 문장의 꼬리**다. 시판본은 60자 이상이 43%, 100자 이상이 15%인데
우리는 100자 넘는 문장이 거의 없었다. 짧은 문장을 없애는 것이 아니라
**긴 설명 문장을 섞어 분포를 넓히는 것**이 맞다.

```bash
python tools/prosestat.py --round r4_korail        # 회차 지문을 규격과 대조
python tools/prosestat.py --round r4_korail -v     # 문항별 낱낱
python tools/prosestat.py --corpus                 # 기준값을 다시 뽑는다
```
"""
from __future__ import annotations

import argparse
import importlib
import pathlib
import re
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── 시판본 실측 (pset_9-20_ocr.txt · 지문 199개 · 문장 2,483개) ──────────
SPEC = {
    "문장 중앙값": (46, 64, 54),      # (하한, 상한, 실측)
    "25자 이하 비율": (6, 20, 12.3),
    "60자 이상 비율": (33, 53, 43.0),
    "100자 이상 비율": (8, 24, 15.0),
    "지문 길이 중앙값": (600, 1300, 888),
    "지문당 문장 수": (6, 13, 9),
}
CORPUS = ROOT / "corpus" / "raw" / "pset_9-20_ocr.txt"


def split_sents(text: str) -> list[str]:
    # **태그는 공백으로 바꾼다.** 빈 문자열로 지우면 `</p><p>` 자리에서
    # 「있다.문제는」처럼 붙어 문장 분리가 실패한다.
    text = re.sub(r"<[^>]+>", " ", text).replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text)
    return [x.strip() for x in re.split(r"(?<=다\.)\s+|(?<=[.?!])\s+", text)
            if len(x.strip()) >= 8 and not re.match(r"^[①-⑤]", x.strip())]


def round_passages(rnd: str):
    """(문항번호, 지문 원문) 목록. 실무문서·규정·조건 상자는 지문이 아니다."""
    cfg = importlib.import_module(f"rounds.{rnd}.config")
    out, n = [], 0
    for mod, _area, _cnt in cfg.AREAS:
        m = importlib.import_module(f"rounds.{rnd}.content.{mod}")
        for b in m.BLOCKS:
            first = True
            for q in b["questions"]:
                n += 1
                for s in ((b.get("passage") or "") if first else "", q.get("material") or ""):
                    if not isinstance(s, str) or "<p>" not in s:
                        continue
                    # 줄글 지문만 — 표·상자·조문은 짧은 것이 맞다
                    if re.search(r'class="box"|<table|제\d+조|\d+단계|<li>', s):
                        continue
                    out.append((n, s))
                first = False
    return out


def report(rnd: str, verbose: bool) -> int:
    psgs = round_passages(rnd)
    if not psgs:
        print(f"[{rnd}] 줄글 지문이 없습니다."); return 0
    lens, plen, spp = [], [], []
    for n, s in psgs:
        ss = split_sents(s)
        if not ss:
            continue
        L = [len(x) for x in ss]
        lens += L; plen.append(sum(L)); spp.append(len(ss))
        if verbose:
            print(f"   {n:>2}번  문장 {len(L):>2}개 · 중앙값 {statistics.median(L):>3.0f}자 "
                  f"· 최장 {max(L):>3}자 · {sorted(L)}")
    got = {
        "문장 중앙값": statistics.median(lens),
        "25자 이하 비율": sum(1 for x in lens if x <= 25) / len(lens) * 100,
        "60자 이상 비율": sum(1 for x in lens if x >= 60) / len(lens) * 100,
        "100자 이상 비율": sum(1 for x in lens if x >= 100) / len(lens) * 100,
        "지문 길이 중앙값": statistics.median(plen),
        "지문당 문장 수": statistics.median(spp),
    }
    print(f"\n[{rnd}] 줄글 지문 {len(plen)}개 · 문장 {len(lens)}개")
    print(f"{'항목':<18}{'우리':>9}{'시판본':>9}   판정")
    bad = 0
    for k, (lo, hi, ref) in SPEC.items():
        v = got[k]
        ok = lo <= v <= hi
        bad += not ok
        mark = "OK" if ok else ("낮다 ↓" if v < lo else "높다 ↑")
        print(f"{k:<18}{v:>9.1f}{ref:>9.1f}   {mark}")
    print(f"\n   기준 벗어남 {bad}/{len(SPEC)}항목"
          + ("  — 맞음" if not bad else "  (허용 폭은 시판본 실측의 ±35%)"))
    return bad


def corpus() -> int:
    if not CORPUS.exists():
        raise SystemExit(f"[중단] 코퍼스가 없습니다: {CORPUS}\n  (gitignore 대상이라 내려받아야 합니다)")
    t = CORPUS.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"########## PAGE (\d+) \(chars=\d+\) ##########", t)
    body = "\n".join(parts[i + 1] for i in range(1, len(parts), 2))
    body = body.replace("，", ",").replace("（", "(").replace("）", ")").replace("•", "·")
    body = re.sub(r"-\s*\d+\s*-", "\n", body)
    heads = re.finditer(r"(\[\s*\d+\s*[-~]\s*\d+\s*\]|^\s*\d{1,2}\s)[^\n]{0,60}"
                        r"(다음 글|다음은|윗글|다음 자료|이어지는)", body, re.M)
    lens, plen, spp = [], [], []
    for h in heads:
        seg = body[h.end(): h.end() + 4000]
        cut = re.search(r"\n\s*①", seg)
        seg = re.sub(r"\s+", " ", (seg[:cut.start()] if cut else seg[:1500])).strip()
        if not (250 <= len(seg) <= 3000):
            continue
        ss = split_sents(seg)
        if len(ss) < 3:
            continue
        L = [len(x) for x in ss]
        lens += L; plen.append(len(seg)); spp.append(len(ss))
    print(f"■ 시판본 실측 — 지문 {len(plen)}개 · 문장 {len(lens):,}개")
    print(f"   문장 중앙값 {statistics.median(lens):.0f}자 · 평균 {statistics.mean(lens):.0f}자")
    for lab, cond in (("25자 이하", lambda x: x <= 25), ("60자 이상", lambda x: x >= 60),
                      ("100자 이상", lambda x: x >= 100)):
        c = sum(1 for x in lens if cond(x))
        print(f"   {lab} {c:>5}개 ({c/len(lens)*100:.1f}%)")
    print(f"   지문 길이 중앙값 {statistics.median(plen):.0f}자 · "
          f"지문당 문장 {statistics.median(spp):.0f}개")
    print("\n   이 값이 위 SPEC 과 다르면 SPEC 을 고치십시오.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="지문 규격 검사 (시판본 실측 기준)")
    ap.add_argument("--round")
    ap.add_argument("--corpus", action="store_true", help="기준값을 코퍼스에서 다시 뽑는다")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    if a.corpus:
        return corpus()
    if not a.round:
        ap.print_help(); return 0
    return 1 if report(a.round, a.verbose) else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
