/** 목표·연속일·경험치 — **기록에서 셈으로 낸다. 따로 저장하지 않는다.**
 *
 *  연속일과 경험치를 별도 칸에 적어 두면 기록과 어긋난다. 백업을 복원하거나
 *  기록을 지웠을 때 둘이 갈라지고, 어느 쪽이 맞는지 알 수 없다.
 *  `att` 에 시도마다 시각(`t`)과 정답 여부(`k`)가 있으므로 매번 세면 된다.
 *
 *  **시각을 주입받는다** — `now`. 「자정을 넘기면 연속이 끊기나」를 기다리지 않고 본다.
 *
 *  저장하는 것은 사용자가 정하는 둘뿐이다 (`store.pref`).
 *    goal    하루에 풀 문항 수
 *    examAt  시험일 — 남은 날을 세는 기준
 */

/** 로컬 하루의 시작. UTC 로 자르면 한국에서 오전 9시에 날짜가 바뀐다 */
export const dayStart = t => {
  const d = new Date(t);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
};

export const DAY_MS = 86400000;

/** 시도 전부를 시각 오름차순 한 줄로 펼친다 — 아래 셈들이 공유한다 */
export function attempts(att) {
  const out = [];
  for (const id in att) for (const a of att[id]) out.push({ id, ...a });
  return out.sort((x, y) => x.t - y.t);
}

/** 하루에 몇 개 풀었나 — `{ 'YYYY-MM-DD': n }` 이 아니라 하루 시작 밀리초를 키로 쓴다.
 *  문자열 날짜는 시간대·서식에 흔들린다. */
export function perDay(att) {
  const m = new Map();
  for (const a of attempts(att)) {
    const k = dayStart(a.t);
    m.set(k, (m.get(k) || 0) + 1);
  }
  return m;
}

/** 연속 학습일.
 *
 *  오늘 풀었으면 오늘부터 거꾸로 센다. 오늘 아직 안 풀었어도 어제 풀었다면
 *  **어제까지의 연속을 살려 둔다** — 오늘 하루가 남아 있으므로 끊긴 것이 아니다.
 *  어제도 없으면 0 이다.
 */
export function streak(att, now = Date.now()) {
  const days = perDay(att);
  if (!days.size) return 0;
  const today = dayStart(now);
  let cur = days.has(today) ? today : (days.has(today - DAY_MS) ? today - DAY_MS : null);
  if (cur == null) return 0;
  let n = 0;
  while (days.has(cur)) { n++; cur -= DAY_MS; }
  return n;
}

/** 오늘 푼 문항 수 — 목표 막대가 본다 */
export function todayCount(att, now = Date.now()) {
  return perDay(att).get(dayStart(now)) || 0;
}

/** 오늘 목표 진행 — `{ done, goal, left, fill }` */
export function goalToday(att, goal = 25, now = Date.now()) {
  const done = todayCount(att, now);
  const g = Math.max(1, goal | 0);
  return {
    done, goal: g,
    left: Math.max(0, g - done),
    fill: Math.min(100, Math.round((done / g) * 100)),
  };
}

// ── 경험치 ────────────────────────────────────────────────────────────
/** 맞히면 3, 틀려도 1. **틀린 시도에도 주는 이유** — 0 을 주면 어려운 문항을
 *  피하는 것이 이득이 된다. 틀려도 푼 것은 푼 것이다. */
export const XP_OK = 3;
export const XP_TRY = 1;
/** 회차를 끝까지 낸 것에만 얹는다 — 낱개 풀이와 다른 노력이다 */
export const XP_EXAM = 20;

export function xp(att, exams = {}) {
  let v = 0;
  for (const a of attempts(att)) v += a.k ? XP_OK : XP_TRY;
  for (const id in exams) if (exams[id]) v += XP_EXAM;
  return v;
}

/** 레벨 — 올라갈수록 느려진다. `50·L²` 이 다음 레벨의 문턱이다.
 *  (Lv2 = 50xp · Lv5 = 800 · Lv10 = 4,050) */
export function level(v) {
  const lv = Math.floor(Math.sqrt(Math.max(0, v) / 50)) + 1;
  const at = 50 * (lv - 1) ** 2;
  const next = 50 * lv ** 2;
  return { lv, at, next, fill: Math.round(((v - at) / (next - at)) * 100) };
}

// ── 시험일 ────────────────────────────────────────────────────────────
/** 남은 날. 시험일이 없으면 null, 지났으면 음수 */
export function daysTo(examAt, now = Date.now()) {
  if (!examAt) return null;
  return Math.round((dayStart(examAt) - dayStart(now)) / DAY_MS);
}

export function examText(examAt, now = Date.now()) {
  const d = daysTo(examAt, now);
  if (d == null) return null;
  if (d > 0) return `D-${d}`;
  if (d === 0) return '오늘';
  return `${-d}일 지남`;
}

// ── 추이 ──────────────────────────────────────────────────────────────
/** 최근 n일의 하루별 정답률 — 분석 화면의 꺾은선이 본다.
 *  푼 것이 없는 날은 `rate: null` 이다. **0% 로 두면 안 된다** — 쉰 날과
 *  다 틀린 날이 같아 보인다. */
export function daily(att, days = 7, now = Date.now()) {
  const byDay = new Map();
  for (const a of attempts(att)) {
    const k = dayStart(a.t);
    const b = byDay.get(k) || { n: 0, ok: 0 };
    b.n++; if (a.k) b.ok++;
    byDay.set(k, b);
  }
  const out = [];
  const t0 = dayStart(now);
  for (let i = days - 1; i >= 0; i--) {
    const k = t0 - i * DAY_MS;
    const b = byDay.get(k);
    out.push({ at: k, n: b?.n || 0, ok: b?.ok || 0,
               rate: b?.n ? Math.round((b.ok / b.n) * 100) : null });
  }
  return out;
}

/** 이번 주 정답률과 지난 주 대비 변화 — 시안의 「+2.4% vs last week」 자리.
 *  한쪽이라도 푼 것이 없으면 `delta` 는 null 이다. */
export function weekOverWeek(att, now = Date.now()) {
  const t0 = dayStart(now) + DAY_MS;            // 오늘 끝
  const span = (from, to) => {
    let n = 0, ok = 0;
    for (const a of attempts(att)) if (a.t >= from && a.t < to) { n++; if (a.k) ok++; }
    return n ? { n, rate: Math.round((ok / n) * 1000) / 10 } : { n: 0, rate: null };
  };
  const cur = span(t0 - 7 * DAY_MS, t0);
  const prev = span(t0 - 14 * DAY_MS, t0 - 7 * DAY_MS);
  const delta = cur.rate != null && prev.rate != null
    ? Math.round((cur.rate - prev.rate) * 10) / 10 : null;
  return { ...cur, prev: prev.rate, delta };
}

// ── 취약 영역 ─────────────────────────────────────────────────────────
/** 정답률이 낮은 순으로 세운다 — 시안의 「AI curated」 자리를 이것이 맡는다.
 *
 *  **표본이 적은 영역은 뺀다.** 2문항 풀어 1개 틀린 영역(50%)이 40문항 중
 *  15개 틀린 영역(62%)보다 약하다고 말할 수 없다.
 *
 *  @param rows [{ area, done, rate }] — 화면이 `core/progress.js` 로 만들어 넘긴다
 *  @param min  이만큼은 풀어 봤어야 센다
 */
export function weakest(rows, min = 5) {
  return rows.filter(r => r.done >= min)
             .sort((a, b) => a.rate - b.rate || b.done - a.done);
}
