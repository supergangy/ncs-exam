/** 정보 — 무엇이 얼마나 들어 있고, 어떻게 만들었나.
 *
 *  **수를 코드에 적지 않는다.** 문항 수·영역 수는 `bank.json` 에서 세어 낸다.
 *  적어 두면 배포본과 어긋나고, 그 어긋남은 화면만 보고는 알 수 없다.
 *  (실제로 배포본이 540문항에서 멈춰 있던 적이 있다 — `tools/deploy_check.py`)
 */
import { go } from '../../router/useHash.js';

const LINKS = [
  ['배포된 웹앱', 'https://supergangy.github.io/ncs-pass-app/'],
  ['저장소', 'https://github.com/supergangy/ncs-exam'],
];

export default function About({ db }) {
  const areas = db.areas();
  const ncs = areas.filter(a => db.byArea(a.area)[0]?.tr === 'ncs');
  const cs = areas.filter(a => db.byArea(a.area)[0]?.tr === 'cs');

  return (
    <div className="stack">
      <div className="card pad" style={{ textAlign: 'center' }}>
        <img src="../icon-192.png" alt=""
             style={{ width: 64, height: 64, borderRadius: 16 }} />
        <div className="h2" style={{ marginTop: '.6rem' }}>NCS PASS</div>
        <div className="sm faint">이전 이름 · NCS 기출은행</div>
      </div>

      <div className="card pad">
        <div className="h3">담긴 것</div>
        <table className="sm" style={{ width: '100%', marginTop: '.6rem' }}>
          <tbody>
            {[
              ['문항', `${db.n}개`],
              ['영역', `${areas.length}개 — NCS ${ncs.length} · 전산 ${cs.length}`],
              ['유형', `${db.types?.length || areas.reduce((s, a) => s + a.types.length, 0)}개`],
              ['회차', `${db.rounds.length}개`],
              ['데이터 판', `v${db.v}`],
            ].map(([k, v]) => (
              <tr key={k}>
                <td style={{ color: 'var(--faint)', padding: '.2rem 0' }}>{k}</td>
                <td className="tick" style={{ textAlign: 'right' }}>{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card pad">
        <div className="h3">어떻게 만들었나</div>
        <ul className="sm muted" style={{ margin: '.6rem 0 0', paddingLeft: '1.1rem',
                                          lineHeight: 1.8 }}>
          <li>640개 기관의 공개 필기후기 <b>4,410건</b>을 영역·유형·키워드로 분류해
              출제 경향을 추정했습니다.</li>
          <li>추정을 <b>시행 공고·발주 문서</b>로 다시 확인했습니다. 후기의 언급 빈도는
              체감 난도이지 출제 비중이 아니었습니다.</li>
          <li>정답 위치는 균등 20%가 아니라 <b>실제 시험 420문항을 집계한 분포</b>에
              맞췄습니다.</li>
          <li>계산·조건추리 문항은 <b>코드가 정답을 다시 계산해</b> 대조합니다
              (516건, 불일치 0).</li>
        </ul>
      </div>

      <div className="card pad">
        <div className="h3">기록과 통신</div>
        <div className="sm muted" style={{ marginTop: '.5rem', lineHeight: 1.75 }}>
          <b>서버가 없습니다.</b> 문항은 앱과 함께 내려오고, 푼 기록은 이 기기에만
          남습니다. 계정도 동기화도 없으므로 신호가 없는 곳에서도 그대로 풀립니다.
          기기를 바꿀 때는 설정에서 백업 파일을 옮기세요.
        </div>
      </div>

      <div className="card rows">
        {LINKS.map(([t, href]) => (
          <a key={href} className="row-item" href={href} target="_blank" rel="noreferrer">
            <span className="row-t">
              {t}
              <span className="row-sub" style={{ display: 'block', overflow: 'hidden',
                                                 textOverflow: 'ellipsis' }}>{href}</span>
            </span>
          </a>
        ))}
      </div>

      <button className="btn btn-ghost" style={{ width: '100%' }} onClick={() => go('/settings')}>
        설정으로
      </button>
    </div>
  );
}
