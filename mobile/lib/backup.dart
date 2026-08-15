/// 기록의 **모양**만 다룬다 — 클래스와 JSON 왕복.
///
/// **Flutter 를 쓰지 않는다.** 이 환경은 `flutter test` 가 막혀 있어서, 여기 있어야
/// `dart run tool/check_backup.dart` 로 왕복을 곧장 확인할 수 있다.
/// 상태를 들고 저장하고 알리는 일은 [Store] (store.dart) 가 맡는다.
library;

class Attempt {
  final int? chosen;
  final bool ok;
  final int at; // 채점한 시각 (epoch ms)
  /// 이 문항에 쓴 시간(ms). 낱개 풀이에서만 잰다 — 회차는 채점 순간이 없다.
  /// 옛 기록에는 없어서 null 이다.
  final int? ms;
  Attempt({required this.chosen, required this.ok, required this.at, this.ms});

  factory Attempt.fromJson(Map<String, dynamic> j) => Attempt(
        chosen: (j['c'] as num?)?.toInt(),
        ok: j['k'] == 1,
        at: (j['t'] as num?)?.toInt() ?? 0,
        ms: (j['m'] as num?)?.toInt(),
      );
  Map<String, dynamic> toJson() => {
        'c': chosen, 'k': ok ? 1 : 0, 't': at,
        if (ms != null) 'm': ms,
      };
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
        at: (j['at'] as num).toInt(),
        score: (j['score'] as num).toInt(),
        n: (j['n'] as num).toInt(),
        sec: (j['sec'] as num).toInt(),
        auto: j['auto'] == 1,
        ans: _intMap(j['ans']),
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
        tag: j['tag'] as String,
        at: (j['at'] as num).toInt(),
        endsAt: (j['endsAt'] as num).toInt(),
        ans: _intMap(j['ans']),
        flag: _boolMap(j['flag']),
        atNo: (j['at_no'] as num?)?.toInt() ?? 1,
      );
  Map<String, dynamic> toJson() => {
        'tag': tag, 'at': at, 'endsAt': endsAt,
        'ans': ans.map((k, v) => MapEntry(k.toString(), v)),
        'flag': flag.map((k, v) => MapEntry(k.toString(), v ? 1 : 0)),
        'at_no': atNo,
      };
}

/// 풀던 낱개 묶음 — 회차와 달리 시계가 없고, 한 칸만 둔다.
///
/// 채점한 답은 이미 `att` 에 들어가 있다. 여기 있는 것은 **커서와 아직 채점 안 한
/// 선택**뿐이라, 다른 묶음을 시작하면 조용히 갈려도 잃는 것이 없다.
class SoloSession {
  final List<String> ids; // 섞인 그 순서 그대로
  final List<int?> chosen;
  final List<bool> graded;
  int at;
  final String title;
  int savedAt;
  SoloSession({
    required this.ids, required this.chosen, required this.graded,
    required this.at, required this.title, required this.savedAt,
  });

  factory SoloSession.fromJson(Map<String, dynamic> j) {
    final ids = (j['ids'] as List).map((e) => e as String).toList();
    final chosen = (j['ch'] as List).map((e) => (e as num?)?.toInt()).toList();
    final graded = (j['g'] as List).map((e) => e == 1).toList();
    // 길이가 어긋난 기록은 되살리지 않는다 — 인덱스가 밀리면 엉뚱한 문항에 답이 붙는다.
    if (chosen.length != ids.length || graded.length != ids.length) {
      throw const FormatException('풀던 묶음의 길이가 맞지 않는다');
    }
    return SoloSession(
      ids: ids, chosen: chosen, graded: graded,
      at: (j['at'] as num?)?.toInt() ?? 0,
      title: (j['t'] as String?) ?? '',
      savedAt: (j['sv'] as num?)?.toInt() ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'ids': ids,
        'ch': chosen,
        'g': graded.map((b) => b ? 1 : 0).toList(),
        'at': at, 't': title, 'sv': savedAt,
      };

  int get done => graded.where((g) => g).length;
}

class Mark {
  bool bookmark, flag;
  String memo;
  int at;
  Mark({this.bookmark = false, this.flag = false, this.memo = '', this.at = 0});
  factory Mark.fromJson(Map<String, dynamic> j) => Mark(
        bookmark: j['b'] == 1, flag: j['f'] == 1,
        memo: (j['memo'] as String?) ?? '',
        at: (j['at'] as num?)?.toInt() ?? 0,
      );
  Map<String, dynamic> toJson() =>
      {'b': bookmark ? 1 : 0, 'f': flag ? 1 : 0, 'memo': memo, 'at': at};
  bool get isEmpty => !bookmark && !flag && memo.isEmpty;
}

// ─────────────────────────────────────────────────────────── 통째로 읽고 쓰기

/// 기록 한 벌. 저장할 때도 백업할 때도 이 모양이다.
class StoreData {
  final Map<String, List<Attempt>> att;
  final Map<String, Srs> srs;
  final Map<String, List<ExamRecord>> exams;
  final Map<String, Mark> mark;
  final SitState? sit;
  final SoloSession? solo;
  final bool admin;
  final double textScale;

  /// 복습 알림을 켰나. 기본은 **꺼짐** — 묻지 않고 알리지 않는다.
  final bool remind;

  /// 알릴 시각. 자정부터의 분(0~1439). 기본 21:00.
  final int remindAt;

  StoreData({
    required this.att, required this.srs, required this.exams,
    required this.mark, this.sit, this.solo,
    this.admin = false, this.textScale = 1.0,
    this.remind = false, this.remindAt = defaultRemindAt,
  });

  int get attCount => att.length;
  int get examCount => exams.values.fold(0, (s, l) => s + l.length);
  int get markCount => mark.length;
}

Map<String, dynamic> encodeStore(StoreData d) => {
      'att': d.att.map((k, v) => MapEntry(k, v.map((a) => a.toJson()).toList())),
      'srs': d.srs.map((k, v) => MapEntry(k, v.toJson())),
      'exams': d.exams.map((k, v) => MapEntry(k, v.map((e) => e.toJson()).toList())),
      'mark': d.mark.map((k, v) => MapEntry(k, v.toJson())),
      'sit': d.sit?.toJson(),
      'solo': d.solo?.toJson(),
      'admin': d.admin,
      'ts': d.textScale,
      'rm': d.remind,
      'rmAt': d.remindAt,
    };

/// 저녁 9시. 기본값을 여기 한 곳에만 둔다.
const defaultRemindAt = 21 * 60;

/// 하루 밖으로 나간 값을 접는다. 옛 백업이나 손으로 고친 파일이 들어와도
/// 시각이 성립하게 둔다 — 던지면 백업 전체를 못 읽는다.
int clampRemindAt(int m) => m % 1440 < 0 ? (m % 1440) + 1440 : m % 1440;

/// 통째로 읽는다. **하나라도 어긋나면 던진다** — 반만 읽어 들이면
/// 다음 저장이 나머지를 영영 지운다.
StoreData decodeStore(Map<String, dynamic> j) {
  final att = <String, List<Attempt>>{};
  (j['att'] as Map?)?.forEach((k, v) {
    att[k as String] = (v as List)
        .map((e) => Attempt.fromJson((e as Map).cast<String, dynamic>()))
        .toList();
  });
  final srs = <String, Srs>{};
  (j['srs'] as Map?)?.forEach(
      (k, v) => srs[k as String] = Srs.fromJson((v as Map).cast<String, dynamic>()));
  final exams = <String, List<ExamRecord>>{};
  (j['exams'] as Map?)?.forEach((k, v) {
    exams[k as String] = (v as List)
        .map((e) => ExamRecord.fromJson((e as Map).cast<String, dynamic>()))
        .toList();
  });
  final mark = <String, Mark>{};
  (j['mark'] as Map?)?.forEach(
      (k, v) => mark[k as String] = Mark.fromJson((v as Map).cast<String, dynamic>()));

  return StoreData(
    att: att, srs: srs, exams: exams, mark: mark,
    sit: j['sit'] == null
        ? null : SitState.fromJson((j['sit'] as Map).cast<String, dynamic>()),
    solo: j['solo'] == null
        ? null : SoloSession.fromJson((j['solo'] as Map).cast<String, dynamic>()),
    admin: j['admin'] == true,
    textScale: clampScale((j['ts'] as num?)?.toDouble() ?? 1.0),
    remind: j['rm'] == true,
    remindAt: clampRemindAt((j['rmAt'] as num?)?.toInt() ?? defaultRemindAt),
  );
}

// ─────────────────────────────────────────────────────────── 백업 파일 봉투

const backupVersion = 1;
const backupApp = 'ncs-bank';

Map<String, dynamic> wrapBackup(StoreData d, DateTime at) => {
      'v': backupVersion,
      'app': backupApp,
      'at': at.toIso8601String(),
      'counts': {'att': d.attCount, 'exams': d.examCount, 'mark': d.markCount},
      'data': encodeStore(d),
    };

/// 백업 파일을 읽는다. 남의 JSON 을 잘못 골랐을 때 **그렇다고 말해 주려고**
/// 봉투를 먼저 본다 — 그냥 던지면 「기록을 불러오지 못했습니다」밖에 안 나온다.
class Backup {
  final StoreData data;
  final DateTime? at;
  Backup(this.data, this.at);
}

Backup readBackup(Object? decoded) {
  if (decoded is! Map) {
    throw const FormatException('백업 파일이 아닙니다');
  }
  final j = decoded.cast<String, dynamic>();
  if (j['app'] != null && j['app'] != backupApp) {
    throw FormatException('다른 앱의 백업입니다 (${j['app']})');
  }
  final raw = j['data'];
  if (raw is! Map) {
    throw const FormatException('백업 파일이 아닙니다 — data 가 없습니다');
  }
  final v = (j['v'] as num?)?.toInt() ?? backupVersion;
  if (v > backupVersion) {
    throw FormatException('더 새로운 앱에서 만든 백업입니다 (형식 v$v)');
  }
  return Backup(
    decodeStore(raw.cast<String, dynamic>()),
    DateTime.tryParse((j['at'] as String?) ?? ''),
  );
}

// ─────────────────────────────────────────────────────────── 잡동사니

/// 글자 배율 — 화면이 무너지지 않는 범위로 가둔다.
double clampScale(double v) => v.clamp(0.9, 1.5);

const textScaleSteps = <(String, double)>[
  ('작게', 0.9),
  ('보통', 1.0),
  ('크게', 1.15),
  ('더 크게', 1.3),
  ('아주 크게', 1.5),
];

Map<int, int> _intMap(Object? v) {
  final out = <int, int>{};
  (v as Map?)?.forEach((k, x) => out[int.parse(k as String)] = (x as num).toInt());
  return out;
}

Map<int, bool> _boolMap(Object? v) {
  final out = <int, bool>{};
  (v as Map?)?.forEach((k, x) => out[int.parse(k as String)] = x == 1);
  return out;
}
