/** PC 홈 — 넓은 화면의 이점을 쓴다.
 *
 *  모바일은 한 단으로 쌓아 내려가지만, 여기서는 **오늘 할 일(왼쪽)과 흐름(오른쪽)을
 *  나란히** 둔다. 스크롤하지 않고 「무엇을 풀지」와 「어떻게 가고 있나」를 함께 본다.
 *
 *  시안에서 못 만드는 것은 바꿔 담았다 —
 *    Percentile 94.2th → 지난 주 대비 내 정답률 변화
 *    AI curated        → 정답률 낮은 영역 (표본 5문항 이상)
 */
import { goalToday, streak, xp, level, examText, weekOverWeek, weakest, daily }
  from '../../core/goal.js';
import { pct, progress } from '../../core/progress.js';
import { mmss } from '../../core/text.js';
import { poolHref , practiceKeep } from '../../data/pool.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useStore, useDerived } from '../../store/useStore.js';

import Trend from './Trend.jsx';

const MIN_N = 5;

export default function Home({ db }) {
  const st = useStore();
  const m = useDerived(s => {
    const keep = practiceKeep(db, s);
    const areas = db.areas(keep).map(a => ({
      area: a.area, types: a.types.length, ...progress(db.byArea(a.area, keep), s.last),
    }));
    return {
      areas,
      // 영역 목록과 같은 체를 쓴다. 여기만 804 로 두면 「남은 804」인데
      // 영역을 다 더해도 614 인 어긋남이 생긴다
      all: progress(db.items.filter(keep), s.last),
      goal: goalToday(s.d.att, s.pref.goal),
      streak: streak(s.d.att),
      xp: xp(s.d.att, s.d.exams),
      week: weekOverWeek(s.d.att),
      weak: weakest(areas, MIN_N).slice(0, 4),
      trend: daily(s.d.att, 14),
      due: s.due(db.items).length,
      wrong: db.items.filter(i => s.isWrong(i.id)).length,
      exams: db.rounds.map(r => ({ r, rec: s.exam(r.tag) })).filter(x => x.rec),
    };
  }, [db]);

  const lv = level(m.xp);
  const dday = examText(st.pref.examAt);

  return (
    <>
      <div className="page-head">
        <div className="h1">
          {m.goal.left ? `오늘 ${m.goal.left}문항 남았습니다` : '오늘 몫을 채웠습니다'}
        </div>
        <div className="row-sub">
          {m.streak > 0 ? `${m.streak}일 연속 풀고 있습니다.`
                        : '오늘 한 문항이라도 풀면 연속이 시작됩니다.'}
          {dday && ` 시험까지 ${dday}.`}
        </div>
      </div>

      <div className="tiles" style={{ marginBottom: '1.25rem' }}>
        <Tile k="이번 주 정답률" v={m.week.rate == null ? '—' : m.week.rate + '%'}
              s={deltaText(m.week)} />
        <Tile k="푼 문항" v={String(m.all.done)}
              s={`전체 ${m.all.n} · 정답률 ${m.all.rate}%`} />
        <Tile k="시험일" v={dday || '—'}
              s={dday ? '설정에서 바꿉니다' : '설정에서 정하세요'} />
        <Tile k="경험치" v={m.xp.toLocaleString()}
              s={`Lv.${lv.lv} · 다음까지 ${(lv.next - m.xp).toLocaleString()}`} />
      </div>

      <div className="cols">
        <div className="stack">
          <div className="card pad">
            <div style={{ display: 'flex', justifyContent: 'space-between',
                          alignItems: 'baseline' }}>
              <span className="h3">오늘 목표</span>
              <span className="tick">{m.goal.done} / {m.goal.goal}</span>
            </div>
            <div className="bar" style={{ margin: '.7rem 0 .5rem' }}>
              <i style={{ width: m.goal.fill + '%' }} />
            </div>
            <div className="sm muted">
              {m.goal.left ? `${m.goal.left}문항 더 풀면 오늘 몫을 채웁니다`
                           : '오늘 몫을 채웠습니다'}
            </div>
          </div>

          <div className="card">
            <div className="pad" style={{ paddingBottom: '.5rem' }}>
              <span className="h3">연습 방식</span>
            </div>
            <div className="rows">
              <Mode icon={I.Book} to="/bank" t="문항 은행"
                    d={`영역 ${m.areas.length}개 · 유형 ${m.areas.reduce((s, a) => s + a.types, 0)}개를 골라 한 문항씩`} />
              <Mode icon={I.Timer} to="/exams" t="회차 응시"
                    d="제한 시간·OMR·제출 후 일괄 채점" n={db.rounds.length} />
              <Mode icon={I.Refresh} to="/review" t="복습"
                    d={m.due ? '오늘 다시 볼 문항이 준비돼 있습니다'
                             : '지금 다시 볼 문항이 없습니다'} n={m.due} />
              <Mode icon={I.Pencil} to="/wrong" t="오답노트"
                    d="마지막에 틀린 문항. 다시 맞히면 빠집니다" n={m.wrong} />
            </div>
          </div>

          {m.exams.length > 0 && (
            <div className="card">
              <div className="pad" style={{ paddingBottom: '.5rem' }}>
                <span className="h3">최근 회차</span>
              </div>
              <div className="rows">
                {m.exams.slice(0, 4).map(({ r, rec }) => (
                  <button key={r.tag} className="row-item"
                          onClick={() => go('/result/' + r.tag)}>
                    <span className="row-t">
                      {r.title}
                      <span className="row-sub" style={{ display: 'block' }}>
                        {rec.score}/{rec.n} · {mmss(rec.sec * 1000)}
                      </span>
                    </span>
                    <span className={'badge ' + (pct(rec.score, rec.n) >= 60 ? 'badge-ok' : 'badge-bad')}>
                      {pct(rec.score, rec.n)}%
                    </span>
                    <I.Chevron className="chev" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="stack">
          <div className="card pad">
            <span className="h3">정답률 추이</span>
            <div className="sm muted" style={{ marginTop: '.2rem' }}>
              최근 14일 · 푼 것이 없는 날은 선을 끊었습니다
            </div>
            <Trend rows={m.trend} height={140} />
          </div>

          <div className="card pad">
            <span className="h3">더 봐야 할 영역</span>
            <div className="sm muted" style={{ marginTop: '.2rem' }}>
              {MIN_N}문항 이상 푼 영역 가운데 정답률이 낮은 순
            </div>
            {m.weak.length === 0
              ? <p className="sm faint" style={{ marginTop: '.8rem' }}>
                  영역마다 {MIN_N}문항 이상 풀면 약한 곳을 짚어 드립니다.
                </p>
              : <div style={{ marginTop: '.8rem' }}>
                  {m.weak.map(a => (
                    <button key={a.area}
                            style={{ display: 'flex', alignItems: 'center', gap: '.7rem',
                                     width: '100%', padding: '.45rem 0', border: 0,
                                     background: 'none', font: 'inherit', color: 'inherit',
                                     cursor: 'pointer' }}
                            onClick={() => go('/t/' + encodeURIComponent(a.area))}>
                      <span className="sm" style={{ flex: 1, minWidth: 0, textAlign: 'left',
                                                    overflow: 'hidden',
                                                    textOverflow: 'ellipsis',
                                                    whiteSpace: 'nowrap' }}>{a.area}</span>
                      <span className="row-n">{a.ok}/{a.done}</span>
                      <div className={'bar ' + tone(a.rate)}
                           style={{ width: '6rem', flex: '0 0 auto' }}>
                        <i style={{ width: a.rate + '%' }} />
                      </div>
                      <span className="tick sm" style={{ width: '2.8rem', textAlign: 'right' }}>
                        {a.rate}%
                      </span>
                    </button>
                  ))}
                  <button className="btn btn-tint" style={{ width: '100%', marginTop: '.8rem' }}
                          onClick={() => go(poolHref({ sj: m.weak[0].area }))}>
                    {m.weak[0].area} 풀기
                  </button>
                </div>}
          </div>
        </div>
      </div>
    </>
  );
}

const tone = r => (r >= 80 ? 'bar-ok' : r >= 50 ? 'bar-warn' : 'bar-bad');

/** 견줄 지난 주가 없으면 **아무 말도 하지 않는다** — 0%p 라고 적으면
 *  「변화 없음」과 「기록 없음」이 같아 보인다 */
function deltaText(w) {
  if (w.rate == null) return '이번 주에 푼 것이 없습니다';
  if (w.delta == null) return `${w.n}문항 기준`;
  return `지난 주 대비 ${w.delta > 0 ? '+' : ''}${w.delta}%p`;
}

function Tile({ k, v, s }) {
  return (
    <div className="card tile">
      <div className="tile-k">{k}</div>
      <div className="tile-v">{v}</div>
      <div className="tile-s">{s}</div>
    </div>
  );
}

function Mode({ icon: Icon, to, t, d, n }) {
  return (
    <button className="row-item" onClick={() => go(to)}>
      <span style={{ display: 'grid', placeItems: 'center', width: 34, height: 34,
                     borderRadius: 'var(--rx)', background: 'var(--acc-bg)',
                     color: 'var(--acc)', flex: '0 0 auto' }}>
        <Icon style={{ width: 18, height: 18 }} />
      </span>
      <span className="row-t">
        {t}
        <span className="row-sub" style={{ display: 'block' }}>{d}</span>
      </span>
      {n != null && <span className={'badge ' + (n ? 'badge-acc' : 'badge-flat')}>{n}</span>}
      <I.Chevron className="chev" />
    </button>
  );
}
