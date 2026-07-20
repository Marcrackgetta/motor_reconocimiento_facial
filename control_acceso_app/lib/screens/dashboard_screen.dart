import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'dart:convert';

class DashboardScreen extends StatefulWidget {
  final String rol;
  final String email;

  const DashboardScreen({super.key, required this.rol, required this.email});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  WebSocketChannel? _channel;
  bool _isConnected = false;
  Map<String, dynamic> _latestData = {};
  String _activeSessionId = "";
  String _cameraInfo = "Esperando conexión...";

  @override
  void initState() {
    super.initState();
    _connectWebSocket();
  }

  void _connectWebSocket() {
    try {
      _channel = WebSocketChannel.connect(
        Uri.parse('ws://127.0.0.1:8000/ws/dashboard'),
      );
      
      _channel!.stream.listen(
        (message) {
          final data = jsonDecode(message);
          _handleWebSocketMessage(data);
        },
        onDone: () {
          if (mounted) {
            setState(() => _isConnected = false);
            // Intentar reconectar después de un rato
            Future.delayed(const Duration(seconds: 3), _connectWebSocket);
          }
        },
        onError: (error) {
          debugPrint("WebSocket Error: $error");
        },
      );
      setState(() => _isConnected = true);
    } catch (e) {
      debugPrint("Error conectando WS: $e");
    }
  }

  void _handleWebSocketMessage(Map<String, dynamic> message) {
    if (!mounted) return;
    
    setState(() {
      if (message['type'] == 'SESSION_STARTED') {
        _activeSessionId = message['session_id'];
        _cameraInfo = message['camara_info']?['curso_asignado'] ?? "General";
        _latestData = {};
      } else if (message['type'] == 'DETECTION_UPDATED') {
        if (_activeSessionId.isEmpty || _activeSessionId == message['session_id']) {
           _activeSessionId = message['session_id'];
           _latestData = message['data'] ?? {};
        }
      } else if (message['type'] == 'SESSION_ENDED') {
        if (_activeSessionId == message['session_id']) {
          _cameraInfo = "Sesión Finalizada";
        }
      }
    });
  }

  @override
  void dispose() {
    _channel?.sink.close();
    super.dispose();
  }

  Widget _buildStatCard(String title, int count, Color color, IconData icon) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            Icon(icon, color: color, size: 32),
            const SizedBox(height: 8),
            Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
            Text(
              count.toString(),
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: color),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (widget.rol == 'Representante') {
      return Scaffold(
        appBar: AppBar(title: const Text("Acceso Restringido")),
        body: const Center(
          child: Text("Los representantes no tienen acceso a la central de monitoreo."),
        ),
      );
    }

    int presentes = _latestData['total_presentes'] ?? 0;
    int ausentes = _latestData['total_ausentes'] ?? 0;
    int intrusos = _latestData['total_intrusos'] ?? 0;
    int desconocidos = _latestData['total_desconocidos'] ?? 0;

    List<dynamic> listaIntrusos = _latestData['lista_intrusos'] ?? [];

    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: Text('HQ Central - ${widget.rol}', style: const TextStyle(color: Colors.white)),
        backgroundColor: Colors.blue.shade900,
        actions: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Row(
              children: [
                Icon(
                  _isConnected ? Icons.cloud_done : Icons.cloud_off,
                  color: _isConnected ? Colors.greenAccent : Colors.redAccent,
                ),
                const SizedBox(width: 8),
                Text(_isConnected ? "EN VIVO" : "DESCONECTADO", 
                     style: const TextStyle(fontWeight: FontWeight.bold)),
              ],
            ),
          )
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              color: Colors.white,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Row(
                  children: [
                    const Icon(Icons.videocam, color: Colors.blue, size: 30),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text("Cámara Activa (Transmisión IA)", style: TextStyle(color: Colors.grey)),
                          Text(_cameraInfo, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ),
                    if (_activeSessionId.isNotEmpty)
                      Chip(
                        backgroundColor: intrusos > 0 ? Colors.red.shade100 : Colors.green.shade100,
                        label: Text(
                          intrusos > 0 ? "¡ALERTA INTRUSOS!" : "TODO EN ORDEN",
                          style: TextStyle(color: intrusos > 0 ? Colors.red.shade900 : Colors.green.shade900, fontWeight: FontWeight.bold),
                        ),
                      )
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                Expanded(child: _buildStatCard("Presentes", presentes, Colors.green, Icons.check_circle)),
                Expanded(child: _buildStatCard("Ausentes", ausentes, Colors.purple, Icons.watch_later)),
                Expanded(child: _buildStatCard("Infiltrados", intrusos, Colors.red, Icons.warning)),
                Expanded(child: _buildStatCard("No Registrados", desconocidos, Colors.orange, Icons.help)),
              ],
            ),
            const SizedBox(height: 16),
            const Text("🚨 Historial de Infiltrados (Tiempo Real)", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Expanded(
              child: listaIntrusos.isEmpty
                  ? const Center(child: Text("No se han detectado intrusos en esta sesión.", style: TextStyle(color: Colors.grey)))
                  : ListView.builder(
                      itemCount: listaIntrusos.length,
                      itemBuilder: (context, index) {
                        final intru = listaIntrusos[index];
                        final nombre = intru['nombre'] ?? 'Desconocido';
                        final duracion = intru['duracion_segundos'] ?? 0.0;
                        return Card(
                          color: Colors.red.shade50,
                          child: ListTile(
                            leading: const Icon(Icons.warning, color: Colors.red),
                            title: Text(nombre, style: const TextStyle(fontWeight: FontWeight.bold)),
                            subtitle: Text("Permanencia en área: ${(duracion as num).toStringAsFixed(1)}s"),
                            trailing: const Text("INFILTRADO", style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
