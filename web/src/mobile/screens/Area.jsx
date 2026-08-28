/** 영역 → 유형 목록.
 *
 *  **결과가 0인 유형도 감추지 않는다** — 감추면 유형이 사라진 줄 안다
 *  (`core/progress.js` 의 필터 주석에 남은, 앱에서 배운 것).
 */
import { progress, progText } from '../../core/progress.js';
import { poolHref , practiceKeep } from '../../data/pool.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useDerived } from '../../store/useStore.js';

export default function Area({ db, area }) {
  const m = useDerived(s => {
    const keep = practiceKeep(db, s);
    const items = db.byArea(area, keep);
    const a = db.areas(keep).find(x => x.area === area);
    return {
      p: progress(items, s.last),
      types: (a?.types || []).map(t => ({
        ...t, p: progress(db.byType(area, t.ty, keep), s.last),
      })),
    };
  }, [db, area]);

  if (!m.types.length) {
    return (
      <div className="empty">
        <p>없는 영역입니다 — {area}</p>
        <button className="btn btn-tint" onClick={() => go('/')}>홈으로</button>
      </div>
    );
  }

  return (
    <div className="stack">
      <div className="card pad">
        <div className="h2">{area}</div>
        <div className="row-sub" style={{ marginTop: '.2rem' }}>{progText(m.p)}</div>
        <div className="bar" style={{ margin: '.7rem 0 .9rem' }}>
          <i style={{ width: m.p.fill + '%' }} />
        </div>
        <button className="btn btn-primary" style={{ width: '100%' }}
                onClick={() => go(poolHref({ sj: area }))}>
          영역 전체 풀기 ({m.p.n})
        </button>
      </div>

      <div>
        <div className="h2" style={{ margin: '.4rem 0 .6rem' }}>유형 {m.types.length}개</div>
        <div className="card rows">
          {m.types.map(t => (
            <button key={t.ty} className="row-item"
                    onClick={() => go('/s/' + encodeURIComponent(area) + '/' + encodeURIComponent(t.ty))}>
              <span className="row-t">
                {t.ty}
                <span className="row-sub" style={{ display: 'block' }}>
                  {t.p.done ? `${t.p.done}/${t.n} · 정답률 ${t.p.rate}%` : `${t.n}문항`}
                </span>
              </span>
              <I.Chevron className="chev" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
