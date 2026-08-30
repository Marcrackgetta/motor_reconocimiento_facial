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
  // Ahora usamos una lista de Mapas para extraer directamente la data de Firebase
  List<Map<String, dynamic>> _notificaciones = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _escucharNotificaciones();
  }

  // NUEVO: Escuchador en tiempo real desde Firebase
  void _escucharNotificaciones() {
    final dbRef = FirebaseDatabase.instance.ref('SesionesCamara/CAM_001/RegistroDiario');
    
    dbRef.onValue.listen((event) {
      if (!mounted) return;

      if (event.snapshot.exists) {
        final data = event.snapshot.value as Map<dynamic, dynamic>;
        List<Map<String, dynamic>> listaTemporal = [];

        data.forEach((key, value) {
          final registro = value as Map<dynamic, dynamic>;
          
          // Verificamos si hay presentes y si nuestro estudiante está en esa lista
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

        // Ordenamos para que la notificación más reciente salga arriba
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
        backgroundColor: Colors.grey[100],
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
      return const Center(child: CircularProgressIndicator(color: Colors.amber));
    }

    return Column(
      children: [
        // Encabezado del estudiante
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 20),
          color: Colors.white,
          child: Text(
            widget.estudiante.nombreCompleto.toUpperCase(),
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.black87),
            textAlign: TextAlign.center,
          ),
        ),
        
        // Lista de Notificaciones o Estado Vacío
        Expanded(
          child: _notificaciones.isEmpty
              ? _construirAlertaVacia("¡No hay notificaciones recientes\npara este alumno!")
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _notificaciones.length,
                  itemBuilder: (context, index) {
                    final notificacion = _notificaciones[index];
                    return _construirTarjetaNotificacion(notificacion);
                  },
                ),
        ),

        // Botones inferiores
        Container(
          padding: const EdgeInsets.all(16),
          color: Colors.white,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              ElevatedButton.icon(
                onPressed: () {},
                icon: const Icon(Icons.history, color: Colors.black87),
                label: const Text('Historial', style: TextStyle(color: Colors.black87, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.amber[300],
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                  elevation: 0,
                ),
              ),
              ElevatedButton(
                onPressed: () {},
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFFF5252), // Rojo de la imagen
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                  elevation: 0,
                ),
                child: const Text('No asiste', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _construirTarjetaNotificacion(Map<String, dynamic> notificacion) {
    bool esEntrada = notificacion['tipo'] == 'ENTRADA';
    
    return Card(
      color: esEntrada ? Colors.green[50] : Colors.blue[50],
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(color: esEntrada ? Colors.green[200]! : Colors.blue[200]!, width: 1),
      ),
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: Icon(
          esEntrada ? Icons.login : Icons.logout,
          color: esEntrada ? Colors.green[700] : Colors.blue[700],
        ),
        title: Text(
          esEntrada ? 'Ingreso Confirmado' : 'Salida Registrada',
          style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.black87),
        ),
        subtitle: Text('Hora: ${notificacion['hora']}', style: const TextStyle(color: Colors.black54)),
      ),
    );
  }

  Widget _construirTabNovedades() {
    return Column(
      children: [
        Expanded(child: _construirAlertaVacia("No hay novedades registradas.")),
      ],
    );
  }

  // NUEVO: Rediseñado para coincidir exactamente con tu imagen de referencia
  Widget _construirAlertaVacia(String mensaje) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF7C0), // Color amarillo idéntico a la foto
        borderRadius: BorderRadius.circular(16),
      ),
      child: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const Icon(Icons.notifications_off, color: Color(0xFFFF5252), size: 28), // Icono rojo
              const SizedBox(width: 16),
              Flexible(
                child: Text(
                  mensaje, 
                  style: const TextStyle(
                    fontSize: 16, 
                    color: Colors.black87,
                    height: 1.4,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}