/** 문항을 연 순간을 잡아 둔다 — 소요 시간 측정.
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
import { useEffect, useRef } from 'react';

export function useElapsed(key) {
  const at = useRef(Date.now());
  useEffect(() => { at.current = Date.now(); }, [key]);
  return () => at.current;
}
