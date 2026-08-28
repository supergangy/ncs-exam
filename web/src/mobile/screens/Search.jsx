/** 전문 검색 — `core/search.js` 가 찾고, 여기서는 **걸린 곳을 함께 보여 준다.**
 *
 *  「발문」인지 「선지 ③」인지 「해설」인지 알려 주지 않으면, 목록에 왜 그 문항이
 *  나왔는지 알 수 없다. core 가 `where` 와 `snip` 을 함께 주는 이유다.
 *
 *  찾는 즉시 세지 않는다 — 764문항 × 7층을 글자마다 훑으면 입력이 끊긴다.
 *  `deferredValue` 로 입력을 먼저 받고 셈은 뒤따르게 한다.
 */
import { useDeferredValue, useState } from 'react';

import { search } from '../../core/search.js';
import { lockedRounds, poolHref } from '../../data/pool.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useStore } from '../../store/useStore.js';

export default function Search({ db }) {
  const st = useStore();
  const [q, setQ] = useState('');
  const dq = useDeferredValue(q);
  // 검색은 **막지 않는다.** 낱말을 치고 그 줄을 고른 것은 대놓고 고른 것이다.
  // 다만 아직 안 본 회차의 문항이면 표를 붙여 알려 준다
  const lock = lockedRounds(db, st);
  const hits = dq.trim().length >= 2 ? search(dq, db) : [];
  const slow = q !== dq;

  return (
    <div className="stack">
      <div className="search">
        <input className="field" value={q} onChange={e => setQ(e.target.value)}
               placeholder="발문·선지·해설에서 찾기" autoFocus
               aria-label="문항 전문 검색" />
        {q && (
          <button className="btn btn-ghost" style={{ position: 'absolute', right: '.3rem',
                       padding: '0 .4rem', minHeight: '2rem' }}
                  onClick={() => setQ('')} aria-label="지우기">
            <I.Close />
          </button>
        )}
      </div>

      {q.trim().length === 1 && (
        <p className="sm faint">두 글자 이상 넣어 주세요.</p>
      )}

      {dq.trim().length >= 2 && (
        <>
          <div className="qmeta">
            <span>{hits.length}문항</span>
            {slow && <span className="faint">찾는 중…</span>}
          </div>

          {hits.length === 0
            ? <p className="empty sm">「{dq}」로는 찾지 못했습니다.</p>
            : (
              <div className="card rows">
                {hits.slice(0, 60).map(({ it, where, snip }) => (
                  <button key={it.id} className="row-item"
                          onClick={() => go(poolHref({ id: it.id }))}>
                    <span className="row-t">
                      <span style={{ display: 'block' }}>{db.line(it, 44)}</span>
                      <span className="row-sub" style={{ display: 'block' }}>
                        <span className="badge badge-flat" style={{ marginRight: '.35rem' }}>
                          {where}
                        </span>
                        {/* 아직 안 본 회차의 문항이면 알려 준다 — 검색은 막지 않되,
                            눌러 열면 그 회차를 태운다는 것을 모르고 누르면 안 된다 */}
                        {lock.has(it.rd) && (
                          <span className="badge badge-warn" style={{ marginRight: '.35rem' }}>
                            회차
                          </span>
                        )}
                        {snip || `${it.sj} · ${it.ty}`}
                      </span>
                    </span>
                    <I.Chevron className="chev" />
                  </button>
                ))}
              </div>
            )}

          {hits.length > 60 && (
            <p className="sm faint" style={{ textAlign: 'center' }}>
              앞의 60문항만 보입니다 — 찾는 말을 좁혀 보세요.
            </p>
          )}
        </>
      )}
    </div>
  );
}
