/// 복습 알림 일정이 제대로 서는지 확인한다. `flutter test` 가 이 환경에서 못 돌아
/// 순수 Dart 로 같은 것을 본다 (`lib/reminder_plan.dart` 가 Flutter 를 안 쓰는 이유).
///
/// 특히 볼 것 —
///  · **방금 예약한 알림이 즉시 뜨면 안 된다.** 같은 분이면 내일로 넘긴다
///  · **복습할 것이 없는 날은 건너뛴다.** 매일 「없습니다」가 오면 알림을 꺼 버린다
///  · 날짜 경계와 서머타임 없는 KST 에서 하루가 정확히 하루인지
///
///   dart run tool/check_reminder.dart
library;

import 'dart:io';
import 'package:ncs_bank/backup.dart';
import 'package:ncs_bank/reminder_plan.dart';

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

/// `due` 가 [at] 인 문항 하나짜리 기록.
Srs _srs(DateTime at) => Srs()..due = at.millisecondsSinceEpoch;

void main() {
  stdout.writeln('■ 시각 표기와 왕복');
  eq('분으로 접기', const ReminderPlan(hour: 21, minute: 5).minuteOfDay, 21 * 60 + 5);
  eq('분에서 펴기', ReminderPlan.fromMinuteOfDay(21 * 60 + 5).label, '21:05');
  eq('자정', ReminderPlan.fromMinuteOfDay(0).label, '00:00');
  eq('하루를 넘긴 값도 접힌다', ReminderPlan.fromMinuteOfDay(1440 + 90).label, '01:30');

  stdout.writeln('■ 다음 알림 시각');
  const plan = ReminderPlan(hour: 21, minute: 0);
  eq('아직 안 지났으면 오늘',
      plan.nextFireAfter(DateTime(2026, 8, 15, 20, 59)), DateTime(2026, 8, 15, 21, 0));
  eq('지났으면 내일',
      plan.nextFireAfter(DateTime(2026, 8, 15, 21, 1)), DateTime(2026, 8, 16, 21, 0));
  // 같은 분에 예약하면 즉시 떠 버린다. 그래서 지난 것으로 본다.
  eq('같은 분이면 내일',
      plan.nextFireAfter(DateTime(2026, 8, 15, 21, 0)), DateTime(2026, 8, 16, 21, 0));
  eq('달을 넘겨도',
      plan.nextFireAfter(DateTime(2026, 8, 31, 23, 0)), DateTime(2026, 9, 1, 21, 0));
  eq('해를 넘겨도',
      plan.nextFireAfter(DateTime(2026, 12, 31, 23, 0)), DateTime(2027, 1, 1, 21, 0));

  stdout.writeln('■ 그 시각까지 도래하는 문항 수');
  final now = DateTime(2026, 8, 15, 9, 0);
  final srs = <String, Srs>{
    'a': _srs(now.subtract(const Duration(days: 1))), // 이미 지났다
    'b': _srs(now.add(const Duration(hours: 6))),     // 오늘 밤
    'c': _srs(now.add(const Duration(days: 3))),      // 사흘 뒤
    'd': _srs(now.add(const Duration(days: 30))),     // 한 달 뒤
  };
  eq('지금 기준', dueCountAt(srs, now), 1);
  eq('오늘 21시', dueCountAt(srs, DateTime(2026, 8, 15, 21, 0)), 2);
  eq('나흘 뒤', dueCountAt(srs, now.add(const Duration(days: 4))), 3);
  eq('두 달 뒤', dueCountAt(srs, now.add(const Duration(days: 60))), 4);
  // 은행에서 빠진 문항의 기록이 남아 있을 수 있다.
  eq('은행에 있는 것만 센다',
      dueCountAt(srs, now.add(const Duration(days: 60)), allIds: ['a', 'b']), 2);
  eq('기록이 비면 0', dueCountAt(const {}, now), 0);

  stdout.writeln('■ 본문');
  eq('없으면 알리지 않는다', reminderBody(0), null);
  eq('음수도 알리지 않는다', reminderBody(-1), null);
  ok('개수가 본문에 들어간다', reminderBody(3)!.contains('3개'));

  stdout.writeln('■ 며칠치 예약');
  final slots = planAhead(plan, srs, now, days: 7);
  // 이 자료에는 이미 지난 문항(a)이 있어 이레 내내 복습할 것이 있다.
  eq('빈 날이 없으면 이레 다 잡는다', slots.length, 7);
  ok('모두 복습할 것이 있는 날', slots.every((s) => s.dueCount > 0));
  ok('시각이 오름차순',
      List.generate(slots.length - 1, (i) => i)
          .every((i) => slots[i].at.isBefore(slots[i + 1].at)));
  ok('id 가 겹치지 않는다', slots.map((s) => s.id).toSet().length == slots.length);
  ok('첫 예약은 지금보다 뒤', slots.isEmpty || slots.first.at.isAfter(now));
  eq('하루 간격', slots.length < 2 ? 1 : slots[1].at.difference(slots[0].at).inDays, 1);
  // 문항 수는 날이 갈수록 늘기만 한다 — 도래한 것은 되돌아가지 않는다.
  ok('개수가 줄지 않는다',
      List.generate(slots.length - 1, (i) => i)
          .every((i) => slots[i].dueCount <= slots[i + 1].dueCount));

  stdout.writeln('■ 빈 날은 건너뛴다');
  // 사흘 뒤에야 도래하는 문항 하나뿐이면 앞의 사흘은 보낼 것이 없다.
  // `due` 는 되돌아가지 않으므로 빈 날은 **창의 앞쪽에만** 생긴다.
  final later = <String, Srs>{'c': _srs(now.add(const Duration(days: 3)))};
  final sparse = planAhead(plan, later, now, days: 7);
  eq('앞의 사흘을 건너뛴다', sparse.length, 4);
  eq('첫 예약이 사흘 뒤', sparse.first.at, DateTime(2026, 8, 18, 21, 0));
  ok('건너뛴 날은 목록에 없다',
      sparse.every((s) => s.at.isAfter(DateTime(2026, 8, 17, 23, 59))));
  ok('전부 1문항', sparse.every((s) => s.dueCount == 1));

  stdout.writeln('■ 기록이 없을 때');
  ok('예약이 하나도 없다', planAhead(plan, const {}, now).isEmpty);

  stdout.writeln('■ 설정이 백업을 왕복한다');
  final d = decodeStore(encodeStore(StoreData(
    att: {}, srs: {}, exams: {}, mark: {},
    remind: true, remindAt: 21 * 60 + 30,
  )));
  eq('켬 여부', d.remind, true);
  eq('시각', d.remindAt, 21 * 60 + 30);
  eq('기본값은 꺼짐', decodeStore({}).remind, false);
  eq('기본 시각 21:00', decodeStore({}).remindAt, 21 * 60);
  eq('범위 밖 시각은 접힌다',
      ReminderPlan.fromMinuteOfDay(decodeStore({'rmAt': 99999}).remindAt).label,
      ReminderPlan.fromMinuteOfDay(99999 % 1440).label);

  stdout.writeln('\n통과 $_pass · 실패 $_fail');
  if (_fail > 0) exit(1);
}
