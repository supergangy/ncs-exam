/** PC 전문 검색 — `core/search.js` 가 찾고, 여기서는 **걸린 곳을 함께 보여 준다.**
 *
 *  「발문」인지 「선지 ③」인지 「해설」인지 알려 주지 않으면 왜 그 문항이 나왔는지
 *  알 수 없다. core 가 `where` 와 `snip` 을 함께 주는 이유다.
 *
 *  764문항 × 7층을 글자마다 훑으면 입력이 끊긴다 — `useDeferredValue` 로
 *  입력을 먼저 받고 셈은 뒤따르게 한다.
 *
 *  PC 는 넓으므로 **걸린 곳별로 몇 건인지** 함께 세어 보여 준다.
 */
import { useDeferredValue, useEffect, useRef, useState } from 'react';

import { search } from '../../core/search.js';
import { lockedRounds, poolHref } from '../../data/pool.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useStore } from '../../store/useStore.js';

const LIMIT = 120;

export default function Search({ db }) {
  const st = useStore();
  const [q, setQ] = useState('');
  const [where, setWhere] = useState(null);      // 걸린 곳으로 좁히기
  const box = useRef(null);
  const dq = useDeferredValue(q);
  const slow = q !== dq;

  useEffect(() => { box.current?.focus(); }, []);

  // 검색은 **막지 않는다.** 낱말을 치고 그 줄을 고른 것은 대놓고 고른 것이다.
  // 다만 아직 안 본 회차의 문항이면 표를 붙여 알려 준다
  const lock = lockedRounds(db, st);
  const all = dq.trim().length >= 2 ? search(dq, db) : [];
  const counts = new Map();
  for (const h of all) counts.set(h.where, (counts.get(h.where) || 0) + 1);
  const hits = where ? all.filter(h => h.where === where) : all;

  return (
    <>
      <div className="page-head">
        <div className="h1">전문 검색</div>
        <div className="row-sub">
          발문 · 선지 · 분류 · 키워드 · 자료 · 지문 · 해설 일곱 층을 훑습니다.
        </div>
      </div>

      <div className="search" style={{ maxWidth: '38rem', marginBottom: '1rem' }}>
        <input ref={box} className="field" value={q} onChange={e => { setQ(e.target.value); setWhere(null); }}
               placeholder="찾을 말을 넣으세요 (두 글자 이상)"
               aria-label="문항 전문 검색" />
        {q && (
          <button className="btn btn-ghost" style={{ position: 'absolute', right: '.3rem',
                       minHeight: 30, padding: '0 .4rem' }}
                  onClick={() => { setQ(''); setWhere(null); box.current?.focus(); }}
                  aria-label="지우기">
            <I.Close />
          </button>
        )}
      </div>

      {q.trim().length === 1 && <p className="sm faint">두 글자 이상 넣어 주세요.</p>}

      {dq.trim().length >= 2 && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem',
                        flexWrap: 'wrap', marginBottom: '.9rem' }}>
            <span className="sm">
              <b>{all.length}</b>문항{slow && <span className="faint"> · 찾는 중…</span>}
            </span>
            {all.length > 0 && (
              <>
                <button className={'btn ' + (where === null ? 'btn-tint' : 'btn-ghost')}
                        style={{ minHeight: 30 }} onClick={() => setWhere(null)}>전체</button>
                {[...counts].sort((a, b) => b[1] - a[1]).map(([w, n]) => (
                  <button key={w} className={'btn ' + (where === w ? 'btn-tint' : 'btn-ghost')}
                          style={{ minHeight: 30 }} onClick={() => setWhere(w)}>
                    {w} {n}
                  </button>
                ))}
              </>
            )}
          </div>

          {all.length === 0
            ? <p className="empty sm">「{dq}」로는 찾지 못했습니다.</p>
            : (
              <div className="card">
                <div className="rows">
                  {hits.slice(0, LIMIT).map(({ it, where: w, snip }) => (
                    <button key={it.id} className="row-item"
                            onClick={() => go(poolHref({ id: it.id }))}>
                      <span className="badge badge-flat" style={{ flex: '0 0 auto' }}>{w}</span>
                      {/* 아직 안 본 회차의 문항 — 열면 그 회차를 태운다 */}
                      {lock.has(it.rd) && (
                        <span className="badge badge-warn" style={{ flex: '0 0 auto' }}>회차</span>
                      )}
                      <span className="row-t">
                        <span style={{ display: 'block' }}>{db.line(it, 84)}</span>
                        <span className="row-sub" style={{ display: 'block' }}>
                          {snip || `${it.sj} · ${it.ty}`}
                        </span>
                      </span>
                      <span className="row-n" style={{ whiteSpace: 'nowrap' }}>
                        {it.sj}
                      </span>
                      <I.Chevron className="chev" />
                    </button>
                  ))}
                </div>
                {hits.length > LIMIT && (
                  <p className="sm faint" style={{ padding: '.8rem 1.25rem', textAlign: 'center' }}>
                    앞의 {LIMIT}문항만 보입니다 — 찾는 말을 좁히거나 걸린 곳으로 나눠 보세요.
                  </p>
                )}
              </div>
            )}
        </>
      )}

      {!q && (
        <div className="card pad" style={{ maxWidth: '38rem' }}>
          <div className="h3">이렇게 찾을 수 있습니다</div>
          <ul className="sm muted" style={{ margin: '.6rem 0 0', paddingLeft: '1.1rem',
                                            lineHeight: 1.9 }}>
            <li>낱말 — <b>가중평균</b>, <b>정규화</b>, <b>DHCP</b></li>
            <li>영역·유형 이름 — <b>자료해석</b>, <b>조건추론</b></li>
            <li>해설에 나온 말 — <b>공동 1위</b>, <b>순열</b></li>
          </ul>
          <div className="sm faint" style={{ marginTop: '.7rem' }}>
            어느 층에서 걸렸는지 함께 표시하므로, 왜 그 문항이 나왔는지 알 수 있습니다.
          </div>
        </div>
      )}
    </>
  );
}
