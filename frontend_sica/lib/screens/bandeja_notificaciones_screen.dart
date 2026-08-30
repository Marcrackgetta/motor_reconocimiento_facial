import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/notificacion.dart';
import 'enviar_notificacion_screen.dart'; // Importamos la pantalla de envío

class BandejaNotificacionesScreen extends StatefulWidget {
  const BandejaNotificacionesScreen({super.key});

  @override
  State<BandejaNotificacionesScreen> createState() => _BandejaNotificacionesScreenState();
}

class _BandejaNotificacionesScreenState extends State<BandejaNotificacionesScreen> {
  final ApiService _apiService = ApiService();
  List<NotificacionUsuario> _notificaciones = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _cargarNotificaciones();
  }

  Future<void> _cargarNotificaciones() async {
    setState(() => _isLoading = true);
    try {
      final notifs = await _apiService.fetchMisNotificaciones();
      setState(() {
        _notificaciones = notifs;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Error al cargar notificaciones')));
    }
  }

  void _abrirNotificacion(NotificacionUsuario notif) async {
    // Si no está leída, avisamos al backend en segundo plano
    if (!notif.leida) {
      _apiService.marcarNotificacionLeida(notif.id).then((_) {
        _cargarNotificaciones(); // Recargamos para quitar la negrita visualmente
      });
    }

    // Mostramos el contenido en un Modal elegante
    showDialog(
      context: context,
      builder: (context) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 500),
          child: Padding(
            padding: const EdgeInsets.all(32.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.mail_outline, color: Colors.blueGrey[600], size: 28),
                    const SizedBox(width: 12),
                    Expanded(child: Text(notif.titulo, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold))),
                  ],
                ),
                const Padding(padding: EdgeInsets.symmetric(vertical: 16), child: Divider()),
                Text('De: ${notif.emisorNombre}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                Text('Fecha: ${notif.fechaCreacion.substring(0, 16).replaceAll('T', ' ')}', style: const TextStyle(color: Colors.black54, fontSize: 12)),
                const SizedBox(height: 24),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(color: Colors.grey[50], borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.grey[200]!)),
                  child: Text(notif.mensaje, style: const TextStyle(fontSize: 15, height: 1.5, color: Colors.black87)),
                ),
                const SizedBox(height: 32),
                SizedBox(
                  width: double.infinity,
                  height: 44,
                  child: ElevatedButton(
                    onPressed: () => Navigator.pop(context),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blueGrey[800],
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    child: const Text('Cerrar', style: TextStyle(fontWeight: FontWeight.bold)),
                  ),
                )
              ],
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[50],
      appBar: AppBar(
        title: const Text('Centro de Notificaciones', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600)),
        backgroundColor: Colors.blueGrey[800],
        iconTheme: const IconThemeData(color: Colors.white),
        elevation: 0,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _cargarNotificaciones),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 800),
          child: _isLoading
              ? const Center(child: CircularProgressIndicator())
              : _notificaciones.isEmpty
                  ? const Center(child: Text('No tienes notificaciones recientes.', style: TextStyle(color: Colors.black54)))
                  : ListView.builder(
                      padding: const EdgeInsets.all(24),
                      itemCount: _notificaciones.length,
                      itemBuilder: (context, index) {
                        final notif = _notificaciones[index];
                        final bool esNueva = !notif.leida;

                        return Card(
                          elevation: esNueva ? 2 : 0.5,
                          color: esNueva ? Colors.white : Colors.grey[100],
                          margin: const EdgeInsets.only(bottom: 12),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                            side: BorderSide(color: esNueva ? Colors.blueGrey[200]! : Colors.transparent),
                          ),
                          child: ListTile(
                            contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                            leading: CircleAvatar(
                              backgroundColor: esNueva ? Colors.blueGrey[100] : Colors.grey[200],
                              child: Icon(esNueva ? Icons.mark_email_unread_rounded : Icons.drafts_outlined, color: esNueva ? Colors.blueGrey[800] : Colors.grey[500]),
                            ),
                            title: Text(
                              notif.titulo,
                              style: TextStyle(fontWeight: esNueva ? FontWeight.bold : FontWeight.w500, fontSize: 15, color: esNueva ? Colors.black87 : Colors.black54),
                            ),
                            subtitle: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const SizedBox(height: 4),
                                Text(notif.mensaje, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 13, color: Colors.grey[600])),
                                const SizedBox(height: 8),
                                Text(notif.fechaCreacion.substring(0, 16).replaceAll('T', ' '), style: const TextStyle(fontSize: 11, color: Colors.grey)),
                              ],
                            ),
                            onTap: () => _abrirNotificacion(notif),
                          ),
                        );
                      },
                    ),
        ),
      ),
      // NUEVO: Botón para enviar notificaciones / justificaciones
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (context) => const EnviarNotificacionScreen()),
          ).then((_) => _cargarNotificaciones()); // Recarga al volver por si se envió algo
        },
        backgroundColor: Colors.blueGrey[800],
        foregroundColor: Colors.white,
        icon: const Icon(Icons.edit_square),
        label: const Text('Redactar', style: TextStyle(fontWeight: FontWeight.bold)),
      ),
    );
  }
}