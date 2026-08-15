# -*- coding: utf-8 -*-
"""문항 지도(`page_map.json`)가 PDF 와 실제로 맞는지 본다.

조판기가 낸 좌표는 **HTML 렌더 기준**이고 PDF 는 Chrome 이 따로 굽는다.
둘이 어긋나면 앱의 「PDF로 풀기」가 엉뚱한 자리를 오려 낸다. 그런데 그 어긋남은
빌드가 통과해도 드러나지 않는다 — 그래서 여기서 대조한다.

두 가지를 한다.

1. **기계 대조** — 각 사각형 안의 글자를 PDF 에서 뽑아 문항 번호가 맨 앞에
   오는지 본다. 사람 눈이 필요 없고 CI 에서도 돈다
2. **눈 대조** — 사각형을 그린 PDF 를 따로 낸다. 1번이 통과해도 여백이 어색할
   수 있어서, 회차를 처음 만들 때 한 번은 본다

```bash
python tools/pagemap_check.py --round r2_korail
python tools/pagemap_check.py --round r2_korail --draw   # 사각형 그린 PDF 도
```
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load(round_tag: str):
    out = ROOT / "out" / round_tag
    pmap_path = out / "page_map.json"
    if not pmap_path.exists():
        raise SystemExit(f"[중단] {pmap_path} 가 없다. 먼저 build.py 를 돌린다")
    pmap = json.loads(pmap_path.read_text(encoding="utf-8"))
    pdfs = sorted(p for p in out.glob("*문제*.pdf"))
    if not pdfs:
        raise SystemExit(f"[중단] {out} 에 문제집 PDF 가 없다 "
                         "(--html 로만 돌렸으면 PDF 가 없다)")
    return pmap, pdfs[0]


def page_texts(pdf_path: Path):
    """면마다 (왼쪽 위 원점 y, x, 낱말). [pagemap.py] 와 같은 방식으로 읽는다.

    `pypdf` 의 visitor 는 일부 텍스트 런의 행렬을 못 따라간다(그쪽 주석 참고).
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from pagemap import page_items
    return page_items(pdf_path)


def stems_of(pmap):
    """지도에 실린 **빌더가 의도한 발문**. 번호 → 발문.

    원문에서 다시 매기면 안 된다 — 조판기가 여백 채우기로 블록 순서를 바꾸므로
    **번호는 빌드 시점에 정해진다**(README 「문항 번호는 인쇄본과 같다」).
    원본 순서로 매긴 번호와 대조했다가 다섯 문항이 어긋난 것처럼 나왔다.

    그래서 `build.py` 가 지도에 발문을 함께 실어 둔다. 여기서 보는 것은
    「빌더가 N번이라고 여긴 문항이 PDF 의 N번 자리에 실제로 있나」다.
    """
    import html as htmlmod
    return {q["no"]: htmlmod.unescape(re.sub(r"<[^>]+>", "", q.get("stem", "")))
            for q in pmap["questions"] if q.get("stem")}


def check_stems(pmap, pdf_path: Path, stems, slack: float = 6.0):
    """사각형 안의 글자에 그 문항의 발문이 실제로 들어 있나."""
    pages = page_texts(pdf_path)
    bad = 0
    for q in pmap["questions"]:
        want = stems.get(q["no"])
        if not want:
            continue
        r = q["bounds"][0]
        idx = r["page"] - 1
        if idx >= len(pages):
            continue
        inside = "".join(t for (y, x, t) in pages[idx]["items"]
                         if r["y"] - slack <= y <= r["y"] + r["h"] + slack)

        # 꺾쇠 묶음은 양쪽에서 함께 지운다.
        # 발문의 `<보기>` 가 빌더 쪽에서는 태그로 오인돼 지워지는데 PDF 에는
        # 그대로 찍혀, 멀쩡한 문항이 어긋난 것처럼 나왔다(r5 11번).
        def norm(s):
            return re.sub(r"[\s·…()（）]", "", re.sub(r"<[^>]*>", "", s))
        head = norm(want)[:14]
        if head and head not in norm(inside):
            bad += 1
            yield f"{q['no']}번: 발문 「{want[:26]}」가 사각형 안에 없다"
    if bad == 0:
        return


def check(pmap, pdf_path: Path, slack: float = 6.0):
    pages = page_texts(pdf_path)
    bad, checked = [], 0

    pw = pmap["pageSize"]["width"]
    if pages and abs(pages[0]["w"] - pw) > 2:
        bad.append(f"면 너비가 다르다 — 지도 {pw:.0f}pt vs PDF {pages[0]['w']:.0f}pt")

    for q in pmap["questions"]:
        for r in q["bounds"]:
            idx = r["page"] - 1          # 지도의 면 번호는 1부터
            if idx < 0 or idx >= len(pages):
                bad.append(f"{q['no']}번: {r['page']}면이 PDF 에 없다 "
                           f"(전체 {len(pages)}면)")
                continue
            inside = [t for (y, x, t) in pages[idx]["items"]
                      if r["y"] - slack <= y <= r["y"] + r["h"] + slack]
            checked += 1
            if not inside:
                bad.append(f"{q['no']}번: {r['page']}면 그 자리에 글자가 없다 "
                           f"(y {r['y']:.0f}~{r['y'] + r['h']:.0f})")
                continue
            head = "".join(inside[:3]).replace(" ", "")
            want = f"{q['no']:02d}"
            if want not in head:
                bad.append(f"{q['no']}번: 사각형 맨 앞이 「{head[:24]}」 — "
                           f"{want} 가 없다")
    return bad, checked


def draw(pmap, pdf_path: Path, out_path: Path):
    """사각형을 그린 PDF 를 낸다. 눈으로 볼 때만 쓴다."""
    from io import BytesIO
    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.colors import Color
    from reportlab.pdfgen import canvas

    by_page = {}
    for q in pmap["questions"]:
        for r in q["bounds"]:
            by_page.setdefault(r["page"], []).append((q["no"], r))

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    for i, page in enumerate(reader.pages, start=1):
        w, h = float(page.mediabox.width), float(page.mediabox.height)
        if i in by_page:
            buf = BytesIO()
            c = canvas.Canvas(buf, pagesize=(w, h))
            c.setStrokeColor(Color(0.9, 0.2, 0.2, alpha=0.8))
            c.setFillColor(Color(0.9, 0.2, 0.2, alpha=0.12))
            c.setLineWidth(0.8)
            for no, r in by_page[i]:
                # 지도는 위가 원점, PDF 는 아래가 원점이라 뒤집는다
                c.rect(r["x"], h - r["y"] - r["h"], r["w"], r["h"],
                       stroke=1, fill=1)
                c.setFillColor(Color(0.9, 0.2, 0.2, alpha=0.9))
                c.setFont("Helvetica-Bold", 8)
                c.drawString(r["x"] + 2, h - r["y"] - 9, f"{no}")
                c.setFillColor(Color(0.9, 0.2, 0.2, alpha=0.12))
            c.save()
            buf.seek(0)
            page.merge_page(PdfReader(buf).pages[0])
        writer.add_page(page)
    with out_path.open("wb") as f:
        writer.write(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", required=True, metavar="이름")
    ap.add_argument("--draw", action="store_true", help="사각형 그린 PDF 도 낸다")
    a = ap.parse_args()

    pmap, pdf = load(a.round)
    print(f"■ {a.round} — 문항 {len(pmap['questions'])}건 · {pdf.name}")
    bad, checked = check(pmap, pdf)
    print(f"  사각형 {checked}개를 PDF 글자와 대조했다")

    # 번호로 만든 지도를 번호로 보면 순환이다. 발문 원문과도 맞춰 본다.
    stems = stems_of(pmap)
    if stems:
        stem_bad = list(check_stems(pmap, pdf, stems))
        print(f"  발문 {len(stems)}건과 대조했다 — "
              f"{'어긋남 없음' if not stem_bad else f'{len(stem_bad)}건 어긋남'}")
        bad += stem_bad
    else:
        print("  (지도에 발문이 없다 — build.py 로 다시 내면 실린다)")
    if bad:
        print(f"  ⚠ 지적 {len(bad)}건")
        for line in bad[:20]:
            print(f"    {line}")
    else:
        print("  어긋남 없음")

    if a.draw:
        out = pdf.with_name(f"_지도확인_{pdf.stem}.pdf")
        draw(pmap, pdf, out)
        print(f"  사각형을 그렸다 → {out}")

    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
