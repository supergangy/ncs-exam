# -*- coding: utf-8 -*-
"""NCS 봉투모의고사 빌더 — content/*.py → HTML → PDF(문제집·해설집)

사용법:
    python build.py            # 전체 빌드 (50문항 완성 시)
    python build.py --preview  # 현재까지 작성된 문항만으로 미리보기 빌드
"""
import argparse
import datetime
import html as htmlmod
import importlib.util
import io
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
OUT = ROOT / "out"
LOGS = ROOT / "logs"
WORKLOG = ROOT / "WORKLOG.md"

_LOG_LINES = []


def log(msg=""):
    """콘솔과 빌드 로그에 동시에 남긴다."""
    print(msg)
    _LOG_LINES.append(str(msg))

EXAM_TITLE = "공기업 NCS 봉투모의고사"
EXAM_ROUND = "실전모의고사 제1회"
TOTAL_Q = 50
TOTAL_MIN = 60

AREAS = [
    ("a1_communication", "의사소통능력", 7),
    ("a2_math", "수리능력", 7),
    ("a3_problem", "문제해결능력", 7),
    ("a4_resource", "자원관리능력", 6),
    ("a5_info", "정보능력", 6),
    ("a6_tech", "기술능력", 6),
    ("a7_org", "조직이해능력", 6),
    ("a8_ethics", "직업윤리", 5),
]

CIRCLED = ["①", "②", "③", "④", "⑤"]

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


# ────────────────────────────────────────────────────────── 적재
def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_blocks(preview: bool):
    blocks, problems, missing = [], [], []
    for mod_name, area, expected in AREAS:
        path = CONTENT / f"{mod_name}.py"
        if not path.exists():
            missing.append(f"{area}({mod_name}.py 없음)")
            continue
        mod = load_module(path)
        area_blocks = list(mod.BLOCKS)
        n = sum(len(b["questions"]) for b in area_blocks)
        if n != expected:
            msg = f"{area}: 문항 수 {n}개 (설계 {expected}개)"
            (problems if not preview else missing).append(msg)
        for b in area_blocks:
            b.setdefault("lead", None)
            b.setdefault("passage", None)
            b["area"] = area
        blocks.extend(area_blocks)

    # 문항 번호 부여
    no = 1
    for b in blocks:
        b["first_no"] = no
        for q in b["questions"]:
            q["no"] = no
            q.setdefault("material", None)
            q.setdefault("type", "")
            q.setdefault("explain", "")
            q.setdefault("each", [])
            no += 1
        b["last_no"] = no - 1
        # 세트 리드문의 [NN~NN] 접두사를 계산된 번호로 강제 교체
        if b["lead"]:
            text = re.sub(r"^\s*\[\s*\d+\s*[~∼\-]\s*\d+\s*\]\s*", "", b["lead"])
            b["lead"] = f"[{b['first_no']:02d}~{b['last_no']:02d}] {text}"
        elif len(b["questions"]) > 1:
            b["lead"] = f"[{b['first_no']:02d}~{b['last_no']:02d}] 다음 자료를 보고 물음에 답하시오."

    return blocks, problems, missing


# ────────────────────────────────────────────────────────── 검증
def validate(blocks, preview: bool):
    errors, warnings = [], []
    answers = []
    for b in blocks:
        for q in b["questions"]:
            no = q["no"]
            if len(q["choices"]) != 5:
                errors.append(f"{no:02d}번: 선택지 {len(q['choices'])}개 (5개여야 함)")
            if q["answer"] not in (1, 2, 3, 4, 5):
                errors.append(f"{no:02d}번: answer={q['answer']} (1~5여야 함)")
            if len(q["each"]) != 5:
                errors.append(f"{no:02d}번: each {len(q['each'])}개 (5개여야 함)")
            if not str(q.get("explain", "")).strip():
                warnings.append(f"{no:02d}번: 해설 비어 있음")
            if len(set(q["choices"])) != len(q["choices"]):
                errors.append(f"{no:02d}번: 중복된 선택지 존재")
            answers.append(q["answer"])

    # 정답 분포
    dist = {i: answers.count(i) for i in range(1, 6)}
    if not preview:
        for i, c in dist.items():
            if not (TOTAL_Q // 5 - 2 <= c <= TOTAL_Q // 5 + 2):
                warnings.append(f"정답 {CIRCLED[i-1]} {c}개 (권장 8~12개)")
    for i in range(len(answers) - 2):
        if answers[i] == answers[i + 1] == answers[i + 2]:
            warnings.append(f"{i+1:02d}~{i+3:02d}번 정답 3연속 동일({CIRCLED[answers[i]-1]})")
    return errors, warnings, dist


# ────────────────────────────────────────────────────────── 렌더
def choice_cols(choices):
    """짧은 선택지는 2단으로 배치한다."""
    plain = [re.sub(r"<[^>]+>", "", htmlmod.unescape(c)) for c in choices]
    return 2 if max(len(p) for p in plain) <= 22 else 1


def build_html(blocks, kind: str, dist=None) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=False,
                      trim_blocks=True, lstrip_blocks=True)
    tpl = env.get_template(f"{kind}.html.j2")

    for b in blocks:
        for q in b["questions"]:
            q["cols"] = choice_cols(q["choices"])

    flat = [q for b in blocks for q in b["questions"]]
    # 영역 헤더 표시 위치 계산
    seen = set()
    for b in blocks:
        b["show_area"] = b["area"] not in seen
        seen.add(b["area"])

    return tpl.render(
        blocks=blocks, questions=flat, circled=CIRCLED,
        exam_title=EXAM_TITLE, exam_round=EXAM_ROUND,
        total_q=TOTAL_Q, total_min=TOTAL_MIN,
        areas=[(a, n) for _, a, n in AREAS],
        answers=[(q["no"], q["answer"]) for q in flat],
        dist=dist or {},
    )


def find_chrome():
    for p in CHROME_CANDIDATES:
        if Path(p).exists():
            return p
    raise RuntimeError("Chrome/Edge 실행 파일을 찾을 수 없습니다.")


def html_to_pdf(html_path: Path, pdf_path: Path):
    chrome = find_chrome()
    with tempfile.TemporaryDirectory() as profile:
        cmd = [
            chrome, "--headless=new", "--disable-gpu", "--no-first-run",
            f"--user-data-dir={profile}",
            "--no-pdf-header-footer",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=20000",
            f"--print-to-pdf={pdf_path}",
            html_path.as_uri(),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=180)
    if not pdf_path.exists():
        raise RuntimeError(f"PDF 생성 실패\nstdout={r.stdout}\nstderr={r.stderr}")


def stamp_page_numbers(pdf_path: Path, skip_first: int = 1):
    """Chrome은 CSS 페이지 마진박스를 지원하지 않으므로 쪽번호를 후처리로 찍는다."""
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas

    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    box = reader.pages[0].mediabox
    w, h = float(box.width), float(box.height)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    for i in range(total):
        if i >= skip_first:
            c.setFont("Helvetica", 9)
            c.drawCentredString(w / 2, 22, f"- {i + 1 - skip_first} -")
        c.showPage()
    c.save()
    buf.seek(0)

    overlay = PdfReader(buf)
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        page.merge_page(overlay.pages[i])
        writer.add_page(page)
    tmp = pdf_path.with_suffix(".stamped.pdf")
    with open(tmp, "wb") as f:
        writer.write(f)
    shutil.move(str(tmp), str(pdf_path))
    return total


# ────────────────────────────────────────────────────────── 로그 기록
def write_build_log(started: datetime.datetime, elapsed: float, outputs):
    """빌드마다 기계 기록을 남기고, WORKLOG.md에 한 줄 요약을 덧붙인다."""
    LOGS.mkdir(exist_ok=True)
    path = LOGS / f"build_{started:%Y%m%d_%H%M%S}.log"
    header = [
        "=" * 68,
        f"빌드 실행  {started:%Y-%m-%d %H:%M:%S}",
        f"명령       python build.py {' '.join(sys.argv[1:])}".rstrip(),
        f"소요       {elapsed:.1f}초",
        "=" * 68,
        "",
    ]
    path.write_text("\n".join(header + _LOG_LINES) + "\n", encoding="utf-8")

    if WORKLOG.exists() and outputs:
        summary = " / ".join(f"{name} {pages}쪽" for name, pages in outputs)
        entry = (
            f"\n### {started:%H:%M} · [빌드] {'미리보기' if '--preview' in sys.argv else '전체'} 빌드\n"
            f"- **행동**: `python build.py {' '.join(sys.argv[1:])}`".rstrip() + "\n"
            f"- **결과**: {summary} · 소요 {elapsed:.1f}초\n"
            f"- **산출물**: `logs/{path.name}`\n"
        )
        with open(WORKLOG, "a", encoding="utf-8") as f:
            f.write(entry)
    return path


# ────────────────────────────────────────────────────────── main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true", help="미완성 상태로 미리보기 빌드")
    args = ap.parse_args()

    started, t0 = datetime.datetime.now(), time.time()
    OUT.mkdir(exist_ok=True)
    outputs = []

    blocks, problems, missing = load_blocks(args.preview)
    if problems:
        log("[중단] 설계와 불일치:")
        for p in problems:
            log(f"  - {p}")
        write_build_log(started, time.time() - t0, outputs)
        sys.exit(1)
    if missing:
        log(f"[미완성] {', '.join(missing)}")

    errors, warnings, dist = validate(blocks, args.preview)
    n_q = sum(len(b["questions"]) for b in blocks)
    log(f"[적재] 블록 {len(blocks)}개 / 문항 {n_q}개")
    log("[정답분포] " + " ".join(f"{CIRCLED[i-1]}{dist[i]}" for i in range(1, 6)))

    log("[문항목록]")
    for b in blocks:
        for q in b["questions"]:
            log(f"  {q['no']:02d}  {b['area']:<7} {q.get('type',''):<18} 정답 {CIRCLED[q['answer']-1]}")

    if errors:
        log("[오류]")
        for e in errors:
            log(f"  - {e}")
        write_build_log(started, time.time() - t0, outputs)
        sys.exit(1)
    if warnings:
        log("[경고]")
        for w in warnings:
            log(f"  - {w}")

    suffix = "_preview" if args.preview else ""
    for kind, label in [("exam", "문제"), ("solution", "해설")]:
        html_path = OUT / f"{kind}{suffix}.html"
        pdf_path = OUT / f"NCS_봉투모의고사_1회_{label}{suffix}.pdf"
        html_path.write_text(build_html(blocks, kind, dist), encoding="utf-8")
        html_to_pdf(html_path, pdf_path)
        pages = stamp_page_numbers(pdf_path)
        log(f"[출력] {pdf_path.name}  ({pages}쪽)")
        outputs.append((pdf_path.name, pages))

    p = write_build_log(started, time.time() - t0, outputs)
    print(f"[로그] {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
