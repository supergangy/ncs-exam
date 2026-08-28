/** 지문 — 여러 문항이 함께 보는 글.
 *
 *  **발문 위에 둔다.** 발문이 그것을 「윗글」이라 부르기 때문이다 —
 *  지문이 붙은 63문항 중 「윗글·위 자료·위 공고문」이 31개이고 「다음·아래」는
 *  3개뿐이다(2026-08-28 실측). 아래에 두면 발문이 거짓말을 한다.
 *
 *  자료(`mt`)는 **반대**다. 「다음」 259 · 「위」 6 이라 발문 아래가 맞다.
 *  지문과 자료를 함께 가진 11문항은 자료가 대개 `<보기>` 다 —
 *  「윗글을 바탕으로 <보기>의 사례를…」. 위·아래가 그대로 맞는다.
 *
 *  ## 왜 부품으로 빼는가
 *
 *  발문을 그리는 화면이 **넷**이다 — 모바일·PC 의 문항 풀이와 응시.
 *  넷 다 지문을 빠뜨리고 있었다. 63문항이 못 푸는 상태였고, 응시 화면은
 *  시간까지 재면서 냈다. 화면마다 적으면 또 하나에서 빠진다.
 *
 *  ## 접기 — 지문 **단위**로 기억한다
 *
 *  한 지문을 최대 네 문항이 함께 본다(`[01~02]`). 두 번째 문항에서 936자를
 *  다시 지나야 하면 스크롤만 길다. 그래서 접을 수 있게 하되 **무엇을 접었는지는
 *  지문 첨자로 기억한다** — 같은 지문의 다음 문항은 접힌 채로 오고, **다른 지문은
 *  펼쳐진 채로 온다.** 안 읽은 글을 접어서 내밀면 안 된다.
 *
 *  기본은 늘 **펼침**이다. 이 글이 없으면 문항을 풀 수 없다.
 *
 *  `lead`(「[01~02] 다음 글을 읽고 물음에 답하시오.」)는 접어도 남긴다 —
 *  접힌 자리에 무엇이 있는지 알려 주는 것이 그 줄이다.
 */
import { useState } from 'react';

import { plain } from './core/text.js';

export default function Passage({ db, it }) {
  // **훅을 먼저 부른다.** 지문 없는 문항에서 일찍 돌아가면 훅 차례가 어긋난다
  //   (묶음 안에 지문 있는 문항과 없는 문항이 섞여 있다)
  const [shut, setShut] = useState(() => new Set());

  if (!it || it.pg == null) return null;
  const p = db.passage(it.pg);
  if (!p || !p.body) return null;

  const open = !shut.has(it.pg);
  const n = plain(p.body).length;
  const id = 'pass-' + it.pg;

  const toggle = () => setShut(s => {
    const next = new Set(s);
    next.has(it.pg) ? next.delete(it.pg) : next.add(it.pg);
    return next;
  });

  return (
    <>
      {p.lead && <div className="lead">{p.lead}</div>}
      {open && (
        <div className="passage" id={id} dangerouslySetInnerHTML={{ __html: p.body }} />
      )}
      {/* 단추는 늘 **발문 바로 앞**에 온다 — 펼쳤을 때는 다 읽은 자리이고,
          접었을 때는 안내 줄 바로 아래다 */}
      <button className="btn btn-ghost fold" onClick={toggle}
              aria-expanded={open} aria-controls={id}>
        {open ? '지문 접기' : `지문 펼치기 · ${n}자`}
      </button>
    </>
  );
}
