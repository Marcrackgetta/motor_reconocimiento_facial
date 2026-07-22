import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'dart:convert';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../config/api_config.dart';

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
  
  double _camLat = -2.128589;
  double _camLng = -79.931099;
  final MapController _mapController = MapController();

  @override
  void initState() {
    super.initState();
    _connectWebSocket();
  }

  void _connectWebSocket() {
    try {
      _channel = WebSocketChannel.connect(
        Uri.parse('${ApiConfig.wsUrl}/ws/dashboard'),
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
        final camInfo = message['camara_info'] ?? {};
        _cameraInfo = camInfo['curso_asignado'] ?? "General";
        
        if (camInfo['ubicacion'] != null) {
          if (camInfo['ubicacion']['latitude'] != null) {
            _camLat = (camInfo['ubicacion']['latitude'] as num).toDouble();
            _camLng = (camInfo['ubicacion']['longitude'] as num).toDouble();
          } else if (camInfo['ubicacion'] is List && camInfo['ubicacion'].length >= 2) {
             _camLat = (camInfo['ubicacion'][0] as num).toDouble();
             _camLng = (camInfo['ubicacion'][1] as num).toDouble();
          }
        }
        
        // Mover el mapa a la ubicación de la cámara si ya está listo
        try {
           _mapController.move(LatLng(_camLat, _camLng), 18);
        } catch (e) {}

        _latestData = {};
      } else if (message['type'] == 'DETECTION_UPDATED') {
        if (_activeSessionId.isEmpty ||
            _activeSessionId == message['session_id']) {
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
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: color,
              ),
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
          child: Text(
            "Los representantes no tienen acceso a la central de monitoreo.",
          ),
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
        title: Text(
          'HQ Central - ${widget.rol}',
          style: const TextStyle(color: Colors.white),
        ),
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
                Text(
                  _isConnected ? "EN VIVO" : "DESCONECTADO",
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
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
                          const Text(
                            "Cámara Activa (Transmisión IA)",
                            style: TextStyle(color: Colors.grey),
                          ),
                          Text(
                            _cameraInfo,
                            style: const TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (_activeSessionId.isNotEmpty)
                      Chip(
                        backgroundColor: intrusos > 0
                            ? Colors.red.shade100
                            : Colors.green.shade100,
                        label: Text(
                          intrusos > 0 ? "¡ALERTA INTRUSOS!" : "TODO EN ORDEN",
                          style: TextStyle(
                            color: intrusos > 0
                                ? Colors.red.shade900
                                : Colors.green.shade900,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                Expanded(
                  child: _buildStatCard(
                    "Presentes",
                    presentes,
                    Colors.green,
                    Icons.check_circle,
                  ),
                ),
                Expanded(
                  child: _buildStatCard(
                    "Ausentes",
                    ausentes,
                    Colors.purple,
                    Icons.watch_later,
                  ),
                ),
                Expanded(
                  child: _buildStatCard(
                    "Infiltrados",
                    intrusos,
                    Colors.red,
                    Icons.warning,
                  ),
                ),
                Expanded(
                  child: _buildStatCard(
                    "No Registrados",
                    desconocidos,
                    Colors.orange,
                    Icons.help,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Expanded(
              child: Row(
                children: [
                  // --- MAPA LEAFLET ---
                  Expanded(
                    flex: 2,
                    child: Card(
                      clipBehavior: Clip.antiAlias,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Stack(
                        children: [
                          FlutterMap(
                            mapController: _mapController,
                            options: MapOptions(
                              center: LatLng(_camLat, _camLng),
                              zoom: 18.0,
                            ),
                            children: [
                              TileLayer(
                                urlTemplate: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
                                subdomains: const ['a', 'b', 'c'],
                              ),
                              MarkerLayer(
                                markers: [
                                  Marker(
                                    point: LatLng(_camLat, _camLng),
                                    width: 40,
                                    height: 40,
                                    builder: (ctx) => Icon(
                                      Icons.location_on,
                                      color: _activeSessionId.isEmpty ? Colors.grey : (intrusos > 0 ? Colors.red : Colors.green),
                                      size: 40,
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                          Positioned(
                            top: 8,
                            left: 8,
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                              decoration: BoxDecoration(
                                color: Colors.white.withOpacity(0.9),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: const Text(
                                "Ubicación de Cámara",
                                style: TextStyle(fontWeight: FontWeight.bold),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  
                  // --- HISTORIAL DE INFILTRADOS ---
                  Expanded(
                    flex: 1,
                    child: Card(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(12.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              "🚨 Infiltrados (Tiempo Real)",
                              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                            ),
                            const SizedBox(height: 8),
                            Expanded(
                              child: listaIntrusos.isEmpty
                                  ? const Center(
                                      child: Text(
                                        "No se han detectado intrusos.",
                                        style: TextStyle(color: Colors.grey),
                                      ),
                                    )
                                  : ListView.builder(
                                      itemCount: listaIntrusos.length,
                                      itemBuilder: (context, index) {
                                        final intru = listaIntrusos[index];
                                        final nombre = intru['nombre'] ?? 'Desconocido';
                                        final duracion = intru['duracion_segundos'] ?? 0.0;
                                        return Card(
                                          color: Colors.red.shade50,
                                          margin: const EdgeInsets.symmetric(vertical: 4),
                                          child: ListTile(
                                            contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                            leading: const Icon(
                                              Icons.warning,
                                              color: Colors.red,
                                            ),
                                            title: Text(
                                              nombre,
                                              style: const TextStyle(
                                                fontWeight: FontWeight.bold,
                                                fontSize: 14,
                                              ),
                                            ),
                                            subtitle: Text(
                                              "Tiempo: ${(duracion as num).toStringAsFixed(1)}s",
                                              style: const TextStyle(fontSize: 12),
                                            ),
                                          ),
                                        );
                                      },
                                    ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
