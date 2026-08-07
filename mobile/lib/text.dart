/// HTML 조각 → 순수 텍스트. **Flutter 를 쓰지 않는다** — 그래야 `dart run` 으로
/// 곧장 돌려 볼 수 있다(이 환경에서는 `flutter test` 가 막혀 있다).
/// 목록·검색·내보내기가 쓴다. 화면에 그리는 쪽은 `html_view.dart` 다.
library;

import 'package:html/dom.dart' as dom;
import 'package:html/parser.dart' as htmlparser;

const supDigits = {
  '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
  '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
  '+': '⁺', '-': '⁻', '−': '⁻', 'n': 'ⁿ', 'i': 'ⁱ',
};
const subDigits = {
  '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
  '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
  '+': '₊', '-': '₋', '−': '₋', 'n': 'ₙ',
};

final _ws = RegExp(r'\s+');
const _blockTags = {
  'p', 'div', 'tr', 'td', 'th', 'li', 'table', 'caption', 'h1', 'h2', 'h3', 'br'
};

/// 태그를 벗기고 문자 참조를 푼다.
///
/// 정규식으로 `<[^>]+>` 를 지우던 옛 방식은 두 가지를 망가뜨렸다 —
/// `&lt;보기&gt;` 가 화면에 그대로 나왔고, `cm<sup>2</sup>` 가 `cm 2` 가 됐다.
/// 뒤엣것은 **값이 바뀌는** 손실이다. 그래서 진짜 파서를 쓰고, 첨자는 유니코드로 살린다.
String plainText(String? html) {
  if (html == null || html.isEmpty) return '';
  final buf = StringBuffer();
  _flatten(htmlparser.parseFragment(html), buf);
  return buf.toString().replaceAll(_ws, ' ').trim();
}

void _flatten(dom.Node node, StringBuffer buf) {
  if (node is dom.Text) {
    buf.write(node.text);
    return;
  }
  if (node is! dom.Element) {
    for (final n in node.nodes) {
      _flatten(n, buf);
    }
    return;
  }
  final tag = node.localName;
  if (tag == 'br') {
    buf.write(' ');
    return;
  }
  if (tag == 'sup' || tag == 'sub') {
    final map = tag == 'sup' ? supDigits : subDigits;
    final inner = node.text;
    // 한 글자라도 못 옮기면 통째로 원문을 쓴다 — 반만 첨자로 바뀌면 더 헷갈린다.
    if (inner.isNotEmpty && inner.split('').every(map.containsKey)) {
      buf.write(inner.split('').map((ch) => map[ch]).join());
    } else {
      buf.write(inner); // 공백 없이 붙인다. 넣으면 값이 바뀐다.
    }
    return;
  }
  for (final n in node.nodes) {
    _flatten(n, buf);
  }
  if (_blockTags.contains(tag)) buf.write(' ');
}

/// 블록 태그를 쓰는 HTML 인가 — 그렇다면 인라인 변환기로는 모자라다.
final _blockRe = RegExp(r'<\s*(table|div|p|ul|ol|li|svg|img|pre)\b', caseSensitive: false);
bool hasBlockHtml(String? s) => s != null && _blockRe.hasMatch(s);

/// 선지 단평에 붙은 「① …」 앞머리 기호를 뗀다 — 선지 옆에 원문자를 이미 붙이므로 겹친다.
final _leadRe = RegExp(r'^[①②③④⑤⑥⑦]\s*');
String stripLead(String s) => s.replaceFirst(_leadRe, '');

String snippet(String? html, [int n = 60]) {
  final t = plainText(html);
  return t.length > n ? '${t.substring(0, n)}…' : t;
}
