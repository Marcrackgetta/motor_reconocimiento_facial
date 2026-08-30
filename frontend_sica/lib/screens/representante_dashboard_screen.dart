import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_database/firebase_database.dart';
import 'login_screen.dart'; 
import 'estudiante_detalle_screen.dart';
import '../models/estudiante.dart';

class RepresentanteDashboardScreen extends StatefulWidget {
  const RepresentanteDashboardScreen({super.key});

  @override
  State<RepresentanteDashboardScreen> createState() => _RepresentanteDashboardScreenState();
}

class _RepresentanteDashboardScreenState extends State<RepresentanteDashboardScreen> {
  String _nombreUsuario = 'Cargando...'; 
  
  String _estadoVinculacion = "CARGANDO";
  
  String _estudianteUUID = ""; 
  String _estudianteNombre = "Estudiante Asignado";
  
  // SOLUCIÓN 1: Se agregó 'final' a la variable que no cambia de valor
  final String _cursoNombre = "Información del Colegio";
  
  String _ultimoEstado = "AUSENTE";
  String _ultimaHora = "--:--";

  final DatabaseReference _dbRef = FirebaseDatabase.instance.ref();
  
  final TextEditingController _cedulaController = TextEditingController();
  final TextEditingController _nombreEstudianteController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _escucharEstadoUsuario();
  }

  void _escucharEstadoUsuario() {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      _cerrarSesion();
      return;
    }

    _dbRef.child('Usuarios/${user.uid}').onValue.listen((event) {
      if (event.snapshot.exists) {
        final data = event.snapshot.value as Map<dynamic, dynamic>;
        
        if (mounted) {
          setState(() {
            _nombreUsuario = data['nombre'] ?? 'Representante';
            
            if (data['cedula_estudiante'] != null && data['cedula_estudiante'].toString().isNotEmpty) {
              _estadoVinculacion = "VINCULADO";
              _estudianteUUID = data['cedula_estudiante'];
              _estudianteNombre = data['nombre_estudiante'] ?? "Estudiante Asignado";
              _escucharAsistenciaEnVivo(); 
            } else if (data['solicitud_pendiente'] == true) {
              _estadoVinculacion = "PENDIENTE";
            } else {
              _estadoVinculacion = "SIN_VINCULAR";
            }
          });
        }
      }
    });
  }

  Future<bool> _solicitarVinculacion() async {
    final cedula = _cedulaController.text.trim();
    final nombreEstudiante = _nombreEstudianteController.text.trim();

    if (cedula.isEmpty || nombreEstudiante.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, ingrese el nombre y la cédula del estudiante.'), backgroundColor: Colors.red),
      );
      return false; 
    }

    final user = FirebaseAuth.instance.currentUser;
    if (user != null) {
      await _dbRef.child('SolicitudesVinculacion').push().set({
        'rep_uid': user.uid,
        'correo_rep': user.email,
        'nombre_rep': _nombreUsuario,
        'cedula_estudiante': cedula,
        'nombre_estudiante': nombreEstudiante,
        'estado': 'pendiente',
        'timestamp': ServerValue.timestamp,
      });

      await _dbRef.child('Usuarios/${user.uid}').update({
        'solicitud_pendiente': true,
      });
      return true; 
    }
    return false;
  }

  void _escucharAsistenciaEnVivo() {
    if (_estudianteUUID.isEmpty) return;

    _dbRef.child('SesionesCamara/CAM_001/RegistroDiario').limitToLast(1).onValue.listen((event) {
      if (event.snapshot.exists && mounted) {
        try {
          final data = event.snapshot.value as Map<dynamic, dynamic>;
          final key = data.keys.first;
          final registro = data[key] as Map<dynamic, dynamic>;

          bool estaPresente = false;
          String horaFormateada = "--:--";

          if (registro['timestamp'] != null) {
            final double timestampDouble = (registro['timestamp'] as num).toDouble();
            
            final date = DateTime.fromMillisecondsSinceEpoch((timestampDouble * 1000).toInt());
            final ahora = DateTime.now();

            bool esDeHoy = date.year == ahora.year && date.month == ahora.month && date.day == ahora.day;

            if (esDeHoy) {
              if (registro['lista_presentes'] != null) {
                final presentes = registro['lista_presentes'] as Map<dynamic, dynamic>;
                if (presentes.containsKey(_estudianteUUID)) {
                  estaPresente = true;
                }
              }
              horaFormateada = "${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}";
            }
          }

          setState(() {
            _ultimoEstado = estaPresente ? "PRESENTE" : "AUSENTE";
            _ultimaHora = horaFormateada;
          });
        } catch (e) {
          debugPrint("Error al procesar asistencia: $e");
        }
      } else if (mounted) {
        setState(() {
          _ultimoEstado = "AUSENTE";
          _ultimaHora = "--:--";
        });
      }
    });
  }

  void _cerrarSesion() async {
    await FirebaseAuth.instance.signOut();
    if (mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => const LoginScreen()),
      );
    }
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
                child: Text('ESTADO DEL SISTEMA', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.black45, letterSpacing: 1.0)),
              ),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
                  children: [
                    _construirContenidoDinamico(), 
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

  Widget _construirContenidoDinamico() {
    if (_estadoVinculacion == "CARGANDO") {
      return const Center(child: Padding(padding: EdgeInsets.all(32.0), child: CircularProgressIndicator()));
    } else if (_estadoVinculacion == "SIN_VINCULAR") {
      return _construirBotonVinculacion(); 
    } else if (_estadoVinculacion == "PENDIENTE") {
      return _construirMensajePendiente();
    } else {
      return _construirTarjetaEstudiante();
    }
  }

  Widget _construirBotonVinculacion() {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(40.0),
        child: Column(
          children: [
            const Icon(Icons.person_search, size: 64, color: Colors.blueGrey),
            const SizedBox(height: 16),
            const Text(
              'Aún no tiene un estudiante asignado',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.black87),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            const Text(
              'Haga clic en el botón inferior para buscar y vincular a su representado.',
              style: TextStyle(color: Colors.black54),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),
            SizedBox(
              width: 250,
              height: 50,
              child: ElevatedButton.icon(
                onPressed: _abrirDialogoVinculacion, 
                icon: const Icon(Icons.add_link),
                label: const Text('Vincular Alumno', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
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
    );
  }

  void _abrirDialogoVinculacion() {
    showDialog(
      context: context,
      barrierDismissible: false, 
      builder: (BuildContext dialogContext) {
        bool isLoadingDialog = false; 

        return StatefulBuilder(
          builder: (context, setStateDialog) {
            return AlertDialog(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              title: const Text('Solicitar Vinculación', style: TextStyle(fontWeight: FontWeight.bold)),
              content: SizedBox(
                width: 400, 
                child: Column(
                  mainAxisSize: MainAxisSize.min, 
                  children: [
                    const Text(
                      'Ingrese los datos exactos del estudiante. Esta solicitud será revisada por la administración.',
                      style: TextStyle(fontSize: 13, color: Colors.black54),
                    ),
                    const SizedBox(height: 24),
                    TextField(
                      controller: _nombreEstudianteController,
                      decoration: InputDecoration(
                        labelText: 'Nombre Completo del Estudiante',
                        prefixIcon: const Icon(Icons.person_outline),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      textCapitalization: TextCapitalization.words,
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _cedulaController,
                      decoration: InputDecoration(
                        labelText: 'Cédula del Estudiante',
                        prefixIcon: const Icon(Icons.badge_outlined),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      keyboardType: TextInputType.number,
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: isLoadingDialog ? null : () => Navigator.pop(dialogContext),
                  child: const Text('Cancelar', style: TextStyle(color: Colors.grey)),
                ),
                ElevatedButton(
                  onPressed: isLoadingDialog ? null : () async {
                    setStateDialog(() => isLoadingDialog = true); 
                    
                    bool exito = await _solicitarVinculacion(); 
                    
                    setStateDialog(() => isLoadingDialog = false); 
                    
                    // SOLUCIÓN 2: Verificamos directamente el contexto del diálogo
                    if (exito && dialogContext.mounted) {
                      Navigator.pop(dialogContext); 
                    }
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.amber[600],
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  child: isLoadingDialog
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : const Text('Enviar Solicitud', style: TextStyle(fontWeight: FontWeight.bold)),
                ),
              ],
            );
          },
        );
      }
    );
  }

  Widget _construirMensajePendiente() {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          children: [
            Icon(Icons.hourglass_top, size: 64, color: Colors.amber[600]),
            const SizedBox(height: 16),
            const Text(
              'Solicitud en Proceso',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.black87),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            const Text(
              'La administración escolar está revisando su solicitud. Esta pantalla se actualizará automáticamente en cuanto sea aprobada.',
              style: TextStyle(color: Colors.black54, height: 1.4),
              textAlign: TextAlign.center,
            ),
          ],
        ),
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