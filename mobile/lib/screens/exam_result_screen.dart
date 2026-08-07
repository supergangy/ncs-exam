library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../theme.dart';
import '../widgets.dart';
import 'question_screen.dart';

int pct(int a, int b) => b == 0 ? 0 : (a / b * 100).round();

class ExamResultScreen extends StatelessWidget {
  final String tag;
  final ExamRecord rec;
  const ExamResultScreen({super.key, required this.tag, required this.rec});

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final r = Repo.instance.round(tag)!;
    final hist = Store.instance.history(tag);
    final items = Repo.instance.roundItems(tag);
    final rate = pct(rec.score, rec.n);

    String? trend;
    if (hist.length > 1) {
      final prev = hist[hist.length - 2];
      final diff = rate - pct(prev.score, prev.n);
      trend = diff == 0
          ? '지난번과 같은 점수입니다.'
          : '지난번보다 ${diff.abs()}%p ${diff > 0 ? "올랐습니다." : "내렸습니다."}';
    }

    final miss = items.where((i) => rec.ans[i.no] != i.an).toList();

    return Scaffold(
      appBar: AppBar(title: Text('${r.title} 결과')),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          Row(children: [
            Expanded(child: _kpi(c, '${rec.score}', '/ ${rec.n}점')),
            Expanded(child: _kpi(c, '$rate%', '정답률')),
            Expanded(child: _kpi(
                c, '${rec.sec ~/ 60}분', '소요${rec.auto ? " (시간 초과)" : ""}')),
          ]),
          if (trend != null)
            Padding(
              padding: const EdgeInsets.only(top: 10, left: 2),
              child: Text(trend, style: TextStyle(color: c.faint, fontSize: 13)),
            ),
          const SectionTitle('영역별'),
          ...r.areas.map((a) {
            final sub = items.where((i) => i.sj == a.name).toList();
            final ok = sub.where((i) => rec.ans[i.no] == i.an).length;
            return RowTile(
              title: a.name,
              subtitle: '$ok / ${sub.length}문항',
              trailing: Text('${pct(ok, sub.length)}%',
                  style: TextStyle(color: c.dim, fontWeight: FontWeight.w700)),
            );
          }),
          const SectionTitle('문항별 — 누르면 해설'),
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                maxCrossAxisExtent: 56,
                mainAxisSpacing: 6,
                crossAxisSpacing: 6,
                childAspectRatio: 0.95),
            itemCount: items.length,
            itemBuilder: (ctx, i) {
              final it = items[i];
              final chosen = rec.ans[it.no];
              final ok = chosen == it.an;
              final color = ok ? c.ok : (chosen != null ? c.no : c.faint);
              final bgc = ok ? c.okSoft : (chosen != null ? c.noSoft : c.card);
              return InkWell(
                onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => QuestionScreen(pool: [it]))),
                borderRadius: BorderRadius.circular(9),
                child: Container(
                  decoration: BoxDecoration(
                      color: bgc,
                      borderRadius: BorderRadius.circular(9),
                      border: Border.all(color: color)),
                  alignment: Alignment.center,
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                    Text('${it.no}', style: TextStyle(fontSize: 10.5, color: c.faint)),
                    Text(ok ? '○' : (chosen != null ? '✕' : '·'),
                        style: TextStyle(
                            fontSize: 15, fontWeight: FontWeight.w800, color: color)),
                  ]),
                ),
              );
            },
          ),
          if (miss.isNotEmpty) ...[
            const SizedBox(height: 14),
            ResumeCard(
              title: '틀린 ${miss.length}문항 다시 풀기',
              subtitle: '해설을 보며 하나씩',
              onTap: () => Navigator.of(context)
                  .push(MaterialPageRoute(builder: (_) => QuestionScreen(pool: miss))),
            ),
          ],
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
