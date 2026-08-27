/** 키워드를 화면에 세울 모양으로 묶는다.
 *
 *  키워드는 **과목을 가로지르는 용어**다. 「충돌」은 데이터통신·정보보안·
 *  프로그래밍언어에 걸쳐 있다. 그래서 목록을 세울 때 세 가지를 정해야 한다.
 *
 *  ① **어느 과목 밑에 둘까**
 *     배포본은 `items.filter(...)[0].sj` — 즉 **문항 순서상 첫 번째**의 과목에
 *     두었다. 가로지르는 키워드에는 뜻이 없는 값이다. 여기서는 **문항이 가장
 *     많은 과목**에 두고, 갈리는 것에는 표를 남긴다(`spans`). 실제로 갈리는 것은
 *     326개 중 7개뿐이라 대부분은 결과가 같다.
 *
 *  ② **몇 개인가**
 *     표(`keywords[i].n`)에 적힌 수를 믿지 않고 **문항에서 다시 센다.**
 *     둘이 어긋나면 화면이 거짓을 말하고, 어긋난 것은 눌러 봐야 안다.
 *     (지금 배포본은 326개 모두 일치한다 — 그래서 더 싸게 지킬 수 있다.)
 *
 *  ③ **과목의 문항 수는 겹치는 것을 한 번만 센다**
 *     키워드별 수를 그냥 더하면 키워드 둘이 붙은 문항이 두 번 세어진다 —
 *     전자계산기구조가 「문항 118개」로 나왔는데 그 과목 문항은 36개였다. 두 걸음으로 고쳤다 —
 *     ⓐ 문항 id 의 **합집합**을 센다 (겹치는 것을 한 번만)
 *     ⓑ 그 합집합을 **이 과목 문항으로 한정**한다. 안 하면 가로지르는 키워드가
 *        다른 과목 문항을 끌고 와 37 > 36 이 된다 (시험이 잡았다)
 *     `narrow()` 뒤에도 다시 센다 — 안 그러면 「해시」 하나만 걸렸는데 머리말이
 *     「문항 87개」라고 말한다(실제로 그랬다).
 *
 *  `db` 대신 **필요한 것만** 받는다 — `{ items, keywords }`. 브라우저가 없어도 돈다.
 *  이름을 `byArea` 로 두지 마라 — `core/grade.js` 에 같은 이름이 이미 있다.
 */

/** @returns [{ sj, n, keys: [{ idx, t, n, spans, own }] }] — 과목별로 묶고 큰 것부터
 *
 *  과목의 `n` 은 **이 과목 안에서 겹치지 않게 센 문항 수**다. 키워드의 `n` 은
 *  모든 과목을 합친 수 — 가로지르는 것은 둘이 다르다. `keys[].own` 은 그 셈을
 *  `narrow()` 뒤에도 다시 하기 위해 들고 다닌다 (326개 × 몇 개라 값이 싸다).
 */
export function group({ items, keywords }) {
  // 첨자 → 과목별 문항 id
  const per = new Map();
  for (const it of items) {
    for (const k of it.kw || []) {
      const e = per.get(k) || new Map();
      e.set(it.sj, [...(e.get(it.sj) || []), it.id]);
      per.set(k, e);
    }
  }

  const groups = new Map();
  (keywords || []).forEach((k, idx) => {
    const e = per.get(idx);
    if (!e || !e.size) return;            // 문항에 붙지 않은 키워드는 세우지 않는다
    const rank = [...e].sort((a, b) => b[1].length - a[1].length
                                    || a[0].localeCompare(b[0], 'ko'));
    const sj = rank[0][0];
    const n = [...e.values()].reduce((t, ids) => t + ids.length, 0);
    const g = groups.get(sj) || { sj, n: 0, keys: [] };
    // `own` 은 **이 과목 안의** 문항이다. `n` 은 모든 과목을 합친 수 —
    // 가로지르는 키워드는 둘이 다르다. 머리말(과목 · 문항 N개)은 `own` 을 세야 한다
    g.keys.push({ idx, t: k.t ?? String(idx), n,
                  spans: e.size > 1 ? e.size : 0, own: e.get(sj) });
    groups.set(sj, g);
  });

  for (const g of groups.values()) {
    g.keys.sort((a, b) => b.n - a.n || a.t.localeCompare(b.t, 'ko'));
    g.n = distinct(g.keys);
  }
  return [...groups.values()]
    .sort((a, b) => b.keys.length - a.keys.length || b.n - a.n);
}

/** 이 과목 안에서 겹치지 않게 센 문항 수.
 *
 *  키워드별 `n` 을 그냥 더하면 두 번 세어지고(키워드 둘이 붙은 문항),
 *  `n` 을 쓰면 **다른 과목 문항까지** 들어온다 — 전자계산기구조가 37개로 나왔는데
 *  그 과목 문항은 36개였다. 그래서 `own`(이 과목 안의 id) 의 합집합을 센다. */
const distinct = keys => {
  const s = new Set();
  for (const k of keys) for (const id of k.own || []) s.add(id);
  return s.size;
};

/** 이름으로 좁힌다. 두 글자 미만이면 그대로 준다 (한 글자에 326개가 다 걸린다) */
export function narrow(groups, q) {
  const n = String(q || '').trim().toLowerCase();
  if (n.length < 2) return groups;
  return groups
    .map(g => {
      const keys = g.keys.filter(k => k.t.toLowerCase().includes(n));
      return { ...g, keys, n: distinct(keys) };   // 문항 수도 다시 센다
    })
    .filter(g => g.keys.length);
}

/** 세운 키워드·과목 수 — 「326개 중 몇 개」를 화면이 세지 않게 */
export function tally(groups) {
  return { areas: groups.length, keys: groups.reduce((s, g) => s + g.keys.length, 0) };
}
