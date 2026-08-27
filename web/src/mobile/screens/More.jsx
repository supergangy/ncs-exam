/** 더보기 — 탭 넷에 못 들어간 화면들의 문.
 *
 *  **개수를 함께 보여 준다.** 「오답노트」만 있으면 들어가 봐야 비었는지 알 수 있다.
 */
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useDerived } from '../../store/useStore.js';

export default function More({ db }) {
  const m = useDerived(s => ({
    wrong: db.items.filter(i => s.isWrong(i.id)).length,
    due: s.due(db.items).length,
    marks: db.items.filter(i => s.marked(i.id)).length,
    tried: db.items.filter(i => s.tried(i.id)).length,
  }), [db]);

  const rows = [
    { icon: I.Search, to: '/search', t: '전문 검색',
      d: '발문·선지·분류·키워드·자료·지문·해설' },
    { icon: I.Pencil, to: '/wrong', t: '오답노트', n: m.wrong,
      d: '마지막에 틀린 문항. 다시 맞히면 빠집니다' },
    { icon: I.Refresh, to: '/review', t: '복습', n: m.due,
      d: 'SM-2 간격으로 돌아오는 오늘 몫' },
    { icon: I.Bookmark, to: '/marks', t: '표시해 둔 문항', n: m.marks,
      d: '나중에 다시 볼 것으로 표시한 문항' },
    { icon: I.Gear, to: '/settings', t: '설정',
      d: '하루 목표 · 시험일 · 기록 백업' },
    { icon: I.Exam, to: '/about', t: '정보',
      d: '판 번호 · 문항 수 · 만든 방법' },
  ];

  return (
    <div className="stack">
      <div className="card pad">
        <div className="h2">{m.tried} / {db.n}</div>
        <div className="row-sub">문항을 풀어 봤습니다</div>
        <div className="bar" style={{ marginTop: '.6rem' }}>
          <i style={{ width: Math.round((m.tried / db.n) * 100) + '%' }} />
        </div>
      </div>

      <div className="card rows">
        {rows.map(r => {
          const Icon = r.icon;
          return (
            <button key={r.to} className="row-item" onClick={() => go(r.to)}>
              <span className="mode-ic" style={{ width: 32, height: 32 }}><Icon /></span>
              <span className="row-t">
                {r.t}
                <span className="row-sub" style={{ display: 'block' }}>{r.d}</span>
              </span>
              {r.n != null && (
                <span className={'badge ' + (r.n ? 'badge-acc' : 'badge-flat')}>{r.n}</span>
              )}
              <I.Chevron className="chev" />
            </button>
          );
        })}
      </div>
    </div>
  );
}
