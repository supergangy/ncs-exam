/// 백업이 왕복하는지 확인한다. `flutter test` 가 이 환경에서 못 돌아
/// 순수 Dart 로 같은 것을 본다 (`lib/backup.dart` 가 Flutter 를 안 쓰는 이유).
///
/// 특히 볼 것 — **깨진 백업을 물려도 아무것도 안 바뀌어야 한다.**
/// 반만 읽어 들이면 다음 저장이 나머지를 영영 지운다.
///
///   dart run tool/check_backup.dart
library;

import 'dart:convert';
import 'dart:io';
import 'package:ncs_bank/backup.dart';

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
  final same = '$got' == '$want';
  if (same) {
    _pass++;
  } else {
    _fail++;
    stdout.writeln('  ✗ $label\n      나온 것: $got\n      바랄 것: $want');
  }
}

/// 던져야 하는 것이 정말 던지는가.
void throws(String label, void Function() f) {
  try {
    f();
    _fail++;
    stdout.writeln('  ✗ $label — 던지지 않았다');
  } catch (_) {
    _pass++;
  }
}

StoreData _sample() => StoreData(
      att: {
        'q1': [
          Attempt(chosen: 3, ok: true, at: 1700000000000, ms: 42000),
          Attempt(chosen: null, ok: false, at: 1700000100000), // 안 고른 것
        ],
        'q2': [Attempt(chosen: 1, ok: false, at: 1700000200000, ms: 9000)],
      },
      srs: {'q1': Srs(e: 2.7, i: 3, due: 1700100000000)},
      exams: {
        'r1_public': [
          ExamRecord(
            at: 1700000300000, score: 41, n: 50, sec: 3212, auto: true,
            ans: {1: 3, 2: 5, 50: 1},
          ),
        ],
      },
      mark: {
        'q2': Mark(bookmark: true, flag: true, memo: '③이 둘 다 맞는 듯', at: 1700000400000),
      },
      sit: SitState(
        tag: 'r4_korail', at: 1700000500000, endsAt: 1700003000000,
        ans: {1: 2, 7: 4}, flag: {7: true, 9: false}, atNo: 7,
      ),
      solo: SoloSession(
        ids: ['q1', 'q2', 'q3'], chosen: [3, null, 5], graded: [true, false, false],
        at: 1, title: '데이터베이스', savedAt: 1700000600000,
      ),
      admin: true,
      textScale: 1.15,
    );

void main() {
  final src = _sample();

  stdout.writeln('■ 왕복 — encode → JSON 문자열 → decode');
  final round = decodeStore(
      (jsonDecode(jsonEncode(encodeStore(src))) as Map).cast<String, dynamic>());

  eq('att 문항 수', round.att.length, 2);
  eq('att 시도 수', round.att['q1']!.length, 2);
  eq('고른 선지', round.att['q1']![0].chosen, 3);
  eq('맞음 여부', round.att['q1']![0].ok, true);
  eq('소요 시간', round.att['q1']![0].ms, 42000);
  eq('안 고른 것은 null', round.att['q1']![1].chosen, null);
  eq('시간 안 잰 것은 null', round.att['q1']![1].ms, null);

  eq('srs 계수', round.srs['q1']!.e, 2.7);
  eq('srs 간격', round.srs['q1']!.i, 3);
  eq('srs 예정', round.srs['q1']!.due, 1700100000000);

  final r = round.exams['r1_public']!.single;
  eq('회차 점수', r.score, 41);
  eq('자동 제출', r.auto, true);
  eq('답안 — 문자열 키가 정수로 돌아온다', r.ans[50], 1);
  eq('답안 칸 수', r.ans.length, 3);

  eq('메모', round.mark['q2']!.memo, '③이 둘 다 맞는 듯');
  eq('북마크', round.mark['q2']!.bookmark, true);

  eq('응시 회차', round.sit!.tag, 'r4_korail');
  eq('응시 위치 (at_no 표기)', round.sit!.atNo, 7);
  eq('별표 켠 것', round.sit!.flag[7], true);
  eq('별표 끈 것', round.sit!.flag[9], false);

  eq('풀던 묶음 문항', round.solo!.ids.join(','), 'q1,q2,q3');
  eq('풀던 묶음 위치', round.solo!.at, 1);
  eq('풀던 묶음 채점 수', round.solo!.done, 1);
  eq('풀던 묶음 이름', round.solo!.title, '데이터베이스');

  eq('관리자 모드', round.admin, true);
  eq('글자 배율', round.textScale, 1.15);

  stdout.writeln('■ 봉투');
  final env = wrapBackup(src, DateTime.utc(2026, 8, 7, 12));
  eq('건수 — 문항', env['counts']['att'], 2);
  eq('건수 — 회차', env['counts']['exams'], 1);
  eq('건수 — 표시', env['counts']['mark'], 1);
  final back = readBackup(jsonDecode(jsonEncode(env)));
  eq('봉투를 거쳐도 그대로', back.data.att.length, 2);
  eq('만든 날짜', back.at?.toUtc().toIso8601String(), '2026-08-07T12:00:00.000Z');

  stdout.writeln('■ 옛 기록과 섞여도 읽힌다');
  final old = decodeStore({
    'att': {
      'q9': [
        {'c': 2, 'k': 1, 't': 1699000000000} // ms 가 없던 시절
      ]
    },
    'srs': {'q9': {'e': 2.5, 'i': 0, 'due': 0}},
  });
  eq('옛 시도도 읽힌다', old.att['q9']!.single.chosen, 2);
  eq('옛 시도의 ms 는 null', old.att['q9']!.single.ms, null);
  eq('없는 칸은 기본값 — solo', old.solo, null);
  eq('없는 칸은 기본값 — 배율', old.textScale, 1.0);
  eq('없는 칸은 기본값 — 관리자', old.admin, false);

  stdout.writeln('■ 깨진 백업은 **던진다** (반만 읽어 들이면 안 된다)');
  throws('data 가 없다', () => readBackup({'v': 1, 'app': 'ncs-bank'}));
  throws('맵이 아니다', () => readBackup('그냥 글자'));
  throws('다른 앱의 백업', () => readBackup({'app': '남의앱', 'data': {}}));
  throws('더 새로운 형식', () => readBackup({'v': 99, 'data': {}}));
  throws('att 안이 리스트가 아니다',
      () => decodeStore({'att': {'q1': {'c': 1}}}));
  throws('회차 기록에 필수 칸이 없다',
      () => decodeStore({'exams': {'r1': [{'at': 1, 'score': 1}]}}));
  throws('풀던 묶음의 길이가 어긋난다', () => decodeStore({
        'solo': {'ids': ['a', 'b'], 'ch': [1], 'g': [1, 0], 'at': 0, 't': '', 'sv': 0}
      }));

  stdout.writeln('■ 글자 배율은 가둔다');
  eq('너무 작게', clampScale(0.1), 0.9);
  eq('너무 크게', clampScale(9.0), 1.5);
  eq('저장된 값이 범위 밖이어도', decodeStore({'ts': 99.0}).textScale, 1.5);
  ok('배율 단계 5개', textScaleSteps.length == 5);

  stdout.writeln('\n통과 $_pass · 실패 $_fail');
  if (_fail > 0) exit(1);
}
