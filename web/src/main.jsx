/** 진입점.
 *
 *  `App.jsx` 는 **Build 결과로 갈아치울 자리**다. 지금 들어 있는 것은
 *  배선이 맞는지 보여 주는 얇은 화면이다 — 문항이 실제로 읽히고,
 *  라우터가 갈리고, 기록이 남는지. 껍데기가 오면 이 안쪽만 바뀐다.
 */
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './styles/tokens.css';

createRoot(document.getElementById('root')).render(<App />);
