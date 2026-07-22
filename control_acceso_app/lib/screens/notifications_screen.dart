import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import '../config/api_config.dart';
import '../services/websocket_service.dart';

class NotificationsScreen extends StatefulWidget {
  final String email;

  const NotificationsScreen({super.key, this.email = ''});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  List<dynamic> _notificaciones = [];
  bool _isLoading = true;
  String? _error;
  Timer? _timer;
  WebSocketService? _wsService;
  StreamSubscription? _wsSubscription;

  @override
  void initState() {
    super.initState();
    _fetchNotificaciones();
    _initWebSocket();
    // Temporizador de respaldo pasivo a 30 segundos
    _timer = Timer.periodic(const Duration(seconds: 30), (_) => _fetchNotificaciones());
  }

  void _initWebSocket() {
    if (widget.email.isEmpty) return;
    _wsService = WebSocketService(email: widget.email);
    _wsService!.connect();
    _wsSubscription = _wsService!.eventStream.listen((event) {
      if (mounted) {
        // Al recibir un nuevo evento en tiempo real, actualizar lista de notificaciones de inmediato
        _fetchNotificaciones();
      }
    });
  }

  Future<void> _fetchNotificaciones() async {
    try {
      final endpoint = widget.email.isNotEmpty
          ? '${ApiConfig.baseUrl}/notifications/me?email=${widget.email}'
          : '${ApiConfig.baseUrl}/alerts';

      final response = await http.get(Uri.parse(endpoint));
      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            _notificaciones = jsonDecode(response.body);
            _isLoading = false;
            _error = null;
          });
        }
      } else {
        if (mounted) {
          setState(() {
            _error = "Error al cargar notificaciones: ${response.statusCode}";
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
    _wsSubscription?.cancel();
    _wsService?.dispose();
    super.dispose();
  }

  Widget _getEventIcon(String tipo) {
    switch (tipo) {
      case 'ENTRADA':
        return const Icon(Icons.login, color: Colors.green);
      case 'SALIDA':
        return const Icon(Icons.logout, color: Colors.blue);
      case 'PRESENCIA':
      case 'PRESENCIA_NORMAL':
        return const Icon(Icons.check_circle, color: Colors.green);
      case 'CURSO_DIFERENTE':
        return const Icon(Icons.warning, color: Colors.orange);
      case 'PERMANENCIA_EXCESIVA_10_MIN':
      case 'INTRUSO_EXTERNO':
      case 'UNKNOWN_INTRUDER':
      case 'INTRUSO':
        return const Icon(Icons.error, color: Colors.red);
      default:
        return const Icon(Icons.notifications, color: Colors.blue);
    }
  }

  Color _getCardBorderColor(String tipo) {
    switch (tipo) {
      case 'PERMANENCIA_EXCESIVA_10_MIN':
      case 'INTRUSO_EXTERNO':
      case 'UNKNOWN_INTRUDER':
      case 'INTRUSO':
        return Colors.red.shade300;
      case 'CURSO_DIFERENTE':
        return Colors.orange.shade300;
      default:
        return Colors.blue.shade100;
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Notificaciones & Alertas',
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
            const Icon(Icons.error_outline, color: Colors.red, size: 50),
            const SizedBox(height: 10),
            Text(_error!, style: const TextStyle(color: Colors.red)),
            const SizedBox(height: 10),
            ElevatedButton(
              onPressed: _fetchNotificaciones,
              child: const Text("Reintentar"),
            ),
          ],
        ),
      );
    }

    if (_notificaciones.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.notifications_off_outlined, size: 80, color: Colors.grey.shade400),
            const SizedBox(height: 16),
            const Text(
              'No hay notificaciones ni alertas recientes.',
              style: TextStyle(fontSize: 16, color: Colors.grey),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _fetchNotificaciones,
      child: ListView.builder(
        padding: const EdgeInsets.all(12),
        itemCount: _notificaciones.length,
        itemBuilder: (context, index) {
          final data = _notificaciones[index];

          final nombre = data['nombre'] ?? 'Estudiante';
          final tipo = data['tipo_evento'] ?? data['tipo'] ?? 'EVENTO';
          final cursoOrigen = data['curso_origen'] ?? 'General';
          final cursoDetectado = data['curso_detectado'] ?? data['curso'] ?? 'General';
          final fecha = _formatDate(data['fecha_hora'] ?? data['fecha']);

          return Card(
            elevation: 3,
            margin: const EdgeInsets.symmetric(vertical: 8),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
              side: BorderSide(color: _getCardBorderColor(tipo), width: 1.5),
            ),
            child: ListTile(
              contentPadding: const EdgeInsets.all(16),
              leading: CircleAvatar(
                backgroundColor: _getCardBorderColor(tipo).withOpacity(0.2),
                child: _getEventIcon(tipo),
              ),
              title: Text(
                '$nombre - $tipo',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              subtitle: Padding(
                padding: const EdgeInsets.only(top: 8.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Origen: $cursoOrigen | Detectado en: $cursoDetectado'),
                    const SizedBox(height: 4),
                    Text('Fecha/Hora: $fecha', style: TextStyle(color: Colors.grey.shade700, fontSize: 12)),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
