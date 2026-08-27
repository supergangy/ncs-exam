/** 설정 — 하루 목표 · 시험일 · 화면 · 기록.
 *
 *  **기록을 지우는 것은 되돌릴 수 없다.** 그래서 지우기 전에 무엇이 사라지는지
 *  개수로 보여 주고 한 번 더 묻는다. 복원도 같다 — 지금 기록과 파일의 기록을
 *  나란히 보여 준 뒤 덮는다.
 *
 *  백업 봉투의 `app` 값은 `'ncs-bank'` 다. 이름이 NCS PASS 로 바뀌었어도
 *  **바꾸지 않는다** — 예전 백업 파일을 복원할 때 대조하는 값이다.
 */
import { useRef, useState } from 'react';

import { nowMs } from '../../hooks/clock.js';
import { go } from '../../router/useHash.js';
import { useStore, useDerived } from '../../store/useStore.js';

/** 오늘 날짜를 `<input type="date">` 가 읽는 꼴로 */
const ymd = t => {
  const d = new Date(t);
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
};

export default function Settings() {
  const st = useStore();
  const counts = useDerived(s => ({
    att: Object.keys(s.d.att).length,
    exams: Object.keys(s.d.exams).length,
    mark: Object.keys(s.d.mark).length,
  }), []);

  const [ask, setAsk] = useState(false);       // 기록 지우기 확인
  const [msg, setMsg] = useState(null);
  const [pending, setPending] = useState(null); // 복원 대기 — 파일에서 읽은 봉투
  const file = useRef(null);

  const pref = st.pref;
  const theme = pref.theme || 'system';

  const setTheme = v => {
    st.setPref({ theme: v });
    const el = document.documentElement;
    if (v === 'system') delete el.dataset.theme;
    else el.dataset.theme = v;
  };

  const backup = () => {
    const at = nowMs();
    const env = st.exportMap(at);
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(env, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `ncspass-backup-${ymd(at)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setMsg('백업 파일을 내려받았습니다.');
  };

  const pick = async e => {
    const f = e.target.files?.[0];
    e.target.value = '';                       // 같은 파일을 다시 고를 수 있게
    if (!f) return;
    try {
      const env = JSON.parse(await f.text());
      if (env.app && env.app !== 'ncs-bank') throw new Error('이 앱의 백업이 아닙니다');
      if (!env.data?.att) throw new Error('기록이 들어 있지 않습니다');
      setPending({ env, name: f.name });
      setMsg(null);
    } catch (err) {
      setPending(null);
      setMsg('읽지 못했습니다 — ' + err.message);
    }
  };

  const restore = () => {
    st.importAll(pending.env);
    setPending(null);
    setMsg('복원했습니다. 되돌리려면 다시 백업 파일을 불러오세요.');
  };

  return (
    <div className="stack">
      <div className="card pad">
        <div className="h3">하루 목표</div>
        <div className="sm muted" style={{ marginTop: '.2rem' }}>
          홈의 목표 막대가 이 값을 봅니다.
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem',
                      marginTop: '.7rem' }}>
          <button className="btn btn-outline narrow" style={{ minWidth: '2.8rem' }}
                  onClick={() => st.setPref({ goal: Math.max(1, pref.goal - 5) })}
                  aria-label="5 줄이기">−5</button>
          <input className="field tick" type="number" min="1" max="200"
                 style={{ textAlign: 'center' }}
                 value={pref.goal}
                 onChange={e => st.setPref({ goal: Math.max(1, Math.min(200, +e.target.value || 1)) })}
                 aria-label="하루 목표 문항 수" />
          <button className="btn btn-outline narrow" style={{ minWidth: '2.8rem' }}
                  onClick={() => st.setPref({ goal: Math.min(200, pref.goal + 5) })}
                  aria-label="5 늘리기">+5</button>
        </div>
      </div>

      <div className="card pad">
        <div className="h3">시험일</div>
        <div className="sm muted" style={{ marginTop: '.2rem' }}>
          남은 날을 홈에 D-day 로 보여 줍니다.
        </div>
        <div style={{ display: 'flex', gap: '.5rem', marginTop: '.7rem' }}>
          <input className="field" type="date"
                 value={pref.examAt ? ymd(pref.examAt) : ''}
                 onChange={e => st.setPref({
                   examAt: e.target.value ? new Date(e.target.value + 'T00:00:00').getTime() : null,
                 })}
                 aria-label="시험일" />
          {pref.examAt && (
            <button className="btn btn-outline narrow"
                    onClick={() => st.setPref({ examAt: null })}>지우기</button>
          )}
        </div>
      </div>

      <div className="card pad">
        <div className="h3">화면</div>
        <div style={{ display: 'flex', gap: '.4rem', marginTop: '.7rem' }}>
          {[['system', '기기 설정'], ['light', '밝게'], ['dark', '어둡게']].map(([v, label]) => (
            <button key={v} className={'btn ' + (theme === v ? 'btn-tint' : 'btn-outline')}
                    style={{ flex: 1 }} onClick={() => setTheme(v)}
                    aria-pressed={theme === v}>
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="card pad">
        <div className="h3">기록</div>
        <div className="sm muted" style={{ marginTop: '.2rem' }}>
          문항 {counts.att}개 · 회차 {counts.exams}건 · 표시 {counts.mark}건
        </div>
        <div className="sm faint" style={{ marginTop: '.4rem' }}>
          기록은 이 기기에만 있습니다. 서버로 보내지 않으므로 기기를 바꿀 때는
          백업 파일을 옮겨야 합니다.
        </div>

        <div style={{ display: 'flex', gap: '.5rem', marginTop: '.8rem' }}>
          <button className="btn btn-outline" style={{ flex: 1 }} onClick={backup}>
            백업 내려받기
          </button>
          <button className="btn btn-outline" style={{ flex: 1 }}
                  onClick={() => file.current?.click()}>
            백업 불러오기
          </button>
        </div>
        <input ref={file} type="file" accept="application/json,.json"
               onChange={pick} style={{ display: 'none' }} />

        {msg && <div className="toast" style={{ marginTop: '.7rem' }} role="status">{msg}</div>}

        {pending && (
          <div className="card pad" style={{ marginTop: '.7rem', borderColor: 'var(--acc)' }}>
            <div className="h3">불러올까요?</div>
            <div className="sm muted" style={{ marginTop: '.3rem' }}>
              <b>{pending.name}</b><br />
              파일 — 문항 {pending.env.counts?.att ?? '?'}개 · 회차 {pending.env.counts?.exams ?? '?'}건<br />
              지금 — 문항 {counts.att}개 · 회차 {counts.exams}건
            </div>
            <div className="sm" style={{ marginTop: '.4rem', color: 'var(--warn)' }}>
              지금 기록을 덮습니다. 덮기 직전 것은 되돌릴 수 있게 따로 남겨 둡니다.
            </div>
            <div style={{ display: 'flex', gap: '.5rem', marginTop: '.8rem' }}>
              <button className="btn btn-outline" style={{ flex: 1 }}
                      onClick={() => setPending(null)}>그만두기</button>
              <button className="btn btn-primary" style={{ flex: 1 }} onClick={restore}>
                덮어쓰기
              </button>
            </div>
          </div>
        )}

        {!ask
          ? <button className="btn btn-ghost" style={{ width: '100%', marginTop: '.7rem',
                         color: 'var(--bad)' }}
                    onClick={() => setAsk(true)}>기록 전부 지우기</button>
          : (
            <div className="card pad" style={{ marginTop: '.7rem', borderColor: 'var(--bad-vivid)' }}>
              <div className="h3">정말 지울까요?</div>
              <div className="sm muted" style={{ marginTop: '.3rem' }}>
                문항 {counts.att}개의 기록과 회차 {counts.exams}건이 사라집니다.
                <b> 되돌릴 수 없습니다.</b> 먼저 백업을 내려받아 두세요.
              </div>
              <div style={{ display: 'flex', gap: '.5rem', marginTop: '.8rem' }}>
                <button className="btn btn-outline" style={{ flex: 1 }}
                        onClick={() => setAsk(false)}>그만두기</button>
                <button className="btn btn-danger" style={{ flex: 1 }}
                        onClick={() => { st.reset(); setAsk(false); setMsg('기록을 지웠습니다.'); }}>
                  지우기
                </button>
              </div>
            </div>
          )}
      </div>

      <button className="btn btn-ghost" style={{ width: '100%' }} onClick={() => go('/about')}>
        앱 정보
      </button>
    </div>
  );
}
