/// 복습 알림의 **계산만** 하는 곳. 플러그인도 Flutter 도 부르지 않는다.
///
/// [backup.dart] 와 같은 규율이다 — 화면 없이 `dart run` 으로 검증하려면
/// 순수 Dart 여야 한다. 플러그인을 부르는 쪽은 [reminder.dart] 에 있다.
///
/// ```bash
/// dart run tool/check_reminder.dart
/// ```
library;

import 'backup.dart';

/// 하루 한 번, 정한 시각에 알린다.
///
/// **정확 알람(`SCHEDULE_EXACT_ALARM`)은 쓰지 않는다.** 스토어가 그 권한에
/// 사유를 요구하고, 복습이 분 단위로 정확할 이유가 없다. 몇 분 늦게 와도 된다.
class ReminderPlan {
  /// 알릴 시각 (0~23)
  final int hour;

  /// 알릴 분 (0~59)
  final int minute;

  const ReminderPlan({required this.hour, required this.minute});

  /// 자정부터의 분 — 저장할 때 이 한 값만 쓴다.
  int get minuteOfDay => hour * 60 + minute;

  factory ReminderPlan.fromMinuteOfDay(int m) {
    final v = m % 1440;
    return ReminderPlan(hour: v ~/ 60, minute: v % 60);
  }

  /// 「21:00」
  String get label =>
      '${hour.toString().padLeft(2, '0')}:${minute.toString().padLeft(2, '0')}';

  /// [now] 다음으로 이 시각이 오는 때.
  ///
  /// 오늘 시각이 아직 안 지났으면 오늘, 지났으면 내일이다.
  /// **같은 분이면 지난 것으로 본다** — 방금 예약한 알림이 즉시 뜨는 것을 막는다.
  DateTime nextFireAfter(DateTime now) {
    final today = DateTime(now.year, now.month, now.day, hour, minute);
    if (today.isAfter(now)) return today;
    return today.add(const Duration(days: 1));
  }
}

/// [when] 시점에 복습 대상이 될 문항 수.
///
/// `Srs.due` 는 epoch 밀리초다. 그 시각까지 도래한 것을 센다.
/// **`allIds` 로 거르는 이유** — 은행에서 빠진 문항의 기록이 남아 있을 수 있다.
int dueCountAt(Map<String, Srs> srs, DateTime when, {Iterable<String>? allIds}) {
  final at = when.millisecondsSinceEpoch;
  if (allIds == null) {
    return srs.values.where((s) => s.due <= at).length;
  }
  var n = 0;
  for (final id in allIds) {
    final s = srs[id];
    if (s != null && s.due <= at) n++;
  }
  return n;
}

/// 알림 본문. 복습할 것이 없으면 null — **알리지 않는다.**
///
/// 매일 같은 시각에 「복습할 것이 없습니다」가 오면 알림을 꺼 버리게 된다.
String? reminderBody(int dueCount) {
  if (dueCount <= 0) return null;
  return '복습할 문항 $dueCount개가 기다리고 있습니다.';
}

/// 앞으로 [days] 일치 알림을 미리 계산한다.
///
/// 하루 한 번 반복 알림 대신 **며칠치를 하나씩 예약**하는 이유 —
/// 반복 알림은 본문이 고정이라 문항 수를 넣을 수 없다. 앱을 열 때마다
/// 다시 계산해 예약하면 그날그날 맞는 수가 들어간다.
///
/// 복습할 것이 없는 날은 **건너뛴다**(목록에 안 들어간다).
List<ReminderSlot> planAhead(
  ReminderPlan plan,
  Map<String, Srs> srs,
  DateTime now, {
  int days = 7,
  Iterable<String>? allIds,
}) {
  final out = <ReminderSlot>[];
  var at = plan.nextFireAfter(now);
  for (var i = 0; i < days; i++) {
    final n = dueCountAt(srs, at, allIds: allIds);
    final body = reminderBody(n);
    if (body != null) out.add(ReminderSlot(id: i, at: at, dueCount: n, body: body));
    at = at.add(const Duration(days: 1));
  }
  return out;
}

/// 예약 한 건.
class ReminderSlot {
  /// 알림 id. 다시 예약할 때 같은 id 를 덮어쓴다 — 0..days-1 을 돌려 쓴다.
  final int id;
  final DateTime at;
  final int dueCount;
  final String body;

  const ReminderSlot({
    required this.id,
    required this.at,
    required this.dueCount,
    required this.body,
  });

  @override
  String toString() => 'ReminderSlot($id, $at, $dueCount)';
}
