/// 회차 PDF 위에 얹는 필기 — 좌표·직렬화·지우개 판정 (순수 Dart).
///
/// 화면 위젯과 떼어 놓는다. 그려지는 모양은 `ink_canvas.dart` 가 맡고, 여기서는
/// **어디에 찍히는가**와 **다시 열었을 때 같은 자리인가**만 다룬다. 그래야
/// `dart run tool/check_ink.dart` 로 기기 없이 확인할 수 있다.
///
/// ## 좌표를 PDF 페이지 점으로 두는 이유
///
/// 화면 폭은 회전·분할화면·기기마다 다르다. 화면 좌표로 저장하면 다음에 열 때
/// 획이 딴 데 찍힌다(`PLAN.md` §2 가 (c) 안을 고른 까닭이 이것이다). PDF 페이지
/// 점은 종이에 매인 값이라 화면이 어떻게 바뀌어도 그대로다.
///
/// 굵기도 페이지 점으로 둔다. 화면 픽셀로 두면 큰 화면에서 가늘어진다.
library;

import 'dart:convert';
import 'dart:math' as math;

/// 도구 — 저장되는 값이므로 문자열을 바꾸면 옛 기록이 안 읽힌다.
const String toolPen = 'pen';
const String toolMarker = 'marker';

/// 도구별 기본 굵기 (PDF 점). A4 폭이 595점이니 연필 1.6점은 종이에서 볼펜 굵기다.
const Map<String, double> inkWidth = {toolPen: 1.6, toolMarker: 11.0};

/// 형광펜은 반투명으로 겹쳐 칠한다. 연필은 불투명.
const Map<String, double> inkOpacity = {toolPen: 1.0, toolMarker: 0.32};

/// 지우개가 획을 집는 반경 (PDF 점). 손가락 끝이 굵으니 넉넉히 잡는다.
const double eraserRadius = 7.0;

/// 획의 한 점. [p] 는 필압 0~1 — 기기가 안 주면 0.5 로 둔다.
class InkPoint {
  final double x, y, p;
  const InkPoint(this.x, this.y, [this.p = 0.5]);

  Map<String, dynamic> toJson() => {
        'x': _round(x),
        'y': _round(y),
        if (p != 0.5) 'p': _round(p),
      };

  factory InkPoint.fromJson(Map<String, dynamic> j) => InkPoint(
        (j['x'] as num).toDouble(),
        (j['y'] as num).toDouble(),
        (j['p'] as num?)?.toDouble() ?? 0.5,
      );

  /// 소수점 둘째 자리까지만 남긴다. 한 회차 필기가 수백 KB 가 되는데
  /// 자릿수를 줄이면 절반 가까이 준다 (`PLAN.md` §3).
  static double _round(double v) => (v * 100).roundToDouble() / 100;

  @override
  String toString() => '(${_round(x)}, ${_round(y)})';
}

/// 획 하나. 좌표는 모두 **PDF 페이지 점**이다.
class Stroke {
  final int page;
  final String tool;
  final int color; // ARGB
  final double width; // PDF 점
  final List<InkPoint> pts;

  const Stroke({
    required this.page,
    required this.tool,
    required this.color,
    required this.width,
    required this.pts,
  });

  bool get isEmpty => pts.isEmpty;

  Map<String, dynamic> toJson() => {
        'g': page,
        't': tool,
        'c': color,
        'w': InkPoint._round(width),
        'v': [for (final q in pts) q.toJson()],
      };

  factory Stroke.fromJson(Map<String, dynamic> j) => Stroke(
        page: (j['g'] as num).toInt(),
        tool: j['t'] as String? ?? toolPen,
        color: (j['c'] as num?)?.toInt() ?? 0xFF1A1A1A,
        width: (j['w'] as num?)?.toDouble() ?? inkWidth[toolPen]!,
        pts: [
          for (final e in (j['v'] as List? ?? const []))
            InkPoint.fromJson(Map<String, dynamic>.from(e as Map))
        ],
      );

  /// 획을 감싸는 사각형 — 굵기의 절반만큼 넓힌다.
  /// 지우개가 먼 획을 건너뛸 때 쓴다.
  (double, double, double, double) get bounds {
    var lo = pts.first, hi = pts.first;
    var x0 = lo.x, y0 = lo.y, x1 = hi.x, y1 = hi.y;
    for (final q in pts) {
      if (q.x < x0) x0 = q.x;
      if (q.y < y0) y0 = q.y;
      if (q.x > x1) x1 = q.x;
      if (q.y > y1) y1 = q.y;
    }
    final pad = width / 2;
    return (x0 - pad, y0 - pad, x1 + pad, y1 + pad);
  }
}

// ── 좌표 변환 ─────────────────────────────────────────────────────────
//
// 화면에 보이는 것은 페이지 전체가 아니라 문항 하나를 오려 낸 사각형이다
// (`exam_pdf.dart` 의 QBound). 그 사각형의 왼쪽 위가 위젯의 (0,0) 이고,
// 사각형 폭 bw 가 위젯 폭 W 로 늘어난다.

/// 위젯 좌표 → PDF 페이지 점.
InkPoint localToPage(double dx, double dy,
    {required double bx,
    required double by,
    required double bw,
    required double widgetW,
    double pressure = 0.5}) {
  final s = bw / widgetW; // 위젯 1픽셀이 PDF 몇 점인가
  return InkPoint(bx + dx * s, by + dy * s, pressure);
}

/// PDF 페이지 점 → 위젯 좌표. (x, y)
(double, double) pageToLocal(double px, double py,
    {required double bx,
    required double by,
    required double bw,
    required double widgetW}) {
  final s = widgetW / bw;
  return ((px - bx) * s, (py - by) * s);
}

/// PDF 점으로 잰 길이를 위젯 픽셀로 옮긴다 (굵기·지우개 반경에 쓴다).
double pageLenToLocal(double len,
        {required double bw, required double widgetW}) =>
    len * widgetW / bw;

// ── 지우개 ────────────────────────────────────────────────────────────

/// 점 (px, py) 에서 선분 (ax,ay)-(bx,by) 까지의 거리.
double segmentDistance(
    double px, double py, double ax, double ay, double bx, double by) {
  final vx = bx - ax, vy = by - ay;
  final wx = px - ax, wy = py - ay;
  final len2 = vx * vx + vy * vy;
  if (len2 == 0) return math.sqrt(wx * wx + wy * wy);
  var t = (wx * vx + wy * vy) / len2;
  if (t < 0) t = 0;
  if (t > 1) t = 1;
  final cx = ax + t * vx, cy = ay + t * vy;
  final ex = px - cx, ey = py - cy;
  return math.sqrt(ex * ex + ey * ey);
}

/// 지우개가 이 획에 닿았는가. 반경은 획 굵기의 절반만큼 더 넓게 본다 —
/// 굵은 형광펜은 가장자리를 스쳐도 지워져야 자연스럽다.
bool strokeHit(Stroke s, double px, double py, {double radius = eraserRadius}) {
  if (s.pts.isEmpty) return false;
  final r = radius + s.width / 2;
  final (x0, y0, x1, y1) = s.bounds;
  // 사각형 밖이면 선분을 재지 않는다. 획이 수백 개일 때 이게 대부분을 걸러 낸다.
  if (px < x0 - r || px > x1 + r || py < y0 - r || py > y1 + r) return false;
  if (s.pts.length == 1) {
    final q = s.pts.first;
    return math.sqrt(math.pow(px - q.x, 2) + math.pow(py - q.y, 2)) <= r;
  }
  for (var i = 0; i + 1 < s.pts.length; i++) {
    final a = s.pts[i], b = s.pts[i + 1];
    if (segmentDistance(px, py, a.x, a.y, b.x, b.y) <= r) return true;
  }
  return false;
}

// ── 한 회차의 필기 ────────────────────────────────────────────────────

/// 회차 하나의 획 묶음. 되돌리기는 **획 단위**다 (`PLAN.md` 4단계).
///
/// 저장은 페이지 단위 행이므로 [byPage] 로 갈라 낸다. 한 페이지만 고쳐도
/// 그 행만 다시 쓰면 된다 — 회차 전체를 통째로 쓰지 않는다.
class InkDoc {
  final List<Stroke> strokes;
  final List<Stroke> _undone = [];

  /// 마지막으로 저장한 뒤에 바뀐 페이지. 이 페이지의 행만 다시 쓴다.
  final Set<int> dirty = {};

  InkDoc([List<Stroke>? initial]) : strokes = [...?initial];

  bool get canUndo => strokes.isNotEmpty;
  bool get canRedo => _undone.isNotEmpty;
  int get count => strokes.length;

  void add(Stroke s) {
    if (s.isEmpty) return;
    strokes.add(s);
    _undone.clear(); // 새로 그리면 다시하기 사슬은 끊긴다
    dirty.add(s.page);
  }

  /// 마지막 획을 되돌린다. 되돌린 획이 있으면 그 페이지 번호를 준다.
  int? undo() {
    if (strokes.isEmpty) return null;
    final s = strokes.removeLast();
    _undone.add(s);
    dirty.add(s.page);
    return s.page;
  }

  int? redo() {
    if (_undone.isEmpty) return null;
    final s = _undone.removeLast();
    strokes.add(s);
    dirty.add(s.page);
    return s.page;
  }

  /// (px, py) 에 닿은 획을 지운다. 지운 개수를 준다.
  ///
  /// 위에 그린 것부터 지운다 — 겹친 곳에서 눈에 보이는 획이 먼저 사라져야
  /// 손에 맞는다. 한 번에 하나만 지워 통째로 날아가는 사고를 막는다.
  int eraseAt(int page, double px, double py, {double radius = eraserRadius}) {
    for (var i = strokes.length - 1; i >= 0; i--) {
      final s = strokes[i];
      if (s.page != page) continue;
      if (!strokeHit(s, px, py, radius: radius)) continue;
      strokes.removeAt(i);
      _undone.add(s);
      dirty.add(page);
      return 1;
    }
    return 0;
  }

  List<Stroke> ofPage(int page) =>
      [for (final s in strokes) if (s.page == page) s];

  Map<int, List<Stroke>> get byPage {
    final out = <int, List<Stroke>>{};
    for (final s in strokes) {
      (out[s.page] ??= []).add(s);
    }
    return out;
  }

  /// 페이지 하나를 저장 문자열로. 빈 페이지는 빈 문자열 — 행을 지우라는 뜻이다.
  String encodePage(int page) {
    final list = ofPage(page);
    if (list.isEmpty) return '';
    return jsonEncode([for (final s in list) s.toJson()]);
  }

  void clearDirty() => dirty.clear();

  /// 페이지별 저장 문자열에서 되살린다.
  static InkDoc decode(Map<int, String> pages) {
    final all = <Stroke>[];
    for (final entry in pages.entries) {
      all.addAll(decodePage(entry.value));
    }
    return InkDoc(all);
  }

  static List<Stroke> decodePage(String raw) {
    if (raw.trim().isEmpty) return const [];
    try {
      final list = jsonDecode(raw);
      if (list is! List) return const [];
      return [
        for (final e in list)
          if (e is Map) Stroke.fromJson(Map<String, dynamic>.from(e))
      ];
    } catch (_) {
      // 깨진 행 하나 때문에 회차 전체가 안 열리면 안 된다. 그 페이지만 버린다.
      return const [];
    }
  }
}
