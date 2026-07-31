# -*- coding: utf-8 -*-
"""후기 수집기 — 브라우저 북마클릿이 보낸 본문을 받아 바로 적재한다.

    python reviews/serve.py --org 건보

띄워 두고, 카페 후기 글을 연 상태에서 북마클릿을 누르면 그 글이 DB로 들어간다.
로그인·세션·봇 우회는 일절 하지 않는다. 이미 열려 있는 페이지의 본문을 받을 뿐이다.

북마클릿 코드는 서버를 띄우면 콘솔에 찍힌다. 브라우저 즐겨찾기에 한 번만 등록하면 된다.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ingest  # noqa: E402

# 페이지에서 본문을 긁어 이 서버로 보내는 한 줄짜리 스크립트.
# iframe(cafe_main) 안에 본문이 있는 경우까지 훑는다.
BOOKMARKLET = """javascript:(function(){
var d=document,f=d.querySelector('iframe#cafe_main');
if(f&&f.contentDocument)d=f.contentDocument;
var s=['.se-main-container','.ArticleContentBox','#postViewArea','.article_viewer','article','body'],e;
for(var i=0;i<s.length;i++){e=d.querySelector(s[i]);if(e&&e.innerText.length>200)break;}
if(!e){alert('본문을 찾지 못했습니다');return;}
var t=(d.title||'')+'\\n'+e.innerText;
fetch('http://127.0.0.1:%PORT%/ingest',{method:'POST',mode:'cors',
 headers:{'Content-Type':'text/plain;charset=UTF-8'},body:t})
.then(function(r){return r.text()}).then(function(m){alert(m)})
.catch(function(){alert('수집기가 꺼져 있습니다. python reviews/serve.py --org <기관>')});
})();"""


class Handler(BaseHTTPRequestHandler):
    org = "건보"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def do_OPTIONS(self):                                    # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):                                       # noqa: N802
        n = int(self.headers.get("Content-Length", 0))
        text = self.rfile.read(n).decode("utf-8", errors="replace")
        try:
            msg = self._store(text)
        except Exception as e:                               # noqa: BLE001
            msg = f"실패: {e}"
        body = msg.encode("utf-8")
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _store(self, text: str) -> str:
        if len(ingest.norm(text)) < 120:
            return "본문이 너무 짧습니다. 글 전체가 보이는 상태에서 눌러 주십시오."

        rec = ingest.parse(text, self.org)
        db = ingest.load_db()
        if any(r["fingerprint"] == rec["fingerprint"] for r in db):
            return f"이미 등록된 글입니다 ({rec['fingerprint']})"

        d = ingest.RAW / self.org
        d.mkdir(parents=True, exist_ok=True)
        stamp = rec["date"] or "날짜미상"
        (d / f"{stamp}_{rec['fingerprint']}.txt").write_text(
            ingest.norm(text), encoding="utf-8")
        db.append(rec)
        ingest.save_db(db)

        mine = sum(1 for r in db if r["org"] == self.org)
        line = (f"[적재] {self.org} {rec['date'] or '날짜미상'} · "
                f"유형 {', '.join(rec['types']) or '-'} · "
                f"소재 {', '.join(rec['topics']) or '-'} · "
                f"난이도 {rec['difficulty'] or '-'}")
        print(line)
        return f"저장했습니다 — {self.org} 누적 {mine}건\n{line}"

    def log_message(self, *a):                               # 접속 로그는 끈다
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", required=True, help="이번에 모을 기관 약칭 (예: 건보)")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()

    Handler.org = args.org
    print(f"[수집기] {args.org} 후기를 받습니다. http://127.0.0.1:{args.port}")
    print("[안내] 아래 한 줄을 브라우저 즐겨찾기 URL로 등록하십시오 (최초 1회).")
    print("       후기 글을 연 상태에서 그 즐겨찾기를 누르면 적재됩니다.\n")
    print(BOOKMARKLET.replace("%PORT%", str(args.port)).replace("\n", ""))
    print("\n[종료] Ctrl+C\n")

    # 로컬 전용. 외부에서 접근할 수 있게 열지 않는다.
    srv = HTTPServer(("127.0.0.1", args.port), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        n = len([r for r in ingest.load_db() if r["org"] == args.org]) \
            if ingest.DB.exists() else 0
        print(f"\n[종료] {args.org} 누적 {n}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
