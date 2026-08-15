# -*- coding: utf-8 -*-
"""NCS 봉투모의고사 빌더 — rounds/<회차>/content/*.py → HTML → PDF(문제집·해설집)

사용법:
    python build.py                        # 기본 회차(r1_public) 전체 빌드
    python build.py --round r2_nhis        # 다른 회차 빌드
    python build.py --preview              # 작성된 문항만으로 미리보기
    python build.py --html                 # HTML만 — 고쳐 가며 확인할 때

회차마다 문항 수·영역 배분·기관명이 다르므로 그 값들은 `rounds/<회차>/config.py`에 둔다.
빌드기·조판기·템플릿·스캐너는 회차와 무관하게 한 벌만 유지한다.
"""
import argparse
import datetime
import html as htmlmod
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    # 새 래퍼로 갈아끼우지 않는다. 이 모듈을 import 하는 쪽(selfcheck.py)에서 이미
    # 감쌌다면 중간 래퍼가 GC 되면서 버퍼가 닫힌다.
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
ROUNDS = ROOT / "rounds"
TEMPLATES = ROOT / "templates"
WORKLOG = ROOT / "WORKLOG.md"

DEFAULT_ROUND = "r1_public"

# 회차를 고르면 아래 값들이 채워진다. select_round() 참고.
ROUND = CONTENT = OUT = LOGS = None
CFG = None

_LOG_LINES = []


def log(msg=""):
    """콘솔과 빌드 로그에 동시에 남긴다."""
    print(msg)
    _LOG_LINES.append(str(msg))

START_PAGE = 3          # 본문 첫 면의 PDF 쪽 번호 (표지1 + 안내1 다음). 짝수 = 왼쪽 면

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


def select_round(name: str):
    """회차 설정을 읽어 전역 경로와 사양을 채운다."""
    global ROUND, CONTENT, OUT, LOGS, CFG
    d = ROUNDS / name
    cfg_path = d / "config.py"
    if not cfg_path.exists():
        have = sorted(p.name for p in ROUNDS.iterdir() if (p / "config.py").exists()) \
            if ROUNDS.exists() else []
        raise SystemExit(f"[중단] 회차 '{name}' 를 찾을 수 없습니다. 사용 가능: {', '.join(have) or '없음'}")
    ROUND, CFG = name, load_module(cfg_path)
    CONTENT = d / "content"
    # 회차별로 나누지 않으면 뒤에 빌드한 회차가 앞 회차 산출물을 덮어쓴다.
    OUT, LOGS = ROOT / "out" / name, ROOT / "logs" / name
    return CFG


def load_blocks(preview: bool):
    blocks, problems, missing = [], [], []
    for mod_name, area, expected in CFG.AREAS:
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
    for i, b in enumerate(blocks):
        b["blk"] = i
        b["pagebreak"] = False
        b["spread_break"] = False
        b["first_no"] = no
        for q in b["questions"]:
            q["no"] = no
            q.setdefault("material", None)
            q.setdefault("type", "")
            q.setdefault("explain", "")
            q.setdefault("each", [])
            q.setdefault("why", None)          # 출제 이유서용. 없으면 굽지 않는다
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
        lo, hi = CFG.TOTAL_Q // 5 - 2, CFG.TOTAL_Q // 5 + 2
        for i, c in dist.items():
            if not (lo <= c <= hi):
                warnings.append(f"정답 {CIRCLED[i-1]} {c}개 (권장 {lo}~{hi}개)")
    for i in range(len(answers) - 2):
        if answers[i] == answers[i + 1] == answers[i + 2]:
            warnings.append(f"{i+1:02d}~{i+3:02d}번 정답 3연속 동일({CIRCLED[answers[i]-1]})")
    return errors, warnings, dist


# ────────────────────────────────────────────────────────── 렌더
def choice_cols(choices):
    """짧은 선택지는 2단으로 배치한다."""
    plain = [re.sub(r"<[^>]+>", "", htmlmod.unescape(c)) for c in choices]
    return 2 if max(len(p) for p in plain) <= 22 else 1


def mini_md(s: str) -> str:
    """출제 이유서 전용 — **굵게** 와 `코드` 만 HTML로 바꾼다.

    출제 이유는 산문이라 본문에 태그를 박아 두면 소스가 읽히지 않는다.
    지문·해설과 달리 표현이 단순해 두 가지만 있으면 충분하다.
    """
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", s)


def build_html(blocks, kind: str, dist=None) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=False,
                      trim_blocks=True, lstrip_blocks=True)
    env.filters["md"] = mini_md
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
        brand=CFG.BRAND, exam_title=CFG.EXAM_TITLE, exam_round=CFG.EXAM_ROUND,
        total_q=CFG.TOTAL_Q, total_min=CFG.TOTAL_MIN,
        areas=[(a, n) for _, a, n in CFG.AREAS],
        answers=[(q["no"], q["answer"]) for q in flat],
        dist=dist or {},
        rationale_intro=getattr(CFG, "RATIONALE_INTRO", None),
    )


def renumber(blocks):
    """재배치 후 문항 번호와 세트 리드문을 다시 매긴다."""
    no = 1
    for b in blocks:
        b["first_no"] = no
        for q in b["questions"]:
            q["no"] = no
            no += 1
        b["last_no"] = no - 1
        if b["lead"]:
            text = re.sub(r"^\s*\[\s*\d+\s*[~∼\-]\s*\d+\s*\]\s*", "", b["lead"])
            b["lead"] = f"[{b['first_no']:02d}~{b['last_no']:02d}] {text}"


def apply_layout(blocks, dist):
    """블록 높이를 실측해 펼침면 기준으로 재배치한다."""
    import layout as L
    html = build_html(blocks, "exam", dist)          # 브레이크 없는 측정용 렌더
    H = L.measure(html, find_chrome(), OUT / ".layout")
    hdr, gap = H.get("hdr", 0), H.get("_gap", 8)
    ordered, plog = L.plan(blocks, H, START_PAGE, hdr, gap)
    log(f"[배치] 펼침면 기준 재배치 (면 용량 {L.CAP}px, 블록 간격 {gap}px)")
    log(L.report(plog))
    return ordered


def write_page_map(pdf_path, blocks):
    """문항 → PDF 면·사각형 표를 낸다. 앱의 「PDF로 풀기」가 이것으로 오려 낸다.

    **PDF 에서 뽑는다.** 조판기의 누적 계산으로도 만들어 봤는데 블록 간격을
    평균으로 쓰는 탓에 30문항 중 12문항이 어긋났다. 앱이 보는 것은 PDF 다.

    함께 넣는 `stem` 은 **빌더가 의도한 발문**이다. PDF 에 찍힌 번호와
    빌더의 번호가 어긋나면 여기서 드러난다 — 조판기가 블록 순서를 바꾸므로
    번호는 빌드 시점에 정해지고, 그 결과가 PDF 와 맞는지 볼 자리가 필요하다.
    """
    sys.path.insert(0, str(ROOT / "tools"))
    import pagemap as PM

    want = {}
    for b in blocks:
        for q in b["questions"]:
            want[q["no"]] = re.sub(r"<[^>]+>", "", q["stem"])
    pmap, missing = PM.build_map(pdf_path, ROUND, len(want))
    bad = PM.check(pmap, len(want))
    if missing:
        bad.insert(0, f"번호 표식을 못 찾은 문항: {missing}")

    # 빌더가 아는 발문을 함께 실어 둔다. 검수기가 이것으로 대조한다.
    for q in pmap["questions"]:
        q["stem"] = want.get(q["no"], "")[:60]

    path = OUT / "page_map.json"
    path.write_text(json.dumps(pmap, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    if bad:
        log(f"[문항지도] ⚠ 지적 {len(bad)}건")
        for line in bad[:8]:
            log(f"    {line}")
    else:
        pages = {r["page"] for q in pmap["questions"] for r in q["bounds"]}
        log(f"[문항지도] {len(pmap['questions'])}문항 · {len(pages)}면 → {path.name}")


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
    LOGS.mkdir(parents=True, exist_ok=True)
    path = LOGS / f"build_{started:%Y%m%d_%H%M%S}.log"
    header = [
        "=" * 68,
        f"빌드 실행  {started:%Y-%m-%d %H:%M:%S}",
        f"회차       {ROUND} — {CFG.EXAM_ROUND} ({CFG.TOTAL_Q}문항 / {CFG.TOTAL_MIN}분)",
        f"명령       python build.py {' '.join(sys.argv[1:])}".rstrip(),
        f"소요       {elapsed:.1f}초",
        "=" * 68,
        "",
    ]
    path.write_text("\n".join(header + _LOG_LINES) + "\n", encoding="utf-8")

    # 확인용 HTML 빌드는 WORKLOG에 남기지 않는다. 반복 실행이라 로그만 지저분해진다.
    if WORKLOG.exists() and outputs and "--html" not in sys.argv:
        summary = " / ".join(f"{name} {pages}쪽" for name, pages in outputs)
        entry = (
            f"\n### {started:%H:%M} · [빌드] {CFG.EXAM_ROUND} "
            f"{'미리보기' if '--preview' in sys.argv else '전체'} 빌드\n"
            f"- **행동**: `python build.py {' '.join(sys.argv[1:])}`".rstrip() + "\n"
            f"- **결과**: {summary} · 소요 {elapsed:.1f}초\n"
            f"- **산출물**: `{path.relative_to(ROOT).as_posix()}`\n"
        )
        with open(WORKLOG, "a", encoding="utf-8") as f:
            f.write(entry)
    return path


# ────────────────────────────────────────────────────────── main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true", help="미완성 상태로 미리보기 빌드")
    ap.add_argument("--no-layout", action="store_true",
                    help="펼침면 재배치를 끄고 작성 순서 그대로 출력")
    ap.add_argument("--html", action="store_true",
                    help="HTML만 생성하고 PDF 변환·쪽번호를 건너뛴다 (수정 확인용)")
    ap.add_argument("--round", default=DEFAULT_ROUND, metavar="이름",
                    help=f"빌드할 회차 폴더 이름 (기본 {DEFAULT_ROUND})")
    args = ap.parse_args()

    select_round(args.round)
    started, t0 = datetime.datetime.now(), time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    outputs = []

    log(f"[회차] {ROUND} — {CFG.EXAM_ROUND} "
        f"({CFG.TOTAL_Q}문항 / {CFG.TOTAL_MIN}분 · {len(CFG.AREAS)}개 영역)")
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

    # 문항목록은 50줄이라 확인용 HTML 빌드에서는 접는다.
    if not args.html:
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

    if not args.no_layout:
        blocks = apply_layout(blocks, dist)
        renumber(blocks)                              # 재배치로 바뀐 번호를 다시 매긴다
        printed = [q["answer"] for b in blocks for q in b["questions"]]
        log("[정답순서] " + " ".join(
            f"{q['no']:02d}{CIRCLED[q['answer']-1]}"
            for b in blocks for q in b["questions"]))
        # selfcheck 는 적재 순서만 본다. 재배치로 같은 정답이 이어 붙는 것은
        # 여기서만 잡힌다 (SPEC 8절 — 3연속 금지).
        run = mx = 1
        for a, nxt in zip(printed, printed[1:]):
            run = run + 1 if a == nxt else 1
            mx = max(mx, run)
        if mx >= 3:
            log(f"[경고] 재배치 후 같은 정답이 {mx}번 이어집니다. 선지 순서를 손보십시오.")
        elif mx == 2:
            log("[안내] 재배치 후 같은 정답이 2번 이어지는 곳이 있습니다 (허용 범위).")

    suffix = "_preview" if args.preview else ""
    kinds = [("exam", "문제"), ("solution", "해설")]
    # 출제 이유서는 문항에 why 가 하나라도 있을 때만 낸다.
    # 없는 회차에서 굽으면 「기록 없음」만 늘어선 책이 된다.
    n_why = sum(1 for b in blocks for q in b["questions"] if q.get("why"))
    if n_why:
        kinds.append(("rationale", "출제이유"))
        log(f"[출제이유] {n_why}/{n_q}문항 기록")

    for kind, label in kinds:
        html_path = OUT / f"{kind}{suffix}.html"
        pdf_path = OUT / f"{CFG.FILE_TAG}_{label}{suffix}.pdf"
        html_path.write_text(build_html(blocks, kind, dist), encoding="utf-8")
        if args.html:                                 # 수정 확인용 — PDF는 굽지 않는다
            log(f"[출력] {html_path.relative_to(ROOT)}  (PDF 미생성)")
            continue
        html_to_pdf(html_path, pdf_path)
        pages = stamp_page_numbers(pdf_path)
        log(f"[출력] {pdf_path.name}  ({pages}쪽)")
        outputs.append((pdf_path.name, pages))
        if kind == "exam":
            write_page_map(pdf_path, blocks)

    if args.html:
        log("[안내] 브라우저로 열어 확인하고, 쪽나눔은 Ctrl+P(A4·배율 100%·여백 없음)로 본다.")

    p = write_build_log(started, time.time() - t0, outputs)
    print(f"[로그] {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
