/** 회차 목록.
 *
 *  응시 중인 회차가 있으면 **맨 위에 세운다.** 나갔다 돌아온 사람이 가장 먼저
 *  찾는 것이 그것이다 (`store.sit` 은 하나만 둔다).
 */
import { pct } from '../../core/progress.js';
import { mmss } from '../../core/text.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useDerived } from '../../store/useStore.js';

export default function Exams({ db }) {
  const m = useDerived(s => ({
    sit: s.sit(),
    rows: db.rounds.map(r => ({
      r,
      rec: s.exam(r.tag),                       // 가장 최근 응시
      tries: s.examHistory(r.tag).length,       // 여러 번 응시할 수 있다
      n: db.byRound(r.tag).length,
    })),
  }), [db]);

  const cur = m.sit ? db.round(m.sit.tag) : null;

  return (
    <div className="stack">
      {cur && (
        <div className="card pad" style={{ borderColor: 'var(--acc)' }}>
          <span className="badge badge-acc">응시 중</span>
          <div className="h3" style={{ marginTop: '.5rem' }}>{cur.title}</div>
          <div className="row-sub">
            {Object.keys(m.sit.ans).length} / {db.byRound(m.sit.tag).length} 표기 ·
            제한 {cur.min}분
          </div>
          <div style={{ display: 'flex', gap: '.5rem', marginTop: '.8rem' }}>
            <button className="btn btn-primary" style={{ flex: 1 }}
                    onClick={() => go('/sit/' + m.sit.tag)}>
              이어서 응시
            </button>
          </div>
        </div>
      )}

      <div className="h2" style={{ margin: '.3rem 0 0' }}>회차 {m.rows.length}개</div>

      {m.rows.map(({ r, rec, tries, n }) => (
        <button key={r.tag} className="card pad" style={{ textAlign: 'left', cursor: 'pointer' }}
                onClick={() => go('/exam/' + r.tag)}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
            <span className="h3" style={{ flex: 1, minWidth: 0 }}>{r.title}</span>
            {rec
              ? <span className={'badge ' + (pct(rec.score, rec.n) >= 60 ? 'badge-ok' : 'badge-bad')}>
                  {pct(rec.score, rec.n)}%
                </span>
              : <span className="badge badge-flat">미응시</span>}
            <I.Chevron className="chev" />
          </div>
          <div className="row-sub" style={{ marginTop: '.3rem' }}>
            {r.org} · {n}문항 · {r.min}분
            {rec && ` · ${rec.score}/${rec.n} 맞음 · ${mmss(rec.sec * 1000)} 걸림`}
            {tries > 1 && ` · ${tries}번 응시`}
          </div>
        </button>
      ))}
    </div>
  );
}
