library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../theme.dart';
import '../widgets.dart';
import 'exam_detail_screen.dart';

class ExamsScreen extends StatelessWidget {
  const ExamsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final repo = Repo.instance;
    final rounds = repo.bank.rounds;

    return Scaffold(
      appBar: AppBar(title: const Text('모의고사')),
      body: ListenableBuilder(
        listenable: Store.instance,
        builder: (context, _) {
          final store = Store.instance;
          final sit = store.sit;
          if (rounds.isEmpty) {
            return const EmptyState(
                title: '회차가 없습니다', body: '문항이 회차로 묶이면 여기에 나옵니다.');
          }
          return ListView(
            padding: const EdgeInsets.all(14),
            children: [
              if (sit != null)
                ResumeCard(
                  title: '「${repo.round(sit.tag)?.title ?? sit.tag}」 푸는 중',
                  subtitle: '${sit.ans.length}/${repo.round(sit.tag)?.n ?? 0}문항'
                      '${sitLeft(sit) > 0 ? " · 남은 시간 ${mmss(sitLeft(sit))}" : " — 시간이 다 됐습니다"}',
                  onTap: () => _open(context, sit.tag),
                ),
              SectionTitle('회차 ${rounds.length}개'),
              ...rounds.map((r) {
                final best = store.best(r.tag);
                final hist = store.history(r.tag);
                return RowTile(
                  title: r.title,
                  subtitle: '${r.brand}\n${r.n}문항 · ${r.min}분 · '
                      '${hist.isEmpty ? "아직 응시하지 않았습니다" : "${hist.length}회 응시 · 최고 ${(best! * 100).round()}점"}',
                  trailing: best == null
                      ? null
                      : Text('${(best * 100).round()}점',
                          style: TextStyle(
                              color: best >= 0.8
                                  ? AppColors.of(context).ok
                                  : AppColors.of(context).dim,
                              fontWeight: FontWeight.w800)),
                  onTap: () => _open(context, r.tag),
                );
              }),
              const SizedBox(height: 10),
              Text('실제 시험처럼 시간을 재고, 푸는 동안 정답을 보여 주지 않습니다. '
                  '제출해야 채점하고 그때 오답노트와 복습에 들어갑니다.',
                  style: TextStyle(color: AppColors.of(context).faint, fontSize: 12.5)),
            ],
          );
        },
      ),
    );
  }

  void _open(BuildContext context, String tag) {
    Navigator.of(context)
        .push(MaterialPageRoute(builder: (_) => ExamDetailScreen(tag: tag)));
  }
}
