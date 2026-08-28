/// 아직 안 본 회차를 연습 목록에서 감추는 규칙.
///
/// 회차 문항은 은행에도 함께 있다. 그대로 두면 과목 연습이 모의고사를 미리
/// 태운다 — 의사소통 86문항 중 61개(71%), 문제해결 66%, 수리 59%가 회차
/// 문항이다(2026-08-28 실측). 며칠 연습하면 시간 재고 앉았을 때 **이미 본
/// 문제**가 되고, 한 번 본 것은 되돌릴 수 없다.
///
/// 제출하면 곧바로 합류한다 — 그때부터는 아껴 둘 것이 아니라 복습할 것이다.
///
/// **여기에 Flutter 를 들이지 않는다.** `repo.dart` 는 `rootBundle` 을 쓰고
/// `store.dart` 는 SharedPreferences 를 써서 둘 다 `dart run` 으로 못 돈다.
/// 규칙만 떼어 두면 `tool/check_pool.dart` 가 순수 Dart 로 검사할 수 있다.
library;

import 'models.dart';

/// 아직 제출하지 않은 회차의 tag 들.
Set<String> lockedRounds(List<RoundEntry> rounds, Map<String, List<Object?>> exams) => {
      for (final r in rounds)
        if ((exams[r.tag] ?? const []).isEmpty) r.tag,
    };

/// 잠긴 회차의 문항을 뺀다. 잠긴 것이 없으면 원래 목록을 그대로 돌려준다.
List<Item> withoutLocked(List<Item> xs, Set<String> lock) => lock.isEmpty
    ? xs
    : xs.where((i) => i.rd == null || !lock.contains(i.rd!)).toList();
