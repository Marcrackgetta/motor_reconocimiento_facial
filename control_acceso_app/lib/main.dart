import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart'; // Importante para Firebase
import 'screens/login_screen.dart';

void main() async {
  // Asegura que los servicios de Flutter estén inicializados antes de correr la app
  WidgetsFlutterBinding.ensureInitialized();

  // Inicializa Firebase para Android/iOS
  await Firebase.initializeApp();

  runApp(const ControlAccesoApp());
}

class ControlAccesoApp extends StatelessWidget {
  const ControlAccesoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Control de Acceso Escolar',
      debugShowCheckedModeBanner:
          false, // Quita la banda de debug de la esquina
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue.shade900),
        useMaterial3: true,
      ),
      home: const LoginScreen(),
    );
  }
}
