library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../widgets.dart';
import 'track_screen.dart';
import 'exams_screen.dart';
import 'exam_detail_screen.dart';
import 'question_screen.dart';
import 'review_screen.dart';
import 'wrong_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  Widget build(BuildContext context) {
    final repo = Repo.instance;
    final all = computeProgress(repo.bank.items);
    final due = Store.instance.dueIds(repo.bank.items.map((i) => i.id));
    final wrong = repo.bank.items.where((i) => Store.instance.isWrong(i.id)).length;
    final sit = Store.instance.sit;

    return Scaffold(
      appBar: AppBar(title: const Text('기출은행')),
      body: RefreshIndicator(
        onRefresh: () async => setState(() {}),
        child: ListView(
          padding: const EdgeInsets.all(14),
          children: [
            if (sit != null)
              ResumeCard(
                title: '「${repo.round(sit.tag)?.title ?? sit.tag}」 푸는 중',
                subtitle: '${sit.ans.length}/${repo.round(sit.tag)?.n ?? 0}문항',
                onTap: () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => ExamDetailScreen(tag: sit.tag))),
              )
            else if (due.isNotEmpty)
              ResumeCard(
                title: '복습할 문제 ${due.length}개',
                subtitle: '간격을 두고 다시 풀면 오래 남습니다',
                onTap: () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => const ReviewScreen())),
              )
            else if (wrong > 0)
              ResumeCard(
                title: '오답 $wrong개가 남아 있습니다',
                subtitle: '틀린 것부터 다시 풀어 보세요',
                onTap: () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => const WrongScreen())),
              ),
            if (repo.bank.rounds.isNotEmpty) ...[
              const SectionTitle('모의고사'),
              RowTile(
                title: '회차 ${repo.bank.rounds.length}개',
                subtitle: '시간을 재고 실제 시험처럼',
                onTap: () => Navigator.of(context)
                    .push(MaterialPageRoute(builder: (_) => const ExamsScreen())),
              ),
            ],
            const SectionTitle('직렬'),
            ...repo.bank.tracks.map((t) {
              final items = repo.filter(tr: t.id);
              final p = computeProgress(items);
              return HeroCard(
                title: t.name, subtitle: '${t.sub} · ${repo.subjects(t.id).length}과목',
                footer: '전체 ${p.n}문항 · 푼 것 ${p.done}'
                    '${p.done > 0 ? " · 정답률 ${p.rate}%" : ""}',
                progress: p,
                onTap: () => Navigator.of(context)
                    .push(MaterialPageRoute(builder: (_) => TrackScreen(trackId: t.id))),
              );
            }),
            const SectionTitle('무작위로'),
            RowTile(
              title: '안 푼 문제 이어서', subtitle: '아직 ${all.n - all.done}문항 남았습니다',
              onTap: () {
                final fresh = repo.bank.items.where((i) => !Store.instance.tried(i.id)).toList();
                final pool = fresh.isNotEmpty ? fresh : List.of(repo.bank.items)..shuffle();
                Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => QuestionScreen(pool: pool..shuffle())));
              },
            ),
            RowTile(
              title: '전체에서 무작위', subtitle: '${all.n}문항 가운데 섞어서',
              onTap: () => Navigator.of(context).push(MaterialPageRoute(
                  builder: (_) => QuestionScreen(pool: List.of(repo.bank.items)..shuffle()))),
            ),
          ],
        ),
      ),
    );
  }
}
