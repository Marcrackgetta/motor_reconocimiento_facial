import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';

class RepresentanteScreen extends StatefulWidget {
  final String email;

  const RepresentanteScreen({super.key, required this.email});

  @override
  State<RepresentanteScreen> createState() => _RepresentanteScreenState();
}

class _RepresentanteScreenState extends State<RepresentanteScreen> {
  List<dynamic> _estudiantes = [];
  bool _isLoading = true;
  String? _error;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _fetchEstudiantes();
    _timer = Timer.periodic(
      const Duration(seconds: 5),
      (_) => _fetchEstudiantes(),
    );
  }

  Future<void> _fetchEstudiantes() async {
    try {
      final response = await http.get(
        Uri.parse('http://127.0.0.1:8000/students/me?email=${widget.email}'),
      );
      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            _estudiantes = jsonDecode(response.body);
            _isLoading = false;
            _error = null;
          });
        }
      } else {
        if (mounted) {
          setState(() {
            _error = "Error al cargar datos: ${response.statusCode}";
            _isLoading = false;
          });
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = "Error de conexión: $e";
          _isLoading = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Widget _buildStatusIcon(String estado) {
    switch (estado) {
      case 'DENTRO_DE_LA_INSTITUCION':
      case 'PRESENTE':
        return const Icon(Icons.check_circle, color: Colors.green, size: 30);
      case 'FUERA_DE_LA_INSTITUCION':
        return const Icon(Icons.exit_to_app, color: Colors.grey, size: 30);
      case 'CURSO_DIFERENTE':
        return const Icon(Icons.warning, color: Colors.orange, size: 30);
      default:
        return const Icon(Icons.help_outline, color: Colors.grey, size: 30);
    }
  }

  String _formatDate(String? isoString) {
    if (isoString == null || isoString.isEmpty) return 'Desconocida';
    try {
      final dt = DateTime.parse(isoString);
      return "${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')} - ${dt.day}/${dt.month}/${dt.year}";
    } catch (e) {
      return isoString;
    }
  }

  Future<void> _showHistory(String studentId, String studentName) async {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );

    try {
      final response = await http.get(
        Uri.parse('http://127.0.0.1:8000/students/$studentId/history'),
      );
      Navigator.of(context).pop(); // Close loading

      if (response.statusCode == 200) {
        final List<dynamic> history = jsonDecode(response.body);
        _buildHistoryDialog(history, studentName);
      } else {
        _showErrorDialog("No se pudo cargar el historial.");
      }
    } catch (e) {
      Navigator.of(context).pop();
      _showErrorDialog("Error de red.");
    }
  }

  void _showErrorDialog(String msg) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("Error"),
        content: Text(msg),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("OK"),
          ),
        ],
      ),
    );
  }

  void _buildHistoryDialog(List<dynamic> history, String studentName) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text("Historial de $studentName"),
        content: SizedBox(
          width: double.maxFinite,
          child: history.isEmpty
              ? const Text("No hay eventos registrados.")
              : ListView.builder(
                  shrinkWrap: true,
                  itemCount: history.length,
                  itemBuilder: (context, index) {
                    final item = history[index];
                    return ListTile(
                      leading: const Icon(Icons.history),
                      title: Text(item['tipo_evento'] ?? 'Evento'),
                      subtitle: Text(
                        "${item['camara_curso']} - ${_formatDate(item['fecha_hora'])}",
                      ),
                    );
                  },
                ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("Cerrar"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Mis Representados',
          style: TextStyle(color: Colors.white),
        ),
        backgroundColor: Colors.blue.shade900,
        elevation: 0,
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error, color: Colors.red, size: 50),
            const SizedBox(height: 10),
            Text(_error!, style: const TextStyle(color: Colors.red)),
            ElevatedButton(
              onPressed: _fetchEstudiantes,
              child: const Text("Reintentar"),
            ),
          ],
        ),
      );
    }

    if (_estudiantes.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.face, size: 80, color: Colors.blue.shade200),
            const SizedBox(height: 16),
            const Text(
              'No hay estudiantes asignados a tu cuenta.',
              style: TextStyle(fontSize: 18, color: Colors.grey),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: _estudiantes.length,
      itemBuilder: (context, index) {
        final est = _estudiantes[index];
        final nombre = est['nombre'] ?? 'Desconocido';
        final curso = est['curso_origen'] ?? 'Desconocido';
        final estado = est['estado_actual'] ?? 'DESCONOCIDO';
        final ultimaDeteccion = _formatDate(est['ultima_deteccion']);
        final camara = est['curso_detectado'] ?? 'Ninguna';

        return Card(
          elevation: 4,
          margin: const EdgeInsets.symmetric(vertical: 8),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(15),
          ),
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    CircleAvatar(
                      radius: 30,
                      backgroundColor: Colors.blue.shade100,
                      child: const Icon(
                        Icons.person,
                        size: 40,
                        color: Colors.blue,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            nombre,
                            style: const TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          Text(
                            curso,
                            style: TextStyle(
                              fontSize: 16,
                              color: Colors.grey.shade700,
                            ),
                          ),
                        ],
                      ),
                    ),
                    _buildStatusIcon(estado),
                  ],
                ),
                const Divider(height: 30, thickness: 1),
                Row(
                  children: [
                    const Icon(
                      Icons.info_outline,
                      size: 20,
                      color: Colors.grey,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Estado: ${estado.replaceAll('_', ' ')}',
                        style: const TextStyle(
                          fontWeight: FontWeight.w500,
                          fontSize: 15,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    const Icon(Icons.location_on, size: 20, color: Colors.grey),
                    const SizedBox(width: 8),
                    Text('Última cámara: $camara'),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        const Icon(
                          Icons.access_time,
                          size: 20,
                          color: Colors.grey,
                        ),
                        const SizedBox(width: 8),
                        Text('Visto a las: $ultimaDeteccion'),
                      ],
                    ),
                    ElevatedButton.icon(
                      onPressed: () {
                        // Assuming student_id is structured like this or passed from backend
                        final sId =
                            est['id'] ??
                            "${curso}_${nombre}".replaceAll(' ', '_');
                        _showHistory(sId, nombre);
                      },
                      icon: const Icon(Icons.history, size: 18),
                      label: const Text("Historial"),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 8,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
