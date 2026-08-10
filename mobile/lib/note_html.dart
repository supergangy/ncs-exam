/// 오답노트 인쇄본의 HTML 을 만든다.
///
/// **Flutter 를 쓰지 않는다.** 그래야 `dart run tool/check_note_html.dart` 로
/// 뽑아 브라우저에 띄워 **실제 인쇄 모양을 눈으로** 볼 수 있다.
/// 안드로이드도 같은 HTML 을 WebView 로 그려 PDF 로 내므로 결과가 같다.
///
/// 서식은 PC 파이프라인의 `templates/solution.html.j2` 를 따라간다 — 같은 A4,
/// 같은 9.6pt, 같은 표 선. 종이로 놓고 보면 둘이 같은 물건이어야 한다.
library;

import 'models.dart';

/// `<` 를 글자로 넣어야 하는 자리(과목명 따위)에만 쓴다.
/// 발문·선지·해설은 **우리가 쓴 HTML** 이므로 손대지 않는다.
String _esc(String s) =>
    s.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');

const _circ = ['①', '②', '③', '④', '⑤', '⑥', '⑦'];

const noteCss = r'''
@page { size: A4; margin: 16mm 14mm 16mm 14mm; }
* { box-sizing: border-box; }
body {
  font-family: 'Malgun Gothic', 'Noto Sans KR', sans-serif;
  font-size: 9.6pt; line-height: 1.58; color: #000; margin: 0;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
p { margin: 0 0 3.2pt; }
h1.title { font-size: 17pt; font-weight: 800; letter-spacing: 2pt; margin: 0 0 1.5mm; }
.sub { font-size: 9pt; color: #444; margin: 0 0 5mm;
       border-bottom: 1.4pt solid #111; padding-bottom: 2.5mm; }

.q { margin-bottom: 6mm; break-inside: avoid; page-break-inside: avoid; }
.q-head { display: flex; align-items: baseline; gap: 3mm; flex-wrap: wrap;
          border-bottom: 0.7pt solid #111; padding-bottom: 1.2mm; margin-bottom: 2mm; }
.q-no { font-size: 12pt; font-weight: 800; }
.q-cls { font-size: 8.6pt; color: #fff; background: #555;
         padding: 0.5mm 2.2mm; border-radius: 2pt; }
.q-rd { font-size: 8.8pt; color: #555; }
.q-ans { font-size: 8.8pt; margin-left: auto; font-weight: 700; }
.q-ans.miss { color: #b3261e; }

.lead { font-size: 9pt; color: #444; margin-bottom: 1.5mm; }
.stem { font-weight: 700; margin: 2mm 0; }

ul.ch { list-style: none; margin: 0 0 2.5mm; padding: 0; }
ul.ch li { padding-left: 5.4mm; text-indent: -5.4mm; margin-bottom: 0.8mm; }
ul.ch li.ok { font-weight: 800; }
ul.ch li.ok::after { content: ' ✓'; }
ul.ch li.picked { color: #b3261e; }
ul.ch li.picked::after { content: ' ✗ 내가 고른 답'; font-size: 8.4pt; }

.oh { font-weight: 700; font-size: 9.2pt; margin: 2.4mm 0 1.2mm;
      border-left: 2.2pt solid #111; padding-left: 2mm; }
ul.each { list-style: none; margin: 0; padding: 0; }
ul.each li { padding-left: 4.6mm; text-indent: -4.6mm; margin-bottom: 1mm;
             font-size: 9.2pt; color: #222; }
ul.each li.ok { font-weight: 700; color: #000; }

table { border-collapse: collapse; font-size: 8.8pt; margin: 1.5mm 0; }
table caption { font-weight: 700; text-align: left; margin-bottom: 1.2mm; }
th, td { border: 0.5pt solid #333; padding: 1mm 1.6mm; text-align: center; }
th { background: #efefef; }
code { font-family: Consolas, 'Courier New', monospace; font-size: 9pt; }
svg { display: block; margin: 1.5mm auto; max-width: 100%; height: auto; }
svg text { font-family: 'Malgun Gothic', 'Noto Sans KR', sans-serif; }
u { text-decoration: underline; }
''';

/// 앞머리 원문자를 뗀다 (선지 옆에 이미 붙으므로 겹친다).
final _leadRe = RegExp(r'^[①②③④⑤⑥⑦]\s*');

/// 인쇄용 HTML 한 장.
///
/// [passage]·[roundTitle]·[picked] 는 앱에서 `Repo`/`Store` 를 물려 준다.
/// 없으면 그 부분만 빠지고 나머지는 그대로 나온다 — 검증 스크립트가 그렇게 쓴다.
String buildNoteHtml(
  List<Item> items, {
  required String title,
  required DateTime at,
  PassageEntry? Function(int idx)? passage,
  String? Function(String tag)? roundTitle,
  int? Function(String id)? picked,
}) {
  final b = StringBuffer()
    ..writeln('<!doctype html><meta charset="utf-8">')
    ..writeln('<meta name="viewport" content="width=device-width,initial-scale=1">')
    ..writeln('<title>${_esc(title)}</title>')
    ..writeln('<style>$noteCss</style>')
    ..writeln('<h1 class="title">${_esc(title)}</h1>')
    ..writeln('<div class="sub">NCS 기출은행 · '
        '${at.year}년 ${at.month}월 ${at.day}일 · ${items.length}문항</div>');

  for (var i = 0; i < items.length; i++) {
    final it = items[i];
    final chose = picked?.call(it.id);
    final missed = chose != null && chose != it.an;

    b.writeln('<div class="q">');
    b.writeln('  <div class="q-head">');
    b.writeln('    <span class="q-no">${i + 1}</span>');
    b.writeln('    <span class="q-cls">${_esc(it.sj)} · ${_esc(it.ty)}</span>');
    if (it.rd != null) {
      final r = roundTitle?.call(it.rd!) ?? it.rd!;
      b.writeln('    <span class="q-rd">${_esc(r)} ${it.no}번</span>');
    }
    b.writeln('    <span class="q-ans${missed ? ' miss' : ''}">'
        '${missed ? '고른 답 ${_circ[chose - 1]} · ' : ''}'
        '정답 ${_circ[it.an - 1]}</span>');
    b.writeln('  </div>');

    // 지문·자료는 우리가 쓴 HTML 그대로 — WebView 가 표와 SVG 를 알아서 그린다.
    if (it.pg != null) {
      final pg = passage?.call(it.pg!);
      if (pg != null) {
        if (pg.lead != null) b.writeln('  <div class="lead">${_esc(pg.lead!)}</div>');
        b.writeln('  <div>${pg.body}</div>');
      }
    } else if (it.ld != null) {
      b.writeln('  <div class="lead">${_esc(it.ld!)}</div>');
    }
    if (it.mt != null) b.writeln('  <div>${it.mt}</div>');

    b.writeln('  <div class="stem">${it.st}</div>');
    b.writeln('  <ul class="ch">');
    for (var n = 0; n < it.ch.length; n++) {
      final cls = [
        if (n + 1 == it.an) 'ok',
        if (missed && chose == n + 1) 'picked',
      ].join(' ');
      b.writeln('    <li${cls.isEmpty ? '' : ' class="$cls"'}>'
          '${_circ[n]} ${it.ch[n]}</li>');
    }
    b.writeln('  </ul>');

    if (it.ex != null) {
      b.writeln('  <div class="oh">해설</div>');
      b.writeln('  <div>${it.ex}</div>');
    }
    if (it.ea != null && it.ea!.isNotEmpty) {
      b.writeln('  <div class="oh">선택지 해설</div>');
      b.writeln('  <ul class="each">');
      for (var n = 0; n < it.ea!.length; n++) {
        b.writeln('    <li${n + 1 == it.an ? ' class="ok"' : ''}>'
            '${it.ea![n].replaceFirst(_leadRe, '')}</li>');
      }
      b.writeln('  </ul>');
    }
    b.writeln('</div>');
  }
  return b.toString();
}
