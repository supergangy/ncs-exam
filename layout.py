# -*- coding: utf-8 -*-
"""펼침면 기준 지면 배치기

실제 시험지는 두 면을 펼쳐 놓고 푼다. 세트문항의 지문과 문항이 펼침을 넘어가면
페이지를 계속 넘겨야 해서, 실전 시험에서 거의 볼 수 없는 형태가 된다.

배치 규칙
  1. 세트문항은 한 면에 통째로 넣는다.
  2. 한 면에 안 들어가는 세트는 **지문을 왼쪽(짝수) 면, 문항을 오른쪽(홀수) 면**에 둔다.
  3. 면 끝에 여백이 남으면 **같은 영역 안에서** 뒤쪽 단독 문항을 끌어올려 채운다.
     영역을 넘나드는 재배치는 하지 않는다.

Chrome이 CSS `break-before: left|right` 를 무시하는 것을 실측으로 확인했으므로
(일반 페이지 넘김으로 처리하고 빈 면도 넣지 않는다), 면 번호를 파이썬에서 직접
계산해 `break-before: page` 를 심는다.
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path

PAGE_H = 990          # A4 297mm − 상하 여백 35mm @96dpi
SAFETY = 12           # 실측 보정 (영역 헤더는 별도 여유를 더한다)
CAP = PAGE_H - SAFETY

_PROBE = """
<style>
/* 화면 렌더 폭을 인쇄 콘텐츠 폭(A4 210mm − 좌우 여백 15mm×2)에 맞춘다.
   맞추지 않으면 줄바꿈이 달라져 높이 실측이 어긋난다. */
html, body { width: 180mm !important; margin: 0 !important; padding: 0 !important; }
.cover, .info, .omr { display: none !important; }
</style>
<script>
/* getBoundingClientRect 는 마진을 제외하고, 인접 마진은 상쇄되기도 한다.
   따라서 형제 블록의 '흐름상 위치 차이'로 실제 점유 높이를 잰다. */
const flow=[];
document.querySelectorAll('.area-header[data-blk], .qset[data-blk]').forEach(e=>{
  const r=e.getBoundingClientRect();
  flow.push({k:e.dataset.blk, t:Math.round(r.top+window.scrollY), h:Math.ceil(r.height)});
});
const inner={};
document.querySelectorAll('.qhead[data-blk], .qbody[data-blk]').forEach(e=>{
  const cs=getComputedStyle(e);
  inner[e.dataset.blk]=Math.ceil(e.getBoundingClientRect().height
      + parseFloat(cs.marginTop) + parseFloat(cs.marginBottom));
});
const d=document.createElement('div');
d.id='__M__';
d.textContent='MEASURE='+JSON.stringify(
  {flow:flow, inner:inner, doch:document.body.scrollHeight});
document.body.appendChild(d);
</script>"""


def measure(html: str, chrome: str, workdir: Path) -> dict:
    """블록별 렌더 높이(px)를 헤드리스 Chrome으로 실측한다."""
    workdir.mkdir(parents=True, exist_ok=True)
    src = workdir / "_measure.html"
    src.write_text(html + _PROBE, encoding="utf-8")
    with tempfile.TemporaryDirectory() as prof:
        r = subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--no-first-run",
             f"--user-data-dir={prof}", "--virtual-time-budget=8000",
             "--dump-dom", src.as_uri()],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=180)
    m = re.search(r"MEASURE=(\{.*\})</div>", r.stdout, re.S)
    if not m:
        raise RuntimeError("높이 실측 실패 — dump-dom 결과에 MEASURE 없음")
    raw = json.loads(m.group(1))

    # 블록 자체 높이(마진 제외)와 블록 사이 간격을 분리한다.
    # 꼬리 마진은 면 끝에서 자리를 차지하지 않으므로 용량 계산에 넣으면 안 된다.
    flow, H, gaps = raw["flow"], {}, []
    for i, e in enumerate(flow):
        H[e["k"]] = e["h"]
        if i + 1 < len(flow):
            g = flow[i + 1]["t"] - (e["t"] + e["h"])
            if e["k"] != "hdr" and flow[i + 1]["k"] != "hdr" and g >= 0:
                gaps.append(g)
    H["hdr"] = max((e["h"] for e in flow if e["k"] == "hdr"), default=0)
    H["_gap"] = round(sum(gaps) / len(gaps)) if gaps else 8
    # 영역 헤더는 앞뒤 마진이 커서 따로 잡는다
    hgaps = [flow[i + 1]["t"] - flow[i]["t"] for i in range(len(flow) - 1)
             if flow[i]["k"] == "hdr"]
    if hgaps:
        # 헤더는 위아래 마진이 커서 실측이 흔들린다. 넉넉히 잡아 넘침을 막는다.
        H["hdr"] = min(hgaps) + 18
    H.update(raw["inner"])
    return H


def plan(blocks, H, start_page, header_h=0, gap=8):
    """블록 순서와 페이지 브레이크를 정한다.

    blocks 각 원소에 pagebreak / spread_break 플래그를 세우고,
    재배치된 순서로 리스트를 돌려준다.
    """
    for b in blocks:
        b["pagebreak"] = False
        b["spread_break"] = False
        b["_h"] = H.get(str(b["blk"]), 0)
        b["_hp"] = H.get(f"{b['blk']}p", 0)
        b["_hq"] = H.get(f"{b['blk']}q", b["_h"])
        b["_set"] = bool(b["passage"]) and len(b["questions"]) > 1
        # 블록이 "movable": False 를 달면 여백 채우기로 끌어올리지 않는다.
        # 짝을 이루는 명제 두 문항이나 같은 기법을 잇달아 묻는 묶음처럼
        # **출제 순서 자체가 설계인 구간**을 지키기 위한 장치다 (D50).
        b["_movable"] = (not b["_set"] and not b["passage"]
                         and b.get("movable", True))

    pool, out = list(blocks), []
    pno, used, seen_area, page_log = start_page, 0, set(), []
    cur = []

    def close():
        nonlocal pno, used, cur
        if cur:
            page_log.append((pno, used, [b["blk"] for b in cur]))
        pno += 1
        used = 0
        cur = []

    while pool:
        b = pool.pop(0)
        hdr = header_h if b["area"] not in seen_area else 0
        first_of_area = b["area"] not in seen_area

        # ── 펼침 세트: 지문을 왼쪽(짝수) 면에 ──────────────────
        if b["_set"] and b["_h"] + hdr > CAP:
            if used:
                close()
            if pno % 2 == 1:                      # 지금이 오른쪽 면이면 한 면 채워 밀어낸다
                f = _filler(pool, CAP - used, b["area"], out and out[-1]["area"])
                if f is not None:
                    g = pool.pop(f)
                    g["pagebreak"] = bool(used == 0 and out)
                    g["_page"], g["_y"] = pno, used
                    out.append(g); cur.append(g); used += g["_h"]
                close()
            b["pagebreak"] = True
            b["spread_break"] = True              # 지문 다음 면으로 문항을 넘긴다
            seen_area.add(b["area"])
            b["_page"], b["_y"] = pno, hdr        # 지문 상자
            b["_qpage"], b["_qy"] = pno + 1, 0    # 문항 상자는 다음 면 맨 위
            out.append(b)
            page_log.append((pno, b["_hp"] + hdr, [f"{b['blk']}지문"]))
            pno += 1
            # 오른쪽(문항) 면은 닫지 않는다. 남는 자리는 같은 영역 뒤쪽 블록으로 채운다.
            used = b["_hq"]
            cur = [{"blk": f"{b['blk']}문항", "_h": b["_hq"], "area": b["area"]}]
            continue

        # ── 일반 블록 ─────────────────────────────────────────
        need = b["_h"] + hdr + (gap if cur else 0)
        if cur and used + need > CAP:
            f = _filler(pool, CAP - used - gap, b["area"], b["area"] if not first_of_area else None)
            if f is not None:
                g = pool.pop(f)
                g["_page"], g["_y"] = pno, used + gap
                out.append(g); cur.append(g); used += g["_h"] + gap
                pool.insert(0, b)                 # 원래 블록은 다음 차례로 되돌린다
                continue
            close()
            b["pagebreak"] = True
        seen_area.add(b["area"])
        b["_page"] = pno
        b["_y"] = used + hdr + (gap if cur else 0)
        out.append(b)
        cur.append(b)
        used += need

    close()
    return out, page_log


def _filler(pool, space, area, restrict_area):
    """같은 영역 안에서 space 에 들어가는, 이동 가능한 뒤쪽 블록 중 가장 큰 것."""
    if space <= 0:
        return None
    best, best_h = None, -1
    for j, v in enumerate(pool):
        if v["area"] != area:
            break                                  # 영역 경계를 넘지 않는다
        if not v["_movable"]:
            continue
        if best_h < v["_h"] <= space:
            best, best_h = j, v["_h"]
    return best


def report(page_log):
    """배치 품질 요약 문자열과 여백 통계."""
    lines, fills = [], []
    for pno, used, ids in page_log:
        side = "L" if pno % 2 == 0 else "R"
        pct = used / CAP * 100
        fills.append(pct)
        bar = "█" * int(pct / 5)
        lines.append(f"  p{pno:>2}({side}) {used:>4}px {pct:>3.0f}% {bar:<20} {','.join(map(str, ids))}")
    avg = sum(fills) / len(fills) if fills else 0
    thin = sum(1 for f in fills if f < 55)
    lines.append(f"  평균 채움 {avg:.0f}% / 55% 미만 면 {thin}개")
    return "\n".join(lines)
