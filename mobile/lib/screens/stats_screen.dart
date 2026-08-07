library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../theme.dart';
import '../widgets.dart';

class StatsScreen extends StatelessWidget {
  const StatsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final repo = Repo.instance;
    final all = computeProgress(repo.bank.items);
    final atts = Store.instance.att.values.fold<int>(0, (s, l) => s + l.length);

    final sections = <Widget>[];
    for (final t in repo.bank.tracks) {
      final subs = repo.subjects(t.id);
      if (subs.isEmpty) continue;
      sections.add(SectionTitle(t.name));
      for (final s in subs) {
        final p = computeProgress(repo.filter(tr: t.id, sj: s.n));
        sections.add(RowTile(
          title: s.n,
          subtitle: progText(p),
          progress: p,
          trailing: Text(p.done > 0 ? '${p.rate}%' : '—',
              style: TextStyle(color: c.dim, fontWeight: FontWeight.w700)),
        ));
      }
    }

    return Scaffold(
      appBar: AppBar(title: const Text('통계')),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          Row(children: [
            Expanded(child: _kpi(c, '${all.done}', '푼 문항')),
            Expanded(child: _kpi(c, all.done > 0 ? '${all.rate}%' : '—', '정답률')),
            Expanded(child: _kpi(c, '$atts', '총 시도')),
          ]),
          if (all.done == 0)
            const EmptyState(title: '아직 기록이 없습니다', body: '한 문제 풀어 보세요.')
          else
            ...sections,
        ],
      ),
    );
  }

  Widget _kpi(AppColors c, String v, String k) => Container(
        margin: const EdgeInsets.symmetric(horizontal: 4),
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
            color: c.card,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: c.line)),
        child: Column(children: [
          Text(v, style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: c.ink)),
          Text(k, style: TextStyle(fontSize: 11.5, color: c.faint)),
        ]),
      );
}
