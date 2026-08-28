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
import { plain } from '../src/core/text.js';
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

// ── 연습 풀이 회차를 미리 소진하지 않는다 ──────────────────────────
//   의사소통 86문항 중 61개(71%)가 회차 문항이었다. 그대로 두면 영역 연습만
//   돌려도 모의고사를 다 보게 된다 — 시간 재고 앉을 때 이미 본 문제가 된다.
import { practiceKeep, lockedRounds } from '../src/data/pool.js';

const round = {
  keywords: [],
  rounds: [{ tag: 'rA', title: 'A회' }, { tag: 'rB', title: 'B회' }],
  items: [
    { id: 'p1', sj: '수리능력', ty: '확률' },                  // 은행 문항
    { id: 'p2', sj: '수리능력', ty: '확률' },
    { id: 'a1', sj: '수리능력', ty: '확률', rd: 'rA', no: 1 },  // A회
    { id: 'a2', sj: '수리능력', ty: '확률', rd: 'rA', no: 2 },
    { id: 'b1', sj: '수리능력', ty: '확률', rd: 'rB', no: 1 },  // B회
  ],
};

const stWith = (submitted) => ({
  examHistory: tag => (submitted.includes(tag) ? [{ at: 1, score: 1, n: 1 }] : []),
  last: () => null, marked: () => null, isWrong: () => false,
  due: () => [], solo: () => null,
});

test('응시하지 않은 회차의 문항은 영역 연습에 나오지 않는다', () => {
  const db = wrap({ ...round, n: round.items.length });
  const p = makePool(db, stWith([]), 'sj=수리능력');
  assert.deepEqual(p.items.map(i => i.id), ['p1', 'p2']);
});

test('제출한 회차의 문항은 곧바로 합류한다 — 아껴 둘 것이 아니라 복습할 것이다', () => {
  const db = wrap({ ...round, n: round.items.length });
  const p = makePool(db, stWith(['rA']), 'sj=수리능력');
  assert.deepEqual(p.items.map(i => i.id), ['p1', 'p2', 'a1', 'a2']);
  assert.deepEqual([...lockedRounds(db, stWith(['rA']))], ['rB']);
});

test('회차를 대놓고 고르면 체를 거치지 않는다 — 「연습 모드로 풀기」', () => {
  const db = wrap({ ...round, n: round.items.length });
  const p = makePool(db, stWith([]), 'rd=rA');
  assert.deepEqual(p.items.map(i => i.id), ['a1', 'a2']);
});

test('내 기록으로 만든 묶음은 감추지 않는다 — 틀린 것은 회차 문항이라도 오답노트에', () => {
  const db = wrap({ ...round, n: round.items.length });
  const st = { ...stWith([]), isWrong: id => id === 'a1' };
  assert.deepEqual(makePool(db, st, 'pool=wrong').items.map(i => i.id), ['a1']);
});

test('세는 곳과 푸는 곳이 같은 체를 쓴다 — 「104문항」이라 적고 43개를 내면 안 된다', () => {
  const db = wrap({ ...round, n: round.items.length });
  const st = stWith([]);
  const keep = practiceKeep(db, st);
  const shown = db.areas(keep).find(a => a.area === '수리능력');
  const pool = makePool(db, st, 'sj=수리능력');
  assert.equal(shown.n, pool.items.length);
  assert.equal(shown.types[0].n, makePool(db, st, 'sj=수리능력&ty=확률').items.length);
});

// ── 직렬로 묶는다 — 고르게 하지 않는다 ─────────────────────────────
//   전산직 지원자도 NCS 직업기초를 본다. 둘 중 하나를 감추면 틀린다.
//   섞어 두면 사무직에게 데이터베이스론이, 전산직에게 대인관계능력이
//   한 줄에 뒤섞여 나온다(영역 18개).
const twoTracks = {
  keywords: [],
  tracks: [{ id: 'cs', name: '전산직', sub: '직무 전공' },
           { id: 'ncs', name: 'NCS 직업기초', sub: '직업기초능력' }],
  rounds: [],
  items: [
    { id: 'n1', sj: '수리능력', ty: 'a', tr: 'ncs' },
    { id: 'n2', sj: '수리능력', ty: 'a', tr: 'ncs' },
    { id: 'n3', sj: '의사소통능력', ty: 'b', tr: 'ncs' },
    { id: 'c1', sj: '운영체제', ty: 'c', tr: 'cs' },
  ],
};

test('NCS 를 먼저 둔다 — 모든 지원자가 보는 것이다', () => {
  const db = wrap({ ...twoTracks, n: twoTracks.items.length });
  assert.deepEqual(db.byTrack().map(g => g.tr), ['ncs', 'cs']);
});

test('영역이 제 직렬에 들어간다', () => {
  const db = wrap({ ...twoTracks, n: twoTracks.items.length });
  const [ncs, cs] = db.byTrack();
  assert.deepEqual(ncs.areas.map(a => a.area), ['수리능력', '의사소통능력']);
  assert.deepEqual(cs.areas.map(a => a.area), ['운영체제']);
  assert.equal(ncs.n, 3);
  assert.equal(cs.n, 1);
});

test('묶어도 하나도 빠지지 않는다 — 감추는 것이 아니라 나누는 것이다', () => {
  const db = wrap({ ...twoTracks, n: twoTracks.items.length });
  const grouped = db.byTrack().flatMap(g => g.areas.map(a => a.area));
  assert.deepEqual(grouped.sort(), db.areas().map(a => a.area).sort());
});

test('실제 bank.json — NCS 10과목 504 · 전산 8과목 300', () => {
  const bank = JSON.parse(readFileSync(new URL('../../app/data/bank.json', import.meta.url),
                                       'utf8'));
  const db = wrap(bank);
  const g = db.byTrack();
  assert.deepEqual(g.map(x => [x.tr, x.areas.length, x.n]),
                   [['ncs', 10, 504], ['cs', 8, 300]]);
  assert.equal(g[0].n + g[1].n, db.n);
});

// ── 목록에서 문항을 알아볼 수 있어야 한다 ─────────────────────────
//   목록에는 지문도 자료도 없다. 「위 자료를 토대로 ㉠과 ㉡을 구하면?」만 보고는
//   오답노트에서 무엇을 다시 풀지 고를 수 없다.
const withSrc = {
  keywords: [], tracks: [], rounds: [],
  passages: [
    { lead: '[01~02] 다음 글을 읽고 물음에 답하시오.',
      body: '<p><strong>2027년도 지원사업 공고</strong></p><p><strong>1. 사업 목적</strong><br>노후 설비를 바꾼다.</p>' },
    { lead: '[03~04] 다음 자료를 보고 물음에 답하시오.',
      body: '<p class="unit">(단위: 개소)</p><table class="data"><caption>&lt;표&gt; 권역별 데이터센터 현황</caption><tr><td>1</td></tr></table>' },
  ],
  items: [
    { id: 'a', sj: '문제해결능력', ty: 'x', pg: 0, st: '위 공고문을 이해한 내용으로 옳지 않은 것은?' },
    { id: 'b', sj: '수리능력', ty: 'y', pg: 1, st: '위 자료를 토대로 ㉠과 ㉡을 구하면?' },
    { id: 'c', sj: '수리능력', ty: 'y', st: '다음 중 옳은 것은?' },
    { id: 'd', sj: '정보능력', ty: 'z', st: '중위 표기식 (A + B) * C 를 후위 표기로 바꾼 것은?' },
  ],
};

test('발문이 「위 공고문」이라 부르면 그 공고문의 제목을 앞에 붙인다', () => {
  const db = wrap({ ...withSrc, n: withSrc.items.length });
  const line = db.line(db.byId('a'), 200);
  assert.ok(line.startsWith('2027년도 지원사업 공고 — '), line);
});

test('표는 caption 이 곧 이름이다 — 「(단위: …)」는 이름이 아니다', () => {
  const db = wrap({ ...withSrc, n: withSrc.items.length });
  const line = db.line(db.byId('b'), 200);
  assert.ok(line.startsWith('<표> 권역별 데이터센터 현황 — ') ||
            line.startsWith('권역별 데이터센터 현황 — '), line);
  assert.ok(!line.includes('단위'), line);
});

test('첫 문장이 아니라 첫 블록을 쓴다 — 「공고 1」 처럼 번호가 딸려 오면 안 된다', () => {
  const db = wrap({ ...withSrc, n: withSrc.items.length });
  assert.ok(!/공고 1 —/.test(db.line(db.byId('a'), 200)));
});

test('저 혼자 서는 발문은 건드리지 않는다', () => {
  const db = wrap({ ...withSrc, n: withSrc.items.length });
  assert.equal(db.line(db.byId('c'), 200), '다음 중 옳은 것은?');
});

test('낱말 안쪽의 「위」는 가리키는 말이 아니다 — 중위 표기식', () => {
  const db = wrap({ ...withSrc, n: withSrc.items.length });
  assert.ok(!db.line(db.byId('d'), 200).includes(' — '));
});

test('실제 bank.json — 40줄이 출처를 단다', () => {
  const bank = JSON.parse(readFileSync(new URL('../../app/data/bank.json', import.meta.url),
                                       'utf8'));
  const db = wrap(bank);
  const n = db.items.filter(i => db.line(i, 300).includes(' — ')).length;
  assert.ok(n >= 35 && n <= 60, `출처를 단 줄이 ${n}개다`);
  // 출처를 단 줄은 발문을 그대로 품는다 — 바꿔치기가 아니라 앞에 붙이는 것이다
  for (const it of db.items.filter(i => db.line(i, 300).includes(" — ")).slice(0, 20)) {
    const line = db.line(it, 300);
    assert.ok(line.endsWith(plain(it.st).slice(-12)), line);
  }
});
