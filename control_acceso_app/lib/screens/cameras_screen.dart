import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class CamerasScreen extends StatefulWidget {
  const CamerasScreen({super.key});

  @override
  State<CamerasScreen> createState() => _CamerasScreenState();
}

class _CamerasScreenState extends State<CamerasScreen> {
  late final WebViewController _controller;
  final TextEditingController _ipController = TextEditingController(text: '127.0.0.1');
  
  List<String> _cameras = ["Vista General (Grid)"];
  String? _selectedCamera = "Vista General (Grid)";
  bool _isLoadingCameras = false;

  @override
  void initState() {
    super.initState();
    _controller = WebViewController();
    
    if (!kIsWeb) {
      try {
        _controller.setJavaScriptMode(JavaScriptMode.unrestricted);
        _controller.setBackgroundColor(Colors.black);
      } catch (_) {}
    }
    
    _controller.loadHtmlString(_getHtmlString('127.0.0.1'));
    _fetchCameras('127.0.0.1');
  }

  Future<void> _fetchCameras(String ip) async {
    setState(() {
      _isLoadingCameras = true;
    });
    try {
      final response = await http.get(Uri.parse('http://$ip:5000/cameras_info'));
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        setState(() {
          _cameras = ["Vista General (Grid)"];
          _cameras.addAll(data.cast<String>());
          _selectedCamera = _cameras.first;
        });
      }
    } catch (e) {
      debugPrint("Error obteniendo cámaras: $e");
      // Mantenemos al menos la opción por defecto
      setState(() {
        _cameras = ["Vista General (Grid)"];
        _selectedCamera = _cameras.first;
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoadingCameras = false;
        });
      }
    }
  }

  Future<void> _changeCamera(String? selected) async {
    if (selected == null) return;
    setState(() {
      _selectedCamera = selected;
    });
    
    String ip = _ipController.text.trim();
    if (ip.isEmpty) ip = '127.0.0.1';

    int idx = _cameras.indexOf(selected) - 1; // -1 porque la primera es Grid
    String target = idx == -1 ? "grid" : idx.toString();

    try {
      await http.get(Uri.parse('http://$ip:5000/set_camera/$target'));
    } catch (e) {
      debugPrint("Error cambiando de cámara: $e");
    }
  }

  String _getHtmlString(String ip) {
    return '''
      <!DOCTYPE html>
      <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
          body { margin: 0; padding: 0; background-color: black; display: flex; justify-content: center; align-items: center; height: 100vh; overflow: hidden; }
          img { max-width: 100%; max-height: 100%; object-fit: contain; }
        </style>
      </head>
      <body>
        <img src="http://$ip:5000/video_feed" alt="No se pudo conectar a la cámara" onerror="this.alt='Error conectando a $ip:5000';"/>
      </body>
      </html>
    ''';
  }

  void _updateStream() {
    String ip = _ipController.text.trim();
    if (ip.isEmpty) ip = '127.0.0.1';
    _controller.loadHtmlString(_getHtmlString(ip));
    _fetchCameras(ip);
  }

  @override
  void dispose() {
    _ipController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Cámaras en Vivo', style: TextStyle(color: Colors.white)),
        backgroundColor: Colors.blue.shade900,
        elevation: 0,
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Row(
              children: [
                Expanded(
                  flex: 3,
                  child: TextField(
                    controller: _ipController,
                    decoration: const InputDecoration(
                      labelText: 'IP Servidor (Ej: 127.0.0.1)',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    keyboardType: TextInputType.url,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  flex: 5,
                  child: _isLoadingCameras 
                    ? const Center(child: CircularProgressIndicator())
                    : DropdownButton<String>(
                        isExpanded: true,
                        value: _selectedCamera,
                        items: _cameras.map((cam) {
                          return DropdownMenuItem(
                            value: cam,
                            child: Text(cam, overflow: TextOverflow.ellipsis),
                          );
                        }).toList(),
                        onChanged: _changeCamera,
                      ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  onPressed: _updateStream,
                  icon: const Icon(Icons.refresh),
                  color: Colors.blue.shade900,
                  tooltip: 'Refrescar Conexión',
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 12),
            color: Colors.yellow.shade100,
            width: double.infinity,
            child: const Text(
              'Selecciona la cámara que deseas monitorear. Las cámaras físicas (USB) se administran desde Python.',
              style: TextStyle(fontSize: 12, color: Colors.black87),
              textAlign: TextAlign.center,
            ),
          ),
          Expanded(child: WebViewWidget(controller: _controller)),
        ],
      ),
    );
  }
}
