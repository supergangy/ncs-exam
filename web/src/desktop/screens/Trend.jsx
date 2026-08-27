/** 정답률 추이 — 시리즈 하나. **범례를 두지 않는다** (제목이 곧 이름이다).
 *
 *  **쉰 날은 선을 끊는다.** 0% 로 이으면 「쉰 날」과 「다 틀린 날」이 같아 보인다.
 *  점은 푼 날에만 찍고, 숫자는 마지막 값에만 붙인다 — 모든 점에 달면 읽히지 않는다.
 *
 *  PC 는 넓으므로 모바일보다 눈금을 하나 더 두고(25·50·75) 날짜도 몇 개 적는다.
 *  마우스를 올리면 그 날의 수치를 띄운다 — 넓은 화면에서는 호버가 자연스럽다.
 *
 *  색만으로 전하지 않도록 **표로도 볼 수 있게** 둔다.
 */
import { useState } from 'react';

const W = 560, H = 160, P = { l: 30, r: 14, t: 14, b: 22 };

export default function Trend({ rows, height = H }) {
  const [at, setAt] = useState(null);            // 마우스가 올라간 날
  const n = rows.length;
  const x = i => P.l + (i * (W - P.l - P.r)) / Math.max(1, n - 1);
  const y = v => H - P.b - ((v / 100) * (H - P.t - P.b));

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
    return <p className="sm faint" style={{ marginTop: '1rem' }}>
      최근 {n}일 동안 푼 문항이 없습니다.
    </p>;
  }

  const last = pts[pts.length - 1];
  const day = t => new Date(t).toLocaleDateString('ko-KR', { month: 'numeric', day: 'numeric' });
  const hov = at != null ? rows[at] : null;

  return (
    <>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={height} role="img"
           aria-label={`최근 ${n}일 정답률 추이. 마지막 값 ${last.r.rate}%`}
           style={{ marginTop: '.8rem', display: 'block' }}
           onMouseLeave={() => setAt(null)}>
        {/* 눈금 — 뒤로 물린다 */}
        {[25, 50, 75].map(v => (
          <g key={v}>
            <line x1={P.l} x2={W - P.r} y1={y(v)} y2={y(v)}
                  stroke="var(--hair)" strokeWidth="1" />
            <text x={P.l - 6} y={y(v) + 3} fill="var(--faint)" fontSize="9"
                  textAnchor="end">{v}</text>
          </g>
        ))}

        {runs.map((run, k) => (
          <path key={k} fill="none" stroke="var(--acc)" strokeWidth="2"
                strokeLinecap="round" strokeLinejoin="round"
                d={run.map((p, j) => `${j ? 'L' : 'M'}${x(p.i)},${y(p.r.rate)}`).join(' ')} />
        ))}

        {pts.map(p => (
          <circle key={p.i} cx={x(p.i)} cy={y(p.r.rate)} r={at === p.i ? 5 : 3.4}
                  fill="var(--surf)" stroke="var(--acc)" strokeWidth="2" />
        ))}

        {/* 마지막 값만 직접 라벨 */}
        <text x={x(last.i) - 6} y={y(last.r.rate) - 9} fill="var(--ink)"
              fontSize="12" fontWeight="700" textAnchor="end">{last.r.rate}%</text>

        {/* 날짜 — 처음·중간·끝만 */}
        {[0, Math.floor((n - 1) / 2), n - 1].map(i => (
          <text key={i} x={x(i)} y={H - 6} fill="var(--faint)" fontSize="9"
                textAnchor={i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle'}>
            {day(rows[i].at)}
          </text>
        ))}

        {/* 호버 판 — 마크보다 넓게 잡는다 */}
        {rows.map((r, i) => (
          <rect key={'h' + i} x={x(i) - (W - P.l - P.r) / (2 * Math.max(1, n - 1))}
                y={P.t} width={(W - P.l - P.r) / Math.max(1, n - 1)} height={H - P.t - P.b}
                fill="transparent" onMouseEnter={() => setAt(i)} />
        ))}
        {at != null && (
          <line x1={x(at)} x2={x(at)} y1={P.t} y2={H - P.b}
                stroke="var(--acc-ln)" strokeWidth="1" />
        )}
      </svg>

      <div className="sm" style={{ minHeight: '1.4em', color: 'var(--mute)' }}>
        {hov
          ? (hov.rate == null
              ? `${day(hov.at)} — 푼 문항이 없습니다`
              : `${day(hov.at)} — ${hov.n}문항 · 정답률 ${hov.rate}%`)
          : <span className="faint">막대 위에 마우스를 올리면 그 날의 수치가 보입니다</span>}
      </div>

      <details style={{ marginTop: '.5rem' }}>
        <summary className="sm muted" style={{ cursor: 'pointer' }}>숫자로 보기</summary>
        <table className="sm" style={{ width: '100%', marginTop: '.5rem',
                                       borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['날짜', '푼 수', '맞음', '정답률'].map(h => (
                <th key={h} style={{ textAlign: h === '날짜' ? 'left' : 'right',
                                     color: 'var(--faint)', fontWeight: 400,
                                     padding: '.2rem 0' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.at}>
                <td>{day(r.at)}</td>
                <td className="tick" style={{ textAlign: 'right' }}>{r.n || '—'}</td>
                <td className="tick" style={{ textAlign: 'right' }}>{r.n ? r.ok : '—'}</td>
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
