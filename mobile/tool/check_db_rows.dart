/// 기록이 테이블 행으로 폈다 접혀도 **한 글자도 안 달라지는지** 확인한다.
///
/// 2단계(저장소 CRUD 전환)에서 가장 위험한 곳이다. 여기서 값이 새면 사용자의
/// 풀이 기록이 조용히 사라지고 되돌릴 수 없다. `flutter test` 가 이 환경에서 못 돌아
/// 순수 Dart 로 본다 (`lib/db_rows.dart` 가 sqflite 를 안 쓰는 이유).
///
/// 특히 볼 것 —
///  · **시도 순서.** 마지막 시도가 오답 여부를 정한다. 뒤집히면 오답노트가 달라진다
///  · **null 과 0 의 구별.** `chosen: null`(무응답)과 `chosen: 0` 은 다르다
///  · 회차 답안 지도의 **정수 키**가 문자열로 굳지 않는지
///  · 설정(글자 배율·알림)이 함께 왕복하는지
///
///   dart run tool/check_db_rows.dart
library;

import 'dart:convert';
import 'dart:io';

import 'package:ncs_bank/backup.dart';
import 'package:ncs_bank/db_rows.dart';

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

/// 왕복시켜 돌려준다.
StoreData roundTrip(StoreData d) => storeFromRows(rowsOf(d));

/// 두 기록이 같은지는 **백업 JSON 으로** 견준다 — 그것이 사용자가 잃는 것의 전부다.
void same(String label, StoreData a, StoreData b) =>
    eq(label, jsonEncode(encodeStore(a)), jsonEncode(encodeStore(b)));

StoreData _sample() => StoreData(
      att: {
        // 순서가 뒤집히면 마지막이 달라져 오답 여부가 바뀐다.
        'q1': [
          Attempt(chosen: 3, ok: false, at: 1000, ms: 4200),
          Attempt(chosen: 1, ok: true, at: 2000, ms: 3100),
        ],
        // 무응답(chosen null)과 시간 미측정(ms null)이 섞인 회차 기록.
        'q2': [Attempt(chosen: null, ok: false, at: 3000)],
        'q3': [Attempt(chosen: 0, ok: false, at: 3500, ms: 0)],
      },
      srs: {
        'q1': Srs(e: 2.7, i: 3, due: 99000),
        'q2': Srs(), // 기본값
      },
      exams: {
        'r1_public': [
          ExamRecord(at: 10, score: 40, n: 50, sec: 3600, auto: false,
              ans: {1: 3, 2: 5, 50: 1}),
          ExamRecord(at: 20, score: 45, n: 50, sec: 3000, auto: true, ans: {}),
        ],
        'r2_korail': [
          ExamRecord(at: 30, score: 20, n: 30, sec: 2100, auto: false,
              ans: {7: 2}),
        ],
      },
      mark: {
        'q1': Mark(bookmark: true, flag: false, memo: '', at: 5),
        'q2': Mark(bookmark: false, flag: true, memo: '선지 ③이 이상하다', at: 6),
      },
      sit: SitState(
        tag: 'r5_nhis', at: 111, endsAt: 222,
        ans: {1: 4, 60: 2}, flag: {3: true, 4: false}, atNo: 7,
      ),
      solo: SoloSession(
        ids: ['a', 'b', 'c'], chosen: [1, null, 3], graded: [true, false, true],
        at: 1, title: '수리능력', savedAt: 9,
      ),
      admin: true,
      textScale: 1.2,
      remind: true,
      remindAt: 21 * 60 + 30,
    );

void main() {
  stdout.writeln('■ 통째로 왕복');
  final s = _sample();
  final r = roundTrip(s);
  same('한 글자도 안 달라진다', s, r);
  same('두 번 돌려도 그대로', s, roundTrip(r));

  stdout.writeln('■ 시도 순서');
  eq('q1 시도 2회', r.att['q1']!.length, 2);
  eq('마지막 시도가 정답', r.att['q1']!.last.ok, true);
  eq('첫 시도가 오답', r.att['q1']!.first.ok, false);
  eq('마지막 고른 선지', r.att['q1']!.last.chosen, 1);

  stdout.writeln('■ null 과 0 을 가른다');
  eq('무응답은 null 로 남는다', r.att['q2']!.first.chosen, null);
  eq('0 은 0 으로 남는다', r.att['q3']!.first.chosen, 0);
  eq('시간 미측정은 null', r.att['q2']!.first.ms, null);
  eq('0ms 는 0', r.att['q3']!.first.ms, 0);

  stdout.writeln('■ 회차');
  eq('r1 이력 2건', r.exams['r1_public']!.length, 2);
  eq('이력 순서 유지', r.exams['r1_public']![0].at, 10);
  eq('답안 지도 키가 정수', r.exams['r1_public']![0].ans[50], 1);
  eq('빈 답안도 빈 채로', r.exams['r1_public']![1].ans.length, 0);
  eq('auto 플래그', r.exams['r1_public']![1].auto, true);

  stdout.writeln('■ 표시');
  eq('북마크', r.mark['q1']!.bookmark, true);
  eq('메모', r.mark['q2']!.memo, '선지 ③이 이상하다');

  stdout.writeln('■ 한 건짜리와 설정');
  eq('응시 중 회차', r.sit!.tag, 'r5_nhis');
  eq('별표 지도', r.sit!.flag[3], true);
  eq('풀던 묶음 길이', r.solo!.ids.length, 3);
  eq('풀던 묶음의 무응답', r.solo!.chosen[1], null);
  eq('관리자', r.admin, true);
  eq('글자 배율', r.textScale, 1.2);
  eq('알림 켬', r.remind, true);
  eq('알림 시각', r.remindAt, 21 * 60 + 30);

  stdout.writeln('■ 빈 기록');
  final empty = StoreData(att: {}, srs: {}, exams: {}, mark: {});
  same('빈 것도 왕복한다', empty, roundTrip(empty));
  eq('응시 중 없음', roundTrip(empty).sit, null);
  eq('풀던 묶음 없음', roundTrip(empty).solo, null);
  eq('기본 배율', roundTrip(empty).textScale, 1.0);
  eq('기본 알림 꺼짐', roundTrip(empty).remind, false);

  stdout.writeln('■ 행의 값이 SQLite 가 받는 것뿐인가');
  final tables = rowsOf(s);
  var bad = <String>[];
  tables.forEach((name, rows) {
    for (final row in rows) {
      row.forEach((k, v) {
        if (v != null && v is! int && v is! double && v is! String) {
          bad.add('$name.$k = ${v.runtimeType}');
        }
      });
    }
  });
  ok('bool 이나 다른 타입이 새지 않았다 ${bad.isEmpty ? "" : bad}', bad.isEmpty);

  stdout.writeln('■ 행 개수');
  eq('시도 행 = 시도 총합', tables[tableAttempt]!.length, 4);
  eq('복습 행 = 문항 수', tables[tableSrs]!.length, 2);
  eq('회차 행 = 이력 총합', tables[tableExam]!.length, 3);
  eq('표시 행', tables[tableMark]!.length, 2);
  eq('설정 행', tables[tableKv]!.length, 6);

  stdout.writeln('■ 스키마');
  // 기록 테이블 다섯 + 인덱스 넷 + 필기 테이블 하나 + 그 인덱스 하나.
  ok('테이블 여섯 + 인덱스 다섯', createSql.length == 11);
  ok('판 번호가 1 이상', dbVersion >= 1);
  ok('올림 목록의 키가 모두 판 번호 이하',
      migrations.keys.every((k) => k <= dbVersion));
  // 새로 깐 기기와 올린 기기의 스키마가 갈리면 한쪽에서만 나는 버그가 생긴다.
  // 판 2 에서 더한 문장이 `createSql` 에도 **그대로** 들어 있어야 한다.
  ok('판 2 의 문장이 createSql 에도 있다',
      migrations[2]!.every(createSql.contains));
  ok('필기 테이블이 판 2 에서 온다', migrations[2] == inkSql);
  ok('필기는 기록 스냅숏에 안 섞인다',
      !tables.containsKey(tableInk));

  stdout.writeln('\n통과 $_pass · 실패 $_fail');
  if (_fail > 0) exit(1);
}
