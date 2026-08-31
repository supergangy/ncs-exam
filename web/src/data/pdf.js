/** 회차 PDF 내려받기 — 어디에 있고 무슨 이름으로 저장되나.
 *
 *  회차마다 인쇄본이 두 벌 있다. 그동안 앱은 그것을 「PDF로 풀기」에만 썼고
 *  (문항 하나를 오려 보여 준다), 파일 자체를 내주지는 않았다.
 *  **인쇄해서 종이로 푸는 것이 실전이다.** 그 길을 열어 둔다.
 *
 *  ## 서버 이름과 보이는 이름이 다르다
 *
 *  파일 이름이 한글이라(`NCS_봉투모의고사_1회_문제.pdf`) 주소에 그대로 쓰면
 *  퍼센트 인코딩이 길어지고 서버·브라우저마다 달리 다룬다. 서버에는
 *  `exams/r1_public.pdf` 로 두고, 저장될 이름만 `download` 속성으로 한글을 준다.
 *  `tools/export_bank.py` 가 두 이름을 함께 만든다.
 *
 *  ## 진입점이 둘이라 상대 경로가 갈린다
 *
 *  PC 는 `<루트>/`, 모바일은 `<루트>/m/` 에서 뜬다. `vite` 의 `base` 가 `'./'` 라
 *  절대 경로를 못 쓴다 — 깃허브 페이지는 저장소 이름 아래에 얹히기 때문이다.
 *  서비스 워커가 껍데기를 고를 때 쓰는 것과 **같은 수**를 쓴다.
 */

/** 무엇을 내주나. 차례가 화면의 차례다 */
export const PDF_KINDS = [
  { k: 'q', name: '문제집', hint: '인쇄해서 종이로 푸는 것' },
  { k: 's', name: '해설집', hint: '정답과 풀이' },
];

/** 회차 PDF 의 주소. `kind` 는 `'q'`(문제집) 또는 `'s'`(해설집) */
export function pdfHref(tag, kind, path = typeof location === 'undefined' ? '' : location.pathname) {
  const up = path.includes('/m/') ? '../' : '';
  return `${up}exams/${tag}${kind === 's' ? '.sol' : ''}.pdf`;
}

/** 1,449KB → `1.4MB`. 1MB 아래는 KB 그대로 — 「0.6MB」보다 「598KB」가 읽힌다 */
export function sizeText(kb) {
  return kb >= 1024 ? `${(kb / 1024).toFixed(1)}MB` : `${kb}KB`;
}

/** 이 회차에서 내려받을 수 있는 것 — `[{ k, name, hint, file, kb, size, href }]`.
 *
 *  **없는 것은 내지 않는다.** 옛 `bank.json` 에는 `pdf` 칸이 아예 없고,
 *  `build.py` 를 안 돌린 회차는 해설집이 빠질 수 있다. 그때 빈 단추를 세우면
 *  눌러도 404 가 난다. */
export function pdfList(round) {
  if (!round || !round.pdf) return [];
  return PDF_KINDS.flatMap(({ k, name, hint }) => {
    const got = round.pdf[k];
    if (!Array.isArray(got) || !got[0]) return [];
    return [{
      k, name, hint,
      file: got[0],
      kb: got[1] || 0,
      size: sizeText(got[1] || 0),
      href: pdfHref(round.tag, k),
    }];
  });
}
