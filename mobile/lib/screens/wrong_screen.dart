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
import '../html_view.dart';
import 'question_screen.dart';

class WrongScreen extends StatefulWidget {
  const WrongScreen({super.key});
  @override
  State<WrongScreen> createState() => _WrongScreenState();
}

class _WrongScreenState extends State<WrongScreen> {
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final repo = Repo.instance;
    final wrong = repo.bank.items.where((i) => Store.instance.isWrong(i.id)).toList();

    return Scaffold(
      appBar: AppBar(title: const Text('오답노트')),
      body: wrong.isEmpty
          ? ListView(padding: const EdgeInsets.all(14), children: const [
              EmptyState(
                title: '오답이 없습니다',
                body: '틀린 문제가 여기 모입니다.\n다시 풀어 맞히면 목록에서 빠집니다.',
              ),
            ])
          : ListView(
              padding: const EdgeInsets.all(14),
              children: [
                ResumeCard(
                  title: '오답 ${wrong.length}개 다시 풀기',
                  subtitle: '맞히면 목록에서 사라집니다',
                  onTap: () => Navigator.of(context)
                      .push(MaterialPageRoute(builder: (_) => QuestionScreen(pool: wrong)))
                      .then((_) => setState(() {})),
                ),
                const SizedBox(height: 8),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    onPressed: () => _export(wrong),
                    child: const Text('오답노트 PDF 용으로 내보내기'),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    '내보낸 파일로 python tools/wrongnote_pdf.py 를 돌리면 '
                    '문제와 해설이 함께 실린 인쇄본이 나옵니다.',
                    style: TextStyle(color: c.faint, fontSize: 12.5),
                  ),
                ),
                const SectionTitle('틀린 문제'),
                ...wrong.map((i) {
                  final cnt = Store.instance.att[i.id]?.where((a) => !a.ok).length ?? 0;
                  return RowTile(
                    title: snippet(i.st, 60),
                    subtitle: '${i.sj} · ${i.ty}',
                    trailing:
                        Text('$cnt회 틀림', style: TextStyle(color: c.faint, fontSize: 12.5)),
                    onTap: () => Navigator.of(context)
                        .push(MaterialPageRoute(builder: (_) => QuestionScreen(pool: [i])))
                        .then((_) => setState(() {})),
                  );
                }),
              ],
            ),
    );
  }

  Future<void> _export(List<Item> wrong) async {
    final ids = wrong.map((i) => i.id).toList();
    final now = DateTime.now();
    final data = {'v': 1, 'at': now.toIso8601String(), 'n': ids.length, 'ids': ids};
    final dir = await getTemporaryDirectory();
    final stamp = '${now.year}${now.month.toString().padLeft(2, '0')}'
        '${now.day.toString().padLeft(2, '0')}';
    final file = File('${dir.path}/wrongnote-$stamp.json');
    await file.writeAsString(const JsonEncoder.withIndent('  ').convert(data));
    if (!mounted) return;
    await Share.shareXFiles([XFile(file.path)],
        text: '오답노트 내보내기 — tools/wrongnote_pdf.py 에 전달하세요');
  }
}
