import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:venera/pages/settings/settings_page.dart';
import 'package:venera/utils/translations.dart';

void main() {
  testWidgets('changelog page renders markdown content', (tester) async {
    await AppTranslation.init();

    await tester.pumpWidget(const MaterialApp(home: ChangelogPage()));
    await tester.pumpAndSettle();

    expect(find.text('更新日志'), findsWidgets);
    expect(find.text('# 更新日志'), findsNothing);
    expect(find.text('改进'), findsWidgets);
    expect(find.text('修复'), findsWidgets);
    expect(
      find.byWidgetPredicate((widget) => widget is Text && widget.data == '•'),
      findsWidgets,
    );
  });
}
