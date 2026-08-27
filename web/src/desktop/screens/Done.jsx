/** PC 묶음 마침 — 방금 푼 묶음을 어떻게 풀었나.
 *
 *  모바일과 같은 값을 본다(`store.passOf`). PC 라서 다른 것은 **목록을 표로 세워**
 *  걸린 시간과 시도 횟수를 나란히 견줄 수 있게 한 것뿐이다.
 *
 *  회차 결과(`/result`)와 다르다 — 저쪽은 제한 시간과 OMR 이 있는 응시의 성적표다.
 */
import { useState } from 'react';

import { pct } from '../../core/progress.js';
import { mmss } from '../../core/text.js';
import { makePool, poolHref } from '../../data/pool.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useDerived } from '../../store/useStore.js';

export default function Done({ db }) {
  const [only, setOnly] = useState('all');

  const d = useDerived(s => {
    const solo = s.solo();
    if (!solo) return null;

    const order = new Map((solo.ids || []).map((id, i) => [id, i]));
    const rows = db.items.filter(i => order.has(i.id))
      .sort((a, b) => order.get(a.id) - order.get(b.id))
      .map(it => ({ it, pass: s.passOf(it.id, solo.t), now: s.isWrong(it.id) }));

    const passed = rows.filter(r => r.pass);
    const ok = passed.filter(r => r.pass.ok).length;

    return {
      title: makePool(db, s, solo.key).title,
      key: solo.key,
      rows, n: rows.length, done: passed.length, ok,
      rate: pct(ok, passed.length),
      ms: passed.reduce((t, r) => t + r.pass.ms, 0),
      missed: passed.length - ok,
      wrong: rows.filter(r => r.now).length,
    };
  }, [db]);

  if (!d) {
    return (
      <div className="empty">
        <p style={{ fontWeight: 700, color: 'var(--ink)' }}>최근에 푼 묶음이 없습니다</p>
        <p className="sm">문항 은행에서 영역이나 유형을 골라 풀면 여기에 결과가 남습니다.</p>
        <button className="btn btn-tint" style={{ marginTop: '1rem' }}
                onClick={() => go('/bank')}>문항 은행으로</button>
      </div>
    );
  }

  if (!d.done) {
    return (
      <div className="empty">
        <p style={{ fontWeight: 700, color: 'var(--ink)' }}>아직 채점한 것이 없습니다</p>
        <p className="sm">{d.title} · {d.n}문항</p>
        <button className="btn btn-primary" style={{ marginTop: '1rem' }}
                onClick={() => go('/q?' + d.key)}>이어서 풀기</button>
      </div>
    );
  }

  const rows = only === 'wrong' ? d.rows.filter(r => r.pass && !r.pass.ok) : d.rows;
  const tone = d.rate >= 80 ? 'bar-ok' : d.rate >= 50 ? 'bar-warn' : 'bar-bad';

  return (
    <>
      <div className="page-head">
        <div className="h1">{d.title} 마침</div>
        <div className="row-sub">
          {d.done}문항 중 {d.ok}개를 맞혔습니다
          {d.done < d.n ? ` · ${d.n - d.done}문항은 건너뛰었습니다` : ''}
        </div>
      </div>

      <div className="tiles">
        {[['정답률', d.rate + '%', `${d.ok} / ${d.done} 맞음`],
          ['걸린 시간', mmss(d.ms), `문항당 ${mmss(Math.round(d.ms / d.done))}`],
          ['이번에 틀림', d.missed, d.missed ? '아래 목록에 있습니다' : '전부 맞혔습니다'],
          ['오답노트', d.wrong,
           d.wrong > d.missed ? `건너뛴 ${d.wrong - d.missed}개 포함`
                              : '마지막 시도가 오답인 것']].map(([k, v, s]) => (
          <div className="card pad" key={k}>
            <div className="row-sub">{k}</div>
            <div className="h2 tick" style={{ margin: '.15rem 0 .1rem' }}>{v}</div>
            <div className="sm faint">{s}</div>
          </div>
        ))}
      </div>

      <div className={'bar ' + tone} style={{ margin: '1rem 0' }}>
        <i style={{ width: d.rate + '%' }} />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem',
                    marginBottom: '.8rem', flexWrap: 'wrap' }}>
        {[['all', `전체 ${d.n}`], ['wrong', `틀린 것 ${d.missed}`]].map(([v, label]) => (
          <button key={v} className={'btn ' + (only === v ? 'btn-tint' : 'btn-ghost')}
                  style={{ minHeight: 32 }} onClick={() => setOnly(v)}
                  aria-pressed={only === v}>{label}</button>
        ))}
        <span style={{ marginLeft: 'auto', display: 'flex', gap: '.4rem' }}>
          {d.wrong > 0 && (
            <button className="btn btn-primary"
                    onClick={() => go(poolHref({ pool: 'wrong' }))}>
              <I.Pencil />오답노트 {d.wrong}개 다시 풀기
            </button>
          )}
          <button className="btn btn-outline" onClick={() => go('/bank')}>문항 은행</button>
        </span>
      </div>

      {!rows.length
        ? <p className="empty sm">이번에 틀린 것이 없습니다.</p>
        : (
          <div className="card" style={{ overflowX: 'auto' }}>
            <table className="sm" style={{ width: '100%', minWidth: '44rem' }}>
              <thead>
                <tr>
                  {['', '영역 · 유형', '발문', '시도', '걸린 시간', ''].map((h, i) => (
                    <th key={i} style={{ textAlign: i >= 3 ? 'right' : 'left' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map(({ it, pass }) => (
                  <tr key={it.id} onClick={() => go(poolHref({ id: it.id }))}
                      style={{ cursor: 'pointer' }}>
                    <td><Tag pass={pass} /></td>
                    <td className="faint" style={{ whiteSpace: 'nowrap' }}>
                      {it.sj} · {it.ty}
                    </td>
                    <td>{db.line(it, 60)}</td>
                    <td className="tick" style={{ textAlign: 'right' }}>
                      {pass ? pass.n : '—'}
                    </td>
                    <td className="tick" style={{ textAlign: 'right' }}>
                      {pass ? mmss(pass.ms) : '—'}
                    </td>
                    <td style={{ textAlign: 'right' }}><I.Chevron className="chev" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
    </>
  );
}

/** 세 가지뿐이다.
 *
 *  「나중에 고쳤다」를 넷째로 두려 했는데 **도달할 수 없는 상태**였다.
 *  `passOf` 의 창은 `solo.t` 이후로 **끝이 없으므로**, 이 묶음을 푼 뒤 오답노트에서
 *  다시 맞혀도 그 시도가 창 안에 들어온다 — 즉 `pass.ok` 는 늘 `!isWrong` 이다.
 *  그래서 화면의 수는 **지금 기준**이고, 그것이 새로 고쳐도 값이 같은 이유다. */
function Tag({ pass }) {
  const [cls, text] = !pass ? ['badge-flat', '건너뜀']
                    : pass.ok ? ['badge-ok', '맞음']
                    : ['badge-bad', '틀림'];
  return <span className={'badge ' + cls}>{text}</span>;
}
