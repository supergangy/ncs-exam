/// 에셋에 번들된 bank.json/admin.json 을 읽어 조회한다. 웹앱의 `DB` 객체와 같다.
///
/// 조회는 전부 **불러올 때 한 번** 색인해 둔다. 화면이 그려질 때마다 426문항을
/// 훑으면 탭을 옮길 때마다 수만 번을 돈다 — 홈 한 번 그리는 데 직렬 수만큼 전수 조사를 했다.
library;

import 'dart:convert';
import 'package:flutter/services.dart' show rootBundle;
import 'models.dart';
import 'round_lock.dart';
import 'store.dart';
import 'text.dart';
export 'models.dart';

class Repo {
  Repo._();
  static final Repo instance = Repo._();

  late BankData bank;
  Map<String, AdminInfo>? admin; // 관리자 모드일 때만 채운다
  bool _loaded = false;

  final Map<String, Item> _byId = {};
  final Map<String, Track> _trackById = {};
  final Map<String, RoundEntry> _roundByTag = {};
  final Map<String, List<Item>> _byTrack = {};
  final Map<String, List<Item>> _byTrackSubject = {};
  final Map<String, List<Item>> _byTrackSubjectType = {};
  final Map<int, List<Item>> _byKeyword = {};
  final Map<String, List<Item>> _byRound = {};
  final Map<String, List<SubjectEntry>> _subjectsByTrack = {};
  final Map<String, List<TypeEntry>> _typesByTrackSubject = {};
  final Map<String, List<TypeGroup>> _groupsByTrackSubject = {};
  /// (과목, 세부유형) → 대유형. 문항을 대유형으로 거를 때 쓴다.
  final Map<String, String> _groupOf = {};
  /// 키워드 색인 → 그 키워드를 쓰는 첫 문항의 과목. 키워드 화면이 묶는 데 쓴다.
  final Map<int, String> _keywordSubject = {};
  /// 검색용 — 문항마다 미리 소문자 순수 텍스트로 펴 둔다.
  final List<SearchDoc> searchDocs = [];

  Future<void> load() async {
    if (_loaded) return;
    final raw = await rootBundle.loadString('assets/data/bank.json');
    bank = BankData.fromJson(jsonDecode(raw));
    _index();
    _loaded = true;
  }

  void _index() {
    for (final t in bank.tracks) {
      _trackById[t.id] = t;
    }
    for (final r in bank.rounds) {
      _roundByTag[r.tag] = r;
    }
    for (final s in bank.subjects) {
      (_subjectsByTrack[s.tr] ??= []).add(s);
    }
    for (final t in bank.types) {
      (_typesByTrackSubject['${t.tr} ${t.sj}'] ??= []).add(t);
      _groupOf['${t.sj} ${t.n}'] = t.g;
    }
    // 대유형은 문항 수가 많은 것부터 — 1문항짜리가 위에 오면 목록이 쓸모없다.
    for (final e in _typesByTrackSubject.entries) {
      final by = <String, List<TypeEntry>>{};
      for (final t in e.value) {
        (by[t.g] ??= []).add(t);
      }
      _groupsByTrackSubject[e.key] =
          by.entries.map((x) => TypeGroup(x.key, x.value)).toList()
            ..sort((a, b) => b.count.compareTo(a.count));
    }
    for (final it in bank.items) {
      _byId[it.id] = it;
      (_byTrack[it.tr] ??= []).add(it);
      (_byTrackSubject['${it.tr} ${it.sj}'] ??= []).add(it);
      (_byTrackSubjectType['${it.tr} ${it.sj} ${it.ty}'] ??= []).add(it);
      if (it.rd != null) (_byRound[it.rd!] ??= []).add(it);
      for (final k in it.kw) {
        (_byKeyword[k] ??= []).add(it);
        _keywordSubject.putIfAbsent(k, () => it.sj);
      }
      searchDocs.add(SearchDoc.of(it, this));
    }
    for (final l in _byRound.values) {
      l.sort((a, b) => (a.no ?? 0).compareTo(b.no ?? 0));
    }
  }

  Future<void> loadAdmin() async {
    if (admin != null) return;
    final raw = await rootBundle.loadString('assets/data/admin.json');
    final j = jsonDecode(raw) as Map<String, dynamic>;
    final items = j['items'] as Map<String, dynamic>;
    admin = items.map((k, v) => MapEntry(k, AdminInfo.fromJson(v)));
  }

  Item? byId(String id) => _byId[id];
  Track? track(String id) => _trackById[id];
  RoundEntry? round(String tag) => _roundByTag[tag];

  List<SubjectEntry> subjects(String tr) => _subjectsByTrack[tr] ?? const [];
  List<TypeEntry> types(String tr, String sj) =>
      _typesByTrackSubject['$tr $sj'] ?? const [];

  /// 화면에 내놓을 단위. 세부 유형을 대유형으로 묶은 것 —
  /// 안 묶으면 NCS 120종이 늘어서고 절반이 1문항짜리다.
  List<TypeGroup> typeGroups(String tr, String sj) =>
      _groupsByTrackSubject['$tr $sj'] ?? const [];

  String groupOf(Item i) => _groupOf['${i.sj} ${i.ty}'] ?? i.ty;

  /// 범위를 벗어나면 null. 앱 판올림으로 지문이 줄어들면 색인이 어긋날 수 있는데,
  /// 그때 지문이 안 보이는 것과 앱이 멎는 것은 아주 다르다.
  PassageEntry? passage(int idx) =>
      (idx >= 0 && idx < bank.passages.length) ? bank.passages[idx] : null;

  String kwName(int idx) =>
      (idx >= 0 && idx < bank.keywords.length) ? bank.keywords[idx].t : '';
  String kwSubject(int idx) => _keywordSubject[idx] ?? '기타';

  List<Item> roundItems(String tag) => _byRound[tag] ?? const [];

  /// 목록 한 줄 — 지문·자료를 찾아 [listLine] 에 넘긴다.
  /// 오답노트·복습·북마크·팔레트가 모두 이 창구를 쓴다.
  String line(Item it, [int n = 60]) =>
      listLine(it.st, it.pg != null ? passage(it.pg!)?.body : it.mt, n);

  /// 대유형 하나에 드는 문항 — 세부 유형 여러 개를 합친다.
  List<Item> groupItems(String tr, String sj, String group) {
    final out = <Item>[];
    for (final t in types(tr, sj)) {
      if (t.g == group) out.addAll(filter(tr: tr, sj: sj, ty: t.n));
    }
    return out;
  }

  /// 훑어보는 목록 — 직렬·과목·유형·키워드.
  ///
  /// **아직 안 본 회차의 문항은 내지 않는다.** 회차 문항은 은행에도 함께 있어서
  /// 그대로 두면 과목 연습이 모의고사를 미리 태운다 — 의사소통 86문항 중
  /// 61개(71%)가 회차 문항이다(2026-08-28 실측). 며칠 연습하면 시간 재고
  /// 앉았을 때 **이미 본 문제**가 되고, 한 번 본 것은 되돌릴 수 없다.
  ///
  /// 제출하면 곧바로 합류한다 — 그때부터는 아껴 둘 것이 아니라 복습할 것이다.
  /// 회차를 먼저 풀어 보고 싶으면 [roundItems] 를 쓰는 회차 화면이 그 길이다.
  ///
  /// 오답노트·복습·북마크는 이 창구를 쓰지 않는다(각자 Store 를 본다).
  /// 내가 이미 푼 것이라 감출 이유가 없다.
  ///
  /// **호출부에 맡기지 않는다.** 화면 여섯 곳이 이 창구를 쓰는데, 넘기는 방식이면
  /// 새 화면 하나에서 빠뜨리는 순간 그 화면만 조용히 새어 나간다.
  /// 규칙은 `round_lock.dart` 에 순수하게 두어 `tool/check_pool.dart` 가 검사한다.
  ///
  /// **화면이 이 목록으로 수를 센다.** 그래서 여기서 거르면 「전체 n문항」도
  /// 함께 맞는다 — 세는 곳과 푸는 곳이 어긋나지 않는다.
  List<Item> filter({String? tr, String? sj, String? ty, int? kw}) {
    final lock = lockedRounds(bank.rounds, Store.instance.exams);
    List<Item> keep(List<Item> xs) => withoutLocked(xs, lock);

    if (kw != null) {
      final base = _byKeyword[kw] ?? const <Item>[];
      if (tr == null && sj == null && ty == null) return keep(base);
      return keep(base.where((i) =>
          (tr == null || i.tr == tr) &&
          (sj == null || i.sj == sj) &&
          (ty == null || i.ty == ty)).toList());
    }
    if (tr != null && sj != null && ty != null) {
      return keep(_byTrackSubjectType['$tr $sj $ty'] ?? const []);
    }
    if (tr != null && sj != null) return keep(_byTrackSubject['$tr $sj'] ?? const []);
    if (tr != null) return keep(_byTrack[tr] ?? const []);
    if (sj == null && ty == null) return keep(bank.items);
    return keep(bank.items.where((i) =>
        (sj == null || i.sj == sj) && (ty == null || i.ty == ty)).toList());
  }
}

/// 검색용으로 미리 펴 둔 한 문항.
///
/// 예전에는 글자를 칠 때마다 426문항 × 8필드를 그 자리에서 HTML 파싱했다 —
/// 한 글자에 3천 번이 넘었고 화면이 멈췄다. 한 번만 펴 두면 그냥 문자열 비교다.
class SearchDoc {
  final Item item;
  final String stem, choices, cls, keywords, material, passage, explain, each;

  SearchDoc({
    required this.item, required this.stem, required this.choices,
    required this.cls, required this.keywords, required this.material,
    required this.passage, required this.explain, required this.each,
  });

  factory SearchDoc.of(Item it, Repo repo) => SearchDoc(
        item: it,
        stem: plainText(it.st).toLowerCase(),
        choices: it.ch.map(plainText).join(' ').toLowerCase(),
        cls: '${it.sj} ${it.ty}'.toLowerCase(),
        keywords: it.kw.map(repo.kwName).join(' ').toLowerCase(),
        material: plainText(it.mt).toLowerCase(),
        passage: it.pg == null ? '' : plainText(repo.passage(it.pg!)?.body).toLowerCase(),
        explain: plainText(it.ex).toLowerCase(),
        each: (it.ea ?? const []).map(plainText).join(' ').toLowerCase(),
      );
}
