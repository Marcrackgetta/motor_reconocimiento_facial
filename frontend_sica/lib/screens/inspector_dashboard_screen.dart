import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../models/curso.dart';
import 'login_screen.dart';
import 'inspector_cursos_screen.dart';

class InspectorDashboardScreen extends StatefulWidget {
  const InspectorDashboardScreen({super.key});

  @override
  State<InspectorDashboardScreen> createState() => _InspectorDashboardScreenState();
}

class _InspectorDashboardScreenState extends State<InspectorDashboardScreen> {
  final ApiService _apiService = ApiService();
  String _nombreUsuario = 'Cargando...';
  bool _isLoading = true;
  String _errorMessage = '';
  
  // Usamos un mapa para agrupar los cursos por jornada
  Map<String, List<Curso>> _jornadasCursos = {};

  @override
  void initState() {
    super.initState();
    _cargarDatos();
  }

  Future<void> _cargarDatos() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      final prefs = await SharedPreferences.getInstance();
      final nombre = prefs.getString('nombre') ?? 'Inspector';
      
      // Obtenemos los cursos que le pertenecen al inspector (El backend filtra esto por el token)
      final cursos = await _apiService.fetchCursos();
      
      // Agrupamos los cursos por jornada
      Map<String, List<Curso>> jornadasAgrupadas = {};
      for (var curso in cursos) {
        if (!jornadasAgrupadas.containsKey(curso.jornada)) {
          jornadasAgrupadas[curso.jornada] = [];
        }
        jornadasAgrupadas[curso.jornada]!.add(curso);
      }

      setState(() {
        _nombreUsuario = nombre;
        _jornadasCursos = jornadasAgrupadas;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = "Error al cargar los datos: ${e.toString().replaceAll('Exception: ', '')}";
        _isLoading = false;
      });
    }
  }

  void _cerrarSesion() async {
    await AuthService().logout();
    if (mounted) {
      Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const LoginScreen()));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: const Text('SICA - Inspector', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
        backgroundColor: Colors.teal[600],
        elevation: 0,
        actions: [
          IconButton(icon: const Icon(Icons.refresh, color: Colors.white), onPressed: _cargarDatos),
          IconButton(icon: const Icon(Icons.logout, color: Colors.white), onPressed: _cerrarSesion),
        ],
      ),
      body: Column(
        children: [
          _construirEncabezado(),
          Expanded(child: _construirListaJornadas()),
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
          const Text('Panel de Inspección', style: TextStyle(fontSize: 16, color: Colors.black54)),
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

  Widget _construirListaJornadas() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage.isNotEmpty) {
      return Center(child: Text(_errorMessage, style: const TextStyle(color: Colors.red)));
    }

    if (_jornadasCursos.isEmpty) {
      return const Center(child: Text('No tiene jornadas ni cursos asignados actualmente.'));
    }

    final jornadas = _jornadasCursos.keys.toList();

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: jornadas.length,
      itemBuilder: (context, index) {
        final jornadaNombre = jornadas[index];
        final cursosDeJornada = _jornadasCursos[jornadaNombre]!;
        
        return Card(
          elevation: 4,
          margin: const EdgeInsets.only(bottom: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      jornadaNombre == 'Matutina' ? Icons.wb_sunny : (jornadaNombre == 'Vespertina' ? Icons.wb_twilight : Icons.nightlight_round),
                      size: 40,
                      color: Colors.teal[400],
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('JORNADA ${jornadaNombre.toUpperCase()}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                          const SizedBox(height: 4),
                          Text('${cursosDeJornada.length} cursos asignados', style: const TextStyle(color: Colors.black54)),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => InspectorCursosScreen(
                            jornada: jornadaNombre,
                            cursos: cursosDeJornada,
                          ),
                        ),
                      );
                    },
                    icon: const Icon(Icons.folder_open),
                    label: const Text('VER CURSOS', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.0)),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.teal[600],
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                  ),
                )
              ],
            ),
          ),
        );
      },
    );
  }
}