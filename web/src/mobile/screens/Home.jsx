/** 홈 — 시안 `mobile-dashboard` 를 옮긴 것.
 *
 *  시안에 있던 것 중 **기기 안에서 낼 수 없는 것은 바꿔 담았다.**
 *    Percentile 94.2th / Top of group  → 지난 주 대비 내 정답률 변화
 *    AI curated exercises              → 정답률 낮은 영역 (표본 5문항 이상)
 *  다른 사람의 기록이 필요한 값을 지어내지 않는다.
 *
 *  시안에 없지만 앱에 필요한 것 하나 — **영역 목록**. 시안 대시보드는 연습 방식
 *  카드에서 끝나지만, 실제로는 「무엇을 풀지」 고르는 자리가 있어야 한다.
 */
import { goalToday, streak, xp, level, examText, weekOverWeek, weakest } from '../../core/goal.js';
import { progress } from '../../core/progress.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useStore, useDerived } from '../../store/useStore.js';

export default function Home({ db }) {
  const st = useStore();

  // 셈이 드는 것은 기록이 바뀔 때만 다시 센다
  const m = useDerived(s => {
    const areas = db.areas().map(a => ({
      ...a, ...progress(db.byArea(a.area), s.last),
    }));
    return {
      areas,
      all: progress(db.items, s.last),
      goal: goalToday(s.d.att, s.pref.goal),
      streak: streak(s.d.att),
      xp: xp(s.d.att, s.d.exams),
      week: weekOverWeek(s.d.att),
      weak: weakest(areas, 5)[0] || null,
      due: s.due(db.items).length,
      wrong: db.items.filter(i => s.isWrong(i.id)).length,
    };
  }, [db]);

  const lv = level(m.xp);
  const dday = examText(st.pref.examAt);

  return (
    <div className="stack">
      <Greeting goal={m.goal} streak={m.streak} dday={dday} />

      <div className="metrics">
        <Metric k="이번 주 정답률"
                v={m.week.rate == null ? '—' : m.week.rate + '%'}
                s={deltaText(m.week)} />
        <Metric k="푼 문항"
                v={`${m.all.done}`}
                s={`전체 ${m.all.n} · 남은 ${m.all.n - m.all.done}`} />
        <Metric k="시험일"
                v={dday || '—'}
                s={dday ? '설정에서 바꿉니다' : '설정에서 정하세요'} />
        <Metric k="경험치"
                v={m.xp.toLocaleString()}
                s={`Lv.${lv.lv} · 다음까지 ${(lv.next - m.xp).toLocaleString()}`} />
      </div>

      <div className="card pad">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <span className="h3">오늘 목표</span>
          <span className="tick sm">{m.goal.done} / {m.goal.goal}</span>
        </div>
        <div className="bar" style={{ margin: '.6rem 0 .4rem' }}>
          <i style={{ width: m.goal.fill + '%' }} />
        </div>
        <div className="sm muted">
          {m.goal.left ? `${m.goal.left}문항 더 풀면 오늘 몫을 채웁니다` : '오늘 몫을 채웠습니다'}
        </div>
      </div>

      <div>
        <div className="h2" style={{ margin: '.4rem 0 .6rem' }}>연습 방식</div>
        <div className="stack">
          <Mode icon={I.Timer} to="/exams" t="회차 응시"
                d="제한 시간·OMR·제출 후 일괄 채점. 실제 시행과 같은 구성입니다."
                cta="회차 고르기" />
          <Mode icon={I.Refresh} to="/review" t="복습"
                d={m.due ? `오늘 다시 볼 ${m.due}문항이 준비돼 있습니다.`
                         : '지금 다시 볼 문항이 없습니다. 풀면 간격을 두고 돌아옵니다.'}
                cta={m.due ? `${m.due}문항 복습` : '복습 규칙 보기'}
                badge={m.due ? String(m.due) : null} />
          <Mode icon={I.Target}
                to={m.weak ? '/t/' + encodeURIComponent(m.weak.area) : '/'}
                t="취약 영역"
                d={m.weak
                  ? `${m.weak.area} 정답률 ${m.weak.rate}% (${m.weak.done}문항 기준) — 가장 낮습니다.`
                  : '영역마다 5문항 이상 풀면 약한 곳을 짚어 드립니다.'}
                cta={m.weak ? `${m.weak.area} 풀기` : '먼저 풀어 보기'}
                disabled={!m.weak} />
          <Mode icon={I.Pencil} to="/wrong" t="오답노트"
                d={m.wrong ? `마지막에 틀린 ${m.wrong}문항입니다. 다시 맞히면 빠집니다.`
                           : '틀린 문항이 모이는 곳입니다.'}
                cta={m.wrong ? `${m.wrong}문항 다시` : '비어 있음'}
                disabled={!m.wrong} />
        </div>
      </div>

      <div>
        <div className="h2" style={{ margin: '.9rem 0 .6rem' }}>영역</div>
        <div className="card rows">
          {m.areas.map(a => (
            <button key={a.area} className="row-item"
                    onClick={() => go('/t/' + encodeURIComponent(a.area))}>
              <span className="row-t">
                {a.area}
                <span className="row-sub" style={{ display: 'block' }}>
                  {a.done ? `${a.done}/${a.n} · 정답률 ${a.rate}%` : `${a.n}문항`}
                </span>
              </span>
              <span className="row-n">{a.types.length}유형</span>
              <I.Chevron className="chev" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/** 지난 주 대비 — 견줄 것이 없으면 **아무 말도 하지 않는다.** 0% 라고 적으면
 *  「변화 없음」과 「기록 없음」이 같아 보인다. */
function deltaText(w) {
  if (w.rate == null) return '이번 주에 푼 것이 없습니다';
  if (w.delta == null) return `${w.n}문항 기준`;
  const sign = w.delta > 0 ? '+' : '';
  return `지난 주 대비 ${sign}${w.delta}%p`;
}

function Greeting({ goal, streak, dday }) {
  return (
    <div className="card pad">
      <div className="h2">
        {goal.left ? `오늘 ${goal.left}문항 남았습니다` : '오늘 몫을 채웠습니다'}
      </div>
      <div className="row-sub" style={{ marginTop: '.25rem' }}>
        {streak > 0
          ? `${streak}일 연속 풀고 있습니다.`
          : '오늘 한 문항이라도 풀면 연속이 시작됩니다.'}
        {dday && ` 시험까지 ${dday}.`}
      </div>
      <div style={{ display: 'flex', gap: '.4rem', marginTop: '.7rem', flexWrap: 'wrap' }}>
        {streak > 0 && (
          <span className="badge pill-streak"><I.Flame />
            {streak}일 연속</span>
        )}
        {dday && (
          <span className="badge badge-acc"><I.Calendar />
            {dday}</span>
        )}
      </div>
    </div>
  );
}

function Metric({ k, v, s }) {
  return (
    <div className="card metric">
      <div className="metric-k">{k}</div>
      <div className="metric-v">{v}</div>
      <div className="metric-s">{s}</div>
    </div>
  );
}

function Mode({ icon: Icon, to, t, d, cta, badge, disabled }) {
  return (
    <div className="card mode">
      <span className="mode-ic"><Icon /></span>
      <div className="mode-b">
        <div className="mode-t">
          {t}
          {badge && <span className="badge badge-acc" style={{ marginLeft: '.4rem' }}>{badge}</span>}
        </div>
        <div className="mode-d">{d}</div>
        <button className={'btn ' + (disabled ? 'btn-outline' : 'btn-tint')}
                style={{ marginTop: '.7rem', width: '100%' }}
                disabled={disabled} onClick={() => go(to)}>
          {cta}
        </button>
      </div>
    </div>
  );
}
