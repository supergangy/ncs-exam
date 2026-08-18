/** 글자 다루기 — **app.js 에서 그대로 옮긴 것이다. 다시 쓰지 않았다.**
 *
 *  이 두 함수는 두 번 물려서 고친 자리다 —
 *  ① `&lt;보기&gt;` 가 화면에 글자 그대로 나왔다 (문자 참조를 풀지 않았다)
 *  ② `cm<sup>2</sup>` 가 「cm 2」 가 됐다 (인라인 태그 자리에 공백을 넣었다)
 *  검증된 구현이므로 옮기기만 하고 손대지 않는다.
 */

const ENT = { '&lt;': '<', '&gt;': '>', '&amp;': '&', '&quot;': '"',
              '&nbsp;': ' ', '&#39;': "'" };
const unent = s => String(s || '').replace(/&(?:lt|gt|amp|quot|nbsp|#39);/g, m => ENT[m]);

/** 목록·검색용 순수 텍스트.
 *
 *  두 가지를 지킨다 —
 *  ① 문자 참조를 푼다. 안 그러면 `&lt;보기&gt;` 가 화면에 그대로 나온다.
 *  ② 인라인 태그는 **붙여서** 지운다. 사이에 공백을 넣으면
 *     `cm<sup>2</sup>` 가 `cm 2` 가 되어 뜻이 바뀐다. */
const INLINE_TAG = /<\/?(?:sup|sub|u|b|strong|i|em|code|span|mark)\b[^>]*>/gi;
const plain = s => unent(String(s || '').replace(INLINE_TAG, '').replace(/<[^>]+>/g, ' '))
  .replace(/\s+/g, ' ').trim();


export const CIRC = ['①', '②', '③', '④', '⑤', '⑥', '⑦'];

/** 화면에 내보낼 때 씌운다. **plain 과 반대 방향이다** */
export const esc = s => String(s).replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

/** `① (정답) …` 에서 앞의 기호를 뗀다 — 선지 옆에 붙으므로 중복이다.
 *
 *  **esc() 를 씌우면 안 된다.** 선지 단평에는 `<sup>5</sup>/<sub>72</sub>` 같은 것이
 *  들어 있어 이스케이프하면 분수 대신 태그 글자가 그대로 나온다. */
export const stripLead = s => String(s).replace(/^[①②③④⑤⑥⑦]\s*/, '');

/** 남은 시간 — 회차 타이머와 소요 시간 표시가 함께 쓴다 */
export function mmss(ms) {
  const t = Math.max(0, Math.round(ms / 1000));
  const m = String(Math.floor(t / 60)).padStart(2, '0');
  return `${m}:${String(t % 60).padStart(2, '0')}`;
}

export { plain, plain as stripTags, unent };
