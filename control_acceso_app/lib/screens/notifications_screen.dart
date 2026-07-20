import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  List<dynamic> _alertas = [];
  bool _isLoading = true;
  String? _error;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _fetchAlertas();
    // Simular tiempo real con polling corto (o usar WebSockets)
    _timer = Timer.periodic(const Duration(seconds: 5), (_) => _fetchAlertas());
  }

  Future<void> _fetchAlertas() async {
    try {
      final response = await http.get(Uri.parse('http://127.0.0.1:8000/alerts'));
      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            _alertas = jsonDecode(response.body);
            _isLoading = false;
            _error = null;
          });
        }
      } else {
        if (mounted) {
          setState(() {
            _error = "Error al cargar alertas: ${response.statusCode}";
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Notificaciones de Seguridad',
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
            ElevatedButton(onPressed: _fetchAlertas, child: const Text("Reintentar"))
          ],
        ),
      );
    }

    if (_alertas.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.security, size: 80, color: Colors.green.shade300),
            const SizedBox(height: 16),
            const Text(
              'No hay alertas de seguridad.',
              style: TextStyle(fontSize: 18, color: Colors.grey),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: _alertas.length,
      itemBuilder: (context, index) {
        final data = _alertas[index];

        final fecha = data['fecha'] ?? '';
        final hora = data['hora_inicio'] ?? '';
        final curso = data['curso'] ?? 'General';
        final intrusos = data['total_intrusos'] ?? 0;
        final desconocidos = data['total_desconocidos'] ?? 0;

        return Card(
          elevation: 3,
          margin: const EdgeInsets.symmetric(vertical: 8),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(color: Colors.red.shade100, width: 1),
          ),
          child: ListTile(
            contentPadding: const EdgeInsets.all(16),
            leading: CircleAvatar(
              backgroundColor: Colors.red.shade100,
              child: const Icon(
                Icons.warning_amber_rounded,
                color: Colors.red,
              ),
            ),
            title: Text(
              'Alerta en $curso',
              style: const TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 16,
              ),
            ),
            subtitle: Padding(
              padding: const EdgeInsets.only(top: 8.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Fecha: $fecha - $hora'),
                  const SizedBox(height: 4),
                  if (intrusos > 0)
                    Text(
                      '🚨 Infiltrados detectados: $intrusos',
                      style: TextStyle(
                        color: Colors.red.shade700,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  if (desconocidos > 0)
                    Text(
                      '❓ Rostros no registrados: $desconocidos',
                      style: TextStyle(
                        color: Colors.orange.shade700,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                ],
              ),
            ),
            isThreeLine: true,
          ),
        );
      },
    );
  }
}
