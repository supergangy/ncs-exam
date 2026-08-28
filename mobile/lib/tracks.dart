/// 회차를 직렬로 묶는 규칙.
///
/// 회차가 일곱이 되면서 한 줄로 세울 수 없게 됐다. 전산직 응시자는 NCS 여섯 개를
/// 헤치고 자기 것을 찾아야 하고, 사무직 응시자는 전산 회차를 자기 시험인 줄 알고
/// 연다. 홈 화면이 과목을 직렬로 묶는 것(`home_screen.dart`)과 같은 규율이다.
///
/// **고르는 것이 아니라 묶는 것이다.** 전산직 응시자도 NCS 를 보므로 어느 한쪽을
/// 감추면 틀린다.
///
/// 회차의 직렬은 **문항이 정한다** — 내보내기가 과목에서 끌어내
/// (`tools/export_bank.py` 의 `track_of`) `tr` 에 담아 준다. 한 회차가 두 직렬에
/// 걸치면 양쪽 묶음에 다 선다. NCS 와 전공을 한 교시에 치르는 회차를 나중에
/// 넣더라도 화면을 고칠 일이 없다.
///
/// **여기에 Flutter 를 들이지 않는다.** `repo.dart` 는 `rootBundle` 을 써서
/// `dart run` 으로 못 돈다. 규칙만 떼어 두면 `tool/check_tracks.dart` 가
/// 순수 Dart 로 검사할 수 있다 — `round_lock.dart` 와 같은 이유다.
library;

import 'models.dart';

/// 직렬 하나와 거기 딸린 회차들.
class RoundGroup {
  final String tr, name, sub;
  final List<RoundEntry> rounds;
  const RoundGroup(this.tr, this.name, this.sub, this.rounds);
}

/// NCS 를 먼저 둔다 — 모든 지원자가 보는 것이고, 전공은 그 위에 얹힌다.
/// `bank.json` 의 tracks 차례는 전산이 앞이라 그대로 쓰면 뒤집힌다.
const _order = ['ncs', 'cs'];

/// 회차가 하나도 없는 직렬은 내지 않는다.
List<RoundGroup> groupRounds(List<Track> tracks, List<RoundEntry> rounds) {
  final sorted = [...tracks]..sort(
      (a, b) => _order.indexOf(a.id).compareTo(_order.indexOf(b.id)));
  final out = <RoundGroup>[];
  for (final t in sorted) {
    final mine = rounds.where((r) => r.tr.contains(t.id)).toList();
    if (mine.isNotEmpty) out.add(RoundGroup(t.id, t.name, t.sub, mine));
  }
  return out;
}
