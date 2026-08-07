library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../theme.dart';
import '../widgets.dart';
import 'exam_detail_screen.dart';

class ExamsScreen extends StatefulWidget {
  const ExamsScreen({super.key});
  @override
  State<ExamsScreen> createState() => _ExamsScreenState();
}

class _ExamsScreenState extends State<ExamsScreen> {
  @override
  Widget build(BuildContext context) {
    final rounds = Repo.instance.bank.rounds;
    final sit = Store.instance.sit;
    return Scaffold(
      appBar: AppBar(title: const Text('모의고사')),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          if (sit != null)
            ResumeCard(
              title: '「${Repo.instance.round(sit.tag)?.title ?? sit.tag}」 푸는 중',
              subtitle: '${sit.ans.length}/${Repo.instance.round(sit.tag)?.n ?? 0}문항',
              onTap: () => _open(context, sit.tag),
            ),
          SectionTitle('회차 ${rounds.length}개'),
          ...rounds.map((r) {
            final best = Store.instance.best(r.tag);
            final hist = Store.instance.history(r.tag);
            return RowTile(
              title: r.title,
              subtitle: '${r.brand}\n${r.n}문항 · ${r.min}분 · '
                  '${hist.isEmpty ? "아직 응시하지 않았습니다" : "${hist.length}회 응시 · 최고 ${(best! * 100).round()}점"}',
              onTap: () => _open(context, r.tag),
            );
          }),
          const SizedBox(height: 10),
          Text('실제 시험처럼 시간을 재고, 푸는 동안 정답을 보여 주지 않습니다. '
              '제출해야 채점하고 그때 오답노트와 복습에 들어갑니다.',
              style: TextStyle(color: AppColors.of(context).faint, fontSize: 12.5)),
        ],
      ),
    );
  }

  void _open(BuildContext context, String tag) {
    Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => ExamDetailScreen(tag: tag))).then((_) => setState(() {}));
  }
}
