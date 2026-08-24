import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// GitHub Pages 는 저장소 이름 아래에 얹힌다 — 절대 경로로 두면 자원을 못 찾는다
export default defineConfig({
  base: './',
  plugins: [react()],
  build: { outDir: 'dist', assetsDir: 'a', sourcemap: false },
  server: { port: 5180, open: false },
});
