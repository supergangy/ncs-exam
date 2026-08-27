/** 묶음 마침 — 방금 푼 묶음을 어떻게 풀었나.
 *
 *  회차 결과(`/result`)와 다르다. 저쪽은 시간 제한과 OMR 이 있는 응시의 성적표이고,
 *  이쪽은 **연습 묶음**(영역·유형·키워드·오답노트·복습)을 끝낸 자리다.
 *
 *  **모듈 변수에 들고 있지 않는다.** 배포본은 `let DONE = S` 에 담고 해시를
 *  바꿨는데, 그 화면에서 새로 고치면 값이 사라져 홈으로 튀었다. 여기서는
 *  `store.solo()` 의 묶음(`ids`)과 잡은 시각(`t`) 만으로 기록에서 다시 센다 —
 *  새로 고쳐도, 나중에 다시 열어도 같은 값이 나온다.
 *
 *  **「이번에 틀림」과 「오답노트」는 다르다.**
 *    이번에 틀림  이 묶음에서 채점했고 틀린 것
 *    오답노트     그것 + **건너뛴 것 중 예전에 틀린 것**
 *  뒤엣것이 더 클 수 있다. 「다시 풀기」는 뒤엣것을 센다 — 건너뛴 오답도 풀어야 한다.
 */
import { useState } from 'react';

import { pct } from '../../core/progress.js';
import { mmss } from '../../core/text.js';
import { makePool, poolHref } from '../../data/pool.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useDerived } from '../../store/useStore.js';

export default function Done({ db }) {
  const [only, setOnly] = useState('all');       // all | wrong

  const d = useDerived(s => {
    const solo = s.solo();
    if (!solo) return null;

    // `byId` 를 id 마다 부르면 764×764 가 된다 — 한 번 훑고 원래 순서로 세운다
    const order = new Map((solo.ids || []).map((id, i) => [id, i]));
    const rows = db.items.filter(i => order.has(i.id))
      .sort((a, b) => order.get(a.id) - order.get(b.id))
      .map(it => ({ it, pass: s.passOf(it.id, solo.t), now: s.isWrong(it.id) }));

    const passed = rows.filter(r => r.pass);
    const ok = passed.filter(r => r.pass.ok).length;

    return {
      // 묶음 이름은 `key`(질의 문자열)에서 되짚는다 — solo 에 이름을 따로 담지 않는다
      title: makePool(db, s, solo.key).title,
      key: solo.key,
      rows,
      n: rows.length,
      done: passed.length,
      ok,
      rate: pct(ok, passed.length),
      ms: passed.reduce((t, r) => t + r.pass.ms, 0),
      missed: passed.length - ok,                 // 이번에 틀린 것
      wrong: rows.filter(r => r.now).length,      // 지금도 오답인 것
    };
  }, [db]);

  if (!d) {
    return (
      <div className="empty">
        <p style={{ fontWeight: 700, color: 'var(--ink)' }}>최근에 푼 묶음이 없습니다</p>
        <p className="sm">영역이나 유형을 골라 풀면 여기에 결과가 남습니다.</p>
        <button className="btn btn-tint" style={{ marginTop: '1rem' }} onClick={() => go('/')}>
          홈으로
        </button>
      </div>
    );
  }

  if (!d.done) {
    return (
      <div className="empty">
        <p style={{ fontWeight: 700, color: 'var(--ink)' }}>아직 채점한 것이 없습니다</p>
        <p className="sm">{d.title} · {d.n}문항</p>
        <button className="btn btn-primary" style={{ marginTop: '1rem' }}
                onClick={() => go('/q?' + d.key)}>이어서 풀기</button>
      </div>
    );
  }

  const rows = only === 'wrong' ? d.rows.filter(r => r.pass && !r.pass.ok) : d.rows;
  const tone = d.rate >= 80 ? 'bar-ok' : d.rate >= 50 ? 'bar-warn' : 'bar-bad';

  return (
    <div className="stack">
      <div className="card pad">
        <div className="row-sub">{d.title}</div>
        <div className="h1" style={{ marginTop: '.2rem' }}>{d.rate}%</div>
        <div className="row-sub">
          {d.done}문항 중 {d.ok}개를 맞혔습니다
          {d.done < d.n ? ` · ${d.n - d.done}문항은 건너뛰었습니다` : ''}
        </div>
        <div className={'bar ' + tone} style={{ marginTop: '.7rem' }}>
          <i style={{ width: d.rate + '%' }} />
        </div>
      </div>

      <div className="metrics">
        <Metric k="푼 문항" v={d.done} s={`전체 ${d.n}`} />
        <Metric k="맞힘" v={d.ok} s={`이번에 틀림 ${d.missed}`} />
        <Metric k="걸린 시간" v={mmss(d.ms)}
                s={`문항당 ${mmss(Math.round(d.ms / d.done))}`} />
        <Metric k="오답노트" v={d.wrong}
                s={d.wrong > d.missed ? `건너뛴 ${d.wrong - d.missed}개 포함`
                                      : '마지막 시도가 오답인 것'} />
      </div>

      {d.wrong > 0 && (
        <button className="btn btn-primary" onClick={() => go(poolHref({ pool: 'wrong' }))}>
          <I.Pencil />오답노트 {d.wrong}개 다시 풀기
        </button>
      )}

      <div style={{ display: 'flex', gap: '.4rem' }}>
        {[['all', `전체 ${d.n}`], ['wrong', `틀린 것 ${d.missed}`]].map(([v, label]) => (
          <button key={v} className={'btn ' + (only === v ? 'btn-tint' : 'btn-outline')}
                  style={{ flex: 1 }} onClick={() => setOnly(v)}
                  aria-pressed={only === v}>{label}</button>
        ))}
      </div>

      {!rows.length
        ? <p className="empty sm">이번에 틀린 것이 없습니다.</p>
        : (
          <div className="card rows">
            {rows.map(({ it, pass }) => (
              <button key={it.id} className="row-item"
                      onClick={() => go(poolHref({ id: it.id }))}>
                <Tag pass={pass} />
                <span className="row-t">
                  <span style={{ display: 'block' }}>{db.line(it, 52)}</span>
                  <span className="row-sub" style={{ display: 'block' }}>
                    {it.sj} · {it.ty}
                    {pass && pass.n > 1 ? ` · ${pass.n}번 시도` : ''}
                  </span>
                </span>
                <I.Chevron className="chev" />
              </button>
            ))}
          </div>
        )}

      <button className="btn btn-outline" onClick={() => go('/')}>홈으로</button>
    </div>
  );
}

/** 세 가지뿐이다.
 *
 *  「나중에 고쳤다」를 넷째로 두려 했는데 **도달할 수 없는 상태**였다.
 *  `passOf` 의 창은 `solo.t` 이후로 **끝이 없으므로**, 이 묶음을 푼 뒤 오답노트에서
 *  다시 맞혀도 그 시도가 창 안에 들어온다 — 즉 `pass.ok` 는 늘 `!isWrong` 이다.
 *  그래서 화면의 수는 **지금 기준**이고, 그것이 새로 고쳐도 값이 같은 이유다. */
function Tag({ pass }) {
  const [cls, text] = !pass ? ['badge-flat', '건너뜀']
                    : pass.ok ? ['badge-ok', '맞음']
                    : ['badge-bad', '틀림'];
  return <span className={'badge ' + cls}>{text}</span>;
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
