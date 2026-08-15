import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/auth_service.dart';
import 'login_screen.dart';
import 'representante_dashboard_screen.dart';
import 'inspector_dashboard_screen.dart';
import 'admin_usuarios_screen.dart';
import 'admin_estudiantes_screen.dart';
import 'admin_cursos_screen.dart'; // Nueva importación

class AdminDashboardScreen extends StatefulWidget {
  const AdminDashboardScreen({super.key});

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen> {
  String _nombreUsuario = 'Cargando...';

  @override
  void initState() {
    super.initState();
    _cargarDatosUsuario();
  }

  Future<void> _cargarDatosUsuario() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _nombreUsuario = prefs.getString('nombre') ?? 'Administrador Principal';
    });
  }

  void _cerrarSesion() async {
    await AuthService().logout();
    if (mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const LoginScreen()),
      );
    }
  }

  void _cambiarDeVista(String vistaDestino) {
    Widget pantalla;
    if (vistaDestino == 'Inspector') {
      pantalla = const InspectorDashboardScreen();
    } else if (vistaDestino == 'Representante') {
      pantalla = const RepresentanteDashboardScreen();
    } else {
      return;
    }

    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => pantalla),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: const Text('SICA - Administración', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
        backgroundColor: Colors.blueGrey[800],
        elevation: 0,
        actions: [
          PopupMenuButton<String>(
            icon: const Icon(Icons.remove_red_eye, color: Colors.white),
            tooltip: 'Cambiar de Vista',
            onSelected: _cambiarDeVista,
            itemBuilder: (BuildContext context) => <PopupMenuEntry<String>>[
              const PopupMenuItem<String>(
                value: 'Representante',
                child: ListTile(
                  leading: Icon(Icons.family_restroom, color: Colors.amber),
                  title: Text('Vista Representante'),
                  contentPadding: EdgeInsets.zero,
                ),
              ),
              const PopupMenuItem<String>(
                value: 'Inspector',
                child: ListTile(
                  leading: Icon(Icons.badge, color: Colors.teal),
                  title: Text('Vista Inspector'),
                  contentPadding: EdgeInsets.zero,
                ),
              ),
            ],
          ),
          IconButton(
            icon: const Icon(Icons.logout, color: Colors.white),
            onPressed: _cerrarSesion,
            tooltip: 'Cerrar Sesión',
          ),
        ],
      ),
      body: Column(
        children: [
          _construirEncabezado(),
          Expanded(child: _construirGridModulos()),
        ],
      ),
    );
  }

  Widget _construirEncabezado() {
    return Container(
      width: double.infinity,
      color: Colors.white,
      padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 16),
      margin: const EdgeInsets.only(bottom: 10),
      child: Column(
        children: [
          const Text('Panel de Control Principal', style: TextStyle(fontSize: 16, color: Colors.black54)),
          const SizedBox(height: 4),
          Text(
            _nombreUsuario.toUpperCase(),
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: Colors.blueGrey),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _construirGridModulos() {
    final modulos = [
      {'titulo': 'Usuarios', 'icono': Icons.manage_accounts, 'color': Colors.blue},
      {'titulo': 'Representantes', 'icono': Icons.family_restroom, 'color': Colors.amber[700]},
      {'titulo': 'Inspectores', 'icono': Icons.badge, 'color': Colors.teal},
      {'titulo': 'Estudiantes', 'icono': Icons.face, 'color': Colors.orange},
      {'titulo': 'Cursos', 'icono': Icons.school, 'color': Colors.indigo},
      {'titulo': 'Jornadas', 'icono': Icons.wb_sunny, 'color': Colors.deepOrange},
      {'titulo': 'Asignaciones', 'icono': Icons.assignment_ind, 'color': Colors.purple},
      {'titulo': 'Notificaciones', 'icono': Icons.notifications_active, 'color': Colors.redAccent},
      {'titulo': 'Configuración', 'icono': Icons.settings, 'color': Colors.grey[700]},
    ];

    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2, 
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
        childAspectRatio: 1.1, 
      ),
      itemCount: modulos.length,
      itemBuilder: (context, index) {
        final modulo = modulos[index];
        return _construirTarjetaModulo(
          titulo: modulo['titulo'] as String,
          icono: modulo['icono'] as IconData,
          colorBase: modulo['color'] as Color,
        );
      },
    );
  }

  Widget _construirTarjetaModulo({required String titulo, required IconData icono, required Color colorBase}) {
    return InkWell(
      onTap: () {
        // Lógica actualizada para enrutar a la gestión de Cursos
        if (titulo == 'Usuarios') {
          Navigator.push(context, MaterialPageRoute(builder: (context) => const AdminUsuariosScreen()));
        } else if (titulo == 'Estudiantes') {
          Navigator.push(context, MaterialPageRoute(builder: (context) => const AdminEstudiantesScreen()));
        } else if (titulo == 'Cursos') {
          Navigator.push(context, MaterialPageRoute(builder: (context) => const AdminCursosScreen()));
        } else {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Módulo de $titulo funcional en proceso...')));
        }
      },
      borderRadius: BorderRadius.circular(15),
      child: Card(
        elevation: 3,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(15),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [colorBase.withOpacity(0.1), Colors.white],
            ),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: colorBase.withOpacity(0.2), shape: BoxShape.circle),
                child: Icon(icono, size: 36, color: colorBase),
              ),
              const SizedBox(height: 12),
              Text(titulo, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Colors.black87), textAlign: TextAlign.center),
            ],
          ),
        ),
      ),
    );
  }
}