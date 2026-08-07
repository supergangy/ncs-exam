library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../theme.dart';
import '../widgets.dart';

/// 초 단위로 짧게 — 「1분 20초」보다 「1:20」이 표에서 읽기 낫다.
String _dur(int ms) {
  final s = (ms / 1000).round();
  if (s < 60) return '$s초';
  return '${s ~/ 60}분 ${(s % 60).toString().padLeft(2, '0')}초';
}

class StatsScreen extends StatelessWidget {
  const StatsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final repo = Repo.instance;
    return Scaffold(
      appBar: AppBar(title: const Text('통계')),
      body: ListenableBuilder(
        listenable: Store.instance,
        builder: (context, _) {
          final c = AppColors.of(context);
          final store = Store.instance;
          final all = computeProgress(repo.bank.items);
          final atts = store.att.values.fold<int>(0, (s, l) => s + l.length);
          final avg = store.avgSolveMs();

          final sections = <Widget>[];
          if (all.done > 0) {
            for (final t in repo.bank.tracks) {
              final subs = repo.subjects(t.id);
              if (subs.isEmpty) continue;
              sections.add(SectionTitle(t.name));
              for (final s in subs) {
                final items = repo.filter(tr: t.id, sj: s.n);
                final p = computeProgress(items);
                final sAvg = store.avgSolveMs(items.map((i) => i.id));
                sections.add(RowTile(
                  title: s.n,
                  subtitle: sAvg == null
                      ? progText(p)
                      : '${progText(p)} · 평균 ${_dur(sAvg)}',
                  progress: p,
                  trailing: Text(p.done > 0 ? '${p.rate}%' : '—',
                      style: TextStyle(color: c.dim, fontWeight: FontWeight.w700)),
                ));
              }
            }
          }

          return ListView(
            padding: const EdgeInsets.all(14),
            children: [
              Row(children: [
                Expanded(child: _kpi(c, '${all.done}', '푼 문항')),
                Expanded(child: _kpi(c, all.done > 0 ? '${all.rate}%' : '—', '정답률')),
                Expanded(
                    child: _kpi(c, avg == null ? '—' : _dur(avg), '평균 풀이')),
              ]),
              if (avg != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8, left: 2),
                  child: Text(
                    '풀이 시간은 낱개 풀이에서만 잽니다 — 회차 응시는 채점 순간이 없어 재지 않습니다. '
                    '총 $atts회 시도했습니다.',
                    style: TextStyle(color: c.faint, fontSize: 12.5),
                  ),
                ),
              if (all.done == 0)
                const EmptyState(title: '아직 기록이 없습니다', body: '한 문제 풀어 보세요.')
              else
                ...sections,
            ],
          );
        },
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
          Text(v,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: c.ink)),
          Text(k, style: TextStyle(fontSize: 11.5, color: c.faint)),
        ]),
      );
}
