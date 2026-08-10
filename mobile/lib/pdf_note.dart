/// 오답노트를 **폰에서 바로** PDF 로 굽는다.
///
/// 문항이 이미 HTML 이라 안드로이드 시스템 WebView 에 그대로 물린다
/// (`Printing.convertHtml`). 표·인라인 SVG 가 앱 화면보다 오히려 정확히 나온다.
///
/// HTML 을 만드는 일은 [note_html.dart] 가 한다 — Flutter 를 안 써야
/// 브라우저에 띄워 인쇄 모양을 눈으로 볼 수 있다.
///
/// PC 쪽(`tools/wrongnote_pdf.py`)은 그대로 둔다. 표지·쪽번호·빠른정답이 붙는
/// 제대로 된 인쇄본은 여전히 그쪽이 낫다.
library;

import 'package:printing/printing.dart';
import 'note_html.dart';
import 'repo.dart';
import 'store.dart';

export 'note_html.dart' show buildNoteHtml;

/// 인쇄 시트를 띄운다 — 거기서 「PDF 로 저장」·공유·인쇄를 고른다.
Future<void> printNote(List<Item> items, {required String title}) async {
  final now = DateTime.now();
  final stamp = '${now.year}${now.month.toString().padLeft(2, '0')}'
      '${now.day.toString().padLeft(2, '0')}';
  final html = buildNoteHtml(
    items,
    title: title,
    at: now,
    passage: Repo.instance.passage,
    roundTitle: (tag) => Repo.instance.round(tag)?.title,
    picked: (id) => Store.instance.last(id)?.chosen,
  );
  await Printing.layoutPdf(
    name: 'wrongnote-$stamp',
    // `convertHtml` 은 deprecated 다 — pdf 패키지 위젯으로 직접 그리라는 뜻이다.
    // 그래도 이걸 쓴다. 문항이 표와 인라인 SVG 를 쓰는 HTML 이라, 위젯으로 다시
    // 짜면 그 둘을 손수 구현해야 하고 결과도 못하다. 안드로이드 구현은
    // WebView + PrintDocumentAdapter 로 멀쩡히 살아 있다.
    // 언젠가 정말 없어지면 PC 파이프라인(tools/wrongnote_pdf.py)이 남는다.
    // ignore: deprecated_member_use
    onLayout: (format) => Printing.convertHtml(format: format, html: html),
  );
}
