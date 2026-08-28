/** Build 가 만든 화면 코드를 검사한다 — **눈으로 보지 않고 센다.**
 *
 *     node tool/check_ui.mjs
 *
 *  Build 는 그림에 없는 것을 자유롭게 채운다. 세 가지가 특히 위험하다 —
 *
 *  ① **로직을 새로 짠다.** 채점·복습 간격이 core 밖에 다시 생기면 겉으로는
 *     도는데 답이 틀리거나 복습이 안 뜬다. 검증한 764문항이 무의미해진다
 *  ② **position: fixed 를 남긴다.** 지금 판이 못 쓰게 된 바로 그 이유다.
 *     세 곳에 있어 서로 덮었고 제출 버튼이 눌리지 않았다
 *  ③ **색을 코드에 박는다.** 토큰을 안 쓰면 다크 모드를 나중에 얹을 수 없다
 *
 *  치명은 exit 1 이다. CI 에 걸어 둔다.
 */
import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs';
import { join, relative, dirname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

// **fileURLToPath 를 쓴다.** URL.pathname 은 윈도우에서 앞에 / 를 붙이고
// 한글 경로를 percent-encode 해 파일을 못 찾는다
const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const UI = join(ROOT, 'src');
const SKIP = new Set(['core', 'node_modules', 'dist']);

function walk(dir, out = []) {
  if (!existsSync(dir)) return out;
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    if (statSync(p).isDirectory()) { if (!SKIP.has(e)) walk(p, out); }
    else if (/\.(jsx?|css)$/.test(e)) out.push(p);
  }
  return out;
}

const files = walk(UI);
const bad = [];   // 치명
const warn = [];  // 알림
const say = (list, file, line, what) =>
  list.push(`${relative(ROOT, file).replace(/\\/g, '/')}:${line}  ${what}`);

// ── ① 로직을 새로 짰나 ─────────────────────────────────────────────
// core 안의 값·판정이 화면 코드에 다시 나타나면 베낀 것이다
const LOGIC = [
  // **문맥까지 본다.** 맨숫자로 찾으면 CSS line-height 1.3 이 걸린다 (실제로 걸렸다)
  [/Math\.(?:max|min)\s*\(\s*(?:1\.3|2\.8)|\be\s*[-+]=\s*0\.[12]\b/,
   'SM-2 용이도 계산 — core/srs.js 의 schedule 을 부르라'],
  [/86400000|\b86_400_000\b/, '하루(ms) — core/srs.js 의 DAY 를 쓰라'],
  [/10\s*\*\s*60\s*\*\s*1000/, '10분 — core 의 AGAIN·MAX_MS 를 쓰라'],
  [/\.an\s*===|===\s*\w+\.an\b/, '정답 비교 — core/grade.js 의 gradeOne 을 부르라'],
  [/replace\(\s*\/<\[\^>\]/, '태그 벗기기 — core/text.js 의 plain 을 쓰라'],
  [/&lt;|&amp;lt;/, '엔티티를 손으로 다룬다 — core/text.js 의 plain 을 쓰라'],
  [/localStorage/, '저장소 직접 접근 — store/useStore.js 를 쓰라'],
  [/\bDate\.now\(\)/, '시각 직접 읽기 — core 는 시각을 주입받는다'],
];

// ── ② 화면에 붙인 것 ───────────────────────────────────────────────
// 허용은 둘뿐 — 모바일 하단 탭과 바텀시트(열려 있을 때만 존재한다)
const FIXED_OK = /tabbar|bottom-?sheet|sheet|scrim|overlay|backdrop|drawer/i;

/** 면제 — **어댑터는 경계를 넘는 것이 일이다.**
 *
 *  `useStore.js` 는 브라우저 저장소를 감싸는 **유일한** 자리다. 여기서
 *  localStorage 를 쓰지 않으면 아무도 못 쓴다. 대신 이 표에 적어 두어
 *  다른 파일이 슬쩍 끼는 것을 막는다. 새 이름을 여기 더할 때는 이유를 적는다.
 */
const EXEMPT = {
  'src/store/useStore.js': ['저장소 직접 접근'],   // 저장소 어댑터 그 자체
  'src/data/bank.js': ['시각 직접 읽기'],          // 없지만 앞으로 캐시 시각을 쓸 자리
  'src/hooks/clock.js': ['시각 직접 읽기'],        // 「지금」을 읽는 유일한 자리 — 화면들은 이것을 쓴다

  // 레이아웃 골격 파일 — 상주 머리말·하단 버튼 줄·하단 탭이 여기 있다.
  // 이 셋은 fixed 여야 하고, **화면 CSS 에는 fixed 가 없어야 한다.**
  // 그래서 파일 단위로만 열어 둔다.
  'src/mobile/mobile.css': ['position:fixed'],
  'src/desktop/desktop.css': ['position:fixed'],
};

/** 윈도우 경로 구분자를 / 로 — 이스케이프를 피해 split/join 으로 한다 */
const slash = p => p.split(sep).join('/');

/** 위쪽에 `prefers-reduced-motion` 블록이 열려 있나 */
function inReducedMotion(lines, i) {
  for (let k = i; k >= 0 && k > i - 12; k--) {
    if (/prefers-reduced-motion/.test(lines[k])) return true;
    if (/^\s*@media/.test(lines[k])) return false;
  }
  return false;
}

function exempt(file, why) {
  const rel = slash(relative(ROOT, file));
  return (EXEMPT[rel] || []).some(w => why.startsWith(w));
}

// ── ③ 토큰을 안 썼나 ───────────────────────────────────────────────
const HEX = /#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b/g;
const TOKEN_FILE = /tokens\.css$/;

for (const f of files) {
  const src = readFileSync(f, 'utf8');
  const lines = src.split(/\r?\n/);

  let inBlock = false;                 // 여러 줄 /* … */ 안인가
  lines.forEach((ln, i) => {
    const n = i + 1;
    let code = ln.replace(/\/\/.*$/, '').replace(/\/\*.*?\*\//g, '');

    // 블록 주석 안에는 스타일이 있을 수 없다. 주석에 적은 색 값·대비 근거를
    // 위반으로 세지 않도록 여기서 걸러낸다.
    if (inBlock) {
      const end = code.indexOf('*/');
      if (end < 0) return;
      code = code.slice(end + 2);
      inBlock = false;
    }
    const open = code.lastIndexOf('/*');
    if (open >= 0) {
      inBlock = true;
      code = code.slice(0, open);
    }
    if (!code.trim()) return;

    for (const [re, why] of LOGIC) {
      if (re.test(code) && !exempt(f, why)) say(bad, f, n, why);
    }

    if (/position\s*:\s*fixed/.test(code)) {
      // 같은 파일 안에 허용 이름이 있으면 넘긴다 — 선택자가 위에 있을 수 있다
      const near = lines.slice(Math.max(0, i - 6), i + 2).join(' ');
      if (!FIXED_OK.test(near) && !FIXED_OK.test(f) && !exempt(f, 'position:fixed')) {
        say(bad, f, n, 'position:fixed — 하단 탭과 바텀시트에만 허용된다');
      }
    }

    if (!TOKEN_FILE.test(f)) {
      const hits = code.match(HEX);
      if (hits) say(warn, f, n, `색을 박았다 (${hits.join(' ')}) — var(--…) 로`);
    }
    // `prefers-reduced-motion` 안의 !important 는 정당하다 —
    // 「움직이지 마라」는 사용자 설정은 컴포넌트 규칙을 이겨야 한다
    if (/!important/.test(code) && !inReducedMotion(lines, i)) {
      say(warn, f, n, '!important — 겹침을 격자로 풀라');
    }
    if (/<div[^>]+onClick/.test(code)) {
      say(bad, f, n, 'div 에 onClick — 선지·버튼은 <button> 이다 (키보드·스크린리더)');
    }
  });
}

// ── 없는 토큰을 쓰나 ───────────────────────────────────────────────
/** `var(--x)` 를 쓰는데 `--x` 를 아무도 정의하지 않았으면 **치명**이다.
 *
 *  var() 하나가 풀리지 않으면 **그 선언 전체가 무효**가 되고, 앞의 값으로
 *  돌아가지도 않는다(unset → 초기값). `--foot-h` 가 정의돼 있지 않던 동안
 *  `.view.has-foot` 의 padding-bottom 이 통째로 **0** 이 되어, 모바일에서
 *  5번 선지가 제출 줄에 28px 깔렸다(2026-08-28). 화면은 멀쩡해 보였다 —
 *  줄 하나가 사라지는 것이 아니라 값 하나가 조용히 0 이 되기 때문이다.
 *
 *  대비값이 있는 `var(--x, 12px)` 는 세지 않는다 — 그것은 없어도 성립한다.
 */
const DEF = /(--[-\w]+)[ ]*:/g;
const USE = /var\([ ]*(--[-\w]+)[ ]*\)/g;
const defined = new Set();
for (const f of files) {
  for (const m of readFileSync(f, 'utf8').matchAll(DEF)) defined.add(m[1]);
}
for (const f of files) {
  const lines = readFileSync(f, 'utf8').split(/\r?\n/);
  lines.forEach((ln, i) => {
    for (const m of ln.matchAll(USE)) {
      if (!defined.has(m[1])) {
        say(bad, f, i + 1,
            `${m[1]} 를 쓰는데 아무 데도 정의가 없다 — 그 선언 전체가 무효가 된다`);
      }
    }
  });
}

// ── 짝이 맞나 ─────────────────────────────────────────────────────
/** 발문을 그리는 화면은 **지문도 그려야 한다.**
 *
 *  네 화면(모바일·PC 의 문항 풀이와 응시)이 전부 `it.pg` 를 빠뜨리고 있었다.
 *  발문이 「윗글에서 추론할 수 있는」이라 부르는데 윗글이 없었다 — 지문이 붙은
 *  63문항이 못 푸는 상태였고, 응시 화면은 **시간까지 재면서** 그것을 냈다.
 *  화면마다 손으로 적으면 또 하나에서 빠진다. 그래서 여기서 센다.
 */
const PAIR = [
  [/className="stem"/, /<Passage[ />]/,
   '발문을 그리는데 <Passage /> 가 없다 — 지문이 붙은 문항을 못 푼다'],
];
for (const f of files) {
  const src = readFileSync(f, 'utf8');
  for (const [need, must, why] of PAIR) {
    if (need.test(src) && !must.test(src)) {
      bad.push(`${slash(relative(ROOT, f))}  ${why}`);
    }
  }
}

// ── 있어야 하는 것 ─────────────────────────────────────────────────
const MUST = [
  ['src/core/text.js', '순수 로직'],
  ['src/store/useStore.js', '기록 훅'],
  ['src/router/useHash.js', '해시 라우터'],
  ['src/data/bank.js', '문항 데이터'],
  ['src/Passage.jsx', '지문 부품 — 발문을 그리는 네 화면이 함께 쓴다'],
];
for (const [p, what] of MUST) {
  if (!existsSync(join(ROOT, p))) bad.push(`${p} 이 없다 — ${what}`);
}

// ── 보고 ───────────────────────────────────────────────────────────
const NL = '\n';
console.log(`검사한 파일 ${files.length}개 (src/core 제외)`);
if (bad.length) {
  console.log(NL + `치명 ${bad.length}건 — 고쳐야 한다`);
  for (const b of bad) console.log('  ' + b);
}
if (warn.length) {
  console.log(NL + `알림 ${warn.length}건`);
  for (const w of warn.slice(0, 25)) console.log('  ' + w);
  if (warn.length > 25) console.log(`  … ${warn.length - 25}건 더`);
}
if (!bad.length && !warn.length) console.log('지적 없음');
process.exit(bad.length ? 1 : 0);
