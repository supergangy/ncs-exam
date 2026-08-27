/** 유형 → 문항 목록.
 *
 *  줄마다 마지막 시도 결과를 표시한다 — 다시 볼 것을 고르는 자리이므로
 *  「풀었나」보다 「맞혔나」가 중요하다.
 */
import { progress, progText } from '../../core/progress.js';
import { poolHref } from '../../data/pool.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useDerived } from '../../store/useStore.js';

export default function Type({ db, area, type }) {
  const m = useDerived(s => {
    const items = db.byType(area, type);
    return {
      items: items.map(it => ({
        it, last: s.last(it.id), flagged: !!s.marked(it.id)?.f,
      })),
      p: progress(items, s.last),
    };
  }, [db, area, type]);

  if (!m.items.length) {
    return (
      <div className="empty">
        <p>없는 유형입니다 — {area} · {type}</p>
        <button className="btn btn-tint" onClick={() => go('/t/' + encodeURIComponent(area))}>
          {area} 로
        </button>
      </div>
    );
  }

  return (
    <div className="stack">
      <div className="card pad">
        <button className="btn btn-ghost" style={{ padding: 0, minHeight: 'auto' }}
                onClick={() => go('/t/' + encodeURIComponent(area))}>
          <I.Back /> {area}
        </button>
        <div className="h2" style={{ marginTop: '.5rem' }}>{type}</div>
        <div className="row-sub" style={{ marginTop: '.2rem' }}>{progText(m.p)}</div>
        <div className="bar" style={{ margin: '.7rem 0 .9rem' }}>
          <i style={{ width: m.p.fill + '%' }} />
        </div>
        <button className="btn btn-primary" style={{ width: '100%' }}
                onClick={() => go(poolHref({ sj: area, ty: type }))}>
          이 유형 풀기 ({m.p.n})
        </button>
      </div>

      <div className="card rows">
        {m.items.map(({ it, last, flagged }, i) => (
          <button key={it.id} className="row-item"
                  onClick={() => go(poolHref({ sj: area, ty: type }) + '&at=' + i)}>
            <span className="row-n" style={{ minWidth: '1.6rem' }}>{i + 1}</span>
            <span className="row-t">
              <span style={{ display: 'block', overflow: 'hidden',
                             textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {db.line(it, 40)}
              </span>
            </span>
            {flagged && <I.Flag style={{ width: 15, height: 15, color: 'var(--warn-vivid)' }} />}
            {last
              ? <span className={'badge ' + (last.k ? 'badge-ok' : 'badge-bad')}>
                  {last.k ? '맞음' : '틀림'}
                </span>
              : <span className="badge badge-flat">안 품</span>}
          </button>
        ))}
      </div>
    </div>
  );
}
