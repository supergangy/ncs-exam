/// sqflite 입출력. **행을 만들고 읽는 규칙은 [db_rows.dart] 에 있다.**
///
/// 여기는 파일을 열고 SQL 을 던지는 일만 한다. 그래야 위험한 쪽(변환)을
/// Flutter 없이 `dart run tool/check_db_rows.dart` 로 검증할 수 있다.
///
/// ## 왜 부분 갱신인가
///
/// 예전에는 한 문항을 풀 때마다 기록 **전체**를 다시 직렬화해 덮어썼다
/// (`SharedPreferences` 한 칸). 그 값이 부담이라 600ms 디바운스를 걸어 두었는데
/// 그것은 고친 것이 아니라 미뤄 둔 것이었다. 여기서는 바뀐 행만 쓴다.
library;

import 'package:flutter/foundation.dart';
import 'package:sqflite/sqflite.dart';

import 'backup.dart';
import 'db_rows.dart';

class Db {
  Db._();
  static final Db instance = Db._();

  static const fileName = 'ncsbank.db';

  Database? _db;
  bool get isOpen => _db != null;

  Future<Database> open() async {
    final cur = _db;
    if (cur != null) return cur;
    final dir = await getDatabasesPath();
    final db = await openDatabase(
      '$dir/$fileName',
      version: dbVersion,
      onCreate: (d, _) async {
        final b = d.batch();
        for (final sql in createSql) {
          b.execute(sql);
        }
        await b.commit(noResult: true);
      },
      onUpgrade: (d, from, to) async {
        for (var v = from + 1; v <= to; v++) {
          for (final sql in migrations[v] ?? const <String>[]) {
            await d.execute(sql);
          }
        }
      },
    );
    _db = db;
    return db;
  }

  Future<void> close() async {
    await _db?.close();
    _db = null;
  }

  /// 비어 있나 — 마이그레이션을 할지 정할 때 본다.
  /// `kv` 는 설정이라 기록이 없어도 채워질 수 있으므로 **기록 테이블만** 본다.
  Future<bool> isEmpty() async {
    final db = await open();
    for (final t in [tableAttempt, tableSrs, tableExam, tableMark]) {
      final n = Sqflite.firstIntValue(
          await db.rawQuery('SELECT COUNT(*) FROM $t')) ?? 0;
      if (n > 0) return false;
    }
    return true;
  }

  Future<StoreData> readAll() async {
    final db = await open();
    return storeFromRows({
      for (final t in [tableAttempt, tableSrs, tableExam, tableMark, tableKv])
        t: await db.query(t),
    });
  }

  /// 통째로 갈아 끼운다. **마이그레이션과 백업 복원에만** 쓴다 —
  /// 평소 저장에 쓰면 옛 방식과 다를 게 없다.
  Future<void> writeAll(StoreData d) async {
    final db = await open();
    final rows = rowsOf(d);
    await db.transaction((tx) async {
      for (final t in [tableAttempt, tableSrs, tableExam, tableMark, tableKv]) {
        await tx.delete(t);
      }
      final b = tx.batch();
      rows.forEach((table, list) {
        for (final r in list) {
          b.insert(table, r, conflictAlgorithm: ConflictAlgorithm.replace);
        }
      });
      await b.commit(noResult: true);
    });
  }

  /// 바뀐 것만 쓴다. 부른 쪽이 무엇이 더러운지 알려 준다.
  ///
  /// `att`·`srs`·`mark` 는 문항 id 단위, `exams` 는 회차 tag 단위다.
  /// 지도에서 사라진 키는 **행도 지운다** — 남겨 두면 되살아난다.
  Future<void> writeDirty(
    StoreData d, {
    required Set<String> attIds,
    required Set<String> srsIds,
    required Set<String> markIds,
    required Set<String> examTags,
    required bool kv,
  }) async {
    if (attIds.isEmpty &&
        srsIds.isEmpty &&
        markIds.isEmpty &&
        examTags.isEmpty &&
        !kv) {
      return;
    }
    final db = await open();
    await db.transaction((tx) async {
      final b = tx.batch();

      for (final id in attIds) {
        b.delete(tableAttempt, where: 'item_id = ?', whereArgs: [id]);
        final list = d.att[id];
        if (list == null) continue;
        for (var i = 0; i < list.length; i++) {
          final a = list[i];
          b.insert(tableAttempt, {
            'item_id': id, 'seq': i, 'chosen': a.chosen,
            'ok': a.ok ? 1 : 0, 'at': a.at, 'ms': a.ms,
          }, conflictAlgorithm: ConflictAlgorithm.replace);
        }
      }

      for (final id in srsIds) {
        final s = d.srs[id];
        if (s == null) {
          b.delete(tableSrs, where: 'item_id = ?', whereArgs: [id]);
        } else {
          b.insert(tableSrs, {'item_id': id, 'e': s.e, 'i': s.i, 'due': s.due},
              conflictAlgorithm: ConflictAlgorithm.replace);
        }
      }

      for (final id in markIds) {
        final m = d.mark[id];
        if (m == null) {
          b.delete(tableMark, where: 'item_id = ?', whereArgs: [id]);
        } else {
          b.insert(tableMark, {
            'item_id': id, 'bookmark': m.bookmark ? 1 : 0,
            'flag': m.flag ? 1 : 0, 'memo': m.memo, 'at': m.at,
          }, conflictAlgorithm: ConflictAlgorithm.replace);
        }
      }

      for (final tag in examTags) {
        b.delete(tableExam, where: 'tag = ?', whereArgs: [tag]);
        final list = d.exams[tag];
        if (list == null) continue;
        // 회차 이력은 한 회차에 몇 건뿐이라 통째로 다시 쓴다.
        for (final r in list) {
          final flat = rowsOf(StoreData(
            att: const {}, srs: const {}, mark: const {},
            exams: {tag: [r]},
          ))[tableExam]!.first;
          b.insert(tableExam, {...flat, 'seq': list.indexOf(r)},
              conflictAlgorithm: ConflictAlgorithm.replace);
        }
      }

      if (kv) {
        for (final r in rowsOf(d)[tableKv]!) {
          b.insert(tableKv, r, conflictAlgorithm: ConflictAlgorithm.replace);
        }
      }

      await b.commit(noResult: true);
    });
  }

  /// 기록만 지운다. 설정(`kv`)은 남긴다 — 글자 배율과 알림은 기록이 아니다.
  Future<void> clearRecords() async {
    final db = await open();
    await db.transaction((tx) async {
      for (final t in [tableAttempt, tableSrs, tableExam, tableMark]) {
        await tx.delete(t);
      }
    });
  }

  /// 복습 대상 개수 — 전 문항을 훑지 않는다. 인덱스 `idx_srs_due` 를 탄다.
  Future<int> dueCount(int now) async {
    final db = await open();
    return Sqflite.firstIntValue(await db.rawQuery(
            'SELECT COUNT(*) FROM $tableSrs WHERE due <= ?', [now])) ??
        0;
  }

  Future<void> deleteFile() async {
    final dir = await getDatabasesPath();
    await close();
    try {
      await deleteDatabase('$dir/$fileName');
    } catch (err) {
      debugPrint('DB 파일을 지우지 못했다: $err');
    }
  }
}
