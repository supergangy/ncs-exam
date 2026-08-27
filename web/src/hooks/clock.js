/** 시계 — **「지금」을 읽는 자리를 이 파일 하나로 모은다.**
 *
 *  `core` 는 시각을 주입받는다. 그러면 누군가는 실제 시각을 읽어야 하고,
 *  그 자리가 여기다. 화면마다 `Date.now()` 를 부르면 무엇이 언제를 기준으로
 *  재는지 흩어지고, 모바일·PC 두 판에 같은 코드가 두 벌 생긴다.
 *  `tool/check_ui.mjs` 의 면제 표에 이 파일만 적혀 있다.
 *
 *  ──────────────────────────────────────────────────────────────
 *  문항을 연 순간을 잡아 둔다 — 소요 시간 측정.
 *
 *  **시각을 읽는 자리를 여기 하나로 모은다.** 화면마다 `Date.now()` 를 부르면
 *  무엇이 언제를 기준으로 재는지 흩어지고, 모바일·PC 두 판에 같은 코드가 두 벌 생긴다.
 *
 *  `core` 는 시각을 주입받는다는 규율이 이 파일의 이유이기도 하다 —
 *  core 는 「받은 시각으로 계산」만 하고, 「지금이 언제인가」는 화면 쪽 사건이다.
 *  문항을 본 순간은 사용자가 화면을 열었을 때이므로 core 가 알 수 없다.
 *
 *  @param key  이 값이 바뀌면 시계를 다시 잡는다 (문항 id 를 넘긴다)
 *  @returns () => number  시작 시각. `core/grade.js` 의 `gradeOne` 에 그대로 넘긴다
 */
import { useEffect, useRef, useState } from 'react';

export function useElapsed(key) {
  const at = useRef(Date.now());
  useEffect(() => { at.current = Date.now(); }, [key]);
  return () => at.current;
}

/** 초 단위로 흐르는 「지금」 — 회차 타이머가 본다.
 *
 *  `useElapsed` 는 시작 시각 하나를 잡아 두는 것이고, 이쪽은 **계속 다시 읽는다.**
 *  시각을 읽는 자리를 이 파일 하나로 모아 두는 편이, 화면마다 `setInterval` 과
 *  `Date.now()` 를 흩뿌리는 것보다 낫다.
 *
 *  @param on  false 면 멈춘다 (제출한 뒤에는 셀 필요가 없다)
 */
export function useNow(tickMs = 1000, on = true) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!on) return undefined;
    const t = setInterval(() => setNow(Date.now()), tickMs);
    return () => clearInterval(t);
  }, [tickMs, on]);
  return now;
}

/** 「지금」 — 버튼을 누른 순간의 시각이 필요할 때. 렌더 시각이 아니다.
 *  (백업 파일에 찍는 시각, 파일 이름의 날짜 같은 것) */
export const nowMs = () => Date.now();
