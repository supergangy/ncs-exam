/** 회차 응시 — 제한 시간·OMR·제출 후 일괄 채점.
 *
 *  **여기서는 채점하지 않는다.** 고른 것만 담아 두고, 제출할 때
 *  `core/grade.js` 의 `gradeAll` 이 한꺼번에 본다. 실제 시행과 같은 순서다.
 *
 *  **답은 문항 번호(`no`)를 키로 저장한다** — 배포본과 같은 구조다.
 *  인덱스로 두면 문항 순서가 바뀔 때 답이 어긋나고, 옛 판으로 응시하던 사람이
 *  이어 풀 수 없다. 고를 때마다 저장하므로 앱을 닫아도 그대로다.
 *
 *  시간이 다하면 **자동 제출한다.** 시험이 그렇다. 남은 시간이 1분 아래로
 *  내려가면 색으로 알린다.
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

  const [ask, setAsk] = useState(false);        // 제출 확인 카드
  const [openOmr, setOpenOmr] = useState(false);

  const live = !!sit && sit.tag === tag && items.length > 0;
  const now = useNow(1000, live);
  const left = live ? sit.endsAt - now : 0;
  const out = live && left <= 0;

  // 시간이 다하면 제출한다
  useEffect(() => {
    if (out) submit(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [out]);

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
                onClick={() => go('/exam/' + tag)}>
          회차 안내로
        </button>
      </div>
    );
  }

  // 보고 있는 문항 — 번호로 찾는다. 없으면 첫 문항
  const idx = Math.max(0, items.findIndex(i => i.no === sit.at_no));
  const it = items[idx];
  const chosen = sit.ans[it.no] ?? null;
  const answered = items.filter(i => sit.ans[i.no] != null).length;
  const flagged = items.filter(i => sit.flag[i.no]).length;

  function submit(auto = false) {
    const arr = items.map(i => sit.ans[i.no] ?? null);
    st.submitSit(items, gradeAll(items, arr), auto);
    go('/result/' + tag);
  }

  const move = d => {
    const n = Math.min(items.length - 1, Math.max(0, idx + d));
    st.sitAt(items[n].no);
  };

  return (
    <>
      <div className="stack">
        <div className="card" style={{ padding: '.7rem .9rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
            <span className="tick" style={{ fontSize: 'var(--t-h3)',
                     color: left < 60000 ? 'var(--bad)' : 'var(--ink)' }}>
              {mmss(Math.max(0, left))}
            </span>
            <span className="sm faint">남음</span>
            <span className="badge badge-flat" style={{ marginLeft: 'auto' }}>
              {answered} / {items.length} 표기
            </span>
            {flagged > 0 && <span className="badge badge-warn">표시 {flagged}</span>}
          </div>
          <div className="bar" style={{ marginTop: '.5rem' }}>
            <i style={{ width: Math.round((answered / items.length) * 100) + '%' }} />
          </div>
        </div>

        <div className="card pad">
          <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem' }}>
            <span className="badge badge-acc">문항 {it.no}</span>
            <span className="sm faint">{it.sj} · {it.ty}</span>
            <button className="btn btn-ghost" style={{ marginLeft: 'auto', padding: '0 .5rem' }}
                    onClick={() => st.sitFlag(it.no)} aria-label="나중에 다시 볼 표시"
                    aria-pressed={!!sit.flag[it.no]}>
              <I.Flag style={{ color: sit.flag[it.no] ? 'var(--warn-vivid)' : undefined }} />
            </button>
          </div>
          <Passage db={db} it={it} />
          <h1 className="stem" dangerouslySetInnerHTML={{ __html: it.st }} />
          {it.mt && <div className="material" dangerouslySetInnerHTML={{ __html: it.mt }} />}
        </div>

        <div className="stack" role="group" aria-label="선지">
          {it.ch.map((c, i) => (
            <button key={i} className={'opt ' + (chosen === i + 1 ? 'opt-picked' : '')}
                    onClick={() => st.sitPick(it.no, i + 1)} aria-pressed={chosen === i + 1}>
              <span className="opt-mark" aria-hidden="true">{i + 1}</span>
              <span className="opt-body">
                <span className="opt-label" dangerouslySetInnerHTML={{ __html: c }} />
              </span>
            </button>
          ))}
        </div>

        <div className="card pad">
          <button className="btn btn-ghost" style={{ width: '100%' }}
                  onClick={() => setOpenOmr(v => !v)} aria-expanded={openOmr}>
            {openOmr ? '답안지 접기' : `답안지 (${answered}/${items.length})`}
          </button>
          {openOmr && (
            <>
              <div className="palette" style={{ marginTop: '.7rem' }}>
                {items.map((q, i) => {
                  const cls = ['pal'];
                  if (sit.ans[q.no] != null) cls.push('done');
                  if (sit.flag[q.no]) cls.push('flag');
                  if (i === idx) cls.push('here');
                  return (
                    <button key={q.no} className={cls.join(' ')}
                            onClick={() => { st.sitAt(q.no); setOpenOmr(false); }}
                            aria-label={`${q.no}번`}
                            aria-current={i === idx ? 'true' : undefined}>
                      {q.no}
                    </button>
                  );
                })}
              </div>
              <div className="sm faint" style={{ marginTop: '.6rem' }}>
                파랑 = 표기함 · 노랑 = 표시해 둔 것 · 테두리 = 지금 문항
              </div>
            </>
          )}
        </div>

        {ask && (
          <div className="card pad" style={{ borderColor: 'var(--acc)' }}>
            <div className="h3">제출하시겠습니까?</div>
            <div className="sm muted" style={{ marginTop: '.3rem' }}>
              {items.length - answered > 0
                ? `표기하지 않은 ${items.length - answered}문항은 오답으로 처리됩니다.`
                : '모든 문항에 표기했습니다.'}
              {' '}제출하면 되돌릴 수 없습니다.
            </div>
            <div style={{ display: 'flex', gap: '.5rem', marginTop: '.8rem' }}>
              <button className="btn btn-outline" style={{ flex: 1 }} onClick={() => setAsk(false)}>
                더 풀기
              </button>
              <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => submit(false)}>
                제출
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="foot">
        <button className="btn btn-outline narrow" onClick={() => move(-1)} disabled={idx === 0}
                aria-label="이전 문항">
          <I.Back />
        </button>
        {idx + 1 < items.length
          ? <button className="btn btn-primary" onClick={() => move(1)}>다음 문항</button>
          : <button className="btn btn-primary" onClick={() => setAsk(true)}>제출하기</button>}
        {idx + 1 < items.length && (
          <button className="btn btn-tint narrow" onClick={() => setAsk(true)}>제출</button>
        )}
      </div>
    </>
  );
}
