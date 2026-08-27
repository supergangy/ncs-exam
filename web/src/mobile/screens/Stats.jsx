/** 분석 — 시안 `test-analytics-desktop` 을 모바일 한 단으로 옮긴 것.
 *
 *  **차트는 하나뿐이다.** 「정답률 추이」만 시간에 따른 변화이므로 꺾은선이고,
 *  나머지는 크기 비교(가로 막대)와 단일 값(스탯 타일)이다. 모든 수치를 차트로
 *  만들면 읽는 사람이 더 오래 걸린다.
 *
 *  추이는 **시리즈가 하나**라 범례를 두지 않는다 — 제목이 곧 이름이다.
 *  쉰 날은 **선을 끊는다.** 0% 로 이으면 「쉰 날」과 「다 틀린 날」이 같아 보인다.
 *
 *  영역별 막대의 색(녹·황·적)은 상태를 나타낸다. 색만으로 전하지 않도록
 *  **정답률 숫자와 n/m 을 함께 적고 낮은 순으로 세운다** — 색약에서도 순서가 읽힌다.
 *  (팔레트 검사: CVD ΔE 8.9 통과 · 표면 대비 WARN 은 「보이는 라벨」로 해소)
 */
import { attempts, daily, streak, xp, level, weekOverWeek } from '../../core/goal.js';
import { pct, progress } from '../../core/progress.js';
import { mmss } from '../../core/text.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useDerived } from '../../store/useStore.js';

const DAYS = 14;
/** 이만큼은 풀어 봤어야 정답률을 견준다 (core/goal.js 의 weakest 와 같은 기준) */
const MIN_N = 5;

export default function Stats({ db }) {
  const m = useDerived(s => {
    const att = s.d.att;
    // 표본이 적은 영역은 뒤로 — 1문항 0% 가 21문항 43% 보다 약하다고 말할 수 없다
    const areas = db.areas()
      .map(a => ({ area: a.area, ...progress(db.byArea(a.area), s.last) }))
      .filter(a => a.done > 0)
      .sort((x, y) => (x.done >= MIN_N) - (y.done >= MIN_N) === 0
        ? x.rate - y.rate
        : (y.done >= MIN_N) - (x.done >= MIN_N));

    // 소요 시간 — 회차 제출은 m 이 0 이므로 평균에서 뺀다 (문항별로 잴 수 없다)
    const timed = attempts(att).filter(a => a.m > 0);
    const avgMs = timed.length
      ? Math.round(timed.reduce((s2, a) => s2 + a.m, 0) / timed.length) : 0;

    return {
      all: progress(db.items, s.last),
      areas,
      trend: daily(att, DAYS),
      week: weekOverWeek(att),
      streak: streak(att),
      xp: xp(att, s.d.exams),
      avgMs,
      timedN: timed.length,
      exams: db.rounds
        .map(r => ({ r, h: s.examHistory(r.tag) }))
        .filter(x => x.h.length)
        .map(x => ({ ...x, last: x.h[x.h.length - 1] })),
    };
  }, [db]);

  if (!m.all.done) {
    return (
      <div className="empty">
        <p style={{ fontWeight: 700, color: 'var(--ink)' }}>아직 분석할 기록이 없습니다</p>
        <p className="sm">한 문항이라도 풀면 여기에 쌓입니다.</p>
        <button className="btn btn-tint" style={{ marginTop: '1rem' }} onClick={() => go('/')}>
          문항 고르기
        </button>
      </div>
    );
  }

  const lv = level(m.xp);

  return (
    <div className="stack">
      <div className="metrics">
        <Tile k="전체 정답률" v={m.all.rate + '%'} s={`${m.all.ok}/${m.all.done} 맞음`} />
        <Tile k="푼 문항" v={String(m.all.done)} s={`전체 ${m.all.n}`} />
        <Tile k="연속 학습" v={m.streak + '일'}
              s={m.streak ? '이어 가고 있습니다' : '오늘 시작할 수 있습니다'} />
        <Tile k="경험치" v={m.xp.toLocaleString()} s={`Lv.${lv.lv}`} />
      </div>

      <div className="card pad">
        <div className="h3">정답률 추이</div>
        <div className="sm muted" style={{ marginTop: '.2rem' }}>
          최근 {DAYS}일 · 푼 것이 없는 날은 선을 끊었습니다
        </div>
        <Trend rows={m.trend} />
      </div>

      <div className="card pad">
        <div className="h3">영역별 — 낮은 순</div>
        <div className="sm muted" style={{ marginTop: '.2rem' }}>
          한 문항이라도 푼 영역 {m.areas.length}개 ·
          {' '}{MIN_N}문항 미만은 옅게 — 견주기 어렵습니다
        </div>
        <div style={{ marginTop: '.7rem' }}>
          {m.areas.map(a => (
            <button key={a.area} title={a.done < MIN_N ? `${a.done}문항만 풀어 견주기 어렵습니다` : undefined}
                    style={{ display: 'flex', alignItems: 'center', gap: '.5rem',
                             width: '100%', padding: '.4rem 0', border: 0,
                             background: 'none', font: 'inherit', color: 'inherit',
                             cursor: 'pointer' }}
                    onClick={() => go('/t/' + encodeURIComponent(a.area))}>
              <span className="sm" style={{ flex: 1, minWidth: 0, overflow: 'hidden',
                                            textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                                            textAlign: 'left' }}>
                {a.area}
              </span>
              <span className="row-n">{a.ok}/{a.done}</span>
              <div className={'bar ' + (a.done >= MIN_N ? tone(a.rate) : '')}
                   style={{ width: '4.2rem', flex: '0 0 auto',
                            opacity: a.done >= MIN_N ? 1 : .45 }}>
                <i style={{ width: a.rate + '%' }} />
              </div>
              <span className="tick sm" style={{ width: '2.6rem', textAlign: 'right',
                       color: a.done >= MIN_N ? undefined : 'var(--faint)' }}>
                {a.rate}%
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="card pad">
        <div className="h3">문항당 소요 시간</div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '.5rem',
                      marginTop: '.4rem' }}>
          <span className="tick" style={{ fontSize: 'var(--t-h1)', fontWeight: 'var(--w-bold)' }}>
            {m.avgMs ? mmss(m.avgMs) : '—'}
          </span>
          <span className="sm muted">평균</span>
        </div>
        <div className="sm muted" style={{ marginTop: '.3rem' }}>
          {m.timedN
            ? `낱개로 푼 ${m.timedN}문항 기준. 회차 응시는 문항을 오가므로 제외했습니다.`
            : '낱개로 푼 문항이 아직 없습니다.'}
        </div>
      </div>

      {m.exams.length > 0 && (
        <div>
          <div className="h2" style={{ margin: '.3rem 0 .6rem' }}>회차 성적</div>
          <div className="card rows">
            {m.exams.map(({ r, h, last }) => (
              <button key={r.tag} className="row-item" onClick={() => go('/result/' + r.tag)}>
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
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const tone = r => (r >= 80 ? 'bar-ok' : r >= 50 ? 'bar-warn' : 'bar-bad');

function Tile({ k, v, s }) {
  return (
    <div className="card metric">
      <div className="metric-k">{k}</div>
      <div className="metric-v">{v}</div>
      <div className="metric-s">{s}</div>
    </div>
  );
}

/** 정답률 추이 — 시리즈 하나. 범례를 두지 않는다(제목이 이름이다).
 *
 *  **쉰 날은 선을 끊는다.** `rate` 가 null 인 날에서 조각을 나눠 그린다.
 *  점은 푼 날에만 찍고, 마지막 값에만 숫자를 붙인다 — 모든 점에 숫자를 달면
 *  읽히지 않는다.
 */
function Trend({ rows }) {
  const W = 320, H = 96, P = 8;           // viewBox 좌표. 실제 크기는 CSS 가 정한다
  const n = rows.length;
  const x = i => P + (i * (W - P * 2)) / Math.max(1, n - 1);
  const y = v => H - P - ((v / 100) * (H - P * 2));

  // 이어진 구간끼리 조각을 만든다
  const runs = [];
  let cur = [];
  rows.forEach((r, i) => {
    if (r.rate == null) { if (cur.length) runs.push(cur); cur = []; return; }
    cur.push({ i, r });
  });
  if (cur.length) runs.push(cur);

  const pts = runs.flat();
  if (!pts.length) {
    return <p className="sm faint" style={{ marginTop: '.8rem' }}>
      최근 {n}일 동안 푼 문항이 없습니다.
    </p>;
  }
  const lastPt = pts[pts.length - 1];

  return (
    <>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img"
           aria-label={`최근 ${n}일 정답률 추이. 마지막 값 ${lastPt.r.rate}%`}
           style={{ marginTop: '.6rem', display: 'block', overflow: 'visible' }}>
        {/* 기준선 — 눈금 대신 50% 한 줄만. 격자는 뒤로 물린다 */}
        <line x1={P} x2={W - P} y1={y(50)} y2={y(50)}
              stroke="var(--hair)" strokeWidth="1" />
        <text x={P} y={y(50) - 3} fill="var(--faint)" fontSize="9">50%</text>

        {runs.map((run, k) => (
          <path key={k} fill="none" stroke="var(--acc)" strokeWidth="2"
                strokeLinecap="round" strokeLinejoin="round"
                d={run.map((p, j) => `${j ? 'L' : 'M'}${x(p.i)},${y(p.r.rate)}`).join(' ')} />
        ))}

        {pts.map(p => (
          <circle key={p.i} cx={x(p.i)} cy={y(p.r.rate)} r="3.2"
                  fill="var(--surf)" stroke="var(--acc)" strokeWidth="2" />
        ))}

        {/* 마지막 값만 직접 라벨 — 모든 점에 숫자를 달지 않는다 */}
        <text x={Math.min(W - P, x(lastPt.i) + 6)} y={y(lastPt.r.rate) - 7}
              fill="var(--ink)" fontSize="11" fontWeight="700"
              textAnchor={lastPt.i > n - 3 ? 'end' : 'start'}>
          {lastPt.r.rate}%
        </text>
      </svg>

      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span className="xs faint">{DAYS}일 전</span>
        <span className="xs faint">오늘</span>
      </div>

      {/* 색만으로 전하지 않는다 — 표로도 읽을 수 있게 둔다 */}
      <details style={{ marginTop: '.6rem' }}>
        <summary className="sm muted" style={{ cursor: 'pointer' }}>숫자로 보기</summary>
        <table className="sm" style={{ width: '100%', marginTop: '.5rem',
                                       borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', color: 'var(--faint)', fontWeight: 400 }}>날짜</th>
              <th style={{ textAlign: 'right', color: 'var(--faint)', fontWeight: 400 }}>푼 수</th>
              <th style={{ textAlign: 'right', color: 'var(--faint)', fontWeight: 400 }}>정답률</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.at}>
                <td>{new Date(r.at).toLocaleDateString('ko-KR', { month: 'numeric', day: 'numeric' })}</td>
                <td className="tick" style={{ textAlign: 'right' }}>{r.n || '—'}</td>
                <td className="tick" style={{ textAlign: 'right' }}>
                  {r.rate == null ? '—' : r.rate + '%'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </>
  );
}
