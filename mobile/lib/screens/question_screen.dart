/// 낱개 풀이 — 웹 `#/q?...` 의 solo 모드.
///
/// 웹판과 다른 점 하나 — **좌우로 넘길 수 있고 되돌아갈 수 있다.**
/// 그래서 고른 답과 채점 여부를 문항마다 따로 들고 있는다(웹은 한 벌만 들고 앞으로만 갔다).
library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../theme.dart';
import '../widgets.dart';
import '../html_view.dart';
import '../qnav.dart';

class QuestionScreen extends StatefulWidget {
  final List<Item> pool;
  final String title;
  const QuestionScreen({super.key, required this.pool, this.title = ''});

  /// 저장해 둔 묶음을 그대로 다시 연다 (홈의 이어하기 카드).
  static QuestionScreen? fromSaved(SoloSession s) {
    final pool = s.ids.map(Repo.instance.byId).whereType<Item>().toList();
    // 판올림으로 문항이 빠졌으면 자리가 밀린다. 되살리지 않는다.
    if (pool.length != s.ids.length) return null;
    return QuestionScreen(pool: pool, title: s.title);
  }

  @override
  State<QuestionScreen> createState() => _QuestionScreenState();
}

/// 한 문항에 이보다 오래 머물렀으면 재지 않는다 —
/// 화면을 켜 둔 채 자리를 비운 것이지 푼 것이 아니다.
const _maxSolveMs = 10 * 60 * 1000;

class _QuestionScreenState extends State<QuestionScreen> {
  late final PageController _pager;
  late List<Item> pool;
  late List<int?> _chosen;
  late List<bool> _graded;
  int at = 0;
  /// 지금 쪽이 보이기 시작한 시각. 여기서 걸린 시간을 뺀다.
  int _shownAt = 0;

  Item get item => pool[at];

  @override
  void initState() {
    super.initState();
    pool = widget.pool;
    _chosen = List.filled(pool.length, null);
    _graded = List.filled(pool.length, false);

    // 나갔다 온 것이면 그 자리에서 잇는다. 섞여 들어와도 **문항 집합이 같으면**
    // 저장된 순서와 상태를 쓴다 — 그래야 16곳 호출부를 안 고치고도 이어진다.
    final saved = Store.instance.solo;
    if (saved != null && pool.length > 1 && _sameSet(saved.ids)) {
      final restored = saved.ids.map(Repo.instance.byId).whereType<Item>().toList();
      if (restored.length == saved.ids.length) {
        pool = restored;
        _chosen = List.of(saved.chosen);
        _graded = List.of(saved.graded);
        at = saved.at.clamp(0, pool.length - 1);
      }
    }
    _pager = PageController(initialPage: at);
    _shownAt = DateTime.now().millisecondsSinceEpoch;
    if (pool.length > 1) _persist();
  }

  bool _sameSet(List<String> ids) {
    if (ids.length != pool.length) return false;
    final mine = pool.map((i) => i.id).toSet();
    return ids.every(mine.contains);
  }

  void _persist() {
    if (pool.length <= 1) return;
    Store.instance.solo = SoloSession(
      ids: pool.map((i) => i.id).toList(),
      chosen: List.of(_chosen),
      graded: List.of(_graded),
      at: at,
      title: widget.title,
      savedAt: DateTime.now().millisecondsSinceEpoch,
    );
    Store.instance.saveSoon();
  }

  @override
  void dispose() {
    _pager.dispose();
    super.dispose();
  }

  void _pick(int n) {
    if (_graded[at]) return;
    setState(() => _chosen[at] = n);
    _persist();
  }

  Future<void> _grade() async {
    final ok = _chosen[at] == item.an;
    final spent = DateTime.now().millisecondsSinceEpoch - _shownAt;
    setState(() => _graded[at] = true);
    _persist();
    await Store.instance.record(item.id, _chosen[at], ok,
        ms: (spent > 0 && spent <= _maxSolveMs) ? spent : null);
  }

  void _go(int i) {
    if (i < 0 || i >= pool.length) return;
    _pager.animateToPage(i,
        duration: const Duration(milliseconds: 260), curve: Curves.easeOutCubic);
  }

  void _onPage(int i) {
    setState(() => at = i);
    _shownAt = DateTime.now().millisecondsSinceEpoch;
    _persist();
  }

  void _finish() {
    Store.instance.solo = null;
    Store.instance.save();
    Navigator.of(context).pushReplacement(MaterialPageRoute(
      builder: (_) => _ResultPage(pool: pool, chosen: _chosen, graded: _graded),
    ));
  }

  /// 어느 쪽(page)의 문항인지 **받아서** 쓴다. `at` 을 쓰면 손가락이 스와이프
  /// 중일 때 옆 쪽의 별을 눌러 엉뚱한 문항이 북마크된다.
  Future<void> _toggleBookmark(int i, bool v) async {
    await Store.instance.toggleMark(pool[i].id, bookmark: v);
    if (!mounted) return;
    setState(() {});
  }

  Future<void> _promptMemo(int i) async {
    final id = pool[i].id;
    final cur = Store.instance.markOf(id);
    final ctl = TextEditingController(text: cur.memo);
    try {
      final action = await showDialog<String>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('무엇이 이상한가요?'),
          content: TextField(controller: ctl, autofocus: true, maxLines: 3,
              decoration: const InputDecoration(hintText: '그냥 확인만 눌러도 됩니다')),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('취소')),
            // 표시를 지우는 길이 없어서, 한 번 쓴 메모가 목록에도 내보내기에도 계속 남았다.
            if (cur.flag || cur.memo.isNotEmpty)
              TextButton(
                onPressed: () => Navigator.pop(ctx, 'clear'),
                child: const Text('표시 지우기'),
              ),
            FilledButton(onPressed: () => Navigator.pop(ctx, 'save'), child: const Text('저장')),
          ],
        ),
      );
      if (action == null) return;
      if (action == 'clear') {
        await Store.instance.clearFlag(id);
      } else {
        final memo = ctl.text.trim();
        if (memo.isEmpty) {
          await Store.instance.toggleMark(id, flag: true);
        } else {
          await Store.instance.setMemo(id, memo);
        }
      }
      if (!mounted) return;
      setState(() {});
    } finally {
      ctl.dispose();
    }
  }

  NavMark _mark(int i) {
    if (!_graded[i]) return _chosen[i] != null ? NavMark.done : NavMark.none;
    return _chosen[i] == pool[i].an ? NavMark.ok : NavMark.no;
  }

  @override
  Widget build(BuildContext context) {
    if (pool.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: Text(widget.title.isEmpty ? '풀기' : widget.title)),
        body: const EmptyState(title: '풀 문항이 없습니다', body: '다른 분류를 골라 보세요.'),
      );
    }
    final graded = _graded[at];
    final chosen = _chosen[at];
    final last = at >= pool.length - 1;

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title.isEmpty
            ? '${at + 1} / ${pool.length}'
            : '${widget.title} · ${at + 1}/${pool.length}'),
        bottom: pool.length > 1
            ? QuestionStrip(
                count: pool.length, current: at,
                markOf: _mark, labelOf: (i) => '${i + 1}', onTap: _go,
              )
            : null,
      ),
      body: PageView.builder(
        controller: _pager,
        itemCount: pool.length,
        onPageChanged: _onPage,
        itemBuilder: (ctx, i) => _QuestionBody(
          item: pool[i],
          chosen: _chosen[i],
          graded: _graded[i],
          onPick: (n) { if (i == at) _pick(n); },
          onBookmark: (v) => _toggleBookmark(i, v),
          onFlag: () => _promptMemo(i),
        ),
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 8, 14, 10),
          child: Row(children: [
            if (at > 0) ...[
              SizedBox(
                width: 60, height: 48,
                child: OutlinedButton(
                  onPressed: () => _go(at - 1),
                  style: OutlinedButton.styleFrom(padding: EdgeInsets.zero),
                  child: const Text('‹'),
                ),
              ),
              const SizedBox(width: 8),
            ],
            Expanded(
              child: SizedBox(
                height: 48,
                child: FilledButton(
                  onPressed: graded
                      ? (last ? _finish : () => _go(at + 1))
                      : (chosen == null ? null : _grade),
                  child: Text(graded ? (last ? '끝내기' : '다음 문제 ›') : '확인'),
                ),
              ),
            ),
          ]),
        ),
      ),
    );
  }
}

/// 한 문항의 본문. PageView 의 한 쪽이다.
class _QuestionBody extends StatelessWidget {
  final Item item;
  final int? chosen;
  final bool graded;
  final void Function(int n) onPick;
  final void Function(bool v) onBookmark;
  final VoidCallback onFlag;
  const _QuestionBody({
    required this.item, required this.chosen, required this.graded,
    required this.onPick, required this.onBookmark, required this.onFlag,
  });

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final m = Store.instance.markOf(item.id);
    final admin = Store.instance.admin ? (Repo.instance.admin?[item.id]) : null;

    return ListView(
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 24),
      children: [
        Row(children: [
          Expanded(
            child: Wrap(spacing: 6, runSpacing: 2, crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                _MetaChip(item.sj), _MetaChip(item.ty),
                if (item.rd != null)
                  _MetaChip('${Repo.instance.round(item.rd!)?.title ?? item.rd} ${item.no}번'),
                if (item.df != null) _MetaChip('난이도 ${item.df}'),
                if (admin?.rk != null) RiskBadge(admin!.rk!),
              ],
            ),
          ),
          IconButton(
            icon: Icon(m.bookmark ? Icons.star : Icons.star_border,
                color: m.bookmark ? c.brand : c.faint, size: 22),
            tooltip: '북마크',
            onPressed: () => onBookmark(!m.bookmark),
          ),
          IconButton(
            icon: Icon(m.flag ? Icons.flag : Icons.outlined_flag,
                color: m.flag ? c.warn : c.faint, size: 20),
            tooltip: '확인 필요',
            onPressed: onFlag,
          ),
        ]),
        if (item.pg != null && Repo.instance.passage(item.pg!) != null) ...[
          if (Repo.instance.passage(item.pg!)!.lead != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Text(Repo.instance.passage(item.pg!)!.lead!,
                  style: TextStyle(color: c.dim, fontSize: 13.5)),
            ),
          HtmlBox(Repo.instance.passage(item.pg!)!.body),
        ] else if (item.ld != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Text(item.ld!, style: TextStyle(color: c.dim, fontSize: 13.5)),
          ),
        if (item.mt != null) HtmlBox(item.mt!),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: SelectionArea(
            child: HtmlText(item.st,
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600,
                    color: c.ink, height: 1.5)),
          ),
        ),
        ...List.generate(item.ch.length, (n) => _ChoiceTile(
              n: n, text: item.ch[n], selected: chosen == n + 1,
              correct: graded && n + 1 == item.an,
              wrong: graded && n + 1 == chosen && chosen != item.an,
              graded: graded,
              each: item.ea != null && n < item.ea!.length ? item.ea![n] : null,
              onTap: () => onPick(n + 1),
            )),
        if (graded) ...[
          const SizedBox(height: 12),
          _Verdict(ok: chosen == item.an, answer: item.an, chosen: chosen),
          if (item.ex != null) ...[
            const SizedBox(height: 10),
            _Labeled('해설', HtmlBox(item.ex!)),
          ],
          if (admin != null) ...[
            const SizedBox(height: 10),
            _AdminBox(admin),
          ],
        ],
      ],
    );
  }
}

class _MetaChip extends StatelessWidget {
  final String text;
  const _MetaChip(this.text);
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    return Text(text, style: TextStyle(color: c.faint, fontSize: 12.5));
  }
}

class _ChoiceTile extends StatelessWidget {
  final int n;
  final String text;
  final bool selected, correct, wrong, graded;
  final String? each;
  final VoidCallback onTap;
  const _ChoiceTile({
    required this.n, required this.text, required this.selected,
    required this.correct, required this.wrong, required this.graded,
    required this.each, required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    Color border = c.line, bg = c.card, circleColor = c.bg, circleFg = c.dim;
    if (selected && !graded) {
      border = c.brand; bg = c.brandSoft; circleColor = c.brand; circleFg = Colors.white;
    }
    if (correct) {
      border = c.ok; bg = c.okSoft; circleColor = c.ok; circleFg = Colors.white;
    } else if (wrong) {
      border = c.no; bg = c.noSoft; circleColor = c.no; circleFg = Colors.white;
    }
    return InkWell(
      onTap: graded ? null : onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        margin: const EdgeInsets.only(bottom: 7),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
        decoration: BoxDecoration(
          color: bg, borderRadius: BorderRadius.circular(12),
          border: Border.all(color: border, width: 1.4),
        ),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(
            width: 24, height: 24,
            decoration: BoxDecoration(color: circleColor, shape: BoxShape.circle,
                border: Border.all(color: border)),
            alignment: Alignment.center,
            child: Text(circ[n], style: TextStyle(color: circleFg, fontSize: 12,
                fontWeight: FontWeight.w700)),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              HtmlText(text, style: TextStyle(color: c.ink, fontSize: 15, height: 1.45)),
              if (graded && each != null && each!.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 5),
                  child: HtmlText(stripLead(each!),
                      style: TextStyle(color: c.dim, fontSize: 13, height: 1.4)),
                ),
            ]),
          ),
        ]),
      ),
    );
  }
}

class _Verdict extends StatelessWidget {
  final bool ok;
  final int answer;
  final int? chosen;
  const _Verdict({required this.ok, required this.answer, required this.chosen});
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(color: ok ? c.okSoft : c.noSoft,
          borderRadius: BorderRadius.circular(14)),
      child: Row(children: [
        Text(ok ? '맞았습니다' : '틀렸습니다',
            style: TextStyle(color: ok ? c.ok : c.no, fontWeight: FontWeight.w800, fontSize: 15)),
        const Spacer(),
        Text(ok ? '정답 ${circ[answer - 1]}'
            : '정답은 ${circ[answer - 1]} (고른 것 ${chosen != null ? circ[chosen! - 1] : "없음"})',
            style: TextStyle(color: ok ? c.ok : c.no, fontSize: 12.5)),
      ]),
    );
  }
}

class _Labeled extends StatelessWidget {
  final String label;
  final Widget child;
  const _Labeled(this.label, this.child);
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Padding(
        padding: const EdgeInsets.only(bottom: 4, left: 2),
        child: Text(label, style: TextStyle(color: c.faint, fontSize: 12, fontWeight: FontWeight.w700)),
      ),
      child,
    ]);
  }
}

class _AdminBox extends StatelessWidget {
  final AdminInfo a;
  const _AdminBox(this.a);
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final rows = <Widget>[];
    if (a.ev != null) rows.add(_kv(c, '후기', a.ev!));
    for (final k in ['근거', '설계', '함정', '검증']) {
      final v = a.wy?[k];
      if (v is String && v.isNotEmpty) rows.add(_kv(c, k, v));
    }
    if (a.sn != null) rows.add(_kv(c, '스냅샷', a.sn!));
    if (a.rd != null) rows.add(_kv(c, '회차', a.rd!));
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: c.warnSoft, borderRadius: BorderRadius.circular(14),
        border: Border.all(color: c.warn, width: 1, style: BorderStyle.solid),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('출제자용 — 위험도 ${(a.rk ?? '—').toUpperCase()}',
            style: TextStyle(color: c.warn, fontWeight: FontWeight.w800, fontSize: 12.5)),
        const SizedBox(height: 8),
        ...rows,
      ]),
    );
  }

  Widget _kv(AppColors c, String k, String v) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: RichText(
          text: TextSpan(children: [
            TextSpan(text: '$k  ', style: TextStyle(color: c.warn, fontWeight: FontWeight.w800,
                fontSize: 12.5)),
            TextSpan(text: plainText(v).replaceAll('**', ''),
                style: TextStyle(color: c.ink, fontSize: 12.5)),
          ]),
        ),
      );
}

class _ResultPage extends StatelessWidget {
  final List<Item> pool;
  final List<int?> chosen;
  final List<bool> graded;
  const _ResultPage({required this.pool, required this.chosen, required this.graded});

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final done = graded.where((g) => g).length;
    var right = 0;
    final miss = <Item>[];
    for (var i = 0; i < pool.length; i++) {
      if (!graded[i]) continue;
      if (chosen[i] == pool[i].an) {
        right++;
      } else {
        miss.add(pool[i]);
      }
    }
    final rate = done == 0 ? 0 : (right / done * 100).round();

    return Scaffold(
      appBar: AppBar(title: const Text('결과')),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          Row(children: [
            Expanded(child: _kpi(c, '$done', '푼 문항')),
            Expanded(child: _kpi(c, '$right', '맞힘')),
            Expanded(child: _kpi(c, '$rate%', '정답률')),
          ]),
          if (done < pool.length)
            Padding(
              padding: const EdgeInsets.only(top: 10, left: 2),
              child: Text('${pool.length - done}문항은 풀지 않았습니다 — 기록에 넣지 않았습니다.',
                  style: TextStyle(color: c.faint, fontSize: 12.5)),
            ),
          if (miss.isEmpty && done > 0)
            const EmptyState(title: '전부 맞혔습니다', body: '다음 분류로 넘어가 보세요.')
          else if (miss.isNotEmpty) ...[
            SectionTitle('틀린 문제 ${miss.length}개'),
            ...miss.map((i) => RowTile(
                  title: Repo.instance.line(i, 40),
                  subtitle: '${i.sj} · ${i.ty}',
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => QuestionScreen(pool: [i]))),
                )),
            const SizedBox(height: 8),
            ResumeCard(
              title: '틀린 ${miss.length}문항 다시 풀기',
              subtitle: '해설을 보며 하나씩',
              onTap: () => Navigator.of(context).pushReplacement(
                  MaterialPageRoute(builder: (_) => QuestionScreen(pool: miss))),
            ),
          ],
          const SizedBox(height: 8),
          OutlinedButton(
            onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst),
            child: const Text('홈으로'),
          ),
        ],
      ),
    );
  }

  Widget _kpi(AppColors c, String v, String k) => Container(
        margin: const EdgeInsets.symmetric(horizontal: 4),
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(color: c.card, borderRadius: BorderRadius.circular(14),
            border: Border.all(color: c.line)),
        child: Column(children: [
          Text(v, style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: c.ink)),
          Text(k, style: TextStyle(fontSize: 11.5, color: c.faint)),
        ]),
      );
}
