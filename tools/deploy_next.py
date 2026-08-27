# -*- coding: utf-8 -*-
"""재제작 판(`web/dist`)을 배포 저장소의 `next/` 로 올린다.

    python tools/deploy_next.py            # 올린다
    python tools/deploy_next.py --dry      # 무엇이 바뀌는지만 보인다

## 왜 손으로 하지 않는가

`rm -rf next && cp -r dist next` 로 올렸다가 **배포본이 하얀 화면**이 되었다
(2026-08-27). 되돌아온 브라우저는 서비스 워커 캐시에 있던 **옛 `index.html`** 을
받았고, 그 안에 적힌 묶음 이름 넷은 방금 지워져 404 가 되었다. Vite 가 해시 붙은
이름을 내므로 배포마다 이름이 바뀌는데, 옛 껍데기는 옛 이름만 안다.

두 군데를 함께 고쳐야 한다.

| 어디 | 무엇 |
|---|---|
| `web/tool/make_sw.mjs` | HTML 은 **그물이 먼저**. 캐시는 오프라인일 때만 |
| 여기 | 직전 배포의 파일을 **한 세대 남긴다** |

워커를 고쳐도 **이미 옛 워커를 물고 있는 브라우저**는 구할 수 없다 — 그 브라우저는
옛 껍데기를 캐시에서 먼저 준다. 옛 이름이 서버에 남아 있으면 그것으로 한 번 더 뜨고,
그때 새 워커가 자리를 잡는다. 그래서 한 세대를 남긴다.

## 세대가 쌓이지 않게

남긴 것을 `next/carry.json` 에 적어 둔다. 다음 배포에서 그 목록은 지운다 —
언제나 **직전 한 세대만** 함께 있다.

    present     지금 배포본에 있는 것
    carried     그중 「지난번에 남겨 둔 것」 (carry.json)
    prev_build  present - carried  →  직전 배포가 실제로 낸 것
    new         이번 dist
    rotated     prev_build - new   →  이번에 이름이 바뀐 것

    hold = rotated 가 있으면  rotated       (직전 세대를 남기고 그 앞은 버린다)
           없으면             carried - new (이름이 안 바뀐 배포다 — 그대로 이어 든다)

**이름이 안 바뀐 배포에서 늙혀선 안 된다.** 워커만 고치는 배포에서는 rotated 가
비므로, 그때 carried 를 버리면 아직 옛 껍데기를 물고 있는 브라우저가 다시 404 를
맞는다 — 실제로 한 번 그랬다. 구조용 파일은 **다음 이름 교체까지** 남는다.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "web" / "dist"
REPO = "https://github.com/supergangy/ncs-pass-app.git"
SUB = "next"
CARRY = "carry.json"
URL = "https://supergangy.github.io/ncs-pass-app/next/"

# 없으면 배포하지 않는다 — 하나라도 빠지면 앱이 뜨지 않는다
MUST = ["index.html", "m/index.html", "sw.js", "data/bank.json",
        "manifest.webmanifest", "m-manifest.webmanifest"]

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def walk(base: pathlib.Path) -> set[str]:
    """`base` 아래 모든 파일의 상대 경로 (`/` 구분)"""
    if not base.is_dir():
        return set()
    return {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}


def run(args: list[str], cwd: pathlib.Path) -> str:
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        print(f"   [실패] {' '.join(args)}")
        print((r.stderr or r.stdout).strip()[:2000])
        sys.exit(1)
    return (r.stdout or "").strip()


def version() -> str:
    m = re.search(r"const VERSION = '([^']+)'", (DIST / "sw.js").read_text(encoding="utf-8"))
    if not m:
        print("   [중단] dist/sw.js 에 VERSION 이 없다 — node tool/make_sw.mjs 를 먼저 돌려라")
        sys.exit(1)
    return m.group(1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="무엇이 바뀌는지만 보인다")
    ap.add_argument("--msg", default=None, help="커밋 제목 (기본: next/ 재배포 — <판>)")
    ap.add_argument("--restore-from", default=None,
                    help="이 커밋의 next/ 를 먼저 되살린다 (지워 버린 세대를 구할 때만)")
    a = ap.parse_args()

    missing = [f for f in MUST if not (DIST / f).is_file()]
    if missing:
        print("   [중단] dist 에 없는 것 —", ", ".join(missing))
        print("          cd web && npx vite build && node tool/make_sw.mjs")
        return 1

    ver = version()
    print(f"   판  {ver}")

    work = pathlib.Path(tempfile.mkdtemp(prefix="ncspass-deploy-"))
    try:
        depth = ["--depth", "1"] if not a.restore_from else []
        run(["git", "clone", "-q", *depth, REPO, str(work)], ROOT)
        target = work / SUB

        if a.restore_from:
            # 지워 버린 세대를 되살린다 — 그 커밋의 next/ 를 얹은 뒤 평소대로 간다
            run(["git", "checkout", a.restore_from, "--", SUB], work)
            print(f"   {a.restore_from} 의 {SUB}/ 를 되살렸다")

        carried = set()
        cf = target / CARRY
        if cf.is_file():
            try:
                carried = set(json.loads(cf.read_text(encoding="utf-8")).get("carried", []))
            except (ValueError, OSError):
                carried = set()

        present = walk(target) - {CARRY}
        prev_build = present - carried
        new = walk(DIST)

        rotated = prev_build - new
        # 이름이 바뀐 배포에서만 세대를 넘긴다. 안 바뀐 배포(워커만 고칠 때)에는
        # 지난번에 남긴 것을 **그대로 이어 든다** — 그것을 버리면 아직 옛 껍데기를
        # 물고 있는 브라우저가 다시 404 를 맞는다
        hold = sorted(rotated if rotated else (carried - new))
        keep = new | set(hold)
        drop = sorted(present - keep)        # 두 세대 전 것

        why = "이름이 바뀌었다" if rotated else "이름 그대로 — 지난 세대를 이어 든다"
        print(f"   이번 판 {len(new)}개 · 남길 것 {len(hold)}개 ({why}) · 지울 것 {len(drop)}개")
        for f in hold:
            print(f"      남긴다  {f}")
        for f in drop:
            print(f"      지운다  {f}")

        if a.dry:
            print("   --dry 이므로 여기서 멈춘다")
            return 0

        for rel in sorted(new):
            dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(DIST / rel, dst)
        for rel in drop:
            (target / rel).unlink(missing_ok=True)
        # 빈 디렉터리를 남기지 않는다
        for d in sorted((p for p in target.rglob("*") if p.is_dir()),
                        key=lambda p: len(p.parts), reverse=True):
            if not any(d.iterdir()):
                d.rmdir()

        cf.write_text(json.dumps({"version": ver, "carried": hold},
                                 ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        run(["git", "add", "-A"], work)
        if not run(["git", "diff", "--cached", "--name-only"], work):
            print("   바뀐 것이 없다 — 올리지 않는다")
            return 0

        subject = a.msg or f"next/ 재배포 — {ver}"
        body = (f"{subject}\n\n"
                f"이번 판 {len(new)}개. 직전 배포의 {len(hold)}개는 한 세대 남긴다 —\n"
                f"옛 껍데기를 캐시에 물고 있는 브라우저가 그것으로 한 번 더 뜬다.\n"
                f"두 세대 전 {len(drop)}개는 지웠다. 남긴 목록은 next/carry.json 에 있다.\n")
        run(["git", "commit", "-q", "-m", body], work)
        run(["git", "push", "-q", "origin", "main"], work)
        print(f"   올렸다 — {URL}")
        print("   Pages 가 다 굽고 나면 tools/deploy_check.py 로 잰다")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
