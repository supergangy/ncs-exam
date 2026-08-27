/** PC 회차 결과 — 좌측 요약·영역별, 우측 틀린 문항.
 *
 *  제출한 그 순간의 성적을 보여 준다. `att` 로 되짚지 않는다 — 그 뒤에 다시 푼 것이
 *  섞이면 「그때 성적」이 아니게 된다. 이력에 남은 `ans`(무엇을 골랐나)로 센다.
 *
 *  **채점은 `core/grade.js` 가 한다.** 화면이 정답을 비교하면 규칙이 두 벌이 된다.
 *  **컷오프를 지어내지 않는다** — 합격선은 기관·연도마다 다르고 데이터에 없다.
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
  const [nth, setNth] = useState(-1);

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
  const graded = gradeAll(items, items.map(it => ans[it.no] ?? null));

  const byArea = new Map();
  items.forEach((it, k) => {
    const key = it.sj || '기타';
    const a = byArea.get(key) || { area: key, n: 0, ok: 0 };
    a.n++;
    if (graded.marks[k].ok) a.ok++;
    byArea.set(key, a);
  });
  const areas = [...byArea.values()]
    .map(a => ({ ...a, rate: pct(a.ok, a.n) }))
    .sort((x, y) => x.rate - y.rate);

  const missed = items.filter((_, k) => !graded.marks[k].ok);

  return (
    <>
      <div className="page-head">
        <button className="btn btn-ghost" style={{ padding: 0, minHeight: 'auto' }}
                onClick={() => go('/exams')}>
          <I.Back /> 회차 목록
        </button>
        <div className="h1" style={{ marginTop: '.5rem' }}>{r.title} 결과</div>
        <div className="row-sub">
          {new Date(rec.at).toLocaleString('ko-KR')}
          {rec.auto ? ' · 시간 초과로 자동 제출' : ''}
        </div>
      </div>

      {hist.length > 1 && (
        <div style={{ display: 'flex', gap: '.35rem', marginBottom: '1.25rem',
                      flexWrap: 'wrap' }}>
          {hist.map((h, k) => (
            <button key={k} className={'btn ' + (k === i ? 'btn-tint' : 'btn-outline')}
                    style={{ minHeight: 32 }} onClick={() => setNth(k)}>
              {k + 1}번째 {pct(h.score, h.n)}%
            </button>
          ))}
        </div>
      )}

      <div className="tiles" style={{ marginBottom: '1.25rem' }}>
        <div className="card tile">
          <div className="tile-k">정답률</div>
          <div className="tile-v">{rate}%</div>
          <div className="tile-s">{rec.score} / {rec.n} 맞음</div>
        </div>
        <div className="card tile">
          <div className="tile-k">소요 시간</div>
          <div className="tile-v" style={{ fontSize: '1.5rem' }}>{mmss(rec.sec * 1000)}</div>
          <div className="tile-s">제한 {r.min}분</div>
        </div>
        <div className="card tile">
          <div className="tile-k">표기 안 함</div>
          <div className="tile-v">{graded.blank}</div>
          <div className="tile-s">빈칸은 오답입니다</div>
        </div>
        <div className="card tile">
          <div className="tile-k">틀린 문항</div>
          <div className="tile-v">{missed.length}</div>
          <div className="tile-s">오답노트에 모입니다</div>
        </div>
      </div>

      <div className="cols">
        <div className="card pad">
          <div className="h3">영역별 — 낮은 순</div>
          <div style={{ marginTop: '.8rem' }}>
            {areas.map(a => (
              <div key={a.area} style={{ display: 'flex', alignItems: 'center', gap: '.7rem',
                                         padding: '.4rem 0' }}>
                <span className="sm" style={{ flex: 1, minWidth: 0, overflow: 'hidden',
                                              textOverflow: 'ellipsis',
                                              whiteSpace: 'nowrap' }}>{a.area}</span>
                <span className="row-n">{a.ok}/{a.n}</span>
                <div className={'bar ' + tone(a.rate)}
                     style={{ width: '8rem', flex: '0 0 auto' }}>
                  <i style={{ width: a.rate + '%' }} />
                </div>
                <span className="tick sm" style={{ width: '2.8rem', textAlign: 'right' }}>
                  {a.rate}%
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="stack">
          {missed.length > 0 && (
            <div className="card">
              <div className="pad" style={{ paddingBottom: '.6rem' }}>
                <div className="h3">틀린 문항 {missed.length}개</div>
              </div>
              <div className="rows" style={{ maxHeight: '26rem', overflowY: 'auto' }}>
                {missed.map(it => {
                  const pick = ans[it.no];
                  const k = items.findIndex(x => x.no === it.no);
                  return (
                    <button key={it.id} className="row-item"
                            onClick={() => go(poolHref({ rd: tag }) + '&at=' + k)}>
                      <span className="row-n" style={{ minWidth: '1.8rem' }}>{it.no}</span>
                      <span className="row-t">
                        <span style={{ display: 'block', overflow: 'hidden',
                                       textOverflow: 'ellipsis',
                                       whiteSpace: 'nowrap' }}>{db.line(it, 52)}</span>
                        <span className="row-sub" style={{ display: 'block' }}>
                          {it.sj} · {it.ty} ·{' '}
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
            </div>
          )}

          <div style={{ display: 'flex', gap: '.5rem' }}>
            <button className="btn btn-primary" style={{ flex: 1 }}
                    onClick={() => go(poolHref({ pool: 'wrong' }))}>
              오답노트로 다시 풀기
            </button>
            <button className="btn btn-outline" style={{ flex: 1 }} onClick={() => go('/stats')}>
              분석 보기
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

const tone = r => (r >= 80 ? 'bar-ok' : r >= 50 ? 'bar-warn' : 'bar-bad');
