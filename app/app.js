/* NCS 기출은행 — 완전 내장형.
 *
 * 문항은 `data/bank.json` 하나에 다 들어 있다. 서버에 물어보지 않는다.
 * 사용자 기록(푼 것·틀린 것·복습 일정)은 이 기기의 localStorage 에만 남는다.
 * 둘을 섞지 않는다 — 콘텐츠를 새로 배포해도 기록이 날아가지 않는다.
 */
'use strict';

// ─────────────────────────────────────────────────────── 저장소
const KEY = 'ncsbank.v1';

const Store = {
  d: { att: {}, srs: {}, admin: false, seen: 0 },

  load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) Object.assign(this.d, JSON.parse(raw));
    } catch (e) { console.warn('기록을 읽지 못했다', e); }
  },
  save() {
    try { localStorage.setItem(KEY, JSON.stringify(this.d)); }
    catch (e) { console.warn('기록을 쓰지 못했다', e); }
  },

  /** 한 문항의 마지막 시도. 없으면 null */
  last(id) { const a = this.d.att[id]; return a ? a[a.length - 1] : null; },
  tried(id) { return !!this.d.att[id]; },
  /** 마지막 시도가 오답인 것만 오답노트에 남긴다 — 다시 맞히면 빠진다 */
  isWrong(id) { const l = this.last(id); return !!l && !l.k; },

  record(id, chosen, ok, ms) {
    (this.d.att[id] ||= []).push({ c: chosen, k: ok ? 1 : 0, t: Date.now(), m: ms | 0 });
    this.schedule(id, ok);
    this.save();
  },

  /** SM-2 를 줄인 것. 틀리면 처음으로 돌아가고, 맞히면 간격이 벌어진다. */
  schedule(id, ok) {
    const s = this.d.srs[id] || { e: 2.5, i: 0, due: 0 };
    if (!ok) {
      s.e = Math.max(1.3, s.e - 0.2);
      s.i = 0;
      s.due = Date.now() + 10 * 60 * 1000;      // 10분 뒤 다시
    } else {
      s.e = Math.min(2.8, s.e + 0.1);
      s.i = s.i === 0 ? 1 : s.i === 1 ? 3 : Math.round(s.i * s.e);
      s.due = Date.now() + s.i * 86400000;
    }
    this.d.srs[id] = s;
  },

  dueIds(all) {
    const now = Date.now();
    return all.filter(i => { const s = this.d.srs[i.id]; return s && s.due <= now; })
              .map(i => i.id);
  },

  reset() { this.d = { att: {}, srs: {}, admin: false, seen: 0 }; this.save(); },
};

// ─────────────────────────────────────────────────────── 데이터
const DB = {
  raw: null, items: [], byId: new Map(), admin: null,

  async load() {
    const r = await fetch('data/bank.json', { cache: 'no-cache' });
    if (!r.ok) throw new Error(`bank.json 을 불러오지 못했다 (${r.status})`);
    this.raw = await r.json();
    this.items = this.raw.items;
    this.items.forEach(i => this.byId.set(i.id, i));
  },

  /** 관리자 자료는 **관리자 모드일 때만** 받는다. 평소에는 내려받지도 않는다. */
  async loadAdmin() {
    if (this.admin) return this.admin;
    const r = await fetch('data/admin.json', { cache: 'no-cache' });
    if (!r.ok) throw new Error('admin.json 없음');
    this.admin = (await r.json()).items;
    return this.admin;
  },

  track(id) { return this.raw.tracks.find(t => t.id === id); },
  subjects(tr) { return this.raw.subjects.filter(s => s.tr === tr); },
  types(tr, sj) { return this.raw.types.filter(t => t.tr === tr && t.sj === sj); },
  passage(n) { return this.raw.passages[n]; },
  kwName(n) { return this.raw.keywords[n] ? this.raw.keywords[n].t : ''; },

  filter(f) {
    return this.items.filter(i =>
      (!f.tr || i.tr === f.tr) &&
      (!f.sj || i.sj === f.sj) &&
      (!f.ty || i.ty === f.ty) &&
      (f.kw == null || i.kw.includes(f.kw)));
  },
};

// ─────────────────────────────────────────────────────── 도우미
const $ = s => document.querySelector(s);
const el = (t, c, h) => { const e = document.createElement(t);
  if (c) e.className = c; if (h != null) e.innerHTML = h; return e; };
const esc = s => String(s).replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const CIRC = ['①', '②', '③', '④', '⑤', '⑥', '⑦'];
const pct = (a, b) => b ? Math.round(a / b * 100) : 0;

/** 통과율·진도 — 목록마다 쓴다 */
function progress(items) {
  let done = 0, ok = 0;
  for (const i of items) {
    const l = Store.last(i.id);
    if (l) { done++; if (l.k) ok++; }
  }
  return { n: items.length, done, ok, rate: pct(ok, done) };
}

function bar(p) {
  const b = el('div', 'bar');
  const i = el('i');
  i.style.width = pct(p.done, p.n) + '%';
  if (p.done === p.n && p.n) i.classList.add('good');
  b.append(i);
  return b;
}

function progText(p) {
  if (!p.done) return `${p.n}문항`;
  return `${p.done}/${p.n} · 정답률 ${p.rate}%`;
}

// ─────────────────────────────────────────────────────── 라우터
const routes = [];
const route = (re, fn) => routes.push([re, fn]);

function go(hash) { location.hash = hash; }

function render() {
  const path = (location.hash || '#/').slice(1);
  for (const [re, fn] of routes) {
    const m = re.exec(path);
    if (m) {
      $('#view').scrollTop = 0;
      window.scrollTo(0, 0);
      $('#view').className = 'view';
      $('#topRight').innerHTML = '';
      document.querySelectorAll('.tabs a').forEach(a =>
        a.classList.toggle('on', a.dataset.tab === path.split('?')[0]));
      $('#back').hidden = path === '/';
      fn(...m.slice(1).map(x => x && decodeURIComponent(x)));
      updateBadges();
      return;
    }
  }
  go('/');
}

function setTitle(t) { $('#title').textContent = t; }
function paint(node) { const v = $('#view'); v.innerHTML = ''; v.append(node); }

function updateBadges() {
  const w = DB.items.filter(i => Store.isWrong(i.id)).length;
  const d = Store.dueIds(DB.items).length;
  for (const [sel, n] of [['#wrongBadge', w], ['#dueBadge', d]]) {
    const b = $(sel); b.textContent = n > 99 ? '99+' : n; b.hidden = !n;
  }
}

// ─────────────────────────────────────────────────────── 화면: 홈
route(/^\/$/, () => {
  setTitle('기출은행');
  const f = document.createDocumentFragment();

  const due = Store.dueIds(DB.items).length;
  const wrong = DB.items.filter(i => Store.isWrong(i.id)).length;
  const all = progress(DB.items);

  if (due || wrong) {
    const a = el('a', 'resume');
    a.href = due ? '#/review' : '#/wrong';
    a.innerHTML = due
      ? `<div class="rt">복습할 문제 ${due}개</div>
         <div class="rs">간격을 두고 다시 풀면 오래 남습니다</div>`
      : `<div class="rt">오답 ${wrong}개가 남아 있습니다</div>
         <div class="rs">틀린 것부터 다시 풀어 보세요</div>`;
    f.append(a);
  }

  f.append(el('h2', 'sec', '직렬'));
  const list = el('div', 'list');
  for (const t of DB.raw.tracks) {
    const items = DB.filter({ tr: t.id });
    const p = progress(items);
    const a = el('a', 'hero');
    a.href = `#/t/${t.id}`;
    a.innerHTML =
      `<div class="hero-t">${esc(t.name)}</div>
       <div class="hero-s">${esc(t.sub)} · ${DB.subjects(t.id).length}과목</div>
       <div class="hero-n">전체 <b>${p.n}</b>문항 · 푼 것 <b>${p.done}</b>` +
      (p.done ? ` · 정답률 <b>${p.rate}%</b>` : '') + `</div>`;
    a.append(bar(p));
    list.append(a);
  }
  f.append(list);

  f.append(el('h2', 'sec', '무작위로'));
  const q = el('div', 'list');
  const mk = (t, s, href) => {
    const a = el('a', 'row');
    a.href = href;
    a.innerHTML = `<div class="row-main"><div class="row-t">${t}</div>
                   <div class="row-s">${s}</div></div><div class="row-go">›</div>`;
    return a;
  };
  q.append(mk('안 푼 문제 이어서', `아직 ${all.n - all.done}문항 남았습니다`,
              '#/q?mode=new'));
  q.append(mk('전체에서 무작위', `${all.n}문항 가운데 섞어서`, '#/q?mode=all'));
  f.append(q);

  const st = el('h2', 'sec', '');
  st.style.marginBottom = '.4rem';
  f.append(st);
  const set = el('a', 'row');
  set.href = '#/settings';
  set.innerHTML = `<div class="row-main"><div class="row-t">설정</div>
    <div class="row-s">기록 관리 · 관리자 모드</div></div><div class="row-go">›</div>`;
  f.append(set);

  paint(f);
});

// ─────────────────────────────────────────────────────── 화면: 과목
route(/^\/t\/([^/]+)$/, (tr) => {
  const t = DB.track(tr);
  if (!t) return go('/');
  setTitle(t.name);

  const f = document.createDocumentFragment();
  const all = DB.filter({ tr });
  const p = progress(all);

  const top = el('a', 'resume');
  top.href = `#/q?tr=${tr}&mode=new`;
  top.innerHTML = `<div class="rt">${esc(t.name)} 이어서 풀기</div>
    <div class="rs">안 푼 문제 ${p.n - p.done}개 · 전체 ${p.n}문항</div>`;
  f.append(top);

  f.append(el('h2', 'sec', '과목'));
  const list = el('div', 'list');
  for (const s of DB.subjects(tr)) {
    const sp = progress(DB.filter({ tr, sj: s.n }));
    const a = el('a', 'row');
    a.href = `#/s/${tr}/${encodeURIComponent(s.n)}`;
    a.innerHTML =
      `<div class="row-main"><div class="row-t">${esc(s.n)}</div>
        <div class="row-s">${progText(sp)} · 유형 ${DB.types(tr, s.n).length}종</div>
       </div><div class="row-go">›</div>`;
    a.querySelector('.row-main').append(bar(sp));
    list.append(a);
  }
  f.append(list);
  paint(f);
});

// ─────────────────────────────────────────────────────── 화면: 유형
route(/^\/s\/([^/]+)\/([^/]+)$/, (tr, sj) => {
  setTitle(sj);
  const f = document.createDocumentFragment();
  const all = DB.filter({ tr, sj });
  const p = progress(all);

  const top = el('a', 'resume');
  top.href = `#/q?tr=${tr}&sj=${encodeURIComponent(sj)}&mode=new`;
  top.innerHTML = `<div class="rt">${esc(sj)} 전체 풀기</div>
    <div class="rs">${progText(p)}</div>`;
  f.append(top);

  f.append(el('h2', 'sec', `유형 ${DB.types(tr, sj).length}종`));
  const list = el('div', 'list');
  for (const t of DB.types(tr, sj)) {
    const tp = progress(DB.filter({ tr, sj, ty: t.n }));
    const a = el('a', 'row');
    a.href = `#/q?tr=${tr}&sj=${encodeURIComponent(sj)}&ty=${encodeURIComponent(t.n)}`;
    a.innerHTML =
      `<div class="row-main"><div class="row-t">${esc(t.n)}</div>
        <div class="row-s">${progText(tp)}</div></div>
       <div class="row-go">›</div>`;
    a.querySelector('.row-main').append(bar(tp));
    list.append(a);
  }
  f.append(list);
  paint(f);
});

// ─────────────────────────────────────────────────────── 화면: 키워드
route(/^\/kw$/, () => {
  setTitle('키워드');
  const f = document.createDocumentFragment();
  f.append(el('p', 'hint',
    '문항을 가로질러 묶는 용어입니다. 과목이 달라도 같은 개념이면 함께 나옵니다.'));

  const groups = new Map();
  DB.raw.keywords.forEach((k, idx) => {
    const its = DB.items.filter(i => i.kw.includes(idx));
    const sj = its.length ? its[0].sj : '기타';
    (groups.get(sj) || groups.set(sj, []).get(sj)).push({ ...k, idx });
  });

  for (const [sj, ks] of [...groups].sort((a, b) => b[1].length - a[1].length)) {
    f.append(el('h2', 'sec', `${sj} · ${ks.length}개`));
    const c = el('div', 'chips');
    for (const k of ks.sort((a, b) => b.n - a.n || a.t.localeCompare(b.t, 'ko'))) {
      const a = el('a', 'chip');
      a.href = `#/q?kw=${k.idx}`;
      a.innerHTML = `${esc(k.t)} <b>${k.n}</b>`;
      c.append(a);
    }
    f.append(c);
  }
  paint(f);
});

// ─────────────────────────────────────────────────────── 화면: 오답노트
route(/^\/wrong$/, () => {
  setTitle('오답노트');
  const wrong = DB.items.filter(i => Store.isWrong(i.id));
  const f = document.createDocumentFragment();

  if (!wrong.length) {
    f.append(el('div', 'empty',
      '<b>오답이 없습니다</b>틀린 문제가 여기 모입니다.<br>다시 풀어 맞히면 목록에서 빠집니다.'));
    return paint(f);
  }

  const a = el('a', 'resume');
  a.href = '#/q?mode=wrong';
  a.innerHTML = `<div class="rt">오답 ${wrong.length}개 다시 풀기</div>
    <div class="rs">맞히면 목록에서 사라집니다</div>`;
  f.append(a);

  f.append(el('h2', 'sec', '틀린 문제'));
  const list = el('div', 'list');
  for (const i of wrong) {
    const cnt = (Store.d.att[i.id] || []).filter(x => !x.k).length;
    const b = el('a', 'row');
    b.href = `#/q?one=${encodeURIComponent(i.id)}`;
    b.innerHTML =
      `<div class="row-main">
         <div class="row-s">${esc(i.sj)} · ${esc(i.ty)}</div>
         <div class="row-t" style="font-weight:550;font-size:.95rem">${esc(i.st.slice(0, 60))}</div>
       </div><div class="row-n">${cnt}회 틀림</div>`;
    list.append(b);
  }
  f.append(list);
  paint(f);
});

// ─────────────────────────────────────────────────────── 화면: 복습
route(/^\/review$/, () => {
  setTitle('복습');
  const due = Store.dueIds(DB.items);
  const f = document.createDocumentFragment();

  if (!due.length) {
    const upcoming = DB.items
      .map(i => ({ i, s: Store.d.srs[i.id] })).filter(x => x.s)
      .sort((a, b) => a.s.due - b.s.due)[0];
    let msg = '한 문제라도 풀면 복습 일정이 잡힙니다.';
    if (upcoming) {
      const d = Math.ceil((upcoming.s.due - Date.now()) / 86400000);
      msg = `다음 복습은 ${d <= 0 ? '곧' : d + '일 뒤'}입니다.`;
    }
    f.append(el('div', 'empty', `<b>지금 복습할 것이 없습니다</b>${msg}`));
    return paint(f);
  }

  const a = el('a', 'resume');
  a.href = '#/q?mode=due';
  a.innerHTML = `<div class="rt">복습 ${due.length}문항 시작</div>
    <div class="rs">맞히면 다음 복습이 뒤로 밀립니다</div>`;
  f.append(a);

  f.append(el('h2', 'sec', '오늘 볼 것'));
  const list = el('div', 'list');
  for (const id of due) {
    const i = DB.byId.get(id);
    const s = Store.d.srs[id];
    const b = el('a', 'row');
    b.href = `#/q?one=${encodeURIComponent(id)}`;
    b.innerHTML =
      `<div class="row-main">
         <div class="row-s">${esc(i.sj)} · ${esc(i.ty)}</div>
         <div class="row-t" style="font-weight:550;font-size:.95rem">${esc(i.st.slice(0, 60))}</div>
       </div><div class="row-n">${s.i ? s.i + '일 간격' : '새로'}</div>`;
    list.append(b);
  }
  f.append(list);
  paint(f);
});

// ─────────────────────────────────────────────────────── 화면: 통계
route(/^\/stats$/, () => {
  setTitle('통계');
  const f = document.createDocumentFragment();
  const all = progress(DB.items);
  const atts = Object.values(Store.d.att).flat();

  const k = el('div', 'kpis');
  k.innerHTML =
    `<div class="kpi"><div class="v">${all.done}</div><div class="k">푼 문항</div></div>
     <div class="kpi"><div class="v">${all.done ? all.rate + '%' : '—'}</div>
       <div class="k">정답률</div></div>
     <div class="kpi"><div class="v">${atts.length}</div><div class="k">총 시도</div></div>`;
  f.append(k);

  if (!all.done) {
    f.append(el('div', 'empty', '<b>아직 기록이 없습니다</b>한 문제 풀어 보세요.'));
    return paint(f);
  }

  for (const t of DB.raw.tracks) {
    const subs = DB.subjects(t.id);
    if (!subs.length) continue;
    f.append(el('h2', 'sec', t.name));
    const list = el('div', 'list');
    for (const s of subs) {
      const p = progress(DB.filter({ tr: t.id, sj: s.n }));
      const row = el('div', 'row');
      row.style.cursor = 'default';
      row.innerHTML =
        `<div class="row-main"><div class="row-t">${esc(s.n)}</div>
          <div class="row-s">${progText(p)}</div></div>
         <div class="row-n">${p.done ? p.rate + '%' : '—'}</div>`;
      row.querySelector('.row-main').append(bar(p));
      list.append(row);
    }
    f.append(list);
  }
  paint(f);
});

// ─────────────────────────────────────────────────────── 화면: 설정
route(/^\/settings$/, () => {
  setTitle('설정');
  const f = document.createDocumentFragment();

  f.append(el('h2', 'sec', '관리자 모드'));
  const fd = el('div', 'field');
  if (Store.d.admin) {
    fd.innerHTML = `<div class="row-t">켜져 있습니다</div>
      <div class="hint">문제 화면에 <b>위험도</b>와 출제 이유서가 함께 나옵니다.</div>`;
    const b = el('button', 'btn ghost', '끄기');
    b.style.marginTop = '.7rem'; b.style.width = '100%';
    b.onclick = () => { Store.d.admin = false; Store.save(); render(); };
    fd.append(b);
  } else {
    fd.innerHTML = `<label for="pw">관리자 암호</label>
      <input id="pw" type="password" autocomplete="off" placeholder="암호를 입력하세요">
      <div class="hint">출제자용입니다. 문항의 <b>위험도(low·mid·high)</b>와
        출제 이유서(근거·설계·함정·검증)를 문제 화면에서 함께 봅니다.<br>
        <b>주의</b> — 이것은 화면 표시를 가리는 장치일 뿐 보안 장치가 아닙니다.
        브라우저 개발자 도구를 열 줄 아는 사람은 우회할 수 있습니다.</div>`;
    const b = el('button', 'btn', '켜기');
    b.style.marginTop = '.7rem'; b.style.width = '100%';
    b.onclick = async () => {
      const v = fd.querySelector('#pw').value;
      if (await sha(v) !== ADMIN_HASH) { b.textContent = '암호가 다릅니다';
        setTimeout(() => b.textContent = '켜기', 1400); return; }
      Store.d.admin = true; Store.save();
      try { await DB.loadAdmin(); } catch (e) { /* 파일이 없으면 배지만 안 나온다 */ }
      render();
    };
    fd.append(b);
  }
  f.append(fd);

  f.append(el('h2', 'sec', '기록'));
  const info = el('div', 'field');
  const n = Object.keys(Store.d.att).length;
  info.innerHTML = `<div class="row-t">이 기기에 ${n}문항의 기록이 있습니다</div>
    <div class="hint">푼 기록과 복습 일정은 <b>이 브라우저에만</b> 저장됩니다.
      서버로 올라가지 않으므로 다른 기기와 공유되지 않고, 방문 기록을 지우면 함께 사라집니다.</div>`;
  const del = el('button', 'btn ghost', '기록 전부 지우기');
  del.style.marginTop = '.7rem'; del.style.width = '100%';
  del.onclick = () => {
    if (!confirm('푼 기록·오답노트·복습 일정이 모두 사라집니다. 계속할까요?')) return;
    Store.reset(); render();
  };
  info.append(del);
  f.append(info);

  f.append(el('h2', 'sec', '문항'));
  const about = el('div', 'field');
  about.innerHTML =
    `<div class="row-t">${DB.raw.n}문항 · 키워드 ${DB.raw.keywords.length}개</div>
     <div class="hint">문항은 앱 안에 들어 있습니다. <b>비행기 모드에서도 전부 풀립니다.</b><br>
       모두 자작 문항이며 기출을 복원한 것이 아닙니다.</div>`;
  f.append(about);

  paint(f);
});

// 암호는 평문으로 두지 않는다. (그래도 보안 장치는 아니다 — 위 안내 참조)
const ADMIN_HASH = 'aa790a259912f75b16643edc4862b87fc60ca9cbf4c359da002a56c7294257f4';
async function sha(s) {
  const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join('');
}

// ─────────────────────────────────────────────────────── 화면: 문제 풀이
let SESSION = null;

route(/^\/q\?(.*)$/, (qs) => {
  const p = new URLSearchParams(qs);

  if (!SESSION || SESSION.key !== qs) {
    let pool;
    if (p.get('one')) {
      pool = [DB.byId.get(p.get('one'))].filter(Boolean);
    } else if (p.get('mode') === 'wrong') {
      pool = DB.items.filter(i => Store.isWrong(i.id));
    } else if (p.get('mode') === 'due') {
      const due = new Set(Store.dueIds(DB.items));
      pool = DB.items.filter(i => due.has(i.id));
    } else {
      const f = {};
      if (p.get('tr')) f.tr = p.get('tr');
      if (p.get('sj')) f.sj = p.get('sj');
      if (p.get('ty')) f.ty = p.get('ty');
      if (p.get('kw')) f.kw = +p.get('kw');
      pool = DB.filter(f);
      if (p.get('mode') === 'new') {
        const fresh = pool.filter(i => !Store.tried(i.id));
        if (fresh.length) pool = fresh;
      }
      if (p.get('mode') === 'all' || p.get('mode') === 'new') pool = shuffle(pool);
    }
    if (!pool.length) {
      setTitle('문제');
      return paint(el('div', 'empty',
        '<b>해당하는 문제가 없습니다</b>다른 분류를 골라 보세요.'));
    }
    SESSION = { key: qs, pool, at: 0, chosen: null, graded: false,
                start: Date.now(), right: 0 };
  }
  drawQuestion();
});

function shuffle(a) {
  a = a.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function drawQuestion() {
  const S = SESSION;
  const it = S.pool[S.at];
  setTitle(`${S.at + 1} / ${S.pool.length}`);
  $('#view').className = 'view solo';

  const f = document.createDocumentFragment();

  const pr = el('div', 'qprog');
  pr.append(el('i'));
  pr.querySelector('i').style.width = ((S.at) / S.pool.length * 100) + '%';
  f.append(pr);

  const meta = el('div', 'qmeta');
  meta.innerHTML = `<span>${esc(it.sj)}</span><span class="sep">›</span>
    <span>${esc(it.ty)}</span>` +
    (it.df ? `<span class="sep">·</span><span>난이도 ${esc(it.df)}</span>` : '');
  if (Store.d.admin && DB.admin && DB.admin[it.id] && DB.admin[it.id].rk) {
    const rk = DB.admin[it.id].rk;
    meta.append(el('span', `badge ${rk}`, rk.toUpperCase()));
  }
  f.append(meta);

  if (it.pg != null) {
    const pg = DB.passage(it.pg);
    if (pg.lead) f.append(el('div', 'lead', pg.lead));
    f.append(el('div', 'passage', pg.body));
  } else if (it.ld) {
    f.append(el('div', 'lead', it.ld));
  }
  if (it.mt) f.append(el('div', 'material', it.mt));

  f.append(el('h1', 'stem', esc(it.st)));

  const cs = el('div', 'choices');
  it.ch.forEach((c, n) => {
    const b = el('button', 'ch');
    b.innerHTML = `<span class="no">${CIRC[n]}</span><span class="tx">${c}</span>`;
    b.onclick = () => {
      if (S.graded) return;
      S.chosen = n + 1;
      cs.querySelectorAll('.ch').forEach((x, k) => x.classList.toggle('sel', k === n));
      $('#gradeBtn').disabled = false;
    };
    if (S.chosen === n + 1) b.classList.add('sel');
    cs.append(b);
  });
  f.append(cs);

  paint(f);
  drawFoot();
  if (S.graded) grade(true);
}

function drawFoot() {
  document.querySelectorAll('.foot').forEach(x => x.remove());
  const S = SESSION;
  const foot = el('div', 'foot');
  const inner = el('div', 'foot-in');

  if (!S.graded) {
    const b = el('button', 'btn', '확인');
    b.id = 'gradeBtn';
    b.disabled = S.chosen == null;
    b.onclick = () => grade(false);
    inner.append(b);
  } else {
    const last = S.at >= S.pool.length - 1;
    const b = el('button', 'btn', last ? '끝내기' : '다음 문제');
    b.onclick = () => {
      if (last) { const done = S; SESSION = null; return finish(done); }
      S.at++; S.chosen = null; S.graded = false; S.start = Date.now();
      drawQuestion();
    };
    inner.append(b);
  }
  foot.append(inner);
  document.body.append(foot);
}

function grade(replay) {
  const S = SESSION;
  const it = S.pool[S.at];
  const ok = S.chosen === it.an;

  if (!replay) {
    S.graded = true;
    if (ok) S.right++;
    Store.record(it.id, S.chosen, ok, Date.now() - S.start);
    updateBadges();
  }

  document.querySelectorAll('.ch').forEach((b, n) => {
    b.classList.add('done');
    const isAns = n + 1 === it.an, isMine = n + 1 === S.chosen;
    b.classList.remove('sel');
    if (isAns) b.classList.add('ans');
    else if (isMine) b.classList.add('bad');
    if (it.ea && it.ea[n]) {
      const w = el('span', 'why', stripLead(it.ea[n]));
      b.querySelector('.tx').append(w);
    }
  });

  const v = el('div', `verdict ${ok ? 'o' : 'x'}`);
  v.innerHTML = ok
    ? `<span>맞았습니다</span><small>정답 ${CIRC[it.an - 1]}</small>`
    : `<span>틀렸습니다</span><small>정답은 ${CIRC[it.an - 1]}
       (고른 것 ${CIRC[S.chosen - 1]})</small>`;
  $('.choices').after(v);

  if (it.ex) {
    const ex = el('div', 'explain');
    ex.append(el('h3', null, '해설'));
    ex.insertAdjacentHTML('beforeend', it.ex);
    v.after(ex);
  }

  if (Store.d.admin && DB.admin && DB.admin[it.id]) {
    const a = DB.admin[it.id];
    const box = el('div', 'adm');
    box.append(el('h3', null,
      '출제자용 — 위험도 ' + (a.rk ? a.rk.toUpperCase() : '—')));
    const dl = el('dl');
    // `근거` 는 아래 출제이유서에도 있다. 후기 실측은 다른 칸이므로 이름을 나눈다.
    if (a.ev) { dl.append(el('dt', null, '후기'), el('dd', null, esc(a.ev))); }
    for (const k of ['근거', '설계', '함정', '검증']) {
      if (a.wy && a.wy[k]) {
        dl.append(el('dt', null, k), el('dd', null, esc(a.wy[k])));
      }
    }
    if (a.sn) { dl.append(el('dt', null, '스냅샷'), el('dd', null, esc(a.sn))); }
    if (a.rd) { dl.append(el('dt', null, '회차'), el('dd', null, esc(a.rd))); }
    box.append(dl);
    $('#view').append(box);
  }

  if (!replay) drawFoot();
}

/** `① (정답) …` 에서 앞의 기호를 뗀다 — 선지 옆에 붙으므로 중복이다 */
function stripLead(s) {
  return esc(String(s).replace(/^[①②③④⑤⑥⑦]\s*/, ''));
}

let DONE = null;

function finish(S) {
  DONE = S;                 // 해시를 바꾸기 **전에** 담는다. 순서가 뒤집히면 홈으로 튄다
  location.hash = '#/done';
}

route(/^\/done$/, () => {
  setTitle('결과');
  const S = DONE;
  if (!S) return go('/');
  const f = document.createDocumentFragment();
  const rate = pct(S.right, S.pool.length);

  const k = el('div', 'kpis');
  k.innerHTML =
    `<div class="kpi"><div class="v">${S.pool.length}</div><div class="k">푼 문항</div></div>
     <div class="kpi"><div class="v">${S.right}</div><div class="k">맞힘</div></div>
     <div class="kpi"><div class="v">${rate}%</div><div class="k">정답률</div></div>`;
  f.append(k);

  const miss = S.pool.filter(i => Store.isWrong(i.id));
  if (miss.length) {
    f.append(el('h2', 'sec', `틀린 문제 ${miss.length}개`));
    const list = el('div', 'list');
    for (const i of miss) {
      const b = el('a', 'row');
      b.href = `#/q?one=${encodeURIComponent(i.id)}`;
      b.innerHTML = `<div class="row-main">
        <div class="row-s">${esc(i.sj)} · ${esc(i.ty)}</div>
        <div class="row-t" style="font-weight:550;font-size:.95rem">${esc(i.st.slice(0, 60))}</div>
        </div><div class="row-go">›</div>`;
      list.append(b);
    }
    f.append(list);
  } else {
    f.append(el('div', 'empty', '<b>전부 맞혔습니다</b>다음 분류로 넘어가 보세요.'));
  }

  const home = el('a', 'resume');
  home.href = '#/';
  home.style.marginTop = '1rem';
  home.innerHTML = `<div class="rt">홈으로</div>
    <div class="rs">다른 과목·유형 고르기</div>`;
  f.append(home);
  paint(f);
});

// ─────────────────────────────────────────────────────── 시작
$('#back').onclick = () => history.length > 1 ? history.back() : go('/');
window.addEventListener('hashchange', () => {
  document.querySelectorAll('.foot').forEach(x => x.remove());
  render();
});

(async () => {
  Store.load();
  try {
    await DB.load();
  } catch (e) {
    const b = $('#boot');
    b.classList.add('err');
    b.querySelector('.boot-msg').textContent =
      '문항을 불러오지 못했습니다 — ' + e.message;
    return;
  }
  if (Store.d.admin) { try { await DB.loadAdmin(); } catch (e) { /* 없으면 넘어간다 */ } }

  $('#boot').remove();
  $('#top').hidden = false;
  $('#view').hidden = false;
  $('#tabs').hidden = false;
  render();

  if ('serviceWorker' in navigator && location.protocol !== 'file:') {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
})();
