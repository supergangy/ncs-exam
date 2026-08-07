/// 회차 응시 — 웹 `#/sit/:tag`.
/// 채점하지 않고, 벽시계로 남은 시간을 재고, 좌우로 넘기며 푼다.
library;

import 'dart:async';
import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../theme.dart';
import '../html_view.dart';
import '../qnav.dart';
import 'exam_detail_screen.dart' show mmss, sitLeft;
import 'exam_result_screen.dart';

class SitScreen extends StatefulWidget {
  final String tag;
  const SitScreen({super.key, required this.tag});
  @override
  State<SitScreen> createState() => _SitScreenState();
}

class _SitScreenState extends State<SitScreen> {
  Timer? _timer;
  /// 제출 대화상자가 떠 있다 — 그 위에 자동 제출을 겹쳐 띄우지 않기 위한 잠금.
  bool _submitting = false;
  /// 이미 냈다 — 두 번 채점하지 않기 위한 빗장. 한 번 서면 다시 내려가지 않는다.
  bool _done = false;
  PageController? _pager;
  late final List<Item> items;
  /// 남은 시간만 따로 흘린다 — 500ms 마다 화면 전체를 다시 그리면 문항이 깜빡인다.
  final _left = ValueNotifier<int>(0);
  int at = 0;

  SitState get s => Store.instance.sit!;

  @override
  void initState() {
    super.initState();
    items = Repo.instance.roundItems(widget.tag);
    if (items.isEmpty) return; // build 에서 안내 화면으로 빠진다
    at = items.indexWhere((i) => i.no == s.atNo);
    if (at < 0) at = 0;
    _pager = PageController(initialPage: at);
    _left.value = sitLeft(s);
    _timer = Timer.periodic(const Duration(milliseconds: 500), (_) {
      if (!mounted) return;
      final v = sitLeft(s);
      _left.value = v;
      if (v <= 0) {
        _timer?.cancel();
        _autoSubmit();
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pager?.dispose();
    _left.dispose();
    super.dispose();
  }

  Item get cur => items[at];

  void _pick(int i, int n) {
    final no = items[i].no!;
    setState(() {
      if (s.ans[no] == n) {
        s.ans.remove(no);
      } else {
        s.ans[no] = n;
      }
    });
    Store.instance.saveSoon();
  }

  /// 어느 쪽의 문항인지 받아서 쓴다 — 스와이프 중에 `at` 을 믿으면 옆 문항에 별이 붙는다.
  void _toggleFlag(int i) {
    final no = items[i].no!;
    setState(() => s.flag[no] = !(s.flag[no] ?? false));
    Store.instance.saveSoon();
  }

  void _go(int i) {
    if (i < 0 || i >= items.length) return;
    _pager?.animateToPage(i,
        duration: const Duration(milliseconds: 240), curve: Curves.easeOutCubic);
  }

  void _onPage(int i) {
    setState(() => at = i);
    s.atNo = items[i].no!;
    Store.instance.saveSoon();
  }

  Future<void> _askSubmit() async {
    if (_submitting) return;
    // 확인 대화상자가 떠 있는 동안 시계가 0이 되면 자동 제출이 그 위에 또 쌓인다.
    // 그러면 pushReplacement 가 **대화상자를** 갈아 끼워 응시 화면이 살아남고,
    // sit 은 이미 null 이라 되돌아왔을 때 앱이 멎는다. 여기서 먼저 잠근다.
    _submitting = true;
    final blanks = items.where((i) => !s.ans.containsKey(i.no)).map((i) => i.no!).toList();
    String msg = '제출하면 채점되고 답을 고칠 수 없습니다.';
    if (blanks.isNotEmpty) {
      final preview = blanks.take(12).join(', ');
      msg = '아직 답하지 않은 문항이 ${blanks.length}개 있습니다.\n'
          '($preview${blanks.length > 12 ? " …" : ""})\n\n빈칸은 오답으로 처리됩니다. 그래도 제출할까요?';
    }
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('제출'),
        content: Text(msg),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('취소')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('제출')),
        ],
      ),
    );
    if (ok != true) {
      _submitting = false;
      // 잠가 둔 사이에 시간이 다 됐다면 지금 바로 낸다.
      if (mounted && sitLeft(s) <= 0) await _autoSubmit();
      return;
    }
    _submitting = false;
    await _submit(false);
  }

  Future<void> _autoSubmit() async {
    if (!mounted || _submitting || _done) return;
    _submitting = true;
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        title: const Text('시간 종료'),
        content: const Text('시간이 다 됐습니다. 제출합니다.'),
        actions: [FilledButton(onPressed: () => Navigator.pop(ctx), child: const Text('확인'))],
      ),
    );
    await _submit(true);
  }

  Future<void> _submit(bool auto) async {
    if (_done) return;
    _done = true;
    _timer?.cancel();
    final now = DateTime.now().millisecondsSinceEpoch;
    final ans = Map<int, int>.of(s.ans);
    // 걸린 시간은 **제한 시간을 넘지 않는다.** 앱을 껐다가 여섯 시간 뒤에 열면
    // 벽시계 그대로는 「360분 소요」가 찍힌다 — 60분짜리 시험인데.
    final elapsed = (now - s.at).clamp(0, s.endsAt - s.at);
    int score = 0;
    for (final it in items) {
      final chosen = ans[it.no];
      final ok = chosen == it.an;
      if (ok) score++;
      // 안 고른 문항도 **틀린 것으로** 남긴다 — 시험은 빈칸이 오답이다.
      Store.instance.recordQuiet(it.id, chosen, ok);
    }
    final rec = ExamRecord(
      at: now, score: score, n: items.length,
      sec: (elapsed / 1000).round(), auto: auto, ans: ans,
    );
    Store.instance.exams.putIfAbsent(widget.tag, () => []).add(rec);
    Store.instance.sit = null;
    await Store.instance.save();
    if (!mounted) return;
    Navigator.of(context).pushReplacement(MaterialPageRoute(
        builder: (_) => ExamResultScreen(tag: widget.tag, rec: rec)));
  }

  void _openOmr() {
    showModalBottomSheet(
      context: context, isScrollControlled: true,
      builder: (ctx) => _OmrSheet(
        items: items, sit: s,
        onJump: (i) { Navigator.pop(ctx); _go(i); },
        onSubmit: () { Navigator.pop(ctx); _askSubmit(); },
      ),
    );
  }

  Future<void> _confirmLeave() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('나가기'),
        content: const Text('시계는 계속 갑니다. 푼 답안은 남아 있어 이어서 볼 수 있습니다.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('계속 풀기')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('나가기')),
        ],
      ),
    );
    if (ok == true && mounted) Navigator.of(context).pop();
  }

  NavMark _mark(int i) {
    final it = items[i];
    if (s.flag[it.no] == true) return NavMark.flag;
    return s.ans.containsKey(it.no) ? NavMark.done : NavMark.none;
  }

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    if (items.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: const Text('응시')),
        body: const Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Text('이 회차의 문항을 찾을 수 없습니다.', textAlign: TextAlign.center),
          ),
        ),
      );
    }
    final last = at >= items.length - 1;

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) { if (!didPop) _confirmLeave(); },
      child: Scaffold(
        appBar: AppBar(
          leading: IconButton(icon: const Icon(Icons.close), onPressed: _confirmLeave),
          title: Text('${cur.no} / ${items.length}'),
          actions: [
            Center(
              child: ValueListenableBuilder<int>(
                valueListenable: _left,
                builder: (ctx, v, _) => Text(
                  mmss(v),
                  style: TextStyle(
                      color: v <= 5 * 60000 ? c.no : c.ink,
                      fontWeight: FontWeight.w800, fontSize: 16,
                      fontFeatures: const [FontFeature.tabularFigures()]),
                ),
              ),
            ),
            IconButton(
                icon: const Icon(Icons.grid_view_rounded),
                tooltip: '답안지',
                onPressed: _openOmr),
          ],
          bottom: QuestionStrip(
            count: items.length, current: at, markOf: _mark,
            labelOf: (i) => '${items[i].no}', onTap: _go,
          ),
        ),
        body: PageView.builder(
          controller: _pager,
          itemCount: items.length,
          onPageChanged: _onPage,
          itemBuilder: (ctx, i) => _SitBody(
            item: items[i],
            chosen: s.ans[items[i].no],
            flagged: s.flag[items[i].no] ?? false,
            onPick: (n) => _pick(i, n),
            onFlag: () => _toggleFlag(i),
          ),
        ),
        bottomNavigationBar: SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(14, 8, 14, 10),
            child: Row(children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: at == 0 ? null : () => _go(at - 1),
                  child: const Text('‹ 이전'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: FilledButton(
                  onPressed: last ? _askSubmit : () => _go(at + 1),
                  child: Text(last ? '제출하기' : '다음 ›'),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

class _SitBody extends StatelessWidget {
  final Item item;
  final int? chosen;
  final bool flagged;
  final void Function(int n) onPick;
  final VoidCallback onFlag;
  const _SitBody({required this.item, required this.chosen, required this.flagged,
      required this.onPick, required this.onFlag});

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 24),
      children: [
        Row(children: [
          Text(item.sj, style: TextStyle(color: c.faint, fontSize: 12.5)),
          const Spacer(),
          OutlinedButton.icon(
            onPressed: onFlag,
            icon: Icon(flagged ? Icons.star : Icons.star_border, size: 16,
                color: flagged ? c.warn : c.faint),
            label: Text(flagged ? '표시함' : '나중에',
                style: TextStyle(fontSize: 12, color: flagged ? c.warn : c.faint)),
            style: OutlinedButton.styleFrom(
                side: BorderSide(color: flagged ? c.warn : c.line),
                padding: const EdgeInsets.symmetric(horizontal: 10),
                visualDensity: VisualDensity.compact),
          ),
        ]),
        const SizedBox(height: 4),
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
        ...List.generate(item.ch.length, (n) {
          final sel = chosen == n + 1;
          return InkWell(
            onTap: () => onPick(n + 1),
            borderRadius: BorderRadius.circular(12),
            child: Container(
              margin: const EdgeInsets.only(bottom: 7),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
              decoration: BoxDecoration(
                color: sel ? c.brandSoft : c.card, borderRadius: BorderRadius.circular(12),
                border: Border.all(color: sel ? c.brand : c.line, width: 1.4),
              ),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Container(
                  width: 24, height: 24,
                  decoration: BoxDecoration(color: sel ? c.brand : c.bg, shape: BoxShape.circle,
                      border: Border.all(color: sel ? c.brand : c.line)),
                  alignment: Alignment.center,
                  child: Text(circ[n], style: TextStyle(
                      color: sel ? Colors.white : c.dim, fontSize: 12,
                      fontWeight: FontWeight.w700)),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: HtmlText(item.ch[n],
                      style: TextStyle(color: c.ink, fontSize: 15, height: 1.45)),
                ),
              ]),
            ),
          );
        }),
      ],
    );
  }
}

class _OmrSheet extends StatelessWidget {
  final List<Item> items;
  final SitState sit;
  final void Function(int index) onJump;
  final VoidCallback onSubmit;
  const _OmrSheet({required this.items, required this.sit, required this.onJump,
      required this.onSubmit});

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    return DraggableScrollableSheet(
      initialChildSize: 0.75, maxChildSize: 0.9, minChildSize: 0.5,
      expand: false,
      builder: (ctx, scroll) => Container(
        decoration: BoxDecoration(color: c.card,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(18))),
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
        child: Column(children: [
          Row(children: [
            const Text('답안지', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            const SizedBox(width: 8),
            Text('${sit.ans.length} / ${items.length} 표기', style: TextStyle(color: c.faint)),
            const Spacer(),
            IconButton(icon: const Icon(Icons.close), onPressed: () => Navigator.pop(context)),
          ]),
          Expanded(
            child: GridView.builder(
              controller: scroll,
              padding: const EdgeInsets.symmetric(vertical: 10),
              gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                  maxCrossAxisExtent: 60, mainAxisSpacing: 6, crossAxisSpacing: 6,
                  childAspectRatio: 0.95),
              itemCount: items.length,
              itemBuilder: (ctx, i) {
                final it = items[i];
                final done = sit.ans.containsKey(it.no);
                final flag = sit.flag[it.no] ?? false;
                final here = it.no == sit.atNo;
                return InkWell(
                  onTap: () => onJump(i),
                  borderRadius: BorderRadius.circular(9),
                  child: Container(
                    decoration: BoxDecoration(
                      color: done ? c.brandSoft : c.card,
                      borderRadius: BorderRadius.circular(9),
                      border: Border.all(
                        color: here ? c.ink : (flag ? c.warn : (done ? c.brand : c.line)),
                        width: here ? 2 : (flag ? 1.6 : 1),
                      ),
                    ),
                    alignment: Alignment.center,
                    child: Column(mainAxisSize: MainAxisSize.min, children: [
                      Text('${it.no}', style: TextStyle(fontSize: 10.5, color: c.faint)),
                      Text(done ? circ[sit.ans[it.no]! - 1] : '·',
                          style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700,
                              color: done ? c.brand : c.faint)),
                    ]),
                  ),
                );
              },
            ),
          ),
          SizedBox(
            width: double.infinity,
            child: FilledButton(onPressed: onSubmit, child: const Text('제출하기')),
          ),
        ]),
      ),
    );
  }
}
