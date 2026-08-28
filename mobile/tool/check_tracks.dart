/// 회차 목록이 **직렬로 묶여 나오는지** 확인한다.
///
/// 회차가 일곱이 되면서 한 줄로 세울 수 없게 됐다 — 여섯은 NCS 고 하나는 전산 전공이다.
/// 전산직 응시자는 NCS 여섯 개를 헤치고 자기 것을 찾아야 하고, 사무직 응시자는
/// 전산 회차를 자기 시험인 줄 알고 연다.
///
/// 규칙은 셋이다 —
///  · 어느 회차도 묶음에서 빠지지 않는다
///  · NCS 가 먼저 선다 (모든 지원자가 보는 것이고, 전공은 그 위에 얹힌다)
///  · 회차가 없는 직렬은 빈 머리말을 내지 않는다
///
/// 그리고 회차의 직렬은 **문항이 정한다** — `bank.json` 의 `tr` 이 그 회차 문항의
/// 과목에서 나온 값과 같은지 함께 본다. 손으로 적게 두면 영역을 바꿀 때 따라오지 않는다.
///
///   dart run tool/check_tracks.dart
library;

import 'dart:convert';
import 'dart:io';

import 'package:ncs_bank/models.dart';
import 'package:ncs_bank/tracks.dart';

int _pass = 0, _fail = 0;

void ok(String what, bool cond) {
  if (cond) {
    _pass++;
  } else {
    _fail++;
    stdout.writeln('  실패 — $what');
  }
}

void main() {
  final raw = File('assets/data/bank.json').readAsStringSync();
  final bank = BankData.fromJson(jsonDecode(raw) as Map<String, dynamic>);
  final groups = groupRounds(bank.tracks, bank.rounds);

  // ── 빠지는 회차가 없다 ────────────────────────────────────────
  final listed = <String>{for (final g in groups) for (final r in g.rounds) r.tag};
  ok('모든 회차가 어느 묶음엔가 든다',
      listed.length == bank.rounds.length);
  ok('없는 회차가 끼어들지 않는다',
      listed.difference(bank.rounds.map((r) => r.tag).toSet()).isEmpty);

  // ── 차례 ──────────────────────────────────────────────────────
  ok('NCS 가 먼저 선다', groups.first.tr == 'ncs');
  ok('빈 묶음을 내지 않는다', groups.every((g) => g.rounds.isNotEmpty));
  ok('직렬 이름이 비어 있지 않다', groups.every((g) => g.name.isNotEmpty));

  // ── 회차의 직렬은 문항이 정한다 ───────────────────────────────
  for (final r in bank.rounds) {
    final fromItems = bank.items
        .where((i) => i.rd == r.tag)
        .map((i) => i.tr)
        .toSet();
    ok('${r.tag} 의 tr 이 문항의 직렬과 같다',
        fromItems.isNotEmpty && fromItems.difference(r.tr.toSet()).isEmpty
            && r.tr.toSet().difference(fromItems).isEmpty);
  }

  // ── 실제로 두 직렬이 다 있다 — 이 검사가 뜻을 가지려면 ────────
  ok('NCS 회차가 있다', groups.any((g) => g.tr == 'ncs'));
  ok('전산 회차가 있다', groups.any((g) => g.tr == 'cs'));

  // ── 두 직렬에 걸친 회차는 양쪽에 다 선다 ──────────────────────
  final both = RoundEntry(
      tag: 'both', title: '한 교시 회차', brand: '', org: '', n: 1, min: 1,
      tr: const ['ncs', 'cs'], areas: const []);
  final mixed = groupRounds(bank.tracks, [both]);
  ok('두 직렬에 걸친 회차는 양쪽 묶음에 다 선다',
      mixed.length == 2 && mixed.every((g) => g.rounds.length == 1));

  // ── 옛 bank.json 대비 — tr 이 없으면 NCS 로 본다 ──────────────
  final old = RoundEntry.fromJson({
    'tag': 'old', 'title': '옛 회차', 'n': 1, 'min': 1, 'areas': <dynamic>[],
  });
  ok('tr 이 없는 회차는 NCS 로 본다', old.tr.length == 1 && old.tr.first == 'ncs');

  stdout.writeln('\n통과 $_pass · 실패 $_fail');
  if (_fail > 0) exit(1);
}
