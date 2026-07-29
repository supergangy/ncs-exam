# -*- coding: utf-8 -*-
"""시판 봉투모의고사 코퍼스 분석기

corpus/raw/*.txt (pypdf로 추출한 페이지 덤프)를 읽어
회차·문항 단위로 분해하고 통계를 산출한다.

사용법:
    python corpus/analyze.py corpus/raw/pidule_1-8_ocr.txt --label "건보 1~8회(피듈형)" --areas 20,20,20
    python corpus/analyze.py corpus/raw/pset_9-20_ocr.txt  --label "닥공 9~20회(피셋형)" --areas 10,10,10,10,10

출력: corpus/parsed/<label>.json  +  콘솔 요약
"""
import argparse
import json
import re
import sys
import io
from collections import Counter
from pathlib import Path
from statistics import mean, median

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parent

# OCR이 흔히 깨뜨리는 문자 정규화
NORM = {
    "（": "(", "）": ")", "〜": "~", "∼": "~",
    "，": ",", "．": ".", "：": ":", "；": ";", "？": "?", "！": "!",
    "０": "0", "１": "1", "２": "2", "３": "3", "４": "4",
    "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
    # OCR이 꺾쇠를 여러 글자로 흩뿌리므로 전부 < > 로 접는다
    "〈": "<", "〉": ">", "＜": "<", "＞": ">", "《": "<", "》": ">",
    "［": "[", "］": "]", "【": "[", "】": "]",
}
CIRCLED = "①②③④⑤"


def normalize(s: str) -> str:
    for a, b in NORM.items():
        s = s.replace(a, b)
    return s


# OCR이 반복적으로 틀리는 한글 (조사·어미 중심). 분류용 매칭에만 적용한다.
FUZZ = str.maketrans({"올": "을", "율": "을", "울": "을",
                      "룰": "를", "롤": "를", "릎": "를",
                      "잘": "절", "옴": "음", "롤": "를"})


def fuzzy(s: str) -> str:
    return normalize(s).translate(FUZZ)


# ── 발문 유형 분류 (위에서부터 우선 적용) ─────────────────────
STEM_PATTERNS = [
    # 자료·계산
    ("자료변환",   r"(그래프|표)로\s*(작성|변환|나타낸)|나타낸\s*그래프"),
    ("빈칸수치",   r"들어갈\s*수치|수치를\s*바르게|들어갈\s*(숫자|값)"),
    ("순서비교",   r"큰\s*순서대로|작은\s*순서대로|순서대로\s*나열|많은\s*순"),
    ("금액산출",   r"얼마인가|총\s*(비용|금액|요금|액)|(총액|부담금|지원금|수당)을?\s*고르"),
    ("수량산출",   r"몇\s*(개|명|가지|번|일|시간|분|%|퍼센트|원)"),
    ("계산일반",   r"구하면|산출하면|계산하면|합은|차이는|비중은|증가율은"),
    # 논리·조건
    ("반드시참",   r"반드시\s*참|항상\s*참"),
    ("보기조합",   r"[<\[]\s*보\s*기\s*[>\]].{0,60}(모두\s*고|골라|묶은)"),
    ("보기조합",   r"보기.{0,25}(에서\s*(모두\s*)?고|골라\s*바르게)"),
    ("짝짓기",     r"바르게\s*(묶은|짝지은|연결한)|옳게\s*짝지은"),
    # 독해 조작
    ("문단배열",   r"(순서대로|흐름상|문맥에\s*맞게).{0,12}(배열|나열)|배열한\s*것"),
    ("문장삭제",   r"삭제되어야\s*할|생략해도\s*좋은|불필요한\s*문장"),
    ("빈칸",       r"빈칸|괄호\s*안에|들어갈\s*(말|내용|것|문장|접속)"),
    ("서술방식",   r"서술\s*(방식|상\s*특징)|전개\s*방식|글쓰기\s*전략"),
    ("주제중심",   r"주제|중심\s*내용|제목|요지|필자의\s*주장"),
    # 진위 판정 — 가장 흔하므로 뒤에 둔다
    ("불가추론",   r"알\s*수\s*없는"),
    ("추론",       r"추론|유추|짐작|미루어"),
    ("일치불일치", r"(일치|부합)하지\s*않"),
    ("일치",       r"(일치|부합)하는"),
    ("인물판단",   r"(사람|직원)을?\s*고르|잘못\s*이해한\s*사람"),
    ("사례적용",   r"사례로\s*(적절|알맞)|해당하(는|지\s*않는)\s*(사례|것|사람)"),
    ("옳지않은",   r"(옳지|적절하지|적절하지|바르지|타당하지|적잘하지)\s*않"),
    ("옳지않은",   r"잘못\s*(이해|파악|설명)"),
    ("옳은것",     r"(옳은|적절한|바른|타당한|알맞은)\s*것"),
    ("이해판단",   r"이해한\s*내용|설명으로|파악한\s*내용"),
]


def classify_stem(stem: str) -> str:
    s = fuzzy(stem)
    for name, pat in STEM_PATTERNS:
        if re.search(pat, s):
            return name
    return "기타"


def parse_dump(path: Path):
    txt = path.read_text(encoding="utf-8")
    parts = re.split(r"########## PAGE (\d+) \(chars=(\d+)\) ##########", txt)
    return {int(parts[i]): parts[i + 2] for i in range(1, len(parts), 3)}


def find_rounds(pages):
    """'실전모의고사 N회' 응시 안내 페이지를 회차 시작점으로 삼는다."""
    marks = []
    for p in sorted(pages):
        b = normalize(pages[p])
        if re.search(r"수험번호", b) and re.search(r"실전\s*모의고사\s*(\d+)\s*회", b):
            m = re.search(r"실전\s*모의고사\s*(\d+)\s*회", b)
            marks.append((int(m.group(1)), p))
    # 회차 번호 중복 제거(첫 등장만)
    seen, out = set(), []
    for r, p in marks:
        if r not in seen:
            seen.add(r); out.append((r, p))
    out.sort(key=lambda x: x[1])
    rounds = []
    last = max(pages)
    for i, (r, p) in enumerate(out):
        end = out[i + 1][1] - 1 if i + 1 < len(out) else last
        rounds.append({"round": r, "start": p, "end": end})
    return rounds


def split_questions(body: str, maxq: int):
    """본문에서 문항 시작 위치를 찾는다.

    OCR 누락·오인식에 견디도록, 후보 번호 마커 중 '위치 오름차순 + 번호 증가'를
    만족하는 최장 체인(LIS)을 골라 문항 경계로 삼는다. 번호 하나를 놓쳐도
    뒤쪽 문항이 통째로 유실되지 않는다.
    """
    body = normalize(body)

    leads = []
    for m in re.finditer(r"(?m)^\s*\[\s*(\d{1,2})\s*[-~]\s*(\d{1,2})\s*\]", body):
        a, b = int(m.group(1)), int(m.group(2))
        if 1 <= a <= b <= maxq:
            leads.append({"pos": m.start(), "kind": "LEAD", "a": a, "b": b})

    cands = []
    for m in re.finditer(r"(?m)^\s*(\d{1,2})\s*[.)]?\s+(?=[가-힣<(\[「※'\"])", body):
        n = int(m.group(1))
        if 1 <= n <= maxq:
            cands.append({"pos": m.start(), "kind": "Q", "a": n})
    if not cands:
        return sorted(leads, key=lambda x: x["pos"])

    # LIS (번호 strictly increasing, 위치는 이미 오름차순)
    N = len(cands)
    best = [1] * N
    prev = [-1] * N
    for i in range(N):
        for j in range(i):
            if cands[j]["a"] < cands[i]["a"] and best[j] + 1 > best[i]:
                best[i] = best[j] + 1
                prev[i] = j
    end = max(range(N), key=lambda i: best[i])
    chain = []
    while end != -1:
        chain.append(cands[end])
        end = prev[end]
    chain.reverse()

    seq = sorted(chain + leads, key=lambda x: x["pos"])
    for i, mk in enumerate(seq):
        stop = seq[i + 1]["pos"] if i + 1 < len(seq) else len(body)
        mk["text"] = body[mk["pos"]:stop]
    return seq


def area_of(qno: int, areas):
    """영역별 문항 수 리스트로 문항번호 → 영역 인덱스."""
    acc = 0
    for i, n in enumerate(areas):
        acc += n
        if qno <= acc:
            return i
    return len(areas) - 1


def analyze(path, label, areas, area_names):
    pages = parse_dump(path)
    rounds = find_rounds(pages)
    maxq = sum(areas)
    records = []

    for rd in rounds:
        body = "\n".join(pages.get(p, "") for p in range(rd["start"], rd["end"] + 1))
        seq = split_questions(body, maxq)
        leads = {}
        for mk in seq:
            if mk["kind"] == "LEAD":
                for q in range(mk["a"], mk["b"] + 1):
                    leads[q] = len(mk["text"])
        for mk in seq:
            if mk["kind"] != "Q":
                continue
            t = mk["text"]
            lines = [l.strip() for l in t.split("\n") if l.strip()]
            stem = lines[0] if lines else ""
            # 선택지 이전까지를 본문(발문+자료)으로 본다
            ci = min([t.find(c) for c in CIRCLED if t.find(c) >= 0] or [len(t)])
            records.append({
                "round": rd["round"], "no": mk["a"],
                "area": area_names[area_of(mk["a"], areas)],
                "stem": stem[:160],
                "type": classify_stem(stem),
                "body_chars": ci + leads.get(mk["a"], 0),
                "shared": mk["a"] in leads,
                "n_choices": sum(1 for c in CIRCLED if c in t),
                "has_table": bool(re.search(r"(?m)[<\[]\s*표|^\s*구분\s+\S+\s+\S+", t)),
                "has_graph": bool(re.search(r"그\s*래\s*프|[<\[]\s*그\s*림", t)),
                "has_bogi": bool(re.search(r"[<\[]\s*보\s*기\s*[>\]]", t)),
                "has_jogeon": bool(re.search(r"[<\[]\s*(조\s*건|정\s*보|상\s*황|자\s*료)\s*\d?\s*[>\]]", t)),
                # OCR이 ※ 를 * 나 '씨' 로 자주 오인식하므로 행 머리 마커까지 인정
                "n_footnote": len(re.findall(r"(?m)^\s*(?:※|\*|씨)\s*\S", t)),
            })

    out = ROOT / "parsed"; out.mkdir(exist_ok=True)
    dst = out / (re.sub(r"[^\w가-힣]+", "_", label).strip("_") + ".json")
    dst.write_text(json.dumps({"label": label, "rounds": rounds, "items": records},
                              ensure_ascii=False, indent=1), encoding="utf-8")

    # ── 콘솔 요약 ──
    print("=" * 70)
    print(f"{label}   회차 {len(rounds)}개 / 문항 {len(records)}개 "
          f"(기대 {len(rounds) * maxq}개, 인식률 {len(records) / max(len(rounds) * maxq, 1) * 100:.0f}%)")
    print("=" * 70)

    print("\n[영역별 유형 분포]")
    for an in area_names:
        sub = [r for r in records if r["area"] == an]
        if not sub: continue
        c = Counter(r["type"] for r in sub)
        top = " / ".join(f"{k} {v}({v/len(sub)*100:.0f}%)" for k, v in c.most_common(7))
        print(f"  {an}({len(sub)}) {top}")

    print("\n[전체 발문 유형 상위]")
    c = Counter(r["type"] for r in records)
    for k, v in c.most_common(12):
        print(f"  {k:<10} {v:>4}  {v/len(records)*100:>5.1f}%")

    print("\n[본문 분량(발문+자료, 자)]")
    for an in area_names:
        sub = [r["body_chars"] for r in records if r["area"] == an and r["body_chars"] > 0]
        if not sub: continue
        sub.sort()
        print(f"  {an:<8} 중앙값 {median(sub):>5.0f} 평균 {mean(sub):>5.0f} "
              f"| 하위25% {sub[len(sub)//4]:>4.0f} 상위25% {sub[len(sub)*3//4]:>5.0f} 최대 {max(sub):>5.0f}")

    print("\n[자료 구조 사용률]")
    for key, name in [("shared", "세트문항"), ("has_table", "표"), ("has_graph", "그래프"),
                      ("has_bogi", "<보기>"), ("has_jogeon", "<조건>/<정보>")]:
        for an in area_names:
            sub = [r for r in records if r["area"] == an]
            if not sub: continue
            v = sum(1 for r in sub if r[key])
            print(f"  {name:<12} {an:<8} {v:>3}/{len(sub)} ({v/len(sub)*100:>4.0f}%)")
        print()

    fn = [r["n_footnote"] for r in records]
    print(f"[각주 ※] 총 {sum(fn)}개 / 회차당 평균 {sum(fn)/max(len(rounds),1):.1f}개 "
          f"/ 각주 있는 문항 {sum(1 for x in fn if x)}개({sum(1 for x in fn if x)/len(records)*100:.0f}%)")
    print(f"\n→ 저장: {dst}")
    return records


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--label", required=True)
    ap.add_argument("--areas", required=True, help="영역별 문항 수 예: 20,20,20")
    ap.add_argument("--names", default="의사소통,수리,문제해결,자원관리,정보,기술,조직이해,직업윤리")
    a = ap.parse_args()
    areas = [int(x) for x in a.areas.split(",")]
    names = a.names.split(",")[:len(areas)]
    analyze(Path(a.dump), a.label, areas, names)
