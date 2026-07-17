import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'login_screen.dart'; // Importamos la pantalla de login para poder regresar
import 'package:flutter/services.dart' show rootBundle;

class DashboardScreen extends StatefulWidget {
  final String rol;
  const DashboardScreen({super.key, required this.rol});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late final WebViewController _controller;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();

    // Obtenemos el correo del usuario actual de Firebase
    final user = FirebaseAuth.instance.currentUser;
    final userEmail = user?.email ?? "usuario@anai.edu.ec";

    // Test para verificar que el HTML está accesible
    rootBundle
        .loadString('assets/dashboard/index.html')
        .then((value) {
          print("✅ FLUTTER SÍ ENCONTRÓ Y LEYÓ EL ARCHIVO HTML!");
        })
        .catchError((error) {
          print("❌ FLUTTER ESTÁ CIEGO, NO ENCUENTRA EL ARCHIVO: $error");
        });

    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (String url) {
            print('Intentando cargar: $url');
          },
          onPageFinished: (String url) {
            print('Carga exitosa de: $url');

            // 🔥 INYECCIÓN DE DATOS: Mandamos el rol y el correo a la página web
            _controller.runJavaScript(
              "recibirDatosDeFlutter('${widget.rol}', '$userEmail');",
            );

            if (mounted) {
              setState(() {
                _isLoading = false;
              });
            }
          },
          onWebResourceError: (WebResourceError error) {
            print('ERROR DEL WEBVIEW: ${error.description}');
            if (mounted) {
              setState(() {
                _isLoading = false; // Detenemos el círculo aunque falle
              });
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(
                    'Error cargando el panel: ${error.description}',
                  ),
                ),
              );
            }
          },
        ),
      )
      ..loadFlutterAsset('assets/dashboard/index.html');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Dashboard - ${widget.rol}'),
        backgroundColor: Colors.blue.shade900,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Cerrar Sesión',
            onPressed: () async {
              // Cierra la sesión en Firebase
              await FirebaseAuth.instance.signOut();
              if (context.mounted) {
                // Regresa a la pantalla de Login
                Navigator.of(context).pushReplacement(
                  MaterialPageRoute(builder: (context) => const LoginScreen()),
                );
              }
            },
          ),
        ],
      ),
      body: Stack(
        children: [
          WebViewWidget(controller: _controller),
          if (_isLoading) const Center(child: CircularProgressIndicator()),
        ],
      ),
    );
  }
}
