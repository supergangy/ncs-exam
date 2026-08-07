library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../theme.dart';
import '../widgets.dart';
import '../html_view.dart';
import 'question_screen.dart';

class _Hit {
  final Item it;
  final String where;
  final String? snip;
  _Hit(this.it, this.where, this.snip);
}

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});
  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _ctl = TextEditingController();
  String _q = '';

  @override
  void dispose() {
    _ctl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final q = _q.trim();
    final hits = q.isEmpty ? const <_Hit>[] : _search(q);

    return Scaffold(
      appBar: AppBar(
        title: TextField(
          controller: _ctl,
          autofocus: true,
          textInputAction: TextInputAction.search,
          decoration: const InputDecoration(
              border: InputBorder.none, hintText: '발문 · 선지 · 해설 · 키워드'),
          onChanged: (v) => setState(() => _q = v),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          if (q.isEmpty)
            const EmptyState(title: '무엇을 찾을까요', body: '「교착」「B+트리」「사자성어」처럼 적어 보세요.')
          else if (hits.isEmpty)
            EmptyState(title: '「$q」 결과가 없습니다', body: '다른 검색어를 시도해 보세요.')
          else ...[
            SectionTitle('${hits.length}문항'),
            for (final h in hits.take(60))
              RowTile(
                title: snippet(h.it.st, 60),
                subtitle: h.where == 'stem'
                    ? '${h.it.sj} · ${h.it.ty}'
                    : '${h.it.sj} · ${h.it.ty}\n${h.where} — ${h.snip ?? ""}',
                onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => QuestionScreen(pool: [h.it]))),
              ),
            if (hits.length > 60)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text('앞의 60개만 보입니다. 검색어를 좁혀 보세요.',
                    style: TextStyle(color: c.faint, fontSize: 12.5)),
              ),
          ],
        ],
      ),
    );
  }

  List<_Hit> _search(String q) {
    final n = q.toLowerCase();
    final repo = Repo.instance;
    bool has(String? s) => plainText(s).toLowerCase().contains(n);
    String around(String? s, {int pad = 24, int len = 70}) {
      final t = plainText(s).replaceAll(RegExp(r'\s+'), ' ').trim();
      final at = t.toLowerCase().indexOf(n);
      if (at < 0) return t.length > len ? t.substring(0, len) : t;
      final start = (at - pad).clamp(0, t.length);
      final end = (start + len).clamp(0, t.length);
      return '${start > 0 ? "…" : ""}${t.substring(start, end).trim()}';
    }

    final hits = <_Hit>[];
    for (final it in repo.bank.items) {
      if (has(it.st)) {
        hits.add(_Hit(it, 'stem', null));
        continue;
      }
      final ci = it.ch.indexWhere(has);
      if (ci >= 0) {
        hits.add(_Hit(it, '선지 ${circ[ci]}', around(it.ch[ci])));
        continue;
      }
      if (has(it.ty) || has(it.sj)) {
        hits.add(_Hit(it, '분류', '${it.sj} · ${it.ty}'));
        continue;
      }
      var kwIdx = -1;
      for (final k in it.kw) {
        if (repo.kwName(k).toLowerCase().contains(n)) {
          kwIdx = k;
          break;
        }
      }
      if (kwIdx >= 0) {
        hits.add(_Hit(it, '키워드', repo.kwName(kwIdx)));
        continue;
      }
      if (it.mt != null && has(it.mt)) {
        hits.add(_Hit(it, '자료', around(it.mt)));
        continue;
      }
      if (it.pg != null && has(repo.passage(it.pg!).body)) {
        hits.add(_Hit(it, '지문', around(repo.passage(it.pg!).body)));
        continue;
      }
      if (it.ex != null && has(it.ex)) {
        hits.add(_Hit(it, '해설', around(it.ex)));
        continue;
      }
      final ei = (it.ea ?? const <String>[]).indexWhere(has);
      if (ei >= 0) hits.add(_Hit(it, '선지 단평', around(it.ea![ei])));
    }
    return hits;
  }
}
