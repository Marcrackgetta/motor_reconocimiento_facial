import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_database/firebase_database.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'representante_dashboard_screen.dart';

class RegistroScreen extends StatefulWidget {
  const RegistroScreen({super.key});

  @override
  State<RegistroScreen> createState() => _RegistroScreenState();
}

class _RegistroScreenState extends State<RegistroScreen> {
  final TextEditingController _nombreController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  
  bool _isLoading = false;
  bool _ocultarPassword = true; // NUEVO: Variable para controlar la visibilidad

  Future<void> _registrarRepresentante() async {
    if (_nombreController.text.isEmpty || _emailController.text.isEmpty || _passwordController.text.isEmpty) {
      _mostrarError('Por favor, complete todos los campos.');
      return;
    }

    setState(() => _isLoading = true);

    try {
      UserCredential userCredential = await FirebaseAuth.instance.createUserWithEmailAndPassword(
        email: _emailController.text.trim(),
        password: _passwordController.text,
      );

      final dbRef = FirebaseDatabase.instance.ref();
      await dbRef.child('Usuarios/${userCredential.user!.uid}').set({
        'rol': 'REPRESENTANTE',
        'correo': _emailController.text.trim(),
        'nombre': _nombreController.text.trim(),
      });

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('nombre', _nombreController.text.trim());

      if (mounted) {
        setState(() => _isLoading = false);
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(builder: (context) => const RepresentanteDashboardScreen()),
          (route) => false,
        );
      }
    } on FirebaseAuthException catch (e) {
      setState(() => _isLoading = false);
      String mensaje = 'Error al registrar.';
      if (e.code == 'weak-password') {
        mensaje = 'La contraseña es muy débil (mínimo 6 caracteres).';
      } else if (e.code == 'email-already-in-use') {
        mensaje = 'Ya existe una cuenta con este correo.';
      } else if (e.code == 'invalid-email') {
        mensaje = 'El formato del correo es inválido.';
      }
      _mostrarError(mensaje);
    } catch (e) {
      setState(() => _isLoading = false);
      _mostrarError('Error inesperado: $e');
    }
  }

  void _mostrarError(String mensaje) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(mensaje), backgroundColor: Colors.red),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.blueGrey[50],
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.blueGrey),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 400),
            child: Card(
              elevation: 4,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              child: Padding(
                padding: const EdgeInsets.all(32.0),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.person_add_alt_1, size: 48, color: Colors.blueGrey),
                    const SizedBox(height: 24),
                    const Text(
                      'Crear Cuenta',
                      style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.black87),
                    ),
                    const SizedBox(height: 32),
                    TextField(
                      controller: _nombreController,
                      decoration: InputDecoration(
                        labelText: 'Nombre Completo',
                        prefixIcon: const Icon(Icons.person_outline),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      textCapitalization: TextCapitalization.words,
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _emailController,
                      decoration: InputDecoration(
                        labelText: 'Correo Electrónico',
                        prefixIcon: const Icon(Icons.email_outlined),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      keyboardType: TextInputType.emailAddress,
                    ),
                    const SizedBox(height: 16),
                    // ==========================================
                    // NUEVO: Campo de Contraseña con el Ojito
                    // ==========================================
                    TextField(
                      controller: _passwordController,
                      obscureText: _ocultarPassword, // Controlado por la variable
                      decoration: InputDecoration(
                        labelText: 'Contraseña (mín. 6 caracteres)',
                        prefixIcon: const Icon(Icons.lock_outline),
                        suffixIcon: IconButton(
                          icon: Icon(
                            _ocultarPassword ? Icons.visibility_off : Icons.visibility,
                            color: Colors.blueGrey,
                          ),
                          onPressed: () {
                            setState(() {
                              _ocultarPassword = !_ocultarPassword; // Invierte el estado
                            });
                          },
                        ),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                    const SizedBox(height: 32),
                    SizedBox(
                      width: double.infinity,
                      height: 50,
                      child: ElevatedButton(
                        onPressed: _isLoading ? null : _registrarRepresentante,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.amber[600],
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                        child: _isLoading
                            ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                            : const Text('Registrarse', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}