library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../widgets.dart';
import 'subject_screen.dart';
import 'question_screen.dart';

class TrackScreen extends StatelessWidget {
  final String trackId;
  const TrackScreen({super.key, required this.trackId});

  @override
  Widget build(BuildContext context) {
    final repo = Repo.instance;
    final t = repo.track(trackId);
    if (t == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('직렬')),
        body: const EmptyState(title: '직렬을 찾을 수 없습니다', body: '앱을 업데이트하면서 바뀌었을 수 있습니다.'),
      );
    }
    final all = repo.filter(tr: trackId);

    return Scaffold(
      appBar: AppBar(title: Text(t.name)),
      body: ListenableBuilder(
        listenable: Store.instance,
        builder: (context, _) {
          final p = computeProgress(all);
          return ListView(
            padding: const EdgeInsets.all(14),
            children: [
              ResumeCard(
                title: '${t.name} 이어서 풀기',
                subtitle: '안 푼 문제 ${p.n - p.done}개 · 전체 ${p.n}문항',
                onTap: () {
                  final fresh =
                      all.where((i) => !Store.instance.tried(i.id)).toList();
                  final pool = fresh.isNotEmpty ? fresh : List.of(all);
                  pool.shuffle();
                  Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => QuestionScreen(pool: pool)));
                },
              ),
              const SectionTitle('과목'),
              ...repo.subjects(trackId).map((s) {
                final sp = computeProgress(repo.filter(tr: trackId, sj: s.n));
                return RowTile(
                  title: s.n,
                  subtitle: '${progText(sp)} · 유형 ${repo.types(trackId, s.n).length}종',
                  progress: sp,
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => SubjectScreen(trackId: trackId, subject: s.n))),
                );
              }),
            ],
          );
        },
      ),
    );
  }
}
