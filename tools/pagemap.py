# -*- coding: utf-8 -*-
"""문항 지도 — **PDF 에서 직접 뽑는다.**

앱의 「PDF로 풀기」가 이 표로 PDF 에서 문항만 오려 낸다. 분석한 PSAT 앱의
`exam_page_mapping.json` 과 같은 목적이다.

## 왜 조판기 계산이 아니라 PDF 인가

처음에는 `layout.py` 의 `plan()` 이 쌓아 둔 면·오프셋으로 지도를 만들었다.
면 나눔을 정하기에는 충분한 계산이지만 **문항별 사각형을 그리기에는 오차가 쌓인다** —
블록 간격을 평균값으로 쓰기 때문이다. 30문항 가운데 12문항이 어긋났다.

앱이 보는 것은 PDF 다. 그러니 PDF 를 읽는다.

## 문항의 시작을 어떻게 아나

발문 앞의 `<span class="qno">` 가 `01`·`02` 처럼 **두 자리 숫자만** 따로 찍힌다.
그것이 왼쪽 여백 자리에 오는 것을 표시로 삼는다. 본문 속 숫자와 헷갈리지 않게
**기대하는 번호와 정확히 같고 왼쪽 끝에 있는 것**만 받는다.

```bash
python tools/pagemap.py --round r2_korail          # page_map.json 을 낸다
python tools/pagemap.py --round r2_korail --dump   # 뽑힌 표식을 훑어본다
```
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MM = 2.834645669291339
MARGIN_L = 15 * MM          # @page margin: 17mm 15mm 18mm 15mm
MARGIN_T = 17 * MM
MARGIN_B = 18 * MM
CONTENT_W = 180 * MM

LEFT_SLACK = 6.0            # 왼쪽 끝으로 볼 여유(pt)
TOP_PAD = 3.0               # 번호 글자 위로 조금 넉넉히
BOTTOM_GAP = 6.0            # 다음 문항과의 사이를 조금 비운다


def page_items(pdf_path: Path):
    """면마다 (왼쪽 위 원점 y, x, 낱말).

    **`pypdf` 로는 안 된다.** 그쪽 `extract_text(visitor_text=…)` 는 일부 텍스트
    런의 행렬을 못 따라가 `tm[5]` 가 0 으로 나온다 — 발문 조각의 y 가 −1438 로
    튀었다. 번호 표식만 우연히 맞아 지도가 서는 것처럼 보였다.
    `pdfplumber` 는 낱말마다 상자를 준다.
    """
    import logging
    import pdfplumber
    # 맑은고딕에 FontBBox 가 없어 pdfminer 가 낱말마다 경고를 뱉는다.
    # 좌표에는 영향이 없고 화면만 덮으므로 잠재운다.
    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    pages = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for p in pdf.pages:
            words = p.extract_words(use_text_flow=True)
            items = sorted((w["top"], w["x0"], w["text"]) for w in words)
            pages.append({"h": p.height, "w": p.width, "items": items})
    return pages


def find_markers(pages, total_q: int):
    """문항 번호 표식을 순서대로 찾는다. 돌려주는 것은 `번호 → (면, y)`."""
    want, found, missing = 1, {}, []
    for pno, page in enumerate(pages, start=1):
        for y, x, t in page["items"]:
            if want > total_q:
                break
            if x > MARGIN_L + LEFT_SLACK:
                continue                       # 왼쪽 끝이 아니면 본문 숫자다
            if re.fullmatch(r"\d{2}", t) and int(t) == want:
                found[want] = (pno, y)
                want += 1
    for n in range(1, total_q + 1):
        if n not in found:
            missing.append(n)
    return found, missing


def build_map(pdf_path: Path, round_tag: str, total_q: int):
    pages = page_items(pdf_path)
    found, missing = find_markers(pages, total_q)
    if not pages:
        raise SystemExit("[중단] PDF 에 면이 없다")
    ph, pw = pages[0]["h"], pages[0]["w"]
    bottom = ph - MARGIN_B

    # 같은 면의 다음 표식이 이 문항의 끝이다
    by_page = {}
    for no, (pno, y) in found.items():
        by_page.setdefault(pno, []).append((y, no))
    for v in by_page.values():
        v.sort()

    out = []
    for no in sorted(found):
        pno, y = found[no]
        same = by_page[pno]
        idx = [i for i, (_, n) in enumerate(same) if n == no][0]
        end = same[idx + 1][0] - BOTTOM_GAP if idx + 1 < len(same) else bottom
        top = max(MARGIN_T, y - TOP_PAD)
        out.append({
            "no": no,
            "bounds": [{
                "page": pno,
                "x": round(MARGIN_L, 2),
                "y": round(top, 2),
                "w": round(CONTENT_W, 2),
                "h": round(max(0.0, end - top), 2),
            }],
        })

    return {
        "round": round_tag,
        "unit": "pt",
        "origin": "top-left",
        "pageSize": {"width": round(pw, 2), "height": round(ph, 2)},
        "source": pdf_path.name,
        "questions": out,
    }, missing


def check(pmap, total_q: int):
    """성립하는지 본다. 돌려주는 것은 사람이 읽을 지적 목록."""
    bad = []
    qs = pmap["questions"]
    nos = [q["no"] for q in qs]
    if len(nos) != total_q:
        bad.append(f"문항 수가 {len(nos)}건 — {total_q}건이어야 한다")
    if len(set(nos)) != len(nos):
        bad.append(f"번호가 겹친다: {sorted({n for n in nos if nos.count(n) > 1})}")
    ph = pmap["pageSize"]["height"]
    for q in qs:
        for r in q["bounds"]:
            if r["h"] <= 20:
                bad.append(f"{q['no']}번 높이가 {r['h']:.0f}pt 로 너무 얕다")
            if r["y"] + r["h"] > ph + 1:
                bad.append(f"{q['no']}번이 면 아래로 넘친다")
    per_page = {}
    for q in qs:
        for r in q["bounds"]:
            per_page.setdefault(r["page"], []).append(
                (r["y"], r["y"] + r["h"], q["no"]))
    for page, spans in per_page.items():
        spans.sort()
        for (y1, e1, n1), (y2, _, n2) in zip(spans, spans[1:]):
            if e1 > y2 + 1:
                bad.append(f"{page}면에서 {n1}번과 {n2}번이 겹친다")
    return bad


def find_pdf(round_tag: str) -> Path:
    out = ROOT / "out" / round_tag
    pdfs = [p for p in out.glob("*문제*.pdf") if not p.name.startswith("_")]
    if not pdfs:
        raise SystemExit(f"[중단] {out} 에 문제집 PDF 가 없다")
    return sorted(pdfs)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", required=True, metavar="이름")
    ap.add_argument("--dump", action="store_true", help="뽑힌 표식을 훑는다")
    a = ap.parse_args()

    sys.path.insert(0, str(ROOT))
    cfg_path = ROOT / "rounds" / a.round / "config.py"
    if not cfg_path.exists():
        raise SystemExit(f"[중단] {cfg_path} 가 없다")
    import importlib.util
    spec = importlib.util.spec_from_file_location("cfg", cfg_path)
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)

    pdf = find_pdf(a.round)
    pmap, missing = build_map(pdf, a.round, cfg.TOTAL_Q)
    print(f"■ {a.round} — {pdf.name}")
    print(f"  문항 {len(pmap['questions'])}/{cfg.TOTAL_Q}건 · "
          f"면 {len({r['page'] for q in pmap['questions'] for r in q['bounds']})}개")
    if missing:
        print(f"  ⚠ 표식을 못 찾은 문항: {missing}")
    for line in check(pmap, cfg.TOTAL_Q):
        print(f"    {line}")

    if a.dump:
        for q in pmap["questions"]:
            r = q["bounds"][0]
            print(f"    {q['no']:>2}번  {r['page']}면  y {r['y']:>6.1f} "
                  f"h {r['h']:>6.1f}")

    path = ROOT / "out" / a.round / "page_map.json"
    path.write_text(json.dumps(pmap, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"  → {path}")


if __name__ == "__main__":
    main()
