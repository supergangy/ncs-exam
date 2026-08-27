/** 회차 결과 — 제출한 그 순간의 성적을 보여 준다.
 *
 *  `att` 로 되짚지 않는다. 제출 뒤에 그 문항을 다시 풀면 기록이 바뀌므로
 *  「그때 성적」이 아니게 된다. 대신 성적 이력에 남은 `ans`(무엇을 골랐나)로 센다.
 *
 *  **컷오프를 지어내지 않는다.** 시안에는 「Passed (Cutoff 75%)」가 있지만
 *  합격선은 기관·연도마다 다르고 데이터에 없다. 그 자리에 영역별 정답률을 둔다 —
 *  「어디를 더 봐야 하나」가 실제로 쓸 수 있는 정보다.
 */
import { useState } from 'react';

import { gradeAll } from '../../core/grade.js';
import { pct } from '../../core/progress.js';
import { CIRC, mmss } from '../../core/text.js';
import { poolHref } from '../../data/pool.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useDerived } from '../../store/useStore.js';

export default function Result({ db, tag }) {
  const r = db.round(tag);
  const items = db.byRound(tag);
  const hist = useDerived(s => s.examHistory(tag), [tag]);
  const [nth, setNth] = useState(-1);            // -1 = 가장 최근

  if (!r || !hist.length) {
    return (
      <div className="empty">
        <p>{r ? '아직 제출한 기록이 없습니다.' : `없는 회차입니다 — ${tag}`}</p>
        <button className="btn btn-tint" onClick={() => go(r ? '/exam/' + tag : '/exams')}>
          {r ? '회차 안내로' : '회차 목록'}
        </button>
      </div>
    );
  }

  const i = nth < 0 ? hist.length - 1 : nth;
  const rec = hist[i];
  const ans = rec.ans || {};
  const rate = pct(rec.score, rec.n);

  // 채점은 core 가 한다 — 그때 고른 답을 그대로 넘긴다
  const graded = gradeAll(items, items.map(it => ans[it.no] ?? null));

  const byArea = new Map();
  items.forEach((it, i) => {
    const k = it.sj || '기타';
    const a = byArea.get(k) || { area: k, n: 0, ok: 0 };
    a.n++;
    if (graded.marks[i].ok) a.ok++;
    byArea.set(k, a);
  });
  const areas = [...byArea.values()]
    .map(a => ({ ...a, rate: pct(a.ok, a.n) }))
    .sort((x, y) => x.rate - y.rate);

  const missed = items.filter((_, i) => !graded.marks[i].ok);
  const blank = graded.blank;

  return (
    <div className="stack">
      <div className="card pad">
        <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem' }}>
          <span className="sm faint" style={{ flex: 1, minWidth: 0 }}>{r.title}</span>
          {rec.auto ? <span className="badge badge-warn">시간 초과 제출</span> : null}
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '.5rem',
                      marginTop: '.3rem' }}>
          <span className="tick" style={{ fontSize: '2.2rem', fontWeight: 'var(--w-bold)',
                   letterSpacing: '-1px' }}>{rate}%</span>
          <span className="sm muted">{rec.score} / {rec.n} 맞음</span>
        </div>
        <div className={'bar ' + (rate >= 80 ? 'bar-ok' : rate >= 50 ? 'bar-warn' : 'bar-bad')}
             style={{ margin: '.7rem 0 .5rem' }}>
          <i style={{ width: rate + '%' }} />
        </div>
        <div className="sm muted">
          {mmss(rec.sec * 1000)} 걸림 · 제한 {r.min}분
          {blank ? ` · 표기 안 함 ${blank}` : ''}
        </div>

        {hist.length > 1 && (
          <div style={{ display: 'flex', gap: '.35rem', marginTop: '.8rem', flexWrap: 'wrap' }}>
            {hist.map((h, k) => (
              <button key={k}
                      className={'btn ' + (k === i ? 'btn-tint' : 'btn-outline')}
                      style={{ minHeight: '2rem', padding: '0 .6rem', fontSize: 'var(--t-sm)' }}
                      onClick={() => setNth(k)}>
                {k + 1}번째 {pct(h.score, h.n)}%
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="card pad">
        <div className="h3">영역별 — 낮은 순</div>
        <div style={{ marginTop: '.7rem' }}>
          {areas.map(a => (
            <div key={a.area} style={{ display: 'flex', alignItems: 'center', gap: '.6rem',
                                       padding: '.35rem 0' }}>
              <span className="sm" style={{ flex: 1, minWidth: 0, overflow: 'hidden',
                                            textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {a.area}
              </span>
              <span className="row-n">{a.ok}/{a.n}</span>
              <div className={'bar ' + (a.rate >= 80 ? 'bar-ok' : a.rate >= 50 ? 'bar-warn' : 'bar-bad')}
                   style={{ width: '4.5rem', flex: '0 0 auto' }}>
                <i style={{ width: a.rate + '%' }} />
              </div>
              <span className="tick sm" style={{ width: '2.6rem', textAlign: 'right' }}>
                {a.rate}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {missed.length > 0 && (
        <div>
          <div className="h2" style={{ margin: '.3rem 0 .6rem' }}>
            틀린 문항 {missed.length}개
          </div>
          <div className="card rows">
            {missed.map(it => {
              const pick = ans[it.no];
              const idx = items.findIndex(x => x.no === it.no);
              return (
                <button key={it.id} className="row-item"
                        onClick={() => go(poolHref({ rd: tag }) + '&at=' + idx)}>
                  <span className="row-n" style={{ minWidth: '1.6rem' }}>{it.no}</span>
                  <span className="row-t">
                    <span style={{ display: 'block', overflow: 'hidden',
                                   textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {db.line(it, 34)}
                    </span>
                    <span className="row-sub" style={{ display: 'block' }}>
                      {pick == null
                        ? '표기하지 않음'
                        : `고른 것 ${CIRC[pick - 1] || '—'} · 정답 ${CIRC[it.an - 1]}`}
                    </span>
                  </span>
                  <I.Chevron className="chev" />
                </button>
              );
            })}
          </div>
          <button className="btn btn-primary" style={{ width: '100%', marginTop: '.75rem' }}
                  onClick={() => go(poolHref({ pool: 'wrong' }))}>
            오답노트로 다시 풀기
          </button>
        </div>
      )}

      <div style={{ display: 'flex', gap: '.5rem' }}>
        <button className="btn btn-outline" style={{ flex: 1 }} onClick={() => go('/exams')}>
          회차 목록
        </button>
        <button className="btn btn-tint" style={{ flex: 1 }} onClick={() => go('/stats')}>
          분석 보기
        </button>
      </div>
    </div>
  );
}
