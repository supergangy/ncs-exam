library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../theme.dart';
import '../widgets.dart';
import '../html_view.dart';
import 'question_screen.dart';

class ReviewScreen extends StatelessWidget {
  const ReviewScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final repo = Repo.instance;
    return Scaffold(
      appBar: AppBar(title: const Text('복습')),
      body: ListenableBuilder(
        listenable: Store.instance,
        builder: (context, _) {
          final c = AppColors.of(context);
          final store = Store.instance;
          final ids = repo.bank.items.map((i) => i.id);
          final due = store.dueIds(ids);

          if (due.isEmpty) {
            final d = store.nextDueInDays(ids);
            return EmptyState(
              title: '지금 복습할 것이 없습니다',
              body: d == null
                  ? '한 문제라도 풀면 복습 일정이 잡힙니다.'
                  : '다음 복습은 ${d <= 0 ? "곧" : "$d일 뒤"}입니다.',
            );
          }

          return ListView(
            padding: const EdgeInsets.all(14),
            children: [
              ResumeCard(
                title: '복습 ${due.length}문항 시작',
                subtitle: '맞히면 다음 복습이 뒤로 밀립니다',
                onTap: () {
                  final pool = due.map(repo.byId).whereType<Item>().toList();
                  Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => QuestionScreen(title: '복습', pool: pool)));
                },
              ),
              const SectionTitle('오늘 볼 것'),
              for (final id in due)
                if (repo.byId(id) case final it?)
                  RowTile(
                    title: snippet(it.st, 60),
                    subtitle: '${it.sj} · ${it.ty}',
                    trailing: Text(
                      (store.srs[id]?.i ?? 0) > 0 ? '${store.srs[id]!.i}일 간격' : '새로',
                      style: TextStyle(color: c.faint, fontSize: 12.5),
                    ),
                    onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => QuestionScreen(pool: [it]))),
                  ),
            ],
          );
        },
      ),
    );
  }
}
