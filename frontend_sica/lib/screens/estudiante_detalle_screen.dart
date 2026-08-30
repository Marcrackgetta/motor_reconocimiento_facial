import 'package:flutter/material.dart';
import '../models/estudiante.dart';
import '../models/asistencia.dart';
import '../services/api_service.dart';

class EstudianteDetalleScreen extends StatefulWidget {
  final Estudiante estudiante;

  // Recibe al estudiante seleccionado desde la pantalla anterior
  const EstudianteDetalleScreen({super.key, required this.estudiante});

  @override
  State<EstudianteDetalleScreen> createState() => _EstudianteDetalleScreenState();
}

class _EstudianteDetalleScreenState extends State<EstudianteDetalleScreen> {
  final ApiService _apiService = ApiService();
  List<Asistencia> _notificaciones = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _cargarNotificaciones();
  }

  Future<void> _cargarNotificaciones() async {
    try {
      // Reutilizamos el endpoint del dashboard que trae los últimos eventos
      final metrics = await _apiService.fetchDashboardMetrics();
      
      // Filtramos la lista para mostrar solo las asistencias de este estudiante en particular
      setState(() {
        _notificaciones = metrics.asistencias
            .where((a) => a.estudianteUuid == widget.estudiante.uuid)
            .toList();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    // Usamos DefaultTabController para manejar las pestañas fácilmente
    return DefaultTabController(
      length: 2, // Dos pestañas: Notificaciones y Novedades
      child: Scaffold(
        backgroundColor: Colors.grey[200],
        appBar: AppBar(
          backgroundColor: Colors.amber[400],
          iconTheme: const IconThemeData(color: Colors.black87),
          title: const Text('DETALLE DE ALUMNO', style: TextStyle(color: Colors.black87, fontWeight: FontWeight.bold)),
          centerTitle: true,
          bottom: const TabBar(
            labelColor: Colors.black87,
            unselectedLabelColor: Colors.black54,
            indicatorColor: Colors.black87,
            indicatorWeight: 3,
            tabs: [
              Tab(text: 'Notificaciones'),
              Tab(text: 'Novedades'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _construirTabNotificaciones(),
            _construirTabNovedades(),
          ],
        ),
      ),
    );
  }

  Widget _construirTabNotificaciones() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    return Column(
      children: [
        // Encabezado del estudiante dentro del tab
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(16),
          color: Colors.white,
          child: Text(
            widget.estudiante.nombreCompleto.toUpperCase(),
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            textAlign: TextAlign.center,
          ),
        ),
        
        // Lista de Notificaciones
        Expanded(
          child: _notificaciones.isEmpty
              ? _construirAlertaVacia("¡No hay notificaciones recientes para este alumno!")
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _notificaciones.length,
                  itemBuilder: (context, index) {
                    final notificacion = _notificaciones[index];
                    return _construirTarjetaNotificacion(notificacion);
                  },
                ),
        ),

        // Botones inferiores inspirados en la referencia
        Container(
          padding: const EdgeInsets.all(16),
          color: Colors.white,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              ElevatedButton.icon(
                onPressed: () {},
                icon: const Icon(Icons.history, color: Colors.black87),
                label: const Text('Historial', style: TextStyle(color: Colors.black87)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.amber[300],
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                ),
              ),
              ElevatedButton(
                onPressed: () {},
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.redAccent,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 25, vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                ),
                child: const Text('No asiste', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _construirTarjetaNotificacion(Asistencia asistencia) {
    bool esPresente = asistencia.estado == 'PRESENTE';
    
    return Card(
      color: esPresente ? Colors.green[50] : Colors.red[50],
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(color: esPresente ? Colors.green[200]! : Colors.red[200]!, width: 1),
      ),
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: Icon(
          esPresente ? Icons.notifications_active : Icons.notification_important,
          color: esPresente ? Colors.green[700] : Colors.red[700],
        ),
        title: Text(
          esPresente ? 'Registro de Acceso Confirmado' : 'Alerta de Intrusión / Desconocido',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: Text('Detectado en: ${asistencia.cameraId}\nHora: ${asistencia.fechaRegistro}'),
      ),
    );
  }

  Widget _construirTabNovedades() {
    return Column(
      children: [
        const SizedBox(height: 20),
        _construirAlertaVacia("No hay novedades registradas."),
      ],
    );
  }

  // Widget reutilizable para los recuadros amarillos de la imagen de referencia
  Widget _construirAlertaVacia(String mensaje) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.amber[100], // Fondo amarillo pálido
        borderRadius: BorderRadius.circular(15),
      ),
      child: Row(
        children: [
          const Icon(Icons.notifications_off, color: Colors.redAccent),
          const SizedBox(width: 15),
          Expanded(child: Text(mensaje, style: const TextStyle(fontSize: 16))),
        ],
      ),
    );
  }
}