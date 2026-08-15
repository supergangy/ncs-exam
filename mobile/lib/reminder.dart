/// 복습 알림을 **실제로 거는** 곳. 계산은 [reminder_plan.dart] 에 있다.
///
/// 여기만 플러그인에 묶인다. 그래야 일정 계산을 `dart run` 으로 검증할 수 있다
/// (`tool/check_reminder.dart`).
///
/// ## 왜 반복 알림이 아닌가
///
/// `periodicallyShow` 는 본문이 고정이라 「복습할 문항 N개」를 넣을 수 없다.
/// 그래서 **며칠치를 하나씩 예약**하고, 앱을 열 때마다 다시 계산해 덮어쓴다.
///
/// ## 정확 알람을 쓰지 않는다
///
/// `SCHEDULE_EXACT_ALARM` 은 스토어가 사유를 요구한다. 복습이 분 단위로 정확할
/// 이유가 없어 `inexactAllowWhileIdle` 로 건다. 몇 분 늦게 와도 된다.
library;

import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_timezone/flutter_timezone.dart';
import 'package:timezone/data/latest_all.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

import 'reminder_plan.dart';
import 'store.dart';

class Reminder {
  Reminder._();
  static final Reminder instance = Reminder._();

  static const _channelId = 'review';
  static const _channelName = '복습 알림';
  static const _days = 7;

  final _plugin = FlutterLocalNotificationsPlugin();
  bool _ready = false;

  /// 앱 시작에 한 번. 실패해도 **앱은 계속 뜬다** — 알림은 곁가지다.
  Future<void> init() async {
    if (_ready) return;
    try {
      tzdata.initializeTimeZones();
      final name = await FlutterTimezone.getLocalTimezone();
      tz.setLocalLocation(tz.getLocation(name));
      await _plugin.initialize(
        const InitializationSettings(
          android: AndroidInitializationSettings('@mipmap/ic_launcher'),
          iOS: DarwinInitializationSettings(
            requestAlertPermission: false,
            requestBadgePermission: false,
            requestSoundPermission: false,
          ),
        ),
      );
      _ready = true;
    } catch (err) {
      // 시간대를 못 읽거나 플러그인이 없는 환경(테스트·데스크톱)일 수 있다.
      debugPrint('알림을 준비하지 못했다: $err');
    }
  }

  /// 알림 권한을 묻는다. 켤 때 한 번만 부른다.
  /// 거절해도 설정은 켜진 채로 둔다 — 나중에 시스템 설정에서 허용하면 바로 온다.
  Future<bool> requestPermission() async {
    if (!_ready) return false;
    try {
      final android = _plugin.resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>();
      if (android != null) {
        return await android.requestNotificationsPermission() ?? false;
      }
      final ios = _plugin.resolvePlatformSpecificImplementation<
          IOSFlutterLocalNotificationsPlugin>();
      return await ios?.requestPermissions(alert: true, badge: true, sound: true) ??
          false;
    } catch (err) {
      debugPrint('알림 권한을 묻지 못했다: $err');
      return false;
    }
  }

  /// 지금 기록으로 앞으로 [_days] 일치를 다시 예약한다.
  ///
  /// **먼저 전부 지우고 다시 건다.** 문항을 풀면 `due` 가 바뀌므로 예전 예약은
  /// 틀린 개수를 들고 있다. [allIds] 는 은행에 실제로 있는 문항 id 다.
  Future<void> reschedule({Iterable<String>? allIds}) async {
    if (!_ready) return;
    try {
      await cancelAll();
      final store = Store.instance;
      if (!store.remind) return;

      final slots = planAhead(
        ReminderPlan.fromMinuteOfDay(store.remindAt),
        store.srs,
        DateTime.now(),
        days: _days,
        allIds: allIds,
      );
      for (final s in slots) {
        await _plugin.zonedSchedule(
          s.id,
          '복습할 시간입니다',
          s.body,
          tz.TZDateTime.from(s.at, tz.local),
          const NotificationDetails(
            android: AndroidNotificationDetails(
              _channelId,
              _channelName,
              channelDescription: '복습할 문항이 쌓이면 정한 시각에 알립니다.',
              importance: Importance.defaultImportance,
              priority: Priority.defaultPriority,
            ),
            iOS: DarwinNotificationDetails(),
          ),
          androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
        );
      }
    } catch (err) {
      debugPrint('알림을 예약하지 못했다: $err');
    }
  }

  Future<void> cancelAll() async {
    if (!_ready) return;
    try {
      await _plugin.cancelAll();
    } catch (err) {
      debugPrint('알림을 지우지 못했다: $err');
    }
  }
}
