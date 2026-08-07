/// 문항의 발문·자료·해설은 `<table>`·`<strong>`·`<sup>`·인라인 SVG 를 쓴 HTML 이다.
/// flutter_html 로 그리고, `<svg>` 만 flutter_svg 로 넘기는 태그 확장을 붙인다.
library;

import 'package:flutter/material.dart';
import 'package:flutter_html/flutter_html.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'theme.dart';

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
          "code": Style(
            fontFamily: 'monospace', backgroundColor: c.bg,
            padding: HtmlPaddings.symmetric(horizontal: 4),
          ),
          ".note": Style(color: c.dim, fontSize: FontSize(13.5)),
          ".box-title": Style(fontWeight: FontWeight.w700, margin: Margins.only(bottom: 6)),
          "u": Style(textDecoration: TextDecoration.underline),
        },
        extensions: const [_SvgExtension()],
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
        child: SvgPicture.string(raw, width: 260),
      ),
    );
  }
}

/// 선지 단평(each)에 붙은 「① (정답) …」 앞머리 기호를 뗀다 — 선지 옆에
/// 원문자를 이미 붙이므로 겹친다.
String stripLead(String s) {
  final re = RegExp(r'^[①②③④⑤⑥⑦]\s*');
  return s.replaceFirst(re, '');
}

String plainText(String? html) {
  if (html == null) return '';
  return html.replaceAll(RegExp(r'<[^>]+>'), ' ').replaceAll(RegExp(r'\s+'), ' ').trim();
}

String snippet(String? html, [int n = 60]) {
  final t = plainText(html);
  return t.length > n ? '${t.substring(0, n)}…' : t;
}
