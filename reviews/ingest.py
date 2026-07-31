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

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
DB = HERE / "db.json"

sys.path.insert(0, str(HERE))
from lexicon import AREAS, TYPES, DIFFICULTY, TIME_PRESSURE, TOPICS, STOPWORDS  # noqa: E402

DATE_PAT = [
    (re.compile(r"(20\d{2})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})"), 3),
    (re.compile(r"(20\d{2})[.\-/년]\s*(\d{1,2})\s*월"), 2),
]
NQ_PAT = re.compile(r"(\d{2,3})\s*문항")
MIN_PAT = re.compile(r"(\d{2,3})\s*분")
TRACK_PAT = re.compile(r"(행정직|기술직|전산직|건강직|요양직|사무직|일반직|토목|건축|전기)")

# 후기 글에 흔히 붙는 머리말·꼬리말. 본문 분류에 잡음이 된다.
BOILERPLATE = re.compile(
    r"(다들 고생|화이팅|파이팅|도움이 되었으면|긴 글 읽어|스크랩|댓글|좋아요|"
    r"광고|문의는 쪽지|카페 규정)")

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


def parse(text: str, org: str) -> dict:
    text = norm(text)
    body = "\n".join(ln for ln in text.split("\n") if not BOILERPLATE.search(ln))

    nq = [int(x) for x in NQ_PAT.findall(body)]
    mins = [int(x) for x in MIN_PAT.findall(body)]
    track = TRACK_PAT.search(body)

    return {
        "org": org,
        "date": find_date(body),
        "track": track.group(1) if track else None,
        "total_q": max(nq) if nq else None,
        "total_min": max(mins) if mins else None,
        "areas": match_lexicon(body, AREAS),
        "types": match_lexicon(body, TYPES),
        "topics": find_topics(body, org),
        "difficulty": pick_one(body, DIFFICULTY),
        "time_pressure": pick_one(body, TIME_PRESSURE),
        "chars": len(body),
        # 원문은 담지 않는다. 같은 글을 두 번 넣지 않으려는 지문만 남긴다.
        "fingerprint": hashlib.sha1(body.encode("utf-8")).hexdigest()[:12],
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="후기 본문 텍스트 파일")
    ap.add_argument("--clip", action="store_true", help="클립보드에서 읽는다")
    ap.add_argument("--org", required=True, help="기관 약칭 (예: 건보, 한전)")
    ap.add_argument("--dry", action="store_true", help="저장하지 않고 결과만 본다")
    args = ap.parse_args()

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
