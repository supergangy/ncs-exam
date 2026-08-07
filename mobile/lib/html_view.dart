/// 문항의 발문·선지·자료·해설은 모두 HTML 이다.
///
/// 두 갈래로 그린다.
///  - 블록(자료·지문·해설) → `HtmlBox` : flutter_html + 표 확장 + SVG 확장
///  - 인라인(발문·선지)     → `HtmlText` : 직접 만든 TextSpan 변환기
///
/// 인라인을 따로 두는 이유 — 발문·선지는 `Text` 한 줄처럼 놓여야 하는데
/// flutter_html 은 블록 상자를 만든다. 그렇다고 정규식으로 태그를 벗기면
/// `cm<sup>2</sup>` 가 `cm 2` 가 되고 `<u>안 되요</u>` 의 밑줄이 사라진다.
/// 둘 다 **뜻이 바뀌는** 손실이라 그럴 수 없다.
library;

import 'package:flutter/material.dart';
import 'package:flutter_html/flutter_html.dart';
import 'package:flutter_html_table/flutter_html_table.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:html/dom.dart' as dom;
import 'package:html/parser.dart' as htmlparser;
import 'text.dart';
import 'theme.dart';

export 'text.dart' show plainText, snippet, stripLead, hasBlockHtml;

class HtmlBox extends StatelessWidget {
  final String html;
  final EdgeInsets? padding;
  final bool bordered;
  const HtmlBox(this.html, {super.key, this.padding, this.bordered = true});

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final body = Padding(
      padding: padding ?? const EdgeInsets.all(14),
      child: Html(
        data: html,
        style: {
          "body": Style(margin: Margins.zero, padding: HtmlPaddings.zero,
              fontSize: FontSize(15.5), color: c.ink, lineHeight: LineHeight(1.55)),
          "p": Style(margin: Margins.only(bottom: 8)),
          "p:last-child": Style(margin: Margins.zero),
          "table": Style(
            width: Width.auto(), border: Border.all(color: c.line),
            margin: Margins.symmetric(vertical: 6), fontSize: FontSize(13.5),
          ),
          "caption": Style(
            fontSize: FontSize(12.5), color: c.dim, textAlign: TextAlign.left,
            padding: HtmlPaddings.only(bottom: 4),
          ),
          "th": Style(
            border: Border.all(color: c.line), padding: HtmlPaddings.symmetric(
                horizontal: 8, vertical: 6),
            backgroundColor: c.bg, fontWeight: FontWeight.w700, textAlign: TextAlign.center,
          ),
          "td": Style(
            border: Border.all(color: c.line),
            padding: HtmlPaddings.symmetric(horizontal: 8, vertical: 6),
            textAlign: TextAlign.center,
          ),
          "strong": Style(fontWeight: FontWeight.w800),
          "sup": Style(fontSize: FontSize(10.5), verticalAlign: VerticalAlign.sup),
          "sub": Style(fontSize: FontSize(10.5), verticalAlign: VerticalAlign.sub),
          "code": Style(
            fontFamily: 'monospace', backgroundColor: c.bg,
            padding: HtmlPaddings.symmetric(horizontal: 4),
          ),
          ".note": Style(color: c.dim, fontSize: FontSize(13.5)),
          ".box-title": Style(fontWeight: FontWeight.w700, margin: Margins.only(bottom: 6)),
          "u": Style(textDecoration: TextDecoration.underline),
        },
        extensions: const [TableHtmlExtension(), _SvgExtension()],
      ),
    );
    if (!bordered) return body;
    return Container(
      decoration: BoxDecoration(
        color: c.card, borderRadius: BorderRadius.circular(14),
        border: Border.all(color: c.line),
      ),
      margin: const EdgeInsets.only(bottom: 10),
      child: body,
    );
  }
}

class _SvgExtension extends HtmlExtension {
  const _SvgExtension();
  @override
  Set<String> get supportedTags => {"svg"};

  @override
  InlineSpan build(ExtensionContext context) {
    final raw = context.element?.outerHtml ?? '';
    return WidgetSpan(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        // 폭을 못 박으면 좁은 기기에서 잘리고 넓은 기기에서 작다. 웹판 CSS 와 같게
        // 가로를 꽉 채우되 원래 비율을 지킨다.
        child: SizedBox(
          width: double.infinity,
          child: SvgPicture.string(raw, fit: BoxFit.contain,
              alignment: Alignment.centerLeft),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────── 인라인 HTML → TextSpan

/// 발문·선지처럼 **한 덩어리 글**로 놓이는 HTML 을 그린다.
/// `<u> <sup> <sub> <strong> <em> <code> <br>` 과 문자 참조(`&lt;`)를 살린다.
class HtmlText extends StatelessWidget {
  final String html;
  final TextStyle style;
  final int? maxLines;
  final TextOverflow overflow;
  const HtmlText(this.html, {super.key, required this.style, this.maxLines,
      this.overflow = TextOverflow.clip});

  @override
  Widget build(BuildContext context) {
    return Text.rich(
      TextSpan(children: inlineSpans(html, style)),
      maxLines: maxLines,
      overflow: overflow,
    );
  }
}

/// HTML 조각을 TextSpan 목록으로 바꾼다. 모르는 태그는 **껍데기만 버리고
/// 안쪽 글은 살린다** — 조용히 사라지는 쪽이 훨씬 위험하다.
List<InlineSpan> inlineSpans(String html, TextStyle base) {
  final frag = htmlparser.parseFragment(html);
  final out = <InlineSpan>[];
  for (final n in frag.nodes) {
    _walk(n, base, out);
  }
  return out;
}

void _walk(dom.Node node, TextStyle st, List<InlineSpan> out) {
  if (node is dom.Text) {
    if (node.text.isNotEmpty) out.add(TextSpan(text: node.text, style: st));
    return;
  }
  if (node is! dom.Element) return;

  switch (node.localName) {
    case 'br':
      out.add(TextSpan(text: '\n', style: st));
      return;
    case 'sup':
    case 'sub':
      final sup = node.localName == 'sup';
      // 유니코드 첨자로 옮길 수 있으면 그게 낫다 — 글자 하나라 줄바꿈·복사에 강하다.
      final map = sup ? supDigits : subDigits;
      final inner = node.text;
      if (inner.isNotEmpty && inner.split('').every(map.containsKey)) {
        out.add(TextSpan(text: inner.split('').map((ch) => map[ch]).join(), style: st));
        return;
      }
      final fs = st.fontSize ?? 15.0;
      out.add(WidgetSpan(
        alignment: PlaceholderAlignment.middle,
        child: Transform.translate(
          offset: Offset(0, sup ? -fs * 0.30 : fs * 0.18),
          child: Text.rich(TextSpan(children: _kids(node, st.copyWith(fontSize: fs * 0.72)))),
        ),
      ));
      return;
  }

  final next = switch (node.localName) {
    'u' => st.copyWith(decoration: TextDecoration.underline),
    'strong' || 'b' => st.copyWith(fontWeight: FontWeight.w800),
    'em' || 'i' => st.copyWith(fontStyle: FontStyle.italic),
    'code' => st.copyWith(fontFamily: 'monospace', letterSpacing: -0.2),
    _ => st,
  };
  out.addAll(_kids(node, next));
}

List<InlineSpan> _kids(dom.Element e, TextStyle st) {
  final out = <InlineSpan>[];
  for (final n in e.nodes) {
    _walk(n, st, out);
  }
  return out;
}

// 순수 텍스트 쪽(plainText·snippet·stripLead·hasBlockHtml)은 text.dart 에 있다.
// Flutter 를 안 쓰는 파일로 떼어 두어야 `dart run tool/check_text.dart` 로 검증할 수 있다.
