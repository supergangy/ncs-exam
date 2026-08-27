/** 모바일 판 진입점.
 *
 *  **폰트 파일을 받지 않는다** (`styles/fonts.css` 를 넣지 않는다). 안드로이드에는
 *  Noto Sans KR, iOS 에는 Apple SD Gothic Neo 가 이미 있다 — 509KB 를 회선으로
 *  받을 이유가 없다. 스택은 `tokens.css` 의 `--font` 가 정한다.
 */
import { createRoot } from 'react-dom/client';

import '../styles/tokens.css';
import '../styles/components.css';
import './mobile.css';
import { registerSW } from '../sw-register.js';
import App from './App.jsx';

createRoot(document.getElementById('root')).render(<App />);

// 오프라인 — 껍데기와 문항을 캐시에 담는다. 캐시 전략은 `dist/sw.js` 가 갖는다
registerSW('../sw.js');   // 배포 루트에 하나 — 두 판을 함께 덮는다
