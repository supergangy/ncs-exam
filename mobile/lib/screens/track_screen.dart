library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../pool_filter.dart';
import '../store.dart';
import '../widgets.dart';
import 'subject_screen.dart';
import 'question_screen.dart';

class TrackScreen extends StatefulWidget {
  final String trackId;
  const TrackScreen({super.key, required this.trackId});
  @override
  State<TrackScreen> createState() => _TrackScreenState();
}

class _TrackScreenState extends State<TrackScreen> {
  PoolFilter _filter = PoolFilter.all;

  @override
  Widget build(BuildContext context) {
    final repo = Repo.instance;
    final t = repo.track(widget.trackId);
    if (t == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('직렬')),
        body: const EmptyState(
            title: '직렬을 찾을 수 없습니다', body: '앱을 업데이트하면서 바뀌었을 수 있습니다.'),
      );
    }
    final all = repo.filter(tr: widget.trackId);

    return Scaffold(
      appBar: AppBar(title: Text(t.name)),
      body: ListenableBuilder(
        listenable: Store.instance,
        builder: (context, _) {
          final pool = _filter.apply(all);
          final p = computeProgress(pool);
          return ListView(
            padding: const EdgeInsets.all(14),
            children: [
              PoolFilterBar(
                items: all, value: _filter,
                onChanged: (f) => setState(() => _filter = f),
              ),
              if (pool.isEmpty)
                FilterEmpty(_filter)
              else ...[
                ResumeCard(
                  title: _filter == PoolFilter.all
                      ? '${t.name} 이어서 풀기'
                      : '${_filter.label} ${pool.length}문항 풀기',
                  subtitle: _filter == PoolFilter.all
                      ? '안 푼 문제 ${p.n - p.done}개 · 전체 ${p.n}문항'
                      : progText(p),
                  onTap: () {
                    final start = _filter == PoolFilter.all
                        ? PoolFilter.untried.applyOrAll(all)
                        : List.of(pool);
                    start.shuffle();
                    Navigator.of(context).push(MaterialPageRoute(
                        builder: (_) => QuestionScreen(title: t.name, pool: start)));
                  },
                ),
                const SectionTitle('과목'),
                ...repo.subjects(widget.trackId).map((s) {
                  final items = _filter.apply(repo.filter(tr: widget.trackId, sj: s.n));
                  final sp = computeProgress(items);
                  return RowTile(
                    title: s.n,
                    subtitle: _filter == PoolFilter.all
                        ? '${progText(sp)} · 유형 ${repo.typeGroups(widget.trackId, s.n).length}종'
                        : '「${_filter.label}」 ${items.length}문항',
                    progress: items.isEmpty ? null : sp,
                    onTap: () => Navigator.of(context).push(MaterialPageRoute(
                        builder: (_) =>
                            SubjectScreen(trackId: widget.trackId, subject: s.n))),
                  );
                }),
              ],
            ],
          );
        },
      ),
    );
  }
}
