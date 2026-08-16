/// 제출한 회차를 **필기까지 그대로** 다시 본다 (`PLAN.md` 4단계).
///
/// 필기는 회차를 낼 때 지우지 않는다. 다시 볼 자리가 없으면 저장해 둔 뜻이
/// 없으므로, 결과 화면에서 이리로 온다.
///
/// 여기서는 **그리지 않는다.** 도구를 끈 상태(`InkMode.off`)로 넘기면
/// 필기층이 손가락을 가로채지 않아 그냥 넘겨 보게 된다 — 채점이 끝난 답안을
/// 나중에 고쳐 그리면 「그때 무엇을 생각했나」가 흐려진다.
library;

import 'package:flutter/material.dart';

import '../exam_pdf.dart';
import '../ink.dart';
import '../repo.dart';
import '../store.dart';
import '../theme.dart';
import '../widgets.dart';

class InkReviewScreen extends StatefulWidget {
  final String tag;
  final ExamRecord rec;
  const InkReviewScreen({super.key, required this.tag, required this.rec});

  @override
  State<InkReviewScreen> createState() => _InkReviewScreenState();
}

class _InkReviewScreenState extends State<InkReviewScreen> {
  ExamPdf? _pdf;
  InkDoc? _ink;
  bool _loading = true;
  String? _error;
  late final List<Item> _items = Repo.instance.roundItems(widget.tag);
  final _pager = PageController();
  int _at = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final doc = await ExamPdf.open(widget.tag);
      final ink = InkDoc.decode(await Store.instance.readInk(widget.tag));
      if (!mounted) {
        await doc.close();
        return;
      }
      setState(() {
        _pdf = doc;
        _ink = ink;
        _loading = false;
      });
    } catch (err) {
      if (!mounted) return;
      setState(() {
        _error = '$err';
        _loading = false;
      });
    }
  }

  @override
  void dispose() {
    _pdf?.close();
    _pager.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final n = _items.length;
    return Scaffold(
      appBar: AppBar(
        title: const Text('필기 다시 보기'),
        bottom: _loading || n == 0
            ? null
            : PreferredSize(
                preferredSize: const Size.fromHeight(24),
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text('${_at + 1} / $n',
                      style: TextStyle(color: c.faint, fontSize: 12.5)),
                ),
              ),
      ),
      body: _body(),
      bottomNavigationBar: _loading || _error != null || n == 0
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(14, 8, 14, 10),
                child: Row(children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _at == 0
                          ? null
                          : () => _pager.jumpToPage(_at - 1),
                      child: const Text('‹ 이전'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _at >= n - 1
                          ? null
                          : () => _pager.jumpToPage(_at + 1),
                      child: const Text('다음 ›'),
                    ),
                  ),
                ]),
              ),
            ),
    );
  }

  Widget _body() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return const EmptyState(
          title: 'PDF 를 열지 못했습니다', body: '앱을 다시 시작해 보십시오.');
    }
    final ink = _ink;
    if (ink == null || ink.count == 0) {
      return const EmptyState(
          title: '남긴 필기가 없습니다',
          body: '회차를 「PDF로 풀기」로 풀면서 그은 것이 여기에 남습니다.');
    }
    final c = AppColors.of(context);
    return PageView.builder(
      controller: _pager,
      itemCount: _items.length,
      onPageChanged: (i) => setState(() => _at = i),
      itemBuilder: (ctx, i) {
        final it = _items[i];
        final chosen = widget.rec.ans[it.no];
        final ok = chosen != null && chosen == it.an;
        return ListView(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 24),
          children: [
            Row(children: [
              Text('${it.no}번 · ${it.sj}',
                  style: TextStyle(color: c.faint, fontSize: 12.5)),
              const Spacer(),
              Text(
                chosen == null
                    ? '무응답'
                    : ok
                        ? '정답 $chosen'
                        : '$chosen → 정답 ${it.an}',
                style: TextStyle(
                    fontSize: 12.5,
                    color: chosen == null
                        ? c.faint
                        : ok
                            ? c.ok
                            : c.no),
              ),
            ]),
            const SizedBox(height: 6),
          Center(
            child: ConstrainedBox(
              constraints:
                  const BoxConstraints(maxWidth: examPaperMaxWidth),
              child: ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: Container(
                color: Colors.white,
                // 도구를 끈 채로 넘긴다 — 보기만 하고 고치지 않는다.
                child: QuestionPdfView(
                  pdf: _pdf!,
                  no: it.no ?? 0,
                  ink: ink,
                ),
              ),
            ),
            ),
          ),
          ],
        );
      },
    );
  }
}
