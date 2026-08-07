library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../widgets.dart';
import 'question_screen.dart';

class SubjectScreen extends StatelessWidget {
  final String trackId, subject;
  const SubjectScreen({super.key, required this.trackId, required this.subject});

  @override
  Widget build(BuildContext context) {
    final repo = Repo.instance;
    final all = repo.filter(tr: trackId, sj: subject);
    final types = repo.types(trackId, subject);

    return Scaffold(
      appBar: AppBar(title: Text(subject)),
      body: ListenableBuilder(
        listenable: Store.instance,
        builder: (context, _) {
          final p = computeProgress(all);
          return ListView(
            padding: const EdgeInsets.all(14),
            children: [
              ResumeCard(
                title: '$subject 이어서 풀기', subtitle: progText(p),
                onTap: () {
                  // 웹판과 같게 **안 푼 것부터** 낸다. 그냥 섞으면 이미 맞힌 문제가 다시 나온다.
                  final fresh =
                      all.where((i) => !Store.instance.tried(i.id)).toList();
                  final pool = fresh.isNotEmpty ? fresh : List.of(all);
                  pool.shuffle();
                  Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => QuestionScreen(title: subject, pool: pool)));
                },
              ),
              SectionTitle('유형 ${types.length}종'),
              ...types.map((t) {
                final items = repo.filter(tr: trackId, sj: subject, ty: t.n);
                final tp = computeProgress(items);
                return RowTile(
                  title: t.n, subtitle: progText(tp), progress: tp,
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => QuestionScreen(title: t.n, pool: List.of(items)))),
                );
              }),
            ],
          );
        },
      ),
    );
  }
}
