/// 필기 좌표가 **화면이 바뀌어도 같은 자리에 찍히는지** 확인한다.
///
/// 4단계에서 가장 위험한 곳이다. 화면 폭으로 저장하면 다음에 열 때 획이 딴 데
/// 찍히는데, 그건 눈으로 보기 전에는 드러나지 않는다. `flutter test` 가 이
/// 환경에서 못 돌아 순수 Dart 로 본다 (`lib/ink.dart` 가 dart:ui 를 안 쓰는 이유).
///
/// 특히 볼 것 —
///  · 위젯 좌표 → PDF 점 → 위젯 좌표 **왕복이 제자리**인가
///  · 화면 폭을 바꿔도 **PDF 점이 같은가** (회전·분할화면)
///  · 지우개가 **닿은 획만** 지우는가 · 굵은 획의 가장자리도 집는가
///  · 되돌리기가 획 단위인가 · 새로 그리면 다시하기가 끊기는가
///  · 저장 문자열이 왕복해도 좌표가 안 흔들리는가
///  · 깨진 행 하나가 회차 전체를 막지 않는가
///
///   dart run tool/check_ink.dart
library;

import 'dart:convert';
import 'dart:io';

import 'package:ncs_bank/ink.dart';

int _fail = 0, _pass = 0;

void ok(String label, bool cond) {
  if (cond) {
    _pass++;
  } else {
    _fail++;
    stdout.writeln('  ✗ $label');
  }
}

void eq(String label, Object? got, Object? want) {
  if ('$got' == '$want') {
    _pass++;
  } else {
    _fail++;
    stdout.writeln('  ✗ $label\n      나온 것 $got\n      바란 것 $want');
  }
}

void near(String label, double got, double want, [double tol = 0.02]) {
  if ((got - want).abs() <= tol) {
    _pass++;
  } else {
    _fail++;
    stdout.writeln('  ✗ $label\n      나온 것 $got\n      바란 것 $want (±$tol)');
  }
}

// r2_korail 3쪽에서 오려 낸 문항 하나라고 보자.
const bx = 40.0, by = 96.0, bw = 515.0;

Stroke line(int page, List<(double, double)> pts,
        {String tool = toolPen, double w = 1.6}) =>
    Stroke(
      page: page,
      tool: tool,
      color: 0xFF1A1A1A,
      width: w,
      pts: [for (final (x, y) in pts) InkPoint(x, y)],
    );

void main() {
  stdout.writeln('■ 좌표 왕복');
  {
    // 폭 360 짜리 화면에서 (100, 50) 을 찍었다.
    final p = localToPage(100, 50, bx: bx, by: by, bw: bw, widgetW: 360);
    final (lx, ly) = pageToLocal(p.x, p.y, bx: bx, by: by, bw: bw, widgetW: 360);
    near('왕복 x', lx, 100);
    near('왕복 y', ly, 50);
    // 사각형 왼쪽 위는 위젯 원점이다.
    final origin = localToPage(0, 0, bx: bx, by: by, bw: bw, widgetW: 360);
    near('원점 → 사각형 왼쪽 위 x', origin.x, bx);
    near('원점 → 사각형 왼쪽 위 y', origin.y, by);
    // 오른쪽 끝은 사각형 오른쪽 끝이다.
    final right = localToPage(360, 0, bx: bx, by: by, bw: bw, widgetW: 360);
    near('오른쪽 끝', right.x, bx + bw);
  }

  stdout.writeln('■ 화면 폭이 바뀌어도 같은 자리');
  {
    // 같은 종이 위 같은 점을, 폭 360 과 폭 1024 화면에서 각각 찍는다.
    // 화면에서의 상대 위치가 같으면 PDF 점도 같아야 한다.
    final small = localToPage(90, 45, bx: bx, by: by, bw: bw, widgetW: 360);
    final large = localToPage(90 * 1024 / 360, 45 * 1024 / 360,
        bx: bx, by: by, bw: bw, widgetW: 1024);
    near('폭 360 과 1024 의 x 가 같다', large.x, small.x);
    near('폭 360 과 1024 의 y 가 같다', large.y, small.y);

    // 반대로, 저장된 PDF 점을 두 화면에 다시 그리면 비율이 같아야 한다.
    final (sx, _) = pageToLocal(small.x, small.y, bx: bx, by: by, bw: bw, widgetW: 360);
    final (gx, _) = pageToLocal(small.x, small.y, bx: bx, by: by, bw: bw, widgetW: 1024);
    near('되그릴 때 비율 유지', gx / 1024, sx / 360, 0.001);

    // 굵기도 페이지 점이라 큰 화면에서 굵어진다 (가늘어지지 않는다).
    final wSmall = pageLenToLocal(inkWidth[toolPen]!, bw: bw, widgetW: 360);
    final wLarge = pageLenToLocal(inkWidth[toolPen]!, bw: bw, widgetW: 1024);
    ok('큰 화면에서 굵기가 커진다', wLarge > wSmall);
    near('굵기 비 = 폭 비', wLarge / wSmall, 1024 / 360, 0.001);
  }

  stdout.writeln('■ 지우개');
  {
    final doc = InkDoc();
    doc.add(line(3, [(100, 100), (200, 100)])); // 가로선
    doc.add(line(3, [(100, 300), (200, 300)])); // 멀리 떨어진 가로선
    doc.add(line(4, [(100, 100), (200, 100)])); // 다른 쪽 같은 자리

    eq('획 셋', doc.count, 3);
    eq('선 위를 찍으면 하나 지운다', doc.eraseAt(3, 150, 100), 1);
    eq('남은 획 둘', doc.count, 2);
    eq('빈 곳을 찍으면 안 지운다', doc.eraseAt(3, 150, 200), 0);
    // 페이지가 다르면 좌표가 같아도 안 지운다 — 3쪽에서 지운 것이 4쪽에 번지면 안 된다.
    eq('다른 쪽 획은 남는다', doc.ofPage(4).length, 1);

    // 굵은 형광펜은 가장자리를 스쳐도 지워진다.
    final thick = InkDoc()
      ..add(line(1, [(100, 100), (200, 100)], tool: toolMarker, w: 11));
    ok('형광펜 가장자리(중심에서 8점)도 집는다',
        thick.eraseAt(1, 150, 108) == 1);
    final thin = InkDoc()..add(line(1, [(100, 100), (200, 100)], w: 1.6));
    eq('가는 연필은 같은 거리에서 안 지워진다', thin.eraseAt(1, 150, 108), 0);

    // 겹쳤을 때 위엣것부터
    final over = InkDoc()
      ..add(line(1, [(100, 100), (200, 100)]))
      ..add(line(1, [(100, 100), (200, 100)]));
    over.eraseAt(1, 150, 100);
    eq('겹친 곳에서 한 번에 하나만', over.count, 1);
  }

  stdout.writeln('■ 되돌리기 · 다시하기');
  {
    final doc = InkDoc();
    ok('빈 상태에서는 되돌릴 것이 없다', !doc.canUndo);
    doc.add(line(2, [(10, 10), (20, 20)]));
    doc.add(line(2, [(30, 30), (40, 40)]));
    eq('되돌리면 쪽 번호를 준다', doc.undo(), 2);
    eq('획 하나 남는다', doc.count, 1);
    ok('다시할 것이 생겼다', doc.canRedo);
    eq('다시하면 돌아온다', doc.redo(), 2);
    eq('획 둘', doc.count, 2);

    // 되돌린 뒤 새로 그리면 다시하기 사슬이 끊긴다.
    doc.undo();
    doc.add(line(2, [(50, 50), (60, 60)]));
    ok('새로 그리면 다시하기가 끊긴다', !doc.canRedo);

    // 지운 것도 되돌릴 수 있어야 한다 — 잘못 지우면 되살려야 한다.
    final e = InkDoc()..add(line(1, [(100, 100), (200, 100)]));
    e.eraseAt(1, 150, 100);
    eq('지운 뒤 0개', e.count, 0);
    ok('지운 것을 되살릴 수 있다', e.canRedo);
    e.redo();
    eq('되살아난 획', e.count, 1);
  }

  stdout.writeln('■ 저장 · 되읽기');
  {
    final doc = InkDoc();
    doc.add(line(3, [(100.123, 100.456), (200.789, 100.111)]));
    doc.add(line(3, [(10, 20), (30, 40)], tool: toolMarker, w: 11));
    doc.add(line(7, [(1, 2), (3, 4)]));

    eq('바뀐 쪽 둘', doc.dirty.length, 2);
    ok('3쪽과 7쪽', doc.dirty.contains(3) && doc.dirty.contains(7));

    final pages = {for (final p in doc.byPage.keys) p: doc.encodePage(p)};
    final back = InkDoc.decode(pages);
    eq('되읽은 획 수', back.count, 3);
    eq('3쪽 획 둘', back.ofPage(3).length, 2);
    eq('7쪽 획 하나', back.ofPage(7).length, 1);

    final a = doc.ofPage(3).first.pts.first;
    final b = back.ofPage(3).first.pts.first;
    near('좌표가 왕복해도 같다 (x)', b.x, a.x, 0.01);
    near('좌표가 왕복해도 같다 (y)', b.y, a.y, 0.01);
    eq('도구가 살아남는다', back.ofPage(3)[1].tool, toolMarker);
    near('굵기가 살아남는다', back.ofPage(3)[1].width, 11);

    // 자릿수를 줄여 저장한다 — 원본보다 짧아야 한다.
    final raw = doc.encodePage(3);
    ok('소수점 둘째 자리까지만', !raw.contains('100.123'));
    ok('세 자리 줄임이 실제로 준다',
        raw.length < jsonEncode([
          for (final s in doc.ofPage(3))
            {'g': s.page, 't': s.tool, 'c': s.color, 'w': s.width,
             'v': [for (final q in s.pts) {'x': q.x, 'y': q.y, 'p': q.p}]}
        ]).length);

    eq('빈 쪽은 빈 문자열', doc.encodePage(99), '');
  }

  stdout.writeln('■ 깨진 행');
  {
    eq('깨진 JSON 은 그 쪽만 버린다', InkDoc.decodePage('{이건 JSON 이 아니다').length, 0);
    eq('빈 문자열', InkDoc.decodePage('').length, 0);
    eq('목록이 아닌 것', InkDoc.decodePage('{"g":1}').length, 0);
    // 한 쪽이 깨져도 나머지는 읽힌다.
    final mixed = InkDoc.decode({
      3: '망가진 값',
      4: jsonEncode([line(4, [(1, 1), (2, 2)]).toJson()]),
    });
    eq('멀쩡한 쪽은 살아남는다', mixed.count, 1);
    eq('살아남은 쪽 번호', mixed.strokes.first.page, 4);
  }

  stdout.writeln('■ 점 하나짜리 획 (톡 찍은 점)');
  {
    final dot = InkDoc()
      ..add(Stroke(page: 1, tool: toolPen, color: 0xFF000000, width: 1.6,
          pts: const [InkPoint(50, 50)]));
    eq('점도 저장된다', dot.count, 1);
    eq('점 위를 찍으면 지워진다', dot.eraseAt(1, 51, 51), 1);
    final dot2 = InkDoc()
      ..add(Stroke(page: 1, tool: toolPen, color: 0xFF000000, width: 1.6,
          pts: const [InkPoint(50, 50)]));
    eq('먼 곳은 안 지워진다', dot2.eraseAt(1, 200, 200), 0);
    // 빈 획은 들어가지 않는다 — 화면을 스치기만 해도 행이 늘면 안 된다.
    final empty = InkDoc()
      ..add(const Stroke(page: 1, tool: toolPen, color: 0, width: 1, pts: []));
    eq('빈 획은 버린다', empty.count, 0);
  }

  stdout.writeln('■ 펜 태블릿 — 팜 리젝션');
  {
    InkInput.reset();
    // 펜을 보기 전: 손가락으로도 그린다 (펜 없는 폰).
    eq('펜 전 · 손가락 → 그린다',
        InkInput.actionFor(InkPointer.touch, drawing: true), InkAction.draw);
    eq('펜 전 · 손가락 + 지우개 → 지운다',
        InkInput.actionFor(InkPointer.touch, drawing: false), InkAction.erase);

    // 펜이 한 번 닿으면 그 뒤로 손가락은 그리지 않는다 — 손바닥이다.
    eq('펜 → 그린다',
        InkInput.actionFor(InkPointer.stylus, drawing: true), InkAction.draw);
    InkInput.stylusSeen = true;
    eq('펜 본 뒤 · 손가락 → 무시',
        InkInput.actionFor(InkPointer.touch, drawing: true), InkAction.ignore);
    eq('펜 본 뒤 · 손가락 + 지우개도 무시',
        InkInput.actionFor(InkPointer.touch, drawing: false), InkAction.ignore);
    eq('펜 본 뒤에도 펜은 그린다',
        InkInput.actionFor(InkPointer.stylus, drawing: true), InkAction.draw);

    // 펜을 뒤집으면 도구와 상관없이 지우개다 (S펜·서피스펜).
    eq('뒤집은 펜 → 지운다 (연필 도구여도)',
        InkInput.actionFor(InkPointer.invertedStylus, drawing: true),
        InkAction.erase);
    eq('뒤집은 펜 → 지운다 (지우개 도구여도)',
        InkInput.actionFor(InkPointer.invertedStylus, drawing: false),
        InkAction.erase);

    // 마우스는 데스크톱 확인용이라 팜 리젝션과 무관하게 받는다.
    eq('마우스는 펜 본 뒤에도 그린다',
        InkInput.actionFor(InkPointer.other, drawing: true), InkAction.draw);
    InkInput.reset();
    ok('되돌리면 손가락이 다시 그린다',
        InkInput.actionFor(InkPointer.touch, drawing: true) == InkAction.draw);
  }

  stdout.writeln('■ 필압이 진짜인가');
  {
    Stroke withP(List<double> ps) => Stroke(
        page: 1, tool: toolPen, color: 0, width: 1.6,
        pts: [for (var i = 0; i < ps.length; i++) InkPoint(i * 10, 0, ps[i])]);
    ok('값이 다 같으면 흉내다', !withP([0.5, 0.5, 0.5]).hasRealPressure);
    ok('값이 흔들리면 진짜다', withP([0.2, 0.6, 0.9]).hasRealPressure);
    ok('아주 작은 차이는 흉내로 본다', !withP([0.50, 0.51, 0.50]).hasRealPressure);
    ok('점 하나는 알 수 없으니 흉내', !withP([0.7]).hasRealPressure);
    // 저장했다 읽어도 판정이 그대로여야 한다 — 소수점 둘째 자리로 줄이므로
    // 차이가 그 아래로 깎이면 진짜가 흉내로 바뀐다.
    final real = withP([0.20, 0.65, 0.95]);
    final back = InkDoc.decodePage(
        jsonEncode([real.toJson()])).first;
    ok('왕복해도 진짜 필압으로 남는다', back.hasRealPressure);
  }

  stdout.writeln('■ 선분 거리');
  {
    near('선분 위', segmentDistance(150, 100, 100, 100, 200, 100), 0);
    near('선분 바로 위쪽 10', segmentDistance(150, 90, 100, 100, 200, 100), 10);
    // 선분 끝을 지나쳐도 끝점까지의 거리로 잰다 (무한 직선이 아니다).
    near('선분 밖 끝점 거리', segmentDistance(300, 100, 100, 100, 200, 100), 100);
    near('길이 0 인 선분', segmentDistance(3, 4, 0, 0, 0, 0), 5);
  }

  stdout.writeln('\n통과 $_pass · 실패 $_fail');
  if (_fail > 0) exit(1);
}
