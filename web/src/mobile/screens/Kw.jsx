/** 키워드 — 과목을 가로지르는 용어로 문항을 묶는다.
 *
 *  **326개를 그냥 늘어놓으면 못 찾는다.** 배포본은 칩을 통째로 펼쳤는데, 폰에서는
 *  스크롤이 끝나지 않는다. 찾는 칸을 위에 두고, 과목별로 접어 둔다.
 *
 *  묶는 규칙은 화면이 정하지 않는다 — `core/keywords.js` 가 정하고 시험을 받는다.
 *
 *  **키워드는 전산직 문항에만 붙어 있다**(764개 중 277개). 없는 과목을 찾다 헤매지
 *  않게 그것을 적어 둔다. 수를 코드에 적지 않고 `db` 에서 세어 낸다.
 */
import { useDeferredValue, useMemo, useState } from 'react';

import { group, narrow, tally } from '../../core/keywords.js';
import { poolHref } from '../../data/pool.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';

export default function Kw({ db }) {
  const [q, setQ] = useState('');
  const dq = useDeferredValue(q);

  const all = useMemo(() => group(db), [db]);
  // 첫 과목은 펼쳐 둔다 — 전부 접으면 무엇이 들었는지 한 번은 눌러 봐야 안다
  const [open, setOpen] = useState(() => null);
  const first = all[0]?.sj ?? null;
  const shown = open === null ? first : open;
  const groups = useMemo(() => narrow(all, dq), [all, dq]);
  const t = tally(all);
  const hit = tally(groups);
  const searching = dq.trim().length >= 2;
  const tagged = useMemo(() => db.items.filter(i => (i.kw || []).length).length, [db]);

  return (
    <div className="stack">
      <div className="card pad">
        <div className="h2">키워드 {t.keys}개</div>
        <div className="row-sub">과목이 달라도 같은 개념이면 함께 나옵니다.</div>
        {/* 수를 한 줄에 몰아 두면 「문 / 항」 처럼 낱말이 갈린다 — 줄을 따로 둔다 */}
        <div className="row-sub">과목 {t.areas}개 · 문항 {tagged}개에 붙어 있습니다.</div>
      </div>

      <div className="search">
        <input className="field" value={q} onChange={e => setQ(e.target.value)}
               placeholder="키워드 찾기 (두 글자 이상)" aria-label="키워드 찾기" />
        {q && (
          <button className="btn btn-ghost"
                  style={{ position: 'absolute', right: '.3rem', minHeight: 30,
                           padding: '0 .4rem' }}
                  onClick={() => setQ('')} aria-label="지우기">
            <I.Close />
          </button>
        )}
      </div>

      {searching && (
        <p className="sm">
          <b>{hit.keys}</b>개 걸렸습니다{hit.keys ? ` · 과목 ${hit.areas}개` : ''}
        </p>
      )}

      {!groups.length
        ? <p className="empty sm">「{dq}」로는 찾지 못했습니다.</p>
        : groups.map(g => {
            // 찾는 중에는 다 펼친다 — 걸린 것을 또 눌러 열게 하면 두 번 일이다
            const on = searching || shown === g.sj;
            return (
              <div className="card" key={g.sj}>
                <button className="row-item"
                        onClick={() => setOpen(on ? '' : g.sj)}
                        aria-expanded={on}>
                  <span className="row-t">
                    {g.sj}
                    <span className="row-sub" style={{ display: 'block' }}>
                      키워드 {g.keys.length}개 · 이 과목 문항 {g.n}개
                    </span>
                  </span>
                  <I.Chevron className="chev"
                             style={{ transform: on ? 'rotate(90deg)' : undefined }} />
                </button>
                {on && (
                  <div className="chips">
                    {g.keys.map(k => (
                      <button key={k.idx} className="chip"
                              onClick={() => go(poolHref({ kw: k.idx }))}
                              title={k.spans ? `과목 ${k.spans}개에 걸쳐 있습니다` : undefined}
                              aria-label={`${k.t} — 문항 ${k.n}개`
                                          + (k.spans ? ` · 과목 ${k.spans}개에 걸쳐 있음` : '')}>
                        {k.t}
                        {/* 가로지르는 것에 표를 남긴다 — 326개 중 7개다.
                            글자는 aria-label 이 대신 읽으므로 여기서는 감춘다 */}
                        {k.spans ? <em aria-hidden="true">↔</em> : null}
                        <b aria-hidden="true">{k.n}</b>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
    </div>
  );
}
