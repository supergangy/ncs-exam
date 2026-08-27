/** 「무엇을 풀지」를 주소에서 읽어 문항 목록으로 만든다.
 *
 *  주소는 배포본과 같다 — `#/q?sj=수리능력&ty=자료해석` 처럼 **질의로 묶음을 넘긴다.**
 *  모바일·PC 가 같은 주소를 쓰므로 이 해석도 한 벌이어야 한다. 두 벌이면
 *  한쪽에서 만든 북마크가 다른 쪽에서 다른 문항을 연다.
 *
 *  `db`(읽기)와 `st`(기록)를 받는다. 판단은 없다 — 걸러 내고 세우기만 한다.
 */

/** @returns { key, title, sub, items } — key 는 「같은 묶음인가」를 보는 값이다 */
export function makePool(db, st, query = '') {
  const q = new URLSearchParams(query || '');
  const get = k => q.get(k) || null;

  const sj = get('sj'), ty = get('ty'), rd = get('rd'), id = get('id'), pool = get('pool');
  const kw = get('kw');

  if (id) {
    const it = db.byId(id);
    return { key: 'id=' + id, title: '문항', sub: it ? `${it.sj} · ${it.ty}` : '',
             items: it ? [it] : [] };
  }

  if (kw !== null && kw !== '') {
    // 키워드 묶음 — 배포본과 같은 주소다 (`#/q?kw=12`). 첨자를 넘긴다.
    //   **이름이 아니라 첨자**인 이유는 이름에 `/`·`+` 가 들어갈 수 있어서다.
    const idx = Number(kw);
    const name = db.kwName(idx);
    return { key: 'kw=' + idx, title: name, sub: '키워드',
             items: Number.isInteger(idx) ? db.byKw(idx) : [] };
  }

  if (pool === 'wrong') {
    // 마지막 시도가 오답인 것만 — 다시 맞히면 여기서 빠진다
    return { key: 'pool=wrong', title: '오답노트', sub: '다시 맞히면 목록에서 빠집니다',
             items: db.items.filter(i => st.isWrong(i.id)) };
  }

  if (pool === 'review') {
    const ids = new Set(st.due(db.items));
    return { key: 'pool=review', title: '복습', sub: 'SM-2 가 정한 오늘 몫',
             items: db.items.filter(i => ids.has(i.id)) };
  }

  if (pool === 'marks') {
    return { key: 'pool=marks', title: '표시해 둔 문항', sub: '',
             items: db.items.filter(i => st.marked(i.id)) };
  }

  if (rd) {
    const r = db.round(rd);
    return { key: 'rd=' + rd, title: r?.title || rd, sub: '연습 모드 — 시간 제한 없이',
             items: db.byRound(rd) };
  }

  if (sj && ty) {
    return { key: `sj=${sj}&ty=${ty}`, title: ty, sub: sj, items: db.byType(sj, ty) };
  }

  if (sj) {
    return { key: 'sj=' + sj, title: sj, sub: '영역 전체', items: db.byArea(sj) };
  }

  return { key: 'all', title: '전체', sub: '', items: db.items };
}

/** 풀이 화면 주소 */
export function poolHref(params) {
  const q = new URLSearchParams(params).toString();
  return '#/q' + (q ? '?' + q : '');
}
