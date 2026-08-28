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
WIDE = (2560, 1440)                  # QHD 100% — 넓은 화면에서 폭을 쓰는지 본다

# 기본 크기(MOBILE·DESKTOP)로 안 되는 것 —
#   세로가 모자란 화면은 세로만 늘린다. 폭을 늘리면 다른 앱을 찍는 셈이다.
#   `w-*` 는 예외다 — **넓은 화면 자체가 볼거리**라 폭을 바꾼다.
SIZE = {
    "m-pass":   (375, 1900),
    "d-pass":   (1440, 1200),
    "m-kw":     (375, 1500),
    "m-done":   (375, 1400),
    "m-more":   (375, 1000),
    "m-home":   (375, 1500),
    "d-kw":     (1440, 1500),
    "w-bank":   WIDE,
    "w-solve":  WIDE,
    "d-done":   (1440, 1150),
}

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
    ("m-pass",   "m/", "#/q?id=r1_public-01", "모바일 지문"),
    ("m-kw",     "m/", "#/kw",               "모바일 키워드"),
    ("m-done",   "m/", "#/done",             "모바일 마침"),

    ("d-home",   "",   "#/",                 "PC 홈"),
    ("d-bank",   "",   "#/s/수리능력/확률",   "PC 문항 은행"),
    ("d-solve",  "",   "#/q?sj=수리능력",     "PC 문항 풀이"),
    ("d-exams",  "",   "#/exams",            "PC 회차"),
    ("d-sit",    "",   "#/sit/r3_korail",    "PC 응시"),
    ("d-result", "",   "#/result/r2_korail", "PC 결과"),
    ("d-stats",  "",   "#/stats",            "PC 분석"),
    ("d-search", "",   "#/search",           "PC 검색"),
    ("d-pass",   "",   "#/q?id=r1_public-01", "PC 지문"),
    ("d-kw",     "",   "#/kw",               "PC 키워드"),
    # QHD — 「왼쪽 절반만 쓴다」를 고친 뒤로 여기서 확인한다
    ("w-bank",   "",   "#/s/수리능력/확률",   "QHD 문항 은행"),
    ("w-solve",  "",   "#/q?id=r1_public-01", "QHD 문항 풀이"),
    ("d-done",   "",   "#/done",             "PC 마침"),
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

    # 방금 푼 묶음 — 「마침」 화면이 빈 상태로 찍히지 않게. 갈래를 **전부** 지나게 짠다:
    #   맞음 · 두 번 만에 맞음 · 틀림 둘 · 건너뛰었으나 예전에 틀린 것 · 아예 안 푼 것
    # 마지막 둘 때문에 「오답노트」가 「이번에 틀림」보다 커진다 (건너뛴 1개 포함).
    pool = [i for i in items if i["sj"] == "수리능력" and i["ty"] == "확률"][:7]
    solo_t = now - 35 * 60000
    wrong = lambda it: (it["an"] % len(it["ch"])) + 1
    plan = [("ok",), ("miss", "ok"), ("miss",), ("miss",), ("ok",), ("old",), ("none",)]
    for it, how in zip(pool, plan):
        if how == ("none",):
            att.pop(it["id"], None)
            continue
        if how == ("old",):          # 예전에 틀린 채로 남아 있고 이번엔 건너뛰었다
            att[it["id"]] = [{"c": wrong(it), "k": 0, "t": now - 3 * DAY, "m": 41000}]
            continue
        tries = []
        for j, r in enumerate(how):
            tries.append({"c": it["an"] if r == "ok" else wrong(it),
                          "k": 1 if r == "ok" else 0,
                          "t": solo_t + (2 + j * 3) * 60000, "m": 38000 + j * 9000})
        att[it["id"]] = tries

    solo = {"key": "sj=수리능력&ty=확률", "ids": [i["id"] for i in pool],
            "at": len(pool) - 1, "t": solo_t}

    return {"att": att, "srs": srs, "exams": exams, "sit": sit, "mark": {}, "solo": solo,
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


def shoot_all(shots) -> list[pathlib.Path]:
    """전부 한 번에 찍는다 — `brand/shot.mjs` 가 DevTools 규약으로 찍는다.

    **`--window-size` 로 찍지 않는다.** Chrome headless 는 창을 500px 아래로 만들지
    않아서, 375 를 달라 해도 뷰포트는 500 이고 사진만 375 로 잘린다 — 탭 넷 중
    하나와 오른쪽 배지들이 사라진 채 저장됐다(2026-08-27 실측: client 500).
    `Emulation.setDeviceMetricsOverride` 는 레이아웃 폭 자체를 정한다.
    """
    spec, paths = [], []
    for name, entry, hash_, _label in shots:
        dst = OUT / ("%s.png" % name)
        w, h = (MOBILE if entry else DESKTOP)
        spec.append({
            "out": str(dst),
            "url": "http://127.0.0.1:%d/%sindex.html%s" % (PORT, entry, hash_),
            "w": SIZE.get(name, (w, h))[0], "h": SIZE.get(name, (w, h))[1],
            # 넓은 화면은 배율 1 로 — 2560×2 면 한 장이 몇 MB 다
            "scale": 1 if SIZE.get(name, (w, h))[0] >= 2000 else 2,
            "mobile": bool(entry),
        })
        paths.append(dst)

    f = OUT / "_shot_spec.json"
    f.write_text(json.dumps({"shots": spec}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run(["node", str(ROOT / "brand" / "shot.mjs"), str(f)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600)
    if r.returncode:
        print((r.stdout or "") + (r.stderr or ""))
        raise SystemExit("찍지 못했다")
    f.unlink(missing_ok=True)
    return paths


def sheet(paths, cols: int = 4, name: str = "screens.png") -> pathlib.Path:
    gap, pad = 12, 26
    ims = [(Image.open(p), label) for p, label in paths if p.exists()]
    if not ims:
        raise SystemExit("붙일 사진이 없다")

    # 배율 2로 찍으므로 줄여 붙인다. 폭은 첫 장 기준으로 통일하고 세로는 비율대로 —
    # **크기가 같다고 가정하면 안 된다.** 긴 화면은 세로를, 넓은 화면은 폭을 달리 찍는다(SIZE)
    cw = ims[0][0].width // 2
    def fit(im):
        h = max(1, round(im.height * cw / im.width))
        return im.resize((cw, h), Image.LANCZOS)
    ims = [(fit(im), label) for im, label in ims]

    rows = (len(ims) + cols - 1) // cols
    rh = [max(im.height for im, _ in ims[r * cols:(r + 1) * cols]) for r in range(rows)]
    sh = Image.new("RGB", (cols * cw + (cols - 1) * gap,
                           sum(h + pad for h in rh) + (rows - 1) * gap), (255, 255, 255))
    from PIL import ImageDraw, ImageFont
    d = ImageDraw.Draw(sh)
    # PIL 기본 폰트는 한글을 못 그린다 — 시트 라벨이 두부가 된다
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\malgun.ttf", 14)
    except OSError:
        font = None
    for k, (im, label) in enumerate(ims):
        r, c = k // cols, k % cols
        x = c * (cw + gap)
        y = sum(rh[i] + pad + gap for i in range(r))
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
        shoot_all(SHOTS)
        m_made, d_made = [], []
        for (name, entry, _h, label), path in zip(SHOTS, [OUT / (n + ".png")
                                                          for n, *_ in SHOTS]):
            ok = path.exists() and path.stat().st_size > 3000
            print("  %-10s %-16s %s" % (name, label, "찍음" if ok else "!! 실패"))
            if ok:
                (m_made if entry else d_made).append((path, label))
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
