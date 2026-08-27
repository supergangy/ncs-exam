/** 화면을 찍는다 — **DevTools 규약(CDP)으로.** 받는 것은 없다(Node 내장 WebSocket).
 *
 *  ## 왜 `--window-size` 로는 안 되나
 *
 *  Chrome headless 는 **창을 500px 아래로 만들지 않는다.** `--window-size=375,812`
 *  를 줘도 뷰포트는 500 이고, `--screenshot` 만 375 로 자른다. 그래서 폰 화면을
 *  찍으면 **오른쪽 125px 이 잘린 채** 저장된다 — 탭 넷 중 하나가 사라지고 배지가
 *  사라졌다. 앱은 멀쩡한데 사진만 거짓말을 했다(2026-08-27 실측: client 500).
 *
 *  `--force-device-scale-factor` 로도 못 피한다. `--window-size` 는 CSS 픽셀이라
 *  배율을 올리면 결과 이미지만 커지고 레이아웃 폭은 그대로다.
 *
 *  `Emulation.setDeviceMetricsOverride` 는 **레이아웃 폭 자체를** 정한다. 덤으로
 *  `captureBeyondViewport` 로 **화면 끝까지** 찍을 수 있다 — 812 로 잘린 조각이
 *  아니라 페이지 전체를 본다.
 *
 *      node brand/shot.mjs spec.json
 *
 *  spec.json — { "shots": [ { out, url, w, h, scale, mobile, settle } ] }
 *  크롬 하나·탭 하나로 전부 찍는다. 화면마다 띄우면 20장에 1분이 넘는다.
 */
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const CHROME = process.env.CHROME
  || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PORT = Number(process.env.CDP_PORT || 9333);

const spec = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const shots = spec.shots || [];
if (!shots.length) { console.error('  찍을 것이 없다'); process.exit(1); }

const sleep = ms => new Promise(r => setTimeout(r, ms));

/** 크롬이 대답할 때까지 기다린다 — 뜨자마자 붙으면 거절한다 */
async function wait(ms = 20000) {
  const until = Date.now() + ms;
  while (Date.now() < until) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      if (r.ok) return await r.json();
    } catch { /* 아직 안 떴다 */ }
    await sleep(150);
  }
  throw new Error(`크롬이 ${ms}ms 안에 안 떴다`);
}

const dir = mkdtempSync(join(tmpdir(), 'ncspass-shot-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--disable-gpu', '--hide-scrollbars', '--mute-audio',
  '--no-first-run', '--no-default-browser-check',
  '--user-data-dir=' + dir,
  '--remote-debugging-port=' + PORT,
  'about:blank',
], { stdio: 'ignore' });

let ws = null;
let id = 0;
const waiting = new Map();
const once = new Map();

/** 명령 하나. 답이 올 때까지 기다린다 */
const send = (method, params = {}) => new Promise((res, rej) => {
  const n = ++id;
  waiting.set(n, { res, rej });
  ws.send(JSON.stringify({ id: n, method, params }));
});

/** 사건 하나를 기다린다. 안 오면 `ms` 뒤에 그냥 넘어간다 — 해시만 바뀌면 load 가 안 온다 */
const event = (name, ms) => new Promise(res => {
  const t = setTimeout(() => { once.delete(name); res(false); }, ms);
  once.set(name, () => { clearTimeout(t); once.delete(name); res(true); });
});

try {
  await wait();
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
  const page = list.find(t => t.type === 'page');
  if (!page) throw new Error('탭을 못 찾았다');

  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  ws.onmessage = e => {
    const m = JSON.parse(e.data);
    if (m.id && waiting.has(m.id)) {
      const { res, rej } = waiting.get(m.id);
      waiting.delete(m.id);
      m.error ? rej(new Error(m.error.message)) : res(m.result);
    } else if (m.method && once.has(m.method)) {
      once.get(m.method)();
    }
  };

  await send('Page.enable');

  for (const s of shots) {
    await send('Emulation.setDeviceMetricsOverride', {
      width: s.w, height: s.h,
      deviceScaleFactor: s.scale ?? 2,
      mobile: !!s.mobile,
    });
    // 해시만 바뀌면 load 가 안 오므로 빈 곳을 한 번 들른다
    await send('Page.navigate', { url: 'about:blank' });
    await sleep(40);
    await send('Page.navigate', { url: s.url });
    await event('Page.loadEventFired', 15000);
    await sleep(s.settle ?? 900);          // 글꼴·문항(1.9MB)이 앉을 틈

    const { data } = await send('Page.captureScreenshot', {
      format: 'png', captureBeyondViewport: true, fromSurface: true,
    });
    writeFileSync(s.out, Buffer.from(data, 'base64'));
    console.log(`  ${s.out}`);
  }
} catch (e) {
  console.error('  [실패]', e.message);
  process.exitCode = 1;
} finally {
  // 순서가 중요하다 — 닫는 명령도 이 소켓으로 나간다
  try { await send('Browser.close'); } catch { /* 이미 가는 중이다 */ }
  try { ws?.close(); } catch { /* 이미 닫혔다 */ }
  chrome.kill();
  await sleep(200);
  rmSync(dir, { recursive: true, force: true });
}
