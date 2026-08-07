library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../theme.dart';
import '../widgets.dart';
import 'sit_screen.dart';
import 'exam_result_screen.dart';

String mmss(int ms) {
  final t = (ms / 1000).ceil().clamp(0, 1 << 30);
  final m = t ~/ 60, s = t % 60;
  return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
}

int sitLeft(SitState s) =>
    (s.endsAt - DateTime.now().millisecondsSinceEpoch).clamp(0, 1 << 40);

int pct(int a, int b) => b == 0 ? 0 : (a / b * 100).round();

class ExamDetailScreen extends StatefulWidget {
  final String tag;
  const ExamDetailScreen({super.key, required this.tag});
  @override
  State<ExamDetailScreen> createState() => _ExamDetailScreenState();
}

class _ExamDetailScreenState extends State<ExamDetailScreen> {
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final r = Repo.instance.round(widget.tag);
    // 앱을 판올림하면서 회차가 빠지거나 이름이 바뀔 수 있다. 그때 멎으면 안 된다 —
    // 진행 중이던 응시가 걸려 있으면 켤 때마다 죽는다.
    if (r == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('회차')),
        body: Column(children: [
          const EmptyState(
            title: '회차를 찾을 수 없습니다',
            body: '앱을 업데이트하면서 빠졌을 수 있습니다.',
          ),
          if (Store.instance.sit?.tag == widget.tag)
            Padding(
              padding: const EdgeInsets.all(14),
              child: OutlinedButton(
                onPressed: () async {
                  await Store.instance.setSit(null);
                  if (context.mounted) Navigator.of(context).pop();
                },
                child: const Text('진행 중이던 응시 지우기'),
              ),
            ),
        ]),
      );
    }

    final cur = Store.instance.sit?.tag == widget.tag ? Store.instance.sit : null;
    final hist = Store.instance.history(widget.tag);
    final perQ = r.n == 0 ? 0 : (r.min * 60 / r.n).round();

    return Scaffold(
      appBar: AppBar(title: Text(r.title)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(14, 14, 14, 100),
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(color: c.card, borderRadius: BorderRadius.circular(16),
                border: Border.all(color: c.line)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(r.brand, style: TextStyle(color: c.faint, fontSize: 12.5)),
              const SizedBox(height: 3),
              Text(r.title, style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800, color: c.ink)),
              const SizedBox(height: 12),
              Row(children: [
                Expanded(child: _kpi(c, '${r.n}', '문항')),
                Expanded(child: _kpi(c, '${r.min}', '분')),
                Expanded(child: _kpi(c, '$perQ', '문항당 초')),
              ]),
            ]),
          ),
          const SectionTitle('영역 구성'),
          _AreaTable(areas: r.areas),
          if (hist.isNotEmpty) ...[
            SectionTitle('지난 성적 ${hist.length}회 — 누르면 다시 봅니다'),
            ...hist.reversed.take(5).map((h) {
              final d = DateTime.fromMillisecondsSinceEpoch(h.at);
              return RowTile(
                title: '${h.score} / ${h.n}점',
                subtitle: '${d.month}월 ${d.day}일 · ${h.sec ~/ 60}분 ${h.sec % 60}초 소요'
                    '${h.auto ? " · 시간 초과" : ""}',
                trailing: Text('${pct(h.score, h.n)}%',
                    style: TextStyle(color: c.dim, fontWeight: FontWeight.w700)),
                // 결과를 한 번 닫으면 영영 못 보던 것 — 영역별·문항별을 다시 연다.
                onTap: () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => ExamResultScreen(tag: widget.tag, rec: h))),
              );
            }),
          ],
        ],
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 8, 14, 10),
          child: Row(children: [
            if (cur != null) ...[
              Expanded(
                child: OutlinedButton(
                  onPressed: () async {
                    final ok = await showDialog<bool>(
                      context: context,
                      builder: (ctx) => AlertDialog(
                        title: const Text('버리기'),
                        content: const Text('푼 답안이 사라집니다. 계속할까요?'),
                        actions: [
                          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('취소')),
                          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('버리기')),
                        ],
                      ),
                    );
                    if (ok == true) {
                      await Store.instance.setSit(null);
                      if (!mounted) return;
                      setState(() {});
                    }
                  },
                  child: const Text('버리기'),
                ),
              ),
              const SizedBox(width: 8),
            ],
            Expanded(
              flex: 2,
              child: FilledButton(
                onPressed: () => _startOrResume(context, r, cur),
                child: Text(cur == null
                    ? '${r.min}분 시작'
                    : (sitLeft(cur) > 0 ? '이어하기 · ${mmss(sitLeft(cur))} 남음' : '시간 초과 — 제출')),
              ),
            ),
          ]),
        ),
      ),
    );
  }

  Future<void> _startOrResume(BuildContext context, RoundEntry r, SitState? cur) async {
    if (cur == null) {
      final otherSit = Store.instance.sit;
      if (otherSit != null && otherSit.tag != r.tag) {
        final other = Repo.instance.round(otherSit.tag)?.title ?? otherSit.tag;
        final ok = await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('다른 회차 진행 중'),
            content: Text('「$other」를 푸는 중입니다.\n그 답안은 사라집니다. 새로 시작할까요?'),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('취소')),
              FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('새로 시작')),
            ],
          ),
        );
        if (ok != true) return;
      }
      final now = DateTime.now().millisecondsSinceEpoch;
      await Store.instance.setSit(SitState(
        tag: r.tag, at: now, endsAt: now + r.min * 60000,
        ans: {}, flag: {}, atNo: 1,
      ));
    }
    if (!context.mounted) return;
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => SitScreen(tag: r.tag)));
    if (!mounted) return;
    setState(() {});
  }

  Widget _kpi(AppColors c, String v, String k) => Column(children: [
        Text(v, style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: c.ink)),
        Text(k, style: TextStyle(fontSize: 11.5, color: c.faint)),
      ]);
}

class _AreaTable extends StatelessWidget {
  final List<RoundArea> areas;
  const _AreaTable({required this.areas});
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    int from = 1;
    final rows = <Widget>[];
    for (final a in areas) {
      rows.add(RowTile(title: a.name, subtitle: '$from~${from + a.n - 1}번',
          trailing: Text('${a.n}문항', style: TextStyle(color: c.dim))));
      from += a.n;
    }
    return Column(children: rows);
  }
}
