/** PC 회차 안내 — 무엇을 얼마나, 얼마 동안 푸는지 먼저 보여 준다.
 *
 *  **컷오프를 지어내지 않는다.** 시안의 「Passed (Cutoff 75%)」는 기관·연도마다
 *  다르고 데이터에 없다. 정답률과 영역 구성만 보여 준다.
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
  const m = useDerived(s => ({ h: s.examHistory(tag), sit: s.sit() }), [tag]);

  if (!r) {
    return (
      <div className="empty">
        <p>없는 회차입니다 — {tag}</p>
        <button className="btn btn-tint" onClick={() => go('/exams')}>회차 목록</button>
      </div>
    );
  }

  const busy = !!m.sit && m.sit.tag !== tag;
  const mine = m.sit?.tag === tag;
  const best = m.h.length ? Math.max(...m.h.map(x => pct(x.score, x.n))) : null;

  return (
    <>
      <div className="page-head">
        <button className="btn btn-ghost" style={{ padding: 0, minHeight: 'auto' }}
                onClick={() => go('/exams')}>
          <I.Back /> 회차 목록
        </button>
        <div className="h1" style={{ marginTop: '.5rem' }}>{r.title}</div>
        <div className="row-sub">{r.brand} · {r.org}</div>
      </div>

      <div className="cols">
        <div className="stack">
          <div className="tiles" style={{ gridTemplateColumns: '1fr 1fr' }}>
            <div className="card tile">
              <div className="tile-k">문항</div>
              <div className="tile-v">{items.length}</div>
            </div>
            <div className="card tile">
              <div className="tile-k">제한 시간</div>
              <div className="tile-v">{r.min}<span style={{ fontSize: '1rem' }}>분</span></div>
            </div>
          </div>

          <div className="card pad">
            <div className="h3">영역 구성</div>
            <div style={{ marginTop: '.8rem' }}>
              {(r.areas || []).map(([area, n]) => (
                <div key={area} style={{ display: 'flex', alignItems: 'center', gap: '.7rem',
                                         padding: '.35rem 0' }}>
                  <span className="sm" style={{ flex: 1, minWidth: 0 }}>{area}</span>
                  <span className="row-n">{n}문항</span>
                  <div className="bar" style={{ width: '8rem', flex: '0 0 auto' }}>
                    <i style={{ width: Math.round((n / items.length) * 100) + '%' }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card pad">
            <div className="sm muted">
              응시를 시작하면 제한 시간이 흐릅니다. 나가도 이어서 풀 수 있고,
              <b> 제출해야</b> 진도와 복습에 남습니다. 표기하지 않은 문항은 오답입니다.
            </div>
            <div style={{ display: 'flex', gap: '.5rem', marginTop: '1rem' }}>
              <button className="btn btn-primary" style={{ flex: 1 }} disabled={busy}
                      onClick={() => {
                        if (!mine) st.startSit(tag, r.min);
                        go('/sit/' + tag);
                      }}>
                {mine ? '이어서 응시' : '응시 시작'}
              </button>
              <button className="btn btn-tint" style={{ flex: 1 }}
                      onClick={() => go(poolHref({ rd: tag }))}>
                연습 모드 — 시간 제한 없이
              </button>
            </div>
            {busy && (
              <div className="sm" style={{ marginTop: '.6rem', color: 'var(--warn)' }}>
                다른 회차를 응시 중입니다 — 응시는 하나만 둘 수 있습니다.
                <button className="btn btn-ghost" style={{ marginLeft: '.4rem', minHeight: 28 }}
                        onClick={() => go('/sit/' + m.sit.tag)}>그 회차로</button>
              </div>
            )}
          </div>
        </div>

        <div className="stack">
          {m.h.length === 0
            ? <div className="card pad">
                <div className="h3">응시 이력</div>
                <p className="sm faint" style={{ marginTop: '.5rem' }}>
                  아직 응시하지 않았습니다.
                </p>
              </div>
            : (
              <div className="card">
                <div className="pad" style={{ paddingBottom: '.6rem' }}>
                  <div className="h3">
                    응시 이력
                    <span className="badge badge-flat" style={{ marginLeft: '.4rem' }}>
                      {m.h.length}번
                    </span>
                  </div>
                  <div className="sm muted" style={{ marginTop: '.2rem' }}>
                    가장 높은 정답률 {best}%
                  </div>
                </div>
                <div className="rows">
                  {[...m.h].reverse().map((h, k) => {
                    const rate = pct(h.score, h.n);
                    return (
                      <button key={k} className="row-item" onClick={() => go('/result/' + tag)}>
                        <span className="row-t">
                          {m.h.length - k}번째
                          <span className="row-sub" style={{ display: 'block' }}>
                            {new Date(h.at).toLocaleString('ko-KR',
                              { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                            {' · '}{mmss(h.sec * 1000)}
                            {h.auto ? ' · 시간 초과 제출' : ''}
                          </span>
                        </span>
                        <span className="row-n">{h.score}/{h.n}</span>
                        <span className={'badge ' + (rate >= 60 ? 'badge-ok' : 'badge-bad')}>
                          {rate}%
                        </span>
                        <I.Chevron className="chev" />
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
        </div>
      </div>
    </>
  );
}
