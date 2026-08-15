/// 기록을 **테이블 행으로 펴고 다시 접는** 곳. sqflite 도 Flutter 도 부르지 않는다.
///
/// [backup.dart] 와 같은 규율이다 — 실제 DB 입출력은 [db.dart] 가 하고,
/// 여기는 순수 변환만 해서 `dart run tool/check_db_rows.dart` 로 검증한다.
/// **기록을 잃는 사고는 대개 이 변환에서 난다.** 그래서 갈라 두었다.
///
/// ## 왜 테이블인가
///
/// 지금은 `SharedPreferences` 한 칸에 JSON 전체를 넣는다. 한 문항을 풀 때마다
/// 기록 전부를 다시 직렬화해 덮어쓰고(`store.dart` 의 `_write`), 오답·복습·통계는
/// 전 문항을 순회한다. 문항이 늘고 필기가 들어오면 못 버틴다.
///
/// ## 바꾸지 않는 것
///
/// [StoreData] 의 모양과 [encodeStore]/[decodeStore] 의 JSON 형식은 **그대로 둔다.**
/// 웹판(`app/app.js`)과 1:1로 맞춰 둔 것이고 백업 파일이 그 형식이다.
/// 바뀌는 것은 기기에 어떻게 눕느냐뿐이다.
library;

import 'dart:convert';

import 'backup.dart';

/// 스키마 판. 올릴 때는 [migrations] 에 한 줄 더한다.
const dbVersion = 1;

const tableAttempt = 'attempt';
const tableSrs = 'srs';
const tableExam = 'exam_result';
const tableMark = 'mark';
const tableKv = 'kv';

/// `kv` 에 들어가는 열쇠들. 한 건뿐이라 테이블을 따로 두지 않는다.
const kvSit = 'sit';
const kvSolo = 'solo';
const kvAdmin = 'admin';
const kvTextScale = 'ts';
const kvRemind = 'rm';
const kvRemindAt = 'rmAt';

/// 처음 만들 때 실행할 것.
///
/// `seq` 는 **순서를 지키려고** 둔다 — `att` 의 마지막 시도가 오답노트를 정하고
/// `exams` 는 이력 순서가 곧 응시 순서다. SQLite 는 행 순서를 보장하지 않는다.
const createSql = <String>[
  '''
  CREATE TABLE $tableAttempt (
    item_id TEXT NOT NULL,
    seq     INTEGER NOT NULL,
    chosen  INTEGER,
    ok      INTEGER NOT NULL,
    at      INTEGER NOT NULL,
    ms      INTEGER,
    PRIMARY KEY (item_id, seq)
  )''',
  '''
  CREATE TABLE $tableSrs (
    item_id TEXT PRIMARY KEY,
    e       REAL NOT NULL,
    i       INTEGER NOT NULL,
    due     INTEGER NOT NULL
  )''',
  '''
  CREATE TABLE $tableExam (
    tag   TEXT NOT NULL,
    seq   INTEGER NOT NULL,
    at    INTEGER NOT NULL,
    score INTEGER NOT NULL,
    n     INTEGER NOT NULL,
    sec   INTEGER NOT NULL,
    auto  INTEGER NOT NULL,
    ans   TEXT NOT NULL,
    PRIMARY KEY (tag, seq)
  )''',
  '''
  CREATE TABLE $tableMark (
    item_id  TEXT PRIMARY KEY,
    bookmark INTEGER NOT NULL,
    flag     INTEGER NOT NULL,
    memo     TEXT NOT NULL,
    at       INTEGER NOT NULL
  )''',
  '''
  CREATE TABLE $tableKv (
    k TEXT PRIMARY KEY,
    v TEXT
  )''',
  // 복습 대상을 고를 때 전 문항을 훑지 않게 한다 — 이것이 테이블로 옮긴 이유다.
  'CREATE INDEX idx_srs_due ON $tableSrs (due)',
  // 오답노트·북마크 목록도 마찬가지.
  'CREATE INDEX idx_mark_flag ON $tableMark (flag)',
  'CREATE INDEX idx_mark_bookmark ON $tableMark (bookmark)',
  'CREATE INDEX idx_attempt_at ON $tableAttempt (at)',
];

/// 판 올림. `dbVersion` 을 올릴 때 여기에 더한다.
/// 키는 **올라가는 판 번호**다 — 2 를 넣으면 1 → 2 에서 돈다.
const migrations = <int, List<String>>{};

// ─────────────────────────────────────────────────────── 펴기

/// [StoreData] 를 테이블별 행 목록으로 편다.
///
/// 돌려주는 것은 `테이블 이름 → 행 목록` 이다. 값은 SQLite 가 받는 것만 쓴다 —
/// `int` · `double` · `String` · `null`. **`bool` 은 없다.**
Map<String, List<Map<String, Object?>>> rowsOf(StoreData d) {
  final attempts = <Map<String, Object?>>[];
  d.att.forEach((id, list) {
    for (var i = 0; i < list.length; i++) {
      final a = list[i];
      attempts.add({
        'item_id': id, 'seq': i,
        'chosen': a.chosen, 'ok': a.ok ? 1 : 0, 'at': a.at, 'ms': a.ms,
      });
    }
  });

  final srs = <Map<String, Object?>>[];
  d.srs.forEach((id, s) {
    srs.add({'item_id': id, 'e': s.e, 'i': s.i, 'due': s.due});
  });

  final exams = <Map<String, Object?>>[];
  d.exams.forEach((tag, list) {
    for (var i = 0; i < list.length; i++) {
      final r = list[i];
      exams.add({
        'tag': tag, 'seq': i, 'at': r.at, 'score': r.score, 'n': r.n,
        'sec': r.sec, 'auto': r.auto ? 1 : 0,
        // 번호→선지 지도는 칸으로 펴 봐야 쓸 일이 없다. JSON 한 칸으로 둔다.
        'ans': jsonEncode(r.ans.map((k, v) => MapEntry(k.toString(), v))),
      });
    }
  });

  final marks = <Map<String, Object?>>[];
  d.mark.forEach((id, m) {
    marks.add({
      'item_id': id, 'bookmark': m.bookmark ? 1 : 0, 'flag': m.flag ? 1 : 0,
      'memo': m.memo, 'at': m.at,
    });
  });

  final kv = <Map<String, Object?>>[
    {'k': kvSit, 'v': d.sit == null ? null : jsonEncode(d.sit!.toJson())},
    {'k': kvSolo, 'v': d.solo == null ? null : jsonEncode(d.solo!.toJson())},
    {'k': kvAdmin, 'v': d.admin ? '1' : '0'},
    {'k': kvTextScale, 'v': d.textScale.toString()},
    {'k': kvRemind, 'v': d.remind ? '1' : '0'},
    {'k': kvRemindAt, 'v': d.remindAt.toString()},
  ];

  return {
    tableAttempt: attempts,
    tableSrs: srs,
    tableExam: exams,
    tableMark: marks,
    tableKv: kv,
  };
}

// ─────────────────────────────────────────────────────── 접기

/// 행 목록을 [StoreData] 로 접는다.
///
/// **`seq` 로 정렬한다.** SQLite 가 넣은 순서로 돌려준다는 보장이 없고,
/// `att` 는 마지막 시도가 오답 여부를 정하므로 순서가 뒤집히면 값이 달라진다.
StoreData storeFromRows(Map<String, List<Map<String, Object?>>> t) {
  int asInt(Object? v, [int or = 0]) =>
      v is int ? v : (v is num ? v.toInt() : (v is String ? int.tryParse(v) ?? or : or));
  double asDouble(Object? v, [double or = 0]) => v is num
      ? v.toDouble()
      : (v is String ? double.tryParse(v) ?? or : or);

  final att = <String, List<Attempt>>{};
  final attRows = [...(t[tableAttempt] ?? const [])]
    ..sort((a, b) {
      final c = (a['item_id'] as String).compareTo(b['item_id'] as String);
      return c != 0 ? c : asInt(a['seq']).compareTo(asInt(b['seq']));
    });
  for (final r in attRows) {
    (att[r['item_id'] as String] ??= []).add(Attempt(
      chosen: r['chosen'] == null ? null : asInt(r['chosen']),
      ok: asInt(r['ok']) == 1,
      at: asInt(r['at']),
      ms: r['ms'] == null ? null : asInt(r['ms']),
    ));
  }

  final srs = <String, Srs>{};
  for (final r in t[tableSrs] ?? const []) {
    srs[r['item_id'] as String] = Srs(
      e: asDouble(r['e'], 2.5), i: asInt(r['i']), due: asInt(r['due']),
    );
  }

  final exams = <String, List<ExamRecord>>{};
  final examRows = [...(t[tableExam] ?? const [])]
    ..sort((a, b) {
      final c = (a['tag'] as String).compareTo(b['tag'] as String);
      return c != 0 ? c : asInt(a['seq']).compareTo(asInt(b['seq']));
    });
  for (final r in examRows) {
    final raw = (jsonDecode(r['ans'] as String? ?? '{}') as Map)
        .cast<String, dynamic>();
    (exams[r['tag'] as String] ??= []).add(ExamRecord(
      at: asInt(r['at']), score: asInt(r['score']), n: asInt(r['n']),
      sec: asInt(r['sec']), auto: asInt(r['auto']) == 1,
      ans: {for (final e in raw.entries) int.parse(e.key): asInt(e.value)},
    ));
  }

  final mark = <String, Mark>{};
  for (final r in t[tableMark] ?? const []) {
    mark[r['item_id'] as String] = Mark(
      bookmark: asInt(r['bookmark']) == 1,
      flag: asInt(r['flag']) == 1,
      memo: (r['memo'] as String?) ?? '',
      at: asInt(r['at']),
    );
  }

  final kv = <String, String?>{
    for (final r in t[tableKv] ?? const []) r['k'] as String: r['v'] as String?,
  };
  final sitRaw = kv[kvSit];
  final soloRaw = kv[kvSolo];

  return StoreData(
    att: att, srs: srs, exams: exams, mark: mark,
    sit: sitRaw == null
        ? null
        : SitState.fromJson((jsonDecode(sitRaw) as Map).cast<String, dynamic>()),
    solo: soloRaw == null
        ? null
        : SoloSession.fromJson(
            (jsonDecode(soloRaw) as Map).cast<String, dynamic>()),
    admin: kv[kvAdmin] == '1',
    textScale: clampScale(asDouble(kv[kvTextScale], 1.0)),
    remind: kv[kvRemind] == '1',
    remindAt: clampRemindAt(asInt(kv[kvRemindAt], defaultRemindAt)),
  );
}
