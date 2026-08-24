/** **배선 확인용 화면. Build 결과로 갈아치울 자리다.**
 *
 *  꾸미지 않았다 — 여기서 확인하는 것은 모양이 아니라 **배선**이다.
 *  ① 문항 764개가 실제로 읽히나 ② 라우터가 갈리나 ③ 기록이 남나
 *  ④ core 의 채점·진도가 화면에서 부르면 도나
 *
 *  껍데기가 오면 이 파일만 지운다. `core/`·`store/`·`router/`·`data/` 는 그대로 쓴다.
 */
import { useEffect, useState } from 'react';
import { loadBank } from './data/bank.js';
import { useHash, go } from './router/useHash.js';
import { useStore } from './store/useStore.js';
import { plain, CIRC } from './core/text.js';
import { choiceStates, gradeOne, CH } from './core/grade.js';
import { progress, progText } from './core/progress.js';

const S = {
  wrap: { maxWidth: 860, margin: '0 auto', padding: '24px 20px 64px' },
  card: { background: 'var(--surf)', borderRadius: 'var(--r)',
          boxShadow: 'var(--sh)', padding: '20px 22px', marginBottom: 16 },
  meta: { font: '11.5px/1.5 var(--mono)', color: 'var(--faint)' },
  stem: { font: '700 20px/1.5 var(--font)', letterSpacing: '-.3px',
          margin: '14px 0 16px' },
  ch: { display: 'block', width: '100%', minHeight: 'var(--tap)',
        textAlign: 'left', padding: '11px 14px', marginBottom: 8,
        borderRadius: 'var(--rs)', cursor: 'pointer' },
  h: { font: '700 14px/1.4 var(--font)', margin: '0 0 10px' },
};

/** 선지 상태를 꾸밈으로 옮긴다 — **색과 테두리 굵기를 함께** 바꾼다 */
const look = st => ({
  [CH.idle]:  { background: 'var(--surf)',  border: '1px solid var(--line)', color: 'var(--ink)' },
  [CH.pick]:  { background: 'var(--acc-bg)', border: '2px solid var(--acc)',  color: 'var(--acc)' },
  [CH.right]: { background: 'var(--ok-bg)',  border: '2px solid var(--ok)',   color: 'var(--ok)' },
  [CH.wrong]: { background: 'var(--bad-bg)', border: '2px solid var(--bad)',  color: 'var(--bad)' },
  [CH.plain]: { background: 'var(--surf)',  border: '1px solid var(--line)', color: 'var(--mute)' },
}[st]);

export default function App() {
  const [db, setDb] = useState(null);
  const [err, setErr] = useState(null);
  const route = useHash();
  const st = useStore();

  useEffect(() => { loadBank().then(setDb).catch(e => setErr(e.message)); }, []);

  if (err) return <p style={S.wrap}>문항을 읽지 못했다 — {err}</p>;
  if (!db) return <p style={S.wrap}>문항을 읽는 중…</p>;

  const areas = db.areas();
  const all = progress(db.items, id => st.last(id));

  return (
    <div style={S.wrap}>
      <div style={S.card}>
        <p style={S.meta}>
          배선 확인 화면 · Build 결과로 갈아치울 자리
        </p>
        <h1 style={{ font: '700 22px/1.3 var(--font)', letterSpacing: '-.4px',
                     margin: '8px 0 4px' }}>
          기출은행 <span style={S.meta}>v2.0.0 · {db.n}문항</span>
        </h1>
        <p style={{ color: 'var(--mute)', margin: 0, fontSize: 13 }}>
          지금 주소 <code>{route.hash}</code> → <b>{route.name}</b>
          {route.params.length ? ' · ' + route.params.join(' / ') : ''}
        </p>
      </div>

      <div style={S.card}>
        <h2 style={S.h}>진도 — core/progress.js 가 셌다</h2>
        <p style={{ margin: 0, color: 'var(--mute)', fontSize: 13 }}>
          전체 {progText(all)} · 복습 대기 {st.due(db.items).length}개
        </p>
        <div style={{ height: 8, background: 'var(--hair)', borderRadius: 4,
                      marginTop: 10, overflow: 'hidden' }}>
          <div style={{ width: all.fill + '%', height: '100%',
                        background: 'linear-gradient(90deg,var(--acc),var(--vivid))' }} />
        </div>
      </div>

      <div style={S.card}>
        <h2 style={S.h}>영역 {areas.length}개 — data/bank.js 가 묶었다</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {areas.map(a => (
            <button key={a.area} onClick={() => go('/t/' + a.area)}
              style={{ ...S.ch, width: 'auto', marginBottom: 0,
                       ...look(route.params[0] === a.area ? CH.pick : CH.idle) }}>
              {a.area} <span style={S.meta}>{a.n}</span>
            </button>
          ))}
        </div>
      </div>

      <Probe db={db} st={st} area={route.name === 'area' ? route.params[0] : null} />
    </div>
  );
}

/** 한 문항을 실제로 풀어 본다 — 채점과 기록이 도는지 보는 곳 */
function Probe({ db, st, area }) {
  const pool = area ? db.byArea(area) : db.items;
  const it = pool[0];
  const [chosen, setChosen] = useState(null);
  const [graded, setGraded] = useState(false);

  useEffect(() => { setChosen(null); setGraded(false); }, [it?.id]);
  if (!it) return null;

  const states = choiceStates(it.an, chosen, graded, it.ch.length);
  const res = graded ? gradeOne(it, chosen, null) : null;

  const pick = n => {
    if (graded) return;
    setChosen(n);
    setGraded(true);
    // **판정을 여기서 하지 않는다.** core 가 준 결과를 그대로 넘긴다
    const r = gradeOne(it, n, null);
    st.record(it.id, n, r.ok, r.ms);
  };

  return (
    <div style={S.card}>
      <p style={S.meta}>{it.sj} · {it.ty} · {it.id}</p>
      {it.mt && (
        <div style={{ background: 'var(--hair)', borderRadius: 'var(--rs)',
                      padding: '12px 14px', margin: '12px 0', overflowX: 'auto',
                      fontSize: 13 }}
             dangerouslySetInnerHTML={{ __html: it.mt }} />
      )}
      <h2 style={S.stem}>{it.st}</h2>
      {it.ch.map((c, i) => (
        <button key={i} onClick={() => pick(i + 1)} disabled={graded}
          style={{ ...S.ch, ...look(states[i]) }}>
          <b style={{ marginRight: 8 }}>{CIRC[i]}</b>
          <span dangerouslySetInnerHTML={{ __html: c }} />
        </button>
      ))}
      {res && (
        <p aria-live="polite" style={{ margin: '12px 0 0', fontWeight: 700,
             color: res.ok ? 'var(--ok)' : 'var(--bad)' }}>
          {res.verdict} — 정답 {CIRC[it.an - 1]}
          {!res.ok && ` (고른 것 ${CIRC[chosen - 1]})`}
          <span style={{ ...S.meta, marginLeft: 10, fontWeight: 400 }}>
            기록됨 · 다시 {st.untilText(it.id)}
          </span>
        </p>
      )}
      {graded && it.ex && (
        <details style={{ marginTop: 12, fontSize: 13.5, color: 'var(--mute)' }}>
          <summary style={{ cursor: 'pointer', color: 'var(--ink)' }}>해설</summary>
          <div dangerouslySetInnerHTML={{ __html: it.ex }} />
        </details>
      )}
      <p style={{ ...S.meta, marginTop: 14 }}>
        발문은 순수 텍스트다 — {plain(it.st).length}자
      </p>
    </div>
  );
}
