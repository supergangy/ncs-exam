/// 통계 화면이 그릴 값을 **계산만** 하는 곳. 차트도 Flutter 도 부르지 않는다.
///
/// [backup.dart]·[reminder_plan.dart] 와 같은 규율이다 — 화면 없이 `dart run` 으로
/// 검증하려면 순수 Dart 여야 한다.
///
/// ```bash
/// dart run tool/check_stats.dart
/// ```
library;

import 'backup.dart';

/// 하루치 집계.
class DayStat {
  /// 그날 자정(로컬).
  final DateTime day;

  /// 그날 푼 횟수. **문항 수가 아니라 시도 수**다 — 같은 문항을 두 번 풀면 2다.
  final int solved;

  /// 그 가운데 맞힌 횟수.
  final int correct;

  const DayStat({required this.day, required this.solved, required this.correct});

  /// 정답률(%). 푼 것이 없으면 null — 0% 로 그리면 「다 틀렸다」로 읽힌다.
  int? get rate => solved == 0 ? null : (correct * 100 / solved).round();

  @override
  String toString() => 'DayStat(${day.year}-${day.month}-${day.day}, $solved/$correct)';
}

/// 자정으로 자른다. 시각을 남겨 두면 같은 날이 서로 다른 키가 된다.
DateTime dayOf(DateTime t) => DateTime(t.year, t.month, t.day);

/// 최근 [days] 일의 일별 집계. **오늘이 마지막**이고 빈 날도 0으로 채운다.
///
/// 빈 날을 빼면 선이 이어지면서 「매일 풀었다」처럼 보인다.
List<DayStat> dailyStats(
  Map<String, List<Attempt>> att,
  DateTime now, {
  int days = 30,
}) {
  final today = dayOf(now);
  final first = today.subtract(Duration(days: days - 1));
  final solved = <DateTime, int>{};
  final correct = <DateTime, int>{};

  for (final list in att.values) {
    for (final a in list) {
      final d = dayOf(DateTime.fromMillisecondsSinceEpoch(a.at));
      if (d.isBefore(first) || d.isAfter(today)) continue;
      solved[d] = (solved[d] ?? 0) + 1;
      if (a.ok) correct[d] = (correct[d] ?? 0) + 1;
    }
  }

  return List.generate(days, (i) {
    final d = first.add(Duration(days: i));
    return DayStat(day: d, solved: solved[d] ?? 0, correct: correct[d] ?? 0);
  });
}

/// 과목 하나의 정답률 — 막대 하나에 들어갈 값.
class SubjectRate {
  final String name;
  final int solved, correct;
  const SubjectRate({required this.name, required this.solved, required this.correct});
  int get rate => solved == 0 ? 0 : (correct * 100 / solved).round();
}

/// 과목별 정답률. [idsBySubject] 는 과목 이름 → 그 과목 문항 id 다.
///
/// **마지막 시도만 센다.** 틀렸다가 다시 맞힌 문항을 오답으로 남겨 두면
/// 오답노트(마지막 시도 기준)와 숫자가 어긋난다.
List<SubjectRate> subjectRates(
  Map<String, List<Attempt>> att,
  Map<String, List<String>> idsBySubject,
) {
  final out = <SubjectRate>[];
  idsBySubject.forEach((name, ids) {
    var s = 0, c = 0;
    for (final id in ids) {
      final list = att[id];
      if (list == null || list.isEmpty) continue;
      s++;
      if (list.last.ok) c++;
    }
    if (s > 0) out.add(SubjectRate(name: name, solved: s, correct: c));
  });
  out.sort((a, b) => b.rate.compareTo(a.rate));
  return out;
}
