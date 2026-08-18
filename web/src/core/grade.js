/** 채점 — **판정만 한다. 화면을 만들지 않는다.**
 *
 *  app.js 의 `grade()` 는 판정과 DOM 조작이 한 함수에 있었다(60줄).
 *  그래서 「정답이 맞게 나오는가」를 브라우저 없이 확인할 수 없었다.
 *  여기서는 무엇을 어떻게 보일지 결정한 **결과만** 돌려주고 그리는 것은 화면이 한다.
 */

/** 선지 하나의 상태 — 화면은 이 다섯 가지에 각각 모양을 준다.
 *
 *  `pick` 은 아직 채점 전이다. 채점하면 `right`·`wrong`·`plain` 으로 갈린다.
 *  색만으로 나누지 않고 테두리 굵기도 함께 바꾼다(접근성).
 */
export const CH = { idle: 'idle', pick: 'pick', right: 'right', wrong: 'wrong', plain: 'plain' };

/**
 * @param answer  정답 번호 (1부터)
 * @param chosen  고른 번호 | null
 * @param graded  채점했나
 * @param n       선지 수
 */
export function choiceStates(answer, chosen, graded, n) {
  return Array.from({ length: n }, (_, i) => {
    const no = i + 1;
    if (!graded) return no === chosen ? CH.pick : CH.idle;
    if (no === answer) return CH.right;
    if (no === chosen) return CH.wrong;
    return CH.plain;
  });
}

/** 한 문항의 채점 결과. `ms` 는 10분으로 자른다 —
 *  화면을 켜 둔 채 밥 먹고 오면 평균이 망가진다 (앱에서 배운 것). */
export const MAX_MS = 10 * 60 * 1000;

export function gradeOne(item, chosen, ms) {
  const ok = chosen === item.an;
  return {
    ok, chosen, answer: item.an,
    ms: ms == null ? null : Math.min(MAX_MS, Math.max(0, ms | 0)),
    verdict: ok ? '맞았습니다' : '틀렸습니다',
  };
}

/** 회차 제출 — **한꺼번에 채점한다.** 고르지 않은 것은 오답이다.
 *
 *  중간에 나간 것과 제출한 것은 다르다. 제출해야 기록에 남는다.
 */
export function gradeAll(items, chosen) {
  const marks = items.map((it, i) => {
    const c = chosen[i] ?? null;
    return { id: it.id, chosen: c, answer: it.an, ok: c === it.an, blank: c == null };
  });
  const right = marks.filter(m => m.ok).length;
  const blank = marks.filter(m => m.blank).length;
  return {
    marks, right, blank, n: items.length,
    rate: items.length ? Math.round(right / items.length * 100) : 0,
  };
}

/** 영역별 성적 — 결과 화면의 막대에 쓴다 */
export function byArea(items, marks) {
  const m = new Map();
  items.forEach((it, i) => {
    const k = it.sj || '기타';
    const a = m.get(k) || { area: k, n: 0, ok: 0 };
    a.n++; if (marks[i].ok) a.ok++;
    m.set(k, a);
  });
  return [...m.values()].map(a => ({ ...a, rate: Math.round(a.ok / a.n * 100) }))
    .sort((x, y) => y.n - x.n);
}

/** 섞기 — Fisher-Yates. **받은 배열을 고치지 않는다** */
export function shuffle(a, rnd = Math.random) {
  const o = [...a];
  for (let i = o.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [o[i], o[j]] = [o[j], o[i]];
  }
  return o;
}
