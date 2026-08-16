/// 「PDF로 풀기」 — 회차 문제집 PDF 에서 문항 하나만 오려 보여 준다.
///
/// 인쇄본과 화면이 같아진다. 실전은 종이로 푸는데 앱은 재조판한 HTML 을 보여
/// 주고 있었다 — 자료 표의 줄바꿈부터 다르다.
///
/// ## 좌표
///
/// `assets/exams/<회차>.map.json` 이 문항마다 면과 사각형을 적어 둔다.
/// **단위는 pt, 원점은 왼쪽 위**다(`tools/pagemap.py` 가 PDF 에서 뽑는다).
/// `pdfx` 의 `cropRect` 는 렌더한 이미지의 픽셀 공간이라 같은 배율만 곱하면 된다.
///
/// ## 왜 pdfx 인가
///
/// 분석한 PSAT 앱은 `flutter_pdfview` 를 쓴다. 그것은 네이티브 뷰라 위에 캔버스를
/// 얹기 어렵다. `pdfx` 는 페이지를 이미지로 내주므로 오려 내기도 되고,
/// 나중에 필기를 덧그릴 자리도 생긴다.
library;

import 'dart:convert';
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:pdfx/pdfx.dart';

import 'ink.dart';
import 'ink_canvas.dart';

/// 문항 하나가 차지하는 사각형. 한 문항이 두 면에 걸치면 조각이 여럿이다.
class QBound {
  final int page;
  final double x, y, w, h;
  const QBound({required this.page, required this.x, required this.y,
      required this.w, required this.h});
  factory QBound.fromJson(Map<String, dynamic> j) => QBound(
        page: (j['page'] as num).toInt(),
        x: (j['x'] as num).toDouble(), y: (j['y'] as num).toDouble(),
        w: (j['w'] as num).toDouble(), h: (j['h'] as num).toDouble(),
      );
}

class ExamMap {
  final String round;
  final double pageW, pageH;
  final Map<int, List<QBound>> byNo;
  ExamMap({required this.round, required this.pageW, required this.pageH,
      required this.byNo});

  factory ExamMap.fromJson(Map<String, dynamic> j) {
    final size = (j['pageSize'] as Map).cast<String, dynamic>();
    final by = <int, List<QBound>>{};
    for (final q in (j['questions'] as List)) {
      final m = (q as Map).cast<String, dynamic>();
      by[(m['no'] as num).toInt()] = [
        for (final b in (m['bounds'] as List))
          QBound.fromJson((b as Map).cast<String, dynamic>())
      ];
    }
    return ExamMap(
      round: j['round'] as String? ?? '',
      pageW: (size['width'] as num).toDouble(),
      pageH: (size['height'] as num).toDouble(),
      byNo: by,
    );
  }
}

/// 회차 하나의 PDF 와 지도. 화면이 살아 있는 동안만 연다.
class ExamPdf {
  ExamPdf._(this.tag, this._doc, this.map);

  final String tag;
  final PdfDocument _doc;
  final ExamMap map;

  static String pdfAsset(String tag) => 'assets/exams/$tag.pdf';
  static String mapAsset(String tag) => 'assets/exams/$tag.map.json';

  /// 이 회차에 PDF 가 실려 있나. 없으면 「PDF로 풀기」를 아예 보여 주지 않는다.
  static Future<bool> exists(String tag) async {
    try {
      await rootBundle.load(mapAsset(tag));
      return true;
    } catch (_) {
      return false;
    }
  }

  static Future<ExamPdf> open(String tag) async {
    final raw = await rootBundle.loadString(mapAsset(tag));
    final m = ExamMap.fromJson((jsonDecode(raw) as Map).cast<String, dynamic>());
    final doc = await PdfDocument.openAsset(pdfAsset(tag));
    return ExamPdf._(tag, doc, m);
  }

  Future<void> close() => _doc.close();

  // 렌더는 비싸다. 같은 문항을 앞뒤로 넘길 때 다시 굽지 않는다.
  final _cache = <String, Uint8List>{};
  static const _cacheMax = 12;

  /// 문항 [no] 의 조각 [part] 를 [widthPx] 픽셀 폭으로 굽는다.
  ///
  /// **안드로이드는 동시 렌더를 허용하지 않는다.** 페이지를 열면 반드시 닫는다.
  Future<Uint8List?> render(int no, {required int part, required int widthPx}) async {
    final bounds = map.byNo[no];
    if (bounds == null || part >= bounds.length) return null;
    final b = bounds[part];
    final key = '$no.$part@$widthPx';
    final hit = _cache[key];
    if (hit != null) return hit;

    // 지도의 폭(사각형)이 화면 폭이 되도록 배율을 잡는다.
    final scale = widthPx / b.w;
    PdfPage? page;
    try {
      page = await _doc.getPage(b.page);
      final img = await page.render(
        width: map.pageW * scale,
        height: map.pageH * scale,
        format: PdfPageImageFormat.png,
        backgroundColor: '#FFFFFF',
        cropRect: ui.Rect.fromLTWH(
            b.x * scale, b.y * scale, b.w * scale, b.h * scale),
      );
      final bytes = img?.bytes;
      if (bytes == null) return null;
      if (_cache.length >= _cacheMax) {
        _cache.remove(_cache.keys.first);
      }
      _cache[key] = bytes;
      return bytes;
    } catch (err) {
      debugPrint('PDF 문항 렌더 실패 ($tag $no): $err');
      return null;
    } finally {
      await page?.close();
    }
  }

  int partsOf(int no) => map.byNo[no]?.length ?? 0;

  /// 사각형의 세로/가로 비. 자리를 미리 잡아 두면 그림이 뜰 때 화면이 안 튄다.
  double aspectOf(int no, int part) {
    final b = map.byNo[no];
    if (b == null || part >= b.length) return 1;
    return b[part].h / b[part].w;
  }
}

/// 종이가 커지는 데 한계를 둔다 (논리 픽셀).
///
/// 문항 사각형의 폭이 515pt(A4 본문 단)쯤이다. 태블릿에서 화면 폭을 다 쓰면
/// 종이가 실물보다 두 배 넘게 커져 눈이 따라가기 힘들다. 이 값에서 멈추고
/// 가운데에 둔다 — 폰에서는 화면이 더 좁아 상한에 닿지 않는다.
const double examPaperMaxWidth = 900;

/// 문항 하나를 PDF 에서 오려 보여 준다.
///
/// 화면 폭이 바뀌면(회전·분할화면) 다시 굽는다. 굽는 동안에도 자리는 잡아 둔다 —
/// 비율을 미리 알고 있어 화면이 튀지 않는다.
class QuestionPdfView extends StatelessWidget {
  final ExamPdf pdf;
  final int no;

  /// 필기층. 없으면(null) 종이만 보여 준다 — 결과 화면에서 그렇다.
  final InkDoc? ink;
  final InkSettings inkSettings;
  final VoidCallback? onInkChanged;

  const QuestionPdfView({
    super.key,
    required this.pdf,
    required this.no,
    this.ink,
    this.inkSettings = const InkSettings(),
    this.onInkChanged,
  });

  @override
  Widget build(BuildContext context) {
    final parts = pdf.partsOf(no);
    if (parts == 0) {
      return _note(context, '이 문항은 PDF 지도에 없습니다.');
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var i = 0; i < parts; i++)
          _Part(
            pdf: pdf,
            no: no,
            part: i,
            ink: ink,
            inkSettings: inkSettings,
            onInkChanged: onInkChanged,
          ),
      ],
    );
  }

  static Widget _note(BuildContext context, String s) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Text(s, textAlign: TextAlign.center,
            style: TextStyle(color: Theme.of(context).hintColor, fontSize: 13)),
      );
}

class _Part extends StatelessWidget {
  final ExamPdf pdf;
  final int no, part;
  final InkDoc? ink;
  final InkSettings inkSettings;
  final VoidCallback? onInkChanged;
  const _Part({
    required this.pdf,
    required this.no,
    required this.part,
    this.ink,
    this.inkSettings = const InkSettings(),
    this.onInkChanged,
  });

  @override
  Widget build(BuildContext context) {
    final dpr = MediaQuery.devicePixelRatioOf(context);
    return LayoutBuilder(builder: (ctx, box) {
      final wPx = (box.maxWidth * dpr).round().clamp(320, 2400);
      return AspectRatio(
        aspectRatio: 1 / pdf.aspectOf(no, part),
        child: FutureBuilder<Uint8List?>(
          // 폭이 바뀌면 키가 바뀌어 다시 굽는다.
          key: ValueKey('$no.$part@$wPx'),
          future: pdf.render(no, part: part, widthPx: wPx),
          builder: (ctx, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(
                  child: SizedBox(width: 22, height: 22,
                      child: CircularProgressIndicator(strokeWidth: 2)));
            }
            final bytes = snap.data;
            if (bytes == null) {
              return QuestionPdfView._note(ctx, 'PDF 를 그리지 못했습니다.');
            }
            // 종이 그대로다. 색을 입히지 않는다 — 다크 모드에서도 흰 종이로 둔다.
            final paper = Image.memory(bytes, fit: BoxFit.fitWidth,
                filterQuality: FilterQuality.medium);
            final doc = ink;
            if (doc == null) return paper;
            // 필기는 종이 **위에** 얹는다. 사각형이 곧 이 조각이 보여 주는
            // PDF 영역이라, 획을 그 좌표로 바꿔 넣으면 화면 크기와 무관해진다.
            final b = pdf.map.byNo[no]![part];
            return Stack(fit: StackFit.expand, children: [
              paper,
              InkLayer(
                doc: doc,
                page: b.page,
                bx: b.x,
                by: b.y,
                bw: b.w,
                settings: inkSettings,
                onChanged: onInkChanged ?? () {},
              ),
            ]);
          },
        ),
      );
    });
  }
}
