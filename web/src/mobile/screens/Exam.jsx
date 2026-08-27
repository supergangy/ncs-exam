/** 회차 안내 — 무엇을 얼마나, 얼마 동안 푸는지 먼저 보여 준다.
 *
 *  들어가는 문이 둘이다.
 *    응시 시작   제한 시간·OMR·제출 후 일괄 채점 (실제 시행과 같다)
 *    연습 모드   시간 제한 없이 한 문항씩 즉시 채점 (`#/q?rd=…`)
 *
 *  **컷오프를 지어내지 않는다.** 시안에는 「Passed (Cutoff 75%)」가 있지만
 *  합격선은 기관·연도마다 다르고 데이터에 없다. 정답률만 보여 준다.
 */
import { pct } from '../../core/progress.js';
import { mmss } from '../../core/text.js';
import { poolHref } from '../../data/pool.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useStore, useDerived } from '../../store/useStore.js';

export default function Exam({ db, tag }) {
  const st = useStore();
  const r = db.round(tag);
  const items = db.byRound(tag);
  const m = useDerived(s => ({ rec: s.exam(tag), tries: s.examHistory(tag).length,
                               sit: s.sit() }), [tag]);

  if (!r) {
    return (
      <div className="empty">
        <p>없는 회차입니다 — {tag}</p>
        <button className="btn btn-tint" onClick={() => go('/exams')}>회차 목록</button>
      </div>
    );
  }

  const start = () => {
    st.startSit(tag, r.min);
    go('/sit/' + tag);
  };

  return (
    <div className="stack">
      <div className="card pad">
        <button className="btn btn-ghost" style={{ padding: 0, minHeight: 'auto' }}
                onClick={() => go('/exams')}>
          <I.Back /> 회차 목록
        </button>
        <div className="h2" style={{ marginTop: '.5rem' }}>{r.title}</div>
        <div className="row-sub">{r.brand} · {r.org}</div>

        <div className="metrics" style={{ marginTop: '.9rem' }}>
          <div className="metric" style={{ background: 'var(--hair)', borderRadius: 'var(--rx)' }}>
            <div className="metric-k">문항</div>
            <div className="metric-v">{items.length}</div>
          </div>
          <div className="metric" style={{ background: 'var(--hair)', borderRadius: 'var(--rx)' }}>
            <div className="metric-k">제한 시간</div>
            <div className="metric-v">{r.min}분</div>
          </div>
        </div>
      </div>

      <div className="card pad">
        <div className="h3">영역 구성</div>
        <div style={{ marginTop: '.6rem' }}>
          {(r.areas || []).map(([area, n]) => (
            <div key={area} style={{ display: 'flex', alignItems: 'center', gap: '.6rem',
                                     padding: '.3rem 0' }}>
              <span className="sm" style={{ flex: 1, minWidth: 0 }}>{area}</span>
              <span className="row-n">{n}문항</span>
              <div className="bar" style={{ width: '5.5rem', flex: '0 0 auto' }}>
                <i style={{ width: Math.round((n / items.length) * 100) + '%' }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {m.rec && (
        <div className="card pad">
          <div className="h3">
            지난 성적
            {m.tries > 1 && <span className="badge badge-flat"
                                  style={{ marginLeft: '.4rem' }}>{m.tries}번 응시</span>}
          </div>
          <div className="row-sub" style={{ marginTop: '.3rem' }}>
            {m.rec.score}/{m.rec.n} 맞음 · 정답률 {pct(m.rec.score, m.rec.n)}%
            · {mmss(m.rec.sec * 1000)} 걸림
            {m.rec.auto ? ' · 시간 초과로 자동 제출' : ''}
          </div>
          <button className="btn btn-outline" style={{ width: '100%', marginTop: '.8rem' }}
                  onClick={() => go('/result/' + tag)}>
            결과 자세히 보기
          </button>
        </div>
      )}

      <div className="card pad">
        <div className="sm muted">
          응시를 시작하면 제한 시간이 흐릅니다. 나가도 이어서 풀 수 있고,
          <b> 제출해야</b> 진도와 복습에 남습니다.
        </div>
        <button className="btn btn-primary" style={{ width: '100%', marginTop: '.8rem' }}
                onClick={start} disabled={!!m.sit && m.sit.tag !== tag}>
          {m.sit?.tag === tag ? '이어서 응시' : '응시 시작'}
        </button>
        {m.sit && m.sit.tag !== tag && (
          <div className="sm" style={{ marginTop: '.5rem', color: 'var(--warn)' }}>
            다른 회차를 응시 중입니다 — 응시는 하나만 둘 수 있습니다.
          </div>
        )}
        <button className="btn btn-tint" style={{ width: '100%', marginTop: '.5rem' }}
                onClick={() => go(poolHref({ rd: tag }))}>
          연습 모드로 풀기 — 시간 제한 없이
        </button>
      </div>
    </div>
  );
}
