import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../config/api_config.dart';

class WebSocketService {
  final String email;
  WebSocketChannel? _channel;
  final StreamController<Map<String, dynamic>> _eventController =
      StreamController<Map<String, dynamic>>.broadcast();

  bool _isConnecting = false;
  bool _isDisposed = false;
  Timer? _reconnectTimer;

  WebSocketService({required this.email});

  Stream<Map<String, dynamic>> get eventStream => _eventController.stream;

  void connect() {
    if (_isConnecting || _isDisposed) return;
    _isConnecting = true;

    try {
      final wsUri = Uri.parse('${ApiConfig.wsUrl}/ws/live?email=$email');
      debugPrint('Conectando a WebSocket: $wsUri');
      
      _channel = WebSocketChannel.connect(wsUri);
      _isConnecting = false;

      _channel!.stream.listen(
        (message) {
          try {
            final Map<String, dynamic> data = jsonDecode(message);
            _eventController.add(data);
          } catch (e) {
            debugPrint('Error parseando mensaje WebSocket: $e');
          }
        },
        onError: (error) {
          debugPrint('Error en WebSocket: $error');
          _scheduleReconnect();
        },
        onDone: () {
          debugPrint('Conexión WebSocket cerrada.');
          _scheduleReconnect();
        },
      );
    } catch (e) {
      debugPrint('Excepción al conectar WebSocket: $e');
      _isConnecting = false;
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (_isDisposed) return;
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 3), () {
      if (!_isDisposed) {
        connect();
      }
    });
  }

  void dispose() {
    _isDisposed = true;
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _eventController.close();
  }
}
