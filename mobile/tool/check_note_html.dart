/// 오답노트 인쇄본을 뽑아 **눈으로 볼 수 있게** 한다.
/// 앱은 이 HTML 을 그대로 WebView 에 물려 PDF 로 내므로, 브라우저에서 본 것이
/// 곧 PDF 다 (Ctrl+P 로 A4 미리보기까지 확인할 수 있다).
///
///   dart run tool/check_note_html.dart                 # 표·SVG 든 문항을 골라 12개
///   dart run tool/check_note_html.dart `id` `id` …     # 특정 문항만
library;

import 'dart:convert';
import 'dart:io';
import 'package:ncs_bank/models.dart';
import 'package:ncs_bank/note_html.dart';

int _fail = 0, _pass = 0;

void ok(String label, bool cond) {
  if (cond) {
    _pass++;
  } else {
    _fail++;
    stdout.writeln('  ✗ $label');
  }
}

void main(List<String> args) {
  final f = File('assets/data/bank.json');
  if (!f.existsSync()) {
    stderr.writeln('assets/data/bank.json 이 없다 — mobile/ 에서 돌려야 한다');
    exit(1);
  }
  final j = jsonDecode(f.readAsStringSync()) as Map<String, dynamic>;
  final bank = BankData.fromJson(j);
  final byId = {for (final i in bank.items) i.id: i};

  List<Item> picked;
  if (args.isNotEmpty) {
    picked = args.map((a) => byId[a]).whereType<Item>().toList();
    if (picked.length != args.length) {
      stderr.writeln('없는 문항 id 가 있다');
      exit(1);
    }
  } else {
    // 까다로운 것부터 — 표·SVG·지문·윗첨자·밑줄이 든 문항을 섞어 고른다.
    bool has(Item i, String s) =>
        (i.mt ?? '').contains(s) ||
        (i.ex ?? '').contains(s) ||
        i.ch.any((c) => c.contains(s));
    final want = <Item>[
      ...bank.items.where((i) => has(i, '<svg')).take(2),
      ...bank.items.where((i) => has(i, '<table')).take(4),
      ...bank.items.where((i) => i.pg != null).take(2),
      ...bank.items.where((i) => has(i, '<sup')).take(2),
      ...bank.items.where((i) => i.ch.any((c) => c.contains('<u>'))).take(2),
    ];
    final seen = <String>{};
    picked = want.where((i) => seen.add(i.id)).toList();
  }

  final html = buildNoteHtml(
    picked,
    title: '오답노트 (미리보기)',
    at: DateTime.utc(2026, 8, 7),
    passage: (idx) =>
        idx >= 0 && idx < bank.passages.length ? bank.passages[idx] : null,
    roundTitle: (tag) =>
        bank.rounds.where((r) => r.tag == tag).map((r) => r.title).firstOrNull,
    // 「틀린 답」 표시를 보려고 일부러 정답이 아닌 것을 고른 척한다.
    picked: (id) {
      final it = byId[id]!;
      return it.an == 1 ? 2 : 1;
    },
  );

  stdout.writeln('■ 뽑은 문항 ${picked.length}개');
  for (final i in picked) {
    stdout.writeln('    ${i.id}  ${i.sj} · ${i.ty}');
  }

  stdout.writeln('■ 산출물 점검');
  ok('A4 쪽 설정', html.contains('@page { size: A4;'));
  ok('문항이 다 들어갔다',
      picked.every((i) => html.contains('${i.sj} · ${i.ty}')));
  ok('정답 표시', html.contains('class="ok"'));
  ok('고른 답 표시', html.contains('picked'));
  ok('표가 살아 있다', !html.contains('&lt;table'));
  ok('문항이 쪽을 넘어 잘리지 않는다', html.contains('break-inside: avoid'));
  // 발문·선지는 우리가 쓴 HTML 이라 이스케이프하면 안 된다.
  ok('발문을 이스케이프하지 않았다', !html.contains('&lt;strong&gt;'));

  final out = File('build/wrongnote-preview.html');
  out.parent.createSync(recursive: true);
  out.writeAsStringSync(html);
  stdout.writeln('\n${out.path} 에 썼다 (${(html.length / 1024).round()}KB)');
  stdout.writeln('통과 $_pass · 실패 $_fail');
  if (_fail > 0) exit(1);
}

extension<T> on Iterable<T> {
  T? get firstOrNull => isEmpty ? null : first;
}
