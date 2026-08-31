/** 회차 PDF 내려받기.
 *
 *  화면이 세우는 단추가 **실제로 있는 파일**을 가리키는지 본다. 링크가 404 면
 *  누르기 전까지 아무도 모른다 — 그래서 배포본 `bank.json` 으로 한 번 훑는다.
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

import { pdfHref, pdfList, sizeText } from '../src/data/pdf.js';
import { wrap } from '../src/data/bank.js';

// ── 주소 ───────────────────────────────────────────────────────────
test('진입점이 둘이라 상대 경로가 갈린다', () => {
  assert.equal(pdfHref('r1_public', 'q', '/ncs-pass-app/'), 'exams/r1_public.pdf');
  assert.equal(pdfHref('r1_public', 'q', '/ncs-pass-app/m/'), '../exams/r1_public.pdf');
  assert.equal(pdfHref('r7_cs', 's', '/'), 'exams/r7_cs.sol.pdf');
  assert.equal(pdfHref('r7_cs', 's', '/m/'), '../exams/r7_cs.sol.pdf');
});

test('주소에 한글이 들어가지 않는다 — 인코딩이 갈리는 자리다', () => {
  for (const k of ['q', 's']) {
    const h = pdfHref('r6_seoulmetro', k, '/m/');
    assert.ok(/^[\x20-\x7e]+$/.test(h), h);
  }
});

// ── 크기 표기 ──────────────────────────────────────────────────────
test('1MB 아래는 KB 그대로', () => {
  assert.equal(sizeText(598), '598KB');
  assert.equal(sizeText(1023), '1023KB');
  assert.equal(sizeText(1024), '1.0MB');
  assert.equal(sizeText(1449), '1.4MB');
});

// ── 없는 것은 내지 않는다 ──────────────────────────────────────────
test('pdf 칸이 없는 회차는 빈 목록 — 옛 bank.json 대비', () => {
  assert.deepEqual(pdfList({ tag: 'old' }), []);
  assert.deepEqual(pdfList(null), []);
});

test('해설집만 없으면 문제집 하나만 낸다', () => {
  const got = pdfList({ tag: 'r9', pdf: { q: ['가.pdf', 500] } });
  assert.equal(got.length, 1);
  assert.equal(got[0].k, 'q');
  assert.equal(got[0].file, '가.pdf');
});

test('차례는 문제집 먼저', () => {
  const got = pdfList({ tag: 'r9', pdf: { s: ['해설.pdf', 1], q: ['문제.pdf', 2] } });
  assert.deepEqual(got.map(x => x.k), ['q', 's']);
});

// ── 배포본으로 한 번 ───────────────────────────────────────────────
test('실제 bank.json — 일곱 회차가 문제집·해설집을 다 갖는다', () => {
  const bank = JSON.parse(readFileSync(new URL('../../app/data/bank.json', import.meta.url),
                                       'utf8'));
  const db = wrap(bank);
  assert.equal(db.rounds.length, 7);
  for (const r of db.rounds) {
    const got = pdfList(r);
    assert.deepEqual(got.map(x => x.k), ['q', 's'], `${r.tag} — ${got.length}개뿐이다`);
    for (const x of got) {
      assert.ok(x.kb > 100, `${r.tag} ${x.k} 가 ${x.kb}KB 다 — 빈 파일이 아닌가`);
      assert.ok(x.file.endsWith('.pdf'), x.file);
      // 출제이유 PDF 는 집필 쪽 자료다. 내주면 함정 설계가 새어 나간다
      assert.ok(!x.file.includes('출제이유'), `${r.tag} 에 출제이유가 섞였다`);
    }
  }
});

test('가리키는 파일이 실제로 있다 — 링크가 404 면 눌러야 안다', () => {
  const bank = JSON.parse(readFileSync(new URL('../../app/data/bank.json', import.meta.url),
                                       'utf8'));
  const db = wrap(bank);

  // `web/public/exams/` 는 gitignore 다 — `tools/export_bank.py` 가 만든다.
  // 새로 클론한 자리에는 없으므로, 있을 때만 본다. CI 는 내보내기를 먼저
  // 돌리므로 거기서는 실제로 검사된다(`.github/workflows/checks.yml`).
  const webDir = new URL('../public/exams/', import.meta.url);
  const madeForWeb = existsSync(webDir);

  for (const r of db.rounds) {
    for (const x of pdfList(r)) {
      const rel = pdfHref(r.tag, x.k, '/');          // `exams/<이름>`
      // 앱 번들은 **커밋되어 있다** — 언제나 있어야 한다
      const onApp = new URL('../../mobile/assets/' + rel, import.meta.url);
      assert.ok(existsSync(onApp), `앱에 없다 — mobile/assets/${rel}`);
      if (madeForWeb) {
        const onWeb = new URL('../public/' + rel, import.meta.url);
        assert.ok(existsSync(onWeb), `웹에 없다 — public/${rel}`);
      }
    }
  }

  if (!madeForWeb) {
    console.log('    (web/public/exams/ 가 없다 — python tools/export_bank.py 를 돌리면 검사된다)');
  }
});
