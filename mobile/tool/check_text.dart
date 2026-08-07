/// `flutter test` 가 이 환경에서 못 돌아(테스트 러너가 자식 VM 에 붙지 못한다)
/// 순수 Dart 로 같은 것을 확인한다. 번들된 bank.json 전수도 함께 훑는다.
///
///   dart run tool/check_text.dart
library;

import 'dart:convert';
import 'dart:io';
import 'package:ncs_bank/text.dart';

int _fail = 0, _pass = 0;

void eq(String label, String got, String want) {
  if (got == want) {
    _pass++;
  } else {
    _fail++;
    stdout.writeln('  ✗ $label\n      나온 것: $got\n      바랄 것: $want');
  }
}

void ok(String label, bool cond) {
  if (cond) {
    _pass++;
  } else {
    _fail++;
    stdout.writeln('  ✗ $label');
  }
}

void main() {
  stdout.writeln('■ 문자 참조 (설치본 버그: &lt;보기&gt; 가 그대로 나왔다)');
  eq('보기', plainText('윗글을 바탕으로 &lt;보기&gt;의 사례를'), '윗글을 바탕으로 <보기>의 사례를');
  eq('조건', plainText('&lt;조건&gt;에 따라'), '<조건>에 따라');
  eq('앰퍼샌드', plainText('A&amp;B'), 'A&B');
  eq('nbsp', plainText('가&nbsp;나'), '가 나');

  stdout.writeln('■ 첨자 — 공백을 끼우면 값이 바뀐다');
  eq('제곱센티', plainText('36π − 72 (cm<sup>2</sup>)'), '36π − 72 (cm²)');
  eq('2의10승', plainText('2<sup>10</sup>바이트'), '2¹⁰바이트');
  eq('물', plainText('H<sub>2</sub>O'), 'H₂O');
  eq('분수', plainText('<sup>1</sup>/<sub>20</sub>'), '¹/₂₀');
  eq('못옮기는첨자', plainText('a<sup>k</sup>'), 'ak');

  stdout.writeln('■ 인라인 태그');
  eq('밑줄', plainText('그렇게 하면 <u>안 되요</u>.'), '그렇게 하면 안 되요.');
  eq('강조', plainText('<strong>반드시</strong> 옳은'), '반드시 옳은');
  eq('코드', plainText('<code>SELECT *</code> 를'), 'SELECT * 를');

  stdout.writeln('■ 블록');
  eq('표', plainText('<table><tr><td>가</td><td>나</td></tr></table>'), '가 나');
  eq('줄바꿈', plainText('앞<br>뒤'), '앞 뒤');
  ok('표는 블록', hasBlockHtml('<table><tr><td>가</td></tr></table>'));
  ok('밑줄은 블록 아님', !hasBlockHtml('밑줄 <u>친</u> 곳'));
  ok('첨자는 블록 아님', !hasBlockHtml('cm<sup>2</sup>'));

  stdout.writeln('■ 앞머리 기호');
  eq('stripLead', stripLead('① (정답) 맞다'), '(정답) 맞다');

  // ── 번들 데이터 전수 ────────────────────────────────────────────────
  final f = File('assets/data/bank.json');
  if (!f.existsSync()) {
    stdout.writeln('bank.json 이 없다 — 데이터 전수는 건너뛴다');
  } else {
    final d = jsonDecode(f.readAsStringSync()) as Map<String, dynamic>;
    final items = (d['items'] as List).cast<Map<String, dynamic>>();
    final leftovers = <String>[];
    var supKept = 0, uKept = 0;
    final ent = RegExp(r'&(?:lt|gt|amp|quot|nbsp|#\d+);');
    // 태그 이름을 아는 것만 태그로 본다. `<보기>` 는 제대로 풀린 결과이지 태그가 아니다 —
    // `<[^>]+>` 로 잡으면 고쳐진 것을 고장이라 부르게 된다.
    final tag = RegExp(r'</?(?:p|div|span|table|tr|td|th|u|b|i|em|strong|sup|sub|code|br)\b[^>]*>',
        caseSensitive: false);
    for (final it in items) {
      for (final field in <String>[it['st'] as String, ...(it['ch'] as List).cast<String>()]) {
        final p = plainText(field);
        if (ent.hasMatch(p) || tag.hasMatch(p)) {
          leftovers.add('${it['id']}: $p');
        }
        if (field.contains('<sup')) supKept++;
        if (field.contains('<u>')) uKept++;
      }
    }
    stdout.writeln('■ 번들 데이터 ${items.length}문항 전수');
    ok('발문·선지에 남은 태그/문자참조 0건 (실제 ${leftovers.length}건)', leftovers.isEmpty);
    for (final l in leftovers.take(5)) {
      stdout.writeln('      $l');
    }
    stdout.writeln('    (윗첨자 쓰는 선지 $supKept개 · 밑줄 쓰는 선지 $uKept개를 훑었다)');
  }

  stdout.writeln('\n통과 $_pass · 실패 $_fail');
  if (_fail > 0) exit(1);
}
