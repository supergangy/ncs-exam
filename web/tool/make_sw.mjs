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
 *      node tool/make_sw.mjs            # dist/sw.js 를 만든다
 */
import { createHash } from 'node:crypto';
import { readdirSync, statSync, writeFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('..', import.meta.url));
const DIST = join(ROOT, 'dist');

/** install 에서 담지 않는 것 — 나중에 요청될 때 담긴다 */
const LAZY = /^(fonts\/|.*\.map$)/;
/** 아예 담지 않는 것 */
const SKIP = /^(sw\.js$|fonts\/OFL-)/;

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

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== location.origin) return;      // 남의 집 것은 건드리지 않는다

  e.respondWith((async () => {
    const cache = await caches.open(VERSION);
    const hit = await cache.match(req, { ignoreSearch: true });
    if (hit) return hit;

    try {
      const res = await fetch(req);
      // 받아 온 것을 담아 둔다 — 폰트가 여기서 캐시된다
      if (res.ok && res.type === 'basic') cache.put(req, res.clone()).catch(() => {});
      return res;
    } catch (err) {
      // 오프라인이고 캐시에도 없다. 화면 이동이면 껍데기를 준다 (해시 라우터라 그것으로 된다)
      if (req.mode === 'navigate') {
        const shellHit = await cache.match(url.pathname.includes('/m/') ? './m/index.html'
                                                                       : './index.html');
        if (shellHit) return shellHit;
      }
      throw err;
    }
  })());
});
`;

writeFileSync(join(DIST, 'sw.js'), src);

const shellBytes = files.filter(f => !LAZY.test(f.rel)).reduce((s, f) => s + f.size, 0);
const lazyBytes = files.filter(f => LAZY.test(f.rel)).reduce((s, f) => s + f.size, 0);
console.log(`  dist/sw.js  ${VERSION}`);
console.log(`    install 에 담을 것  ${shell.length}개 · ${(shellBytes / 1024).toFixed(1)} KB`);
console.log(`    나중에 담을 것      ${files.length - shell.length}개 · ${(lazyBytes / 1024).toFixed(1)} KB (폰트)`);
