/** 키워드 묶기와 키워드 묶음 — 화면 없이 검사한다.
 *
 *     node --test web/test/
 *
 *  마지막 묶음은 **실제 bank.json** 을 읽는다. 인공 데이터로는
 *  「과목을 가로지르는 키워드가 7개」 같은 것을 알 수 없다.
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { group, narrow, tally } from '../src/core/keywords.js';
import { wrap } from '../src/data/bank.js';
import { makePool } from '../src/data/pool.js';
import { createStore, memory } from '../src/core/store.js';

const fake = {
  keywords: [{ t: '프로세스', n: 3 }, { t: '충돌', n: 2 }, { t: '안 붙은 것', n: 0 },
             { t: '해시', n: 1 }],
  items: [
    { id: 'a', sj: '운영체제', ty: 'x', kw: [0] },
    { id: 'b', sj: '운영체제', ty: 'x', kw: [0] },
    { id: 'c', sj: '운영체제', ty: 'x', kw: [0, 1] },
    { id: 'd', sj: '정보보안', ty: 'y', kw: [1, 3] },
    { id: 'e', sj: '수리능력', ty: 'z' },              // kw 칸이 아예 없다
  ],
};

test('문항에 붙지 않은 키워드는 세우지 않는다 — 눌러도 빈 목록이다', () => {
  const g = group(fake);
  const names = g.flatMap(x => x.keys.map(k => k.t));
  assert.ok(!names.includes('안 붙은 것'), names.join(','));
  assert.equal(tally(g).keys, 3);
});

test('개수는 표를 믿지 않고 문항에서 다시 센다', () => {
  const g = group({ ...fake, keywords: [{ t: '프로세스', n: 999 }] });
  assert.equal(g[0].keys[0].n, 3);          // 표의 999 가 아니다
});

test('가장 많은 과목 밑에 둔다 — 문항 순서상 첫 번째가 아니다', () => {
  // 「충돌」은 운영체제 1 · 정보보안 1 로 같다 → 이름 순으로 갈린다(운영체제)
  // 「해시」는 정보보안에만 있다
  const g = group(fake);
  const at = t => g.find(x => x.keys.some(k => k.t === t)).sj;
  assert.equal(at('프로세스'), '운영체제');
  assert.equal(at('해시'), '정보보안');
});

test('가로지르는 것에 표를 남긴다 (spans)', () => {
  const g = group(fake);
  const k = g.flatMap(x => x.keys);
  assert.equal(k.find(x => x.t === '충돌').spans, 2);
  assert.equal(k.find(x => x.t === '프로세스').spans, 0);
});

test('kw 칸이 없는 문항에도 터지지 않는다', () => {
  assert.doesNotThrow(() => group({ keywords: fake.keywords, items: [{ id: 'x', sj: 'a' }] }));
  assert.deepEqual(group({ keywords: [], items: [] }), []);
});

test('한 글자로는 좁히지 않는다 — 326개가 다 걸린다', () => {
  const g = group(fake);
  assert.equal(tally(narrow(g, '충')).keys, tally(g).keys);
  assert.equal(tally(narrow(g, '충돌')).keys, 1);
  assert.equal(tally(narrow(g, '없는말')).keys, 0);
});

test('과목 문항 수는 겹치는 것을 한 번만 센다', () => {
  // 운영체제 — 프로세스 3개(a·b·c) + 충돌 1개(c). c 가 겹치므로 4가 아니라 3이다
  const g = group(fake);
  assert.equal(g.find(x => x.sj === '운영체제').n, 3);
});

test('좁힌 뒤에도 문항 수를 다시 센다 — 전체 수를 남기면 거짓말이 된다', () => {
  const g = narrow(group(fake), '충돌');
  assert.equal(g.length, 1);
  assert.equal(g[0].keys.length, 1);
  assert.equal(g[0].n, 1, '충돌은 운영체제에서 1개다 (전체 3이 아니다)');
});

test('좁힌 뒤 빈 과목은 남기지 않는다', () => {
  const g = narrow(group(fake), '해시');
  assert.equal(g.length, 1);
  assert.equal(g[0].sj, '정보보안');
});

// ── 키워드 묶음 주소 ─ 배포본과 같아야 한다 ────────────────────────
test('#/q?kw=1 이 그 키워드의 문항만 준다', () => {
  const db = wrap({ ...fake, n: fake.items.length });
  const st = createStore(memory()).load();
  const p = makePool(db, st, 'kw=1');
  assert.equal(p.key, 'kw=1');
  assert.equal(p.title, '충돌');
  assert.deepEqual(p.items.map(i => i.id), ['c', 'd']);
});

test('kw=0 도 묶음이다 — 첨자 0 을 「없음」으로 보면 안 된다', () => {
  const db = wrap({ ...fake, n: fake.items.length });
  const st = createStore(memory()).load();
  const p = makePool(db, st, 'kw=0');
  assert.equal(p.title, '프로세스');
  assert.equal(p.items.length, 3);
});

test('없는 첨자는 빈 묶음 — 터지지 않는다', () => {
  const db = wrap({ ...fake, n: fake.items.length });
  const st = createStore(memory()).load();
  assert.equal(makePool(db, st, 'kw=99').items.length, 0);
  assert.equal(makePool(db, st, 'kw=abc').items.length, 0);
});

// ── 실제 데이터 ────────────────────────────────────────────────────
test('실제 bank.json 의 키워드를 묶는다', () => {
  const bank = JSON.parse(readFileSync(new URL('../../app/data/bank.json', import.meta.url),
                                       'utf8'));
  const db = wrap(bank);
  const g = group(db);
  const t = tally(g);

  // 표에 있는 것이 전부 문항에 붙어 있다 (지금 배포본은 326/326)
  assert.equal(t.keys, db.keywords.length,
               `표 ${db.keywords.length}개 중 ${t.keys}개만 문항에 붙어 있다`);

  // 이름이 글자로 나온다 — 객체가 새면 목록이 '[object Object]' 로 찬다
  for (const k of g.flatMap(x => x.keys).slice(0, 50)) {
    assert.equal(typeof k.t, 'string');
    assert.ok(k.t.length > 0 && !k.t.includes('object'), k.t);
    assert.ok(k.n > 0, k.t + ' 가 0개다');
  }

  // 과목 문항 수가 그 과목의 실제 문항 수를 넘지 않는다 —
  // 키워드별 수를 그냥 더하면 넘는다 (전자계산기구조가 118개로 나왔다)
  for (const x of g) {
    const real = db.byArea(x.sj).length;
    assert.ok(x.n <= real, `${x.sj} — 키워드 문항 ${x.n} > 과목 문항 ${real}`);
  }

  // 어느 키워드를 눌러도 문항이 나온다
  const st = createStore(memory()).load();
  for (const k of g.flatMap(x => x.keys).slice(0, 30)) {
    const p = makePool(db, st, 'kw=' + k.idx);
    assert.equal(p.items.length, k.n, `${k.t} — 목록 ${k.n} vs 묶음 ${p.items.length}`);
  }
});
