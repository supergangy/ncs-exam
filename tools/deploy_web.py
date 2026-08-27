# -*- coding: utf-8 -*-
"""재제작 판(`web/dist`)을 배포 저장소 **루트**로 올린다.

    python tools/deploy_web.py            # 올린다
    python tools/deploy_web.py --dry      # 무엇이 바뀌는지만 보인다

## 한 세대를 남긴다

`rm -rf * && cp -r dist/* .` 로 올렸다가 **배포본이 하얀 화면**이 되었다
(2026-08-27, `/next/` 에서). 되돌아온 브라우저는 서비스 워커 캐시에 있던 옛
`index.html` 을 받았고, 그 안에 적힌 묶음 이름은 방금 지워져 404 가 되었다.
Vite 가 해시 붙은 이름을 내므로 배포마다 이름이 바뀌는데, 옛 껍데기는 옛 이름만 안다.

그래서 **직전 배포의 파일을 지우지 않고 한 세대 함께 둔다.** 남긴 것은
`carry.json` 에 적고, **이름이 바뀐 배포에서만** 늙힌다 — 워커만 고치는 배포에서
늙히면 아직 옛 껍데기를 물고 있는 브라우저가 다시 404 를 맞는다(한 번 그랬다).

## 루트로 옮길 때 (2026-08-28)

옛 루트 워커 `ncsbank-v12` 는 **캐시 먼저**(stale-while-revalidate)다. 그래서
되돌아온 사용자는 **옛 앱을 한 번 더 본다** — 캐시에 든 옛 `index.html` 이 먼저
나가고, 그 사이 새 워커가 설치·활성화되어 옛 캐시를 지운다. 다음 방문에 새 앱이다.
그 「한 번 더」를 없앨 방법은 없다. 캐시에 이미 든 HTML 은 바꿀 수 없다.

옛 앱이 부르는 것은 해시 없는 `app.js`·`app.css` 다. 새 워커가 활성화되며 옛 캐시를
지우는 순간 아직 안 온 요청이 그물로 떨어지므로, 그 둘이 **서버에 남아 있어야** 한다.
한 세대 규칙이 그것을 한다.

`data/admin.json`·`README.md` 는 KEEP 이다 — 빌드 산출물이 아니라 일부러 둔 것이라
세대에 얽히지 않는다. (관리자 모드 화면은 재제작 판에 아직 없다. 파일만 남긴다.)

## `/next/` 는 이정표로 바꾼다

재제작 판을 시험하던 하위 경로다. 이제 루트가 그 판이므로 **되돌려 보낸다.**
안내 페이지만 올리면 안 된다 — 그 경로에 워커가 남아 캐시에서 옛 앱을 계속 내준다
(옛 `ncs-exam-app` 주소에서 배운 것, `docs/BANK.md` 6절). 그래서 **자기를 지우는
워커**를 함께 올린다.

캐시 저장소는 **출처 단위**다. 그 워커가 캐시를 전부 지우면 루트 앱의 캐시까지
날아간다 — 그래서 **`/next/` 항목만 든 캐시**를 골라 지운다.
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
CARRY = "carry.json"
URL = "https://supergangy.github.io/ncs-pass-app/"

# 빌드 산출물이 아니다 — 건드리지 않고, 세대 셈에도 넣지 않는다
KEEP = {"README.md", "data/admin.json"}
# 일부러 만드는 이정표. 세대 셈 밖이다
LEGACY = "next"

# 없으면 배포하지 않는다 — 하나라도 빠지면 앱이 뜨지 않는다
MUST = ["index.html", "m/index.html", "sw.js", "data/bank.json",
        "manifest.webmanifest", "m-manifest.webmanifest"]

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


SIGNPOST = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>NCS PASS — 주소가 바뀌었습니다</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="canonical" href="{up}">
<script>
  /* 해시를 그대로 들고 간다 — 북마크한 #/t/수리능력 이 열려야 한다 */
  location.replace('{up}' + location.hash);
</script>
<style>
  body {{ margin: 0; display: grid; place-items: center; min-height: 100vh;
         background: #f7f8fa; color: #0f172a;
         font: 15px/1.7 -apple-system, "Segoe UI", "Malgun Gothic", sans-serif; }}
  div {{ max-width: 22rem; padding: 1.5rem; text-align: center; }}
  a {{ color: #4f46e5; font-weight: 700; }}
</style>
</head>
<body>
<div>
  <p><b>NCS PASS</b> 는 주소를 옮겼습니다.</p>
  <p><a href="{up}">여기서 이어서 풀기</a></p>
  <p style="color:#64748b;font-size:13px">
    푼 기록은 그대로 있습니다 — 같은 브라우저에 남습니다.
  </p>
</div>
</body>
</html>
"""

UNREGISTER = """/* 이 경로의 워커 — **자기를 지운다.**
 *
 * 재제작 판이 루트로 옮겼다. 안내 페이지만 올리면 이 워커가 캐시에서 옛 앱을
 * 계속 내주므로 안내가 보이지 않는다 (옛 ncs-exam-app 주소에서 배운 것).
 *
 * 캐시 저장소는 **출처 단위**다. 전부 지우면 루트 앱의 캐시까지 날아간다 —
 * 그래서 항목이 **모두 /next/ 인 캐시**만 골라 지운다.
 */
self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) {
      const c = await caches.open(k);
      const urls = (await c.keys()).map(r => new URL(r.url).pathname);
      if (urls.length && urls.every(p => p.includes('/next/'))) await caches.delete(k);
    }
    await self.registration.unregister();
  })());
});

/* 아무것도 가로채지 않는다 — 그물에서 안내 페이지를 받게 둔다 */
"""


def walk(base: pathlib.Path, skip: set[str] = frozenset()) -> set[str]:
    """`base` 아래 모든 파일의 상대 경로 (`/` 구분). `skip` 은 최상위 디렉터리 이름"""
    if not base.is_dir():
        return set()
    out = set()
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(base).as_posix()
        if rel.split("/")[0] in skip or rel.split("/")[0] == ".git":
            continue
        out.add(rel)
    return out


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


def signpost(target: pathlib.Path, dry: bool) -> list[str]:
    """`/next/` 를 이정표로 바꾼다. @returns 지운 파일 목록"""
    old = walk(target / LEGACY)
    files = {
        "index.html": SIGNPOST.format(up="../"),
        "m/index.html": SIGNPOST.format(up="../../m/"),
        "sw.js": UNREGISTER,
    }
    gone = sorted(old - set(files))
    if dry:
        return gone
    for rel, body in files.items():
        p = target / LEGACY / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8", newline="\n")
    for rel in gone:
        (target / LEGACY / rel).unlink(missing_ok=True)
    for d in sorted((p for p in (target / LEGACY).rglob("*") if p.is_dir()),
                    key=lambda p: len(p.parts), reverse=True):
        if not any(d.iterdir()):
            d.rmdir()
    return gone


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="무엇이 바뀌는지만 보인다")
    ap.add_argument("--msg", default=None, help="커밋 제목 (기본: 재배포 — <판>)")
    ap.add_argument("--restore-from", default=None,
                    help="이 커밋의 파일을 먼저 되살린다 (지워 버린 세대를 구할 때만)")
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

        if a.restore_from:
            run(["git", "checkout", a.restore_from, "--", "."], work)
            print(f"   {a.restore_from} 을 되살렸다")

        carried = set()
        cf = work / CARRY
        if cf.is_file():
            try:
                carried = set(json.loads(cf.read_text(encoding="utf-8")).get("carried", []))
            except (ValueError, OSError):
                carried = set()

        present = walk(work, skip={LEGACY}) - {CARRY} - KEEP
        prev_build = present - carried
        new = walk(DIST)

        rotated = prev_build - new
        # 이름이 바뀐 배포에서만 세대를 넘긴다. 안 바뀐 배포(워커만 고칠 때)에는
        # 지난번에 남긴 것을 **그대로 이어 든다** — 그것을 버리면 아직 옛 껍데기를
        # 물고 있는 브라우저가 다시 404 를 맞는다
        hold = sorted(rotated if rotated else (carried - new))
        keep = new | set(hold)
        drop = sorted(present - keep)

        why = "이름이 바뀌었다" if rotated else "이름 그대로 — 지난 세대를 이어 든다"
        print(f"   이번 판 {len(new)}개 · 남길 것 {len(hold)}개 ({why}) · 지울 것 {len(drop)}개")
        for f in hold:
            print(f"      남긴다  {f}")
        for f in drop:
            print(f"      지운다  {f}")
        gone = signpost(work, dry=True)
        print(f"   /{LEGACY}/ 를 이정표로 — 안내 2장 + 자기를 지우는 워커, {len(gone)}개 정리")

        if a.dry:
            print("   --dry 이므로 여기서 멈춘다")
            return 0

        for rel in sorted(new):
            dst = work / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(DIST / rel, dst)
        for rel in drop:
            (work / rel).unlink(missing_ok=True)
        signpost(work, dry=False)
        for d in sorted((p for p in work.rglob("*") if p.is_dir() and ".git" not in p.parts),
                        key=lambda p: len(p.parts), reverse=True):
            if not any(d.iterdir()):
                d.rmdir()

        cf.write_text(json.dumps({"version": ver, "carried": hold},
                                 ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        run(["git", "add", "-A"], work)
        if not run(["git", "diff", "--cached", "--name-only"], work):
            print("   바뀐 것이 없다 — 올리지 않는다")
            return 0

        subject = a.msg or f"재배포 — {ver}"
        body = (f"{subject}\n\n"
                f"이번 판 {len(new)}개. 직전 배포의 {len(hold)}개는 한 세대 남긴다 —\n"
                f"옛 껍데기를 캐시에 물고 있는 브라우저가 그것으로 한 번 더 뜬다.\n"
                f"두 세대 전 {len(drop)}개는 지웠다. 남긴 목록은 {CARRY} 에 있다.\n"
                f"/{LEGACY}/ 는 이정표다 — 안내 페이지와 자기를 지우는 워커.\n")
        run(["git", "commit", "-q", "-m", body], work)
        run(["git", "push", "-q", "origin", "main"], work)
        print(f"   올렸다 — {URL}")
        print("   Pages 가 다 굽고 나면 tools/deploy_check.py 로 잰다")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
