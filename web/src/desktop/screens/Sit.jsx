/** PC 회차 응시 — 좌측 문항, **우측 OMR 이 늘 보인다.**
 *
 *  모바일은 답안지를 접었다 펴야 하지만 PC 는 넓다. 실제 시험지처럼 옆에 두면
 *  「어디까지 표기했나」를 확인하러 화면을 옮기지 않아도 된다.
 *
 *  **여기서 채점하지 않는다.** 고른 것만 담아 두고 제출할 때 `gradeAll` 이 본다.
 *  답은 문항 번호(`no`)를 키로 저장한다 — 배포본과 같은 구조다.
 *
 *  시간이 다하면 자동 제출한다. 키보드로도 풀 수 있다 (1~5 · ←→ · F).
 */
import { useEffect, useState } from 'react';

import { gradeAll } from '../../core/grade.js';
import { mmss } from '../../core/text.js';
import { useNow } from '../../hooks/clock.js';
import Passage from '../../Passage.jsx';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useStore } from '../../store/useStore.js';

export default function Sit({ db, tag }) {
  const st = useStore();
  const sit = st.sit();
  const r = db.round(tag);
  const items = db.byRound(tag);

  const [ask, setAsk] = useState(false);

  const live = !!sit && sit.tag === tag && items.length > 0;
  const now = useNow(1000, live);
  const left = live ? sit.endsAt - now : 0;
  const out = live && left <= 0;

  const idx = live ? Math.max(0, items.findIndex(i => i.no === sit.at_no)) : 0;

  useEffect(() => {
    if (out) submit(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [out]);

  // 키보드 — 시험지를 넘기듯
  useEffect(() => {
    if (!live) return undefined;
    const onKey = e => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const tag2 = e.target?.tagName;
      if (tag2 === 'INPUT' || tag2 === 'TEXTAREA') return;
      const it = items[idx];
      if (!it) return;
      const n = Number(e.key);
      if (n >= 1 && n <= it.ch.length) { e.preventDefault(); st.sitPick(it.no, n); return; }
      if (e.key === 'ArrowLeft') { e.preventDefault(); move(-1); }
      if (e.key === 'ArrowRight' || e.key === 'Enter') { e.preventDefault(); move(1); }
      if (e.key.toLowerCase() === 'f') { e.preventDefault(); st.sitFlag(it.no); }
    };
    addEventListener('keydown', onKey);
    return () => removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [live, idx, items.length]);

  if (!r) {
    return (
      <div className="empty">
        <p>없는 회차입니다 — {tag}</p>
        <button className="btn btn-tint" onClick={() => go('/exams')}>회차 목록</button>
      </div>
    );
  }
  if (!live) {
    return (
      <div className="empty">
        <p style={{ fontWeight: 700, color: 'var(--ink)' }}>{r.title}</p>
        <p className="sm">응시 중이 아닙니다.</p>
        <button className="btn btn-tint" style={{ marginTop: '1rem' }}
                onClick={() => go('/exam/' + tag)}>회차 안내로</button>
      </div>
    );
  }

  const it = items[idx];
  const chosen = sit.ans[it.no] ?? null;
  const answered = items.filter(i => sit.ans[i.no] != null).length;
  const flagged = items.filter(i => sit.flag[i.no]).length;

  function submit(auto = false) {
    const arr = items.map(i => sit.ans[i.no] ?? null);
    st.submitSit(items, gradeAll(items, arr), auto);
    go('/result/' + tag);
  }
  function move(d) {
    const n = Math.min(items.length - 1, Math.max(0, idx + d));
    if (n !== idx) st.sitAt(items[n].no);
  }

  return (
    <div className="split">
      <div>
        <div className="qhead">
          <span className="tick" style={{ fontSize: '1.35rem',
                   color: left < 60000 ? 'var(--bad)' : 'var(--ink)' }}>
            {mmss(Math.max(0, left))}
          </span>
          <span className="sm faint">남음 · 제한 {r.min}분</span>
          <span className="sm" style={{ marginLeft: 'auto' }}>{r.title}</span>
        </div>

        <div className="bar" style={{ marginBottom: '1rem' }}>
          <i style={{ width: Math.round((answered / items.length) * 100) + '%' }} />
        </div>

        <div className="card pad">
          <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
            <span className="badge badge-acc">문항 {it.no}</span>
            <span className="sm faint">{it.sj} · {it.ty}</span>
            <button className="btn btn-ghost" style={{ marginLeft: 'auto' }}
                    onClick={() => st.sitFlag(it.no)} aria-pressed={!!sit.flag[it.no]}>
              <I.Flag style={{ color: sit.flag[it.no] ? 'var(--warn-vivid)' : undefined }} />
              표시 <span className="sm faint">F</span>
            </button>
          </div>

          <Passage db={db} it={it} />
          <h1 className="stem" dangerouslySetInnerHTML={{ __html: it.st }} />
          {it.mt && <div className="material" dangerouslySetInnerHTML={{ __html: it.mt }} />}

          <div className="stack" role="group" aria-label="선지" style={{ gap: '.5rem' }}>
            {it.ch.map((c, i) => (
              <button key={i} className={'opt ' + (chosen === i + 1 ? 'opt-picked' : '')}
                      onClick={() => st.sitPick(it.no, i + 1)}
                      aria-pressed={chosen === i + 1}>
                <span className="opt-mark" aria-hidden="true">{i + 1}</span>
                <span className="opt-body">
                  <span className="opt-label" dangerouslySetInnerHTML={{ __html: c }} />
                </span>
              </button>
            ))}
          </div>

          <div style={{ display: 'flex', gap: '.5rem', marginTop: '1.25rem',
                        alignItems: 'center' }}>
            <button className="btn btn-outline" onClick={() => move(-1)} disabled={idx === 0}>
              <I.Back /> 이전
            </button>
            <span style={{ marginLeft: 'auto' }} />
            {idx + 1 < items.length
              ? <button className="btn btn-primary" onClick={() => move(1)}>
                  다음 문항 <span className="sm" style={{ opacity: .7 }}>Enter</span>
                </button>
              : <button className="btn btn-primary" onClick={() => setAsk(true)}>제출하기</button>}
          </div>
        </div>

        {ask && (
          <div className="card pad" style={{ marginTop: '1rem', borderColor: 'var(--acc)' }}>
            <div className="h3">제출하시겠습니까?</div>
            <div className="sm muted" style={{ marginTop: '.3rem' }}>
              {items.length - answered > 0
                ? `표기하지 않은 ${items.length - answered}문항은 오답으로 처리됩니다.`
                : '모든 문항에 표기했습니다.'}
              {' '}제출하면 되돌릴 수 없습니다.
            </div>
            <div style={{ display: 'flex', gap: '.5rem', marginTop: '.9rem' }}>
              <button className="btn btn-outline" onClick={() => setAsk(false)}>더 풀기</button>
              <button className="btn btn-primary" onClick={() => submit(false)}>제출</button>
            </div>
          </div>
        )}
      </div>

      <div className="aside">
        <div className="card pad">
          <div className="h3">답안지</div>
          <div className="sm muted" style={{ marginTop: '.2rem' }}>
            {answered} / {items.length} 표기{flagged ? ` · 표시 ${flagged}` : ''}
          </div>
          <div className="legend" style={{ margin: '.6rem 0 .7rem' }}>
            <span><i style={{ background: 'var(--acc-bg)',
                              border: '1px solid var(--acc-ln)' }} />표기함</span>
            <span><i style={{ background: 'var(--surf)',
                              border: '1px solid var(--line)' }} />비어 있음</span>
            <span><i style={{ background: 'var(--warn-tint)',
                              border: '1px solid var(--warn-vivid)' }} />표시</span>
          </div>
          <div className="palette">
            {items.map((q, i) => {
              const cls = ['pal'];
              if (sit.ans[q.no] != null) cls.push('done');
              if (sit.flag[q.no]) cls.push('flag');
              if (i === idx) cls.push('here');
              return (
                <button key={q.no} className={cls.join(' ')} onClick={() => st.sitAt(q.no)}
                        aria-label={`${q.no}번`}
                        aria-current={i === idx ? 'true' : undefined}>
                  {q.no}
                </button>
              );
            })}
          </div>
          <button className="btn btn-primary" style={{ width: '100%', marginTop: '.9rem' }}
                  onClick={() => setAsk(true)}>제출하기</button>
        </div>

        <div className="card pad">
          <div className="h3">키보드</div>
          <table className="sm" style={{ width: '100%', marginTop: '.5rem' }}>
            <tbody>
              {[['1 ~ 5', '표기'], ['Enter · →', '다음'], ['←', '이전'], ['F', '표시']].map(([k, v]) => (
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
