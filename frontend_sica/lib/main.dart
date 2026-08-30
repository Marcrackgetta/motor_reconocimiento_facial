import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'firebase_options.dart'; 
import 'screens/login_screen.dart';
import 'services/push_notification_service.dart';

// Llave global para poder mostrar mensajes emergentes desde servicios en segundo plano
final GlobalKey<ScaffoldMessengerState> scaffoldMessengerKey = GlobalKey<ScaffoldMessengerState>();

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  debugPrint("Manejando mensaje en segundo plano: ${message.messageId}");
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

  final pushService = PushNotificationService();
  await pushService.initialize();

  runApp(const SicaApp());
}

class SicaApp extends StatelessWidget {
  const SicaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SICA Representantes',
      debugShowCheckedModeBanner: false,
      scaffoldMessengerKey: scaffoldMessengerKey, // <- Inyectamos la llave aquí
      theme: ThemeData(
        primarySwatch: Colors.blueGrey,
        scaffoldBackgroundColor: Colors.blueGrey[50],
      ),
      home: const LoginScreen(),
    );
  }
}