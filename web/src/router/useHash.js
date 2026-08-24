/** 해시 라우터 — 라이브러리를 받지 않는다.
 *
 *  **주소를 바꾸면 안 된다.** 지금 배포본과 같은 해시를 쓴다.
 *  사용자가 북마크한 `#/t/수리능력` 이 새 판에서도 열려야 한다.
 *
 *  react-router 를 쓰지 않는 이유 —
 *  ① 해시 17개를 정규식으로 맞추는 일에 34KB 가 든다
 *  ② 오프라인 앱이라 받는 것이 곧 캐시 용량이다
 *  ③ 지금 app.js 의 라우터가 20줄이고 잘 돌았다
 */
import { useSyncExternalStore, useMemo } from 'react';

/** 지금 배포본과 **같은** 주소들. 늘릴 때는 뒤에 붙인다 */
export const ROUTES = [
  ['home',     /^\/?$/],
  ['area',     /^\/t\/([^/]+)$/],            // 영역
  ['type',     /^\/s\/([^/]+)\/([^/]+)$/],   // 영역 · 유형
  ['exams',    /^\/exams$/],
  ['exam',     /^\/exam\/([^/]+)$/],         // 회차 안내
  ['sit',      /^\/sit\/([^/]+)$/],          // 응시 중
  ['result',   /^\/result\/([^/]+)$/],
  ['wrong',    /^\/wrong$/],
  ['review',   /^\/review$/],
  ['marks',    /^\/marks$/],
  ['stats',    /^\/stats$/],
  ['search',   /^\/search$/],
  ['settings', /^\/settings$/],
  ['about',    /^\/about$/],                 // 새로 만든다 — 버전·문항 수
  ['more',     /^\/more$/],
  ['kw',       /^\/kw$/],
  ['done',     /^\/done$/],
  ['question', /^\/q(?:\?(.*))?$/],          // 문항 풀이
];

const read = () => location.hash.replace(/^#/, '') || '/';
const subscribe = f => {
  addEventListener('hashchange', f);
  return () => removeEventListener('hashchange', f);
};

/** @returns { name, params, hash } — 맞는 것이 없으면 name 은 'notfound' */
export function useHash() {
  const hash = useSyncExternalStore(subscribe, read, () => '/');
  return useMemo(() => match(hash), [hash]);
}

export function match(hash) {
  const path = hash.split('#').pop() || '/';
  for (const [name, re] of ROUTES) {
    const m = re.exec(path);
    if (m) return { name, params: m.slice(1).map(decodeURIComponent), hash: path };
  }
  return { name: 'notfound', params: [], hash: path };
}

/** 화면을 옮긴다. `history.pushState` 를 쓰지 마라 — 해시라 뒤로 가기가 공짜다 */
export const go = h => { location.hash = h.startsWith('#') ? h : '#' + h; };

/** 문항 풀이 주소를 만든다 — 어떤 묶음인지 질의 문자열로 넘긴다 */
export function qHref(params) {
  const q = new URLSearchParams(params).toString();
  return '#/q' + (q ? '?' + q : '');
}
