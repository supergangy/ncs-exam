/** 「무엇을 풀지」를 주소에서 읽어 문항 목록으로 만든다.
 *
 *  ## 아직 안 본 회차는 연습에 내지 않는다
 *
 *  회차 문항은 은행에도 함께 있다. 그대로 두면 **영역 연습이 모의고사를 미리
 *  소진한다** — 의사소통 86문항 중 61개(71%), 문제해결 66%, 수리 59%가 회차
 *  문항이다(2026-08-28 실측). 「수리능력」을 눌러 다섯 문항을 풀었더니 전부
 *  1회차 문항이었다. 그 상태로 며칠 연습하면 시간 재고 앉았을 때 **이미 본
 *  문제**가 되어 회차의 뜻이 사라진다.
 *
 *  그래서 **제출하지 않은 회차의 문항을 연습 목록에서 감춘다.** 제출하면 곧바로
 *  합류한다 — 그때부터는 복습할 것이지 아껴 둘 것이 아니기 때문이다.
 *
 *  설정을 새로 만들지 않았다. 회차를 보기 전에 그 문항을 풀고 싶으면
 *  회차 안내의 **「연습 모드로 풀기」**(`?rd=<tag>`)가 이미 그 길이다.
 *
 *  체를 거치지 않는 것 — **내 기록으로 만든 묶음**이다.
 *  오답노트·복습·표시함은 이미 내가 푼 것이라 감출 이유가 없고,
 *  `id`·`rd` 는 무엇을 열지 내가 대놓고 고른 것이다.
 *
 *  주소는 배포본과 같다 — `#/q?sj=수리능력&ty=자료해석` 처럼 **질의로 묶음을 넘긴다.**
 *  모바일·PC 가 같은 주소를 쓰므로 이 해석도 한 벌이어야 한다. 두 벌이면
 *  한쪽에서 만든 북마크가 다른 쪽에서 다른 문항을 연다.
 *
 *  `db`(읽기)와 `st`(기록)를 받는다. 판단은 없다 — 걸러 내고 세우기만 한다.
 */

/** 아직 제출하지 않은 회차의 tag 들 */
export function lockedRounds(db, st) {
  const out = new Set();
  for (const r of db.rounds || []) {
    if (!st.examHistory(r.tag).length) out.add(r.tag);
  }
  return out;
}

/** 연습에서 보일 문항인가 — `bank.js` 의 조회 함수와 아래 `makePool` 이 함께 쓴다.
 *
 *  **세는 곳과 푸는 곳이 같은 체를 써야 한다.** 홈이 「104문항」이라 적어 놓고
 *  들어가면 43개만 나오는 것이 더 나쁘다.
 */
export function practiceKeep(db, st) {
  const lock = lockedRounds(db, st);
  return it => !it.rd || !lock.has(it.rd);
}

/** @returns { key, title, sub, items } — key 는 「같은 묶음인가」를 보는 값이다 */
export function makePool(db, st, query = '') {
  const q = new URLSearchParams(query || '');
  const get = k => q.get(k) || null;

  const sj = get('sj'), ty = get('ty'), rd = get('rd'), id = get('id'), pool = get('pool');
  const kw = get('kw');
  // 훑어보는 묶음(영역·유형·키워드·전체)에만 건다. 위 머리말을 보라
  const keep = practiceKeep(db, st);

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
             items: Number.isInteger(idx) ? db.byKw(idx, keep) : [] };
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
    return { key: `sj=${sj}&ty=${ty}`, title: ty, sub: sj,
             items: db.byType(sj, ty, keep) };
  }

  if (sj) {
    return { key: 'sj=' + sj, title: sj, sub: '영역 전체', items: db.byArea(sj, keep) };
  }

  return { key: 'all', title: '전체', sub: '', items: db.items.filter(keep) };
}

/** 풀이 화면 주소 */
export function poolHref(params) {
  const q = new URLSearchParams(params).toString();
  return '#/q' + (q ? '?' + q : '');
}
