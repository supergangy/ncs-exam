/** PC 분석 — 시안 `test-analytics-desktop` 을 옮긴 것.
 *
 *  시안 구성 그대로 — 요약 타일 · 영역별 막대 · 정답률 추이 · 오답 로그.
 *  다만 시안의 「Percentile 94.2th / Top of group」 은 다른 사람의 기록이 필요해
 *  만들 수 없다. 그 자리에 **지난 주 대비 내 변화**를 둔다.
 *
 *  **차트는 추이 하나뿐이다.** 나머지는 크기 비교(막대)와 단일 값(타일)이다 —
 *  모든 수치를 차트로 만들면 읽는 사람이 더 오래 걸린다.
 *
 *  막대 색(녹·황·적)은 상태를 나타낸다. 색만으로 전하지 않도록 **정답률과 n/m 을
 *  함께 적고 낮은 순으로 세운다.** 표본 5문항 미만은 뒤로 보내고 옅게 —
 *  1문항 0% 가 21문항 43% 보다 약하다고 말할 수 없다.
 */
import { attempts, daily, streak, xp, level, weekOverWeek } from '../../core/goal.js';
import { pct, progress } from '../../core/progress.js';
import { CIRC, mmss } from '../../core/text.js';
import { poolHref , practiceKeep } from '../../data/pool.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useDerived } from '../../store/useStore.js';

import Trend from './Trend.jsx';

const DAYS = 21;
const MIN_N = 5;

export default function Stats({ db }) {
  const m = useDerived(s => {
    const att = s.d.att;
    const keep = practiceKeep(db, s);
    const areas = db.areas(keep)
      .map(a => ({ area: a.area, ...progress(db.byArea(a.area, keep), s.last) }))
      .filter(a => a.done > 0)
      .sort((x, y) => (x.done >= MIN_N) === (y.done >= MIN_N)
        ? x.rate - y.rate
        : (y.done >= MIN_N) - (x.done >= MIN_N));

    const timed = attempts(att).filter(a => a.m > 0);
    const avgMs = timed.length
      ? Math.round(timed.reduce((acc, a) => acc + a.m, 0) / timed.length) : 0;

    return {
      // 영역 목록과 같은 체를 쓴다. 여기만 804 로 두면 「남은 804」인데
      // 영역을 다 더해도 614 인 어긋남이 생긴다
      all: progress(db.items.filter(keep), s.last),
      areas,
      trend: daily(att, DAYS),
      week: weekOverWeek(att),
      streak: streak(att),
      xp: xp(att, s.d.exams),
      avgMs,
      timedN: timed.length,
      wrong: db.items.filter(i => s.isWrong(i.id)).map(it => ({ it, last: s.last(it.id) })),
      exams: db.rounds.map(r => ({ r, h: s.examHistory(r.tag) })).filter(x => x.h.length),
    };
  }, [db]);

  if (!m.all.done) {
    return (
      <div className="empty">
        <p style={{ fontWeight: 700, color: 'var(--ink)' }}>아직 분석할 기록이 없습니다</p>
        <p className="sm">한 문항이라도 풀면 여기에 쌓입니다.</p>
        <button className="btn btn-tint" style={{ marginTop: '1rem' }} onClick={() => go('/bank')}>
          문항 고르기
        </button>
      </div>
    );
  }

  const lv = level(m.xp);

  return (
    <>
      <div className="page-head">
        <div className="h1">분석</div>
        <div className="row-sub">
          {m.all.done}문항을 풀었고 전체 정답률은 {m.all.rate}% 입니다.
        </div>
      </div>

      <div className="tiles" style={{ marginBottom: '1.25rem' }}>
        <div className="card tile">
          <div className="tile-k">전체 정답률</div>
          <div className="tile-v">{m.all.rate}%</div>
          <div className="tile-s">{m.all.ok} / {m.all.done} 맞음</div>
        </div>
        <div className="card tile">
          <div className="tile-k">이번 주</div>
          <div className="tile-v">{m.week.rate == null ? '—' : m.week.rate + '%'}</div>
          <div className="tile-s">
            {m.week.rate == null ? '푼 것이 없습니다'
              : m.week.delta == null ? `${m.week.n}문항 기준`
              : `지난 주 대비 ${m.week.delta > 0 ? '+' : ''}${m.week.delta}%p`}
          </div>
        </div>
        <div className="card tile">
          <div className="tile-k">문항당 소요</div>
          <div className="tile-v" style={{ fontSize: '1.5rem' }}>
            {m.avgMs ? mmss(m.avgMs) : '—'}
          </div>
          <div className="tile-s">
            {m.timedN ? `낱개 ${m.timedN}문항 기준` : '낱개로 푼 문항이 없습니다'}
          </div>
        </div>
        <div className="card tile">
          <div className="tile-k">연속 · 경험치</div>
          <div className="tile-v" style={{ fontSize: '1.5rem' }}>
            {m.streak}일 · Lv.{lv.lv}
          </div>
          <div className="tile-s">{m.xp.toLocaleString()} XP</div>
        </div>
      </div>

      <div className="card pad" style={{ marginBottom: '1.25rem' }}>
        <div className="h3">정답률 추이</div>
        <div className="sm muted" style={{ marginTop: '.2rem' }}>
          최근 {DAYS}일 · 푼 것이 없는 날은 선을 끊었습니다
        </div>
        <Trend rows={m.trend} height={190} />
      </div>

      <div className="cols">
        <div className="card pad">
          <div className="h3">영역별 — 낮은 순</div>
          <div className="sm muted" style={{ marginTop: '.2rem' }}>
            푼 영역 {m.areas.length}개 · {MIN_N}문항 미만은 옅게 (견주기 어렵습니다)
          </div>
          <div style={{ marginTop: '.8rem' }}>
            {m.areas.map(a => {
              const thin = a.done < MIN_N;
              return (
                <button key={a.area}
                        style={{ display: 'flex', alignItems: 'center', gap: '.7rem',
                                 width: '100%', padding: '.4rem 0', border: 0,
                                 background: 'none', font: 'inherit', color: 'inherit',
                                 cursor: 'pointer' }}
                        title={thin ? `${a.done}문항만 풀어 견주기 어렵습니다` : undefined}
                        onClick={() => go('/t/' + encodeURIComponent(a.area))}>
                  <span className="sm" style={{ flex: 1, minWidth: 0, textAlign: 'left',
                                                overflow: 'hidden', textOverflow: 'ellipsis',
                                                whiteSpace: 'nowrap' }}>{a.area}</span>
                  <span className="row-n">{a.ok}/{a.done}</span>
                  <div className={'bar ' + (thin ? '' : tone(a.rate))}
                       style={{ width: '8rem', flex: '0 0 auto', opacity: thin ? .45 : 1 }}>
                    <i style={{ width: a.rate + '%' }} />
                  </div>
                  <span className="tick sm" style={{ width: '2.8rem', textAlign: 'right',
                           color: thin ? 'var(--faint)' : undefined }}>{a.rate}%</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="stack">
          {m.exams.length > 0 && (
            <div className="card">
              <div className="pad" style={{ paddingBottom: '.6rem' }}>
                <div className="h3">회차 성적</div>
              </div>
              <div className="rows">
                {m.exams.map(({ r, h }) => {
                  const last = h[h.length - 1];
                  return (
                    <button key={r.tag} className="row-item"
                            onClick={() => go('/result/' + r.tag)}>
                      <span className="row-t">
                        {r.title}
                        <span className="row-sub" style={{ display: 'block' }}>
                          {last.score}/{last.n} · {mmss(last.sec * 1000)}
                          {h.length > 1 && ` · ${h.length}번 응시`}
                        </span>
                      </span>
                      <span className={'badge ' + (pct(last.score, last.n) >= 60 ? 'badge-ok' : 'badge-bad')}>
                        {pct(last.score, last.n)}%
                      </span>
                      <I.Chevron className="chev" />
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <div className="card">
            <div className="pad" style={{ paddingBottom: '.6rem' }}>
              <div className="h3">
                틀린 문항
                <span className="badge badge-flat" style={{ marginLeft: '.4rem' }}>
                  {m.wrong.length}
                </span>
              </div>
              <div className="sm muted" style={{ marginTop: '.2rem' }}>
                마지막 시도가 오답인 것. 다시 맞히면 빠집니다
              </div>
            </div>
            {m.wrong.length === 0
              ? <p className="sm faint" style={{ padding: '0 1.25rem 1.1rem' }}>
                  틀린 문항이 없습니다.
                </p>
              : (
                <>
                  <div className="rows" style={{ maxHeight: '18rem', overflowY: 'auto' }}>
                    {m.wrong.slice(0, 40).map(({ it, last }, k) => (
                      <button key={it.id} className="row-item"
                              onClick={() => go(poolHref({ pool: 'wrong' }) + '&at=' + k)}>
                        <span className="row-t">
                          <span style={{ display: 'block', overflow: 'hidden',
                                         textOverflow: 'ellipsis',
                                         whiteSpace: 'nowrap' }}>{db.line(it, 46)}</span>
                          <span className="row-sub" style={{ display: 'block' }}>
                            {it.sj} · {it.ty}
                            {last && ` · 고른 것 ${CIRC[last.c - 1] || '—'} · 정답 ${CIRC[it.an - 1]}`}
                          </span>
                        </span>
                        <I.Chevron className="chev" />
                      </button>
                    ))}
                  </div>
                  <div className="pad" style={{ paddingTop: '.7rem' }}>
                    <button className="btn btn-primary" style={{ width: '100%' }}
                            onClick={() => go(poolHref({ pool: 'wrong' }))}>
                      오답노트 전부 풀기 ({m.wrong.length})
                    </button>
                  </div>
                </>
              )}
          </div>
        </div>
      </div>
    </>
  );
}

const tone = r => (r >= 80 ? 'bar-ok' : r >= 50 ? 'bar-warn' : 'bar-bad');
