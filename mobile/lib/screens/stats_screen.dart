library;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../repo.dart';
import '../stats_data.dart';
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
              else ...[
                const SectionTitle('최근 30일'),
                _daily(c, dailyStats(store.att, DateTime.now())),
                ...sections,
              ],
            ],
          );
        },
      ),
    );
  }

  /// 최근 30일 하루치 시도 수. 막대 하나가 하루다.
  ///
  /// 맞힌 몫을 진한 색으로 아래 깔고 그 위에 전체를 얹는다 — 막대 두 개를
  /// 나란히 두면 30일치가 화면에 안 들어간다.
  Widget _daily(AppColors c, List<DayStat> days) {
    final maxY = days.fold<int>(0, (m, d) => d.solved > m ? d.solved : m);
    if (maxY == 0) return const SizedBox.shrink();
    final total = days.fold<int>(0, (s, d) => s + d.solved);
    final acted = days.where((d) => d.solved > 0).length;

    return Container(
      padding: const EdgeInsets.fromLTRB(10, 16, 14, 8),
      decoration: BoxDecoration(
          color: c.card,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: c.line)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SizedBox(
          height: 130,
          child: BarChart(
            BarChartData(
              maxY: maxY * 1.15,
              alignment: BarChartAlignment.spaceBetween,
              barTouchData: BarTouchData(enabled: false),
              gridData: const FlGridData(show: false),
              borderData: FlBorderData(show: false),
              titlesData: FlTitlesData(
                leftTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                rightTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                topTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 20,
                    interval: 7,
                    getTitlesWidget: (v, meta) {
                      final i = v.toInt();
                      if (i < 0 || i >= days.length) return const SizedBox.shrink();
                      final d = days[i].day;
                      return Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text('${d.month}/${d.day}',
                            style: TextStyle(color: c.faint, fontSize: 10)),
                      );
                    },
                  ),
                ),
              ),
              barGroups: [
                for (var i = 0; i < days.length; i++)
                  BarChartGroupData(x: i, barRods: [
                    BarChartRodData(
                      toY: days[i].solved.toDouble(),
                      width: 5,
                      borderRadius: BorderRadius.circular(2),
                      color: c.brandSoft,
                      rodStackItems: [
                        // 아래쪽 진한 몫이 맞힌 것.
                        BarChartRodStackItem(
                            0, days[i].correct.toDouble(), c.brand),
                      ],
                    ),
                  ]),
              ],
            ),
          ),
        ),
        const SizedBox(height: 6),
        Text('30일 동안 $acted일 · $total회 시도했습니다. 진한 칸이 맞힌 것입니다.',
            style: TextStyle(color: c.faint, fontSize: 12.5)),
      ]),
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
