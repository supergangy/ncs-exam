/** 검색 — 문항의 **모든 글**을 본다.
 *
 *  좁게 잡으면 조용히 빠진다. 「정규화」가 유형 이름에만 있는 문항이 그랬다.
 *  먼저 걸린 곳을 함께 돌려주어 어디서 잡혔는지 보이게 한다.
 *
 *  app.js 의 것은 `DB` 전역을 직접 봤다. 여기서는 **인자로 받는다** —
 *  그래야 인공 문항으로 시험할 수 있다.
 */
import { plain, CIRC } from './text.js';

/** 걸린 자리 앞뒤를 잘라 보여 준다 */
function around(s, n, pad = 24, len = 70) {
  const t = plain(s);
  const at = t.toLowerCase().indexOf(n);
  if (at < 0) return t.slice(0, len);
  return (at > pad ? '…' : '') + t.slice(Math.max(0, at - pad), at + len - pad).trim();
}

/**
 * @param q    찾는 말
 * @param db   { items, kwName(k), passage(i) }
 * @returns    [{ it, where, snip }] — 먼저 걸린 곳 하나만
 */
export function search(q, db) {
  const n = String(q || '').trim().toLowerCase();
  if (!n) return [];
  const has = s => plain(s).toLowerCase().includes(n);
  const cut = s => around(s, n);
  const hits = [];

  for (const it of db.items) {
    if (has(it.st)) { hits.push({ it, where: '발문' }); continue; }

    const ci = (it.ch || []).findIndex(has);
    if (ci >= 0) { hits.push({ it, where: `선지 ${CIRC[ci]}`, snip: cut(it.ch[ci]) }); continue; }

    if (has(it.ty) || has(it.sj)) {
      hits.push({ it, where: '분류', snip: `${it.sj} · ${it.ty}` }); continue;
    }
    const kw = (it.kw || []).find(k => plain(db.kwName(k)).toLowerCase().includes(n));
    if (kw != null) { hits.push({ it, where: '키워드', snip: db.kwName(kw) }); continue; }

    if (it.mt && has(it.mt)) { hits.push({ it, where: '자료', snip: cut(it.mt) }); continue; }
    if (it.pg != null && has(db.passage(it.pg).body)) {
      hits.push({ it, where: '지문', snip: cut(db.passage(it.pg).body) }); continue;
    }
    if (it.ex && has(it.ex)) { hits.push({ it, where: '해설', snip: cut(it.ex) }); continue; }

    const ei = (it.ea || []).findIndex(has);
    if (ei >= 0) { hits.push({ it, where: '선지 단평', snip: cut(it.ea[ei]) }); }
  }
  return hits;
}

/** 찾은 말을 세 토막으로 돌려준다 — `[앞, 걸린 것, 뒤]`.
 *
 *  app.js 는 `<mark>` 를 문자열로 붙였다. React 는 그러면 태그가 글자로 나오므로
 *  **토막만 주고 감싸는 것은 화면이 한다.** 이스케이프도 화면이 알아서 한다.
 */
export function split(text, q) {
  const s = plain(text);
  const t = String(q || '');
  if (!t) return [s, '', ''];
  const i = s.toLowerCase().indexOf(t.toLowerCase());
  if (i < 0) return [s, '', ''];
  return [s.slice(0, i), s.slice(i, i + t.length), s.slice(i + t.length)];
}
