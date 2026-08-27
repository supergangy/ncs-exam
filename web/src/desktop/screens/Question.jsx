/** PC 문항 풀이 — 시안 `question-engine-desktop` 을 옮긴 것.
 *
 *  좌측에 문항, 우측에 팔레트와 통계. 1200px 아래에서는 팔레트가 본문 아래로 내려간다
 *  (본문 폭을 먼저 지킨다).
 *
 *  **PC 에만 있는 것 셋**
 *    키보드   1~5 선지 · Enter 제출/다음 · ←→ 이동 · F 표시
 *    글자 크기 긴 발문을 읽을 때. 고른 값은 기록에 남는다
 *    힌트     시안의 「AI Hint」 자리. **AI 가 아니라 해설의 첫 문장**이다 —
 *             방향만 주고 답은 주지 않는다. 없는 것을 있다고 하지 않는다
 *
 *  **채점을 여기서 하지 않는다.** `core/grade.js` 가 준 결과를 그대로 보여 준다.
 */
import { useEffect, useState } from 'react';

import { XP_OK, XP_TRY } from '../../core/goal.js';
import { choiceStates, gradeOne, CH, MAX_MS } from '../../core/grade.js';
import { CIRC, mmss, plain } from '../../core/text.js';
import { makePool } from '../../data/pool.js';
import { useElapsed } from '../../hooks/clock.js';
import Passage from '../../Passage.jsx';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useStore } from '../../store/useStore.js';

const CLS = {
  [CH.idle]: '', [CH.plain]: '',
  [CH.pick]: 'opt-picked', [CH.right]: 'opt-correct', [CH.wrong]: 'opt-wrong',
};
const MARK = { [CH.right]: '✓', [CH.wrong]: '✗' };

const SIZES = [15, 16.5, 18, 20];      // 발문·선지 글자 크기 단계

/** 해설의 첫 문장 — 방향만 준다. 태그를 벗기고 첫 마침표까지 자른다 */
function hintOf(ex) {
  if (!ex) return null;
  const s = plain(ex).trim();
  const at = s.search(/[.!?]\s|다\.\s|다\.$/);
  return at > 0 ? s.slice(0, at + 2).trim() : s.slice(0, 90) + (s.length > 90 ? '…' : '');
}

export default function Question({ db, query }) {
  const st = useStore();
  const pool = makePool(db, st, query);
  const saved = st.solo();

  const [at, setAt] = useState(() => {
    const want = parseInt(new URLSearchParams(query || '').get('at') ?? '', 10);
    if (Number.isInteger(want) && want >= 0 && want < pool.items.length) return want;
    if (saved?.key === pool.key && saved.at < pool.items.length) return saved.at;
    return 0;
  });
  const [chosen, setChosen] = useState(null);
  const [graded, setGraded] = useState(false);
  const [hint, setHint] = useState(false);
  const [toast, setToast] = useState(false);

  const it = pool.items[at] || null;
  const startedAt = useElapsed(it?.id);
  const size = SIZES.includes(st.pref.qsize) ? st.pref.qsize : SIZES[1];

  useEffect(() => {
    if (!pool.items.length) return;
    if (saved?.key !== pool.key) {
      st.setSolo(pool.key, pool.items.map(i => i.id), 0);
      setAt(0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pool.key]);

  useEffect(() => { setChosen(null); setGraded(false); setHint(false); }, [it?.id]);

  // 키보드 — PC 에서 마우스를 오가지 않고 풀 수 있게
  useEffect(() => {
    const onKey = e => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const tag = e.target?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      if (!it) return;

      const n = Number(e.key);
      if (n >= 1 && n <= it.ch.length) { e.preventDefault(); if (!graded) setChosen(n); return; }
      if (e.key === 'Enter') {
        e.preventDefault();
        if (graded) move(1);
        else if (chosen != null) submit();
        return;
      }
      if (e.key === 'ArrowLeft') { e.preventDefault(); move(-1); }
      if (e.key === 'ArrowRight') { e.preventDefault(); move(1); }
      if (e.key.toLowerCase() === 'f') { e.preventDefault(); st.toggle(it.id, 'f'); }
    };
    addEventListener('keydown', onKey);
    return () => removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [it?.id, chosen, graded, at, pool.items.length]);

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
  const done = pool.items.filter(i => st.tried(i.id)).length;

  function submit() {
    if (graded || chosen == null) return;
    const r = gradeOne(it, chosen, startedAt());
    st.record(it.id, chosen, r.ok, r.ms);
    setGraded(true);
    setToast(true);
    setTimeout(() => setToast(false), 1800);
  }
  function move(d) {
    const n = Math.min(pool.items.length - 1, Math.max(0, at + d));
    if (n === at) return;
    setAt(n);
    st.soloAt(n);
  }

  return (
    <div className="split">
      <div>
        <div className="qhead">
          <span className="tick">{at + 1} / {pool.items.length}</span>
          <span className="faint">·</span>
          <span className="sm" style={{ flex: 1, minWidth: 0, overflow: 'hidden',
                                        textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {pool.title}{pool.sub ? ` · ${pool.sub}` : ''}
          </span>
          <span className="sm faint">글자</span>
          {SIZES.map((v, i) => (
            <button key={v} className={'btn ' + (v === size ? 'btn-tint' : 'btn-ghost')}
                    style={{ minHeight: 30, padding: '0 .5rem',
                             fontSize: 11 + i * 1.5 + 'px' }}
                    onClick={() => st.setPref({ qsize: v })}
                    aria-pressed={v === size} aria-label={`글자 크기 ${i + 1}단계`}>
              가
            </button>
          ))}
        </div>

        <div className="bar" style={{ marginBottom: '1rem' }}>
          <i style={{ width: Math.round(((at + 1) / pool.items.length) * 100) + '%' }} />
        </div>

        <div className="card pad">
          <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
            <span className="badge badge-acc">문항 {it.no || at + 1}</span>
            <span className="badge pill-xp">
              <I.Star />{graded ? (res.ok ? XP_OK : XP_TRY) : XP_OK} XP
            </span>
            <span className="sm faint">{it.sj} · {it.ty}</span>
            <button className="btn btn-ghost" style={{ marginLeft: 'auto' }}
                    onClick={() => st.toggle(it.id, 'f')}
                    aria-pressed={!!st.marked(it.id)?.f}>
              <I.Flag style={{ color: st.marked(it.id)?.f ? 'var(--warn-vivid)' : undefined }} />
              표시 <span className="sm faint">F</span>
            </button>
          </div>

          <Passage db={db} it={it} />
          <h1 className="stem" style={{ fontSize: size + 'px' }}
              dangerouslySetInnerHTML={{ __html: it.st }} />

          {/* 자료는 PC 에서 기본으로 펼친다 — 넓으므로 접을 이유가 없다 */}
          {it.mt && <div className="material" dangerouslySetInnerHTML={{ __html: it.mt }} />}

          <div className="stack" role="group" aria-label="선지" style={{ gap: '.5rem' }}>
            {it.ch.map((c, i) => (
              <button key={i} className={'opt ' + CLS[states[i]]}
                      onClick={() => !graded && setChosen(i + 1)} disabled={graded}
                      aria-pressed={chosen === i + 1}>
                <span className="opt-mark" aria-hidden="true">{MARK[states[i]] || (i + 1)}</span>
                <span className="opt-body">
                  <span className="opt-label" style={{ fontSize: size - 1.5 + 'px' }}
                        dangerouslySetInnerHTML={{ __html: c }} />
                </span>
              </button>
            ))}
          </div>

          {hint && !graded && (
            <div className="card pad" style={{ marginTop: '1rem', background: 'var(--warn-bg)',
                                               borderColor: 'var(--warn-tint)' }}>
              <div className="sm" style={{ fontWeight: 'var(--w-bold)', color: 'var(--warn)' }}>
                해설의 첫 문장
              </div>
              <div className="sm" style={{ marginTop: '.3rem' }}>{hintOf(it.ex)}</div>
            </div>
          )}

          {res && (
            <div className="card pad" id="verdict" aria-live="polite"
                 style={{ marginTop: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '.6rem' }}>
                <span className={'badge ' + (res.ok ? 'badge-ok' : 'badge-bad')}>
                  {res.ok ? '맞음' : '틀림'}
                </span>
                <span className="sm">
                  정답 {CIRC[it.an - 1]}
                  {!res.ok && chosen && ` · 고른 것 ${CIRC[chosen - 1]}`}
                </span>
                <span className="tick sm faint" style={{ marginLeft: 'auto' }}>
                  {mmss(Math.min(res.ms, MAX_MS))} 걸림 · 다시 {st.untilText(it.id)}
                </span>
              </div>
              {it.ex && (
                <div className="sm" style={{ marginTop: '.8rem', color: 'var(--mute)',
                                             lineHeight: 1.75 }}
                     dangerouslySetInnerHTML={{ __html: it.ex }} />
              )}
            </div>
          )}

          <div style={{ display: 'flex', gap: '.5rem', marginTop: '1.25rem',
                        alignItems: 'center' }}>
            <button className="btn btn-outline" onClick={() => move(-1)} disabled={at === 0}>
              <I.Back /> 이전
            </button>
            {!graded && (
              <>
                <button className="btn btn-ghost" onClick={() => move(1)}
                        disabled={at + 1 >= pool.items.length}>건너뛰기</button>
                {it.ex && !hint && (
                  <button className="btn btn-ghost" onClick={() => setHint(true)}>힌트</button>
                )}
              </>
            )}
            <span style={{ marginLeft: 'auto' }} />
            {graded
              ? <button className="btn btn-primary"
                        onClick={() => (at + 1 < pool.items.length ? move(1) : go('/done'))}>
                  {at + 1 < pool.items.length ? '다음 문항' : '마치기'}
                  <span className="sm" style={{ opacity: .7 }}>Enter</span>
                </button>
              : <button className="btn btn-primary" onClick={submit} disabled={chosen == null}>
                  {chosen == null ? '선지를 고르세요 (1~5)' : '제출'}
                  {chosen != null && <span className="sm" style={{ opacity: .7 }}>Enter</span>}
                </button>}
          </div>
        </div>

        {last && !graded && (
          <p className="sm faint" style={{ marginTop: '.8rem' }}>
            지난번에 {last.k ? '맞혔습니다' : '틀렸습니다'} · 다시 {st.untilText(it.id)}
          </p>
        )}
      </div>

      <div className="aside">
        {toast && (
          <div className="toast" role="status">
            <I.Check style={{ width: 15, height: 15 }} />기록했습니다
          </div>
        )}

        <div className="card pad">
          <div className="h3">문항 목록</div>
          <div className="legend" style={{ margin: '.6rem 0 .7rem' }}>
            <span><i style={{ background: 'var(--acc-bg)',
                              border: '1px solid var(--acc-ln)' }} />푼 것 {done}</span>
            <span><i style={{ background: 'var(--surf)',
                              border: '1px solid var(--line)' }} />안 푼 것 {pool.items.length - done}</span>
            <span><i style={{ background: 'var(--warn-tint)',
                              border: '1px solid var(--warn-vivid)' }} />표시</span>
          </div>
          <div className="palette">
            {pool.items.map((q, i) => {
              const cls = ['pal'];
              if (st.tried(q.id)) cls.push('done');
              if (st.marked(q.id)?.f) cls.push('flag');
              if (i === at) cls.push('here');
              return (
                <button key={q.id} className={cls.join(' ')}
                        onClick={() => { setAt(i); st.soloAt(i); }}
                        aria-label={`${i + 1}번 문항`}
                        aria-current={i === at ? 'true' : undefined}>
                  {i + 1}
                </button>
              );
            })}
          </div>
        </div>

        <div className="card pad">
          <div className="h3">키보드</div>
          <table className="sm" style={{ width: '100%', marginTop: '.5rem' }}>
            <tbody>
              {[['1 ~ 5', '선지 고르기'], ['Enter', '제출 · 다음'],
                ['← →', '앞뒤 문항'], ['F', '표시']].map(([k, v]) => (
                <tr key={k}>
                  <td><span className="search-key" style={{ position: 'static' }}>{k}</span></td>
                  <td style={{ color: 'var(--mute)', paddingLeft: '.5rem' }}>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
