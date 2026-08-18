# -*- coding: utf-8 -*-
"""배포된 웹판이 로컬과 얼마나 벌어졌는지 잰다.

## 왜 있는가

웹 배포는 `app/` 을 **별도 공개 저장소로 옮기는 수동 절차**다(docs/BANK.md 6절).
파이프라인에 묶여 있지 않으므로 문항을 늘리고 커밋해도 배포본은 그대로다.

실제로 그렇게 벌어졌다 — 로컬 764문항인데 **배포본이 540에서 멈춰** 있었고,
전산직 300문항 완성과 새 두 영역(대인관계·자기개발)이 반영되지 않았다.
커밋 기록만 보면 알 수 없다(2026-08-18).

`sw.js` 의 캐시 버전도 함께 본다. 파일을 새로 올려도 **버전이 같으면
브라우저가 옛 캐시를 계속 쓴다.**

    python tools/deploy_check.py

벌어져 있으면 exit 1 이므로 CI 나 배포 스크립트 앞에 걸 수 있다.
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://supergangy.github.io/ncs-exam-app"
LOCAL_BANK = ROOT / "app" / "data" / "bank.json"
LOCAL_SW = ROOT / "app" / "sw.js"
VER = re.compile(r"const VERSION = '([^']+)'")


def fetch(path: str) -> str | None:
    try:
        with urllib.request.urlopen(f"{BASE}/{path}", timeout=30) as r:
            return r.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"   [받기 실패] {path} — {e}")
        return None


def items(blob: str | bytes) -> list[dict]:
    d = json.loads(blob)
    return d["items"] if isinstance(d, dict) and "items" in d else d


def main() -> int:
    local = items(LOCAL_BANK.read_text(encoding="utf-8"))
    raw = fetch("data/bank.json")
    if raw is None:
        return 1
    remote = items(raw)

    print(f"   로컬  {len(local):4}문항")
    print(f"   배포본 {len(remote):4}문항")
    gap = len(local) - len(remote)

    lc = collections.Counter(i.get("sj", "") for i in local)
    rc = collections.Counter(i.get("sj", "") for i in remote)
    diff = {k: (lc.get(k, 0), rc.get(k, 0))
            for k in set(lc) | set(rc) if lc.get(k, 0) != rc.get(k, 0)}
    if diff:
        print()
        print("   영역별 차이 (로컬 → 배포본)")
        for k, (a, b) in sorted(diff.items()):
            mark = "  ← 배포본에 없다" if b == 0 else ""
            print(f"     {k:14} {a:4} → {b:4}{mark}")

    # 캐시 버전 — 같으면 새 파일을 올려도 옛 캐시가 나간다
    lsw = VER.search(LOCAL_SW.read_text(encoding="utf-8"))
    rraw = fetch("sw.js")
    rsw = VER.search(rraw) if rraw else None
    print()
    print(f"   sw 캐시  로컬 {lsw.group(1) if lsw else '?'} · "
          f"배포본 {rsw.group(1) if rsw else '?'}")

    same_ver = bool(lsw and rsw and lsw.group(1) == rsw.group(1))
    if gap == 0 and not diff:
        if same_ver:
            print()
            print("   배포본이 로컬과 같다.")
            return 0
        print()
        print("   [주의] 문항은 같은데 sw 캐시 버전이 다르다 — 배포가 덜 끝났을 수 있다")
        return 1

    print()
    print(f"   [벌어짐] 문항 {gap:+}개. 재배포가 필요하다.")
    if same_ver:
        print("   **sw 캐시 버전을 올려야** 브라우저가 새 파일을 받는다 "
              "(app/sw.js 의 VERSION).")
    print()
    print("   재배포 — docs/BANK.md 6절")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
