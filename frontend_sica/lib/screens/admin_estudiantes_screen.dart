import 'package:flutter/material.dart';
import '../models/estudiante.dart';
import '../models/curso.dart';
import '../models/usuario.dart';
import '../services/api_service.dart';

class AdminEstudiantesScreen extends StatefulWidget {
  const AdminEstudiantesScreen({super.key});

  @override
  State<AdminEstudiantesScreen> createState() => _AdminEstudiantesScreenState();
}

class _AdminEstudiantesScreenState extends State<AdminEstudiantesScreen> {
  final ApiService _apiService = ApiService();
  List<Estudiante> _estudiantes = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _cargarEstudiantes();
  }

  Future<void> _cargarEstudiantes() async {
    setState(() => _isLoading = true);
    try {
      final estudiantes = await _apiService.fetchEstudiantes();
      setState(() {
        _estudiantes = estudiantes;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  // --- FORMULARIO UNIFICADO (CREACIÓN Y ASIGNACIÓN) ---
  void _mostrarDialogoCrear() async {
    // 1. Cargamos las listas para los Dropdowns antes de mostrar el diálogo
    List<Curso> cursosDisponibles = [];
    List<Usuario> representantesDisponibles = [];
    
    try {
      cursosDisponibles = await _apiService.fetchCursos();
      representantesDisponibles = await _apiService.fetchUsuariosPorRol('REPRESENTANTE');
    } catch (e) {
      if(mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Error al cargar datos para asignación')));
    }

    if (!mounted) return;

    final nombreController = TextEditingController();
    final uuidController = TextEditingController();
    int? cursoSeleccionado = cursosDisponibles.isNotEmpty ? cursosDisponibles.first.id : null;
    int? representanteSeleccionado; // Opcional al inicio

    bool isSubmitting = false;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setStateDialog) {
            return AlertDialog(
              title: const Text('Crear y Asignar Estudiante', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text('Datos del Estudiante', style: TextStyle(color: Colors.grey, fontWeight: FontWeight.bold)),
                    TextField(controller: nombreController, decoration: const InputDecoration(labelText: 'Nombre Completo')),
                    TextField(controller: uuidController, decoration: const InputDecoration(labelText: 'Identificador (UUID) Edge')),
                    const SizedBox(height: 20),
                    const Divider(),
                    const Text('Asignaciones', style: TextStyle(color: Colors.grey, fontWeight: FontWeight.bold)),
                    
                    // Dropdown de Cursos
                    DropdownButtonFormField<int>(
                      value: cursoSeleccionado,
                      decoration: const InputDecoration(labelText: 'Asignar a Curso'),
                      items: cursosDisponibles.map((c) => DropdownMenuItem(value: c.id, child: Text(c.nombre))).toList(),
                      onChanged: (val) => setStateDialog(() => cursoSeleccionado = val),
                    ),
                    const SizedBox(height: 10),
                    
                    // Dropdown de Representantes
                    DropdownButtonFormField<int?>(
                      value: representanteSeleccionado,
                      decoration: const InputDecoration(labelText: 'Asignar Representante (Opcional)'),
                      items: [
                        const DropdownMenuItem<int?>(value: null, child: Text('Sin asignar por ahora')),
                        ...representantesDisponibles.map((r) => DropdownMenuItem(value: r.id, child: Text(r.nombreCompleto)))
                      ],
                      onChanged: (val) => setStateDialog(() => representanteSeleccionado = val),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: isSubmitting ? null : () => Navigator.pop(context),
                  child: const Text('Cancelar'),
                ),
                ElevatedButton(
                  onPressed: isSubmitting
                      ? null
                      : () async {
                          if (nombreController.text.isEmpty || uuidController.text.isEmpty || cursoSeleccionado == null) {
                            return; // Validación básica
                          }
                          setStateDialog(() => isSubmitting = true);
                          try {
                            await _apiService.crearEstudiante(
                              uuidController.text.trim(),
                              nombreController.text.trim(),
                              cursoSeleccionado!,
                              representanteSeleccionado, // Se envía la asignación al backend!
                            );
                            if (context.mounted) {
                              Navigator.pop(context);
                              _cargarEstudiantes();
                              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Guardado y asignado')));
                            }
                          } catch (e) {
                            setStateDialog(() => isSubmitting = false);
                            if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
                          }
                        },
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.blueGrey[800], foregroundColor: Colors.white),
                  child: isSubmitting ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : const Text('Crear y Asignar'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: const Text('Estudiantes y Asignaciones', style: TextStyle(color: Colors.white)),
        backgroundColor: Colors.blueGrey[800],
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _estudiantes.isEmpty
              ? const Center(child: Text('No hay estudiantes registrados. Crea el primero.'))
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _estudiantes.length,
                  itemBuilder: (context, index) {
                    final est = _estudiantes[index];
                    return Card(
                      elevation: 2,
                      margin: const EdgeInsets.only(bottom: 12),
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.face, color: Colors.blueGrey),
                                const SizedBox(width: 10),
                                Text(est.nombreCompleto, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                              ],
                            ),
                            const Divider(),
                            Text('Curso: ${est.cursoNombre}', style: const TextStyle(color: Colors.black87)),
                            Text('Representante: ${est.representanteNombre}', 
                              style: TextStyle(color: est.representanteId == null ? Colors.red : Colors.green[700], fontWeight: FontWeight.bold)
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _mostrarDialogoCrear,
        backgroundColor: Colors.blueGrey[800],
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add),
        label: const Text('Agregar Estudiante'),
      ),
    );
  }
}