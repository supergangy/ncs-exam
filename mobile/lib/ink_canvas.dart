/// 회차 PDF 위에 얹는 필기 캔버스 — 그리는 쪽.
///
/// 좌표·저장·지우개 판정은 `ink.dart` 가 순수 Dart 로 들고 있다. 여기서는
/// 손가락을 받아 [InkDoc] 에 넣고, 들어 있는 획을 그리기만 한다.
///
/// ## 왜 오려 낸 조각마다 캔버스를 두나
///
/// 한 문항이 쪽을 넘어가면 조각이 둘이 된다(`exam_pdf.dart` 의 QBound).
/// 조각마다 보고 있는 PDF 사각형이 다르므로 캔버스도 조각마다 붙인다.
/// 획은 PDF 페이지 점으로 저장되니 조각이 갈려도 같은 종이 위에 남는다.
library;

import 'dart:ui' show PointerDeviceKind;

import 'package:flutter/material.dart';
import 'package:perfect_freehand/perfect_freehand.dart' as pf;

import 'ink.dart';

/// 지금 손에 쥔 도구.
enum InkMode { off, pen, marker, eraser }

/// 도구·색을 담아 화면 사이로 넘긴다.
class InkSettings {
  final InkMode mode;
  final int penColor;
  final int markerColor;
  const InkSettings({
    this.mode = InkMode.off,
    this.penColor = 0xFF1A1A1A,
    this.markerColor = 0xFFFFD54F,
  });

  bool get drawing => mode == InkMode.pen || mode == InkMode.marker;
  String get tool => mode == InkMode.marker ? toolMarker : toolPen;
  int get color => mode == InkMode.marker ? markerColor : penColor;
  double get width => inkWidth[tool]!;

  InkSettings copyWith({InkMode? mode, int? penColor, int? markerColor}) =>
      InkSettings(
        mode: mode ?? this.mode,
        penColor: penColor ?? this.penColor,
        markerColor: markerColor ?? this.markerColor,
      );
}

/// PDF 조각 하나 위의 필기층.
///
/// [bx]·[by]·[bw] 는 이 조각이 보여 주는 PDF 사각형이다. 위젯 폭은
/// [LayoutBuilder] 가 준다 — 회전해도 다시 잰다.
class InkLayer extends StatefulWidget {
  final InkDoc doc;
  final int page;
  final double bx, by, bw;
  final InkSettings settings;

  /// 획이 늘거나 줄었을 때. 바깥이 저장 시점을 정한다.
  final VoidCallback onChanged;

  const InkLayer({
    super.key,
    required this.doc,
    required this.page,
    required this.bx,
    required this.by,
    required this.bw,
    required this.settings,
    required this.onChanged,
  });

  @override
  State<InkLayer> createState() => _InkLayerState();
}

class _InkLayerState extends State<InkLayer> {
  /// 지금 그리는 중인 획. 손을 떼야 [InkDoc] 으로 넘어간다 —
  /// 중간에 넣으면 되돌리기가 획이 아니라 점 단위가 된다.
  final List<InkPoint> _live = [];
  double _widgetW = 1;

  /// 지금 획을 끌고 있는 포인터. 손바닥이 나중에 닿아도 획을 가로채지 못한다.
  int? _active;

  static InkPointer _kindOf(PointerEvent e) => switch (e.kind) {
        PointerDeviceKind.stylus => InkPointer.stylus,
        PointerDeviceKind.invertedStylus => InkPointer.invertedStylus,
        PointerDeviceKind.touch => InkPointer.touch,
        _ => InkPointer.other,
      };

  InkPoint _toPage(Offset local, double pressure) => localToPage(
        local.dx,
        local.dy,
        bx: widget.bx,
        by: widget.by,
        bw: widget.bw,
        widgetW: _widgetW,
        pressure: pressure,
      );

  void _down(PointerDownEvent e) {
    final kind = _kindOf(e);
    if (kind == InkPointer.stylus || kind == InkPointer.invertedStylus) {
      // 펜을 본 기기에서는 그 뒤로 손가락을 그리기에서 뺀다 (팜 리젝션).
      InkInput.stylusSeen = true;
    }
    final act = InkInput.actionFor(kind, drawing: widget.settings.drawing);
    if (act == InkAction.ignore) return;
    if (act == InkAction.erase) {
      _active = e.pointer;
      _erase(e.localPosition);
      return;
    }
    // 이미 한 획을 끌고 있으면 두 번째 포인터는 무시한다 — 손바닥이 뒤늦게
    // 닿아도 쓰던 획이 그리로 끌려가지 않는다.
    if (_active != null) return;
    _active = e.pointer;
    setState(() => _live
      ..clear()
      ..add(_toPage(e.localPosition, _pressure(e))));
  }

  void _moveEvent(PointerMoveEvent e) {
    if (e.pointer != _active) return;
    final act = InkInput.actionFor(_kindOf(e), drawing: widget.settings.drawing);
    if (act == InkAction.ignore) return;
    if (act == InkAction.erase) {
      _erase(e.localPosition);
      return;
    }
    if (_live.isEmpty) return;
    final p = _toPage(e.localPosition, _pressure(e));
    // 손이 거의 안 움직였으면 점을 늘리지 않는다. 한 획이 수천 점이 되면
    // 저장 크기가 부풀고 다시 그릴 때도 느려진다.
    final last = _live.last;
    if ((p.x - last.x).abs() < 0.4 && (p.y - last.y).abs() < 0.4) return;
    setState(() => _live.add(p));
  }

  void _up(PointerEvent e) {
    if (e.pointer != _active) return;
    _active = null;
    _end();
  }

  void _end() {
    if (_live.isEmpty) return;
    widget.doc.add(Stroke(
      page: widget.page,
      tool: widget.settings.tool,
      color: widget.settings.color,
      width: widget.settings.width,
      pts: List.of(_live),
    ));
    setState(_live.clear);
    widget.onChanged();
  }

  void _erase(Offset local) {
    final p = _toPage(local, 0.5);
    if (widget.doc.eraseAt(widget.page, p.x, p.y) > 0) {
      setState(() {});
      widget.onChanged();
    }
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (ctx, box) {
      _widgetW = box.maxWidth <= 0 ? 1 : box.maxWidth;
      final painter = _InkPainter(
        strokes: widget.doc.ofPage(widget.page),
        live: _live,
        liveTool: widget.settings.tool,
        liveColor: widget.settings.color,
        liveWidth: widget.settings.width,
        bx: widget.bx,
        by: widget.by,
        bw: widget.bw,
        widgetW: _widgetW,
      );
      final canvas = CustomPaint(painter: painter, size: Size.infinite);
      if (widget.settings.mode == InkMode.off) {
        // 도구를 껐으면 손가락을 가로채지 않는다 — 회차 화면을 넘길 수 있어야 한다.
        return IgnorePointer(child: canvas);
      }
      // `translucent` 라 손가락 이벤트가 아래로도 내려간다. 펜을 쓰는 기기에서
      // 손가락으로 화면을 넘기려면 이 층이 막고 서 있으면 안 된다.
      return Listener(
        behavior: HitTestBehavior.translucent,
        onPointerDown: _down,
        onPointerMove: _moveEvent,
        onPointerUp: _up,
        onPointerCancel: _up,
        child: canvas,
      );
    });
  }

  /// 필압을 주는 기기면 쓰고, 아니면 0.5 로 고정한다.
  /// `pressureMin == pressureMax` 인 기기가 손가락 입력의 대부분이다.
  static double _pressure(PointerEvent e) {
    if (e.pressureMax <= e.pressureMin) return 0.5;
    final t = (e.pressure - e.pressureMin) / (e.pressureMax - e.pressureMin);
    return t.clamp(0.0, 1.0);
  }
}

class _InkPainter extends CustomPainter {
  final List<Stroke> strokes;
  final List<InkPoint> live;
  final String liveTool;
  final int liveColor;
  final double liveWidth;
  final double bx, by, bw, widgetW;

  _InkPainter({
    required this.strokes,
    required this.live,
    required this.liveTool,
    required this.liveColor,
    required this.liveWidth,
    required this.bx,
    required this.by,
    required this.bw,
    required this.widgetW,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // 형광펜은 획끼리 겹칠 때 색이 쌓이면 지저분하다. 층을 따로 떠서
    // 한 번에 얹으면 같은 색으로 고르게 칠해진다.
    final markers = [
      ...strokes.where((s) => s.tool == toolMarker),
      if (live.isNotEmpty && liveTool == toolMarker) _liveStroke(),
    ];
    if (markers.isNotEmpty) {
      canvas.saveLayer(Offset.zero & size, Paint());
      for (final s in markers) {
        _draw(canvas, s, opaque: true);
      }
      canvas.drawRect(
        Offset.zero & size,
        Paint()
          ..blendMode = BlendMode.dstIn
          ..color = Color.fromRGBO(0, 0, 0, inkOpacity[toolMarker]!),
      );
      canvas.restore();
    }
    // 연필은 형광펜 위에 온다 — 종이에 형광펜을 칠하고 그 위에 쓰는 순서다.
    for (final s in strokes) {
      if (s.tool != toolMarker) _draw(canvas, s, opaque: true);
    }
    if (live.isNotEmpty && liveTool != toolMarker) {
      _draw(canvas, _liveStroke(), opaque: true);
    }
  }

  Stroke _liveStroke() => Stroke(
        page: 0,
        tool: liveTool,
        color: liveColor,
        width: liveWidth,
        pts: live,
      );

  void _draw(Canvas canvas, Stroke s, {required bool opaque}) {
    if (s.pts.isEmpty) return;
    final scale = widgetW / bw;
    final pts = [
      for (final q in s.pts)
        pf.PointVector((q.x - bx) * scale, (q.y - by) * scale, q.p)
    ];
    // 펜이 진짜 필압을 준 획이면 흉내를 끈다. 켜 둔 채로 두면 실제 필압 위에
    // 속도로 만든 굵기가 겹쳐 획이 울퉁불퉁해진다.
    final real = s.hasRealPressure;
    final outline = pf.getStroke(
      pts,
      options: pf.StrokeOptions(
        size: s.width * scale,
        // 형광펜은 힘을 안 준다 — 굵기가 일정해야 밑줄로 쓸 만하다.
        thinning: s.tool == toolMarker ? 0.0 : 0.45,
        smoothing: 0.5,
        // 펜은 손보다 촘촘히 점을 준다. 많이 다듬으면 획 끝이 뭉툭해진다.
        streamline: real ? 0.2 : 0.4,
        simulatePressure: !real,
        isComplete: true,
      ),
    );
    if (outline.length < 3) {
      // 점 하나를 톡 찍은 경우 — 다각형이 안 나온다. 동그라미로 찍는다.
      final p = pts.first;
      canvas.drawCircle(Offset(p.dx, p.dy), s.width * scale / 2,
          Paint()..color = Color(s.color));
      return;
    }
    final path = Path()..moveTo(outline.first.dx, outline.first.dy);
    for (final p in outline.skip(1)) {
      path.lineTo(p.dx, p.dy);
    }
    path.close();
    canvas.drawPath(path, Paint()..color = Color(s.color));
  }

  @override
  bool shouldRepaint(_InkPainter old) =>
      old.strokes.length != strokes.length ||
      old.live.length != live.length ||
      old.widgetW != widgetW ||
      old.liveColor != liveColor ||
      old.liveTool != liveTool;
}

/// 도구 막대 — 회차 화면 아래에 붙인다.
class InkToolbar extends StatelessWidget {
  final InkSettings settings;
  final bool canUndo, canRedo;
  final ValueChanged<InkSettings> onChanged;
  final VoidCallback onUndo, onRedo, onClear;

  const InkToolbar({
    super.key,
    required this.settings,
    required this.canUndo,
    required this.canRedo,
    required this.onChanged,
    required this.onUndo,
    required this.onRedo,
    required this.onClear,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    Widget tool(InkMode m, IconData icon, String label) {
      final on = settings.mode == m;
      return Tooltip(
        message: label,
        child: IconButton(
          icon: Icon(icon),
          isSelected: on,
          color: on ? cs.primary : null,
          style: on
              ? IconButton.styleFrom(backgroundColor: cs.primaryContainer)
              : null,
          // 같은 것을 다시 누르면 꺼진다 — 화면을 넘기려면 꺼야 한다.
          onPressed: () => onChanged(
              settings.copyWith(mode: on ? InkMode.off : m)),
        ),
      );
    }

    return Material(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 52,
          child: Row(
            children: [
              const SizedBox(width: 4),
              tool(InkMode.pen, Icons.edit_outlined, '연필'),
              tool(InkMode.marker, Icons.brush_outlined, '형광펜'),
              // 이 Flutter 판에는 ink_eraser 가 없다. 지우는 도구로 읽히는 것 중 고른다.
              tool(InkMode.eraser, Icons.auto_fix_normal_outlined, '지우개'),
              const VerticalDivider(width: 12, indent: 10, endIndent: 10),
              IconButton(
                icon: const Icon(Icons.undo),
                tooltip: '되돌리기',
                onPressed: canUndo ? onUndo : null,
              ),
              IconButton(
                icon: const Icon(Icons.redo),
                tooltip: '다시하기',
                onPressed: canRedo ? onRedo : null,
              ),
              const Spacer(),
              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: Text(
                  settings.mode == InkMode.off
                      ? '도구를 골라야 그려집니다'
                      : InkInput.stylusSeen
                          // 팜 리젝션이 켜졌다는 것을 알려 준다. 손가락이 안
                          // 먹히는 것을 고장으로 오해하지 않게.
                          ? '펜으로 씁니다 · 손가락은 넘기기'
                          : '손가락으로 씁니다',
                  style: TextStyle(
                      fontSize: 12, color: Theme.of(context).hintColor),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.delete_sweep_outlined),
                tooltip: '이 회차 필기 모두 지우기',
                onPressed: canUndo || canRedo ? onClear : null,
              ),
              const SizedBox(width: 4),
            ],
          ),
        ),
      ),
    );
  }
}
