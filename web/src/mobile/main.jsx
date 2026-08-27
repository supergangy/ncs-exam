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
import App from './App.jsx';

createRoot(document.getElementById('root')).render(<App />);
