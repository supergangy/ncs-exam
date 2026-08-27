/** 순수 로직 검사 — **브라우저 없이 돈다.**
 *
 *     node --test web/test/
 *
 *  Flutter 판의 `dart run tool/check_*.dart` 와 같은 규율이다 —
 *  화면을 볼 수 없는 환경이므로 볼 수 없는 것을 코드로 대신 본다.
 *  마지막 묶음은 **실제 bank.json** 을 읽는다. 인공 문항만으로는 모자란다.
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { plain, stripLead, mmss, CIRC } from '../src/core/text.js';
import { schedule, fresh, due, untilText, DAY, AGAIN } from '../src/core/srs.js';
import { search, split } from '../src/core/search.js';
import { progress, apply, FILTERS } from '../src/core/progress.js';
import { choiceStates, gradeOne, gradeAll, byArea, shuffle, CH, MAX_MS }
  from '../src/core/grade.js';
import { createStore, memory } from '../src/core/store.js';
import { group, narrow, tally } from '../src/core/keywords.js';
import { wrap } from '../src/data/bank.js';
import { makePool } from '../src/data/pool.js';

// ── 글자 ─ 두 번 물린 자리다. 회귀로 못 박는다 ──────────────────────
test('문자 참조를 푼다 — 「보기」 꺾쇠가 글자로 나오면 안 된다', () => {
  assert.equal(plain('다음 &lt;보기&gt; 중'), '다음 <보기> 중');
  assert.equal(plain('가&nbsp;나'), '가 나');
});

test('인라인 태그는 붙여서 지운다 — 제곱이 「cm 2」가 되면 안 된다', () => {
  assert.equal(plain('3cm<sup>2</sup>'), '3cm2');
  assert.equal(plain('<u>밑줄</u>과 <strong>굵게</strong>'), '밑줄과 굵게');
  assert.equal(plain('<p>가</p><p>나</p>'), '가 나');   // 블록은 띄운다
});

test('선지 기호를 뗀다', () => {
  assert.equal(stripLead('① (정답) 가'), '(정답) 가');
  assert.equal(stripLead('정답 아님'), '정답 아님');
});

test('시간 표기', () => {
  assert.equal(mmss(2700000), '45:00');
  assert.equal(mmss(-5), '00:00');
});

// ── 복습 일정 ──────────────────────────────────────────────────────
test('맞히면 1 → 3 → 벌어진다', () => {
  let s = null;
  s = schedule(s, true, 0); assert.equal(s.i, 1);
  s = schedule(s, true, 0); assert.equal(s.i, 3);
  s = schedule(s, true, 0); assert.ok(s.i > 3);
  assert.equal(s.due, s.i * DAY);
});

test('틀리면 처음으로 돌아가고 10분 뒤 다시 뜬다', () => {
  const s = schedule({ e: 2.5, i: 30, due: 0 }, false, 1000);
  assert.equal(s.i, 0);
  assert.equal(s.due, 1000 + AGAIN);
});

test('용이도는 1.3~2.8 로 묶인다 — 아래로 열면 한 문항이 영원히 뜬다', () => {
  let s = fresh();
  for (let i = 0; i < 30; i++) s = schedule(s, false, 0);
  assert.equal(s.e, 1.3);
  for (let i = 0; i < 30; i++) s = schedule(s, true, 0);
  assert.equal(s.e, 2.8);
});

test('받은 상태를 고치지 않는다', () => {
  const before = { e: 2.5, i: 0, due: 0 };
  schedule(before, true, 0);
  assert.deepEqual(before, { e: 2.5, i: 0, due: 0 });
});

test('안 푼 것은 복습 대상이 아니다', () => {
  const items = [{ id: 'a' }, { id: 'b' }];
  assert.deepEqual(due({ a: { due: 0 } }, items, 100), ['a']);
});

test('하루 미만을 「1일 뒤」라고 하지 않는다 — 화면에 그렇게 나와서 고쳤다', () => {
  const now = 1000;
  assert.equal(untilText({ due: now + AGAIN }, now), '10분 뒤');
  assert.equal(untilText({ due: now + 3 * 3600000 }, now), '3시간 뒤');
  assert.equal(untilText({ due: now + 3 * DAY }, now), '3일 뒤');
  assert.equal(untilText({ due: now - 5 }, now), '지금');
  assert.equal(untilText({ due: now + 500 }, now), '곧');
  assert.equal(untilText(null, now), null);
});

// ── 채점 ───────────────────────────────────────────────────────────
test('선지 다섯 상태', () => {
  assert.deepEqual(choiceStates(3, 2, false, 5),
    [CH.idle, CH.pick, CH.idle, CH.idle, CH.idle]);
  assert.deepEqual(choiceStates(3, 2, true, 5),
    [CH.plain, CH.wrong, CH.right, CH.plain, CH.plain]);
});

test('소요 시간은 10분으로 자른다', () => {
  assert.equal(gradeOne({ an: 1 }, 1, 999999999).ms, MAX_MS);
  assert.equal(gradeOne({ an: 1 }, 1, null).ms, null);
});

test('회차 제출 — 고르지 않은 것은 오답이다', () => {
  const items = [{ id: 'a', an: 1 }, { id: 'b', an: 2 }, { id: 'c', an: 3 }];
  const r = gradeAll(items, [1, 5, null]);
  assert.equal(r.right, 1);
  assert.equal(r.blank, 1);
  assert.equal(r.rate, 33);
  assert.ok(r.marks[2].blank && !r.marks[2].ok);
});

test('영역별 성적', () => {
  const items = [{ id: 'a', an: 1, sj: '수리' }, { id: 'b', an: 2, sj: '수리' },
                 { id: 'c', an: 3, sj: '의사소통' }];
  const a = byArea(items, gradeAll(items, [1, 1, 3]).marks);
  assert.equal(a[0].area, '수리');
  assert.equal(a[0].rate, 50);
});

test('섞기는 원본을 고치지 않고 원소를 잃지 않는다', () => {
  const src = [1, 2, 3, 4, 5];
  const out = shuffle(src);
  assert.deepEqual(src, [1, 2, 3, 4, 5]);
  assert.deepEqual([...out].sort(), src);
});

// ── 검색 ───────────────────────────────────────────────────────────
const DB = {
  items: [
    { id: 'a', st: '다음 &lt;보기&gt; 중 옳은 것은?', ch: ['가', '나'],
      ty: '자료해석', sj: '수리능력', kw: [1] },
    { id: 'b', st: '평균은?', ch: ['3cm<sup>2</sup>', '4'],
      ty: '응용수리', sj: '수리능력', kw: [2], ex: '표준편차로 푼다' },
  ],
  kwName: k => ({ 1: '비중', 2: '정규화' })[k],
  passage: () => ({ body: '' }),
};

test('발문·선지·분류·키워드·해설 어디서든 걸린다', () => {
  const cases = [['보기', 'a', '발문'], ['cm2', 'b', '선지 ①'],
                 ['자료해석', 'a', '분류'], ['정규화', 'b', '키워드'],
                 ['표준편차', 'b', '해설']];
  for (const [q, id, where] of cases) {
    const h = search(q, DB);
    assert.equal(h.length, 1, q + ' 가 ' + h.length + '건');
    assert.equal(h[0].it.id, id);
    assert.equal(h[0].where, where);
  }
});

test('빈 검색어는 아무것도 돌려주지 않는다', () => {
  assert.deepEqual(search('', DB), []);
  assert.deepEqual(search('   ', DB), []);
});

test('걸린 말을 세 토막으로 준다 — 태그를 문자열로 붙이지 않는다', () => {
  assert.deepEqual(split('다음 &lt;보기&gt; 중', '보기'), ['다음 <', '보기', '> 중']);
  assert.deepEqual(split('없다', 'zz'), ['없다', '', '']);
});

// ── 진도·필터 ──────────────────────────────────────────────────────
test('진도와 정답률', () => {
  const last = id => ({ a: { k: 1 }, b: { k: 0 } })[id] || null;
  const p = progress([{ id: 'a' }, { id: 'b' }, { id: 'c' }], last);
  assert.deepEqual([p.n, p.done, p.ok, p.rate], [3, 2, 1, 50]);
});

test('네 가지 필터', () => {
  const items = [{ id: 'a' }, { id: 'b' }, { id: 'c' }];
  const ctx = { last: id => ({ a: { k: 1 }, b: { k: 0 } })[id] || null,
                marked: id => id === 'c' };
  const got = Object.fromEntries(
    FILTERS.map(f => [f, apply(f, items, ctx).map(i => i.id).join('')]));
  assert.deepEqual(got, { all: 'abc', untried: 'c', wrong: 'b', marked: 'c' });
});

// ── 기록 ───────────────────────────────────────────────────────────
function store(t0 = 1700000000000) {
  let t = t0;
  const io = memory();
  const S = createStore({ get: io.get, set: io.set, now: () => t }).load();
  return { S, io, at: v => { t = t0 + v; } };
}

test('틀린 것만 오답노트에 남고 다시 맞히면 빠진다', () => {
  const { S } = store();
  S.record('a', 2, false, 5000);
  assert.ok(S.isWrong('a'));
  S.record('a', 1, true, 4000);
  assert.ok(!S.isWrong('a'));
});

test('복습은 시각에 따라 뜬다', () => {
  const { S, at } = store();
  S.record('a', 2, false, 0);
  const items = [{ id: 'a' }];
  assert.deepEqual(S.due(items), []);
  at(11 * 60 * 1000);
  assert.deepEqual(S.due(items), ['a']);
});

test('깨진 백업은 아무것도 바꾸지 않는다', () => {
  const { S } = store();
  S.record('a', 1, true, 0);
  const bads = [null, undefined, 'x', {}, { app: 'other', data: {} },
                { data: { att: [] } }, { data: null }];
  for (const bad of bads) {
    const r = S.importAll(bad);
    assert.ok(!r.ok, JSON.stringify(bad) + ' 를 받았다');
    assert.ok(r.why);
  }
  assert.ok(S.tried('a'), '거절했는데 기록이 사라졌다');
});

test('백업 왕복 — 내보낸 것을 그대로 되살린다', () => {
  const { S, io } = store();
  S.record('a', 2, false, 5000);
  S.record('b', 1, true, 3000);
  S.toggle('c', 'b');
  const env = JSON.parse(JSON.stringify(S.exportMap('2026-08-18')));
  const snap = JSON.stringify(S.d);
  S.reset();
  assert.ok(!S.tried('a'));
  const r = S.importAll(env);
  assert.ok(r.ok, r.why);
  assert.equal(JSON.stringify(S.d), snap);
  assert.ok(io.get('ncsbank.v1.prev'), '되돌릴 여지를 안 남겼다');
});

test('저장한 것을 다시 읽는다', () => {
  const io = memory();
  const A = createStore({ get: io.get, set: io.set }).load();
  A.record('a', 1, true, 0);
  const B = createStore({ get: io.get, set: io.set }).load();
  assert.ok(B.tried('a'));
});

// ── 묶음 마침 ─ 새로 고쳐도 같은 값이 나와야 한다 ──────────────────
test('passOf — since 이전의 시도는 세지 않는다', () => {
  let t = 1000;
  const S = createStore({ ...memory(), now: () => t }).load();
  S.record('a', 1, false, 5000);            // 지난주에 틀렸다
  const since = t = 100000;                 // 여기서 묶음을 잡았다
  assert.equal(S.passOf('a', since), null, '이전 시도가 새 나왔다');

  t = 100500; S.record('a', 2, false, 500);
  t = 101000; S.record('a', 3, true, 700);
  const p = S.passOf('a', since);
  assert.equal(p.n, 2, '이번 시도만 센다');
  assert.equal(p.ok, true, '마지막이 정답이면 맞음이다');
  assert.equal(p.ms, 1200, '이번 시도들의 시간만 더한다');
});

test('passOf — 다시 풀어 맞히면 「이번엔 맞음」이지만 오답노트에서도 빠진다', () => {
  let t = 1000;
  const S = createStore({ ...memory(), now: () => t }).load();
  t = 2000; S.record('a', 1, false, 100);
  t = 3000; S.record('a', 2, true, 100);
  assert.equal(S.passOf('a', 1500).ok, true);
  assert.equal(S.isWrong('a'), false);
});

test('passOf — 시도가 없으면 null. 없는 문항에도 터지지 않는다', () => {
  const S = createStore({ ...memory(), now: () => 5000 }).load();
  assert.equal(S.passOf('없는것', 0), null);
});

// ── 실제 데이터 ─ 인공 문항만으로는 모자라다 ────────────────────────
test('실제 bank.json 으로 돌린다', () => {
  const bank = JSON.parse(readFileSync(new URL('../../app/data/bank.json', import.meta.url), 'utf8'));
  // **`wrap()` 을 쓴다.** 여기에 `{ items, kwName, passage }` 를 손으로 만들어
  // 넣었더니, 실제 `data/bank.js` 의 `kwName` 이 이름 대신 `{ t, n }` 객체를
  // 돌려주는 것을 이 시험이 놓쳤다 — 키워드로는 아무것도 안 걸리는 상태였다.
  // 가짜를 끼우면 검사하는 것은 core 뿐이고, 화면이 쓰는 것은 wrap 이다.
  const db = wrap(bank);
  assert.ok(db.items.length > 700, '문항이 ' + db.items.length + '개뿐이다');

  // 모든 문항의 정답이 선지 범위 안에 있고 발문이 비지 않았다
  for (const it of db.items) {
    assert.ok(it.an >= 1 && it.an <= it.ch.length, it.id + ' 정답 ' + it.an);
    assert.ok(plain(it.st).length > 0, it.id + ' 발문이 비었다');
    // **원문에서** 찾는다. plain 결과에서 찾으면 엔티티를 푼 뒤라
    // 정당한 「&lt;보기&gt;」 23건이 태그로 잡힌다 (SPEC 4절은 태그를 금할 뿐
    // 꺾쇠 글자를 금하지 않는다)
    assert.ok(!/<[a-zA-Z/]/.test(it.st), it.id + ' 발문에 태그가 있다');
  }

  // 검색이 실제로 걸린다 — 흔한 말로 확인
  for (const q of ['비중', '다음', '것은']) {
    assert.ok(search(q, db).length > 0, q + ' 가 한 건도 안 걸린다');
  }

  // 키워드 이름이 **글자**로 나온다. 객체가 새면 '[object Object]' 가 된다
  assert.equal(typeof db.kwName(0), 'string');
  assert.ok(!db.kwName(0).includes('object'), db.kwName(0));
  // 그 이름으로 검색이 걸린다 — kwName 이 객체였을 때 0건이던 자리다
  const kwHit = search(db.kwName(0), db).filter(h => h.where === '키워드');
  assert.ok(kwHit.length > 0, db.kwName(0) + ' 가 키워드로 안 걸린다');

  // 전 문항을 실제로 채점해 본다 — 정답만 고르면 100%
  const all = gradeAll(db.items, db.items.map(i => i.an));
  assert.equal(all.rate, 100);
  assert.equal(all.blank, 0);

  // 아무것도 안 고르면 0% 이고 전부 미기입이다
  const none = gradeAll(db.items, db.items.map(() => null));
  assert.equal(none.rate, 0);
  assert.equal(none.blank, db.items.length);

  // 선지 상태가 문항마다 선지 수와 맞는다
  for (const it of db.items) {
    assert.equal(choiceStates(it.an, 1, true, it.ch.length).length, it.ch.length);
  }
  assert.ok(CIRC.length >= 5);
});
