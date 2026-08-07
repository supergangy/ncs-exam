library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../theme.dart';
import '../widgets.dart';
import '../html_view.dart';
import 'question_screen.dart';

class ReviewScreen extends StatefulWidget {
  const ReviewScreen({super.key});
  @override
  State<ReviewScreen> createState() => _ReviewScreenState();
}

class _ReviewScreenState extends State<ReviewScreen> {
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final repo = Repo.instance;
    final due = Store.instance.dueIds(repo.bank.items.map((i) => i.id));

    return Scaffold(
      appBar: AppBar(title: const Text('복습')),
      body: due.isEmpty
          ? ListView(padding: const EdgeInsets.all(14), children: [_empty(c, repo)])
          : ListView(
              padding: const EdgeInsets.all(14),
              children: [
                ResumeCard(
                  title: '복습 ${due.length}문항 시작',
                  subtitle: '맞히면 다음 복습이 뒤로 밀립니다',
                  onTap: () {
                    final pool = due.map((id) => repo.byId(id)).whereType<Item>().toList();
                    Navigator.of(context)
                        .push(MaterialPageRoute(builder: (_) => QuestionScreen(pool: pool)))
                        .then((_) => setState(() {}));
                  },
                ),
                const SectionTitle('오늘 볼 것'),
                for (final id in due)
                  if (repo.byId(id) case final it?)
                    RowTile(
                      title: snippet(it.st, 60),
                      subtitle: '${it.sj} · ${it.ty}',
                      trailing: Text(
                        (Store.instance.srs[id]?.i ?? 0) > 0
                            ? '${Store.instance.srs[id]!.i}일 간격'
                            : '새로',
                        style: TextStyle(color: c.faint, fontSize: 12.5),
                      ),
                      onTap: () => Navigator.of(context)
                          .push(MaterialPageRoute(builder: (_) => QuestionScreen(pool: [it])))
                          .then((_) => setState(() {})),
                    ),
              ],
            ),
    );
  }

  Widget _empty(AppColors c, Repo repo) {
    String msg = '한 문제라도 풀면 복습 일정이 잡힙니다.';
    final withSrs = repo.bank.items.where((i) => Store.instance.srs[i.id] != null).toList()
      ..sort((a, b) =>
          Store.instance.srs[a.id]!.due.compareTo(Store.instance.srs[b.id]!.due));
    if (withSrs.isNotEmpty) {
      final due = Store.instance.srs[withSrs.first.id]!.due;
      final d = ((due - DateTime.now().millisecondsSinceEpoch) / 86400000).ceil();
      msg = '다음 복습은 ${d <= 0 ? "곧" : "$d일 뒤"}입니다.';
    }
    return EmptyState(title: '지금 복습할 것이 없습니다', body: msg);
  }
}
