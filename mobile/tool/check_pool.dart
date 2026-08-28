/// 연습 목록이 **아직 안 본 회차를 미리 태우지 않는지** 확인한다.
///
/// 회차 문항은 은행에도 함께 있다. 그대로 두면 과목 연습이 모의고사를 먼저
/// 소진한다 — 의사소통 86문항 중 61개(71%), 문제해결 66%, 수리 59%가 회차
/// 문항이다(2026-08-28 실측). 며칠 연습하면 시간 재고 앉았을 때 **이미 본
/// 문제**가 되고, 한 번 본 것은 되돌릴 수 없다.
///
/// 규칙은 셋이다 —
///  · 제출하지 않은 회차의 문항은 `Repo.filter()` 가 내지 않는다
///  · 제출하면 곧바로 합류한다 (아껴 둘 것이 아니라 복습할 것이다)
///  · 회차 화면(`roundItems`)과 기록 기반 목록(오답노트·복습·북마크)은 거르지 않는다
///
/// **화면이 이 목록으로 수를 센다.** 그래서 거르는 곳과 세는 곳이 저절로 맞는다.
///
///   dart run tool/check_pool.dart
library;

import 'dart:convert';
import 'dart:io';

import 'package:ncs_bank/models.dart';
import 'package:ncs_bank/round_lock.dart';

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
  // `Repo` 는 rootBundle 을, `Store` 는 SharedPreferences 를 써서 `dart run` 으로
  // 못 돈다. 그래서 **규칙만** 순수하게 떼어 둔 `round_lock.dart` 를 검사한다.
  // Repo.filter() 는 이 둘을 그대로 부른다.
  final rounds = bank.rounds.map((r) => r.tag).toSet();
  final byTag = <String, List<Item>>{};
  for (final i in bank.items) {
    if (i.rd != null) (byTag[i.rd!] ??= []).add(i);
  }

  // ── 아무 회차도 제출하지 않은 상태 ────────────────────────────
  var lock = lockedRounds(bank.rounds, {});
  ok('아무것도 제출하지 않으면 회차가 모두 잠긴다', lock.length == rounds.length);
  final all = withoutLocked(bank.items, lock);
  ok('회차 문항이 하나도 안 나온다',
      all.every((i) => i.rd == null || !rounds.contains(i.rd)));

  final comm = bank.items.where((i) => i.sj == '의사소통능력').toList();
  final sj = withoutLocked(comm, lock);
  ok('과목 목록에도 안 나온다', sj.every((i) => i.rd == null));
  ok('의사소통은 회차 문항이 많다 — 그래서 이 규칙이 필요하다',
      comm.where((i) => i.rd != null).length > comm.length ~/ 2);
  ok('그래도 풀 것이 남는다', sj.isNotEmpty);

  final hidden = bank.items.where((i) => i.rd != null).length;
  ok('감춘 수가 회차 문항 수와 같다', all.length + hidden == bank.items.length);

  // 회차 화면은 이 규칙을 거치지 않는다 (Repo.roundItems 는 따로다)
  final first = bank.rounds.first.tag;
  ok('회차 문항 자체는 그대로 있다', (byTag[first] ?? const []).isNotEmpty);

  // ── 한 회차를 제출한 뒤 ───────────────────────────────────────
  lock = lockedRounds(bank.rounds, {first: [Object()]});
  ok('제출한 회차만 풀린다', !lock.contains(first) && lock.length == rounds.length - 1);
  final after = withoutLocked(bank.items, lock);
  final joined = (byTag[first] ?? const []).length;
  ok('제출한 회차가 합류한다', after.length == all.length + joined);
  ok('제출한 회차의 문항이 실제로 들어 있다',
      after.any((i) => i.rd == first));
  ok('나머지 회차는 그대로 감춰져 있다',
      after.every((i) => i.rd == null || i.rd == first));

  // 과목 목록도 함께 늘어난다 — 세는 곳과 푸는 곳이 같은 창구다
  final sj2 = withoutLocked(comm, lock);
  ok('과목 목록도 함께 늘어난다', sj2.length > sj.length);

  stdout.writeln('\n통과 $_pass · 실패 $_fail');
  if (_fail > 0) exit(1);
}
