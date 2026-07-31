# -*- coding: utf-8 -*-
"""필기후기 본문 → 기관별 출제유형 DB 적재.

    python reviews/ingest.py --clip --org 건보          # 클립보드에서
    python reviews/ingest.py 후기.txt --org 건보         # 파일에서
    python reviews/ingest.py --clip --org 건보 --dry     # 저장하지 않고 결과만 확인

원문은 reviews/raw/<기관>/ 에만 남기고 커밋하지 않는다. db.json 에는 분류 결과만 담는다.
자세한 원칙은 같은 폴더의 README.md 참고.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# stdout 을 새 TextIOWrapper 로 갈아끼우면 안 된다. 이 모듈을 import 하는 쪽에서 이미
# 감싸 두었을 경우 중간 래퍼가 GC 되면서 버퍼가 닫힌다(serve.py 에서 실제로 터졌다).
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
DB = HERE / "db.json"

sys.path.insert(0, str(HERE))
from lexicon import (AREAS, TYPES, DIFFICULTY, TIME_PRESSURE, TOPICS,  # noqa: E402
                     STOPWORDS, ORG_ALIASES)

DATE_PAT = [
    (re.compile(r"(20\d{2})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})"), 3),
    (re.compile(r"(20\d{2})[.\-/년]\s*(\d{1,2})\s*월"), 2),
]
# 후기는 「60문항」 「60문제」 「60문제까지」를 섞어 쓴다.
NQ_PAT = re.compile(r"(\d{2,3})\s*문(?:항|제)")
MIN_PAT = re.compile(r"(\d{2,3})\s*분")
TRACK_PAT = re.compile(r"([가-힣]{0,6}(?:행정|기술|전산|건강|요양|사무|일반|토목|건축|전기)직?"
                       r"(?:\([^)]{1,10}\))?)")

# 공준모 후기는 정형 양식으로 시작한다. 자유서술보다 이쪽이 훨씬 정확하다.
#     ▷ 기관명 : 국민건강보험공단
#     ▷ 직렬명 : 요양직
#     ▷ 시험시간 : 60분/ 30분
#     ▷ 난이도 : 중상
FORM_PAT = re.compile(r"^\s*[▷▶>·\-]?\s*([가-힣]{2,6})\s*[:：]\s*(.+?)\s*$", re.M)
FORM_KEYS = {
    "기관명": "org_raw", "기관": "org_raw",
    "직렬명": "track", "직렬": "track", "직군": "track",
    "시험시간": "time_raw", "시험과목": "subject_raw",
    "난이도": "diff_raw", "결시율": "absent_raw", "고사장": None,
}

# 후기 글에 흔히 붙는 머리말·꼬리말. 본문 분류에 잡음이 된다.
BOILERPLATE = re.compile(
    r"(다들 고생|화이팅|파이팅|도움이 되었으면|긴 글 읽어|스크랩|댓글|좋아요|"
    r"광고|문의는 쪽지|카페 규정|"
    # 공준모 후기 양식의 안내 문구. 본문에 그대로 남아 분류를 흐린다.
    # "지원 기관 정보를 공유해주세요" 때문에 전건이 정보능력으로 잡혔었다.
    r"공유해주세요|공유해 주세요|후기를 남겨|남겨 주세요|※\s*예시|네이버 카페)")

# 사전 후보에서 걸러낼 용언 활용형. 형태소 분석 없이 어미만 보고 자른다.
VERB_TAIL = re.compile(
    r"(습니다|했어요|였어요|어요|아요|네요|겠다|였다|았다|었다|한다|된다|"
    r"나왔|있었|없었|같았|봤|였|하고|되고|이고|라서|해서|지만|는데|더라|"
    r"입니다|이었|하는|되는|같은|많은|적은)$")


def norm(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def find_date(text: str) -> str | None:
    for pat, n in DATE_PAT:
        m = pat.search(text)
        if m:
            g = [int(x) for x in m.groups()]
            return f"{g[0]:04d}-{g[1]:02d}-" + (f"{g[2]:02d}" if n == 3 else "01")
    return None


# "모듈 문제는 거의 없었고" 처럼 부정된 언급을 출제 사실로 세면 안 된다.
NEGATION = re.compile(r"(없었|없고|없음|안 나왔|나오지 않|아니었|적었|거의 없)")
NEG_SPAN = 30          # 매칭 지점 뒤 이 범위 안의 부정만 본다


def _negated(text: str, pos: int, word: str) -> bool:
    return bool(NEGATION.search(text[pos + len(word): pos + len(word) + NEG_SPAN]))


def match_lexicon(text: str, table: dict) -> list[str]:
    """사전에 걸리는 항목을 등장 순서대로 중복 없이 돌려준다. 부정된 언급은 뺀다."""
    hits = []
    for label, words in table.items():
        for w in words:
            pos = text.find(w)
            while pos >= 0 and _negated(text, pos, w):
                pos = text.find(w, pos + 1)
            if pos >= 0:
                hits.append((pos, label))
                break
    return [label for _, label in sorted(hits)]


def pick_one(text: str, table: dict) -> str | None:
    """등장 순서가 아니라 **사전에 적힌 순서**로 고른다.

    난이도·시간압박 사전은 강한 것부터 나열돼 있다. '시간이 부족'과 '시간이 매우 부족'이
    함께 나오면 강한 쪽을 택해야 후기의 취지에 맞는다.
    """
    got = set(match_lexicon(text, table))
    return next((k for k in table if k in got), None)


def find_topics(text: str, org: str) -> list[str]:
    table = {**TOPICS.get("_공통", {}), **TOPICS.get(org, {})}
    return match_lexicon(text, table)


def unmatched_candidates(text: str, org: str, limit: int = 12) -> list[tuple[str, int]]:
    """사전에 없지만 자주 나오는 명사형 어절 — 사전을 키우는 단서로 쓴다."""
    tables = (TYPES, DIFFICULTY, TIME_PRESSURE, AREAS,
              TOPICS.get("_공통", {}), TOPICS.get(org, {}))
    known = {w for t in tables for ws in t.values() for w in ws} | STOPWORDS

    words = re.findall(r"[가-힣]{2,10}", text)
    cnt = Counter(w for w in words
                  if len(w) >= 3 and not VERB_TAIL.search(w)
                  and w not in known and not any(k in w for k in known))
    return cnt.most_common(limit)


def normalize_org(name: str | None) -> str | None:
    """표기가 흔들리는 기관명을 정식명으로 접는다. 「건보」→「국민건강보험공단」."""
    if not name:
        return None
    s = name.strip()
    for official, aliases in ORG_ALIASES.items():
        if any(a in s for a in aliases):
            return official
    return s          # 사전에 없으면 적힌 그대로 둔다


# 양식 칸의 난이도는 「중상」 「중~중상」 「상」처럼 등급만 적혀 온다.
# 자유서술용 사전으로는 잡히지 않으므로 등급 토큰을 직접 읽는다.
# 긴 것부터 봐야 「중상」이 「중」+「상」으로 쪼개지지 않는다.
DIFF_TOKENS = ["중상", "중하", "상", "하", "중"]
DIFF_RANK = ["상", "중상", "중", "중하", "하"]


def normalize_difficulty(raw: str | None) -> str | None:
    """양식 칸의 난이도 표기를 등급 하나로 접는다. 범위로 적혔으면 강한 쪽을 택한다."""
    if not raw:
        return None
    s = raw.strip()
    found = set()
    for t in DIFF_TOKENS:
        while t in s:
            found.add(t)
            s = s.replace(t, "·", 1)
    return next((g for g in DIFF_RANK if g in found), None)


def parse_form(text: str) -> dict:
    """후기 머리의 정형 양식을 읽는다. 자유서술 추론보다 우선한다."""
    out = {}
    for key, val in FORM_PAT.findall(text):
        field = FORM_KEYS.get(key)
        if field and val and val not in {"-", "없음", "?"}:
            out.setdefault(field, val)
    return out


# ── 출제 키워드 절 ───────────────────────────────────────────────
# 이 절이 후기에서 가장 값어치 있다. 응시자가 영역별로 실제 출제 소재를 직접 적어 준다.
#
#     ✍기억 나는 문항 혹은 출제 키워드를 남겨 주세요 :)
#     <의사소통>
#     - 반려견 놀이공원
#     - 루게릭병
#     <수리>
#     - 무역수지
#
# 사전으로 추측할 필요가 없다. 적힌 그대로 읽는다.
KW_SECTION = re.compile(r"(기억\s*나는\s*문항|출제\s*키워드|기억나는\s*키워드)")
KW_HEADER = re.compile(r"^\s*[<〈\[【]\s*([^>〉\]】]{1,20})\s*[>〉\]】]\s*$", re.M)
KW_ITEM = re.compile(r"^\s*(?:[-–—•*]|\d{1,2}[.)])\s*(.+?)\s*$")

# 영역 표기를 정식 이름으로 접는다. 「문해」 「의통」이 그대로 쓰인다.
KW_AREA_ALIAS = {
    "의사소통": "의사소통", "의통": "의사소통", "의사소통능력": "의사소통",
    "수리": "수리", "수리능력": "수리",
    "문해": "문제해결", "문제해결": "문제해결", "문제해결능력": "문제해결",
    "자원관리": "자원관리", "정보": "정보", "기술": "기술",
    "조직이해": "조직이해", "직업윤리": "직업윤리",
}


def parse_keywords(text: str) -> dict[str, list[str]]:
    """출제 키워드 절을 영역별로 뽑는다. 직무시험(법) 절도 그대로 담는다."""
    m = KW_SECTION.search(text)
    if not m:
        return {}
    tail = text[m.end():]

    out: dict[str, list[str]] = {}
    cur = None
    for line in tail.split("\n"):
        h = KW_HEADER.match(line)
        if h:
            raw = h.group(1).strip()
            cur = KW_AREA_ALIAS.get(raw, raw)          # 법 과목명은 적힌 그대로 둔다
            out.setdefault(cur, [])
            continue
        if cur is None:
            continue
        it = KW_ITEM.match(line)
        if it:
            v = it.group(1).strip(" :·-")
            if 1 < len(v) <= 60:
                out[cur].append(v)
        elif line.strip() and not line.strip().startswith(("저는", "그래도", "이제", "이번")):
            continue
    return {k: v for k, v in out.items() if v}


TITLE_TERM = re.compile(r"(20\d{2})\s*(상반기|하반기)?")

# 「유형이 바뀌었다」는 언급. 구조 지표를 대체하진 못하지만,
# 코퍼스(시판본 실측)가 낡았다는 경보로는 이만한 게 없다.
CHANGE_SIGNAL = re.compile(
    r"(유형이?\s*(많이\s*|완전\s*)?(달라|바뀌)|기존.{0,12}(다르|달라)|처음\s*보는|"
    r"난생\s*처음|대행사가?\s*(달라|바뀌)|작년.{0,12}(다르|달라))")


def form_signature(form: dict) -> str | None:
    """양식 값만으로 만든 글 식별자. 같은 글을 범위 달리 긁었을 때 겹치는지 본다."""
    keys = ("org_raw", "track", "time_raw", "absent_raw")
    vals = [re.sub(r"\s+", "", form.get(k, "")) for k in keys]
    if sum(1 for v in vals if v) < 3:          # 양식이 부실하면 판정하지 않는다
        return None
    return hashlib.sha1("|".join(vals).encode("utf-8")).hexdigest()[:12]


def parse(text: str, org: str) -> dict:
    text = norm(text)
    # 키워드 절은 원문 그대로 읽어야 한다. BOILERPLATE 로 줄을 지우기 전에 뽑는다.
    keywords = parse_keywords(text)
    body = "\n".join(ln for ln in text.split("\n") if not BOILERPLATE.search(ln))
    form = parse_form(body)

    # 제목(첫 줄)에 연도·상하반기가 들어 있는 경우가 많다. 시행 시기 판정에 쓴다.
    head = text.split("\n", 1)[0]
    tm = TITLE_TERM.search(head)
    term = f"{tm.group(1)} {tm.group(2)}" if tm and tm.group(2) else (tm.group(1) if tm else None)

    # 시험시간은 「60+20」 「60분/ 30분」처럼 NCS와 직무시험이 붙어 나온다. 앞이 NCS다.
    time_raw = form.get("time_raw", "")
    tmins = [int(x) for x in re.findall(r"\d{2,3}", time_raw)]
    mins = [int(x) for x in MIN_PAT.findall(body)]
    nq = [int(x) for x in NQ_PAT.findall(body)]
    track = TRACK_PAT.search(form.get("track") or body)

    return {
        # 양식의 기관명을 우선한다. 수집기에 넘긴 --org 는 폴백일 뿐이다.
        "org": normalize_org(form.get("org_raw")) or normalize_org(org),
        "title": head[:80] or None,
        "term": term,                       # 「2026 상반기」 — 시행 시기
        "date": find_date(body),
        "track": (track.group(1) if track else None) or form.get("track"),
        "total_q": max(nq) if nq else None,
        "total_min": tmins[0] if tmins else (max(mins) if mins else None),
        "subject": form.get("subject_raw"),
        "areas": match_lexicon(body, AREAS),
        "types": match_lexicon(body, TYPES),
        "topics": find_topics(body, normalize_org(form.get("org_raw")) or org),
        # 응시자가 직접 적어 준 영역별 출제 소재. 사전 추측보다 이쪽이 정확하다.
        "keywords": keywords,
        # 양식에 적힌 난이도가 자유서술 추론보다 정확하다.
        "difficulty": normalize_difficulty(form.get("diff_raw")) or pick_one(body, DIFFICULTY),
        "time_pressure": pick_one(body, TIME_PRESSURE),
        # 「기존과 다르다」는 언급 여부. 코퍼스가 낡았는지 판단하는 단서다.
        "change_signal": bool(CHANGE_SIGNAL.search(body)),
        "chars": len(body),
        # 원문은 담지 않는다. 같은 글을 두 번 넣지 않으려는 지문만 남긴다.
        "fingerprint": hashlib.sha1(body.encode("utf-8")).hexdigest()[:12],
        # 같은 글을 범위를 달리 긁으면 본문 해시가 갈린다. 양식 값은 그대로이므로
        # 이걸로 근접 중복을 잡는다. 양식이 없는 후기는 None 이라 판정에서 빠진다.
        "form_sig": form_signature(form),
        "ingested_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def load_db() -> list[dict]:
    if not DB.exists():
        return []
    return json.loads(DB.read_text(encoding="utf-8"))


def save_db(rows: list[dict]):
    DB.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_clipboard() -> str:
    try:
        import subprocess
        r = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                           capture_output=True, text=True, encoding="utf-8", timeout=20)
        return r.stdout
    except Exception as e:                                   # noqa: BLE001
        raise SystemExit(f"[중단] 클립보드를 읽지 못했습니다: {e}")


def rebuild() -> int:
    """raw/ 의 원문을 전부 다시 파싱해 db.json 을 새로 만든다.

    사전을 키우거나 파서를 고친 뒤에 돌린다. 기관명 표기를 바꾸는 것도 이걸로 해결된다 —
    원문을 남겨 두는 이유가 이것이다.
    """
    files = sorted(RAW.rglob("*.txt"))
    if not files:
        raise SystemExit(f"[중단] {RAW} 에 원문이 없습니다.")

    parsed = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        parsed.append((f, text, parse(text, f.parent.name)))

    # 같은 글을 범위 달리 긁은 것이 섞일 수 있다. 양식 값이 같으면 **정보가 많은 쪽**을 남긴다.
    best: dict[str, tuple] = {}
    dropped = []
    for item in parsed:
        rec = item[2]
        key = rec.get("form_sig") or rec["fingerprint"]
        score = (len(rec.get("keywords") or {}), rec["chars"])
        if key in best:
            prev = best[key][2]
            if score > (len(prev.get("keywords") or {}), prev["chars"]):
                dropped.append(best[key]); best[key] = item
            else:
                dropped.append(item)
        else:
            best[key] = item

    for f, _, _ in dropped:                      # 정보가 적은 중복 원문은 치운다
        f.unlink()

    rows, moved = [], 0
    for f, _, rec in best.values():
        rows.append(rec)
        want = RAW / rec["org"]                  # 폴더 이름도 정식 기관명으로 맞춘다
        if f.parent != want or not f.name.startswith(str(rec["date"] or "날짜미상")):
            want.mkdir(parents=True, exist_ok=True)
            f.replace(want / f"{rec['date'] or '날짜미상'}_{rec['fingerprint']}.txt")
            moved += 1

    for d in RAW.iterdir():                      # 비게 된 옛 폴더 정리
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()

    rows.sort(key=lambda r: r.get("date") or "", reverse=True)
    save_db(rows)
    org_cnt = Counter(r["org"] for r in rows)
    print(f"[재생성] {len(files)}개 원문 → {len(rows)}건 "
          + (f"· 근접 중복 {len(dropped)}건 정리 " if dropped else "")
          + (f"· 원문 {moved}개 정리" if moved else ""))
    for o, n in org_cnt.most_common():
        print(f"   {o}  {n}건")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="후기 본문 텍스트 파일")
    ap.add_argument("--clip", action="store_true", help="클립보드에서 읽는다")
    ap.add_argument("--org", help="기관명. 후기 양식에 기관명이 있으면 그쪽이 우선한다")
    ap.add_argument("--dry", action="store_true", help="저장하지 않고 결과만 본다")
    ap.add_argument("--rebuild", action="store_true",
                    help="raw/ 원문을 전부 다시 파싱해 db.json 을 새로 만든다")
    args = ap.parse_args()

    if args.rebuild:
        return rebuild()
    if not args.org:
        raise SystemExit("[중단] --org 를 주십시오 (--rebuild 제외).")

    if args.clip:
        text = read_clipboard()
    elif args.path:
        text = Path(args.path).read_text(encoding="utf-8")
    else:
        raise SystemExit("[중단] 파일 경로를 주거나 --clip 을 쓰십시오.")

    if len(norm(text)) < 120:
        raise SystemExit("[중단] 본문이 너무 짧습니다. 글 전체를 복사했는지 확인하십시오.")

    rec = parse(text, args.org)
    db = load_db()
    if any(r["fingerprint"] == rec["fingerprint"] for r in db):
        print(f"[건너뜀] 이미 등록된 글입니다 (fingerprint {rec['fingerprint']})")
        return 0

    print(f"[기관] {rec['org']}   [시행일] {rec['date'] or '미상'}   "
          f"[직렬] {rec['track'] or '미상'}")
    print(f"[구성] {rec['total_q'] or '?'}문항 / {rec['total_min'] or '?'}분   "
          f"영역 {', '.join(rec['areas']) or '미상'}")
    print(f"[유형] {', '.join(rec['types']) or '없음'}")
    print(f"[소재] {', '.join(rec['topics']) or '없음'}")
    print(f"[체감] 난이도 {rec['difficulty'] or '미상'} · 시간 {rec['time_pressure'] or '미상'}")
    if rec["keywords"]:
        print("[출제 키워드] 응시자가 직접 적은 것 — 소재 선정에 그대로 쓴다")
        for area, ws in rec["keywords"].items():
            print(f"   {area:<10} {' · '.join(ws)}")

    cands = unmatched_candidates(text, args.org)
    if cands:
        print("\n[사전 미등록 후보] lexicon.py 에 추가할 만한 것이 있는지 보십시오.")
        print("   " + "  ".join(f"{w}({n})" for w, n in cands))

    if args.dry:
        print("\n[건너뜀] --dry 이므로 저장하지 않았습니다.")
        return 0

    # 원문은 로컬에만 남긴다 (.gitignore 로 차단)
    d = RAW / args.org
    d.mkdir(parents=True, exist_ok=True)
    stamp = rec["date"] or datetime.now().strftime("%Y-%m-%d")
    (d / f"{stamp}_{rec['fingerprint']}.txt").write_text(norm(text), encoding="utf-8")

    db.append(rec)
    save_db(db)
    print(f"\n[저장] db.json 총 {len(db)}건 "
          f"({sum(1 for r in db if r['org'] == args.org)}건이 {args.org})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
