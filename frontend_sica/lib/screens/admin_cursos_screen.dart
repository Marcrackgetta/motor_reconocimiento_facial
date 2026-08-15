import 'package:flutter/material.dart';
import '../models/curso.dart';
import '../models/usuario.dart';
import '../services/api_service.dart';

class AdminCursosScreen extends StatefulWidget {
  const AdminCursosScreen({super.key});

  @override
  State<AdminCursosScreen> createState() => _AdminCursosScreenState();
}

class _AdminCursosScreenState extends State<AdminCursosScreen> {
  final ApiService _apiService = ApiService();
  List<Curso> _cursos = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _cargarCursos();
  }

  Future<void> _cargarCursos() async {
    setState(() => _isLoading = true);
    try {
      final cursos = await _apiService.fetchCursos();
      setState(() {
        _cursos = cursos;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  void _mostrarDialogoCrear() async {
    // Cargamos los inspectores disponibles para el dropdown
    List<Usuario> inspectoresDisponibles = [];
    try {
      inspectoresDisponibles = await _apiService.fetchUsuariosPorRol('INSPECTOR');
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Error al cargar inspectores')));
      }
    }

    if (!mounted) return;

    final nombreController = TextEditingController();
    int? inspectorSeleccionado;
    bool isSubmitting = false;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setStateDialog) {
            return AlertDialog(
              title: const Text('Crear Curso y Asignar Inspector', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                      controller: nombreController,
                      decoration: const InputDecoration(labelText: 'Nombre del Curso (Ej. 2° Informática B Matutino)'),
                    ),
                    const SizedBox(height: 20),
                    DropdownButtonFormField<int?>(
                      value: inspectorSeleccionado,
                      decoration: const InputDecoration(labelText: 'Asignar Inspector (Opcional)'),
                      items: [
                        const DropdownMenuItem<int?>(value: null, child: Text('Sin asignar por ahora')),
                        ...inspectoresDisponibles.map((i) => DropdownMenuItem(value: i.id, child: Text(i.nombreCompleto)))
                      ],
                      onChanged: (val) => setStateDialog(() => inspectorSeleccionado = val),
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
                          if (nombreController.text.isEmpty) return;
                          
                          setStateDialog(() => isSubmitting = true);
                          try {
                            await _apiService.crearCurso(
                              nombreController.text.trim(),
                              inspectorSeleccionado,
                            );
                            if (context.mounted) {
                              Navigator.pop(context);
                              _cargarCursos();
                              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Curso guardado y asignado')));
                            }
                          } catch (e) {
                            setStateDialog(() => isSubmitting = false);
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
                            }
                          }
                        },
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.indigo, foregroundColor: Colors.white),
                  child: isSubmitting 
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) 
                    : const Text('Crear'),
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
        title: const Text('Cursos y Asignaciones', style: TextStyle(color: Colors.white)),
        backgroundColor: Colors.indigo,
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _cursos.isEmpty
              ? const Center(child: Text('No hay cursos registrados. Crea el primero.'))
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _cursos.length,
                  itemBuilder: (context, index) {
                    final curso = _cursos[index];
                    return Card(
                      elevation: 2,
                      margin: const EdgeInsets.only(bottom: 12),
                      child: ListTile(
                        leading: const CircleAvatar(
                          backgroundColor: Colors.indigo,
                          child: Icon(Icons.school, color: Colors.white),
                        ),
                        title: Text(curso.nombre, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                        subtitle: Text('Jornada: ${curso.jornada}\nInspector: ${curso.inspectorNombre ?? 'Sin asignar'}'),
                        isThreeLine: true,
                      ),
                    );
                  },
                ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _mostrarDialogoCrear,
        backgroundColor: Colors.indigo,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add),
        label: const Text('Agregar Curso'),
      ),
    );
  }
}