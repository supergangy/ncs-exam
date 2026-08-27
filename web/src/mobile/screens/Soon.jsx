/** 아직 옮기지 않은 화면 — **무엇이 올 자리인지 적어 둔다.**
 *
 *  「준비 중」만 띄우면 어디까지 됐는지 알 수 없다. 배포본에 이미 있는 기능들이므로
 *  옮기는 순서를 여기에 적어 두고, 하나씩 지운다.
 */
import { go } from '../../router/useHash.js';

const WHAT = {
  area:     '영역 안의 유형 목록',
  type:     '유형 안의 문항 목록',
  question: '문항 풀이 — 자료·선지·채점·해설',
  exams:    '회차 목록',
  exam:     '회차 안내 — 문항 수·제한 시간',
  sit:      '응시 중 — 타이머·OMR·팔레트',
  result:   '회차 결과 — 영역별 정답률·오답 목록',
  stats:    '분석 — 정답률 추이·영역별·소요 시간',
  wrong:    '오답노트',
  review:   '복습 — SM-2 가 정한 오늘 몫',
  marks:    '표시해 둔 문항',
  search:   '전문 검색',
  kw:       '키워드 목록',
  settings: '설정 — 목표·시험일·기록 백업',
  about:    '정보 — 판 번호·문항 수',
  more:     '더보기',
  done:     '오늘 몫 마침',
};

export default function Soon({ name, params }) {
  return (
    <div className="empty">
      <p style={{ fontWeight: 700, color: 'var(--ink)' }}>{WHAT[name] || name}</p>
      <p className="sm">이 화면은 아직 옮기지 않았습니다.</p>
      {params?.length ? <p className="sm faint">받은 값 — {params.join(' / ')}</p> : null}
      <button className="btn btn-tint" style={{ marginTop: '1rem' }} onClick={() => go('/')}>
        홈으로
      </button>
    </div>
  );
}
