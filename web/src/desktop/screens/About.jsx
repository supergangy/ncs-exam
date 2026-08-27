/** 정보 — 무엇이 얼마나 들어 있고, 어떻게 만들었나.
 *
 *  **수를 코드에 적지 않는다.** 문항 수·영역 수는 `bank.json` 에서 세어 낸다.
 *  적어 두면 배포본과 어긋나고, 그 어긋남은 화면만 보고는 알 수 없다
 *  (실제로 배포본이 540문항에서 멈춰 있던 적이 있다 — `tools/deploy_check.py`).
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
  const types = areas.reduce((s, a) => s + a.types.length, 0);

  return (
    <>
      <div className="page-head">
        <div className="h1">NCS PASS</div>
        <div className="row-sub">이전 이름 · NCS 기출은행</div>
      </div>

      <div className="cols">
        <div className="stack">
          <div className="card pad">
            <div className="h3">담긴 것</div>
            <table className="sm" style={{ width: '100%', marginTop: '.7rem' }}>
              <tbody>
                {[
                  ['문항', `${db.n}개`],
                  ['영역', `${areas.length}개 — NCS ${ncs.length} · 전산 ${cs.length}`],
                  ['유형', `${types}개`],
                  ['회차', `${db.rounds.length}개`],
                  ['데이터 판', `v${db.v}`],
                ].map(([k, v]) => (
                  <tr key={k}>
                    <td style={{ color: 'var(--faint)', padding: '.25rem 0' }}>{k}</td>
                    <td className="tick" style={{ textAlign: 'right' }}>{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card pad">
            <div className="h3">기록과 통신</div>
            <div className="sm muted" style={{ marginTop: '.6rem', lineHeight: 1.8 }}>
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
                  <span className="row-sub" style={{ display: 'block' }}>{href}</span>
                </span>
              </a>
            ))}
          </div>
        </div>

        <div className="stack">
          <div className="card pad">
            <div className="h3">어떻게 만들었나</div>
            <ol className="sm muted" style={{ margin: '.7rem 0 0', paddingLeft: '1.2rem',
                                              lineHeight: 1.95 }}>
              <li>
                <b>현황 조사</b> — 640개 기관의 공개 필기후기 <b>4,410건</b>을
                영역·유형·키워드로 분류해 출제 경향을 추정했습니다.
                원문은 보관하지 않고 분류 결과만 남깁니다.
              </li>
              <li>
                <b>격차 분석</b> — 「후기 언급 점유율 − 보유 문항 비중」으로 부족한 영역을
                찾아 우선 보완했습니다.
              </li>
              <li>
                <b>1차 자료로 재검증</b> — 후기 384건 분석은 「80문항 90분」을 가리켰지만
                시행 자료는 <b>40문항 45분</b>이었습니다. 언급 빈도는 체감 난도이지
                출제 비중이 아니었습니다. 이후 분량은 시행 공고·발주 문서로 확정합니다.
              </li>
              <li>
                <b>정답 분포</b> — 균등 20%가 아니라 실제 시험 <b>420문항을 집계한 값</b>에
                맞췄습니다 (① 14.8 · ② 21.0 · ③ 23.1 · ④ 22.9 · ⑤ 18.3).
              </li>
              <li>
                <b>기계 검증</b> — 계산·조건추리 문항은 코드가 정답을 다시 계산해
                대조합니다 (516건, 불일치 0). 법령 인용은 원문과 대조합니다 (18조각, 오류 0).
              </li>
            </ol>
          </div>

          <div className="card pad">
            <div className="h3">이 화면에 없는 것</div>
            <div className="sm muted" style={{ marginTop: '.6rem', lineHeight: 1.8 }}>
              합격선(컷오프)과 다른 응시자와의 백분위는 <b>보여 주지 않습니다.</b>
              합격선은 기관·연도마다 다르고, 백분위는 다른 사람의 기록이 필요합니다.
              가진 자료로 낼 수 없는 수치는 만들지 않았습니다 —
              대신 <b>지난 주 대비 내 변화</b>와 <b>영역별 정답률</b>을 둡니다.
            </div>
          </div>

          <button className="btn btn-ghost" onClick={() => go('/settings')}>설정으로</button>
        </div>
      </div>
    </>
  );
}
