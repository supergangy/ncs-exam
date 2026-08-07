/// 기기 로컬 기록 — 웹앱의 `Store` 객체와 같은 역할·같은 알고리즘.
/// SharedPreferences 에 JSON 문자열 하나로 저장한다(웹의 localStorage 한 칸과 동일).
library;

import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class Attempt {
  final int? chosen;
  final bool ok;
  final int at; // epoch ms
  Attempt({required this.chosen, required this.ok, required this.at});
  factory Attempt.fromJson(Map<String, dynamic> j) =>
      Attempt(chosen: j['c'], ok: j['k'] == 1, at: j['t']);
  Map<String, dynamic> toJson() => {'c': chosen, 'k': ok ? 1 : 0, 't': at};
}

class Srs {
  double e; // 난이도 계수
  int i; // 간격(일)
  int due; // 다음 복습 epoch ms
  Srs({this.e = 2.5, this.i = 0, this.due = 0});
  factory Srs.fromJson(Map<String, dynamic> j) =>
      Srs(e: (j['e'] as num).toDouble(), i: j['i'], due: j['due']);
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
        ans: (j['ans'] as Map).map((k, v) => MapEntry(int.parse(k), v as int)),
      );
  Map<String, dynamic> toJson() => {
        'at': at, 'score': score, 'n': n, 'sec': sec, 'auto': auto ? 1 : 0,
        'ans': ans.map((k, v) => MapEntry(k.toString(), v)),
      };
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
        ans: (j['ans'] as Map).map((k, v) => MapEntry(int.parse(k), v as int)),
        flag: (j['flag'] as Map).map((k, v) => MapEntry(int.parse(k), v == 1)),
        atNo: j['at_no'],
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

class Store {
  Store._();
  static final Store instance = Store._();
  static const _key = 'ncsbank.v1';

  final Map<String, List<Attempt>> att = {};
  final Map<String, Srs> srs = {};
  final Map<String, List<ExamRecord>> exams = {};
  final Map<String, Mark> mark = {};
  SitState? sit;
  bool admin = false;

  late SharedPreferences _prefs;
  bool _loaded = false;

  Future<void> load() async {
    if (_loaded) return;
    _prefs = await SharedPreferences.getInstance();
    final raw = _prefs.getString(_key);
    if (raw != null) {
      try {
        final d = jsonDecode(raw) as Map<String, dynamic>;
        (d['att'] as Map?)?.forEach((k, v) {
          att[k] = (v as List).map((e) => Attempt.fromJson(e)).toList();
        });
        (d['srs'] as Map?)?.forEach((k, v) => srs[k] = Srs.fromJson(v));
        (d['exams'] as Map?)?.forEach((k, v) {
          exams[k] = (v as List).map((e) => ExamRecord.fromJson(e)).toList();
        });
        (d['mark'] as Map?)?.forEach((k, v) => mark[k] = Mark.fromJson(v));
        if (d['sit'] != null) sit = SitState.fromJson(d['sit']);
        admin = d['admin'] == true;
      } catch (_) {
        // 기록이 깨져 있으면 빈 상태로 시작한다. 예외로 앱이 멎으면 안 된다.
      }
    }
    _loaded = true;
  }

  Future<void> save() async {
    final d = {
      'att': att.map((k, v) => MapEntry(k, v.map((a) => a.toJson()).toList())),
      'srs': srs.map((k, v) => MapEntry(k, v.toJson())),
      'exams': exams.map((k, v) => MapEntry(k, v.map((e) => e.toJson()).toList())),
      'mark': mark.map((k, v) => MapEntry(k, v.toJson())),
      'sit': sit?.toJson(),
      'admin': admin,
    };
    await _prefs.setString(_key, jsonEncode(d));
  }

  Attempt? last(String id) {
    final a = att[id];
    return (a == null || a.isEmpty) ? null : a.last;
  }

  bool tried(String id) => att.containsKey(id) && att[id]!.isNotEmpty;
  bool isWrong(String id) {
    final l = last(id);
    return l != null && !l.ok;
  }

  Future<void> record(String id, int? chosen, bool ok) async {
    (att[id] ??= []).add(Attempt(chosen: chosen, ok: ok, at: _now()));
    _schedule(id, ok);
    await save();
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
    return allIds.where((id) => srs[id] != null && srs[id]!.due <= now).toList();
  }

  double? best(String tag) {
    final h = exams[tag];
    if (h == null || h.isEmpty) return null;
    return h.map((r) => r.score / r.n).reduce((a, b) => a > b ? a : b);
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
