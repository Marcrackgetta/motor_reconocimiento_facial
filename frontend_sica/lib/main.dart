import 'package:flutter/material.dart';
import 'screens/login_screen.dart';

void main() {
  runApp(const SicaApp());
}

class SicaApp extends StatelessWidget {
  const SicaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SICA Flutter',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.amber),
        useMaterial3: true,
        fontFamily: 'Roboto', 
      ),
      // Configuramos la nueva pantalla de Login como página de inicio
      home: const LoginScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}