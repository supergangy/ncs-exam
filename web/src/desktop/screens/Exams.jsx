/** PC 회차 목록 — 표로 한눈에.
 *
 *  모바일은 카드를 쌓지만 PC 는 넓다. 기관·문항·시간·성적을 **열로 세우면**
 *  회차끼리 견주기 쉽다. 응시 중인 회차는 맨 위에 따로 세운다.
 */
import { pct } from '../../core/progress.js';
import { mmss } from '../../core/text.js';
import { poolHref } from '../../data/pool.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useDerived } from '../../store/useStore.js';

export default function Exams({ db }) {
  const m = useDerived(s => ({
    sit: s.sit(),
    rows: db.rounds.map(r => ({
      r,
      n: db.byRound(r.tag).length,
      h: s.examHistory(r.tag),
      rec: s.exam(r.tag),
    })),
  }), [db]);

  const cur = m.sit ? db.round(m.sit.tag) : null;
  const tried = m.rows.filter(x => x.rec).length;

  return (
    <>
      <div className="page-head">
        <div className="h1">회차</div>
        <div className="row-sub">
          {m.rows.length}개 가운데 {tried}개 응시했습니다.
          제한 시간·OMR·제출 후 일괄 채점 — 실제 시행과 같은 구성입니다.
        </div>
      </div>

      {cur && (
        <div className="card pad" style={{ borderColor: 'var(--acc)', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '.7rem' }}>
            <span className="badge badge-acc">응시 중</span>
            <span className="h3">{cur.title}</span>
            <span className="sm muted">
              {Object.keys(m.sit.ans).length} / {db.byRound(m.sit.tag).length} 표기 ·
              제한 {cur.min}분
            </span>
            <button className="btn btn-primary" style={{ marginLeft: 'auto' }}
                    onClick={() => go('/sit/' + m.sit.tag)}>이어서 응시</button>
          </div>
        </div>
      )}

      <div className="card">
        <table className="sm" style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--line)' }}>
              {[['회차', 'left'], ['기관', 'left'], ['문항', 'right'], ['제한', 'right'],
                ['성적', 'right'], ['소요', 'right'], ['응시', 'right'], ['', 'right']].map(([h, a], i) => (
                <th key={i} style={{ textAlign: a, color: 'var(--faint)', fontWeight: 400,
                                     padding: '.7rem 1rem' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {m.rows.map(({ r, n, h, rec }) => (
              <tr key={r.tag} style={{ borderBottom: '1px solid var(--hair)' }}>
                <td style={{ padding: '.7rem 1rem', fontWeight: 'var(--w-semi)' }}>{r.title}</td>
                <td style={{ padding: '.7rem 1rem', color: 'var(--mute)' }}>{r.org}</td>
                <td className="tick" style={{ textAlign: 'right', padding: '.7rem 1rem' }}>{n}</td>
                <td className="tick" style={{ textAlign: 'right', padding: '.7rem 1rem' }}>
                  {r.min}분
                </td>
                <td style={{ textAlign: 'right', padding: '.7rem 1rem' }}>
                  {rec
                    ? <span className={'badge ' + (pct(rec.score, rec.n) >= 60 ? 'badge-ok' : 'badge-bad')}>
                        {pct(rec.score, rec.n)}% · {rec.score}/{rec.n}
                      </span>
                    : <span className="badge badge-flat">미응시</span>}
                </td>
                <td className="tick" style={{ textAlign: 'right', padding: '.7rem 1rem',
                                              color: 'var(--mute)' }}>
                  {rec ? mmss(rec.sec * 1000) : '—'}
                </td>
                <td className="tick" style={{ textAlign: 'right', padding: '.7rem 1rem',
                                              color: 'var(--faint)' }}>
                  {h.length || '—'}
                </td>
                <td style={{ textAlign: 'right', padding: '.5rem 1rem', whiteSpace: 'nowrap' }}>
                  <button className="btn btn-ghost" style={{ minHeight: 32 }}
                          onClick={() => go(poolHref({ rd: r.tag }))}>연습</button>
                  <button className="btn btn-tint" style={{ minHeight: 32, marginLeft: '.3rem' }}
                          onClick={() => go('/exam/' + r.tag)}>
                    {rec ? '다시' : '응시'} <I.Chevron style={{ width: 14, height: 14 }} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="sm faint" style={{ marginTop: '.8rem' }}>
        「연습」은 시간 제한 없이 한 문항씩 즉시 채점합니다. 「응시」는 제한 시간이 흐르고
        제출해야 성적에 남습니다.
      </p>
    </>
  );
}
