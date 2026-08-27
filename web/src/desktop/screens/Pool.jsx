/** 오답노트 · 복습 · 표시해 둔 문항 — **한 화면이 셋을 맡는다.**
 *
 *  구성이 같다 — 무엇이 왜 모였는지 알리고, 목록을 보이고, 「전부 풀기」로 넘긴다.
 *  세 파일로 나누면 한쪽만 고쳐 어긋난다.
 *
 *  PC 는 넓으므로 영역·유형·상태를 **열로 세운다** — 어디가 몰렸는지 보인다.
 */
import { CIRC } from '../../core/text.js';
import { makePool, poolHref } from '../../data/pool.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useStore, useDerived } from '../../store/useStore.js';

const EMPTY = {
  wrong: '틀린 문항이 여기 모입니다. 다시 맞히면 자동으로 빠집니다.',
  review: '지금 다시 볼 문항이 없습니다. 풀고 나면 SM-2 간격으로 돌아옵니다.',
  marks: '문항 화면의 「표시」를 누르면 여기 모입니다.',
};

export default function Pool({ db, kind }) {
  const st = useStore();
  const pool = makePool(db, st, 'pool=' + kind);
  const m = useDerived(s => {
    const rows = pool.items.map(it => ({
      it, last: s.last(it.id), until: s.untilText(it.id), flag: !!s.marked(it.id)?.f,
    }));
    // 어느 영역에 몰렸나 — 많은 순
    const by = new Map();
    for (const { it } of rows) by.set(it.sj, (by.get(it.sj) || 0) + 1);
    return { rows, byArea: [...by].sort((a, b) => b[1] - a[1]) };
  }, [db, kind, pool.items.length]);

  if (!m.rows.length) {
    return (
      <div className="empty">
        <p style={{ fontWeight: 700, color: 'var(--ink)' }}>{pool.title}</p>
        <p className="sm">{EMPTY[kind]}</p>
        <button className="btn btn-tint" style={{ marginTop: '1rem' }} onClick={() => go('/bank')}>
          문항 고르기
        </button>
      </div>
    );
  }

  return (
    <>
      <div className="page-head">
        <div className="h1">{pool.title}</div>
        <div className="row-sub">
          {m.rows.length}문항{pool.sub ? ` · ${pool.sub}` : ''}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem', flexWrap: 'wrap',
                    marginBottom: '1rem' }}>
        <button className="btn btn-primary" onClick={() => go(poolHref({ pool: kind }))}>
          전부 풀기 ({m.rows.length})
        </button>
        <span className="sm faint" style={{ marginLeft: '.5rem' }}>몰린 영역</span>
        {m.byArea.slice(0, 5).map(([area, n]) => (
          <button key={area} className="badge badge-flat"
                  style={{ border: 0, cursor: 'pointer', font: 'inherit',
                           fontSize: 'var(--t-sm)', fontWeight: 'var(--w-bold)' }}
                  onClick={() => go('/t/' + encodeURIComponent(area))}>
            {area} {n}
          </button>
        ))}
      </div>

      <div className="card">
        <table className="sm" style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--line)' }}>
              {[['#', 'right'], ['문항', 'left'], ['영역 · 유형', 'left'],
                [kind === 'review' ? '복습' : '지난 시도', 'left'], ['', 'right']].map(([h, a], i) => (
                <th key={i} style={{ textAlign: a, color: 'var(--faint)', fontWeight: 400,
                                     padding: '.6rem 1rem' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {m.rows.map(({ it, last, until, flag }, i) => (
              <tr key={it.id} style={{ borderBottom: '1px solid var(--hair)', cursor: 'pointer' }}
                  onClick={() => go(poolHref({ pool: kind }) + '&at=' + i)}>
                <td className="tick" style={{ textAlign: 'right', padding: '.6rem 1rem',
                                              color: 'var(--faint)' }}>{i + 1}</td>
                <td style={{ padding: '.6rem 1rem', maxWidth: '32rem' }}>
                  <span style={{ display: 'block', overflow: 'hidden',
                                 textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {db.line(it, 70)}
                  </span>
                </td>
                <td style={{ padding: '.6rem 1rem', color: 'var(--mute)' }}>
                  {it.sj} · {it.ty}
                </td>
                <td style={{ padding: '.6rem 1rem', color: 'var(--mute)' }}>
                  {kind === 'review'
                    ? (until || '—')
                    : last
                      ? (last.k
                          ? '맞음'
                          : `고른 것 ${CIRC[last.c - 1] || '—'} · 정답 ${CIRC[it.an - 1]}`)
                      : '안 품'}
                </td>
                <td style={{ textAlign: 'right', padding: '.6rem 1rem', whiteSpace: 'nowrap' }}>
                  {flag && <I.Flag style={{ width: 15, height: 15,
                                            color: 'var(--warn-vivid)' }} />}
                  <I.Chevron className="chev" style={{ marginLeft: '.4rem',
                                                       verticalAlign: 'middle' }} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
