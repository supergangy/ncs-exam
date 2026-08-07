/// 기기 로컬 기록 — 웹앱의 `Store` 객체와 같은 역할·같은 알고리즘.
/// SharedPreferences 에 JSON 문자열 하나로 저장한다(웹의 localStorage 한 칸과 동일).
///
/// 여기는 **상태를 들고 저장하고 알리는** 일만 한다.
/// 클래스와 JSON 왕복은 [backup.dart] 에 있다 — Flutter 없이 검증하기 위해서다.
///
/// `ChangeNotifier` 인 이유 — 탭 다섯 개가 한 화면에 살아 있어서(`IndexedStack`),
/// 오답 탭에서 문제를 풀면 홈 탭의 진도·오답 개수도 함께 바뀌어야 한다.
library;

import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'backup.dart';

export 'backup.dart';

class Store extends ChangeNotifier {
  Store._();
  static final Store instance = Store._();
  static const _key = 'ncsbank.v1';
  static const _brokenKey = 'ncsbank.v1.broken';
  static const _prevKey = 'ncsbank.v1.prev';

  final Map<String, List<Attempt>> att = {};
  final Map<String, Srs> srs = {};
  final Map<String, List<ExamRecord>> exams = {};
  final Map<String, Mark> mark = {};
  SitState? sit;
  SoloSession? solo;
  bool admin = false;
  double textScale = 1.0;

  late SharedPreferences _prefs;
  bool _loaded = false;
  Timer? _flush;
  bool _dirty = false;

  Future<void> load() async {
    if (_loaded) return;
    _prefs = await SharedPreferences.getInstance();
    final raw = _prefs.getString(_key);
    _loaded = true;
    if (raw == null) return;
    try {
      _adopt(decodeStore((jsonDecode(raw) as Map).cast<String, dynamic>()));
    } catch (err) {
      // 못 읽은 원본은 따로 남긴다 — 덮어써 버리면 되살릴 길이 없다.
      debugPrint('기록을 읽지 못했다: $err');
      await _prefs.setString(_brokenKey, raw);
      _adopt(StoreData(att: {}, srs: {}, exams: {}, mark: {}));
    }
  }

  /// 다 읽힌 뒤에야 옮긴다. 중간에 터져서 반만 남으면, 다음 저장이
  /// 못 읽은 나머지를 영영 지운다.
  void _adopt(StoreData d) {
    att..clear()..addAll(d.att);
    srs..clear()..addAll(d.srs);
    exams..clear()..addAll(d.exams);
    mark..clear()..addAll(d.mark);
    sit = d.sit;
    solo = d.solo;
    admin = d.admin;
    textScale = d.textScale;
  }

  StoreData snapshot() => StoreData(
        att: att, srs: srs, exams: exams, mark: mark,
        sit: sit, solo: solo, admin: admin, textScale: textScale,
      );

  /// 백업 파일에 담을 것.
  Map<String, dynamic> exportMap(DateTime at) => wrapBackup(snapshot(), at);

  /// 백업으로 **통째로 바꾼다.** 부르기 전에 [readBackup] 으로 검증돼 있어야 한다.
  /// 덮어쓰기 직전 지금 기록을 따로 남긴다 — 잘못 골랐을 때 되돌릴 여지.
  Future<void> importAll(StoreData d) async {
    final now = _prefs.getString(_key);
    if (now != null) await _prefs.setString(_prevKey, now);
    _adopt(d);
    await save();
  }

  /// 바로 저장한다. 제출·설정처럼 잃으면 안 되는 순간에 쓴다.
  Future<void> save() async {
    _flush?.cancel();
    _flush = null;
    await _write();
  }

  /// 곧 저장한다. 선지 탭·쪽 넘김처럼 **자주 일어나는** 것에 쓴다 —
  /// 건건이 쓰면 기록 전체를 그때마다 다시 직렬화한다.
  void saveSoon() {
    _dirty = true;
    notifyListeners();
    _flush ??= Timer(const Duration(milliseconds: 600), () {
      _flush = null;
      if (_dirty) _write();
    });
  }

  /// 앱이 백그라운드로 갈 때 부른다. 미뤄 둔 저장을 흘려보낸다.
  Future<void> flush() async {
    if (_dirty || _flush != null) await save();
  }

  Future<void> _write() async {
    if (!_loaded) return;
    _dirty = false;
    final ok = await _prefs.setString(_key, jsonEncode(encodeStore(snapshot())));
    if (!ok) debugPrint('기록을 저장하지 못했다 — 저장 공간을 확인해 주세요');
    notifyListeners();
  }

  Attempt? last(String id) {
    final a = att[id];
    return (a == null || a.isEmpty) ? null : a.last;
  }

  bool tried(String id) => att[id]?.isNotEmpty ?? false;
  bool isWrong(String id) {
    final l = last(id);
    return l != null && !l.ok;
  }

  int wrongCount(Iterable<String> ids) => ids.where(isWrong).length;

  Future<void> record(String id, int? chosen, bool ok, {int? ms}) async {
    recordQuiet(id, chosen, ok, ms: ms);
    await save();
  }

  /// 저장하지 않고 기록만 올린다. 회차 제출처럼 **한 번에 수십 건**을 넣을 때 쓴다 —
  /// 건건이 저장하면 저장소 전체를 그 횟수만큼 다시 쓴다. 부른 쪽이 마지막에 [save] 한다.
  void recordQuiet(String id, int? chosen, bool ok, {int? ms}) {
    final list = att[id] ??= [];
    list.add(Attempt(chosen: chosen, ok: ok, at: _now(), ms: ms));
    // 한 문항을 수백 번 풀어도 기록이 무한정 늘지 않게 한다. 최근 것만 쓸모가 있다.
    if (list.length > 40) list.removeRange(0, list.length - 40);
    _schedule(id, ok);
  }

  /// SM-2 를 줄인 것. 틀리면 처음으로, 맞히면 간격이 벌어진다.
  void _schedule(String id, bool ok) {
    final s = srs[id] ?? Srs();
    if (!ok) {
      s.e = (s.e - 0.2).clamp(1.3, 2.8);
      s.i = 0;
      s.due = _now() + 10 * 60 * 1000; // 10분 뒤
    } else {
      s.e = (s.e + 0.1).clamp(1.3, 2.8);
      s.i = s.i == 0 ? 1 : (s.i == 1 ? 3 : (s.i * s.e).round());
      s.due = _now() + s.i * 86400000;
    }
    srs[id] = s;
  }

  List<String> dueIds(Iterable<String> allIds) {
    final now = _now();
    return allIds.where((id) {
      final s = srs[id];
      return s != null && s.due <= now;
    }).toList();
  }

  /// 다음 복습까지 남은 날 — 복습할 것이 없을 때 안내에 쓴다.
  int? nextDueInDays(Iterable<String> allIds) {
    int? soonest;
    for (final id in allIds) {
      final s = srs[id];
      if (s == null) continue;
      if (soonest == null || s.due < soonest) soonest = s.due;
    }
    if (soonest == null) return null;
    return ((soonest - _now()) / 86400000).ceil();
  }

  /// 낱개 풀이의 평균 소요 시간(ms). 잰 기록이 없으면 null.
  /// 회차 응시는 채점 순간이 없어 시간을 재지 않으므로 여기 안 들어온다.
  int? avgSolveMs([Iterable<String>? ids]) {
    var sum = 0, n = 0;
    final keys = ids ?? att.keys;
    for (final id in keys) {
      for (final a in att[id] ?? const <Attempt>[]) {
        if (a.ms != null) {
          sum += a.ms!;
          n++;
        }
      }
    }
    return n == 0 ? null : sum ~/ n;
  }

  double? best(String tag) {
    final h = exams[tag];
    if (h == null || h.isEmpty) return null;
    return h.map((r) => r.rate).reduce((a, b) => a > b ? a : b);
  }

  List<ExamRecord> history(String tag) => exams[tag] ?? const [];

  Mark markOf(String id) => mark[id] ?? Mark();
  bool isMarked(String id) {
    final m = mark[id];
    return m != null && (m.bookmark || m.flag);
  }

  Future<void> toggleMark(String id, {bool? bookmark, bool? flag}) async {
    final m = mark[id] ?? Mark();
    if (bookmark != null) m.bookmark = bookmark;
    if (flag != null) m.flag = flag;
    m.at = _now();
    if (m.isEmpty) {
      mark.remove(id);
    } else {
      mark[id] = m;
    }
    await save();
  }

  Future<void> setMemo(String id, String memo) async {
    final m = mark[id] ?? Mark();
    m.memo = memo;
    m.at = _now();
    if (memo.isNotEmpty) m.flag = true;
    if (m.isEmpty) {
      mark.remove(id);
    } else {
      mark[id] = m;
    }
    await save();
  }

  /// 「확인 필요」 표시와 메모를 함께 지운다.
  /// 이게 없어서 한 번 쓴 메모를 지울 길이 없었다 — 표시만 꺼지고 메모는 남아
  /// 목록에도 뜨고 내보내기에도 실려 나갔다.
  Future<void> clearFlag(String id) async {
    final m = mark[id];
    if (m == null) return;
    m.flag = false;
    m.memo = '';
    m.at = _now();
    if (m.isEmpty) mark.remove(id);
    await save();
  }

  List<String> marked({required bool flag}) {
    final es = mark.entries.where((e) => flag ? e.value.flag : e.value.bookmark).toList()
      ..sort((a, b) => b.value.at.compareTo(a.value.at));
    return es.map((e) => e.key).toList();
  }

  Future<void> reset() async {
    _adopt(StoreData(att: {}, srs: {}, exams: {}, mark: {}, textScale: textScale));
    await save();
  }

  Future<void> setSit(SitState? s) async {
    sit = s;
    await save();
  }

  Future<void> setSolo(SoloSession? s) async {
    solo = s;
    await save();
  }

  Future<void> addExam(String tag, ExamRecord rec) async {
    (exams[tag] ??= []).add(rec);
    await save();
  }

  Future<void> setAdmin(bool v) async {
    admin = v;
    await save();
  }

  Future<void> setTextScale(double v) async {
    textScale = clampScale(v);
    await save();
  }

  int _now() => DateTime.now().millisecondsSinceEpoch;
}
