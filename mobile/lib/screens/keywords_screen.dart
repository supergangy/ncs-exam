library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../theme.dart';
import '../widgets.dart';
import 'question_screen.dart';

class KeywordsScreen extends StatelessWidget {
  const KeywordsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final repo = Repo.instance;

    // 과목은 불러올 때 이미 색인해 뒀다. 여기서 키워드 305개 × 문항 426개를
    // 그때그때 돌면 13만 번이라 화면이 멈춘다.
    final groups = <String, List<MapEntry<int, KeywordEntry>>>{};
    for (var idx = 0; idx < repo.bank.keywords.length; idx++) {
      (groups[repo.kwSubject(idx)] ??= []).add(MapEntry(idx, repo.bank.keywords[idx]));
    }
    final sorted = groups.entries.toList()
      ..sort((a, b) => b.value.length.compareTo(a.value.length));
    for (final e in sorted) {
      e.value.sort((a, b) =>
          b.value.n != a.value.n ? b.value.n.compareTo(a.value.n) : a.value.t.compareTo(b.value.t));
    }

    return Scaffold(
      appBar: AppBar(title: const Text('키워드')),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          Text('문항을 가로질러 묶는 용어입니다. 과목이 달라도 같은 개념이면 함께 나옵니다.',
              style: TextStyle(color: c.faint, fontSize: 12.5)),
          for (final e in sorted) ...[
            SectionTitle('${e.key} · ${e.value.length}개'),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final ke in e.value)
                  ChipButton(
                    label: ke.value.t,
                    count: ke.value.n,
                    onTap: () => Navigator.of(context).push(MaterialPageRoute(
                        builder: (_) => QuestionScreen(
                            title: ke.value.t, pool: repo.filter(kw: ke.key)))),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
