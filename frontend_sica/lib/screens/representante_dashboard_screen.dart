import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/estudiante.dart';
import 'estudiante_detalle_screen.dart';

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

  @override
  void initState() {
    super.initState();
    _cargarEstudiantes();
  }

  Future<void> _cargarEstudiantes() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      // Consumimos los estudiantes reales desde la API
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: const Text('SICA', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 24, letterSpacing: 1.2)),
        backgroundColor: Colors.amber[400], // Color amarillo basado en la referencia
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.menu),
          onPressed: () {}, // Menú lateral futuro
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _cargarEstudiantes,
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
      // Botón flotante extendido basado en la referencia "Agregar Alumno"
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {},
        backgroundColor: Colors.amber[400],
        icon: const Icon(Icons.person_add_alt_1, color: Colors.black87),
        label: const Text('Agregar Alumno', style: TextStyle(color: Colors.black87, fontWeight: FontWeight.bold)),
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
    );
  }

  // 1. DATOS DEL REPRESENTANTE
  Widget _construirEncabezadoRepresentante() {
    return Container(
      width: double.infinity,
      color: Colors.white,
      padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 16),
      margin: const EdgeInsets.only(bottom: 10),
      child: const Column(
        children: [
          Text('Bienvenido', style: TextStyle(fontSize: 16, color: Colors.black54)),
          SizedBox(height: 4),
          Text(
            'ELSA MARINA AGUIRRE ALARCÓN', 
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
            textAlign: TextAlign.center,
          ),
          SizedBox(height: 4),
          Text('Cédula 1202976328', style: TextStyle(fontSize: 16, color: Colors.black54)),
        ],
      ),
    );
  }

  // 2. LISTA DE ESTUDIANTES
  Widget _construirListaEstudiantes() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage.isNotEmpty) {
      return Center(child: Text(_errorMessage, textAlign: TextAlign.center));
    }

    if (_estudiantes.isEmpty) {
      return const Center(child: Text('No tiene estudiantes registrados.'));
    }

    return RefreshIndicator(
      onRefresh: _cargarEstudiantes,
      child: ListView.builder(
        padding: const EdgeInsets.only(left: 16, right: 16, bottom: 80), // bottom padding para no tapar el FAB
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
            // Avatar del estudiante
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
            
            // Datos del Estudiante
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
            
            // Botón VER
            Column(
              children: [
                ElevatedButton(
                  onPressed: () {
                    // Navegamos al detalle y le pasamos el estudiante completo
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => EstudianteDetalleScreen(estudiante: estudiante),
                      ),
                    );
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.greenAccent[700], // Verde vibrante
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