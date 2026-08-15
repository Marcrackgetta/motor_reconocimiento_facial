import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../models/estudiante.dart';
import 'estudiante_detalle_screen.dart';
import 'login_screen.dart'; 

class RepresentanteDashboardScreen extends StatefulWidget {
  const RepresentanteDashboardScreen({super.key});

  @override
  State<RepresentanteDashboardScreen> createState() => _RepresentanteDashboardScreenState();
}

class _RepresentanteDashboardScreenState extends State<RepresentanteDashboardScreen> {
  final ApiService _apiService = ApiService();
  List<Estudiante> _estudiantes = [];
  bool _isLoading = true;
  String _errorMessage = '';
  String _nombreUsuario = 'Cargando...'; 

  @override
  void initState() {
    super.initState();
    _cargarDatosUsuario(); 
    _cargarEstudiantes();  
  }

  Future<void> _cargarDatosUsuario() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _nombreUsuario = prefs.getString('nombre') ?? 'Representante';
    });
  }

  Future<void> _cargarEstudiantes() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      final estudiantes = await _apiService.fetchEstudiantes();
      setState(() {
        _estudiantes = estudiantes;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = "No se pudo conectar con el servidor.\nVerifique su conexión.";
        _isLoading = false;
      });
    }
  }

  void _cerrarSesion() async {
    final authService = AuthService();
    await authService.logout();
    if (mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => const LoginScreen()),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: const Text('SICA', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 24, letterSpacing: 1.2, color: Colors.black87)),
        backgroundColor: Colors.amber[400], 
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.black87),
            onPressed: _cargarEstudiantes,
          ),
          IconButton(
            icon: const Icon(Icons.logout, color: Colors.black87), 
            onPressed: _cerrarSesion,
          ), 
        ],
      ),
      body: Column(
        children: [
          _construirEncabezadoRepresentante(),
          Expanded(
            child: _construirListaEstudiantes(),
          ),
        ],
      ),
      // EL BOTÓN FLOTANTE DE "AGREGAR ALUMNO" HA SIDO ELIMINADO CUMPLIENDO LA REGLA DE NEGOCIO
    );
  }

  Widget _construirEncabezadoRepresentante() {
    return Container(
      width: double.infinity,
      color: Colors.white,
      padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 16),
      margin: const EdgeInsets.only(bottom: 10),
      child: Column(
        children: [
          const Text('Bienvenido', style: TextStyle(fontSize: 16, color: Colors.black54)),
          const SizedBox(height: 4),
          Text(
            _nombreUsuario.toUpperCase(), 
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _construirListaEstudiantes() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator(color: Colors.amber));
    }

    if (_errorMessage.isNotEmpty) {
      return Center(child: Text(_errorMessage, textAlign: TextAlign.center));
    }

    if (_estudiantes.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(32.0),
          child: Text(
            'Aún no tiene estudiantes asignados.\nConsulte con la administración.', 
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.black54, fontSize: 16)
          ),
        )
      );
    }

    return RefreshIndicator(
      color: Colors.amber,
      onRefresh: _cargarEstudiantes,
      child: ListView.builder(
        padding: const EdgeInsets.all(16), 
        itemCount: _estudiantes.length,
        itemBuilder: (context, index) {
          final estudiante = _estudiantes[index];
          return _construirTarjetaEstudiante(estudiante);
        },
      ),
    );
  }

  Widget _construirTarjetaEstudiante(Estudiante estudiante) {
    return Card(
      elevation: 3,
      margin: const EdgeInsets.symmetric(vertical: 10),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            Container(
              width: 70,
              height: 70,
              decoration: BoxDecoration(
                color: Colors.amber[100],
                shape: BoxShape.circle,
                border: Border.all(color: Colors.amber, width: 3),
              ),
              child: const Icon(Icons.person, size: 40, color: Colors.black54),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    estudiante.nombreCompleto.toUpperCase(),
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Identificador: ${estudiante.uuid}',
                    style: const TextStyle(fontSize: 13, color: Colors.black54),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    estudiante.cursoNombre.toUpperCase(),
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.black87),
                  ),
                ],
              ),
            ),
            Column(
              children: [
                ElevatedButton(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => EstudianteDetalleScreen(estudiante: estudiante),
                      ),
                    );
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.greenAccent[700], 
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                  ),
                  child: const Text('VER', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}