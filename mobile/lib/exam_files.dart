/// 회차 인쇄본 — 무엇을 번들에서 꺼내 무슨 이름으로 저장하나.
///
/// 회차마다 PDF 가 두 벌 있다. 그동안 앱은 문제집을 「PDF로 풀기」에만 썼고
/// (`exam_pdf.dart` 가 문항 하나를 오려 보여 준다), 파일 자체를 내주지는 않았다.
/// **실전은 종이로 푼다.** 그 길을 열어 둔다.
///
/// ## 이름이 둘이다
///
/// 번들에는 `assets/exams/r1_public.pdf` 로 두고, 저장될 이름은
/// `NCS_봉투모의고사_1회_문제.pdf` 다. 자산 경로에 한글을 쓰면 플랫폼마다
/// 다루는 법이 갈리고, 저장될 이름은 사람이 읽어야 한다 — 두 요구가 다르다.
/// `tools/export_bank.py` 가 두 이름을 함께 만들어 `bank.json` 에 담는다.
///
/// ## 웹판과 같은 규칙이다
///
/// `web/src/data/pdf.js` 와 차례·이름·크기 표기가 같다. 한쪽만 고치면 두 판이
/// 다른 것을 말하게 된다.
///
/// **여기에 Flutter 를 들이지 않는다.** 규칙만 떼어 두면
/// `tool/check_exam_files.dart` 가 순수 Dart 로 검사할 수 있다 —
/// `round_lock.dart` · `tracks.dart` 와 같은 이유다.
library;

import 'models.dart';

/// 내려받을 수 있는 인쇄본 하나.
class ExamFile {
  /// `'q'`(문제집) 또는 `'s'`(해설집)
  final String kind;

  /// 화면에 보이는 이름
  final String name;

  /// 번들 안의 자산 경로
  final String asset;

  /// 저장될 파일 이름 (한글)
  final String file;

  /// 크기(KB)
  final int kb;

  const ExamFile({
    required this.kind, required this.name,
    required this.asset, required this.file, required this.kb,
  });

  /// `1449` → `1.4MB`. 1MB 아래는 KB 그대로 — 「0.6MB」보다 「598KB」가 읽힌다
  String get size => kb >= 1024
      ? '${(kb / 1024).toStringAsFixed(1)}MB'
      : '${kb}KB';
}

/// 차례가 화면의 차례다 — 문제집 먼저.
const _kinds = [('q', '문제집'), ('s', '해설집')];

/// 번들 안의 자산 경로. 해설집만 `.sol` 이 붙는다.
String examAsset(String tag, String kind) =>
    'assets/exams/$tag${kind == 's' ? '.sol' : ''}.pdf';

/// 이 회차에서 내려받을 수 있는 것.
///
/// **없는 것은 내지 않는다.** 옛 `bank.json` 에는 `pdf` 칸이 아예 없고,
/// `build.py` 를 안 돌린 회차는 해설집이 빠질 수 있다. 그때 단추를 세우면
/// 눌러야 없다는 것을 안다.
List<ExamFile> examFiles(RoundEntry r) {
  final out = <ExamFile>[];
  for (final (kind, name) in _kinds) {
    final got = r.pdf[kind];
    if (got == null || got.isEmpty || got[0] is! String) continue;
    final file = got[0] as String;
    if (file.isEmpty) continue;
    out.add(ExamFile(
      kind: kind, name: name,
      asset: examAsset(r.tag, kind),
      file: file,
      kb: got.length > 1 && got[1] is num ? (got[1] as num).round() : 0,
    ));
  }
  return out;
}
