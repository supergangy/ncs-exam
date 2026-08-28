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

/** 아무것도 거르지 않는 체 — `keep` 을 안 넘겼을 때의 기본값 */
const ALL = () => true;

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

    /** 직렬별로 묶은 영역 목록 — `[{ tr, name, sub, areas }]`.
     *
     *  **고르게 하지 않고 묶어서 보인다.** 전산직 지원자도 NCS 직업기초를 보므로
     *  둘 중 하나를 감추면 틀린다. 앱(`mobile/lib/screens/home_screen.dart`)도
     *  같은 모양이다 — 직렬 카드 둘을 나란히 두고 들어가게 한다.
     *
     *  섞어 놓으면 사무직 지원자에게 데이터베이스론·네트워크가, 전산직에게
     *  대인관계능력이 한 줄에 뒤섞여 나온다(영역 18개). */
    byTrack(keep = ALL) {
      const all = db.areas(keep);
      // NCS 를 먼저 둔다 — 모든 지원자가 보는 것이고, 전공은 그 위에 얹힌다.
      // `bank.json` 의 tracks 차례는 전산이 앞이라 그대로 쓰면 뒤집힌다
      const order = ['ncs', 'cs'];
      return [...(raw.tracks || [])]
        .sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id))
        .map(t => ({ tr: t.id, name: t.name, sub: t.sub,
                     areas: all.filter(a => a.tr === t.id) }))
        .filter(g => g.areas.length)
        .map(g => ({ ...g, n: g.areas.reduce((s2, a) => s2 + a.n, 0) }));
    },

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
    byKw: (k, keep = ALL) => raw.items.filter(i => (i.kw || []).includes(+k) && keep(i)),
    passage: i => at(raw.passages, i, { body: '' }),
    // 회차 식별자는 `tag` 다 (`r1_public`). items 의 `rd` 가 이 값을 가리킨다 —
    // `r.id` 로 찾으면 늘 null 이 나온다
    round: tag => (raw.rounds || []).find(r => r.tag === tag) || null,

    /** 영역 목록 — 문항 수와 함께. 내비가 쓴다.
     *
     *  `keep` 은 **연습에서 보일 문항**을 고르는 함수다(`data/pool.js` 의 `practiceKeep`).
     *  세는 수와 실제로 풀리는 목록이 어긋나면, 「104문항」을 보고 들어갔는데
     *  43개만 나오는 일이 생긴다. 그래서 같은 체를 여기에도 통과시킨다. */
    areas(keep = ALL) {
      const m = new Map();
      for (const it of raw.items.filter(keep)) {
        // `tr` 을 함께 실어 보낸다 — 화면이 직렬로 묶는 데 쓴다.
        // 한 영역의 문항은 모두 같은 직렬이다(전산 과목이 NCS 에 섞이지 않는다)
        const a = m.get(it.sj) || { area: it.sj, tr: it.tr, n: 0, types: new Map() };
        a.n++;
        a.types.set(it.ty, (a.types.get(it.ty) || 0) + 1);
        m.set(it.sj, a);
      }
      return [...m.values()]
        .map(a => ({ ...a, types: [...a.types].map(([ty, n]) => ({ ty, n }))
                                              .sort((x, y) => y.n - x.n) }))
        .sort((x, y) => y.n - x.n);
    },

    byArea: (sj, keep = ALL) => raw.items.filter(i => i.sj === sj && keep(i)),
    byType: (sj, ty, keep = ALL) =>
      raw.items.filter(i => i.sj === sj && i.ty === ty && keep(i)),
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
