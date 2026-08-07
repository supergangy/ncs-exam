library;

import 'dart:async';
import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../theme.dart';
import '../html_view.dart';
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
  bool _submitting = false;

  SitState get s => Store.instance.sit!;
  List<Item> get items => Repo.instance.roundItems(widget.tag);
  Item get cur => items[(s.atNo - 1).clamp(0, items.length - 1)];

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(milliseconds: 500), (_) {
      if (!mounted) return;
      if (sitLeft(s) <= 0) {
        _timer?.cancel();
        _autoSubmit();
      } else {
        setState(() {});
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _pick(int n) async {
    final same = s.ans[cur.no] == n;
    if (same) {
      s.ans.remove(cur.no);
    } else {
      s.ans[cur.no!] = n;
    }
    await Store.instance.save();
    setState(() {});
  }

  Future<void> _goto(int no) async {
    s.atNo = no;
    await Store.instance.save();
    setState(() {});
  }

  Future<void> _toggleFlag() async {
    s.flag[cur.no!] = !(s.flag[cur.no] ?? false);
    await Store.instance.save();
    setState(() {});
  }

  Future<void> _askSubmit() async {
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
    if (ok == true) await _submit(false);
  }

  Future<void> _autoSubmit() async {
    if (!mounted || _submitting) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('시간 종료'),
        content: const Text('시간이 다 됐습니다. 제출합니다.'),
        actions: [FilledButton(onPressed: () => Navigator.pop(ctx), child: const Text('확인'))],
      ),
    );
    await _submit(true);
  }

  Future<void> _submit(bool auto) async {
    if (_submitting) return;
    _submitting = true;
    int score = 0;
    for (final it in items) {
      final chosen = s.ans[it.no];
      final ok = chosen == it.an;
      if (ok) score++;
      await Store.instance.record(it.id, chosen, ok);
    }
    final rec = ExamRecord(
      at: DateTime.now().millisecondsSinceEpoch, score: score, n: items.length,
      sec: ((DateTime.now().millisecondsSinceEpoch - s.at) / 1000).round(),
      auto: auto, ans: Map.of(s.ans),
    );
    await Store.instance.addExam(widget.tag, rec);
    await Store.instance.setSit(null);
    if (!mounted) return;
    Navigator.of(context).pushReplacement(MaterialPageRoute(
        builder: (_) => ExamResultScreen(tag: widget.tag, rec: rec)));
  }

  void _openOmr() {
    showModalBottomSheet(
      context: context, isScrollControlled: true,
      builder: (ctx) => _OmrSheet(
        items: items, sit: s,
        onJump: (no) { Navigator.pop(ctx); _goto(no); },
        onSubmit: () { Navigator.pop(ctx); _askSubmit(); },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final it = cur;
    final idx = items.indexWhere((i) => i.no == it.no);
    final left = sitLeft(s);
    final flagged = s.flag[it.no] ?? false;

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) Navigator.of(context).pop(); // 응시 화면을 나가도 진행 상태는 저장돼 있다
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text('${it.no} / ${items.length}'),
          actions: [
            TextButton(
              onPressed: _openOmr,
              child: Text(mmss(left),
                  style: TextStyle(
                      color: left <= 5 * 60000 ? c.no : c.ink,
                      fontWeight: FontWeight.w800, fontVariations: const [])),
            ),
            IconButton(icon: const Icon(Icons.grid_view_rounded), onPressed: _openOmr),
          ],
        ),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 90),
          children: [
            LinearProgressIndicator(value: idx / items.length, minHeight: 3,
                backgroundColor: c.line, valueColor: AlwaysStoppedAnimation(c.brand)),
            const SizedBox(height: 10),
            Row(children: [
              Text(it.sj, style: TextStyle(color: c.faint, fontSize: 12.5)),
              const Spacer(),
              OutlinedButton.icon(
                onPressed: _toggleFlag,
                icon: Icon(flagged ? Icons.star : Icons.star_border, size: 16,
                    color: flagged ? c.warn : c.faint),
                label: Text(flagged ? '표시함' : '나중에',
                    style: TextStyle(fontSize: 12, color: flagged ? c.warn : c.faint)),
                style: OutlinedButton.styleFrom(
                    side: BorderSide(color: flagged ? c.warn : c.line),
                    padding: const EdgeInsets.symmetric(horizontal: 10)),
              ),
            ]),
            const SizedBox(height: 6),
            if (it.pg != null) ...[
              if (Repo.instance.passage(it.pg!).lead != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(Repo.instance.passage(it.pg!).lead!,
                      style: TextStyle(color: c.dim, fontSize: 13.5)),
                ),
              HtmlBox(Repo.instance.passage(it.pg!).body),
            ] else if (it.ld != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(it.ld!, style: TextStyle(color: c.dim, fontSize: 13.5)),
              ),
            if (it.mt != null) HtmlBox(it.mt!),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(plainText(it.st),
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: c.ink)),
            ),
            ...List.generate(it.ch.length, (n) {
              final sel = s.ans[it.no] == n + 1;
              return InkWell(
                onTap: () => _pick(n + 1),
                borderRadius: BorderRadius.circular(12),
                child: Container(
                  margin: const EdgeInsets.only(bottom: 7),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
                  decoration: BoxDecoration(
                    color: sel ? c.brandSoft : c.card, borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: sel ? c.brand : c.line, width: 1.4),
                  ),
                  child: Row(children: [
                    Container(
                      width: 24, height: 24,
                      decoration: BoxDecoration(color: sel ? c.brand : c.bg, shape: BoxShape.circle,
                          border: Border.all(color: sel ? c.brand : c.line)),
                      alignment: Alignment.center,
                      child: Text(circ[n], style: TextStyle(
                          color: sel ? Colors.white : c.dim, fontSize: 12, fontWeight: FontWeight.w700)),
                    ),
                    const SizedBox(width: 10),
                    Expanded(child: Text(plainText(it.ch[n]),
                        style: TextStyle(color: c.ink, fontSize: 15))),
                  ]),
                ),
              );
            }),
          ],
        ),
        bottomNavigationBar: SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(14, 8, 14, 10),
            child: Row(children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: idx == 0 ? null : () => _goto(items[idx - 1].no!),
                  child: const Text('‹ 이전'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: FilledButton(
                  onPressed: idx >= items.length - 1 ? _askSubmit
                      : () => _goto(items[idx + 1].no!),
                  child: Text(idx >= items.length - 1 ? '제출하기' : '다음 ›'),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

class _OmrSheet extends StatelessWidget {
  final List<Item> items;
  final SitState sit;
  final void Function(int no) onJump;
  final VoidCallback onSubmit;
  const _OmrSheet({required this.items, required this.sit, required this.onJump,
      required this.onSubmit});

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    return DraggableScrollableSheet(
      initialChildSize: 0.75, maxChildSize: 0.9, minChildSize: 0.5,
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
                  maxCrossAxisExtent: 60, mainAxisSpacing: 6, crossAxisSpacing: 6, childAspectRatio: 0.95),
              itemCount: items.length,
              itemBuilder: (ctx, i) {
                final it = items[i];
                final done = sit.ans.containsKey(it.no);
                final flag = sit.flag[it.no] ?? false;
                final here = it.no == sit.atNo;
                return InkWell(
                  onTap: () => onJump(it.no!),
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
