/** 문항 은행 — 영역 | 유형 | 문항을 **한 화면에** 펼친다.
 *
 *  모바일은 세 화면을 오가야 하지만 PC 는 넓다. 고르는 동안 앞뒤가 함께 보이면
 *  「이 유형이 몇 문항이고 내가 얼마나 풀었나」를 견주기 쉽다.
 *
 *  주소는 모바일 판과 같다 — `/bank`(고른 것 없음) · `/t/영역` · `/s/영역/유형`.
 *  칸을 누르면 주소가 바뀌므로 뒤로 가기가 그대로 듣는다.
 *
 *  **결과가 0인 유형도 감추지 않는다** — 감추면 유형이 사라진 줄 안다
 *  (`core/progress.js` 의 필터 주석에 남은, 앱에서 배운 것).
 */
import { progress, progText } from '../../core/progress.js';
import { poolHref , practiceKeep } from '../../data/pool.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useDerived } from '../../store/useStore.js';

export default function Bank({ db, area = null, type = null }) {
  const m = useDerived(s => {
    const keep = practiceKeep(db, s);
    const areas = db.areas(keep).map(a => ({
      area: a.area, types: a.types, ...progress(db.byArea(a.area, keep), s.last),
    }));
    const cur = areas.find(a => a.area === area) || null;
    const types = cur
      ? cur.types.map(t => ({ ...t, ...progress(db.byType(area, t.ty, keep), s.last) }))
      : [];
    const items = area && type
      ? db.byType(area, type, keep).map(it => ({
          it, last: s.last(it.id), flag: !!s.marked(it.id)?.f,
        }))
      : [];
    const locked = db.items.length - db.items.filter(keep).length;
    // 직렬로 묶는다 — 섞어 놓으면 사무직에게 데이터베이스론이,
    // 전산직에게 대인관계능력이 한 칸에 뒤섞여 나온다(영역 18개)
    const byName = new Map(areas.map(a => [a.area, a]));
    const tracks = db.byTrack(keep)
      .map(g => ({ ...g, areas: g.areas.map(a => byName.get(a.area)) }));
    return { areas, cur, types, items, locked, tracks };
  }, [db, area, type]);

  return (
    <>
      <div className="page-head">
        <div className="h1">문항 은행</div>
        <div className="row-sub">
          영역 {m.areas.length}개 · 문항 {db.n - m.locked}개.
          {' '}영역과 유형을 골라 한 문항씩 풉니다.
        </div>
        {/* 감춘 것이 있으면 말한다. `db.n` 을 그대로 적으면 목록과 어긋난다 */}
        {m.locked > 0 && (
          <div className="sm faint" style={{ marginTop: '.3rem' }}>
            아직 응시하지 않은 회차의 {m.locked}문항은 빼고 셌습니다 —
            회차를 제출하면 여기 합류합니다. 먼저 풀어 보려면 회차 안내의
            「연습 모드로 풀기」를 쓰세요.
          </div>
        )}
      </div>

      <div className="bank">
        {/* 1단 — 영역 */}
        <div className="card bank-col">
          <div className="bank-h">
            <span className="h3">영역</span>
            <span className="row-n">{m.areas.length}</span>
          </div>
          <div className="rows">
            {m.tracks.map(g => (
              <div key={g.tr}>
                <div className="bank-sub">{g.name} · {g.n}문항</div>
                {g.areas.map(a => (
                  <button key={a.area} className="row-item"
                          aria-current={a.area === area ? 'true' : undefined}
                          onClick={() => go('/t/' + encodeURIComponent(a.area))}>
                    <span className="row-t">
                      {a.area}
                      <span className="row-sub" style={{ display: 'block' }}>
                        {a.done ? `${a.done}/${a.n} · ${a.rate}%` : `${a.n}문항`}
                      </span>
                    </span>
                    <I.Chevron className="chev" />
                  </button>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* 2단 — 유형 */}
        <div className="card bank-col">
          <div className="bank-h">
            <span className="h3">유형</span>
            {m.cur && <span className="row-n">{m.types.length}</span>}
          </div>
          {!m.cur
            ? <p className="empty sm" style={{ padding: '2.5rem 1rem' }}>
                왼쪽에서 영역을 고르세요.
              </p>
            : (
              <>
                <div style={{ padding: '.7rem 1.25rem', borderBottom: '1px solid var(--hair)' }}>
                  <div className="sm muted">{progText(m.cur)}</div>
                  <div className="bar" style={{ margin: '.5rem 0 .6rem' }}>
                    <i style={{ width: m.cur.fill + '%' }} />
                  </div>
                  <button className="btn btn-primary" style={{ width: '100%' }}
                          onClick={() => go(poolHref({ sj: area }))}>
                    영역 전체 풀기 ({m.cur.n})
                  </button>
                </div>
                <div className="rows">
                  {m.types.map(t => (
                    <button key={t.ty} className="row-item"
                            aria-current={t.ty === type ? 'true' : undefined}
                            onClick={() => go('/s/' + encodeURIComponent(area)
                                              + '/' + encodeURIComponent(t.ty))}>
                      <span className="row-t">
                        {t.ty}
                        <span className="row-sub" style={{ display: 'block' }}>
                          {t.done ? `${t.done}/${t.n} · ${t.rate}%` : `${t.n}문항`}
                        </span>
                      </span>
                      <I.Chevron className="chev" />
                    </button>
                  ))}
                </div>
              </>
            )}
        </div>

        {/* 3단 — 문항 */}
        <div className="card bank-col">
          <div className="bank-h">
            <span className="h3">{type || '문항'}</span>
            {m.items.length ? <span className="row-n">{m.items.length}</span> : null}
          </div>
          {!m.items.length
            ? <p className="empty sm" style={{ padding: '2.5rem 1rem' }}>
                {m.cur ? '유형을 고르세요.' : '영역과 유형을 고르세요.'}
              </p>
            : (
              <>
                <div style={{ padding: '.7rem 1.25rem', borderBottom: '1px solid var(--hair)' }}>
                  <button className="btn btn-primary" style={{ width: '100%' }}
                          onClick={() => go(poolHref({ sj: area, ty: type }))}>
                    이 유형 풀기 ({m.items.length})
                  </button>
                </div>
                <div className="rows">
                  {m.items.map(({ it, last, flag }, i) => (
                    <button key={it.id} className="row-item"
                            onClick={() => go(poolHref({ sj: area, ty: type }) + '&at=' + i)}>
                      <span className="row-n" style={{ minWidth: '1.6rem' }}>{i + 1}</span>
                      <span className="row-t">
                        {/* **글자 수로 자르지 않는다.** 위 span 이 CSS 로 자르므로
                            폭이 정하게 둔다 — QHD 에서 이 칸이 900px 인데 64자에서
                            끊으면 줄의 절반이 빈다. 200 은 「자르지 않는다」는 뜻이다 */}
                        <span style={{ display: 'block', overflow: 'hidden',
                                       textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {db.line(it, 200)}
                        </span>
                      </span>
                      {flag && <I.Flag style={{ width: 15, height: 15,
                                                color: 'var(--warn-vivid)' }} />}
                      {last
                        ? <span className={'badge ' + (last.k ? 'badge-ok' : 'badge-bad')}>
                            {last.k ? '맞음' : '틀림'}
                          </span>
                        : <span className="badge badge-flat">안 품</span>}
                    </button>
                  ))}
                </div>
              </>
            )}
        </div>
      </div>
    </>
  );
}
