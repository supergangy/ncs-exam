/** 오답노트 · 복습 · 표시해 둔 문항 — **한 화면이 셋을 맡는다.**
 *
 *  구성이 같다 — 무엇이 왜 모였는지 알리고, 목록을 보이고, 「전부 풀기」로 넘긴다.
 *  세 파일로 나누면 한쪽만 고쳐 어긋난다.
 *
 *  묶음을 만드는 것은 `data/pool.js` 다. 주소(`?pool=wrong`)를 화면과 나눠 갖는다.
 */
import { CIRC } from '../../core/text.js';
import { makePool, poolHref } from '../../data/pool.js';
import * as I from '../../icons.jsx';
import { go } from '../../router/useHash.js';
import { useStore, useDerived } from '../../store/useStore.js';

/** 비었을 때 무엇을 하면 되는지 적는다 — 「없습니다」만으로는 막막하다 */
const EMPTY = {
  wrong: '틀린 문항이 여기 모입니다. 다시 맞히면 자동으로 빠집니다.',
  review: '지금 다시 볼 문항이 없습니다. 풀고 나면 SM-2 간격으로 돌아옵니다.',
  marks: '문항 화면의 깃발을 누르면 여기 모입니다.',
};

export default function Pool({ db, kind }) {
  const st = useStore();
  const pool = makePool(db, st, 'pool=' + kind);
  const rows = useDerived(s => pool.items.map(it => ({
    it, last: s.last(it.id), until: s.untilText(it.id), flag: !!s.marked(it.id)?.f,
  })), [db, kind, pool.items.length]);

  if (!rows.length) {
    return (
      <div className="empty">
        <p style={{ fontWeight: 700, color: 'var(--ink)' }}>{pool.title}</p>
        <p className="sm">{EMPTY[kind]}</p>
        <button className="btn btn-tint" style={{ marginTop: '1rem' }} onClick={() => go('/')}>
          문항 고르기
        </button>
      </div>
    );
  }

  return (
    <div className="stack">
      <div className="card pad">
        <div className="h2">{pool.title}</div>
        <div className="row-sub" style={{ marginTop: '.2rem' }}>
          {rows.length}문항{pool.sub ? ` · ${pool.sub}` : ''}
        </div>
        <button className="btn btn-primary" style={{ width: '100%', marginTop: '.8rem' }}
                onClick={() => go(poolHref({ pool: kind }))}>
          전부 풀기 ({rows.length})
        </button>
      </div>

      <div className="card rows">
        {rows.map(({ it, last, until, flag }, i) => (
          <button key={it.id} className="row-item"
                  onClick={() => go(poolHref({ pool: kind }) + '&at=' + i)}>
            <span className="row-n" style={{ minWidth: '1.6rem' }}>{i + 1}</span>
            <span className="row-t">
              <span style={{ display: 'block', overflow: 'hidden',
                             textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {db.line(it, 32)}
              </span>
              <span className="row-sub" style={{ display: 'block' }}>
                {it.sj} · {it.ty}
                {last && !last.k && ` · 고른 것 ${CIRC[last.c - 1] || '—'}`}
                {kind === 'review' && until && ` · ${until}`}
              </span>
            </span>
            {flag && <I.Flag style={{ width: 15, height: 15, color: 'var(--warn-vivid)' }} />}
            <I.Chevron className="chev" />
          </button>
        ))}
      </div>
    </div>
  );
}
