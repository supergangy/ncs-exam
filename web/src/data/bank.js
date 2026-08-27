/** 문항 데이터 — `bank.json` 하나에 다 들어 있다. 서버에 물어보지 않는다.
 *
 *  `core/search.js` 가 요구하는 모양(`{ items, kwName, passage }`)을 맞춘다.
 *  이름 표를 첨자로 참조하는 구조라 그대로 쓰면 화면마다 풀어야 한다.
 *
 *  **콘텐츠와 기록을 섞지 않는다.** 이 파일은 읽기만 하고,
 *  사용자 기록은 `store/useStore.js` 가 따로 맡는다. 그래서 문항을
 *  새로 배포해도 푼 기록이 날아가지 않는다.
 */
import { plain } from '../core/text.js';

/** 첨자 표를 함수로 감싼다 — 없는 첨자에도 터지지 않게 */
export function wrap(raw) {
  const at = (arr, i, fb) => (Array.isArray(arr) && arr[i] != null ? arr[i] : fb);

  const db = {
    v: raw.v,
    n: raw.n ?? raw.items.length,
    items: raw.items,
    rounds: raw.rounds || [],
    tracks: raw.tracks || [],
    subjects: raw.subjects || [],
    types: raw.types || [],

    /** 키워드 표. 항목은 `{ t: 이름, n: 문항 수 }` 다 */
    keywords: raw.keywords || [],
    /** 키워드 **이름만** 준다.
     *
     *  항목이 객체라 그대로 넘기면 `core/search.js` 가 `'[object Object]'` 를 훑고
     *  **키워드로는 아무것도 안 걸린다** — 실제로 그랬다. 시험이 놓친 까닭은
     *  `kwName` 을 손으로 만든 가짜로 갈아 끼워 검사했기 때문이다.
     *  지금은 `test/core.test.js` 가 이 `wrap()` 을 실제 bank.json 으로 돌린다. */
    kwName: k => at(raw.keywords, k, null)?.t ?? String(k),
    /** 이름과 문항 수를 함께 — 키워드 목록 화면이 쓴다 */
    kw: k => at(raw.keywords, k, null),
    byKw: k => raw.items.filter(i => (i.kw || []).includes(+k)),
    passage: i => at(raw.passages, i, { body: '' }),
    // 회차 식별자는 `tag` 다 (`r1_public`). items 의 `rd` 가 이 값을 가리킨다 —
    // `r.id` 로 찾으면 늘 null 이 나온다
    round: tag => (raw.rounds || []).find(r => r.tag === tag) || null,

    /** 영역 목록 — 문항 수와 함께. 내비가 쓴다 */
    areas() {
      const m = new Map();
      for (const it of raw.items) {
        const a = m.get(it.sj) || { area: it.sj, n: 0, types: new Map() };
        a.n++;
        a.types.set(it.ty, (a.types.get(it.ty) || 0) + 1);
        m.set(it.sj, a);
      }
      return [...m.values()]
        .map(a => ({ ...a, types: [...a.types].map(([ty, n]) => ({ ty, n }))
                                              .sort((x, y) => y.n - x.n) }))
        .sort((x, y) => y.n - x.n);
    },

    byArea: sj => raw.items.filter(i => i.sj === sj),
    byType: (sj, ty) => raw.items.filter(i => i.sj === sj && i.ty === ty),
    byRound: rd => raw.items.filter(i => i.rd === rd)
                            .sort((a, b) => (a.no || 0) - (b.no || 0)),
    byId: id => raw.items.find(i => i.id === id) || null,

    /** 목록에 쓸 한 줄 — 발문에서 태그를 벗기고 길면 자른다 */
    line: (it, len = 64) => {
      const s = plain(it.st);
      return s.length > len ? s.slice(0, len - 1) + '…' : s;
    },
  };
  return db;
}

let cache = null;

/** 한 번만 받는다. 오프라인이면 Service Worker 가 캐시에서 준다 */
export async function loadBank(url = 'data/bank.json') {
  if (cache) return cache;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`문항을 받지 못했다 (${r.status})`);
  cache = wrap(await r.json());
  return cache;
}
