/** 아이콘 — **문자를 쓰지 않고 직접 그린다.**
 *
 *  배포본은 `⚐ ⚑ ✎ ✕` 같은 문자를 아이콘으로 썼다. 그 글자는 기기마다 자형이
 *  다르고, 없는 기기에서는 두부(□)가 된다. 폰트에 넣어 해결할 수도 있지만
 *  아이콘을 폰트에 의존시킬 이유가 없다 — 24px 격자에 직접 그린다.
 *
 *  모바일·PC 가 같은 것을 쓴다. 크기는 CSS 가 정한다(`width`/`height` 를 박지 않는다).
 *  선 굵기 2 · 끝 둥글게 — 시안의 아이콘 톤이다.
 */

const S = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
};

/** 공통 껍데기. `aria-hidden` 이 기본이다 — 뜻은 옆의 글자가 전한다.
 *  아이콘만 있는 단추에는 `title` 을 넘겨 이름을 준다. */
function Ico({ title, children, ...rest }) {
  return (
    <svg viewBox="0 0 24 24" role={title ? 'img' : undefined}
         aria-hidden={title ? undefined : 'true'} aria-label={title} {...S} {...rest}>
      {title && <title>{title}</title>}
      {children}
    </svg>
  );
}

// ── 항해 ─────────────────────────────────────────────────────────────
export const Home = p => (
  <Ico {...p}><path d="M3 10.5 12 3l9 7.5" /><path d="M5 9.5V21h14V9.5" /></Ico>
);
export const Exam = p => (            // 회차 — 답안지
  <Ico {...p}><path d="M6 3h12v18H6z" /><path d="M9 8h6M9 12h6M9 16h3" /></Ico>
);
export const Chart = p => (           // 분석
  <Ico {...p}><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></Ico>
);
export const More = p => (            // 더보기
  <Ico {...p}><circle cx="5" cy="12" r="1.4" /><circle cx="12" cy="12" r="1.4" />
    <circle cx="19" cy="12" r="1.4" /></Ico>
);

// ── 연습 방식 ────────────────────────────────────────────────────────
export const Book = p => (            // 낱개 풀이
  <Ico {...p}><path d="M4 4h7v16H4z" /><path d="M13 4h7v16h-7z" /><path d="M11 4v16" /></Ico>
);
export const Timer = p => (           // 회차 응시
  <Ico {...p}><circle cx="12" cy="13" r="8" /><path d="M12 13V9M9 2h6" /></Ico>
);
export const Target = p => (          // 취약 영역
  <Ico {...p}><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3.4" /></Ico>
);
export const Refresh = p => (         // 복습
  <Ico {...p}><path d="M20 12a8 8 0 1 1-2.6-5.9" /><path d="M20 4v4h-4" /></Ico>
);

// ── 표시·상태 ────────────────────────────────────────────────────────
export const Search = p => (
  <Ico {...p}><circle cx="10.5" cy="10.5" r="6.5" /><path d="M15.5 15.5 21 21" /></Ico>
);
export const Flame = p => (           // 연속일 — ⚑ 를 대신한다
  <Ico {...p}><path d="M12 3c3 3.4 5.5 6 5.5 9.6A5.5 5.5 0 0 1 12 21a5.5 5.5 0 0 1-5.5-8.4C7 10 9 8.6 9.6 6.4c1 1 1.6 2 1.8 3.2C12.3 8 12.6 5.6 12 3z" /></Ico>
);
export const Star = p => (            // 경험치
  <Ico {...p}><path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1 5.9L12 17l-5.2 2.7 1-5.9L3.5 9.7l5.9-.8z" /></Ico>
);
export const Flag = p => (            // 표시해 둔 문항 — ⚐ 를 대신한다
  <Ico {...p}><path d="M6 21V4" /><path d="M6 4h11l-2 4 2 4H6" /></Ico>
);
export const Check = p => (
  <Ico {...p}><path d="M4.5 12.5 9.5 17.5 20 7" /></Ico>
);
export const Close = p => (           // ✕ 를 대신한다
  <Ico {...p}><path d="M6 6l12 12M18 6 6 18" /></Ico>
);
export const Pencil = p => (          // ✎ 를 대신한다
  <Ico {...p}><path d="M4 20h4L20 8l-4-4L4 16z" /><path d="M14.5 5.5 18.5 9.5" /></Ico>
);
export const Bookmark = p => (
  <Ico {...p}><path d="M7 3h10v18l-5-4-5 4z" /></Ico>
);

// ── 이동 ─────────────────────────────────────────────────────────────
export const Chevron = p => (
  <Ico {...p}><path d="M9 5l7 7-7 7" /></Ico>
);
export const Back = p => (
  <Ico {...p}><path d="M20 12H4" /><path d="M10 6 4 12l6 6" /></Ico>
);
/** 설정 — 이빨을 선으로 그리면 해(sun) 처럼 보인다.
 *  점선 원으로 톱니를 만들고 축을 안에 둔다. */
export const Gear = p => (
  <Ico {...p}>
    <circle cx="12" cy="12" r="8.2" strokeDasharray="2.4 2.7" />
    <circle cx="12" cy="12" r="3.4" />
  </Ico>
);
export const Calendar = p => (
  <Ico {...p}><path d="M4 6h16v15H4z" /><path d="M4 10h16M9 3v4M15 3v4" /></Ico>
);
export const Text = p => (            // 글자 크기
  <Ico {...p}><path d="M4 6h16M9 6v14M15 10h5M17.5 10v10" /></Ico>
);
