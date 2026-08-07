library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../theme.dart';
import '../widgets.dart';
import 'sit_screen.dart';

String mmss(int ms) {
  final t = (ms / 1000).ceil().clamp(0, 1 << 30);
  final m = t ~/ 60, s = t % 60;
  return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
}

int sitLeft(SitState s) =>
    (s.endsAt - DateTime.now().millisecondsSinceEpoch).clamp(0, 1 << 40);

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
    final r = Repo.instance.round(widget.tag)!;
    final cur = Store.instance.sit?.tag == widget.tag ? Store.instance.sit : null;
    final hist = Store.instance.history(widget.tag);

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
                Expanded(child: _kpi(c, '${(r.min * 60 / r.n).round()}', '문항당 초')),
              ]),
            ]),
          ),
          const SectionTitle('영역 구성'),
          _AreaTable(areas: r.areas),
          if (hist.isNotEmpty) ...[
            SectionTitle('지난 성적 ${hist.length}회'),
            ...hist.reversed.take(5).map((h) {
              final d = DateTime.fromMillisecondsSinceEpoch(h.at);
              return RowTile(
                title: '${h.score} / ${h.n}점',
                subtitle: '${d.month}월 ${d.day}일 · ${h.sec ~/ 60}분 ${h.sec % 60}초 소요'
                    '${h.auto ? " · 시간 초과" : ""}',
                trailing: Text('${(h.score / h.n * 100).round()}%',
                    style: TextStyle(color: c.dim, fontWeight: FontWeight.w700)),
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
        final ok = await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('다른 회차 진행 중'),
            content: Text('「${Repo.instance.round(otherSit.tag)?.title}」를 푸는 중입니다.\n'
                '그 답안은 사라집니다. 새로 시작할까요?'),
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
