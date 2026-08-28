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
import { poolHref, practiceKeep } from '../../data/pool.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useDerived } from '../../store/useStore.js';

export default function Kw({ db }) {
  const [q, setQ] = useState('');
  const dq = useDeferredValue(q);

  // **거르는 곳과 세는 곳이 같아야 한다.** 아직 안 본 회차의 문항은 연습 목록에
  // 나오지 않으므로 키워드 수에서도 빼야 한다 — 안 그러면 「호스트 10개」를 눌렀는데
  // 8개가 나온다(전산 회차가 들어오며 시험이 잡았다).
  const keep = useDerived(s => practiceKeep(db, s), [db]);
  const all = useMemo(() => group({ items: db.items.filter(keep), keywords: db.keywords }),
                      [db, keep]);
  // 첫 과목은 펼쳐 둔다 — 전부 접으면 무엇이 들었는지 한 번은 눌러 봐야 안다
  const [open, setOpen] = useState(() => null);
  const first = all[0]?.sj ?? null;
  const shown = open === null ? first : open;
  const groups = useMemo(() => narrow(all, dq), [all, dq]);
  const t = tally(all);
  const hit = tally(groups);
  const searching = dq.trim().length >= 2;
  const tagged = useMemo(() => db.items.filter(keep).filter(i => (i.kw || []).length).length, [db, keep]);
  // 키워드가 붙은 문항이 한 직렬에만 몰려 있나 — 그렇다면 그렇다고 적는다
  const onlyCs = useMemo(
    () => db.items.filter(keep).filter(i => (i.kw || []).length)
            .every(i => i.tr === 'cs'), [db, keep]);

  return (
    <div className="stack">
      <div className="card pad">
        <div className="h2">키워드 {t.keys}개</div>
        <div className="row-sub">과목이 달라도 같은 개념이면 함께 나옵니다.</div>
        {/* 수를 한 줄에 몰아 두면 「문 / 항」 처럼 낱말이 갈린다 — 줄을 따로 둔다 */}
        <div className="row-sub">과목 {t.areas}개 · 문항 {tagged}개에 붙어 있습니다.</div>
        {/* **전산 과목에만 붙어 있다.** 안 적으면 사무직 지원자가 자기 영역을
            찾다가 헤맨다 — 326개가 전부 전공 쪽이다 */}
        {onlyCs && (
          <div className="row-sub" style={{ marginTop: '.3rem' }}>
            지금은 <b>전산직 전공 과목</b>에만 붙어 있습니다.
            NCS 직업기초 과목에는 아직 없습니다.
          </div>
        )}
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
