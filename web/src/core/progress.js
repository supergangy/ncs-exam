/** 진도·정답률 — 목록마다 쓴다.
 *
 *  app.js 는 `Store` 전역을 직접 봤다. 여기서는 **마지막 시도를 주는 함수를 받는다** —
 *  저장소가 무엇이든(localStorage·메모리·시험용 가짜) 같은 계산을 쓴다.
 */

export const pct = (a, b) => b ? Math.round(a / b * 100) : 0;

/** @param last  id → { k: 0|1 } | null */
export function progress(items, last) {
  let done = 0, ok = 0;
  for (const i of items) {
    const l = last(i.id);
    if (l) { done++; if (l.k) ok++; }
  }
  return { n: items.length, done, ok, rate: pct(ok, done), fill: pct(done, items.length) };
}

export function progText(p) {
  if (!p.done) return `${p.n}문항`;
  return `${p.done}/${p.n} · 정답률 ${p.rate}%`;
}

/** 목록 필터 — Flutter 판 `pool_filter.dart` 와 같은 어휘를 쓴다.
 *
 *  **결과가 0인 유형은 감추지 않는다.** 감추면 유형이 사라진 줄 안다 (앱에서 배운 것).
 *  그래서 걸러진 목록만 주고, 흐리게 두는 것은 화면이 판단한다.
 */
export const FILTERS = ['all', 'untried', 'wrong', 'marked'];
export const FILTER_LABEL = {
  all: '전체', untried: '안 푼 것', wrong: '틀린 것', marked: '표시한 것',
};

export function apply(filter, items, { last, marked }) {
  switch (filter) {
    case 'untried': return items.filter(i => !last(i.id));
    case 'wrong': return items.filter(i => { const l = last(i.id); return l && !l.k; });
    case 'marked': return items.filter(i => marked(i.id));
    default: return items;
  }
}
