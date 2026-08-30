import 'package:flutter/material.dart';
import 'package:firebase_database/firebase_database.dart';
import '../models/estudiante.dart';

class EstudianteDetalleScreen extends StatefulWidget {
  final Estudiante estudiante;

  const EstudianteDetalleScreen({super.key, required this.estudiante});

  @override
  State<EstudianteDetalleScreen> createState() => _EstudianteDetalleScreenState();
}

class _EstudianteDetalleScreenState extends State<EstudianteDetalleScreen> {
  List<Map<String, dynamic>> _notificaciones = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _escucharNotificaciones();
  }

  void _escucharNotificaciones() {
    final dbRef = FirebaseDatabase.instance.ref('SesionesCamara/CAM_001/RegistroDiario');
    
    dbRef.onValue.listen((event) {
      if (!mounted) return;

      if (event.snapshot.exists) {
        final data = event.snapshot.value as Map<dynamic, dynamic>;
        List<Map<String, dynamic>> listaTemporal = [];

        data.forEach((key, value) {
          final registro = value as Map<dynamic, dynamic>;
          
          if (registro['lista_presentes'] != null) {
            final presentes = registro['lista_presentes'] as Map<dynamic, dynamic>;
            
            if (presentes.containsKey(widget.estudiante.uuid)) {
              final tipo = registro['tipo_evento'] ?? 'ENTRADA';
              final timestamp = (registro['timestamp'] as num).toDouble();
              
              final date = DateTime.fromMillisecondsSinceEpoch((timestamp * 1000).toInt());
              final hora = "${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}";

              listaTemporal.add({
                'tipo': tipo,
                'hora': hora,
                'timestamp': timestamp,
              });
            }
          }
        });

        listaTemporal.sort((a, b) => b['timestamp'].compareTo(a['timestamp']));

        setState(() {
          _notificaciones = listaTemporal;
          _isLoading = false;
        });
      } else {
        setState(() {
          _notificaciones = [];
          _isLoading = false;
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2, 
      child: Scaffold(
        backgroundColor: Colors.blueGrey[50], // Fondo claro idéntico al Dashboard
        appBar: AppBar(
          backgroundColor: Colors.blueGrey[800], // Azul grisáceo oscuro elegante
          elevation: 0,
          iconTheme: const IconThemeData(color: Colors.white),
          title: const Text(
            'Detalle de Alumno', 
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 18)
          ),
          centerTitle: true,
          bottom: const TabBar(
            labelColor: Colors.white,
            unselectedLabelColor: Colors.white54,
            indicatorColor: Colors.white,
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
      return Center(child: CircularProgressIndicator(color: Colors.blueGrey[800]));
    }

    return Column(
      children: [
        // Encabezado del estudiante estilo Minimalista (igual al Dashboard)
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: Colors.white,
            border: Border(bottom: BorderSide(color: Colors.grey[200]!)),
          ),
          child: Row(
            children: [
              CircleAvatar(
                radius: 26,
                backgroundColor: Colors.blueGrey[50],
                child: Icon(Icons.person, color: Colors.blueGrey[800], size: 28),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Historial de', style: TextStyle(fontSize: 13, color: Colors.black54)),
                    const SizedBox(height: 2),
                    Text(
                      widget.estudiante.nombreCompleto.toUpperCase(),
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.black87),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        
        // Lista de Notificaciones o Estado Vacío
        Expanded(
          child: _notificaciones.isEmpty
              ? _construirAlertaVacia("No hay notificaciones\nrecientes para este alumno.")
              : ListView.builder(
                  padding: const EdgeInsets.all(20),
                  itemCount: _notificaciones.length,
                  itemBuilder: (context, index) {
                    final notificacion = _notificaciones[index];
                    return _construirTarjetaNotificacion(notificacion);
                  },
                ),
        ),

        // Botones inferiores minimalistas
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          decoration: BoxDecoration(
            color: Colors.white,
            border: Border(top: BorderSide(color: Colors.grey[200]!)),
          ),
          child: SafeArea(
            child: Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () {},
                    icon: Icon(Icons.history, color: Colors.blueGrey[800], size: 20),
                    label: Text('Historial', style: TextStyle(color: Colors.blueGrey[800], fontWeight: FontWeight.bold)),
                    style: OutlinedButton.styleFrom(
                      side: BorderSide(color: Colors.blueGrey[200]!),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () {},
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red[50], // Fondo rojo muy suave
                      foregroundColor: Colors.red[700], // Texto rojo oscuro
                      elevation: 0,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    child: const Text('Reportar Falta', style: TextStyle(fontWeight: FontWeight.bold)),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _construirTarjetaNotificacion(Map<String, dynamic> notificacion) {
    bool esEntrada = notificacion['tipo'] == 'ENTRADA';
    
    return Card(
      color: Colors.white,
      elevation: 2,
      shadowColor: Colors.black.withOpacity(0.05),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: esEntrada ? Colors.green[50] : Colors.blueGrey[50],
                shape: BoxShape.circle,
              ),
              child: Icon(
                esEntrada ? Icons.login : Icons.logout,
                color: esEntrada ? Colors.green[600] : Colors.blueGrey[600],
                size: 24,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    esEntrada ? 'Ingreso Confirmado' : 'Salida Registrada',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Colors.black87),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Hora: ${notificacion['hora']}', 
                    style: const TextStyle(color: Colors.black54, fontSize: 13),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _construirTabNovedades() {
    return Column(
      children: [
        Expanded(child: _construirAlertaVacia("No hay novedades\nregistradas hoy.")),
      ],
    );
  }

  // Estado vacío moderno y sutil
  Widget _construirAlertaVacia(String mensaje) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.notifications_none_outlined, size: 64, color: Colors.blueGrey[200]),
          const SizedBox(height: 16),
          Text(
            mensaje, 
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 15, 
              color: Colors.blueGrey[400],
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}