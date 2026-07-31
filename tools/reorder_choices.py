# -*- coding: utf-8 -*-
"""선지 순서를 바꿔 정답 위치를 옮긴다. 정답 분포를 맞출 때 쓴다.

    python tools/reorder_choices.py --round r4_korail 01=1 05=5 22=5 ...

`문항번호=목표위치` 를 나열하면 그 문항의 정답 선지를 목표 위치로 옮기고,
나머지 선지의 상대 순서는 그대로 둔다. `answer` 값과 `each` 목록의 순서·
동그라미 번호도 함께 고쳐 준다.

**손으로 하면 반드시 어긋난다.** 선지·`each`·`answer` 세 곳을 동시에 맞춰야 하고,
`each` 는 동그라미 번호까지 다시 매겨야 한다. 그래서 도구로 만들었다.

`explain` 본문이 선지 번호를 가리키는 경우(「③이다」 같은)는 **자동으로 고치지 않는다.**
문맥을 봐야 하므로, 옮긴 문항의 `explain` 에 남은 번호 참조를 목록으로 보고한다.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CIRCLED = "①②③④⑤"


def spans(raw: bytes, node: ast.List) -> list[tuple[int, int]]:
    """리스트 원소별 소스 구간. 여러 줄 암시적 연결도 통째로 잡는다.

    **`ast` 의 `col_offset` 은 문자 수가 아니라 UTF-8 바이트 수다.**
    한글이 섞인 소스에서 문자 단위로 계산하면 시작 위치가 어긋나 파일이 깨진다.
    그래서 바이트로 자르고 마지막에 디코딩한다.
    """
    offs, acc = [], 0
    for ln in raw.splitlines(keepends=True):
        offs.append(acc)
        acc += len(ln)
    return [(offs[e.lineno - 1] + e.col_offset,
             offs[e.end_lineno - 1] + e.end_col_offset) for e in node.elts]


def move(items: list[str], frm: int, to: int) -> list[str]:
    """frm 위치 원소를 to 위치로 옮긴다(둘 다 0-기반). 나머지 순서는 유지."""
    rest = items[:frm] + items[frm + 1:]
    return rest[:to] + [items[frm]] + rest[to:]


def renumber_each(texts: list[str]) -> list[str]:
    """each 원소 앞머리의 동그라미 번호를 자리에 맞게 다시 매긴다."""
    out = []
    for i, t in enumerate(texts):
        out.append(re.sub(r"[①②③④⑤]", CIRCLED[i], t, count=1))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", required=True, metavar="이름")
    ap.add_argument("moves", nargs="+", metavar="번호=위치",
                    help="예) 01=1 05=5 — 정답을 그 위치(1~5)로 옮긴다")
    args = ap.parse_args()

    want = {}
    for m in args.moves:
        no, pos = m.split("=")
        want[int(no)] = int(pos)
    if any(not 1 <= p <= 5 for p in want.values()):
        raise SystemExit("[중단] 목표 위치는 1~5 다")

    sys.path.insert(0, str(ROOT))
    import build
    build.select_round(args.round)

    # 문항 번호는 적재 순서대로 붙는다. 파일별 시작 번호를 미리 센다.
    no = 1
    done, notes = [], []
    for mod_name, area, _ in build.CFG.AREAS:
        path = build.CONTENT / f"{mod_name}.py"
        if not path.exists():
            continue
        raw = path.read_bytes()
        tree = ast.parse(raw.decode("utf-8"))
        # BLOCKS = [ ... ] 안의 문항 dict 를 순서대로 훑는다
        edits = []                                  # (구간, 새 텍스트)
        assign = next(n for n in tree.body
                      if isinstance(n, ast.Assign)
                      and getattr(n.targets[0], "id", "") == "BLOCKS")
        for blk in assign.value.elts:
            qs = next(v for k, v in zip(blk.keys, blk.values)
                      if getattr(k, "value", "") == "questions")
            for q in qs.elts:
                keys = {getattr(k, "value", ""): v for k, v in zip(q.keys, q.values)}
                cur_no = no
                no += 1
                if cur_no not in want:
                    continue
                ch, ea, an = keys.get("choices"), keys.get("each"), keys.get("answer")
                if ch is None or an is None:
                    notes.append(f"{cur_no:02d}번: choices/answer 를 찾지 못했다")
                    continue
                frm = ast.literal_eval(an) - 1
                to = want[cur_no] - 1
                if frm == to:
                    notes.append(f"{cur_no:02d}번: 이미 {want[cur_no]}번 자리다")
                    continue
                cs = spans(raw, ch)
                texts = [raw[a:b].decode("utf-8") for a, b in cs]
                new = move(texts, frm, to)
                edits.append(((cs[0][0], cs[-1][1]), ", ".join(new)))
                if ea is not None and len(ea.elts) == len(ch.elts):
                    es = spans(raw, ea)
                    et = [raw[a:b].decode("utf-8") for a, b in es]
                    edits.append(((es[0][0], es[-1][1]),
                                  ", ".join(renumber_each(move(et, frm, to)))))
                elif ea is not None:
                    notes.append(f"{cur_no:02d}번: each 개수가 선지와 달라 건드리지 않았다")
                asp = spans(raw, ast.List(elts=[an]))[0]
                edits.append((asp, str(to + 1)))
                done.append((cur_no, frm + 1, to + 1))
        if not edits:
            continue
        # 구간이 겹치면 파일이 깨진다. 적용 전에 반드시 확인한다.
        ordered = sorted(edits, key=lambda x: x[0][0])
        for (a1, b1), (a2, _) in zip(ordered, ordered[1:]):
            if b1 > a2:
                raise SystemExit(f"[중단] 수정 구간이 겹친다: {b1} > {a2}")
        for (a, b), text in reversed(ordered):
            raw = raw[:a] + text.encode("utf-8") + raw[b:]
        path.write_bytes(raw)
        print(f"[수정] {path.relative_to(ROOT)}")

    for cur_no, frm, to in sorted(done):
        print(f"   {cur_no:02d}번  {CIRCLED[frm-1]} → {CIRCLED[to-1]}")
    for n in notes:
        print(f"   [안내] {n}")

    # explain 이 선지 번호를 가리키는 곳을 알려 준다 — 자동으로 고치지 않는다
    print("\n[확인 필요] 옮긴 문항의 explain 에 남은 선지 번호 참조")
    build.select_round(args.round)
    blocks, _, _ = build.load_blocks(preview=True)
    hit = 0
    for b in blocks:
        for q in b["questions"]:
            if q["no"] not in want:
                continue
            for m in re.finditer(r"[①②③④⑤]", q.get("explain") or ""):
                s = q["explain"]
                lo, hi = max(0, m.start() - 28), min(len(s), m.end() + 28)
                print(f"   {q['no']:02d}번  …{re.sub(r'<[^>]+>', '', s[lo:hi])}…")
                hit += 1
    if not hit:
        print("   없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
