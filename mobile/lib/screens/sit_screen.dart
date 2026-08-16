/// 회차 응시 — 웹 `#/sit/:tag`.
/// 채점하지 않고, 벽시계로 남은 시간을 재고, 좌우로 넘기며 푼다.
library;

import 'dart:async';
import 'package:flutter/material.dart';
import '../exam_pdf.dart';
import '../ink.dart';
import '../ink_canvas.dart';
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
  // 「PDF로 풀기」 — 인쇄본과 같은 화면으로 본다. 회차에만 둔다.
  // 낱개 풀이는 HTML 그대로다(글자 크기 조절·검색이 살아 있어야 한다).
  ExamPdf? _pdf;
  bool _pdfMode = false;
  bool _pdfAvailable = false;

  // 필기 (4단계). PDF 모드에서만 뜬다 — 앱 화면은 글자가 흐르므로 획이 어긋난다.
  InkDoc? _ink;
  InkSettings _inkSet = const InkSettings();
  Timer? _inkSave;

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
    // 자산이 있는 회차에만 전환 버튼을 보여 준다. 문서는 켤 때 연다 —
    // 안 쓸 사람에게 4.5MB 를 열게 할 이유가 없다.
    ExamPdf.exists(widget.tag).then((yes) {
      if (mounted && yes) setState(() => _pdfAvailable = true);
    });
  }

  Future<void> _togglePdf() async {
    if (_pdfMode) {
      setState(() => _pdfMode = false);
      return;
    }
    var doc = _pdf;
    if (doc == null) {
      final messenger = ScaffoldMessenger.of(context);
      try {
        doc = await ExamPdf.open(widget.tag);
      } catch (err) {
        messenger.showSnackBar(
            const SnackBar(content: Text('PDF 를 열지 못했습니다.')));
        return;
      }
      if (!mounted) {
        await doc.close();
        return;
      }
      _pdf = doc;
    }
    // 필기는 PDF 를 켤 때 한 번만 읽는다. 회차를 열 때마다 읽으면
    // 안 쓸 사람에게도 수백 KB 를 붙인다.
    if (_ink == null) {
      try {
        _ink = InkDoc.decode(await Store.instance.readInk(widget.tag));
      } catch (err) {
        debugPrint('필기를 읽지 못했다: $err');
        _ink = InkDoc();
      }
    }
    if (!mounted) return;
    setState(() => _pdfMode = true);
  }

  /// 획이 바뀔 때마다 쓰면 손이 멈출 때마다 디스크를 친다. 잠깐 모았다 쓴다.
  void _inkChanged() {
    setState(() {});
    _inkSave?.cancel();
    _inkSave = Timer(const Duration(milliseconds: 700), _flushInk);
  }

  Future<void> _flushInk() async {
    final doc = _ink;
    if (doc == null || doc.dirty.isEmpty) return;
    final pages = {for (final p in doc.dirty) p: doc.encodePage(p)};
    doc.clearDirty();
    try {
      await Store.instance.writeInkPages(widget.tag, pages);
    } catch (err) {
      // 저장에 실패해도 화면의 획은 남는다. 다음 저장 때 다시 시도된다.
      debugPrint('필기를 쓰지 못했다: $err');
      doc.dirty.addAll(pages.keys);
    }
  }

  Future<void> _clearInk() async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('필기를 모두 지울까요?'),
        content: const Text('이 회차에 그린 것이 전부 사라집니다. 되돌릴 수 없습니다.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('그만두기')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('지우기')),
        ],
      ),
    );
    if (yes != true || !mounted) return;
    setState(() => _ink = InkDoc());
    await Store.instance.clearInk(widget.tag);
  }

  @override
  void dispose() {
    _timer?.cancel();
    _inkSave?.cancel();
    // 나가기 직전의 획도 남긴다 — 제출하고 나가도 복기 때 보인다.
    unawaited(_flushInk());
    _pager?.dispose();
    _left.dispose();
    _pdf?.close();
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
            if (_pdfAvailable)
              IconButton(
                icon: Icon(_pdfMode
                    ? Icons.article_outlined
                    : Icons.picture_as_pdf_outlined),
                tooltip: _pdfMode ? '앱 화면으로' : 'PDF로 풀기',
                onPressed: _togglePdf,
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
          // 그리는 중에는 옆으로 안 넘어간다. 획을 긋다 화면이 넘어가면
          // 그 획이 통째로 날아간다.
          physics: _inkSet.mode == InkMode.off
              ? null
              : const NeverScrollableScrollPhysics(),
          itemCount: items.length,
          onPageChanged: _onPage,
          itemBuilder: (ctx, i) => _SitBody(
            item: items[i],
            pdf: _pdfMode ? _pdf : null,
            ink: _pdfMode ? _ink : null,
            inkSettings: _inkSet,
            onInkChanged: _inkChanged,
            chosen: s.ans[items[i].no],
            flagged: s.flag[items[i].no] ?? false,
            onPick: (n) => _pick(i, n),
            onFlag: () => _toggleFlag(i),
          ),
        ),
        bottomNavigationBar: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (_pdfMode && _ink != null)
              InkToolbar(
                settings: _inkSet,
                canUndo: _ink!.canUndo,
                canRedo: _ink!.canRedo,
                onChanged: (v) => setState(() => _inkSet = v),
                onUndo: () { _ink!.undo(); _inkChanged(); },
                onRedo: () { _ink!.redo(); _inkChanged(); },
                onClear: _clearInk,
              ),
            SafeArea(
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
          ],
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
  /// null 이면 평소대로 HTML 로 그린다.
  final ExamPdf? pdf;
  final InkDoc? ink;
  final InkSettings inkSettings;
  final VoidCallback? onInkChanged;
  const _SitBody({required this.item, required this.chosen, required this.flagged,
      required this.onPick, required this.onFlag, this.pdf,
      this.ink, this.inkSettings = const InkSettings(), this.onInkChanged});

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
        if (pdf != null) ...[
          // 종이 그대로 오려 낸 문항. 선지도 그림 안에 있고, 답은 아래에서 고른다.
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: Container(
              color: Colors.white,
              child: QuestionPdfView(
                pdf: pdf!,
                no: item.no ?? 0,
                ink: ink,
                inkSettings: inkSettings,
                onInkChanged: onInkChanged,
              ),
            ),
          ),
          const SizedBox(height: 10),
        ] else if (item.pg != null && Repo.instance.passage(item.pg!) != null) ...[
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
        if (pdf == null && item.mt != null) HtmlBox(item.mt!),
        if (pdf == null) Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: SelectionArea(
            child: HtmlText(item.st,
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600,
                    color: c.ink, height: 1.5)),
          ),
        ),
        // PDF 모드에서는 선지 글자를 다시 쓰지 않는다 — 그림 안에 이미 있다.
        // 동그라미만 크게 늘어놓아 손가락으로 고르게 한다.
        if (pdf != null)
          Row(children: [
            for (var n = 0; n < item.ch.length; n++)
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 3),
                  child: InkWell(
                    onTap: () => onPick(n + 1),
                    borderRadius: BorderRadius.circular(12),
                    child: Container(
                      height: 52,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: chosen == n + 1 ? c.brand : c.card,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                            color: chosen == n + 1 ? c.brand : c.line, width: 1.4),
                      ),
                      child: Text(circ[n], style: TextStyle(
                          fontSize: 20, fontWeight: FontWeight.w700,
                          color: chosen == n + 1 ? Colors.white : c.dim)),
                    ),
                  ),
                ),
              ),
          ])
        else
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
