import { fileURLToPath } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

/** 진입점이 둘이다 — PC 는 `/`, 모바일은 `/m/`.
 *
 *  화면·부품·화면상태는 두 벌이고, 아래 넷만 한 벌로 공유한다.
 *
 *    src/core/     순수 로직 — SM-2 · 채점 · 진도 · 검색 · 본문추출 · 저장
 *                  화면이 없고 테스트 32건으로 고정되어 있다
 *    src/data/     문항 래퍼 — 읽기만 한다
 *    src/store/    기록 훅 — core/store 를 React 에 잇기만 한다
 *    src/router/   해시 주소 — **양쪽이 같은 주소를 써야** 북마크가 산다
 *    src/styles/   토큰·부품 — 색과 부품 모양이 갈리면 한 앱으로 보이지 않는다
 *
 *  `new URL().pathname` 을 쓰지 마라. 윈도우에서 한글 경로가 퍼센트 인코딩되어
 *  `%EC%82%AC...` 가 그대로 경로에 박힌다. `fileURLToPath` 로 받는다.
 */
const here = p => fileURLToPath(new URL(p, import.meta.url));

export default defineConfig({
  // GitHub Pages 는 저장소 이름 아래에 얹힌다 — 절대 경로로 두면 자원을 못 찾는다
  base: './',
  plugins: [react()],
  build: {
    outDir: 'dist',
    assetsDir: 'a',
    sourcemap: false,
    rollupOptions: {
      input: {
        desktop: here('index.html'),
        mobile: here('m/index.html'),
      },
    },
  },
  server: { port: 5180, open: false },
});
