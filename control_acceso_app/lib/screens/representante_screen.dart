import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import '../config/api_config.dart';
import '../services/websocket_service.dart';
import 'notifications_screen.dart';
import 'profile_screen.dart';
import 'login_screen.dart';

class RepresentanteScreen extends StatefulWidget {
  final String email;

  const RepresentanteScreen({super.key, required this.email});

  @override
  State<RepresentanteScreen> createState() => _RepresentanteScreenState();
}

class _RepresentanteScreenState extends State<RepresentanteScreen> {
  List<dynamic> _estudiantes = [];
  bool _isLoading = true;
  String? _error;
  Timer? _timer;
  WebSocketService? _wsService;
  StreamSubscription? _wsSubscription;

  @override
  void initState() {
    super.initState();
    _fetchEstudiantes();
    _initWebSocket();
    // Temporizador de respaldo pasivo a 30 segundos (WebSockets es el canal primario)
    _timer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _fetchEstudiantes(),
    );
  }

  void _initWebSocket() {
    _wsService = WebSocketService(email: widget.email);
    _wsService!.connect();
    _wsSubscription = _wsService!.eventStream.listen((event) {
      if (mounted) {
        // Al recibir un evento en tiempo real, actualizar la lista de representados inmediatamente
        _fetchEstudiantes();
      }
    });
  }

  Future<void> _fetchEstudiantes() async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConfig.baseUrl}/students/me?email=${widget.email}'),
      );
      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            _estudiantes = jsonDecode(response.body);
            _isLoading = false;
            _error = null;
          });
        }
      } else {
        if (mounted) {
          setState(() {
            _error = "Error al cargar datos: ${response.statusCode}";
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

  String _formatDate(String? isoString) {
    if (isoString == null || isoString.isEmpty) return 'Sin datos';
    try {
      final dt = DateTime.parse(isoString);
      return "${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')} - ${dt.day}/${dt.month}/${dt.year}";
    } catch (e) {
      return isoString;
    }
  }

  Widget _buildStatusChip(String estado) {
    Color color;
    IconData icon;
    String label;

    switch (estado) {
      case 'PRESENCIA_NORMAL':
      case 'PRESENTE':
        color = const Color(0xFF2E7D32); // Verde
        icon = Icons.check_circle;
        label = "PRESENTE";
        break;
      case 'DENTRO_DE_LA_INSTITUCION':
        color = const Color(0xFF1565C0); // Azul
        icon = Icons.school;
        label = "EN INSTITUCIÓN";
        break;
      case 'CURSO_DIFERENTE':
        color = const Color(0xFFEF6C00); // Naranja
        icon = Icons.warning_amber_rounded;
        label = "CURSO DIFERENTE";
        break;
      case 'INTRUSO':
      case 'INTRUSO_EXTERNO':
      case 'ALERTA':
        color = const Color(0xFFC62828); // Rojo
        icon = Icons.error_outline;
        label = "INCIDENCIA / ALERTA";
        break;
      case 'FUERA_DE_LA_INSTITUCION':
      case 'SALIDA':
        color = const Color(0xFF616161); // Gris
        icon = Icons.exit_to_app;
        label = "FUERA DE INSTITUCIÓN";
        break;
      default:
        color = const Color(0xFF757575);
        icon = Icons.help_outline;
        label = estado.replaceAll('_', ' ');
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.5), width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 5),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.bold,
              fontSize: 11,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _showStudentDetail(dynamic est) async {
    final sId = est['id'] ?? "${est['curso_origen']}_${est['nombre']}".replaceAll(' ', '_');
    final nombre = est['nombre'] ?? 'Estudiante';

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _StudentDetailBottomSheet(
        student: est,
        studentId: sId,
        studentName: nombre,
      ),
    );
  }

  void _showAddStudentDialog() {
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text(
          "Agregar Alumno",
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "Ingrese el ID o código institucional del estudiante para vincularlo a su cuenta:",
              style: TextStyle(fontSize: 14, color: Colors.black87),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: controller,
              decoration: InputDecoration(
                labelText: "ID o Nombre del Estudiante",
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                prefixIcon: const Icon(Icons.badge),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("Cancelar"),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text("Solicitud enviada para vincular estudiante ${controller.text}"),
                  backgroundColor: const Color(0xFFFBC02D),
                ),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFFBC02D),
              foregroundColor: Colors.black,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
            child: const Text("Vincular", style: TextStyle(fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FA),
      appBar: AppBar(
        backgroundColor: const Color(0xFFFBC02D), // Amarillo inspirador de referencia
        elevation: 1,
        iconTheme: const IconThemeData(color: Colors.black),
        title: const Text(
          'CONTROL ACCESO ESCOLAR',
          style: TextStyle(
            color: Colors.black,
            fontWeight: FontWeight.w900,
            fontSize: 16,
            letterSpacing: 0.5,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined, color: Colors.black),
            tooltip: 'Notificaciones',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => NotificationsScreen(email: widget.email),
                ),
              );
            },
          ),
          Container(
            margin: const EdgeInsets.only(right: 8, top: 8, bottom: 8),
            decoration: BoxDecoration(
              color: Colors.black.withOpacity(0.08),
              borderRadius: BorderRadius.circular(8),
            ),
            child: IconButton(
              icon: const Icon(Icons.refresh, color: Colors.black, size: 20),
              tooltip: 'Actualizar',
              onPressed: _fetchEstudiantes,
            ),
          ),
        ],
      ),
      drawer: _buildSideDrawer(),
      body: _buildBody(),
    );
  }

  Widget _buildSideDrawer() {
    final representativeName = widget.email.split('@')[0].toUpperCase().replaceAll('.', ' ');

    return Drawer(
      child: Column(
        children: [
          UserAccountsDrawerHeader(
            decoration: const BoxDecoration(
              color: Color(0xFFFBC02D),
            ),
            currentAccountPicture: CircleAvatar(
              backgroundColor: Colors.white,
              child: Icon(Icons.person, size: 45, color: Colors.grey.shade800),
            ),
            accountName: Text(
              representativeName,
              style: const TextStyle(
                color: Colors.black,
                fontWeight: FontWeight.bold,
                fontSize: 16,
              ),
            ),
            accountEmail: Text(
              widget.email,
              style: const TextStyle(color: Colors.black87),
            ),
          ),
          ListTile(
            leading: const Icon(Icons.home, color: Color(0xFFFBC02D)),
            title: const Text('Inicio / Mis Estudiantes', style: TextStyle(fontWeight: FontWeight.bold)),
            onTap: () => Navigator.pop(context),
          ),
          ListTile(
            leading: const Icon(Icons.notifications, color: Colors.amber),
            title: const Text('Notificaciones & Alertas'),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => NotificationsScreen(email: widget.email),
                ),
              );
            },
          ),
          ListTile(
            leading: const Icon(Icons.history, color: Colors.blue),
            title: const Text('Historial Global'),
            onTap: () {
              Navigator.pop(context);
              if (_estudiantes.isNotEmpty) {
                _showStudentDetail(_estudiantes.first);
              }
            },
          ),
          ListTile(
            leading: const Icon(Icons.person, color: Colors.purple),
            title: const Text('Mi Perfil'),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => ProfileScreen(rol: 'representante', email: widget.email),
                ),
              );
            },
          ),
          const Spacer(),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.logout, color: Colors.red),
            title: const Text('Cerrar Sesión', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
            onTap: () {
              Navigator.pop(context);
              Navigator.of(context).pushReplacement(
                MaterialPageRoute(builder: (context) => const LoginScreen()),
              );
            },
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _buildBody() {
    final representativeName = widget.email.split('@')[0].toUpperCase().replaceAll('.', ' ');

    return Column(
      children: [
        // Encabezado de Bienvenida
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
          color: const Color(0xFFEEEEEE),
          child: Column(
            children: [
              const Text(
                'Bienvenido',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                representativeName,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w900,
                  color: Colors.black,
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                'ID: ${widget.email}',
                style: const TextStyle(
                  fontSize: 12,
                  color: Colors.grey,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),

        // Lista de Estudiantes
        Expanded(
          child: _isLoading
              ? const Center(child: CircularProgressIndicator())
              : _error != null
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.error_outline, color: Colors.red, size: 50),
                          const SizedBox(height: 10),
                          Text(_error!, style: const TextStyle(color: Colors.red)),
                          const SizedBox(height: 10),
                          ElevatedButton(
                            onPressed: _fetchEstudiantes,
                            child: const Text("Reintentar"),
                          ),
                        ],
                      ),
                    )
                  : _estudiantes.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.school_outlined, size: 70, color: Colors.grey.shade400),
                              const SizedBox(height: 16),
                              const Text(
                                'No hay estudiantes vinculados a tu cuenta.',
                                style: TextStyle(fontSize: 16, color: Colors.grey),
                              ),
                            ],
                          ),
                        )
                      : RefreshIndicator(
                          onRefresh: _fetchEstudiantes,
                          child: ListView.builder(
                            padding: const EdgeInsets.all(16),
                            itemCount: _estudiantes.length,
                            itemBuilder: (context, index) {
                              return _buildStudentCard(_estudiantes[index]);
                            },
                          ),
                        ),
        ),

        // Botón "Agregar Alumno" al pie de página (Inspirado en la referencia)
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          child: SizedBox(
            width: double.infinity,
            height: 48,
            child: ElevatedButton(
              onPressed: _showAddStudentDialog,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFFBC02D), // Amarillo botón referencia
                foregroundColor: Colors.black,
                elevation: 3,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(24),
                ),
              ),
              child: const Text(
                'Agregar Alumno',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 0.5,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildStudentCard(dynamic est) {
    final nombre = est['nombre'] ?? 'Estudiante';
    final cursoOrigen = est['curso_origen'] ?? 'Desconocido';
    final cursoDetectado = est['curso_detectado'] ?? 'General';
    final estado = est['estado_actual'] ?? 'DESCONOCIDO';
    final studentId = est['id'] ?? '${cursoOrigen}_$nombre'.replaceAll(' ', '_');

    // Manejo visual de alertas si está en curso diferente
    final esCursoDiferente = estado == 'CURSO_DIFERENTE' || (cursoDetectado != 'General' && cursoDetectado != cursoOrigen);

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: const Color(0xFFF4F5F7), // Fondo tarjeta inspirada en referencia
        borderRadius: BorderRadius.circular(18),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.06),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
        border: Border.all(
          color: esCursoDiferente ? Colors.orange.shade300 : Colors.grey.shade300,
          width: esCursoDiferente ? 1.5 : 1,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Avatar del Estudiante con anillo amarillo dorado y badge (Inspirado en referencia)
                Stack(
                  alignment: Alignment.bottomLeft,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(3),
                      decoration: const BoxDecoration(
                        color: Color(0xFFFFA000), // Anillo amarillo dorado
                        shape: BoxShape.circle,
                      ),
                      child: CircleAvatar(
                        radius: 34,
                        backgroundColor: const Color(0xFFFFF9C4),
                        child: Icon(
                          Icons.person,
                          size: 45,
                          color: Colors.grey.shade800,
                        ),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.all(4),
                      decoration: const BoxDecoration(
                        color: Colors.white,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.edit_note,
                        size: 14,
                        color: Colors.black,
                      ),
                    ),
                  ],
                ),
                const SizedBox(width: 14),

                // Información del Estudiante
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        nombre.toUpperCase(),
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w900,
                          color: Colors.black,
                          height: 1.2,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Curso: $cursoOrigen',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                          color: Colors.grey.shade800,
                        ),
                      ),
                      if (esCursoDiferente) ...[
                        const SizedBox(height: 2),
                        Text(
                          'Detectado en: $cursoDetectado',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: Colors.orange.shade900,
                          ),
                        ),
                      ],
                      const SizedBox(height: 2),
                      Text(
                        'Última vista: ${_formatDate(est['ultima_deteccion'])}',
                        style: TextStyle(
                          fontSize: 11,
                          color: Colors.grey.shade600,
                        ),
                      ),
                    ],
                  ),
                ),

                // ID del estudiante en la parte superior derecha de la tarjeta
                Text(
                  'ID:\n${studentId.split('_').last}',
                  textAlign: TextAlign.right,
                  style: TextStyle(
                    fontSize: 11,
                    color: Colors.grey.shade600,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),

            const SizedBox(height: 14),

            // Fila inferior de Estado y Botón VER (Inspirado en verde brillante de referencia)
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildStatusChip(estado),

                // Botón VER Verde Brillante Ovalado
                ElevatedButton(
                  onPressed: () => _showStudentDetail(est),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF00C853), // Verde brillante de referencia
                    foregroundColor: Colors.white,
                    elevation: 2,
                    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20),
                    ),
                  ),
                  child: const Text(
                    'VER',
                    style: TextStyle(
                      fontWeight: FontWeight.w900,
                      fontSize: 13,
                      letterSpacing: 1.0,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// Modal desplegable de detalles e historial del estudiante
class _StudentDetailBottomSheet extends StatefulWidget {
  final dynamic student;
  final String studentId;
  final String studentName;

  const _StudentDetailBottomSheet({
    required this.student,
    required this.studentId,
    required this.studentName,
  });

  @override
  State<_StudentDetailBottomSheet> createState() => _StudentDetailBottomSheetState();
}

class _StudentDetailBottomSheetState extends State<_StudentDetailBottomSheet> {
  List<dynamic> _history = [];
  bool _loadingHistory = true;

  @override
  void initState() {
    super.initState();
    _fetchHistory();
  }

  Future<void> _fetchHistory() async {
    try {
      final res = await http.get(
        Uri.parse('${ApiConfig.baseUrl}/students/${widget.studentId}/history'),
      );
      if (res.statusCode == 200) {
        if (mounted) {
          setState(() {
            _history = jsonDecode(res.body);
            _loadingHistory = false;
          });
        }
      } else {
        if (mounted) setState(() => _loadingHistory = false);
      }
    } catch (e) {
      if (mounted) setState(() => _loadingHistory = false);
    }
  }

  String _formatTime(String? isoString) {
    if (isoString == null || isoString.isEmpty) return '--:--';
    try {
      final dt = DateTime.parse(isoString);
      return "${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}";
    } catch (e) {
      return isoString;
    }
  }

  @override
  Widget build(BuildContext context) {
    final est = widget.student;
    final nombre = est['nombre'] ?? widget.studentName;
    final cursoOrigen = est['curso_origen'] ?? 'Desconocido';
    final cursoDetectado = est['curso_detectado'] ?? 'General';

    return Container(
      height: MediaQuery.of(context).size.height * 0.85,
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          // Drag handle
          const SizedBox(height: 12),
          Container(
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: Colors.grey.shade300,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(height: 16),

          // Student Header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 30,
                  backgroundColor: const Color(0xFFFBC02D),
                  child: Icon(Icons.person, size: 40, color: Colors.grey.shade900),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        nombre,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      Text(
                        'Curso de Origen: $cursoOrigen',
                        style: TextStyle(color: Colors.grey.shade700, fontSize: 13),
                      ),
                      Text(
                        'Curso Detectado: $cursoDetectado',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),
          const Divider(),

          // Timeline Title
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'LÍNEA DE TIEMPO / HISTORIAL RECIENTE',
                style: TextStyle(
                  fontWeight: FontWeight.w900,
                  fontSize: 13,
                  letterSpacing: 0.5,
                  color: Colors.black87,
                ),
              ),
            ),
          ),

          // Timeline Events List
          Expanded(
            child: _loadingHistory
                ? const Center(child: CircularProgressIndicator())
                : _history.isEmpty
                    ? Center(
                        child: Text(
                          'No hay eventos registrados recientemente.',
                          style: TextStyle(color: Colors.grey.shade600),
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        itemCount: _history.length,
                        itemBuilder: (context, index) {
                          final item = _history[index];
                          final tipo = item['tipo_evento'] ?? 'EVENTO';
                          final hora = _formatTime(item['fecha_hora']);
                          final camara = item['camara_curso'] ?? item['curso_detectado'] ?? 'General';

                          return Container(
                            margin: const EdgeInsets.only(bottom: 12),
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: const Color(0xFFF5F5F7),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: Colors.grey.shade200),
                            ),
                            child: Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFFBC02D).withOpacity(0.2),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Text(
                                    hora,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 13,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 14),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        tipo.replaceAll('_', ' '),
                                        style: const TextStyle(
                                          fontWeight: FontWeight.bold,
                                          fontSize: 14,
                                        ),
                                      ),
                                      Text(
                                        'Ubicación: $camara',
                                        style: TextStyle(color: Colors.grey.shade700, fontSize: 12),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}
