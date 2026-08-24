/** 해시 라우터 검사 — **주소가 지금 배포본과 같아야 한다.**
 *
 *  사용자가 북마크한 `#/t/수리능력` 이 새 판에서도 열려야 한다.
 *  라우터를 새로 짜면서 주소를 바꾸는 것이 가장 흔한 사고다.
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { match, ROUTES, qHref } from '../src/router/useHash.js';

test('지금 배포본의 주소 17개가 그대로 갈린다', () => {
  const cases = [
    ['/', 'home'],
    ['', 'home'],
    ['/t/수리능력', 'area'],
    ['/s/수리능력/자료해석', 'type'],
    ['/exams', 'exams'],
    ['/exam/r5_nhis', 'exam'],
    ['/sit/r5_nhis', 'sit'],
    ['/result/r5_nhis', 'result'],
    ['/wrong', 'wrong'],
    ['/review', 'review'],
    ['/marks', 'marks'],
    ['/stats', 'stats'],
    ['/search', 'search'],
    ['/settings', 'settings'],
    ['/about', 'about'],
    ['/more', 'more'],
    ['/kw', 'kw'],
    ['/done', 'done'],
    ['/q?area=수리능력', 'question'],
    ['/q', 'question'],
  ];
  for (const [path, want] of cases) {
    assert.equal(match(path).name, want, path + ' 가 ' + match(path).name + ' 로 갔다');
  }
});

test('앞의 # 을 붙여도 같다', () => {
  assert.equal(match('#/wrong').name, 'wrong');
  assert.equal(match('#/t/수리능력').name, 'area');
});

test('한글 매개변수가 풀린다 — %EC… 가 그대로 오면 목록을 못 찾는다', () => {
  assert.deepEqual(match('/t/' + encodeURIComponent('수리능력')).params, ['수리능력']);
  assert.deepEqual(match('/s/수리능력/자료해석').params, ['수리능력', '자료해석']);
});

test('모르는 주소는 notfound — 홈으로 조용히 튀지 않는다', () => {
  assert.equal(match('/없는곳').name, 'notfound');
  assert.equal(match('/t').name, 'notfound');          // 영역 없이 /t 만
  assert.equal(match('/s/수리능력').name, 'notfound');   // 유형이 빠졌다
});

test('주소가 겹치지 않는다 — 먼저 맞는 것 하나만 나온다', () => {
  for (const path of ['/exams', '/exam/x', '/wrong', '/q?a=1']) {
    const hit = ROUTES.filter(([, re]) => re.test(path));
    assert.equal(hit.length, 1, path + ' 에 ' + hit.length + '개가 맞는다: '
      + hit.map(h => h[0]).join(','));
  }
});

test('문항 주소를 만든다', () => {
  assert.equal(qHref({}), '#/q');
  assert.equal(match(qHref({ area: '수리능력' }).slice(1)).name, 'question');
});
