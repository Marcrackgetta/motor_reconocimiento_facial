import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:control_acceso_app/main.dart'; // Importante para que encuentre la clase

void main() {
  testWidgets('Counter increments smoke test', (WidgetTester tester) async {
    // Aquí cambiamos MyApp() por ControlAccesoApp()
    await tester.pumpWidget(const ControlAccesoApp());

    expect(find.text('0'), findsOneWidget);
    expect(find.text('1'), findsNothing);

    await tester.tap(find.byIcon(Icons.add));
    await tester.pump();

    expect(find.text('0'), findsNothing);
    expect(find.text('1'), findsOneWidget);
  });
}
