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
import 'search_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final repo = Repo.instance;
    return Scaffold(
      appBar: AppBar(
        title: const Text('기출은행'),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            tooltip: '검색',
            onPressed: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => const SearchScreen())),
          ),
        ],
      ),
      // 기록이 바뀌면 스스로 다시 그린다 — 다른 탭에서 문제를 풀어도 여기 숫자가 따라온다.
      body: ListenableBuilder(
        listenable: Store.instance,
        builder: (context, _) {
          final store = Store.instance;
          final all = computeProgress(repo.bank.items);
          final ids = repo.bank.items.map((i) => i.id);
          final due = store.dueIds(ids).length;
          final wrong = store.wrongCount(ids);
          final sit = store.sit;

          return ListView(
            padding: const EdgeInsets.all(14),
            children: [
              if (sit != null)
                _SitResume(sit: sit)
              else if (due > 0)
                ResumeCard(
                  title: '복습할 문제 $due개',
                  subtitle: '간격을 두고 다시 풀면 오래 남습니다',
                  onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const ReviewScreen())),
                )
              else if (wrong > 0)
                ResumeCard(
                  title: '오답 $wrong개가 남아 있습니다',
                  subtitle: '틀린 것부터 다시 풀어 보세요',
                  onTap: () => Navigator.of(context)
                      .push(MaterialPageRoute(builder: (_) => const WrongScreen())),
                ),
              if (repo.bank.rounds.isNotEmpty) ...[
                const SectionTitle('모의고사'),
                RowTile(
                  title: '회차 ${repo.bank.rounds.length}개',
                  subtitle: _roundsSub(repo, store),
                  onTap: () => Navigator.of(context)
                      .push(MaterialPageRoute(builder: (_) => const ExamsScreen())),
                ),
              ],
              const SectionTitle('직렬'),
              ...repo.bank.tracks.map((t) {
                final p = computeProgress(repo.filter(tr: t.id));
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
                  final fresh =
                      repo.bank.items.where((i) => !store.tried(i.id)).toList();
                  final pool = fresh.isNotEmpty ? fresh : List.of(repo.bank.items);
                  pool.shuffle();
                  Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => QuestionScreen(pool: pool)));
                },
              ),
              RowTile(
                title: '전체에서 무작위', subtitle: '${all.n}문항 가운데 섞어서',
                onTap: () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => QuestionScreen(pool: List.of(repo.bank.items)..shuffle()))),
              ),
            ],
          );
        },
      ),
    );
  }

  String _roundsSub(Repo repo, Store store) {
    final taken = repo.bank.rounds.where((r) => store.history(r.tag).isNotEmpty).length;
    if (taken == 0) return '시간을 재고 실제 시험처럼';
    return '시간을 재고 실제 시험처럼 · $taken회차 응시함';
  }
}

/// 진행 중인 회차 — 남은 시간까지 보여 준다. 목록에서 시계가 안 보이면
/// 몇 분 남았는지 알려고 들어가 봐야 한다.
class _SitResume extends StatefulWidget {
  final SitState sit;
  const _SitResume({required this.sit});
  @override
  State<_SitResume> createState() => _SitResumeState();
}

class _SitResumeState extends State<_SitResume> {
  @override
  Widget build(BuildContext context) {
    final repo = Repo.instance;
    final r = repo.round(widget.sit.tag);
    final left = sitLeft(widget.sit);
    return ResumeCard(
      title: '「${r?.title ?? widget.sit.tag}」 푸는 중',
      subtitle: '${widget.sit.ans.length}/${r?.n ?? repo.roundItems(widget.sit.tag).length}문항'
          '${left > 0 ? " · 남은 시간 ${mmss(left)}" : " — 시간이 다 됐습니다"}',
      onTap: () => Navigator.of(context)
          .push(MaterialPageRoute(builder: (_) => ExamDetailScreen(tag: widget.sit.tag)))
          .then((_) { if (mounted) setState(() {}); }),
    );
  }
}
