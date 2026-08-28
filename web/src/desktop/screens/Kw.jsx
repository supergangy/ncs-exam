/** PC 키워드 — 과목을 가로지르는 용어.
 *
 *  모바일은 과목을 접어 두고 하나씩 펼친다(스크롤이 끝나지 않으므로). PC 는 넓으니
 *  **접지 않는다** — 과목을 2열로 나란히 두고 326개를 한눈에 훑게 한다.
 *
 *  묶는 규칙은 `core/keywords.js` 다. 모바일과 같은 것을 쓴다 — 두 벌이면
 *  같은 키워드가 판마다 다른 과목에 붙는다.
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
  const groups = useMemo(() => narrow(all, dq), [all, dq]);
  const t = tally(all);
  const hit = tally(groups);
  const searching = dq.trim().length >= 2;
  const tagged = useMemo(() => db.items.filter(i => (i.kw || []).length).length, [db]);
  // 키워드가 붙은 문항이 한 직렬에만 몰려 있나 — 그렇다면 그렇다고 적는다
  const onlyCs = useMemo(
    () => db.items.filter(i => (i.kw || []).length).every(i => i.tr === 'cs'), [db]);
  const spans = useMemo(
    () => all.reduce((s, g) => s + g.keys.filter(k => k.spans).length, 0), [all]);

  return (
    <>
      <div className="page-head">
        <div className="h1">키워드</div>
        <div className="row-sub">
          과목이 달라도 같은 개념이면 함께 나옵니다. 키워드 {t.keys}개 ·
          과목 {t.areas}개 · 문항 {tagged}개에 붙어 있습니다.
        </div>
        {/* 326개가 전부 전공 쪽이다. 안 적으면 사무직 지원자가 헤맨다 */}
        {onlyCs && (
          <div className="row-sub" style={{ marginTop: '.2rem' }}>
            지금은 <b>전산직 전공 과목</b>에만 붙어 있습니다.
            NCS 직업기초 과목에는 아직 없습니다.
          </div>
        )}
      </div>

      <div className="search" style={{ maxWidth: '30rem', marginBottom: '1rem' }}>
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
        <p className="sm" style={{ marginBottom: '.8rem' }}>
          <b>{hit.keys}</b>개 걸렸습니다{hit.keys ? ` · 과목 ${hit.areas}개` : ''}
        </p>
      )}

      {!groups.length
        ? <p className="empty sm">「{dq}」로는 찾지 못했습니다.</p>
        : (
          <>
            <div className="cols">
              {[0, 1].map(col => (
                <div className="stack" key={col}>
                  {groups.filter((_, i) => i % 2 === col).map(g => (
                    <div className="card" key={g.sj}>
                      <div className="pad" style={{ paddingBottom: '.4rem' }}>
                        <div className="h3">{g.sj}</div>
                        <div className="row-sub">
                          키워드 {g.keys.length}개 · 이 과목 문항 {g.n}개
                        </div>
                      </div>
                      <div className="chips">
                        {g.keys.map(k => (
                          <button key={k.idx} className="chip"
                                  onClick={() => go(poolHref({ kw: k.idx }))}
                                  title={k.spans ? `과목 ${k.spans}개에 걸쳐 있습니다`
                                                 : undefined}
                                  aria-label={`${k.t} — 문항 ${k.n}개`
                                    + (k.spans ? ` · 과목 ${k.spans}개에 걸쳐 있음` : '')}>
                            {k.t}
                            {k.spans ? <em aria-hidden="true">↔</em> : null}
                            <b aria-hidden="true">{k.n}</b>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>

            {!searching && spans > 0 && (
              <p className="sm faint" style={{ marginTop: '1rem' }}>
                <b>↔</b> 표가 붙은 {spans}개는 과목을 가로지릅니다 — 문항이 가장 많은
                과목 밑에 두었습니다.
              </p>
            )}
          </>
        )}
    </>
  );
}
