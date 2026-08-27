/** PC 판 — 좌측 항해 · 상주 머리말 · 본문(+선택적 우측 팔레트).
 *
 *  **모바일 판과 코드를 엮지 않는다.** 여기서 무엇을 고쳐도 `mobile/` 은 바뀌지 않는다.
 *  공유하는 것은 화면이 없는 것들뿐이다 — `core/` · `data/` · `store/` · `router/` ·
 *  `styles/`(토큰·부품) · `icons.jsx` · `hooks/`.
 *
 *  주소는 **모바일 판과 같다.** 북마크한 `#/t/수리능력` 이 어느 판에서도 열려야 한다.
 */
import { useEffect, useRef, useState } from 'react';

import { streak, xp, level } from '../core/goal.js';
import { loadBank } from '../data/bank.js';
import * as I from '../icons.jsx';
import { useHash, go } from '../router/useHash.js';
import { store, useDerived } from '../store/useStore.js';

import About from './screens/About.jsx';
import Bank from './screens/Bank.jsx';
import Done from './screens/Done.jsx';
import Exam from './screens/Exam.jsx';
import Exams from './screens/Exams.jsx';
import Home from './screens/Home.jsx';
import Kw from './screens/Kw.jsx';
import Pool from './screens/Pool.jsx';
import Question from './screens/Question.jsx';
import Result from './screens/Result.jsx';
import Search from './screens/Search.jsx';
import Settings from './screens/Settings.jsx';
import Sit from './screens/Sit.jsx';
import Stats from './screens/Stats.jsx';

/** 좌측 항해 — 묶음별로. 모바일 탭 넷보다 넓게 펼 수 있다 */
const NAV = [
  { sec: '학습' },
  { to: '/',      icon: I.Home,     label: '홈',      on: ['home'] },
  { to: '/bank',  icon: I.Book,     label: '문항',    on: ['bank', 'area', 'type', 'question', 'done'] },
  { to: '/kw',    icon: I.Tag,      label: '키워드',  on: ['kw'] },
  { to: '/exams', icon: I.Timer,    label: '회차',    on: ['exams', 'exam', 'sit', 'result'] },
  { to: '/review', icon: I.Refresh, label: '복습',    on: ['review'], count: 'due' },
  { to: '/wrong', icon: I.Pencil,   label: '오답노트', on: ['wrong'], count: 'wrong' },
  { sec: '기록' },
  { to: '/stats', icon: I.Chart,    label: '분석',    on: ['stats'] },
  { to: '/marks', icon: I.Bookmark, label: '표시함',  on: ['marks'], count: 'marks' },
];
const NAV_FOOT = [
  { to: '/settings', icon: I.Gear, label: '설정', on: ['settings'] },
  { to: '/about',    icon: I.Exam, label: '정보', on: ['about'] },
];

/** 우측 팔레트를 쓰는 화면 — 본문 폭을 먼저 지키고 1200px 아래에서는 아래로 내린다 */
const SPLIT = new Set(['question', 'sit']);

export default function App() {
  const [db, setDb] = useState(null);
  const [err, setErr] = useState(null);
  const route = useHash();

  useEffect(() => { loadBank().then(setDb).catch(e => setErr(e.message)); }, []);
  useEffect(() => { window.scrollTo(0, 0); }, [route.hash]);

  // 설정에서 고른 화면 밝기를 다시 씌운다 (`system` 이면 속성을 지워 기기 설정에 맡긴다)
  useEffect(() => {
    const t = store.pref.theme;
    if (t === 'light' || t === 'dark') document.documentElement.dataset.theme = t;
    else delete document.documentElement.dataset.theme;
  }, []);

  return (
    <div className="shell">
      <Nav db={db} route={route} />
      <div className="main">
        <Bar db={db} />
        {err ? <p className="empty">문항을 읽지 못했습니다 — {err}</p>
             : !db ? <p className="empty">문항을 읽는 중…</p>
             : <div className={'page' + (SPLIT.has(route.name) ? ' page-split' : '')}>
                 <Screen route={route} db={db} />
               </div>}
      </div>
    </div>
  );
}

function Nav({ db, route }) {
  const counts = useDerived(s => (db ? {
    due: s.due(db.items).length,
    wrong: db.items.filter(i => s.isWrong(i.id)).length,
    marks: db.items.filter(i => s.marked(i.id)).length,
  } : {}), [db]);

  const item = it => {
    const Icon = it.icon;
    const here = it.on.includes(route.name);
    const n = it.count ? counts[it.count] : null;
    return (
      <button key={it.to} className="nav-item" onClick={() => go(it.to)}
              aria-current={here ? 'page' : undefined} title={it.label}>
        <Icon />
        <span>{it.label}</span>
        {n ? <span className="n">{n}</span> : null}
      </button>
    );
  };

  return (
    <nav className="nav" aria-label="주요 화면">
      <div className="nav-brand">
        <img src="icon-192.png" alt="" />
        <b>NCS PASS</b>
      </div>
      {NAV.map((it, i) => (it.sec
        ? <div key={'s' + i} className="nav-sec">{it.sec}</div>
        : item(it)))}
      <div className="nav-foot">{NAV_FOOT.map(item)}</div>
    </nav>
  );
}

/** 상주 머리말 — 시안처럼 검색·연속일·경험치를 둔다.
 *
 *  검색 칸은 **누르면 검색 화면으로 가는 문**이다. 여기서 결과를 드롭다운으로
 *  띄우면 화면이 둘로 갈리고, 넓은 화면에서는 본문에 펼치는 것이 읽기 낫다.
 *  `Ctrl/⌘ K` 도 같은 곳으로 보낸다.
 */
function Bar({ db }) {
  const g = useDerived(s => ({
    streak: streak(s.d.att),
    xp: xp(s.d.att, s.d.exams),
  }), []);
  const btn = useRef(null);

  useEffect(() => {
    const onKey = e => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        go('/search');
      }
    };
    addEventListener('keydown', onKey);
    return () => removeEventListener('keydown', onKey);
  }, []);

  const lv = level(g.xp);
  const mac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || '');

  return (
    <header className="topbar">
      <div className="search" style={{ maxWidth: '24rem' }}>
        <button ref={btn} className="field" onClick={() => go('/search')}
                style={{ display: 'flex', alignItems: 'center', gap: '.5rem',
                         cursor: 'pointer', color: 'var(--faint)', textAlign: 'left' }}>
          <I.Search style={{ width: 16, height: 16 }} />
          발문·선지·해설에서 찾기
          <span className="search-key" style={{ position: 'static', marginLeft: 'auto' }}>
            {mac ? '⌘' : 'Ctrl'} K
          </span>
        </button>
      </div>

      <div className="topbar-right">
        {db && <span className="badge badge-flat">{db.n}문항</span>}
        {g.streak > 0 && (
          <span className="badge pill-streak"><I.Flame />{g.streak}일 연속</span>
        )}
        <span className="badge pill-xp"><I.Star />{g.xp.toLocaleString()} XP · Lv.{lv.lv}</span>
        <a className="btn btn-ghost" href="./m/" style={{ minHeight: 34, padding: '0 .6rem' }}>
          모바일 판
        </a>
      </div>
    </header>
  );
}

function Screen({ route, db }) {
  switch (route.name) {
    case 'home':     return <Home db={db} />;
    case 'bank':     return <Bank db={db} />;
    case 'area':     return <Bank db={db} area={route.params[0]} />;
    case 'type':     return <Bank db={db} area={route.params[0]} type={route.params[1]} />;
    case 'question': return <Question db={db} query={route.params[0]} />;
    case 'exams':    return <Exams db={db} />;
    case 'exam':     return <Exam db={db} tag={route.params[0]} />;
    case 'sit':      return <Sit db={db} tag={route.params[0]} />;
    case 'result':   return <Result db={db} tag={route.params[0]} />;
    case 'stats':    return <Stats db={db} />;
    case 'wrong':    return <Pool db={db} kind="wrong" />;
    case 'review':   return <Pool db={db} kind="review" />;
    case 'marks':    return <Pool db={db} kind="marks" />;
    case 'search':   return <Search db={db} />;
    case 'settings': return <Settings />;
    case 'about':    return <About db={db} />;
    case 'kw':       return <Kw db={db} />;
    case 'done':     return <Done db={db} />;
    default:
      return (
        <div className="empty">
          <p>없는 주소입니다 — <code>{route.hash}</code></p>
          <button className="btn btn-tint" onClick={() => go('/')}>홈으로</button>
        </div>
      );
  }
}
