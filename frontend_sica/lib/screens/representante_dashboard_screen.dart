import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:firebase_database/firebase_database.dart';
import 'login_screen.dart'; 
import 'estudiante_detalle_screen.dart';
import '../models/estudiante.dart'; // Mantén esta importación si la pantalla de detalle la usa

class RepresentanteDashboardScreen extends StatefulWidget {
  const RepresentanteDashboardScreen({super.key});

  @override
  State<RepresentanteDashboardScreen> createState() => _RepresentanteDashboardScreenState();
}

class _RepresentanteDashboardScreenState extends State<RepresentanteDashboardScreen> {
  String _nombreUsuario = 'Representante'; 
  
  // Datos del estudiante para el MVP
  final String _estudianteUUID = "0931605919"; 
  final String _estudianteNombre = "Marcelo Zambrano";
  final String _cursoNombre = "2° Informática B";
  
  String _ultimoEstado = "AUSENTE";
  String _ultimaHora = "--:--";

  // Referencia a Realtime Database
  final DatabaseReference _dbRef = FirebaseDatabase.instance.ref();

  @override
  void initState() {
    super.initState();
    _cargarDatosUsuario(); 
    _escucharAsistenciaEnVivo();
  }

  Future<void> _cargarDatosUsuario() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _nombreUsuario = prefs.getString('nombre') ?? 'Representante';
    });
  }

  // ==========================================================
  // LA MAGIA DEL MVP: Escuchar Realtime Database en vivo
  // ==========================================================
  void _escucharAsistenciaEnVivo() {
    _dbRef.child('SesionesCamara/CAM_001/RegistroDiario').limitToLast(1).onValue.listen((event) {
      if (event.snapshot.value != null) {
        try {
          final data = event.snapshot.value as Map<dynamic, dynamic>;
          final key = data.keys.first;
          final registro = data[key] as Map<dynamic, dynamic>;

          // 1. Verificamos si la cédula está en la lista de presentes que envió Python
          bool estaPresente = false;
          if (registro['lista_presentes'] != null) {
            final presentes = registro['lista_presentes'] as Map<dynamic, dynamic>;
            if (presentes.containsKey(_estudianteUUID)) {
              estaPresente = true;
            }
          }

          // 2. Extraemos la hora exacta del timestamp del motor
          String horaFormateada = "--:--";
          if (registro['timestamp'] != null) {
            final double timestampDouble = (registro['timestamp'] as num).toDouble();
            // Restamos 5 horas para igualar la zona horaria de Ecuador (UTC-5)
            final date = DateTime.fromMillisecondsSinceEpoch((timestampDouble * 1000).toInt()).subtract(const Duration(hours: 5));
            horaFormateada = "${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}";
          }

          if (mounted) {
            setState(() {
              _ultimoEstado = estaPresente ? "PRESENTE" : "AUSENTE";
              _ultimaHora = horaFormateada;
            });
          }
        } catch (e) {
          debugPrint("Error al procesar datos de Firebase: $e");
        }
      }
    });
  }

  void _cerrarSesion() {
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (context) => const LoginScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100], 
      appBar: AppBar(
        title: const Text('Portal del Representante', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 18, color: Colors.white)),
        backgroundColor: Colors.blueGrey[800],
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.logout, color: Colors.white, size: 22), 
            onPressed: _cerrarSesion,
            tooltip: 'Cerrar Sesión',
          ), 
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 800), 
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _construirEncabezadoRepresentante(),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 24.0, vertical: 8.0),
                child: Text('ESTUDIANTE ASIGNADO', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.black45, letterSpacing: 1.0)),
              ),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
                  children: [
                    _construirTarjetaEstudiante(),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _construirEncabezadoRepresentante() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: Colors.grey[200]!)),
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 30,
            backgroundColor: Colors.blueGrey[50],
            child: Icon(Icons.family_restroom, color: Colors.blueGrey[800], size: 30),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Bienvenido/a,', style: TextStyle(fontSize: 14, color: Colors.black54)),
                const SizedBox(height: 4),
                Text(
                  _nombreUsuario.toUpperCase(), 
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.black87),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _construirTarjetaEstudiante() {
    final bool estaPresente = _ultimoEstado == "PRESENTE";
    final Color colorEstado = estaPresente ? Colors.green : Colors.grey;
    final String textoEstado = estaPresente ? "En la institución" : "Fuera de la institución";
    final IconData iconoEstado = estaPresente ? Icons.check_circle : Icons.radio_button_unchecked;

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () {
          // Creamos un objeto de estudiante falso solo para que la pantalla de detalle no falle
          final estMock = Estudiante(
            id: 1, 
            uuid: _estudianteUUID, 
            nombreCompleto: _estudianteNombre, 
            cursoNombre: _cursoNombre, 
            representanteNombre: _nombreUsuario
          );
          Navigator.push(context, MaterialPageRoute(builder: (context) => EstudianteDetalleScreen(estudiante: estMock)));
        },
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(color: Colors.blueGrey[50], shape: BoxShape.circle),
                    child: Icon(Icons.person, size: 28, color: Colors.blueGrey[700]),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _estudianteNombre,
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.black87),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          "Cédula: $_estudianteUUID • $_cursoNombre",
                          style: const TextStyle(fontSize: 13, color: Colors.black54),
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.arrow_forward_ios, size: 16, color: Colors.grey[400]),
                ],
              ),
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 12),
                child: Divider(height: 1),
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Icon(iconoEstado, color: colorEstado, size: 18),
                      const SizedBox(width: 8),
                      Text(textoEstado, style: TextStyle(color: colorEstado, fontWeight: FontWeight.bold, fontSize: 13)),
                    ],
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.grey[100],
                      borderRadius: BorderRadius.circular(8)
                    ),
                    child: Text(
                      "Hora: $_ultimaHora", 
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.black54)
                    ),
                  )
                ],
              )
            ],
          ),
        ),
      ),
    );
  }
}