# -*- coding: utf-8 -*-
"""릴리스 APK 를 짓는다 — **ASCII 경로에서.**

    python mobile/tool/build_apk.py            # 짓고 mobile/build/ 로 가져온다
    python mobile/tool/build_apk.py --keep     # 작업 사본을 남긴다

## 왜 여기서 바로 못 짓나

이 저장소는 `C:\\Users\\사용자\\...` 아래에 있다. 사용자 이름이 한글이다.
Flutter 3.44 의 AOT 스냅샷터(`gen_snapshot`)가 그 경로를 시스템 코드페이지로
넘기다가 깨뜨린다 — 커널 컴파일까지는 되는데 그 결과를 못 읽는다.

    Error: Unable to read file: C:\\Users\\?????\\...\\app.dill
    Dart snapshot generator failed with exit code 255

`app.dill` 은 **실제로 만들어져 있다**(46MB). 파일이 없는 게 아니라 이름이
깨진 것이다. 같은 이유로 `flutter analyze` 도 LSP 핸드셰이크에서 죽는다.

2026-08-07 (v1.2.0) 에는 됐다. Flutter 를 올린 뒤에 생긴 회귀다.

## 고르지 않은 길

  · 윈도우의 「UTF-8 전역 설정」을 켠다 — **시스템 설정은 건드리지 않는다**
  · 저장소를 통째로 옮긴다 — 집필·검증 파이프라인의 경로가 다 바뀐다
  · 정션을 건다 — 윈도우가 실제 경로로 되돌려 풀어서 소용이 없다

그래서 **짓는 동안만** ASCII 경로에 사본을 두고, 결과물만 가져온다.
소스의 진실은 계속 `mobile/` 이다.
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
APP = HERE.parent                       # mobile/
WORK = pathlib.Path(r"C:\dev\ncs_bank")  # ASCII 경로. .claude/launch.json 의 flutter-web 도 여기를 본다

# 사본에 옮기지 않는 것 — 지으면 다시 생기고, 옮기면 오히려 옛 산출물이 섞인다
SKIP = {"build", ".dart_tool", ".idea", ".git"}

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sync() -> None:
    """`mobile/` 를 작업 경로로 옮긴다. 지운 파일이 남지 않게 먼저 비운다."""
    if WORK.exists():
        for p in WORK.iterdir():
            if p.name in SKIP:
                continue                 # 빌드 캐시는 남겨 두어야 다시 짓는 것이 빠르다
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    WORK.mkdir(parents=True, exist_ok=True)

    n = 0
    for src in APP.rglob("*"):
        rel = src.relative_to(APP)
        if rel.parts[0] in SKIP:
            continue
        dst = WORK / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            n += 1
    print(f"   옮겼다 {n}개 → {WORK}")


def version() -> str:
    for line in (APP / "pubspec.yaml").read_text(encoding="utf-8").splitlines():
        if line.startswith("version:"):
            return line.split(":", 1)[1].strip()
    raise SystemExit("pubspec.yaml 에 version 이 없다")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="작업 사본을 남긴다")
    a = ap.parse_args()

    ver = version()
    print(f"   판  {ver}")

    # **먼저 지운다.** 작업 경로에는 지난 빌드의 app-release.apk 가 남아 있다.
    # 이번 빌드가 실패해도 그 파일은 그대로라, 지우지 않으면 **옛 APK 를 새 판인 척
    # 가져와 올리게 된다.** 없는 것이 실패보다 낫다.
    made = WORK / "build" / "app" / "outputs" / "flutter-apk" / "app-release.apk"
    made.unlink(missing_ok=True)

    sync()

    for cmd in (["flutter", "pub", "get"], ["flutter", "build", "apk", "--release"]):
        print("   $", " ".join(cmd))
        r = subprocess.run(cmd, cwd=WORK, shell=True)
        if r.returncode:
            return r.returncode

    if not made.is_file():
        print("   [실패] APK 가 없다 —", made)
        return 1

    out_dir = APP / "build" / "app" / "outputs" / "flutter-apk"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"ncs-bank-v{ver.split('+')[0]}.apk"
    shutil.copy2(made, out)
    print(f"   가져왔다 — {out}  ({out.stat().st_size / 1048576:.1f}MB)")

    if not a.keep:
        # 사본의 소스만 지운다. 빌드 캐시는 남겨 다음 빌드를 빠르게 한다
        for p in WORK.iterdir():
            if p.name not in SKIP:
                shutil.rmtree(p) if p.is_dir() else p.unlink()
        print("   작업 사본의 소스를 치웠다 (빌드 캐시는 남긴다)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
