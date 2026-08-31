/** 빌드 산출물에서 `sw.js` 를 만든다.
 *
 *  ## 왜 만들어 내는가
 *
 *  Vite 는 `a/mobile-MW_vo6Ym.js` 처럼 **해시가 붙은 이름**을 낸다. 캐시 목록을
 *  손으로 적어 두면 빌드마다 어긋나고, 어긋난 것은 오프라인으로 들어가 봐야 안다.
 *
 *  **버전도 손으로 올리지 않는다.** 파일 목록과 크기에서 해시를 낸다 —
 *  내용이 바뀌면 버전이 저절로 바뀌고, 안 바뀌면 그대로다. 배포본에서
 *  「파일은 새로 올렸는데 버전이 같아 옛 캐시가 계속 나가는」 일이 실제로 있었다
 *  (`docs/BANK.md` 6절).
 *
 *  ## 무엇을 미리 담고 무엇을 나중에 담나
 *
 *  껍데기와 문항은 install 에서 담는다 — 첫 실행 뒤 바로 오프라인이 되어야 한다.
 *  **폰트(509KB)는 담지 않는다.** PC 판만 쓰는 것이라 모바일에서 미리 받으면 낭비다.
 *  대신 fetch 에서 받아 오는 대로 담는다(runtime cache) — PC 로 한 번 열면 캐시된다.
 *
 *  ## HTML 은 그물이 먼저다
 *
 *  묶음 이름에 해시가 붙으므로 **배포마다 이름이 바뀐다.** HTML 을 캐시에서 먼저
 *  주면 옛 HTML 이 사라진 이름을 불러 **화면이 하얗게 남는다** — 2026-08-27
 *  배포에서 실제로 그랬다(옛 워커가 캐시의 옛 index.html 을 내주고, 그 안의
 *  묶음 넷이 404). 이름이 안 바뀌는 것만 캐시가 먼저다.
 *
 *  배포 쪽 짝은 `tools/deploy_next.py` 다 — 직전 배포의 묶음을 한 세대 남겨,
 *  이미 옛 껍데기를 물고 있는 브라우저가 한 번 더 뜨고 그때 새 워커가 자리 잡게 한다.
 *
 *      node tool/make_sw.mjs            # dist/sw.js 를 만든다
 */
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('..', import.meta.url));
const DIST = join(ROOT, 'dist');

/** install 에서 담지 않는 것 — 나중에 요청될 때 담긴다 */
const LAZY = /^(fonts\/|.*\.map$)/;
/**
 *  아예 담지 않는 것.
 *
 *  `exams/` 는 회차 PDF 12MB 다. **내려받으면 기기에 저장되는 파일**이라
 *  캐시에 또 두면 같은 것을 두 벌 갖는 셈이다. 목록에서 빼면 판 도장(VERSION)
 *  에도 안 들어가므로, PDF 를 다시 구웠다고 캐시 전체가 갈리지도 않는다.
 *  워커의 fetch 도 이 경로는 그물로 그냥 보낸다(아래 `isDownload`).
 */
const SKIP = /^(sw\.js$|fonts\/OFL-|exams\/)/;

function walk(dir) {
  const out = [];
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) out.push(...walk(p));
    else out.push(p);
  }
  return out;
}

const files = walk(DIST)
  .map(p => ({ rel: relative(DIST, p).split(sep).join('/'), size: statSync(p).size }))
  .filter(f => !SKIP.test(f.rel))
  .sort((a, b) => a.rel.localeCompare(b.rel));

const shell = files.filter(f => !LAZY.test(f.rel)).map(f => './' + f.rel);

// 버전 — 목록과 크기에서 낸다. 내용이 바뀌면 저절로 바뀐다
const stamp = createHash('sha256')
  .update(files.map(f => `${f.rel}:${f.size}`).join('\n'))
  .update('==make_sw==')
  // `sw.js` 는 SKIP 이라 위 목록에 없다. 목록만으로 판을 내면 **워커의 전략을
  // 고쳐도 판이 그대로**여서 옛 캐시가 지워지지 않는다 — 껍데기를 캐시에서
  // 먼저 주던 그 캐시가 그대로 남는다. 전략이 바뀌면 이 파일이 바뀌므로 섞는다.
  .update(readFileSync(fileURLToPath(import.meta.url)))
  .digest('hex').slice(0, 10);
const VERSION = `ncspass-${stamp}`;

const src = `/* 서비스 워커 — **만들어진 파일이다. 손으로 고치지 마라.**
 *
 *   생성: node tool/make_sw.mjs   (빌드 뒤에 돌린다)
 *   버전: 파일 목록과 크기의 해시. 내용이 바뀌면 저절로 바뀐다.
 *
 * 껍데기와 문항은 install 에서 담고, 폰트는 요청될 때 담는다 —
 * 폰트 509KB 는 PC 판만 쓰므로 모바일에서 미리 받을 이유가 없다.
 */
const VERSION = '${VERSION}';

/** 첫 실행에 담을 것 — ${shell.length}개 */
const SHELL = ${JSON.stringify(shell, null, 2).replace(/\n/g, '\n')};

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(VERSION)
      // 하나가 실패해도 설치를 깨지 않는다 — 나머지라도 담아 둔다
      .then(c => Promise.all(SHELL.map(u => c.add(u).catch(() => {}))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

/** 껍데기 문서인가 — 이름이 안 바뀌는 주소라 캐시가 오래 남으면 위험한 것 */
const isDoc = (req, url) => req.mode === 'navigate'
                         || url.pathname.endsWith('/')
                         || url.pathname.endsWith('.html');

/** 내려받는 파일인가 — 회차 PDF. 기기에 저장되므로 캐시에 또 두지 않는다 */
const isDownload = url => url.pathname.includes('/exams/');

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== location.origin) return;      // 남의 집 것은 건드리지 않는다

  // 회차 PDF 는 워커가 손대지 않는다 — 12MB 를 캐시에 겹쳐 두지 않으려는 것이다.
  // 그물이 없으면 내려받기가 실패하지만, 그것은 정직한 실패다.
  if (isDownload(url)) return;

  e.respondWith((async () => {
    const cache = await caches.open(VERSION);

    // ── HTML — 그물 먼저, 끊기면 캐시 ───────────────────────
    //    캐시를 먼저 주면 배포 뒤에도 옛 껍데기가 계속 나가고, 그 안의 묶음
    //    이름은 이미 사라져 **하얀 화면**이 된다. 오프라인일 때만 캐시로 돈다.
    if (isDoc(req, url)) {
      try {
        // fetch(req) 로는 모자란다 — 그것은 **브라우저 HTTP 캐시**를 먼저 본다.
        //   GitHub Pages 가 HTML 에 max-age=600 을 붙이므로, 워커가 그물로 나가도
        //   10분 동안 옛 껍데기가 되돌아온다(실측). no-cache 로 매번 서버에
        //   물어본다 — 안 바뀌었으면 304 라 값이 거의 없다. (backtick 금지: 이 글은
        //   템플릿 문자열 안에 들어간다)
        const res = await fetch(url.href, { cache: 'no-cache', credentials: 'same-origin' });
        if (res.ok && res.type === 'basic') cache.put(req, res.clone()).catch(() => {});
        return res;
      } catch (err) {
        const hit = await cache.match(req, { ignoreSearch: true })
                 || await cache.match(url.pathname.includes('/m/') ? './m/index.html'
                                                                   : './index.html');
        if (hit) return hit;                        // 해시 라우터라 껍데기 하나로 된다
        throw err;
      }
    }

    // ── 그 밖 — 캐시 먼저 ───────────────────────────────────
    //    묶음·폰트·아이콘·문항은 이름이나 캐시 판이 바뀌어야 바뀐다
    const hit = await cache.match(req, { ignoreSearch: true });
    if (hit) return hit;

    const res = await fetch(req);
    // 받아 온 것을 담아 둔다 — 폰트가 여기서 캐시된다
    if (res.ok && res.type === 'basic') cache.put(req, res.clone()).catch(() => {});
    return res;
  })());
});
`;

// 만든 것이 문법에 맞는지 여기서 본다.
//   위 `src` 는 템플릿 문자열이다 — 주석에 backtick 이나 ${ } 를 넣으면 문자열이
//   끊기거나 조용히 값이 끼워진다. 배포본에서 알아채면 늦다.
try {
  new Function(src);
} catch (e) {
  console.error('  [중단] 만든 sw.js 가 파싱되지 않는다 —', e.message);
  console.error('         주석에 backtick 이나 ${ } 를 넣지 않았는지 보라');
  process.exit(1);
}

writeFileSync(join(DIST, 'sw.js'), src);

const shellBytes = files.filter(f => !LAZY.test(f.rel)).reduce((s, f) => s + f.size, 0);
const lazyBytes = files.filter(f => LAZY.test(f.rel)).reduce((s, f) => s + f.size, 0);
console.log(`  dist/sw.js  ${VERSION}`);
console.log(`    install 에 담을 것  ${shell.length}개 · ${(shellBytes / 1024).toFixed(1)} KB`);
console.log(`    나중에 담을 것      ${files.length - shell.length}개 · ${(lazyBytes / 1024).toFixed(1)} KB (폰트)`);
