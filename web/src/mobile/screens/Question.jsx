/** 문항 풀이 — 시안 `mobile-question-engine` 을 옮긴 것.
 *
 *  **채점을 여기서 하지 않는다.** `core/grade.js` 가 준 결과를 그대로 보여 준다.
 *  선지 상태(기본·고름·정답·오답)도 `choiceStates` 가 정한다 — 화면이 규칙을
 *  다시 쓰면 두 벌이 되어 어긋난다.
 *
 *  **자리를 기록에 남긴다.** 앱을 닫았다 열면 그 문항에서 이어진다 (`store.solo`).
 *  id 목록까지 저장하는 이유는 `data/pool.js` 주석에 있다.
 *
 *  시안에 있던 「3 XP」 배지는 남겼다 — `core/goal.js` 의 실제 배점이다.
 */
import { useEffect, useState } from 'react';

import { XP_OK, XP_TRY } from '../../core/goal.js';
import { choiceStates, gradeOne, CH, MAX_MS } from '../../core/grade.js';
import { CIRC, mmss } from '../../core/text.js';
import { makePool } from '../../data/pool.js';
import { useElapsed } from '../../hooks/clock.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useStore } from '../../store/useStore.js';

/** 선지 상태 → 클래스. 색은 `components.css` 가 갖는다 */
const CLS = {
  [CH.idle]: '', [CH.plain]: '',
  [CH.pick]: 'opt-picked', [CH.right]: 'opt-correct', [CH.wrong]: 'opt-wrong',
};
const MARK = { [CH.right]: '✓', [CH.wrong]: '✗' };

export default function Question({ db, query }) {
  const st = useStore();
  const pool = makePool(db, st, query);

  // 이어서 풀 자리 — 같은 묶음이면 기록에 남은 위치에서 시작한다
  const saved = st.solo();
  const [at, setAt] = useState(() => {
    // 목록에서 그 문항을 눌러 들어왔으면 주소가 이긴다
    const want = parseInt(new URLSearchParams(query || '').get('at') ?? '', 10);
    if (Number.isInteger(want) && want >= 0 && want < pool.items.length) return want;
    if (saved?.key === pool.key && saved.at < pool.items.length) return saved.at;
    return 0;
  });
  const [chosen, setChosen] = useState(null);
  const [graded, setGraded] = useState(false);
  const [openMat, setOpenMat] = useState(false);
  const [openPal, setOpenPal] = useState(false);
  const [toast, setToast] = useState(false);

  const it = pool.items[at] || null;
  // 시각을 직접 읽지 않는다 — 훅이 문항이 바뀔 때마다 시계를 다시 잡는다
  const startedAt = useElapsed(it?.id);

  // 묶음이 바뀌면 자리를 새로 잡고 기록에 심는다
  useEffect(() => {
    if (!pool.items.length) return;
    if (saved?.key !== pool.key) {
      st.setSolo(pool.key, pool.items.map(i => i.id), 0);
      setAt(0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pool.key]);

  // 문항이 바뀌면 상태를 비운다 (시계는 useElapsed 가 맡는다)
  useEffect(() => {
    setChosen(null); setGraded(false); setOpenMat(false);
  }, [it?.id]);

  if (!pool.items.length) {
    return (
      <div className="empty">
        <p style={{ fontWeight: 700, color: 'var(--ink)' }}>{pool.title}</p>
        <p className="sm">지금 풀 문항이 없습니다.</p>
        <button className="btn btn-tint" style={{ marginTop: '1rem' }} onClick={() => go('/')}>
          홈으로
        </button>
      </div>
    );
  }
  if (!it) return <p className="empty">문항을 찾지 못했습니다.</p>;

  const states = choiceStates(it.an, chosen, graded, it.ch.length);
  const res = graded ? gradeOne(it, chosen, startedAt()) : null;
  const last = st.last(it.id);

  const submit = () => {
    if (graded || chosen == null) return;
    const r = gradeOne(it, chosen, startedAt());
    st.record(it.id, chosen, r.ok, r.ms);
    setGraded(true);
    setToast(true);
    setTimeout(() => setToast(false), 1600);
  };

  const move = d => {
    const n = Math.min(pool.items.length - 1, Math.max(0, at + d));
    setAt(n);
    st.soloAt(n);
  };
  const jump = n => { setAt(n); st.soloAt(n); setOpenPal(false); };

  const done = pool.items.filter(i => st.tried(i.id)).length;

  return (
    <>
      <div className="stack">
        {toast && (
          <div className="toast" role="status"><I.Check style={{ width: 15, height: 15 }} />
            기록했습니다 · 다시 {st.untilText(it.id)}
          </div>
        )}

        <div>
          <div className="qmeta">
            <span className="tick">{at + 1} / {pool.items.length}</span>
            <span className="faint">·</span>
            <span style={{ flex: 1, minWidth: 0, overflow: 'hidden',
                           textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {pool.title}
            </span>
            <span className="badge badge-flat">{done}개 풀었음</span>
          </div>
          <div className="bar" style={{ marginTop: '.5rem' }}>
            <i style={{ width: Math.round(((at + 1) / pool.items.length) * 100) + '%' }} />
          </div>
        </div>

        <div className="card pad">
          <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem' }}>
            <span className="badge badge-acc">문항 {it.no || at + 1}</span>
            <span className="badge pill-xp"><I.Star />{graded ? (res.ok ? XP_OK : XP_TRY) : XP_OK} XP</span>
            <button className="btn btn-ghost" style={{ marginLeft: 'auto', padding: '0 .5rem' }}
                    onClick={() => st.toggle(it.id, 'f')}
                    aria-label="확인 필요 표시">
              <I.Flag style={{ color: st.marked(it.id)?.f ? 'var(--warn-vivid)' : undefined }} />
            </button>
          </div>

          <div className="sm faint" style={{ marginTop: '.5rem' }}>{it.sj} · {it.ty}</div>
          <h1 className="stem" dangerouslySetInnerHTML={{ __html: it.st }} />

          {it.mt && (
            <>
              <button className="btn btn-outline" style={{ width: '100%' }}
                      onClick={() => setOpenMat(v => !v)} aria-expanded={openMat}>
                {openMat ? '자료 접기' : '자료 펼치기'}
              </button>
              {openMat && <div className="material"
                               dangerouslySetInnerHTML={{ __html: it.mt }} />}
            </>
          )}
        </div>

        <div className="stack" role="group" aria-label="선지">
          {it.ch.map((c, i) => (
            <button key={i} className={'opt ' + CLS[states[i]]}
                    onClick={() => !graded && setChosen(i + 1)} disabled={graded}
                    aria-pressed={chosen === i + 1}
                    aria-describedby={graded && states[i] !== CH.plain ? 'verdict' : undefined}>
              {/* 번호·✓·✗ 는 눈으로 보는 것이다. 읽어 주면 「111일」처럼 붙어 들린다 —
                  스크린리더에는 선지 본문만 이름으로 준다 */}
              <span className="opt-mark" aria-hidden="true">{MARK[states[i]] || (i + 1)}</span>
              <span className="opt-body">
                <span className="opt-label" dangerouslySetInnerHTML={{ __html: c }} />
              </span>
            </button>
          ))}
        </div>

        {res && (
          <div className="card pad" id="verdict" aria-live="polite">
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span className={'badge ' + (res.ok ? 'badge-ok' : 'badge-bad')}>
                {res.ok ? '맞음' : '틀림'}
              </span>
              <span className="sm">
                정답 {CIRC[it.an - 1]}
                {!res.ok && chosen && ` · 고른 것 ${CIRC[chosen - 1]}`}
              </span>
              <span className="tick sm faint" style={{ marginLeft: 'auto' }}>
                {mmss(Math.min(res.ms, MAX_MS))}
              </span>
            </div>
            {it.ex && (
              <div className="sm" style={{ marginTop: '.7rem', color: 'var(--mute)' }}
                   dangerouslySetInnerHTML={{ __html: it.ex }} />
            )}
          </div>
        )}

        <div className="card pad">
          <button className="btn btn-ghost" style={{ width: '100%' }}
                  onClick={() => setOpenPal(v => !v)} aria-expanded={openPal}>
            {openPal ? '문항 목록 접기' : `문항 목록 (${pool.items.length})`}
          </button>
          {openPal && (
            <div className="palette" style={{ marginTop: '.7rem' }}>
              {pool.items.map((q, i) => {
                const l = st.last(q.id);
                const cls = ['pal'];
                if (l) cls.push('done');
                if (st.marked(q.id)?.f) cls.push('flag');
                if (i === at) cls.push('here');
                return (
                  <button key={q.id} className={cls.join(' ')} onClick={() => jump(i)}
                          aria-label={`${i + 1}번 문항`} aria-current={i === at ? 'true' : undefined}>
                    {i + 1}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {last && !graded && (
          <p className="sm faint" style={{ textAlign: 'center' }}>
            지난번에 {last.k ? '맞혔습니다' : '틀렸습니다'} · 다시 {st.untilText(it.id)}
          </p>
        )}
      </div>

      <div className="foot">
        <button className="btn btn-outline narrow" onClick={() => move(-1)} disabled={at === 0}
                aria-label="이전 문항">
          <I.Back />
        </button>
        {graded
          ? <button className="btn btn-primary"
                    onClick={() => (at + 1 < pool.items.length ? move(1) : go('/'))}>
              {at + 1 < pool.items.length ? '다음 문항' : '마치기'}
            </button>
          : <button className="btn btn-primary" onClick={submit} disabled={chosen == null}>
              {chosen == null ? '선지를 고르세요' : '제출'}
            </button>}
      </div>
    </>
  );
}
