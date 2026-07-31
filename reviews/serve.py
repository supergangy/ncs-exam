# -*- coding: utf-8 -*-
"""후기 수집기 — 브라우저 북마클릿이 보낸 본문을 받아 바로 적재한다.

    python reviews/serve.py --org 건보

띄워 두고, 카페 후기 글을 연 상태에서 북마클릿을 누르면 그 글이 DB로 들어간다.
로그인·세션·봇 우회는 일절 하지 않는다. 이미 열려 있는 페이지의 본문을 받을 뿐이다.

북마클릿 코드는 서버를 띄우면 콘솔에 찍힌다. 브라우저 즐겨찾기에 한 번만 등록하면 된다.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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
var ds=['.article_info .date','.ArticleTool .date','.date','.se_publishDate','.post_date'],dt='';
for(var j=0;j<ds.length;j++){var n=d.querySelector(ds[j]);
 if(n&&/20\\d\\d/.test(n.innerText)){dt=n.innerText.trim();break;}}
var t=(d.title||'')+'\\n작성일 '+dt+'\\n'+e.innerText;
fetch('http://127.0.0.1:%PORT%/ingest',{method:'POST',mode:'cors',
 headers:{'Content-Type':'text/plain;charset=UTF-8'},body:t})
.then(function(r){return r.text()}).then(function(m){alert(m)})
.catch(function(){alert('수집기가 꺼져 있습니다. python reviews/serve.py --org <기관>')});
})();"""


# 붙여넣기보다 드래그가 확실하다. 브라우저에 따라 주소창 붙여넣기는 javascript: 를 지운다.
INSTALL_PAGE = """<!doctype html><meta charset="utf-8">
<title>후기 수집기</title>
<style>
 body{font:15px/1.75 'Malgun Gothic',sans-serif;max-width:680px;margin:48px auto;padding:0 20px;color:#222}
 h1{font-size:21px;margin:0 0 4px} .sub{color:#666;margin:0 0 12px}
 h2{font-size:16px;margin:34px 0 10px;padding-top:18px;border-top:1px solid #e5e5e5}
 .step{margin:14px 0 14px 0}
 .num{display:inline-block;width:22px;height:22px;line-height:22px;text-align:center;
      background:#222;color:#fff;border-radius:50%;font-size:13px;font-weight:700;margin-right:8px}
 .bm{display:inline-block;padding:11px 22px;background:#03c75a;color:#fff;
     border-radius:6px;text-decoration:none;font-weight:700;cursor:grab;font-size:15px}
 .bm:active{cursor:grabbing}
 .hint{color:#666;font-size:13.5px;margin:6px 0 0 30px}
 code,kbd{background:#f1f3f5;padding:2px 6px;border-radius:3px;font-size:13px;
     font-family:Consolas,monospace}
 kbd{border:1px solid #ccc;border-bottom-width:2px}
 .bar{margin:14px 0;border:1px dashed #bbb;border-radius:6px;padding:0}
 .bar .chrome{background:#f1f3f5;border-bottom:1px solid #ddd;padding:7px 12px;font-size:13px;color:#555}
 .bar .body{padding:26px 12px;text-align:center;color:#aaa;font-size:13px}
 .arrow{font-size:22px;color:#03c75a;margin:0 0 0 96px}
 details{margin-top:12px;background:#fafafa;border:1px solid #e5e5e5;border-radius:6px;padding:12px 16px}
 summary{cursor:pointer;font-weight:700;font-size:14px}
 textarea{width:100%;height:80px;margin-top:10px;font-family:Consolas,monospace;font-size:11px;
     border:1px solid #ddd;border-radius:4px;padding:8px;box-sizing:border-box}
 .now{margin-top:30px;padding:12px 16px;background:#f7f7f7;border-radius:6px;font-size:14px}
 .sum{margin:0 0 14px;padding:10px 14px;background:#eef7f1;border-radius:6px;font-size:14px}
 table.rec{width:100%;border-collapse:collapse;font-size:13.5px}
 table.rec th,table.rec td{border-bottom:1px solid #eee;padding:7px 8px;text-align:left;
   vertical-align:top}
 table.rec th{background:#fafafa;font-weight:700;color:#555;white-space:nowrap}
 table.rec td.n{color:#999;white-space:nowrap}
 .kw{margin:4px 0 0;font-size:12.5px;color:#555}
 .kw summary{cursor:pointer;color:#03723a}
 .kw b{color:#222}
 .warn{color:#b45309}
</style>
<h1>필기후기 수집기</h1>
<p class="sub">지금 <b>%ORG%</b> 후기를 받는 중입니다. 누적 <b>%N%</b>건.</p>

<h2>설치 — 최초 한 번만</h2>

<div class="step"><span class="num">1</span>
 <b>즐겨찾기 바를 먼저 켜십시오.</b> <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>B</kbd>
 <div class="hint">브라우저 주소창 바로 아래에 가로줄이 하나 생깁니다. 이미 보이면 넘어가십시오.</div>
</div>

<div class="step"><span class="num">2</span>
 <b>아래 초록 버튼을 마우스로 꾹 눌러 잡은 채, 그 즐겨찾기 바 위로 끌어다 놓으십시오.</b>
 <div class="hint">클릭이 아니라 <b>드래그</b>입니다. 파일을 폴더로 옮기듯 끌어 올리면 됩니다.</div>
</div>

<div class="bar">
  <div class="chrome">⬆ 여기가 즐겨찾기 바입니다 — 이 줄 위로 끌어다 놓으십시오</div>
  <div class="body">
    <div class="arrow">↑</div>
    <a class="bm" href="%BM%">후기 담기</a>
  </div>
</div>

<div class="step"><span class="num">3</span>
 즐겨찾기 바에 <b>후기 담기</b>가 생겼으면 설치 끝입니다.
</div>

<details>
 <summary>드래그가 잘 안 되면 — 직접 등록하기</summary>
 <p style="font-size:14px;margin:10px 0 0">
  <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>O</kbd> 로 즐겨찾기 관리자를 열고
  <b>새 북마크 추가</b> → 이름은 <code>후기 담기</code>, URL 칸에 아래를 통째로 붙여넣으십시오.<br>
  <span style="color:#666">주소창에 붙여넣으면 안 됩니다. 브라우저가 <code>javascript:</code> 를 지웁니다.</span>
 </p>
 <textarea readonly onclick="this.select()">%BMRAW%</textarea>
</details>

<h2>사용</h2>
<p>카페에서 후기 글을 열고, 즐겨찾기 바의 <b>후기 담기</b>를 누르면 끝입니다.
 알림창에 적재 결과가 뜹니다. 같은 글을 두 번 눌러도 걸러집니다.</p>

<div class="now">
 다른 기관을 모으려면 수집기를 끄고 <code>python reviews/serve.py --org 한전</code> 처럼 다시 띄우십시오.<br>
 <b>즐겨찾기는 그대로 씁니다. 기관은 수집기가 정합니다.</b>
</div>

<h2>수집 기록</h2>
<p class="sub" style="margin-bottom:14px">
 <b>담는 즉시 분류·저장됩니다.</b> 양식·출제 키워드·난이도까지 읽어
 <code>reviews/raw/&lt;기관&gt;/</code> 에 원문을, <code>reviews/db.json</code> 에 분류 결과를 넣습니다.
 따로 가공할 것이 없습니다. &nbsp;<a href="/">새로고침</a>
</p>
%RECORDS%"""

EMPTY_RECORDS = """<p style="padding:20px;background:#fafafa;border-radius:6px;color:#666">
아직 담은 후기가 없습니다. 위 즐겨찾기를 설치하고 후기 글에서 눌러 보십시오.</p>"""


def esc(s) -> str:
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_records(db: list[dict], limit: int = 20) -> str:
    """지금까지 담은 후기를 최근순으로 보여 준다."""
    if not db:
        return EMPTY_RECORDS

    by_org = Counter(r["org"] for r in db)
    unknown = sum(1 for r in db if not r.get("term") and not r.get("date"))
    summary = (f"총 <b>{len(db)}건</b> &nbsp;·&nbsp; "
               + " &nbsp;·&nbsp; ".join(f"{esc(o)} {c}건" for o, c in by_org.most_common()))
    if unknown:
        summary += (f'<br><span class="warn">시행 시기를 모르는 후기 {unknown}건 — '
                    "같은 글을 다시 담으면 게시일이 채워집니다.</span>")

    rows = sorted(db, key=lambda r: r.get("ingested_at") or "", reverse=True)[:limit]
    out = [f'<p class="sum">{summary}</p>', '<table class="rec">',
           "<tr><th>담은 시각</th><th>기관</th><th>시행</th><th>직렬</th>"
           "<th>난이도</th><th>소재</th></tr>"]
    for r in rows:
        kw = r.get("keywords") or {}
        n_kw = sum(len(v) for v in kw.values())
        cell = f"{n_kw}개" if n_kw else "—"
        if kw:
            parts = "".join(
                f"<div><b>{esc(a)}</b> {esc(' · '.join(ws))}</div>" for a, ws in kw.items())
            cell = (f'<details class="kw"><summary>{n_kw}개</summary>{parts}</details>')
        out.append(
            f'<tr><td class="n">{esc((r.get("ingested_at") or "")[5:])}</td>'
            f"<td>{esc(r.get('org'))}</td>"
            f"<td>{esc(r.get('term') or r.get('date') or '—')}</td>"
            f"<td>{esc(r.get('track') or '—')}</td>"
            f"<td>{esc(r.get('difficulty') or '—')}</td>"
            f"<td>{cell}</td></tr>")
    out.append("</table>")
    if len(db) > limit:
        out.append(f'<p class="sub" style="margin-top:10px">최근 {limit}건만 표시했습니다. '
                   "전체는 <code>python reviews/report.py --matrix</code></p>")
    return "\n".join(out)


class Handler(BaseHTTPRequestHandler):
    org = "건보"

    def do_GET(self):                                        # noqa: N802
        db = ingest.load_db()
        n = sum(1 for r in db if r["org"] == self.org)
        raw = BOOKMARKLET.replace("%PORT%", str(self.server.server_port)).replace("\n", "")
        page = (INSTALL_PAGE.replace("%ORG%", self.org).replace("%N%", str(n))
                .replace("%BM%", raw.replace('"', "&quot;"))
                .replace("%BMRAW%", raw.replace("&", "&amp;").replace("<", "&lt;"))
                .replace("%RECORDS%", render_records(db)))
        body = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
    ap.add_argument("--open", action="store_true", help="설치 페이지를 바로 연다")
    args = ap.parse_args()

    Handler.org = args.org
    url = f"http://127.0.0.1:{args.port}"
    print(f"[수집기] {args.org} 후기를 받습니다.")
    print(f"[설치] 브라우저로 {url} 를 여십시오.")
    print("       초록 버튼을 즐겨찾기 바로 끌어다 놓으면 끝입니다 (최초 1회).")
    print("       이후 후기 글을 열고 그 즐겨찾기를 누르면 적재됩니다.")
    print("[종료] Ctrl+C\n")
    if args.open:
        import webbrowser
        webbrowser.open(url)

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
