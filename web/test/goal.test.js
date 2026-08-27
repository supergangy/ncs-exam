/** `core/goal.js` — 브라우저 없이 시험한다. 시각을 넘겨 주므로 기다릴 것이 없다. */
import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  DAY_MS, dayStart, perDay, streak, todayCount, goalToday,
  xp, level, XP_OK, XP_TRY, XP_EXAM, daysTo, examText, daily, weekOverWeek, weakest,
} from '../src/core/goal.js';

/** 2026-08-27 (목) 14:00 로컬 */
const NOW = new Date(2026, 7, 27, 14, 0, 0).getTime();
const T0 = dayStart(NOW);

/** att 를 만든다 — `[[하루전차, 정답여부], …]` */
const mk = (rows, hour = 10) => {
  const att = {};
  rows.forEach(([back, ok], i) => {
    const t = T0 - back * DAY_MS + hour * 3600000;
    (att['q' + i] ||= []).push({ c: 1, k: ok ? 1 : 0, t, m: 5000 });
  });
  return att;
};

test('dayStart — 로컬 자정으로 자른다', () => {
  const d = new Date(T0);
  assert.equal(d.getHours(), 0);
  assert.equal(d.getMinutes(), 0);
  assert.equal(dayStart(NOW), dayStart(NOW + 3600000), '같은 날이면 같은 값');
  assert.notEqual(dayStart(NOW), dayStart(NOW + DAY_MS), '다음 날이면 다르다');
});

test('perDay — 하루 단위로 묶어 센다', () => {
  const m = perDay(mk([[0, 1], [0, 0], [1, 1], [3, 1]]));
  assert.equal(m.get(T0), 2);
  assert.equal(m.get(T0 - DAY_MS), 1);
  assert.equal(m.get(T0 - 2 * DAY_MS), undefined, '건너뛴 날은 없다');
  assert.equal(m.get(T0 - 3 * DAY_MS), 1);
});

test('streak — 오늘 풀었으면 오늘부터 거꾸로', () => {
  assert.equal(streak(mk([[0, 1], [1, 1], [2, 1]]), NOW), 3);
  assert.equal(streak(mk([[0, 1]]), NOW), 1);
  assert.equal(streak(mk([[0, 1], [1, 1], [3, 1]]), NOW), 2, '2일 전이 비면 거기서 끊긴다');
});

test('streak — 오늘 안 풀었어도 어제 풀었으면 살려 둔다', () => {
  // 오늘 하루가 남아 있으므로 끊긴 것이 아니다
  assert.equal(streak(mk([[1, 1], [2, 1]]), NOW), 2);
});

test('streak — 어제도 없으면 0', () => {
  assert.equal(streak(mk([[2, 1], [3, 1]]), NOW), 0);
  assert.equal(streak({}, NOW), 0, '기록이 없으면 0');
});

test('todayCount · goalToday', () => {
  const att = mk([[0, 1], [0, 0], [0, 1], [1, 1]]);
  assert.equal(todayCount(att, NOW), 3);

  const g = goalToday(att, 25, NOW);
  assert.deepEqual(g, { done: 3, goal: 25, left: 22, fill: 12 });

  const done = goalToday(mk([[0, 1], [0, 1]]), 2, NOW);
  assert.equal(done.left, 0);
  assert.equal(done.fill, 100);

  const over = goalToday(mk([[0, 1], [0, 1], [0, 1]]), 2, NOW);
  assert.equal(over.fill, 100, '넘겨도 100 을 넘지 않는다');
  assert.equal(over.left, 0);

  assert.equal(goalToday({}, 0, NOW).goal, 1, '목표 0 은 1 로 본다 — 0 으로 나누지 않게');
});

test('xp — 맞히면 3, 틀려도 1', () => {
  assert.equal(xp(mk([[0, 1]])), XP_OK);
  assert.equal(xp(mk([[0, 0]])), XP_TRY, '틀린 시도에도 준다 — 0 이면 어려운 문항을 피하게 된다');
  assert.equal(xp(mk([[0, 1], [0, 1], [0, 0]])), XP_OK * 2 + XP_TRY);
  assert.equal(xp({}, { r1: { score: 80 }, r2: { score: 90 } }), XP_EXAM * 2, '회차 완주 보너스');
});

test('level — 올라갈수록 느려진다', () => {
  assert.equal(level(0).lv, 1);
  assert.equal(level(49).lv, 1);
  assert.equal(level(50).lv, 2);
  assert.equal(level(800).lv, 5);
  assert.equal(level(4050).lv, 10);

  const l = level(75);                      // Lv2 구간(50~200) 의 가운데쯤
  assert.equal(l.lv, 2);
  assert.equal(l.at, 50);
  assert.equal(l.next, 200);
  assert.equal(l.fill, 17);
  assert.equal(level(-10).lv, 1, '음수도 터지지 않는다');
});

test('daysTo · examText', () => {
  assert.equal(daysTo(null, NOW), null, '시험일이 없으면 null');
  assert.equal(daysTo(NOW + 18 * DAY_MS, NOW), 18);
  assert.equal(daysTo(NOW, NOW), 0);
  assert.equal(daysTo(NOW - 2 * DAY_MS, NOW), -2, '지났으면 음수');

  assert.equal(examText(NOW + 18 * DAY_MS, NOW), 'D-18');
  assert.equal(examText(NOW, NOW), '오늘');
  assert.equal(examText(NOW - 3 * DAY_MS, NOW), '3일 지남');
  assert.equal(examText(null, NOW), null);
});

test('daily — 쉰 날은 rate 가 null 이다', () => {
  // 0% 로 두면 「쉰 날」과 「다 틀린 날」이 같아 보인다
  const att = mk([[0, 1], [0, 0], [2, 1]]);
  const rows = daily(att, 3, NOW);

  assert.equal(rows.length, 3);
  assert.equal(rows[0].at, T0 - 2 * DAY_MS);
  assert.equal(rows[0].rate, 100);
  assert.equal(rows[1].n, 0);
  assert.equal(rows[1].rate, null, '푼 것이 없는 날');
  assert.equal(rows[2].n, 2);
  assert.equal(rows[2].rate, 50);
});

test('weekOverWeek — 한쪽이라도 비면 delta 는 null', () => {
  // 이번 주 2문항 중 1개 정답(50%) · 지난 주 2문항 전부 정답(100%)
  const att = mk([[1, 1], [2, 0], [8, 1], [9, 1]]);
  const w = weekOverWeek(att, NOW);
  assert.equal(w.n, 2);
  assert.equal(w.rate, 50);
  assert.equal(w.prev, 100);
  assert.equal(w.delta, -50);

  const only = weekOverWeek(mk([[1, 1]]), NOW);
  assert.equal(only.rate, 100);
  assert.equal(only.prev, null);
  assert.equal(only.delta, null, '견줄 지난 주가 없으면 변화를 말하지 않는다');

  const none = weekOverWeek({}, NOW);
  assert.equal(none.n, 0);
  assert.equal(none.rate, null);
});

test('weakest — 표본이 적은 영역은 세지 않는다', () => {
  const rows = [
    { area: '수리', done: 40, rate: 62 },
    { area: '정보', done: 2, rate: 50 },    // 2문항으로는 약하다고 말할 수 없다
    { area: '의사소통', done: 20, rate: 45 },
    { area: '윤리', done: 10, rate: 90 },
  ];
  const w = weakest(rows, 5);
  assert.deepEqual(w.map(r => r.area), ['의사소통', '수리', '윤리']);
  assert.equal(w.find(r => r.area === '정보'), undefined, '표본 미달은 빠진다');

  assert.deepEqual(weakest([], 5), []);
  assert.deepEqual(weakest(rows, 100), [], '아무도 기준을 못 넘으면 빈 목록');
});

test('weakest — 정답률이 같으면 많이 푼 쪽을 앞에 (근거가 두텁다)', () => {
  const w = weakest([{ area: 'A', done: 10, rate: 50 }, { area: 'B', done: 30, rate: 50 }], 5);
  assert.deepEqual(w.map(r => r.area), ['B', 'A']);
});
