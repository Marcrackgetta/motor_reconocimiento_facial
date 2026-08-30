import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_service.dart';
import '../models/estudiante.dart';

class EnviarNotificacionScreen extends StatefulWidget {
  const EnviarNotificacionScreen({super.key});

  @override
  State<EnviarNotificacionScreen> createState() => _EnviarNotificacionScreenState();
}

class _EnviarNotificacionScreenState extends State<EnviarNotificacionScreen> {
  final ApiService _apiService = ApiService();
  final _tituloController = TextEditingController();
  final _mensajeController = TextEditingController();

  String _rolUsuario = 'REPRESENTANTE';
  String _tipoSeleccionado = 'JUSTIFICACION';
  String? _estudianteSeleccionadoUuid;
  
  List<Estudiante> _estudiantes = [];
  bool _isLoading = true;
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    _cargarContexto();
  }

  Future<void> _cargarContexto() async {
    final prefs = await SharedPreferences.getInstance();
    final rol = prefs.getString('rol')?.toUpperCase() ?? 'REPRESENTANTE';
    
    try {
      final estudiantes = await _apiService.fetchEstudiantes();
      setState(() {
        _rolUsuario = rol;
        _estudiantes = estudiantes;
        // Ajustamos el tipo por defecto según el rol
        if (rol == 'INSPECTOR') _tipoSeleccionado = 'NOVEDAD';
        if (rol == 'ADMINISTRADOR') _tipoSeleccionado = 'COMUNICADO';
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Error al cargar datos.')));
      }
    }
  }

  void _enviar() async {
    if (_tituloController.text.isEmpty || _mensajeController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Por favor, completa el título y el mensaje.')));
      return;
    }

    setState(() => _isSubmitting = true);

    try {
      // El backend intercepta a los representantes, así que enviamos una lista vacía de destinatarios en ese caso.
      // Si fuéramos a implementar selección manual de destinatarios para el admin, se pasarían aquí.
      await _apiService.enviarNotificacion(
        _tituloController.text.trim(),
        _mensajeController.text.trim(),
        _tipoSeleccionado,
        _estudianteSeleccionadoUuid,
        [], 
      );
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Notificación enviada correctamente.')));
        Navigator.pop(context);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString().replaceAll('Exception: ', ''))));
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    // Definimos qué opciones de tipo mostrar según el rol
    List<String> opcionesTipo = [];
    if (_rolUsuario == 'REPRESENTANTE') {
      opcionesTipo = ['JUSTIFICACION'];
    } else if (_rolUsuario == 'INSPECTOR') {
      opcionesTipo = ['NOVEDAD', 'AVISO'];
    } else {
      opcionesTipo = ['COMUNICADO', 'AVISO', 'URGENTE'];
    }

    return Scaffold(
      backgroundColor: Colors.grey[50],
      appBar: AppBar(
        title: const Text('Redactar Mensaje', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600)),
        backgroundColor: Colors.blueGrey[800],
        iconTheme: const IconThemeData(color: Colors.white),
        elevation: 0,
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 600), // Diseño compacto de formulario
          child: _isLoading
              ? const Center(child: CircularProgressIndicator())
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(32),
                  child: Card(
                    elevation: 2,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                    child: Padding(
                      padding: const EdgeInsets.all(32.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Información General', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.black54)),
                          const SizedBox(height: 16),
                          
                          // Tipo de Notificación
                          DropdownButtonFormField<String>(
                            initialValue: _tipoSeleccionado,
                            decoration: _decoracionCampo('Tipo de Mensaje', Icons.label_outline),
                            items: opcionesTipo.map((t) => DropdownMenuItem(value: t, child: Text(t))).toList(),
                            onChanged: _rolUsuario == 'REPRESENTANTE' ? null : (val) => setState(() => _tipoSeleccionado = val!),
                          ),
                          const SizedBox(height: 16),

                          // Selector de Estudiante (Obligatorio para representantes)
                          DropdownButtonFormField<String?>(
                            initialValue: _estudianteSeleccionadoUuid,
                            decoration: _decoracionCampo('Estudiante Relacionado (Opcional)', Icons.face),
                            items: [
                              const DropdownMenuItem(value: null, child: Text('Ninguno (Aviso General)')),
                              ..._estudiantes.map((e) => DropdownMenuItem(value: e.uuid, child: Text(e.nombreCompleto)))
                            ],
                            onChanged: (val) => setState(() => _estudianteSeleccionadoUuid = val),
                          ),
                          
                          const Padding(
                            padding: EdgeInsets.symmetric(vertical: 24),
                            child: Divider(),
                          ),
                          
                          const Text('Contenido del Mensaje', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.black54)),
                          const SizedBox(height: 16),
                          
                          // Título
                          TextField(
                            controller: _tituloController,
                            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                            decoration: _decoracionCampo('Asunto / Título', Icons.short_text),
                          ),
                          const SizedBox(height: 16),
                          
                          // Cuerpo del mensaje
                          TextField(
                            controller: _mensajeController,
                            maxLines: 5,
                            style: const TextStyle(fontSize: 14),
                            decoration: _decoracionCampo('Escribe tu mensaje aquí...', Icons.notes),
                          ),
                          
                          const SizedBox(height: 32),
                          
                          // Botón Enviar
                          SizedBox(
                            width: double.infinity,
                            height: 48,
                            child: ElevatedButton.icon(
                              onPressed: _isSubmitting ? null : _enviar,
                              icon: _isSubmitting ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : const Icon(Icons.send),
                              label: const Text('ENVIAR NOTIFICACIÓN', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.0)),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.blueGrey[800],
                                foregroundColor: Colors.white,
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                              ),
                            ),
                          )
                        ],
                      ),
                    ),
                  ),
                ),
        ),
      ),
    );
  }

  InputDecoration _decoracionCampo(String etiqueta, IconData icono) {
    return InputDecoration(
      labelText: etiqueta,
      labelStyle: const TextStyle(fontSize: 14),
      prefixIcon: Icon(icono, color: Colors.black54, size: 20),
      filled: true,
      fillColor: Colors.grey[100],
      contentPadding: const EdgeInsets.symmetric(vertical: 16, horizontal: 16),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Colors.blueGrey, width: 1.5)),
    );
  }
}