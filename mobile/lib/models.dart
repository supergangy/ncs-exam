/// bank.json / admin.json 을 그대로 옮긴 모델.
/// 필드명은 JSON 원본의 축약 키를 그대로 쓴다 (app.js 와 대조하기 쉽게).
library;

class Track {
  final String id, name, sub;
  final int c;
  Track({required this.id, required this.name, required this.sub, required this.c});
  factory Track.fromJson(Map<String, dynamic> j) =>
      Track(id: j['id'], name: j['name'], sub: j['sub'], c: j['c'] ?? 0);
}

class SubjectEntry {
  final String tr, n;
  final int c;
  SubjectEntry({required this.tr, required this.n, required this.c});
  factory SubjectEntry.fromJson(Map<String, dynamic> j) =>
      SubjectEntry(tr: j['tr'], n: j['n'], c: j['c']);
}

class TypeEntry {
  final String tr, sj, n;
  /// 대유형. 세부 유형(`n`)을 묶는 이름 — bank/types.py 가 정한다.
  /// 이게 없으면 NCS 120종이 그대로 목록에 늘어서고 절반이 1문항짜리다.
  final String g;
  final int c;
  TypeEntry({required this.tr, required this.sj, required this.n,
      required this.g, required this.c});
  factory TypeEntry.fromJson(Map<String, dynamic> j) => TypeEntry(
        tr: j['tr'], sj: j['sj'], n: j['n'],
        g: j['g'] ?? j['n'], // 옛 bank.json 과도 읽힌다
        c: j['c'],
      );
}

/// 한 과목 안의 대유형 하나 — 화면에 한 줄로 나가는 단위.
class TypeGroup {
  final String name;
  final List<TypeEntry> details;
  TypeGroup(this.name, this.details);
  int get count => details.fold(0, (s, t) => s + t.c);
  /// 「자료해석 · 증감률 · 교차참조」처럼 안에 무엇이 있는지 보여 준다.
  String get detailLine => details.map((t) => t.n).join(' · ');
}

class KeywordEntry {
  final String t;
  final int n;
  KeywordEntry({required this.t, required this.n});
  factory KeywordEntry.fromJson(Map<String, dynamic> j) =>
      KeywordEntry(t: j['t'], n: j['n']);
}

class PassageEntry {
  final String body;
  final String? lead;
  PassageEntry({required this.body, this.lead});
  factory PassageEntry.fromJson(Map<String, dynamic> j) =>
      PassageEntry(body: j['body'] ?? '', lead: j['lead']);
}

class RoundArea {
  final String name;
  final int n;
  RoundArea(this.name, this.n);
}

class RoundEntry {
  final String tag, title, brand, org;
  final int n, min;

  /// 이 회차가 어느 직렬의 것인가 — `['ncs']` · `['cs']` · 둘 다.
  ///
  /// 내보내기가 **문항의 과목에서 끌어낸다**(`tools/export_bank.py` 의 `track_of`).
  /// 옛 bank.json 에는 이 칸이 없다. 그때는 회차가 다 NCS 였으므로 그렇게 본다.
  final List<String> tr;

  /// 인쇄본 PDF — `{'q': [보이는 이름, KB], 's': [...]}`.
  ///
  /// 서버·번들의 이름(`r1_public.pdf`)과 **저장될 이름**(`NCS_봉투모의고사_1회_문제.pdf`)
  /// 이 다르다. 파일 이름이 한글이라 주소에 그대로 쓰면 인코딩이 갈리기 때문이다.
  /// `tools/export_bank.py` 가 두 이름을 함께 만든다.
  ///
  /// 옛 bank.json 에는 이 칸이 없다. 그때는 빈 map 이다 — 화면이 아무것도 세우지
  /// 않는다(눌러도 없는 파일을 여는 단추를 만들지 않는다).
  final Map<String, List<dynamic>> pdf;

  final List<RoundArea> areas;
  RoundEntry({
    required this.tag, required this.title, required this.brand,
    required this.org, required this.n, required this.min,
    required this.tr, required this.pdf, required this.areas,
  });
  factory RoundEntry.fromJson(Map<String, dynamic> j) => RoundEntry(
        tag: j['tag'], title: j['title'], brand: j['brand'] ?? '',
        org: j['org'] ?? '', n: j['n'], min: j['min'],
        tr: ((j['tr'] as List?) ?? const ['ncs']).cast<String>(),
        pdf: ((j['pdf'] as Map?) ?? const {})
            .map((k, v) => MapEntry(k as String, (v as List))),
        areas: (j['areas'] as List)
            .map((a) => RoundArea(a[0] as String, a[1] as int))
            .toList(),
      );
}

class Item {
  final String id, tr, sj, ty, og, st;
  final List<String> ch;
  final int an;
  final List<int> kw;
  final int? pg; // passage index
  final String? mt, ex, df, ld; // material, explain, difficulty, lead
  final List<String>? ea; // each — 선지별 단평
  final String? rd; // round tag
  final int? no; // round 안 문항 번호

  Item({
    required this.id, required this.tr, required this.sj, required this.ty,
    required this.og, required this.st, required this.ch, required this.an,
    required this.kw, this.pg, this.mt, this.ex, this.df, this.ld,
    this.ea, this.rd, this.no,
  });

  factory Item.fromJson(Map<String, dynamic> j) => Item(
        id: j['id'], tr: j['tr'], sj: j['sj'], ty: j['ty'], og: j['og'],
        st: j['st'], ch: List<String>.from(j['ch']), an: j['an'],
        kw: List<int>.from(j['kw'] ?? const []),
        pg: j['pg'], mt: j['mt'], ex: j['ex'], df: j['df'], ld: j['ld'],
        ea: j['ea'] == null ? null : List<String>.from(j['ea']),
        rd: j['rd'], no: j['no'],
      );
}

class BankData {
  final int v, n;
  final List<Track> tracks;
  final List<SubjectEntry> subjects;
  final List<TypeEntry> types;
  final List<KeywordEntry> keywords;
  final List<PassageEntry> passages;
  final List<Item> items;
  final List<RoundEntry> rounds;

  BankData({
    required this.v, required this.n, required this.tracks,
    required this.subjects, required this.types, required this.keywords,
    required this.passages, required this.items, required this.rounds,
  });

  factory BankData.fromJson(Map<String, dynamic> j) => BankData(
        v: j['v'], n: j['n'],
        tracks: (j['tracks'] as List).map((e) => Track.fromJson(e)).toList(),
        subjects: (j['subjects'] as List).map((e) => SubjectEntry.fromJson(e)).toList(),
        types: (j['types'] as List).map((e) => TypeEntry.fromJson(e)).toList(),
        keywords: (j['keywords'] as List).map((e) => KeywordEntry.fromJson(e)).toList(),
        passages: (j['passages'] as List).map((e) => PassageEntry.fromJson(e)).toList(),
        items: (j['items'] as List).map((e) => Item.fromJson(e)).toList(),
        rounds: ((j['rounds'] as List?) ?? const [])
            .map((e) => RoundEntry.fromJson(e))
            .toList(),
      );
}

/// admin.json 의 한 항목 — 위험도·근거·출제이유서.
class AdminInfo {
  final String? rk, ev, sn, rd;
  final Map<String, dynamic>? wy;
  AdminInfo({this.rk, this.ev, this.sn, this.rd, this.wy});
  factory AdminInfo.fromJson(Map<String, dynamic> j) => AdminInfo(
        rk: j['rk'], ev: j['ev'], sn: j['sn'], rd: j['rd'],
        wy: j['wy'] == null ? null : Map<String, dynamic>.from(j['wy']),
      );
}
