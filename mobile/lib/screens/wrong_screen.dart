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
import '../pdf_note.dart';
import 'question_screen.dart';

class WrongScreen extends StatefulWidget {
  const WrongScreen({super.key});
  @override
  State<WrongScreen> createState() => _WrongScreenState();
}

class _WrongScreenState extends State<WrongScreen> {
  bool _busy = false;

  /// 문항이 많으면 WebView 가 그리는 데 몇 초 걸린다. 그동안 버튼을 잠근다.
  Future<void> _makePdf(List<Item> wrong) async {
    setState(() => _busy = true);
    try {
      await printNote(wrong, title: '오답노트');
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('PDF를 만들지 못했습니다: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final repo = Repo.instance;
    return Scaffold(
      appBar: AppBar(title: const Text('오답노트')),
      body: ListenableBuilder(
        listenable: Store.instance,
        builder: (context, _) {
          final c = AppColors.of(context);
          final store = Store.instance;
          final wrong = repo.bank.items.where((i) => store.isWrong(i.id)).toList();

          if (wrong.isEmpty) {
            return const EmptyState(
              title: '오답이 없습니다',
              body: '틀린 문제가 여기 모입니다.\n다시 풀어 맞히면 목록에서 빠집니다.',
            );
          }

          return ListView(
            padding: const EdgeInsets.all(14),
            children: [
              ResumeCard(
                title: '오답 ${wrong.length}개 다시 풀기',
                subtitle: '맞히면 목록에서 사라집니다',
                onTap: () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => QuestionScreen(title: '오답', pool: List.of(wrong)))),
              ),
              const SizedBox(height: 8),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _busy ? null : () => _makePdf(wrong),
                  icon: _busy
                      ? const SizedBox(
                          width: 16, height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.picture_as_pdf_outlined, size: 18),
                  label: Text(_busy ? '만드는 중…' : 'PDF 만들기'),
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  '문제와 해설이 함께 실린 인쇄본을 폰에서 바로 만듭니다. '
                  '뜨는 창에서 「PDF로 저장」을 고르면 파일로 남습니다.',
                  style: TextStyle(color: c.faint, fontSize: 12.5),
                ),
              ),
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: () => _export(wrong),
                  child: const Text('PC용 목록 내보내기 (.json)'),
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  '문항 번호만 담은 목록입니다. PC로 옮겨 python tools/wrongnote_pdf.py 에 '
                  '넘기면 표지·쪽번호까지 붙은 인쇄본이 나옵니다.',
                  style: TextStyle(color: c.faint, fontSize: 12.5),
                ),
              ),
              const SectionTitle('틀린 문제'),
              ...wrong.map((i) {
                final cnt = store.att[i.id]?.where((a) => !a.ok).length ?? 0;
                return RowTile(
                  title: Repo.instance.line(i, 60),
                  subtitle: '${i.sj} · ${i.ty}',
                  trailing:
                      Text('$cnt회 틀림', style: TextStyle(color: c.faint, fontSize: 12.5)),
                  onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => QuestionScreen(pool: [i]))),
                );
              }),
            ],
          );
        },
      ),
    );
  }

  Future<void> _export(List<Item> wrong) async {
    final ids = wrong.map((i) => i.id).toList();
    final now = DateTime.now();
    final data = {'v': 1, 'at': now.toIso8601String(), 'n': ids.length, 'ids': ids};
    final stamp = '${now.year}${now.month.toString().padLeft(2, '0')}'
        '${now.day.toString().padLeft(2, '0')}';
    try {
      final dir = await getTemporaryDirectory();
      final file = File('${dir.path}/wrongnote-$stamp.json');
      await file.writeAsString(const JsonEncoder.withIndent('  ').convert(data));
      await Share.shareXFiles([XFile(file.path)],
          text: '오답노트 내보내기 — tools/wrongnote_pdf.py 에 전달하세요');
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('내보내지 못했습니다: $e')));
    }
  }
}
