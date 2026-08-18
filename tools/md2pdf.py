# -*- coding: utf-8 -*-
"""Markdown → PDF. **문서의 단일 진실은 .md 파일이다.**

## 왜 이렇게 하나

v1.0 명세서는 HTML 을 손으로 썼다. 스타일은 정확했지만 고치기가 번거로웠다 —
한 줄 바꾸려면 태그를 헤집어야 했다.

Markdown 은 편집이 쉬운 대신 표·여백·쪽나눔을 통제할 수 없다.
그래서 **둘을 갈라 둔다** — 내용은 .md 에, 모양은 여기 CSS 한 곳에.
PDF 는 산출물이므로 손으로 만들지 않고 언제든 다시 굽는다.

    python tools/md2pdf.py docs/PROJECT_SPEC.md
    python tools/md2pdf.py docs/PROJECT_SPEC.md --out out/spec/명세서.pdf

이미지는 .md 가 있는 폴더 기준 상대 경로로 쓴다 (`![](ui/01-layout.png)`).
Chrome 이 file:// 로 읽으므로 그대로 들어간다.

렌더는 `build.py` 와 같은 방식이다 — Chrome `--headless --print-to-pdf`.
새 의존성은 없다(markdown 은 이미 있다).
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
import tempfile

import markdown

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CSS = """
@page { size: A4; margin: 17mm 15mm 15mm; }
* { box-sizing: border-box; }
body {
  font: 10pt/1.65 "Pretendard", "맑은 고딕", "Malgun Gothic", sans-serif;
  color: #0f172a; margin: 0; -webkit-print-color-adjust: exact;
}
h1 {
  font-size: 23pt; margin: 0 0 3mm; letter-spacing: -.6px;
  border-bottom: 2.4pt solid #3b5bdb; padding-bottom: 3mm;
}
h1 + p { font-size: 11.5pt; color: #64748b; margin: 0 0 8mm; }
h2 {
  font-size: 14pt; margin: 10mm 0 3.5mm; padding-left: 3mm;
  border-left: 3.6pt solid #3b5bdb; color: #0f172a; letter-spacing: -.3px;
  break-after: avoid;
}
h3 {
  font-size: 11pt; margin: 6mm 0 2.5mm; color: #1e293b;
  break-after: avoid;
}
h2 + h3 { margin-top: 4mm; }
p { margin: 0 0 2.8mm; }
strong { color: #0f172a; font-weight: 700; }
em { color: #64748b; font-style: normal; font-size: 9.2pt; }

table {
  width: 100%; border-collapse: collapse; margin: 0 0 4.5mm;
  font-size: 9pt; break-inside: avoid;
}
th, td {
  border: .5pt solid #e2e8f0; padding: 1.8mm 2.4mm; vertical-align: top;
  text-align: left;
}
th { background: #f1f5f9; font-weight: 700; color: #334155; }
tr:nth-child(even) td { background: #fafbfc; }

code {
  font-family: "SF Mono", Consolas, "D2Coding", monospace; font-size: 8.6pt;
  background: #f1f5f9; padding: .3mm 1mm; border-radius: 2pt; color: #1e293b;
}
pre {
  background: #0f172a; color: #e2e8f0; padding: 3mm 4mm; border-radius: 4pt;
  font-size: 8.2pt; line-height: 1.5; overflow-x: auto; break-inside: avoid;
}
pre code { background: none; color: inherit; padding: 0; }

blockquote {
  margin: 0 0 4mm; padding: 2.6mm 3.4mm; background: #eef2ff;
  border-left: 3pt solid #3b5bdb; border-radius: 3pt; font-size: 9.4pt;
}
blockquote p { margin: 0; }
blockquote strong { color: #3b5bdb; }

ul, ol { margin: 0 0 3.4mm; padding-left: 6.5mm; }
li { margin-bottom: 1mm; }

img {
  max-width: 100%; height: auto; display: block; margin: 2mm 0 1.5mm;
  border: .5pt solid #e2e8f0; border-radius: 4pt;
}

hr {
  border: none; border-top: .5pt solid #e2e8f0; margin: 8mm 0;
  break-before: page;
}
"""


def render(md_path: pathlib.Path, out: pathlib.Path) -> int:
    text = md_path.read_text(encoding="utf-8")
    html_body = markdown.markdown(
        text, extensions=["tables", "fenced_code", "sane_lists", "attr_list"])
    title = (re.search(r"^#\s+(.+)$", text, re.M) or [None, md_path.stem])[1]
    page = (f"<!doctype html><meta charset='utf-8'><title>{title}</title>"
            f"<style>{CSS}</style>{html_body}")

    # HTML 을 .md 옆에 둔다 — 이미지 상대 경로가 그대로 맞는다
    tmp = md_path.with_suffix(".render.html")
    tmp.write_text(page, encoding="utf-8")
    try:
        import build
        chrome = build.find_chrome()
        if not chrome:
            print("[중단] Chrome 을 찾지 못했다")
            return 1
        out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as prof:
            subprocess.run([
                chrome, "--headless=new", "--disable-gpu", "--no-first-run",
                f"--user-data-dir={prof}", "--no-pdf-header-footer",
                "--run-all-compositor-stages-before-draw",
                "--virtual-time-budget=30000",
                f"--print-to-pdf={out}", tmp.as_uri(),
            ], capture_output=True, timeout=180)
    finally:
        tmp.unlink(missing_ok=True)

    if not out.exists():
        print("[중단] PDF 가 만들어지지 않았다")
        return 1
    try:
        import pypdf
        n = len(pypdf.PdfReader(str(out)).pages)
        extra = f" · {n}쪽"
    except Exception:
        extra = ""
    print(f"[출력] {out.relative_to(ROOT)}  {out.stat().st_size/1024:,.0f}KB{extra}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("md")
    ap.add_argument("--out")
    a = ap.parse_args()
    md = pathlib.Path(a.md)
    if not md.is_absolute():
        md = ROOT / md
    out = pathlib.Path(a.out) if a.out else ROOT / "out" / "spec" / f"{md.stem}.pdf"
    if not out.is_absolute():
        out = ROOT / out
    return render(md, out)


if __name__ == "__main__":
    raise SystemExit(main())
