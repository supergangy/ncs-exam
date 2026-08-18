/** 기록 — 푼 것·복습 일정·회차 성적·표시.
 *
 *  **저장소를 주입받는다.** app.js 는 `localStorage` 를 직접 불러
 *  브라우저 없이는 한 줄도 시험할 수 없었다. 여기서는 `{ get, set }` 만 있으면
 *  메모리든 파일이든 무엇으로든 돈다.
 *
 *  **시각도 주입받는다** — `now()`. 「3일 뒤에 정말 뜨는가」를 기다리지 않고 본다.
 *
 *  콘텐츠와 기록을 섞지 않는다는 원칙은 그대로다. 문항을 새로 배포해도
 *  이 기록은 건드리지 않는다.
 */
import { schedule, due as dueIds, daysUntil } from './srs.js';

export const KEY = 'ncsbank.v1';
export const PREV = 'ncsbank.v1.prev';   // 복원 직전의 것 — 되돌릴 여지

const blank = () => ({
  att: {},      // 낱개 진도 (회차 제출도 여기 들어간다 — 오답노트·복습이 본다)
  srs: {},      // 복습 일정
  exams: {},    // 회차 성적 이력
  sit: null,    // 응시 중인 회차 (하나만. 나가도 이어진다)
  mark: {},     // 북마크(b)·확인 필요(f)·메모
  solo: null,   // 풀던 묶음 (하나만)
  admin: false, seen: 0, ts: 1.0,
});

export function createStore({ get, set, now = Date.now } = {}) {
  let d = blank();

  const save = () => { try { set(KEY, JSON.stringify(d)); } catch (e) { warn('쓰지', e); } };
  const warn = (what, e) => console.warn(`기록을 ${what} 못했다`, e);

  const S = {
    get d() { return d; },

    load() {
      try {
        const raw = get(KEY);
        if (raw) d = { ...blank(), ...JSON.parse(raw) };
      } catch (e) { warn('읽지', e); }
      return S;
    },
    save,

    // ── 진도 ──────────────────────────────────────────────────────
    /** 한 문항의 마지막 시도. 없으면 null */
    last(id) { const a = d.att[id]; return a ? a[a.length - 1] : null; },
    tried(id) { return !!d.att[id]; },
    /** 마지막 시도가 오답인 것만 오답노트에 남긴다 — 다시 맞히면 빠진다 */
    isWrong(id) { const l = S.last(id); return !!l && !l.k; },

    record(id, chosen, ok, ms) {
      const t = now();
      (d.att[id] ||= []).push({ c: chosen, k: ok ? 1 : 0, t, m: ms | 0 });
      d.srs[id] = schedule(d.srs[id], ok, t);
      save();
    },

    // ── 복습 ──────────────────────────────────────────────────────
    due(items) { return dueIds(d.srs, items, now()); },
    daysUntil(id) { return daysUntil(d.srs[id], now()); },

    // ── 표시 ──────────────────────────────────────────────────────
    marked(id) { const m = d.mark[id]; return !!(m && (m.b || m.f)); },
    mark(id) { return d.mark[id] || null; },
    toggle(id, k) {
      const m = d.mark[id] || {};
      m[k] = !m[k];
      if (!m.b && !m.f && !m.n) delete d.mark[id]; else d.mark[id] = m;
      save();
    },

    // ── 백업 ──────────────────────────────────────────────────────
    /** 내보내기 봉투 — 앱(Flutter)과 **같은 규약**이다. 서로 읽을 수 있다 */
    exportMap(at) {
      return {
        v: 1, app: 'ncs-bank', at,
        counts: { att: Object.keys(d.att).length, exams: Object.keys(d.exams).length,
                  mark: Object.keys(d.mark).length },
        data: d,
      };
    },

    /** 복원 — **통째로 덮어쓴다.** 성공했을 때만 옮긴다.
     *  실패하면 아무것도 건드리지 않고 사유를 돌려준다. */
    importAll(env) {
      if (!env || typeof env !== 'object') return { ok: false, why: '읽을 수 없는 파일이다' };
      if (env.app && env.app !== 'ncs-bank') return { ok: false, why: '이 앱의 백업이 아니다' };
      const next = env.data;
      if (!next || typeof next !== 'object' || Array.isArray(next)) {
        return { ok: false, why: '기록이 들어 있지 않다' };
      }
      for (const k of ['att', 'srs', 'exams', 'mark']) {
        if (next[k] != null && (typeof next[k] !== 'object' || Array.isArray(next[k]))) {
          return { ok: false, why: `${k} 칸이 어긋난다` };
        }
      }
      try { set(PREV, JSON.stringify(d)); } catch { /* 여지가 없어도 복원은 한다 */ }
      d = { ...blank(), ...next };
      save();
      return { ok: true, counts: { att: Object.keys(d.att).length,
                                   exams: Object.keys(d.exams).length,
                                   mark: Object.keys(d.mark).length } };
    },

    reset() { d = blank(); save(); },
  };
  return S;
}

/** 메모리 저장소 — 시험과 서버 렌더에 쓴다 */
export function memory(seed = {}) {
  const m = new Map(Object.entries(seed));
  return { get: k => m.get(k) ?? null, set: (k, v) => m.set(k, v) };
}
