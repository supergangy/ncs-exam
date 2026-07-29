# -*- coding: utf-8 -*-
"""PDF → 페이지 단위 텍스트 덤프

사용법:
    python corpus/extract.py "<PDF 경로>" corpus/raw/이름.txt

스캔본이면 텍스트가 거의 나오지 않는다. 그 경우 OCR을 먼저 돌린 뒤
OCR 결과 PDF를 입력으로 넣는다(알PDF·Acrobat·Tesseract 무엇이든 무방).
추출 결과가 페이지당 평균 300자 미만이면 스캔본으로 판단하고 경고한다.
"""
import io
import sys
import time
from pathlib import Path

from pypdf import PdfReader

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def extract(src: Path, dst: Path):
    t = time.time()
    reader = PdfReader(str(src))
    n = len(reader.pages)
    print(f"{src.name}  {n}쪽  (로드 {time.time()-t:.0f}s)")

    dst.parent.mkdir(parents=True, exist_ok=True)
    t, total, empty = time.time(), 0, 0
    with open(dst, "w", encoding="utf-8") as f:
        for i, page in enumerate(reader.pages):
            try:
                txt = page.extract_text() or ""
            except Exception:
                txt = ""
            if len(txt) < 50:
                empty += 1
            total += len(txt)
            f.write(f"\n\n########## PAGE {i+1} (chars={len(txt)}) ##########\n{txt}")
            if (i + 1) % 200 == 0:
                print(f"  {i+1}/{n}쪽 … 누적 {total:,}자")

    avg = total // max(n - empty, 1)
    print(f"완료  {total:,}자 / 빈 페이지 {empty}개 / 유효 페이지당 평균 {avg:,}자 "
          f"({time.time()-t:.0f}s)")
    print(f"→ {dst}")
    if avg < 300:
        print("\n[경고] 페이지당 텍스트가 지나치게 적다. 스캔본일 가능성이 높으니 "
              "OCR을 거친 PDF로 다시 시도할 것.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    extract(Path(sys.argv[1]), Path(sys.argv[2]))
