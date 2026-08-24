/** 복습 일정 — SM-2 를 줄인 것.
 *
 *  **`Date.now()` 를 쓰지 않는다.** 지금 시각을 인자로 받는다.
 *  그래야 「3일 뒤에 정말 뜨는가」를 시계를 기다리지 않고 확인할 수 있다.
 *  app.js 의 것은 함수 안에서 Date.now() 를 불러 시험할 수 없었다.
 */

export const DAY = 86400000;
export const AGAIN = 10 * 60 * 1000;   // 틀리면 10분 뒤 다시

/** 처음 만나는 문항의 상태 */
export const fresh = () => ({ e: 2.5, i: 0, due: 0 });

/** 한 번 풀고 난 뒤의 상태를 돌려준다. **받은 것을 고치지 않는다.**
 *
 *  틀리면 간격이 0 으로 돌아가고 용이도가 깎인다. 맞히면 1 → 3 → ×e 로 벌어진다.
 *  용이도는 1.3~2.8 로 묶는다 — 아래로 열어 두면 한 문항이 영원히 10분마다 뜬다.
 */
export function schedule(prev, ok, now) {
  const s = { ...(prev || fresh()) };
  if (!ok) {
    s.e = Math.max(1.3, s.e - 0.2);
    s.i = 0;
    s.due = now + AGAIN;
  } else {
    s.e = Math.min(2.8, s.e + 0.1);
    s.i = s.i === 0 ? 1 : s.i === 1 ? 3 : Math.round(s.i * s.e);
    s.due = now + s.i * DAY;
  }
  return s;
}

/** 지금 복습할 차례인 id — **한 번이라도 푼 것만.** 안 푼 것은 복습이 아니다 */
export function due(srs, items, now) {
  return items.filter(i => { const s = srs[i.id]; return s && s.due <= now; })
              .map(i => i.id);
}

/** 며칠 뒤에 뜨는지 — 「복습 예정」 표시에 쓴다. 지난 것은 0 */
export function daysUntil(s, now) {
  if (!s) return null;
  return Math.max(0, Math.ceil((s.due - now) / DAY));
}

/** 사람이 읽을 표기 — **하루 미만을 「1일 뒤」라고 하지 않는다.**
 *
 *  틀린 문항은 10분 뒤에 다시 뜨는데 `daysUntil` 은 그것을 1 로 올린다
 *  (ceil 이므로). 화면에 「1일 뒤」라고 쓰면 사용자가 내일 오라는 줄 안다.
 *  실제로 화면에 그렇게 나온 것을 보고 고쳤다.
 */
export function untilText(s, now) {
  if (!s) return null;
  const left = s.due - now;
  if (left <= 0) return '지금';
  if (left < 60 * 1000) return '곧';
  if (left < 60 * 60 * 1000) return Math.round(left / 60000) + '분 뒤';
  if (left < DAY) return Math.round(left / 3600000) + '시간 뒤';
  return Math.round(left / DAY) + '일 뒤';
}
