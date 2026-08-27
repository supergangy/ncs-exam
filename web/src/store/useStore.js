/** 기록을 React 에 잇는 훅 — **`core/store.js` 를 감싸기만 한다.**
 *
 *  판단은 아무것도 하지 않는다. 채점 규칙도, 복습 간격도 여기 없다.
 *  그것은 `core/` 에 있고 764문항으로 검증했다. 이 파일이 하는 일은
 *  「바뀌었다」를 React 에 알리는 것뿐이다.
 *
 *  `useSyncExternalStore` 를 쓴다 — 상태가 React 밖(localStorage)에 있으므로
 *  useState 로 흉내내면 두 벌이 되어 어긋난다.
 */
import { useSyncExternalStore, useCallback, useMemo } from 'react';
import { createStore } from '../core/store.js';

const browser = {
  get: k => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k, v) => { try { localStorage.setItem(k, v); } catch { /* 꽉 찼다 */ } },
};

const S = createStore(browser).load();

// ── 알림 ─ 기록이 바뀌면 화면을 다시 그린다 ─────────────────────────
const subs = new Set();
let version = 0;
const emit = () => { version++; subs.forEach(f => f()); };
const subscribe = f => { subs.add(f); return () => subs.delete(f); };

/** 기록을 고치는 것은 모두 이 문을 지난다 — 알림을 빠뜨릴 수 없게 */
function mutate(fn) {
  return (...a) => { const r = fn(...a); emit(); return r; };
}

const API = {
  // 읽기 — 알림과 무관하다
  last: id => S.last(id),
  tried: id => S.tried(id),
  isWrong: id => S.isWrong(id),
  marked: id => S.marked(id),
  mark: id => S.mark(id),
  due: items => S.due(items),
  daysUntil: id => S.daysUntil(id),
  untilText: id => S.untilText(id),
  get d() { return S.d; },
  get pref() { return S.pref; },
  solo: () => S.solo(),
  sit: () => S.sit(),
  exam: tag => S.exam(tag),
  examHistory: tag => S.examHistory(tag),

  // 쓰기 — 모두 알린다
  record: mutate((id, chosen, ok, ms) => S.record(id, chosen, ok, ms)),
  toggle: mutate((id, k) => S.toggle(id, k)),
  importAll: mutate(env => S.importAll(env)),
  startSit: mutate((tag, min) => S.startSit(tag, min)),
  sitPick: mutate((no, n) => S.sitPick(no, n)),
  sitFlag: mutate(no => S.sitFlag(no)),
  sitAt: mutate(no => S.sitAt(no)),
  dropSit: mutate(() => S.dropSit()),
  submitSit: mutate((items, result, auto) => S.submitSit(items, result, auto)),
  setSolo: mutate((key, ids, at) => S.setSolo(key, ids, at)),
  soloAt: mutate(at => S.soloAt(at)),
  clearSolo: mutate(() => S.clearSolo()),
  setPref: mutate(patch => S.setPref(patch)),
  reset: mutate(() => S.reset()),
  exportMap: at => S.exportMap(at),
};

/** 화면에서 쓴다 — `const st = useStore()`.
 *
 *  기록이 바뀌면 이 훅을 쓴 컴포넌트가 다시 그려진다.
 */
export function useStore() {
  useSyncExternalStore(subscribe, () => version, () => 0);
  return API;
}

/** 진도처럼 **셈이 드는 것**은 이걸로 받는다 — 기록이 바뀔 때만 다시 센다 */
export function useDerived(fn, deps = []) {
  const v = useSyncExternalStore(subscribe, () => version, () => 0);
  const f = useCallback(fn, deps);   // eslint-disable-line react-hooks/exhaustive-deps
  return useMemo(() => f(API), [f, v]);
}

export { API as store };
