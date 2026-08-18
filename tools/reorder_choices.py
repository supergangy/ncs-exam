# -*- coding: utf-8 -*-
"""선지 순서를 바꿔 정답 위치를 옮긴다. 정답 분포를 맞출 때 쓴다.

    python tools/reorder_choices.py --round r4_korail 01=1 05=5 22=5 ...
    python tools/reorder_choices.py --bank ncs-math-common-003=5 ...

회차(`--round`)는 **문항 번호**로, 은행(`--bank`)은 **문항 id** 로 가리킨다.
은행 문항은 `bank/**/*.py` 의 `ITEMS` 에 있고 한 item 에 문항이 하나뿐이라
id 만으로 특정된다.

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
import contextlib
import importlib
import io
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


def edit_file(path, list_name, key_of, want, done, notes) -> bool:
    """한 파일 안의 문항을 옮긴다. 회차(BLOCKS)와 은행(ITEMS)이 같은 구조라
    리스트 이름과 「문항을 무엇으로 가리키나」만 달리 받는다.

    key_of(item_node, q_index) 가 None 이면 그 문항은 건드리지 않는다.
    """
    raw = path.read_bytes()
    tree = ast.parse(raw.decode("utf-8"))
    assign = next((n for n in tree.body
                   if isinstance(n, ast.Assign)
                   and getattr(n.targets[0], "id", "") == list_name), None)
    if assign is None:
        return False

    edits = []                                  # (구간, 새 텍스트)
    if not isinstance(assign.value, ast.List):
        return False
    for blk in assign.value.elts:
        # 헬퍼 함수로 만든 항목(`item(...)`)은 소스에서 선지를 집어낼 수 없다.
        # 리터럴 dict 만 다룬다.
        if not isinstance(blk, ast.Dict):
            continue
        qs = next((v for k, v in zip(blk.keys, blk.values)
                   if getattr(k, "value", "") == "questions"), None)
        if qs is None or not isinstance(qs, ast.List):
            continue
        for qi, q in enumerate(qs.elts):
            if not isinstance(q, ast.Dict):
                continue
            key = key_of(blk, qi)
            if key is None or key not in want:
                continue
            keys = {getattr(k, "value", ""): v for k, v in zip(q.keys, q.values)}
            ch, ea, an = keys.get("choices"), keys.get("each"), keys.get("answer")
            if ch is None or an is None:
                notes.append(f"{key}: choices/answer 를 찾지 못했다")
                continue
            frm = ast.literal_eval(an) - 1
            to = want[key] - 1
            if frm == to:
                notes.append(f"{key}: 이미 {want[key]}번 자리다")
                continue
            cs = spans(raw, ch)
            texts = [raw[a:b].decode("utf-8") for a, b in cs]
            edits.append(((cs[0][0], cs[-1][1]), ", ".join(move(texts, frm, to))))
            if ea is not None and len(ea.elts) == len(ch.elts):
                es = spans(raw, ea)
                et = [raw[a:b].decode("utf-8") for a, b in es]
                edits.append(((es[0][0], es[-1][1]),
                              ", ".join(renumber_each(move(et, frm, to)))))
            elif ea is not None:
                notes.append(f"{key}: each 개수가 선지와 달라 건드리지 않았다")
            edits.append((spans(raw, ast.List(elts=[an]))[0], str(to + 1)))
            done.append((key, frm + 1, to + 1))

    if not edits:
        return False
    # 구간이 겹치면 파일이 깨진다. 적용 전에 반드시 확인한다.
    ordered = sorted(edits, key=lambda x: x[0][0])
    for (prev, _pt), (nxt, _nt) in zip(ordered, ordered[1:]):
        if prev[1] > nxt[0]:
            raise SystemExit(f"[중단] 수정 구간이 겹친다: {prev} / {nxt}")
    for (a, b), text in reversed(ordered):
        raw = raw[:a] + text.encode("utf-8") + raw[b:]
    path.write_bytes(raw)
    print(f"[수정] {path.relative_to(ROOT)}")
    return True


# ── 수치 선지 오름차순 정렬 ──────────────────────────────────────────
#
# 규칙 4-13 은 「수 + 같은 꼬리말」 선지가 오름차순이기를 요구한다.
# 정답 위치를 옮기다 보면 이 순서가 깨진다. 여기서는 **선지 전체를 값 순으로
# 다시 늘어놓고** answer·each·검증기 배치람다를 따라 맞춘다.
_NUM = re.compile(r"^\s*(-?[\d,]+(?:\.\d+)?)\s*([^\d]*)$")


def choice_values(choices: list[str]) -> list[float] | None:
    """값을 견줄 수 있는 선지면 수 목록을, 아니면 None. 비트 패턴은 뺀다."""
    plains = [re.sub(r"<[^>]+>", "", c).strip() for c in choices]
    if all(re.fullmatch(r"[01]{3,}", t) for t in plains):
        return None
    vals, tails = [], set()
    for t in plains:
        m = _NUM.match(t)
        if not m:
            return None
        vals.append(float(m.group(1).replace(",", "")))
        tails.add(m.group(2).strip())
    return vals if len(tails) <= 1 else None


def apply_perm(texts: list[str], perm: list[int]) -> list[str]:
    """perm[i] = 새 i 번째 자리에 올 원래 인덱스."""
    return [texts[j] for j in perm]


# ── 검증기 매핑 동반 갱신 ────────────────────────────────────────────
#
# `tools/verify_*.py` 의 REGISTRY 는 (계산함수, 배치람다) 짝이다.
# 배치람다가 **선지 번호를 알고 있다** — 값→번호 dict 이거나 `lambda i: i` 다.
# 그래서 선지를 옮기면 검증이 깨진다. 문항만 고치고 끝내면 안 된다.
VERIFIERS = ("tools/verify_ncs.py", "tools/verify_cs.py")


def newpos(p: int, frm: int, to: int) -> int:
    """선지를 frm→to 로 옮겼을 때 원래 p 자리에 있던 선지의 새 자리(1-기반)."""
    if p == frm:
        return to
    if frm < p <= to:
        return p - 1
    if to <= p < frm:
        return p + 1
    return p


def registry_kind(lam: ast.Lambda) -> str:
    b = lam.body
    if isinstance(b, ast.Subscript) and isinstance(b.value, ast.Dict):
        return "dict"
    if isinstance(b, ast.Name):
        return "identity"
    return "other"


def sync_verifiers(moved: dict) -> list[str]:
    """옮긴 문항(id → (frm, to))에 맞춰 REGISTRY 배치람다를 고친다.

    돌려주는 것은 **검증기에 있는데도 손대지 못한 id** 다.
    아예 등록되지 않은 문항은 고칠 것이 없으므로 여기 들지 않는다.
    """
    left = dict(moved)
    registered = set()
    for f in VERIFIERS:
        path = ROOT / f
        raw = path.read_bytes()
        tree = ast.parse(raw.decode("utf-8"))
        reg = next((n for n in tree.body
                    if isinstance(n, ast.Assign)
                    and getattr(n.targets[0], "id", "") == "REGISTRY"), None)
        if reg is None:
            continue
        edits = []
        for k, v in zip(reg.value.keys, reg.value.values):
            iid = ast.literal_eval(k)
            registered.add(iid)
            if iid not in left:
                continue
            if not (isinstance(v, ast.Tuple) and len(v.elts) == 2
                    and isinstance(v.elts[1], ast.Lambda)):
                continue
            lam = v.elts[1]
            spec = left[iid]
            kind = registry_kind(lam)
            # (frm, to) 는 한 개 옮기기, perm 은 전체 재배열이다.
            if isinstance(spec, list):
                place = {old + 1: new + 1 for new, old in enumerate(spec)}
            else:
                frm, to = spec
                place = {p: newpos(p, frm, to) for p in range(1, 6)}
            span = spans(raw, ast.List(elts=[lam]))[0]
            arg = lam.args.args[0].arg
            if kind == "dict":
                d = lam.body.value
                pairs = []
                for dk, dv in zip(d.keys, d.values):
                    val = raw[spans(raw, ast.List(elts=[dk]))[0][0]:
                              spans(raw, ast.List(elts=[dk]))[0][1]].decode("utf-8")
                    pairs.append(f"{val}: {place[ast.literal_eval(dv)]}")
                idx = raw[spans(raw, ast.List(elts=[lam.body.slice]))[0][0]:
                          spans(raw, ast.List(elts=[lam.body.slice]))[0][1]].decode("utf-8")
                edits.append((span, f"lambda {arg}: {{{', '.join(pairs)}}}[{idx}]"))
            elif kind == "identity":
                m = ", ".join(f"{p}: {place[p]}" for p in range(1, 6))
                edits.append((span, f"lambda {arg}: {{{m}}}[{arg}]"))
            else:
                continue                     # 손댈 수 없는 모양 — 호출자에게 남긴다
            del left[iid]
        if not edits:
            continue
        ordered = sorted(edits, key=lambda x: x[0][0])
        for (a, b), text in reversed(ordered):
            raw = raw[:a] + text.encode("utf-8") + raw[b:]
        path.write_bytes(raw)
        print(f"[수정] {path.relative_to(ROOT)}  배치람다 {len(edits)}건")
    return sorted(i for i in left if i in registered)


def _helper_fields(tree, call):
    """헬퍼 호출(`_q(...)`)의 인자를 **파라미터 이름**에 맞춰 돌려준다.

    NCS 공통 문항은 `_q(no, typ, stem, choices, answer, ...)` 로 만든다.
    파일마다 시그니처가 조금씩 달라서(ncs_rule 은 subject·area 가 더 있다)
    자리 번호를 박아 두면 엉뚱한 인자를 집는다. 그래서 정의를 읽어 맞춘다.
    """
    fname = getattr(call.func, "id", None)
    if fname is None:
        return {}
    fndef = next((n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == fname), None)
    if fndef is None:
        return {}
    names = [a.arg for a in fndef.args.args]
    out = {}
    for i, a in enumerate(call.args):
        if i < len(names):
            out[names[i]] = a
    for kw in call.keywords:
        if kw.arg:
            out[kw.arg] = kw.value
    return out


def _question_nodes(tree, node):
    """은행 item 하나에서 choices·each·answer 노드를 집어낸다.

    두 형태가 섞여 있다 —
      · 전산직(major_cs_*) 은 dict 리터럴
      · NCS 공통은 `_q(...)` 헬퍼 호출
    """
    if isinstance(node, ast.Call):
        f = _helper_fields(tree, node)
        return f.get("choices"), f.get("each"), f.get("answer")
    if isinstance(node, ast.Dict):
        qs = next((v for k, v in zip(node.keys, node.values)
                   if getattr(k, "value", "") == "questions"), None)
        if qs is None or not isinstance(qs, ast.List) or not qs.elts:
            return None, None, None
        q = qs.elts[0]
        if not isinstance(q, ast.Dict):
            return None, None, None
        keys = {getattr(k, "value", ""): v for k, v in zip(q.keys, q.values)}
        return keys.get("choices"), keys.get("each"), keys.get("answer")
    return None, None, None


def edit_bank_file(path, ids, want, done, notes) -> bool:
    """은행 파일 하나에서 문항을 옮긴다. `ids[i]` 는 ITEMS[i] 의 문항 id."""
    raw = path.read_bytes()
    tree = ast.parse(raw.decode("utf-8"))
    assign = next((n for n in tree.body
                   if isinstance(n, ast.Assign)
                   and getattr(n.targets[0], "id", "") == "ITEMS"), None)
    if assign is None or not isinstance(assign.value, ast.List):
        return False

    edits = []
    for i, node in enumerate(assign.value.elts):
        key = ids[i] if i < len(ids) else None
        if key is None or key not in want:
            continue
        ch, ea, an = _question_nodes(tree, node)
        if ch is None or an is None:
            notes.append(f"{key}: choices/answer 를 소스에서 찾지 못했다")
            continue
        frm = ast.literal_eval(an) - 1
        to = want[key] - 1
        if frm == to:
            notes.append(f"{key}: 이미 {want[key]}번 자리다")
            continue
        cs = spans(raw, ch)
        texts = [raw[a:b].decode("utf-8") for a, b in cs]
        edits.append(((cs[0][0], cs[-1][1]), ", ".join(move(texts, frm, to))))
        if ea is not None and isinstance(ea, ast.List) and len(ea.elts) == len(ch.elts):
            es = spans(raw, ea)
            et = [raw[a:b].decode("utf-8") for a, b in es]
            edits.append(((es[0][0], es[-1][1]),
                          ", ".join(renumber_each(move(et, frm, to)))))
        elif ea is not None:
            notes.append(f"{key}: each 개수가 선지와 달라 건드리지 않았다")
        edits.append((spans(raw, ast.List(elts=[an]))[0], str(to + 1)))
        done.append((key, frm + 1, to + 1))

    if not edits:
        return False
    ordered = sorted(edits, key=lambda x: x[0][0])
    for (prev, _pt), (nxt, _nt) in zip(ordered, ordered[1:]):
        if prev[1] > nxt[0]:
            raise SystemExit(f"[중단] 수정 구간이 겹친다: {prev} / {nxt}")
    for (a, b), text in reversed(ordered):
        raw = raw[:a] + text.encode("utf-8") + raw[b:]
    path.write_bytes(raw)
    print(f"[수정] {path.relative_to(ROOT)}")
    return True


def bank_files():
    """(경로, ITEMS 순서대로의 id 목록, 모듈) 을 돌려준다.

    id 는 `_q()` 안에서 f-string 으로 만들어져 **소스만 봐서는 알 수 없다.**
    그래서 모듈을 실제로 읽어 순서와 id 를 맞춘다.
    """
    for path in sorted((ROOT / "bank").rglob("*.py")):
        if "__pycache__" in path.parts or path.name in ("loader.py", "qtypes.py"):
            continue
        mod = path.relative_to(ROOT).with_suffix("").as_posix().replace("/", ".")
        try:
            # 전산직 파일 몇 개는 적재하면서 검증 결과를 찍는다. 여기서는 방해만 된다.
            with contextlib.redirect_stdout(io.StringIO()):
                m = importlib.import_module(mod)
        except Exception as e:
            print(f"   [적재 실패] {mod} — {type(e).__name__}: {e}")
            continue
        items = getattr(m, "ITEMS", None)
        if not items:
            continue
        yield path, [it.get("id") for it in items], m


def run_bank(want: dict) -> int:
    """은행 문항(bank/**/*.py 의 ITEMS)을 문항 id 로 옮긴다."""
    done, notes, seen = [], [], set()
    mods = []
    for path, ids, m in bank_files():
        seen |= {i for i in ids if i}
        mods.append((ids, m))
        if any(i in want for i in ids):
            edit_bank_file(path, ids, want, done, notes)

    if done:
        stuck = sync_verifiers({k: (f, t) for k, f, t in done})
        if stuck:
            print(f"   [주의] 검증기 배치람다를 자동으로 못 고친 문항 {len(stuck)}개")
            for i in stuck:
                print(f"      {i}")

    for key, frm, to in sorted(done):
        print(f"   {key:34} {CIRCLED[frm-1]} → {CIRCLED[to-1]}")
    for n in notes:
        print(f"   [안내] {n}")
    missing = [k for k in want if k not in seen]
    if missing:
        print(f"\n[중단] 은행에 없는 id {len(missing)}개 — {missing[:5]}")
        return 1

    # explain 이 선지 번호를 가리키는 곳을 알려 준다 — 자동으로 고치지 않는다.
    # **파일을 고친 뒤라 모듈을 다시 읽어야 한다.**
    print("\n[확인 필요] 옮긴 문항의 explain 에 남은 선지 번호 참조")
    moved = {k for k, _f, _t in done}
    hit = 0
    for _ids, m in mods:
        with contextlib.redirect_stdout(io.StringIO()):
            importlib.reload(m)
        for it in getattr(m, "ITEMS", []):
            if it.get("id") not in moved:
                continue
            for q in it.get("questions", []):
                body = q.get("explain") or ""
                for mt in re.finditer(r"[①②③④⑤]", body):
                    lo, hi = max(0, mt.start() - 28), min(len(body), mt.end() + 28)
                    print(f"   {it['id']}  …{re.sub(r'<[^>]+>', '', body[lo:hi])}…")
                    hit += 1
    if not hit:
        print("   없음")
    return 0


def sort_bank(dry: bool) -> int:
    """은행에서 오름차순이 깨진 수치 선지 문항을 찾아 값 순으로 다시 늘어놓는다."""
    done, notes = [], []
    plans = {}
    for path, ids, m in bank_files():
        todo = {}
        for i, it in enumerate(m.ITEMS):
            q = it["questions"][0]
            v = choice_values(q["choices"])
            if v is None or v == sorted(v):
                continue
            perm = sorted(range(len(v)), key=lambda j: v[j])
            todo[it["id"]] = perm
            plans[it["id"]] = (perm, q["answer"], perm.index(q["answer"] - 1) + 1)
        if not todo:
            continue
        if dry:
            continue
        edit_sorted(path, ids, todo, done, notes)

    for iid, (perm, old, new) in sorted(plans.items()):
        print(f"   {iid:26} 정답 {CIRCLED[old-1]} → {CIRCLED[new-1]}")
    if dry:
        print(f"\n[미리보기] {len(plans)}문항. 실제로 고치려면 --sort 를 쓴다")
        return 0
    if done:
        stuck = sync_verifiers({k: p for k, (p, _o, _n) in plans.items()})
        if stuck:
            print(f"   [주의] 검증기를 자동으로 못 고친 문항 {len(stuck)}개 — {stuck}")
    for n in notes:
        print(f"   [안내] {n}")
    return 0


def edit_sorted(path, ids, todo, done, notes) -> bool:
    """choices·each 를 순열대로 다시 쓰고 answer 를 맞춘다."""
    raw = path.read_bytes()
    tree = ast.parse(raw.decode("utf-8"))
    assign = next((n for n in tree.body
                   if isinstance(n, ast.Assign)
                   and getattr(n.targets[0], "id", "") == "ITEMS"), None)
    if assign is None or not isinstance(assign.value, ast.List):
        return False
    edits = []
    for i, node in enumerate(assign.value.elts):
        key = ids[i] if i < len(ids) else None
        if key not in todo:
            continue
        ch, ea, an = _question_nodes(tree, node)
        if ch is None or an is None:
            notes.append(f"{key}: choices/answer 를 소스에서 찾지 못했다")
            continue
        perm = todo[key]
        cs = spans(raw, ch)
        texts = [raw[a:b].decode("utf-8") for a, b in cs]
        edits.append(((cs[0][0], cs[-1][1]), ", ".join(apply_perm(texts, perm))))
        if ea is not None and isinstance(ea, ast.List) and len(ea.elts) == len(ch.elts):
            es = spans(raw, ea)
            et = [raw[a:b].decode("utf-8") for a, b in es]
            edits.append(((es[0][0], es[-1][1]),
                          ", ".join(renumber_each(apply_perm(et, perm)))))
        old = ast.literal_eval(an)
        edits.append((spans(raw, ast.List(elts=[an]))[0],
                      str(perm.index(old - 1) + 1)))
        done.append(key)
    if not edits:
        return False
    ordered = sorted(edits, key=lambda x: x[0][0])
    for (prev, _pt), (nxt, _nt) in zip(ordered, ordered[1:]):
        if prev[1] > nxt[0]:
            raise SystemExit(f"[중단] 수정 구간이 겹친다: {prev} / {nxt}")
    for (a, b), text in reversed(ordered):
        raw = raw[:a] + text.encode("utf-8") + raw[b:]
    path.write_bytes(raw)
    print(f"[수정] {path.relative_to(ROOT)}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--round", metavar="이름")
    g.add_argument("--bank", action="store_true",
                   help="bank/**/*.py 의 ITEMS 를 문항 id 로 가리킨다")
    g.add_argument("--sort", action="store_true",
                   help="은행의 수치 선지를 오름차순으로 다시 늘어놓는다 (규칙 4-13)")
    g.add_argument("--sort-dry", action="store_true", help="--sort 미리보기")
    ap.add_argument("moves", nargs="*", metavar="번호=위치",
                    help="예) 01=1 05=5 · ncs-math-common-003=5")
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT))
    if args.sort or args.sort_dry:
        return sort_bank(dry=args.sort_dry)

    want = {}
    for m in args.moves:
        no, pos = m.rsplit("=", 1)
        want[no if args.bank else int(no)] = int(pos)
    if any(not 1 <= p <= 5 for p in want.values()):
        raise SystemExit("[중단] 목표 위치는 1~5 다")

    if args.bank:
        return run_bank(want)

    import build
    build.select_round(args.round)

    # 문항 번호는 적재 순서대로 붙는다. 파일별 시작 번호를 미리 센다.
    counter = {"no": 1}

    def key_of(_blk, _qi):
        n = counter["no"]
        counter["no"] += 1
        return n

    done, notes = [], []
    for mod_name, area, _ in build.CFG.AREAS:
        path = build.CONTENT / f"{mod_name}.py"
        if path.exists():
            edit_file(path, "BLOCKS", key_of, want, done, notes)

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
