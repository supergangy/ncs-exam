import 'package:flutter_test/flutter_test.dart';

import 'package:ncs_bank/main.dart';

void main() {
  testWidgets('앱이 뜨고 홈 화면이 보인다', (WidgetTester tester) async {
    await tester.pumpWidget(const NcsPassApp());
    await tester.pumpAndSettle();

    expect(find.text('NCS PASS'), findsOneWidget);
  });
}
