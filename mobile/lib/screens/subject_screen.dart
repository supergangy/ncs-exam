library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../pool_filter.dart';
import '../store.dart';
import '../theme.dart';
import '../widgets.dart';
import 'question_screen.dart';

class SubjectScreen extends StatefulWidget {
  final String trackId, subject;
  const SubjectScreen({super.key, required this.trackId, required this.subject});
  @override
  State<SubjectScreen> createState() => _SubjectScreenState();
}

class _SubjectScreenState extends State<SubjectScreen> {
  PoolFilter _filter = PoolFilter.all;

  @override
  Widget build(BuildContext context) {
    final repo = Repo.instance;
    final c = AppColors.of(context);
    final all = repo.filter(tr: widget.trackId, sj: widget.subject);
    final types = repo.types(widget.trackId, widget.subject);

    return Scaffold(
      appBar: AppBar(title: Text(widget.subject)),
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
                      ? '${widget.subject} 이어서 풀기'
                      : '${_filter.label} ${pool.length}문항 풀기',
                  subtitle: progText(p),
                  onTap: () {
                    // 「전체」일 때는 웹판과 같게 안 푼 것부터 낸다.
                    final start = _filter == PoolFilter.all
                        ? PoolFilter.untried.applyOrAll(all)
                        : List.of(pool);
                    start.shuffle();
                    Navigator.of(context).push(MaterialPageRoute(
                        builder: (_) =>
                            QuestionScreen(title: widget.subject, pool: start)));
                  },
                ),
                SectionTitle('유형 ${types.length}종'),
                ...types.map((t) {
                  final items = _filter
                      .apply(repo.filter(tr: widget.trackId, sj: widget.subject, ty: t.n));
                  final tp = computeProgress(items);
                  // 0건이어도 줄은 남긴다 — 감추면 유형이 사라진 줄 안다.
                  if (items.isEmpty) {
                    return Opacity(
                      opacity: 0.45,
                      child: RowTile(
                        title: t.n,
                        subtitle: '「${_filter.label}」 해당 없음',
                        trailing: Text('0', style: TextStyle(color: c.faint)),
                      ),
                    );
                  }
                  return RowTile(
                    title: t.n, subtitle: progText(tp), progress: tp,
                    onTap: () => Navigator.of(context).push(MaterialPageRoute(
                        builder: (_) =>
                            QuestionScreen(title: t.n, pool: List.of(items)))),
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
