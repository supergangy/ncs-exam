/// 기기 로컬 기록 — 웹앱의 `Store` 객체와 같은 역할·같은 알고리즘.
/// SharedPreferences 에 JSON 문자열 하나로 저장한다(웹의 localStorage 한 칸과 동일).
///
/// `ChangeNotifier` 인 이유 — 탭 다섯 개가 한 화면에 살아 있어서(`IndexedStack`),
/// 오답 탭에서 문제를 풀면 홈 탭의 진도·오답 개수도 함께 바뀌어야 한다.
/// 안 그러면 앱을 껐다 켤 때까지 옛 숫자가 붙어 있는다.
library;

import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class Attempt {
  final int? chosen;
  final bool ok;
  final int at; // epoch ms
  Attempt({required this.chosen, required this.ok, required this.at});
  factory Attempt.fromJson(Map<String, dynamic> j) =>
      Attempt(chosen: j['c'], ok: j['k'] == 1, at: j['t'] ?? 0);
  Map<String, dynamic> toJson() => {'c': chosen, 'k': ok ? 1 : 0, 't': at};
}

class Srs {
  double e; // 난이도 계수
  int i; // 간격(일)
  int due; // 다음 복습 epoch ms
  Srs({this.e = 2.5, this.i = 0, this.due = 0});
  factory Srs.fromJson(Map<String, dynamic> j) => Srs(
        e: (j['e'] as num?)?.toDouble() ?? 2.5,
        i: (j['i'] as num?)?.toInt() ?? 0,
        due: (j['due'] as num?)?.toInt() ?? 0,
      );
  Map<String, dynamic> toJson() => {'e': e, 'i': i, 'due': due};
}

class ExamRecord {
  final int at;
  final int score, n, sec;
  final bool auto;
  final Map<int, int> ans; // 문항 번호 → 고른 선지
  ExamRecord({
    required this.at, required this.score, required this.n,
    required this.sec, required this.auto, required this.ans,
  });
  factory ExamRecord.fromJson(Map<String, dynamic> j) => ExamRecord(
        at: j['at'], score: j['score'], n: j['n'], sec: j['sec'],
        auto: j['auto'] == 1,
        ans: (j['ans'] as Map).map((k, v) => MapEntry(int.parse(k), (v as num).toInt())),
      );
  Map<String, dynamic> toJson() => {
        'at': at, 'score': score, 'n': n, 'sec': sec, 'auto': auto ? 1 : 0,
        'ans': ans.map((k, v) => MapEntry(k.toString(), v)),
      };
  double get rate => n == 0 ? 0 : score / n;
}

/// 응시 중인 회차 — 한 번에 하나만 존재한다.
class SitState {
  final String tag;
  final int at, endsAt;
  Map<int, int> ans; // 번호 → 고른 선지
  Map<int, bool> flag; // 번호 → 별표
  int atNo; // 지금 보고 있는 번호
  SitState({
    required this.tag, required this.at, required this.endsAt,
    required this.ans, required this.flag, required this.atNo,
  });
  factory SitState.fromJson(Map<String, dynamic> j) => SitState(
        tag: j['tag'], at: j['at'], endsAt: j['endsAt'],
        ans: (j['ans'] as Map).map((k, v) => MapEntry(int.parse(k), (v as num).toInt())),
        flag: (j['flag'] as Map).map((k, v) => MapEntry(int.parse(k), v == 1)),
        atNo: j['at_no'] ?? 1,
      );
  Map<String, dynamic> toJson() => {
        'tag': tag, 'at': at, 'endsAt': endsAt,
        'ans': ans.map((k, v) => MapEntry(k.toString(), v)),
        'flag': flag.map((k, v) => MapEntry(k.toString(), v ? 1 : 0)),
        'at_no': atNo,
      };
}

class Mark {
  bool bookmark, flag;
  String memo;
  int at;
  Mark({this.bookmark = false, this.flag = false, this.memo = '', this.at = 0});
  factory Mark.fromJson(Map<String, dynamic> j) => Mark(
        bookmark: j['b'] == 1, flag: j['f'] == 1, memo: j['memo'] ?? '',
        at: j['at'] ?? 0,
      );
  Map<String, dynamic> toJson() =>
      {'b': bookmark ? 1 : 0, 'f': flag ? 1 : 0, 'memo': memo, 'at': at};
  bool get isEmpty => !bookmark && !flag && memo.isEmpty;
}

class Store extends ChangeNotifier {
  Store._();
  static final Store instance = Store._();
  static const _key = 'ncsbank.v1';
  static const _backupKey = 'ncsbank.v1.broken';

  final Map<String, List<Attempt>> att = {};
  final Map<String, Srs> srs = {};
  final Map<String, List<ExamRecord>> exams = {};
  final Map<String, Mark> mark = {};
  SitState? sit;
  bool admin = false;

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
      // **먼저 통째로 읽고, 다 읽힌 뒤에야 옮긴다.** 중간에 터지면 반만 남는데,
      // 그 상태로 다음 저장이 일어나면 못 읽은 나머지가 영영 지워진다.
      final d = jsonDecode(raw) as Map<String, dynamic>;
      final a = <String, List<Attempt>>{};
      (d['att'] as Map?)?.forEach((k, v) {
        a[k] = (v as List).map((e) => Attempt.fromJson(e)).toList();
      });
      final s = <String, Srs>{};
      (d['srs'] as Map?)?.forEach((k, v) => s[k] = Srs.fromJson(v));
      final e = <String, List<ExamRecord>>{};
      (d['exams'] as Map?)?.forEach((k, v) {
        e[k] = (v as List).map((x) => ExamRecord.fromJson(x)).toList();
      });
      final m = <String, Mark>{};
      (d['mark'] as Map?)?.forEach((k, v) => m[k] = Mark.fromJson(v));
      final st = d['sit'] == null ? null : SitState.fromJson(d['sit']);

      att..clear()..addAll(a);
      srs..clear()..addAll(s);
      exams..clear()..addAll(e);
      mark..clear()..addAll(m);
      sit = st;
      admin = d['admin'] == true;
    } catch (err) {
      // 못 읽은 원본은 따로 남긴다 — 덮어써 버리면 되살릴 길이 없다.
      debugPrint('기록을 읽지 못했다: $err');
      await _prefs.setString(_backupKey, raw);
      att.clear(); srs.clear(); exams.clear(); mark.clear();
      sit = null; admin = false;
    }
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
    final d = {
      'att': att.map((k, v) => MapEntry(k, v.map((a) => a.toJson()).toList())),
      'srs': srs.map((k, v) => MapEntry(k, v.toJson())),
      'exams': exams.map((k, v) => MapEntry(k, v.map((e) => e.toJson()).toList())),
      'mark': mark.map((k, v) => MapEntry(k, v.toJson())),
      'sit': sit?.toJson(),
      'admin': admin,
    };
    final ok = await _prefs.setString(_key, jsonEncode(d));
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

  Future<void> record(String id, int? chosen, bool ok) async {
    recordQuiet(id, chosen, ok);
    await save();
  }

  /// 저장하지 않고 기록만 올린다. 회차 제출처럼 **한 번에 수십 건**을 넣을 때 쓴다 —
  /// 건건이 저장하면 저장소 전체를 그 횟수만큼 다시 쓴다. 부른 쪽이 마지막에 [save] 한다.
  void recordQuiet(String id, int? chosen, bool ok) {
    final list = att[id] ??= [];
    list.add(Attempt(chosen: chosen, ok: ok, at: _now()));
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

  double? best(String tag) {
    final h = exams[tag];
    if (h == null || h.isEmpty) return null;
    return h.map((r) => r.rate).reduce((a, b) => a > b ? a : b);
  }

  List<ExamRecord> history(String tag) => exams[tag] ?? const [];

  Mark markOf(String id) => mark[id] ?? Mark();

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
    att.clear(); srs.clear(); exams.clear(); mark.clear();
    sit = null; admin = false;
    await save();
  }

  Future<void> setSit(SitState? s) async {
    sit = s;
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

  int _now() => DateTime.now().millisecondsSinceEpoch;
}
