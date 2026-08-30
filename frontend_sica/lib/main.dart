import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'firebase_options.dart'; 
import 'screens/login_screen.dart';

Future<void> main() async {
  // Asegura que los bindings de Flutter estén listos antes de inicializar Firebase
  WidgetsFlutterBinding.ensureInitialized();
  
  // Inicializa Firebase con las credenciales autogeneradas por FlutterFire
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  runApp(const SicaApp());
}

class SicaApp extends StatelessWidget {
  const SicaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SICA Representantes',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primarySwatch: Colors.blueGrey,
        scaffoldBackgroundColor: Colors.blueGrey[50],
      ),
      home: const LoginScreen(),
    );
  }
}