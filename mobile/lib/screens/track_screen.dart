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
    final t = repo.track(trackId)!;
    final all = repo.filter(tr: trackId);
    final p = computeProgress(all);

    return Scaffold(
      appBar: AppBar(title: Text(t.name)),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          ResumeCard(
            title: '${t.name} 이어서 풀기',
            subtitle: '안 푼 문제 ${p.n - p.done}개 · 전체 ${p.n}문항',
            onTap: () {
              final pool = all.where((i) => !Store.instance.tried(i.id)).toList();
              Navigator.of(context).push(MaterialPageRoute(
                  builder: (_) => QuestionScreen(pool: (pool.isNotEmpty ? pool : all)..shuffle())));
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
      ),
    );
  }
}
