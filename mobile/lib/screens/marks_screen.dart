library;

import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import '../repo.dart';
import '../store.dart';
import '../theme.dart';
import '../widgets.dart';
import 'question_screen.dart';

class MarksScreen extends StatefulWidget {
  const MarksScreen({super.key});
  @override
  State<MarksScreen> createState() => _MarksScreenState();
}

class _MarksScreenState extends State<MarksScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('북마크 · 확인 필요')),
      body: ListenableBuilder(
        listenable: Store.instance,
        builder: (context, _) {
          final c = AppColors.of(context);
          final flags = Store.instance.marked(flag: true);
          final books = Store.instance.marked(flag: false);

          if (flags.isEmpty && books.isEmpty) {
            return const EmptyState(
              title: '표시한 문항이 없습니다',
              body: '문제를 풀다가 ☆ 로 담아 두거나,\n이상한 점이 보이면 ⚑ 로 표시해 두세요.',
            );
          }

          return ListView(
            padding: const EdgeInsets.all(14),
            children: [
              if (flags.isNotEmpty) ...[
                SectionTitle('확인 필요 ${flags.length}개'),
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    '이상하다고 표시한 문항입니다. 아래에서 내보내 주시면 문항을 고칠 수 있습니다.',
                    style: TextStyle(color: c.faint, fontSize: 12.5),
                  ),
                ),
                ..._rows(flags),
              ],
              if (books.isNotEmpty) ...[
                SectionTitle('북마크 ${books.length}개'),
                ..._rows(books),
              ],
              const SizedBox(height: 14),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                    onPressed: _export, child: const Text('표시 목록 내보내기 (.json)')),
              ),
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  '내보낸 파일을 전달하시면 어느 문항의 무엇이 문제인지 그대로 읽힙니다. '
                  '문항 번호·과목·메모가 들어갑니다.',
                  style: TextStyle(color: c.faint, fontSize: 12.5),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  List<Widget> _rows(List<String> ids) {
    final repo = Repo.instance;
    final rows = <Widget>[];
    for (final id in ids) {
      final it = repo.byId(id);
      if (it == null) continue;
      final m = Store.instance.markOf(id);
      final rk = Store.instance.admin ? (repo.admin?[id]?.rk) : null;
      rows.add(_MarkRow(item: it, memo: m.memo, risk: rk));
    }
    return rows;
  }

  Future<void> _export() async {
    final repo = Repo.instance;
    final items = Store.instance.mark.entries.map((e) {
      final it = repo.byId(e.key);
      final o = <String, dynamic>{
        'id': e.key,
        'sj': it?.sj ?? '?',
        'ty': it?.ty ?? '?',
        'stem': it != null ? Repo.instance.line(it, 80) : '',
      };
      if (it?.rd != null) {
        o['round'] = it!.rd;
        o['no'] = it.no;
      }
      if (e.value.flag) o['flag'] = true;
      if (e.value.bookmark) o['bookmark'] = true;
      if (e.value.memo.isNotEmpty) o['memo'] = e.value.memo;
      final rk = repo.admin?[e.key]?.rk;
      if (rk != null) o['risk'] = rk;
      return o;
    }).toList();
    final now = DateTime.now();
    final data = {'v': 1, 'at': now.toIso8601String(), 'n': items.length, 'items': items};
    final stamp = '${now.year}${now.month.toString().padLeft(2, '0')}'
        '${now.day.toString().padLeft(2, '0')}';
    try {
      final dir = await getTemporaryDirectory();
      final file = File('${dir.path}/marks-$stamp.json');
      await file.writeAsString(const JsonEncoder.withIndent('  ').convert(data));
      await Share.shareXFiles([XFile(file.path)], text: '표시 목록 내보내기');
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('내보내지 못했습니다: $e')));
    }
  }
}

class _MarkRow extends StatelessWidget {
  final Item item;
  final String memo;
  final String? risk;
  const _MarkRow({required this.item, required this.memo, required this.risk});

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    return InkWell(
      onTap: () => Navigator.of(context)
          .push(MaterialPageRoute(builder: (_) => QuestionScreen(pool: [item]))),
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
          color: c.card, borderRadius: BorderRadius.circular(14),
          border: Border.all(color: c.line),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Text('${item.sj} · ${item.ty}',
                style: TextStyle(fontSize: 12, color: c.faint)),
            if (risk != null) ...[const SizedBox(width: 6), RiskBadge(risk!)],
          ]),
          const SizedBox(height: 3),
          Text(Repo.instance.line(item, 56),
              style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w600, color: c.ink)),
          if (memo.isNotEmpty)
            Container(
              margin: const EdgeInsets.only(top: 6),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
              decoration: BoxDecoration(
                color: c.warnSoft, borderRadius: BorderRadius.circular(8),
                border: Border(left: BorderSide(color: c.warn, width: 3)),
              ),
              child: Text(memo, style: TextStyle(fontSize: 12.5, color: c.ink)),
            ),
        ]),
      ),
    );
  }
}
