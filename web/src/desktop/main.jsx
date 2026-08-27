/** PC 판 진입점.
 *
 *  **여기만 폰트 파일을 받는다** (509KB). 모바일은 기기에 있는 것으로 간다 —
 *  안드로이드 Noto Sans KR · iOS Apple SD Gothic Neo. 아쉬운 것은 Windows 뿐이고
 *  그게 곧 이 판이다.
 */
import { createRoot } from 'react-dom/client';

import '../styles/fonts.css';
import '../styles/tokens.css';
import '../styles/components.css';
import App from './App.jsx';

createRoot(document.getElementById('root')).render(<App />);
