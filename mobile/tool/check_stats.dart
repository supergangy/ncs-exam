/// 통계 집계가 맞는지 확인한다. `flutter test` 가 이 환경에서 못 돌아
/// 순수 Dart 로 같은 것을 본다 (`lib/stats_data.dart` 가 Flutter 를 안 쓰는 이유).
///
/// 특히 볼 것 —
///  · **빈 날을 0으로 채운다.** 빼 버리면 선이 이어져 매일 푼 것처럼 보인다
///  · **과목 정답률은 마지막 시도만 센다.** 오답노트와 숫자가 어긋나면 안 된다
///  · 푼 것이 없는 날의 정답률은 0%가 아니라 null 이다
///
///   dart run tool/check_stats.dart
library;

import 'dart:io';
import 'package:ncs_bank/backup.dart';
import 'package:ncs_bank/stats_data.dart';

int _fail = 0, _pass = 0;

void ok(String label, bool cond) {
  if (cond) {
    _pass++;
  } else {
    _fail++;
    stdout.writeln('  ✗ $label');
  }
}

void eq(String label, Object? got, Object? want) {
  if ('$got' == '$want') {
    _pass++;
  } else {
    _fail++;
    stdout.writeln('  ✗ $label\n      나온 것 $got\n      바란 것 $want');
  }
}

Attempt _at(DateTime when, bool correct) =>
    Attempt(chosen: 1, ok: correct, at: when.millisecondsSinceEpoch, ms: 1000);

void main() {
  final now = DateTime(2026, 8, 15, 14, 30);

  stdout.writeln('■ 자정으로 자른다');
  eq('시각을 버린다', dayOf(now), DateTime(2026, 8, 15));
  eq('자정은 그대로', dayOf(DateTime(2026, 8, 15)), DateTime(2026, 8, 15));

  stdout.writeln('■ 일별 집계');
  final att = <String, List<Attempt>>{
    'q1': [
      _at(now, true),                                    // 오늘 O
      _at(now.subtract(const Duration(hours: 2)), false), // 오늘 X
    ],
    'q2': [_at(now.subtract(const Duration(days: 3)), true)],   // 사흘 전 O
    'q3': [_at(now.subtract(const Duration(days: 90)), true)],  // 범위 밖
  };
  final d = dailyStats(att, now, days: 30);
  eq('길이는 항상 days', d.length, 30);
  eq('마지막이 오늘', d.last.day, DateTime(2026, 8, 15));
  eq('첫날은 29일 전', d.first.day, DateTime(2026, 8, 15).subtract(const Duration(days: 29)));
  eq('오늘 시도 2회', d.last.solved, 2);
  eq('오늘 정답 1회', d.last.correct, 1);
  eq('오늘 정답률 50%', d.last.rate, 50);
  eq('사흘 전 1회', d[30 - 1 - 3].solved, 1);
  eq('빈 날은 0', d[10].solved, 0);
  eq('빈 날 정답률은 null', d[10].rate, null);
  // 90일 전 기록이 범위 안으로 새어 들어오면 합이 어긋난다.
  eq('범위 밖은 안 센다', d.fold<int>(0, (s, x) => s + x.solved), 3);
  ok('날짜가 하루씩 증가',
      List.generate(d.length - 1, (i) => i)
          .every((i) => d[i + 1].day.difference(d[i].day).inDays == 1));

  stdout.writeln('■ 기록이 없을 때');
  final empty = dailyStats(const {}, now, days: 7);
  eq('길이는 유지', empty.length, 7);
  ok('전부 0', empty.every((x) => x.solved == 0 && x.correct == 0));
  ok('전부 null 정답률', empty.every((x) => x.rate == null));

  stdout.writeln('■ 과목별 정답률 — 마지막 시도만');
  final att2 = <String, List<Attempt>>{
    // 틀렸다가 다시 맞혔다 → 맞은 것으로 센다 (오답노트와 같은 기준)
    'a1': [_at(now, false), _at(now, true)],
    'a2': [_at(now, true)],
    'a3': [_at(now, true), _at(now, false)], // 맞혔다가 틀렸다 → 틀린 것
    'b1': [_at(now, false)],
    'c1': const [], // 시도 없음
  };
  final rates = subjectRates(att2, {
    '수리': ['a1', 'a2', 'a3'],
    '의사소통': ['b1'],
    '정보': ['c1'],
    '기술': ['없는id'],
  });
  eq('푼 과목만 나온다', rates.length, 2);
  final math = rates.firstWhere((r) => r.name == '수리');
  eq('수리 푼 문항 3', math.solved, 3);
  eq('수리 정답 2', math.correct, 2);
  eq('수리 정답률 67%', math.rate, 67);
  final comm = rates.firstWhere((r) => r.name == '의사소통');
  eq('의사소통 0%', comm.rate, 0);
  ok('정답률 내림차순', rates.first.rate >= rates.last.rate);
  ok('시도 없는 과목은 빠진다', !rates.any((r) => r.name == '정보'));
  ok('없는 id 만 있는 과목도 빠진다', !rates.any((r) => r.name == '기술'));

  stdout.writeln('\n통과 $_pass · 실패 $_fail');
  if (_fail > 0) exit(1);
}
