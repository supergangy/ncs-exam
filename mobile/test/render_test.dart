/// 화면을 눈으로 볼 수 없는 환경이라, **눈으로 보던 것을 테스트로 대신 본다.**
/// 설치본에서 발견된 두 버그(표가 안 나옴 · `&lt;보기&gt;` 노출)의 회귀 방지가 목적이다.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ncs_bank/html_view.dart';

Widget _wrap(Widget child) => MaterialApp(home: Scaffold(body: SingleChildScrollView(child: child)));

void main() {
  group('plainText — 목록·검색용 순수 텍스트', () {
    test('문자 참조를 푼다 (설치본 버그: &lt;보기&gt; 가 그대로 나왔다)', () {
      expect(plainText('윗글을 바탕으로 &lt;보기&gt;의 사례를'), '윗글을 바탕으로 <보기>의 사례를');
      expect(plainText('&lt;조건&gt;에 따라'), '<조건>에 따라');
      expect(plainText('A&amp;B'), 'A&B');
    });

    test('윗첨자를 유니코드로 살린다 — 공백을 끼우면 값이 바뀐다', () {
      expect(plainText('36π − 72 (cm<sup>2</sup>)'), '36π − 72 (cm²)');
      expect(plainText('2<sup>10</sup>바이트'), '2¹⁰바이트');
      expect(plainText('H<sub>2</sub>O'), 'H₂O');
    });

    test('유니코드로 못 옮기는 첨자는 붙여 쓴다', () {
      expect(plainText('x<sup>n+1</sup>'), 'xⁿ⁺¹');
      expect(plainText('a<sup>k</sup>'), 'ak');
    });

    test('밑줄·강조는 글자만 남긴다', () {
      expect(plainText('그렇게 하면 <u>안 되요</u>.'), '그렇게 하면 안 되요.');
    });

    test('표는 칸 사이를 띄운다', () {
      expect(plainText('<table><tr><td>가</td><td>나</td></tr></table>'), '가 나');
    });
  });

  group('HtmlText — 발문·선지', () {
    testWidgets('&lt;보기&gt; 가 꺾쇠로 보인다', (t) async {
      await t.pumpWidget(_wrap(const HtmlText('옳은 것을 &lt;보기&gt;에서 고르면?',
          style: TextStyle(fontSize: 15))));
      expect(find.textContaining('<보기>', findRichText: true), findsOneWidget);
    });

    testWidgets('밑줄이 살아 있다 — 어문규범 문항은 밑줄이 곧 문제다', (t) async {
      await t.pumpWidget(_wrap(const HtmlText('담당자<u>로써</u> 책임을',
          style: TextStyle(fontSize: 15))));
      final rich = t.widget<Text>(find.byType(Text).first);
      var underlined = false;
      rich.textSpan!.visitChildren((s) {
        if (s is TextSpan && s.text == '로써' &&
            s.style?.decoration == TextDecoration.underline) {
          underlined = true;
        }
        return true;
      });
      expect(underlined, isTrue, reason: '<u> 가 밑줄로 그려져야 한다');
    });

    testWidgets('윗첨자는 지워지지 않는다', (t) async {
      await t.pumpWidget(_wrap(const HtmlText('넓이는 36π (cm<sup>2</sup>)',
          style: TextStyle(fontSize: 15))));
      expect(find.textContaining('2', findRichText: true), findsWidgets);
    });

    testWidgets('모르는 태그는 껍데기만 버리고 속글은 남긴다', (t) async {
      await t.pumpWidget(_wrap(const HtmlText('앞 <weird>속글</weird> 뒤',
          style: TextStyle(fontSize: 15))));
      expect(find.textContaining('속글', findRichText: true), findsOneWidget);
    });
  });

  group('HtmlBox — 자료·해설', () {
    testWidgets('표의 칸이 화면에 나온다 (설치본 버그: 표가 통째로 사라졌다)', (t) async {
      const html = '<table><caption>발전량</caption>'
          '<tr><th>연도</th><th>원자력</th></tr>'
          '<tr><td>2023</td><td>176</td></tr>'
          '<tr><td>2024</td><td>188</td></tr></table>';
      await t.pumpWidget(_wrap(const HtmlBox(html)));
      await t.pumpAndSettle();
      for (final cell in ['연도', '원자력', '2023', '176', '2024', '188']) {
        expect(find.textContaining(cell, findRichText: true), findsWidgets,
            reason: '표의 「$cell」 칸이 보여야 한다');
      }
    });
  });

  group('hasBlockHtml', () {
    test('블록 태그를 알아본다', () {
      expect(hasBlockHtml('<table><tr><td>가</td></tr></table>'), isTrue);
      expect(hasBlockHtml('<p>글</p>'), isTrue);
      expect(hasBlockHtml('밑줄 <u>친</u> 곳'), isFalse);
      expect(hasBlockHtml('cm<sup>2</sup>'), isFalse);
    });
  });
}
