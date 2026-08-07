library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../widgets.dart';
import 'question_screen.dart';

class SubjectScreen extends StatelessWidget {
  final String trackId, subject;
  const SubjectScreen({super.key, required this.trackId, required this.subject});

  @override
  Widget build(BuildContext context) {
    final repo = Repo.instance;
    final all = repo.filter(tr: trackId, sj: subject);
    final p = computeProgress(all);
    final types = repo.types(trackId, subject);

    return Scaffold(
      appBar: AppBar(title: Text(subject)),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          ResumeCard(
            title: '$subject 전체 풀기', subtitle: progText(p),
            onTap: () => Navigator.of(context).push(MaterialPageRoute(
                builder: (_) => QuestionScreen(pool: List.of(all)..shuffle()))),
          ),
          SectionTitle('유형 ${types.length}종'),
          ...types.map((t) {
            final tp = computeProgress(repo.filter(tr: trackId, sj: subject, ty: t.n));
            return RowTile(
              title: t.n, subtitle: progText(tp), progress: tp,
              onTap: () => Navigator.of(context).push(MaterialPageRoute(
                  builder: (_) => QuestionScreen(
                      title: t.n,
                      pool: repo.filter(tr: trackId, sj: subject, ty: t.n)))),
            );
          }),
        ],
      ),
    );
  }
}
