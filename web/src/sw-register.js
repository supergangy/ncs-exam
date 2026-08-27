/** 서비스 워커 등록 — 오프라인 동작의 배선.
 *
 *  **캐시 전략은 `sw.js` 가 갖는다.** 여기서 하는 일은 등록과, 새 판이 올라왔을 때
 *  알려 주는 것뿐이다.
 *
 *  `file:` 에서는 등록하지 않는다 — 로컬 파일로 열어 볼 때 콘솔이 오류로 덮인다.
 *  등록 실패를 조용히 삼키지 않고 콘솔에 남긴다. 배포본에서 오프라인이 안 될 때
 *  이유를 알 수 있어야 한다 (예전 판은 `.catch(() => {})` 로 삼켰다).
 */

/** `sw.js` 는 배포 루트에 **하나만** 둔다. 모바일 판은 `/m/` 아래에 있으므로
 *  한 칸 위를 가리킨다 — 그러면 scope 가 배포 루트가 되어 두 판을 함께 덮는다.
 *  (워커가 있는 자리보다 상위 scope 는 못 잡는다. 아래는 잡힌다.)
 *
 *  @param url      워커 파일 — PC `'./sw.js'` · 모바일 `'../sw.js'`
 *  @param onUpdate 새 판이 준비되면 부른다 — 화면이 「새로 고치세요」를 띄울 수 있다
 */
export function registerSW(url = './sw.js', onUpdate) {
  if (!('serviceWorker' in navigator)) return;
  if (location.protocol === 'file:') return;

  window.addEventListener('load', () => {
    navigator.serviceWorker.register(url)
      .then(reg => {
        reg.addEventListener('updatefound', () => {
          const sw = reg.installing;
          if (!sw) return;
          sw.addEventListener('statechange', () => {
            // 이미 돌던 워커가 있는데 새 것이 설치됐다 = 갱신이다
            if (sw.state === 'installed' && navigator.serviceWorker.controller) {
              onUpdate?.(reg);
            }
          });
        });
      })
      .catch(e => console.warn('서비스 워커를 등록하지 못했다 — 오프라인이 안 된다', e));
  });
}
