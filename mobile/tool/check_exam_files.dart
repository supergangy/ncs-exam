/// 회차 인쇄본 내려받기가 **실제로 있는 파일**을 가리키는지 확인한다.
///
/// 단추가 없는 자산을 가리키면 눌러야 안다. 그것도 「내려받지 못했습니다」라는
/// 스낵바 하나로 끝나 원인이 남지 않는다. 그래서 여기서 한 번 훑는다.
///
/// 규칙은 넷이다 —
///  · 일곱 회차가 문제집·해설집을 둘 다 갖는다
///  · 가리키는 자산이 `assets/exams/` 에 실제로 있다
///  · 저장될 이름은 한글이고 자산 경로는 아스키다 (인코딩이 갈리는 자리)
///  · **출제이유 PDF 가 섞이지 않는다** — 함정 설계가 새어 나간다
///
/// 웹판(`web/test/pdf.test.js`)과 같은 것을 본다. 한쪽만 고치면 두 판이
/// 다른 것을 말하게 된다.
///
///   dart run tool/check_exam_files.dart
library;

import 'dart:convert';
import 'dart:io';

import 'package:ncs_bank/exam_files.dart';
import 'package:ncs_bank/models.dart';

int _pass = 0, _fail = 0;

void ok(String what, bool cond) {
  if (cond) {
    _pass++;
  } else {
    _fail++;
    stdout.writeln('  실패 — $what');
  }
}

bool _ascii(String s) => s.runes.every((r) => r >= 0x20 && r < 0x7f);

void main() {
  final raw = File('assets/data/bank.json').readAsStringSync();
  final bank = BankData.fromJson(jsonDecode(raw) as Map<String, dynamic>);

  ok('회차가 있다', bank.rounds.isNotEmpty);

  for (final r in bank.rounds) {
    final files = examFiles(r);
    ok('${r.tag} — 문제집·해설집 둘 다 있다',
        files.map((f) => f.kind).toList().join() == 'qs');

    for (final f in files) {
      ok('${r.tag} ${f.kind} — 자산이 실제로 있다  ${f.asset}',
          File(f.asset).existsSync());
      ok('${r.tag} ${f.kind} — 자산 경로가 아스키다', _ascii(f.asset));
      ok('${r.tag} ${f.kind} — 저장될 이름이 .pdf 다', f.file.endsWith('.pdf'));
      ok('${r.tag} ${f.kind} — 출제이유가 섞이지 않았다',
          !f.file.contains('출제이유'));
      ok('${r.tag} ${f.kind} — 크기가 비어 있지 않다 (${f.kb}KB)', f.kb > 100);

      // 적어 둔 크기가 실제와 크게 어긋나면 화면이 거짓을 말한다
      final real = (File(f.asset).lengthSync() / 1024).round();
      ok('${r.tag} ${f.kind} — 적힌 크기가 실제와 같다 ($real vs ${f.kb})',
          (real - f.kb).abs() <= 1);
    }
  }

  // ── 크기 표기 ────────────────────────────────────────────────
  String sz(int kb) => ExamFile(
      kind: 'q', name: '', asset: '', file: '', kb: kb).size;
  ok('1MB 아래는 KB 그대로', sz(598) == '598KB' && sz(1023) == '1023KB');
  ok('1MB 위는 소수 한 자리', sz(1024) == '1.0MB' && sz(1449) == '1.4MB');

  // ── 자산 경로 ────────────────────────────────────────────────
  ok('해설집만 .sol 이 붙는다',
      examAsset('r1_public', 'q') == 'assets/exams/r1_public.pdf' &&
      examAsset('r1_public', 's') == 'assets/exams/r1_public.sol.pdf');

  // ── 없는 것은 내지 않는다 ────────────────────────────────────
  RoundEntry make(Map<String, List<dynamic>> pdf) => RoundEntry(
      tag: 'r9', title: '', brand: '', org: '', n: 1, min: 1,
      tr: const ['ncs'], pdf: pdf, areas: const []);
  ok('pdf 칸이 비면 빈 목록', examFiles(make({})).isEmpty);
  ok('해설집만 없으면 문제집 하나만',
      examFiles(make({'q': ['가.pdf', 500]})).length == 1);
  ok('차례는 문제집 먼저',
      examFiles(make({'s': ['해설.pdf', 1], 'q': ['문제.pdf', 2]}))
          .map((f) => f.kind).join() == 'qs');
  ok('옛 bank.json 에 pdf 칸이 없어도 터지지 않는다',
      RoundEntry.fromJson({
        'tag': 'old', 'title': '옛 회차', 'n': 1, 'min': 1, 'areas': <dynamic>[],
      }).pdf.isEmpty);

  stdout.writeln('\n통과 $_pass · 실패 $_fail');
  if (_fail > 0) exit(1);
}
