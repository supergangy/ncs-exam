/** 모바일 판 — 상주 머리말 · 본문 · 하단 탭.
 *
 *  **PC 판과 코드를 엮지 않는다.** 여기서 무엇을 고쳐도 `desktop/` 은 바뀌지 않는다.
 *  공유하는 것은 화면이 없는 것들뿐이다 — `core/`(로직) · `data/`(문항) ·
 *  `store/`(기록) · `router/`(주소) · `styles/`(토큰·부품) · `icons.jsx`.
 *
 *  주소는 **배포본과 같다.** 사용자가 북마크한 `#/t/수리능력` 이 여기서도 열려야 한다.
 */
import { useEffect, useState } from 'react';

import { loadBank } from '../data/bank.js';
import * as I from '../icons.jsx';
import { useHash, go } from '../router/useHash.js';
import { store } from '../store/useStore.js';

import About from './screens/About.jsx';
import Area from './screens/Area.jsx';
import Exam from './screens/Exam.jsx';
import Done from './screens/Done.jsx';
import Exams from './screens/Exams.jsx';
import Home from './screens/Home.jsx';
import More from './screens/More.jsx';
import Kw from './screens/Kw.jsx';
import Pool from './screens/Pool.jsx';
import Question from './screens/Question.jsx';
import Result from './screens/Result.jsx';
import Search from './screens/Search.jsx';
import Settings from './screens/Settings.jsx';
import Sit from './screens/Sit.jsx';
import Stats from './screens/Stats.jsx';
import Type from './screens/Type.jsx';

/** 하단 탭 넷 — 시안 구성(Home · Tests · Analytics · Profile)에 맞춘다.
 *  복습·오답노트는 홈의 연습 방식 카드와 「더보기」에서 들어간다. */
const TABS = [
  { to: '/',      icon: I.Home,  label: '홈',     on: ['home', 'area', 'type', 'question'] },
  { to: '/exams', icon: I.Exam,  label: '회차',   on: ['exams', 'exam', 'sit', 'result'] },
  { to: '/stats', icon: I.Chart, label: '분석',   on: ['stats'] },
  { to: '/more',  icon: I.More,  label: '더보기', on: ['more', 'settings', 'about', 'search',
                                                      'wrong', 'review', 'marks', 'kw'] },
];

/** 하단에 버튼 줄이 있는 화면 — 탭 + 버튼 몫을 함께 비워야 마지막 줄이 가려지지 않는다 */
const HAS_FOOT = new Set(['question', 'sit']);

export default function App() {
  const [db, setDb] = useState(null);
  const [err, setErr] = useState(null);
  const route = useHash();

  // 모바일 판은 `/m/` 아래에서 돈다 — 문항은 한 칸 위에 있다
  useEffect(() => { loadBank('../data/bank.json').then(setDb).catch(e => setErr(e.message)); }, []);

  // 화면을 옮기면 위로 올린다 — 스크롤이 남아 있으면 새 화면 중간이 보인다
  useEffect(() => { window.scrollTo(0, 0); }, [route.hash]);

  // 설정에서 고른 화면 밝기를 다시 씌운다. `system` 이면 속성을 지워
  // `prefers-color-scheme` 에 맡긴다 (tokens.css 가 그렇게 짜여 있다)
  useEffect(() => {
    const t = store.pref.theme;
    if (t === 'light' || t === 'dark') document.documentElement.dataset.theme = t;
    else delete document.documentElement.dataset.theme;
  }, []);

  return (
    <>
      <Header db={db} />
      <main className={'view' + (HAS_FOOT.has(route.name) ? ' has-foot' : '')}>
        {err ? <p className="empty">문항을 읽지 못했습니다 — {err}</p>
             : !db ? <p className="empty">문항을 읽는 중…</p>
             : <Screen route={route} db={db} />}
      </main>
      <Tabs route={route} />
    </>
  );
}

function Header({ db }) {
  return (
    <header className="top">
      <img className="top-logo" src="../icon-192.png" alt="" />
      <span className="top-name">NCS PASS</span>
      <div className="top-right">
        {db && <span className="badge badge-flat sm">{db.n}문항</span>}
        <button className="btn btn-ghost narrow" style={{ padding: '0 .5rem' }}
                onClick={() => go('/search')} aria-label="검색">
          <I.Search />
        </button>
      </div>
    </header>
  );
}

function Tabs({ route }) {
  return (
    <nav className="tabs" aria-label="주요 화면">
      {TABS.map(t => {
        const Icon = t.icon;
        const here = t.on.includes(route.name);
        return (
          <button key={t.to} className="tab" onClick={() => go(t.to)}
                  aria-current={here ? 'page' : undefined}>
            <Icon />
            {t.label}
          </button>
        );
      })}
    </nav>
  );
}

/** 주소 → 화면. `router/useHash.js` 의 `ROUTES` 와 짝이 맞아야 한다. */
function Screen({ route, db }) {
  switch (route.name) {
    case 'home':
    // PC 의 「문항 은행」 주소. 모바일에서는 홈이 그 일을 한다
    case 'bank':
      return <Home db={db} />;
    case 'area':
      return <Area db={db} area={route.params[0]} />;
    case 'type':
      return <Type db={db} area={route.params[0]} type={route.params[1]} />;
    case 'question':
      return <Question db={db} query={route.params[0]} />;
    case 'exams':
      return <Exams db={db} />;
    case 'exam':
      return <Exam db={db} tag={route.params[0]} />;
    case 'sit':
      return <Sit db={db} tag={route.params[0]} />;
    case 'result':
      return <Result db={db} tag={route.params[0]} />;
    case 'stats':
      return <Stats db={db} />;
    case 'more':
      return <More db={db} />;
    case 'wrong':
      return <Pool db={db} kind="wrong" />;
    case 'review':
      return <Pool db={db} kind="review" />;
    case 'marks':
      return <Pool db={db} kind="marks" />;
    case 'search':
      return <Search db={db} />;
    case 'settings':
      return <Settings />;
    case 'about':
      return <About db={db} />;
    case 'kw':
      return <Kw db={db} />;
    case 'done':
      return <Done db={db} />;
    case 'notfound':
      return (
        <div className="empty">
          <p>없는 주소입니다 — <code>{route.hash}</code></p>
          <button className="btn btn-tint" onClick={() => go('/')}>홈으로</button>
        </div>
      );
    default:
      // `ROUTES` 의 이름을 **전부** 위에서 다룬다. 여기 오면 라우터에 이름을
      // 더하고 화면을 잊은 것이다 — 조용히 빈 화면을 주지 않는다
      return (
        <div className="empty">
          <p>화면이 없습니다 — <code>{route.name}</code></p>
          <button className="btn btn-tint" onClick={() => go('/')}>홈으로</button>
        </div>
      );
  }
}
