# -*- coding: utf-8 -*-
"""앱 화면을 찍는다 — **기록이 있는 상태**로.

기록이 빈 화면은 「—」와 「비어 있음」만 보여 준다. 그것도 봐야 하지만,
실제로 쓰는 모습은 풀어 본 기록이 쌓인 뒤다. 그래서 씨앗 기록을 만들어
localStorage 에 미리 심고 찍는다.

Chrome headless 의 `--window-size` 는 창 크기이지 뷰포트 에뮬레이션이 아니다.
세로를 화면보다 크게 주면 **폭 계산이 어긋나 오른쪽이 잘린다** — 실제로 잘렸다.
그래서 세로를 화면 안에 두고 화면마다 한 장씩 찍는다.

    python brand/shots.py            # 빌드된 web/dist 를 찍는다
    python brand/shots.py --keep     # 임시 사본을 남긴다 (직접 열어 보려면)
"""
from __future__ import annotations

import argparse
import http.server
import json
import pathlib
import random
import shutil
import socketserver
import subprocess
import sys
import threading
import time

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "web" / "dist"
OUT = ROOT / "brand" / "out"
WORK = ROOT / "brand" / "out" / "_shots"
CHROME = pathlib.Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

PORT = 8802
DAY = 86400000

MOBILE = (375, 812)                  # 실기기와 같은 폭
DESKTOP = (1440, 900)                # 팔레트까지 펼쳐지는 폭 (1200 이상)

# 찍을 화면 — (파일명, 진입점, 해시, 설명)
SHOTS = [
    ("m-home",   "m/", "#/",                 "모바일 홈"),
    ("m-area",   "m/", "#/t/수리능력",        "모바일 영역"),
    ("m-solve",  "m/", "#/q?sj=수리능력",     "모바일 문항"),
    ("m-exams",  "m/", "#/exams",            "모바일 회차"),
    ("m-sit",    "m/", "#/sit/r3_korail",    "모바일 응시"),
    ("m-result", "m/", "#/result/r2_korail", "모바일 결과"),
    ("m-stats",  "m/", "#/stats",            "모바일 분석"),
    ("m-more",   "m/", "#/more",             "모바일 더보기"),

    ("d-home",   "",   "#/",                 "PC 홈"),
    ("d-bank",   "",   "#/s/수리능력/확률",   "PC 문항 은행"),
    ("d-solve",  "",   "#/q?sj=수리능력",     "PC 문항 풀이"),
    ("d-exams",  "",   "#/exams",            "PC 회차"),
    ("d-sit",    "",   "#/sit/r3_korail",    "PC 응시"),
    ("d-result", "",   "#/result/r2_korail", "PC 결과"),
    ("d-stats",  "",   "#/stats",            "PC 분석"),
    ("d-search", "",   "#/search",           "PC 검색"),
]


def seed() -> dict:
    """씨앗 기록 — 배포본과 같은 구조로 만든다.

    닷새 연속 · 오늘 12문항 · 영역마다 정답률을 달리해 취약 영역이 드러나게.
    회차는 2회차를 두 번 응시, 3회차는 응시 중(8분 남음)으로 둔다.
    """
    raw = json.loads((DIST / "data" / "bank.json").read_text(encoding="utf-8"))
    items = raw["items"]
    rnd = random.Random(20260827)     # 찍을 때마다 달라지면 견줄 수 없다

    now = int(time.time() * 1000)
    t0 = now - now % DAY             # 대충 하루 시작 (UTC 기준이어도 그림에는 무해)

    sjs = sorted({i["sj"] for i in items})
    rate = {s: 0.45 + (k % 5) * 0.12 for k, s in enumerate(sjs)}

    att, srs = {}, {}
    k = 0
    for back, n in [(0, 12), (1, 38), (2, 41), (3, 33), (4, 45)]:
        for j in range(n):
            it = items[(k * 7 + back * 13) % len(items)]
            k += 1
            if it["id"] in att:
                continue
            ok = rnd.random() < rate.get(it["sj"], .7)
            t = t0 - back * DAY + (9 + j % 10) * 3600000
            att[it["id"]] = [{"c": it["an"] if ok else (it["an"] % len(it["ch"])) + 1,
                              "k": 1 if ok else 0, "t": t, "m": 20000 + j * 900}]
            srs[it["id"]] = {"due": t + (-DAY if j % 6 == 0 else 3 * DAY), "i": 1, "e": 2.5}

    # 2회차 — 두 번 응시한 이력
    r2 = sorted([i for i in items if i.get("rd") == "r2_korail"], key=lambda x: x["no"])
    ans, score = {}, 0
    for j, it in enumerate(r2):
        if j % 7 == 3:
            continue                 # 몇 개는 표기 안 함
        ok = j % 3 != 0
        ans[str(it["no"])] = it["an"] if ok else (it["an"] % len(it["ch"])) + 1
        score += ok
    exams = {"r2_korail": [
        {"at": now - 3 * DAY, "score": 15, "n": len(r2), "sec": 1850, "auto": 0, "ans": ans},
        {"at": now - DAY, "score": score, "n": len(r2), "sec": 2010, "auto": 1, "ans": ans},
    ]}

    # 3회차 — 응시 중
    r3 = sorted([i for i in items if i.get("rd") == "r3_korail"], key=lambda x: x["no"])
    sit = {"tag": "r3_korail", "at": now - 27 * 60000, "endsAt": now + 8 * 60000,
           "ans": {str(r3[i]["no"]): 1 + i % 4 for i in (0, 1, 2, 4, 7)},
           "flag": {str(r3[3]["no"]): True, str(r3[8]["no"]): True},
           "at_no": r3[3]["no"]}

    return {"att": att, "srs": srs, "exams": exams, "sit": sit, "mark": {}, "solo": None,
            "pref": {"goal": 25, "examAt": now + 18 * DAY}, "admin": False, "seen": 0, "ts": 1.0}


def prepare() -> None:
    """dist 를 사본으로 옮기고, 앱 스크립트보다 **먼저** 기록을 심는다."""
    if WORK.exists():
        shutil.rmtree(WORK)
    shutil.copytree(DIST, WORK)

    blob = json.dumps(seed(), ensure_ascii=False, separators=(",", ":"))
    inject = ("<script>try{localStorage.setItem('ncsbank.v1',"
              + json.dumps(blob) + ")}catch(e){}</script>")

    # 두 진입점 모두 — 앱이 store 를 읽기 전에 심어야 한다
    for rel in ("m/index.html", "index.html"):
        p = WORK / rel
        s = p.read_text(encoding="utf-8")
        at = s.index("<script type=\"module\"")
        s = s[:at] + inject + s[at:]
        # PC 진입점은 좁은 화면이면 모바일로 보낸다 — 찍을 때는 그 길을 막는다
        s = s.replace("location.replace('./m/' + location.hash);", "/* 촬영 중 */;")
        p.write_text(s, encoding="utf-8")


def serve() -> socketserver.TCPServer:
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(WORK), **kw)

        def log_message(self, *a):
            pass

    srv = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def shoot(name: str, entry: str, hash_: str) -> pathlib.Path:
    dst = OUT / ("%s.png" % name)
    w, h = MOBILE if entry else DESKTOP
    subprocess.run(
        [str(CHROME), "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--virtual-time-budget=9000", "--window-size=%d,%d" % (w, h),
         "--screenshot=" + str(dst),
         "http://127.0.0.1:%d/%sindex.html%s" % (PORT, entry, hash_)],
        capture_output=True, timeout=120)
    return dst


def sheet(paths, cols: int = 4, name: str = "screens.png") -> pathlib.Path:
    gap, pad = 12, 26
    ims = [(Image.open(p), label) for p, label in paths if p.exists()]
    rows = (len(ims) + cols - 1) // cols
    cw, ch = ims[0][0].width, ims[0][0].height
    sh = Image.new("RGB", (cols * cw + (cols - 1) * gap,
                           rows * (ch + pad) + (rows - 1) * gap), (255, 255, 255))
    from PIL import ImageDraw, ImageFont
    d = ImageDraw.Draw(sh)
    # PIL 기본 폰트는 한글을 못 그린다 — 시트 라벨이 두부가 된다
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\malgun.ttf", 14)
    except OSError:
        font = None
    for k, (im, label) in enumerate(ims):
        x = (k % cols) * (cw + gap)
        y = (k // cols) * (ch + pad + gap)
        d.text((x + 2, y + 5), label, fill=(71, 85, 105), font=font)
        sh.paste(im, (x, y + pad))
    out = OUT / name
    sh.save(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="임시 사본을 남긴다")
    args = ap.parse_args()

    if not (DIST / "m" / "index.html").exists():
        print("  web/dist 가 없다 — 먼저 빌드하라 (cd web && npx vite build)")
        return 1
    if not CHROME.exists():
        print("  크롬을 찾지 못했다:", CHROME)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    prepare()
    srv = serve()
    try:
        m_made, d_made = [], []
        for name, entry, hash_, label in SHOTS:
            p = shoot(name, entry, hash_)
            ok = p.exists() and p.stat().st_size > 3000
            print("  %-10s %-16s %s" % (name, label, "찍음" if ok else "!! 실패"))
            if ok:
                (m_made if entry else d_made).append((p, label))
        if m_made:
            out = sheet(m_made, cols=4, name="m-screens.png")
            print("  %s  %s" % (out.name, Image.open(out).size))
        if d_made:
            out = sheet(d_made, cols=2, name="d-screens.png")
            print("  %s  %s" % (out.name, Image.open(out).size))
    finally:
        srv.shutdown()
        if not args.keep:
            shutil.rmtree(WORK, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
