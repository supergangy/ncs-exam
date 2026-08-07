library;

import 'dart:async';
import 'package:flutter/material.dart';
import '../repo.dart';
import '../theme.dart';
import '../widgets.dart';
import '../html_view.dart';
import 'question_screen.dart';

/// 검색어는 화면을 닫아도 남는다 — 결과를 열어 보고 돌아와 다시 치는 일이 없게.
String _lastQuery = '';

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
  late final TextEditingController _ctl;
  Timer? _debounce;
  String _q = _lastQuery;
  List<_Hit> _hits = const [];

  @override
  void initState() {
    super.initState();
    _ctl = TextEditingController(text: _lastQuery);
    if (_q.isNotEmpty) _hits = _search(_q);
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _ctl.dispose();
    super.dispose();
  }

  void _onChanged(String v) {
    _lastQuery = v;
    _debounce?.cancel();
    // 글자마다 훑지 않는다. 빨리 치는 동안은 기다렸다가 멈추면 한 번만 돈다.
    _debounce = Timer(const Duration(milliseconds: 180), () {
      if (!mounted) return;
      setState(() {
        _q = v;
        _hits = v.trim().isEmpty ? const [] : _search(v.trim());
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final q = _q.trim();

    return Scaffold(
      appBar: AppBar(
        title: TextField(
          controller: _ctl,
          autofocus: true,
          textInputAction: TextInputAction.search,
          decoration: const InputDecoration(
              border: InputBorder.none, hintText: '발문 · 선지 · 해설 · 키워드'),
          onChanged: _onChanged,
        ),
        actions: [
          if (_ctl.text.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.clear),
              onPressed: () { _ctl.clear(); _onChanged(''); },
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          if (q.isEmpty)
            const EmptyState(title: '무엇을 찾을까요', body: '「교착」「B+트리」「사자성어」처럼 적어 보세요.')
          else if (_hits.isEmpty)
            EmptyState(title: '「$q」 결과가 없습니다', body: '다른 검색어를 시도해 보세요.')
          else ...[
            SectionTitle('${_hits.length}문항'),
            for (final h in _hits.take(60)) _hitRow(context, c, h, q),
            if (_hits.length > 60)
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

  Widget _hitRow(BuildContext context, AppColors c, _Hit h, String q) {
    final rd = h.it.rd == null
        ? ''
        : ' · ${Repo.instance.round(h.it.rd!)?.title ?? h.it.rd} ${h.it.no}번';
    return InkWell(
      onTap: () => Navigator.of(context)
          .push(MaterialPageRoute(builder: (_) => QuestionScreen(pool: [h.it]))),
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
          color: c.card, borderRadius: BorderRadius.circular(14),
          border: Border.all(color: c.line),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${h.it.sj} · ${h.it.ty}$rd',
              style: TextStyle(fontSize: 12, color: c.faint)),
          const SizedBox(height: 3),
          _Highlighted(text: plainText(h.it.st), query: q,
              style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w600, color: c.ink)),
          if (h.where != 'stem' && h.snip != null) ...[
            const SizedBox(height: 3),
            _Highlighted(text: '${h.where} — ${h.snip}', query: q,
                style: TextStyle(fontSize: 12.5, color: c.dim)),
          ],
        ]),
      ),
    );
  }

  /// 미리 펴 둔 색인(`Repo.searchDocs`)에 대고 문자열 비교만 한다.
  List<_Hit> _search(String q) {
    final n = q.toLowerCase();
    final hits = <_Hit>[];
    for (final d in Repo.instance.searchDocs) {
      if (d.stem.contains(n)) {
        hits.add(_Hit(d.item, 'stem', null));
        continue;
      }
      final ci = d.item.ch.indexWhere((c) => plainText(c).toLowerCase().contains(n));
      if (ci >= 0) {
        hits.add(_Hit(d.item, '선지 ${circ[ci]}', _around(plainText(d.item.ch[ci]), n)));
        continue;
      }
      if (d.cls.contains(n)) {
        hits.add(_Hit(d.item, '분류', '${d.item.sj} · ${d.item.ty}'));
        continue;
      }
      if (d.keywords.contains(n)) {
        final kw = d.item.kw.firstWhere(
            (k) => Repo.instance.kwName(k).toLowerCase().contains(n),
            orElse: () => -1);
        hits.add(_Hit(d.item, '키워드', kw >= 0 ? Repo.instance.kwName(kw) : ''));
        continue;
      }
      if (d.material.contains(n)) {
        hits.add(_Hit(d.item, '자료', _around(plainText(d.item.mt), n)));
        continue;
      }
      if (d.passage.contains(n)) {
        final body = d.item.pg == null
            ? '' : plainText(Repo.instance.passage(d.item.pg!)?.body);
        hits.add(_Hit(d.item, '지문', _around(body, n)));
        continue;
      }
      if (d.explain.contains(n)) {
        hits.add(_Hit(d.item, '해설', _around(plainText(d.item.ex), n)));
        continue;
      }
      if (d.each.contains(n)) {
        final ea = (d.item.ea ?? const <String>[])
            .map(plainText)
            .firstWhere((e) => e.toLowerCase().contains(n), orElse: () => '');
        hits.add(_Hit(d.item, '선지 단평', _around(ea, n)));
      }
    }
    return hits;
  }

  String _around(String t, String n, {int pad = 24, int len = 70}) {
    final at = t.toLowerCase().indexOf(n);
    if (at < 0) return t.length > len ? t.substring(0, len) : t;
    final start = (at - pad).clamp(0, t.length);
    final end = (start + len).clamp(0, t.length);
    return '${start > 0 ? "…" : ""}${t.substring(start, end).trim()}';
  }
}

/// 찾은 말에 표시를 씌운다. 결과가 60줄이면 어디에서 걸렸는지 눈으로 못 찾는다.
class _Highlighted extends StatelessWidget {
  final String text, query;
  final TextStyle style;
  const _Highlighted({required this.text, required this.query, required this.style});

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final i = text.toLowerCase().indexOf(query.toLowerCase());
    if (query.isEmpty || i < 0) {
      return Text(text, maxLines: 3, overflow: TextOverflow.ellipsis, style: style);
    }
    return Text.rich(
      TextSpan(children: [
        TextSpan(text: text.substring(0, i), style: style),
        TextSpan(
          text: text.substring(i, i + query.length),
          style: style.copyWith(backgroundColor: c.warnSoft, color: c.warn,
              fontWeight: FontWeight.w800),
        ),
        TextSpan(text: text.substring(i + query.length), style: style),
      ]),
      maxLines: 3,
      overflow: TextOverflow.ellipsis,
    );
  }
}
