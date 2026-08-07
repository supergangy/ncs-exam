/// 에셋에 번들된 bank.json/admin.json 을 읽어 조회한다. 웹앱의 `DB` 객체와 같다.
library;

import 'dart:convert';
import 'package:flutter/services.dart' show rootBundle;
import 'models.dart';
export 'models.dart';

class Repo {
  Repo._();
  static final Repo instance = Repo._();

  late BankData bank;
  Map<String, AdminInfo>? admin; // 관리자 모드일 때만 채운다
  final Map<String, Item> _byId = {};
  bool _loaded = false;

  Future<void> load() async {
    if (_loaded) return;
    final raw = await rootBundle.loadString('assets/data/bank.json');
    bank = BankData.fromJson(jsonDecode(raw));
    for (final it in bank.items) {
      _byId[it.id] = it;
    }
    _loaded = true;
  }

  Future<void> loadAdmin() async {
    if (admin != null) return;
    final raw = await rootBundle.loadString('assets/data/admin.json');
    final j = jsonDecode(raw) as Map<String, dynamic>;
    final items = j['items'] as Map<String, dynamic>;
    admin = items.map((k, v) => MapEntry(k, AdminInfo.fromJson(v)));
  }

  Item? byId(String id) => _byId[id];

  Track? track(String id) =>
      bank.tracks.where((t) => t.id == id).cast<Track?>().firstOrNull;

  List<SubjectEntry> subjects(String tr) =>
      bank.subjects.where((s) => s.tr == tr).toList();

  List<TypeEntry> types(String tr, String sj) =>
      bank.types.where((t) => t.tr == tr && t.sj == sj).toList();

  PassageEntry passage(int idx) => bank.passages[idx];

  String kwName(int idx) => idx < bank.keywords.length ? bank.keywords[idx].t : '';

  RoundEntry? round(String tag) =>
      bank.rounds.where((r) => r.tag == tag).cast<RoundEntry?>().firstOrNull;

  List<Item> roundItems(String tag) {
    final list = bank.items.where((i) => i.rd == tag).toList()
      ..sort((a, b) => (a.no ?? 0).compareTo(b.no ?? 0));
    return list;
  }

  List<Item> filter({String? tr, String? sj, String? ty, int? kw}) {
    return bank.items.where((i) {
      if (tr != null && i.tr != tr) return false;
      if (sj != null && i.sj != sj) return false;
      if (ty != null && i.ty != ty) return false;
      if (kw != null && !i.kw.contains(kw)) return false;
      return true;
    }).toList();
  }
}

extension _FirstOrNull<T> on Iterable<T> {
  T? get firstOrNull => isEmpty ? null : first;
}
