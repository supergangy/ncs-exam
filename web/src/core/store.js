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
import { schedule, due as dueIds, daysUntil, untilText } from './srs.js';

export const KEY = 'ncsbank.v1';
export const PREV = 'ncsbank.v1.prev';   // 복원 직전의 것 — 되돌릴 여지

const blank = () => ({
  att: {},      // 낱개 진도 (회차 제출도 여기 들어간다 — 오답노트·복습이 본다)
  srs: {},      // 복습 일정
  exams: {},    // 회차 성적 이력
  sit: null,    // 응시 중인 회차 (하나만. 나가도 이어진다)
  mark: {},     // 북마크(b)·확인 필요(f)·메모
  solo: null,   // 풀던 묶음 (하나만)
  // 사용자가 정하는 것 — 나머지는 att 에서 세어 낸다 (core/goal.js)
  pref: { goal: 25, examAt: null },   // 하루 목표 문항 수 · 시험일
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
    untilText(id) { return untilText(d.srs[id], now()); },

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

    // ── 회차 응시 ─────────────────────────────────────────────────
    /** 응시 중인 회차 — **하나만.** 나가도 이어진다.
     *
     *  구조를 배포본과 맞춘다. 백업 파일에도 이 모양이 담겨 있고, 옛 판으로
     *  응시하던 사람이 새 판에서 이어 풀 수 있어야 한다.
     *
     *    { tag, at, endsAt, ans: {문항no: 고른번호}, flag: {문항no: true}, at_no }
     *
     *  **키가 문항 번호(`no`)다.** 인덱스로 두면 문항 순서가 바뀔 때 답이 어긋난다.
     *  `endsAt` 을 미리 못박아 두는 것도 배포본과 같다 — 회차 사양의 제한 시간이
     *  나중에 바뀌어도 진행 중인 응시는 흔들리지 않는다.
     */
    sit() { return d.sit; },
    startSit(tag, min) {
      const t = now();
      d.sit = { tag, at: t, endsAt: t + min * 60000, ans: {}, flag: {}, at_no: 1 };
      save();
      return d.sit;
    },
    sitPick(no, n) { if (d.sit) { d.sit.ans[no] = n; save(); } return d.sit; },
    sitFlag(no) { if (d.sit) { d.sit.flag[no] = !d.sit.flag[no]; save(); } return d.sit; },
    sitAt(no) { if (d.sit) { d.sit.at_no = no; save(); } return d.sit; },
    dropSit() { d.sit = null; save(); },

    /** 제출 — 성적을 이력에 쌓고 **낱개 진도에도 넣는다.**
     *
     *  `att` 에 들어가야 오답노트와 복습이 회차 문항을 본다. 소요 시간은 0 이다 —
     *  회차에서는 문항을 자유롭게 오가므로 문항별 시간을 잴 수 없다.
     *  **안 고른 문항도 오답으로 기록한다** — 시험은 빈칸이 오답이다.
     *
     *  @param result `core/grade.js` 의 `gradeAll` 결과
     *  @param auto   시간이 다해 자동 제출된 것인가
     */
    submitSit(items, result, auto = false) {
      if (!d.sit) return null;
      const s = d.sit;
      const t = now();
      items.forEach((it, i) => {
        const m = result.marks[i];
        (d.att[it.id] ||= []).push({ c: m.chosen, k: m.ok ? 1 : 0, t, m: 0 });
        d.srs[it.id] = schedule(d.srs[it.id], m.ok, t);
      });
      const rec = {
        at: t, score: result.right, n: result.n,
        sec: Math.round((t - s.at) / 1000),
        auto: auto ? 1 : 0,
        ans: { ...s.ans },          // 무엇을 골랐나 — 결과 화면이 이것으로 되짚는다
      };
      (d.exams[s.tag] ||= []).push(rec);
      d.sit = null;
      save();
      return rec;
    },

    /** 회차 이력 — **배열이다.** 같은 회차를 여러 번 응시할 수 있다 */
    examHistory(tag) {
      const h = d.exams[tag];
      return Array.isArray(h) ? h : (h ? [h] : []);   // 옛 판이 객체로 둔 경우도 받는다
    },
    /** 가장 최근 응시 */
    exam(tag) {
      const h = S.examHistory(tag);
      return h.length ? h[h.length - 1] : null;
    },

    // ── 풀던 묶음 ─────────────────────────────────────────────────
    /** 하나만 둔다. 앱을 닫았다 열어도 그 자리에서 이어진다.
     *
     *  **id 목록을 함께 저장한다.** 「복습 대기」·「오답노트」는 다시 만들면
     *  순서와 구성이 달라진다 — 풀던 중에 하나를 맞히면 목록에서 빠지므로
     *  위치(at)만 저장하면 다른 문항으로 튄다. */
    solo() { return d.solo; },
    setSolo(key, ids, at = 0) {
      d.solo = { key, ids, at, t: now() };
      save();
      return d.solo;
    },
    soloAt(at) {
      if (!d.solo) return null;
      d.solo.at = at;
      save();
      return d.solo;
    },
    clearSolo() { d.solo = null; save(); },

    // ── 설정 ──────────────────────────────────────────────────────
    /** 목표·시험일. 넘긴 칸만 바꾼다 */
    setPref(patch) {
      d.pref = { ...d.pref, ...patch };
      save();
      return d.pref;
    },
    get pref() { return d.pref || { goal: 25, examAt: null }; },

    reset() { d = blank(); save(); },
  };
  return S;
}

/** 메모리 저장소 — 시험과 서버 렌더에 쓴다 */
export function memory(seed = {}) {
  const m = new Map(Object.entries(seed));
  return { get: k => m.get(k) ?? null, set: (k, v) => m.set(k, v) };
}
