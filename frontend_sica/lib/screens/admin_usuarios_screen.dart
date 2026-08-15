import 'package:flutter/material.dart';
import '../models/usuario.dart';
import '../services/api_service.dart';

class AdminUsuariosScreen extends StatefulWidget {
  const AdminUsuariosScreen({super.key});

  @override
  State<AdminUsuariosScreen> createState() => _AdminUsuariosScreenState();
}

class _AdminUsuariosScreenState extends State<AdminUsuariosScreen> {
  final ApiService _apiService = ApiService();
  List<Usuario> _usuarios = [];
  bool _isLoading = true;
  String _errorMessage = '';

  @override
  void initState() {
    super.initState();
    _cargarUsuarios();
  }

  Future<void> _cargarUsuarios() async {
    setState(() => _isLoading = true);
    try {
      final usuarios = await _apiService.fetchUsuarios();
      setState(() {
        _usuarios = usuarios;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  void _mostrarDialogoCrear() {
    final emailController = TextEditingController();
    final passwordController = TextEditingController();
    final nombreController = TextEditingController();
    String rolSeleccionado = 'REPRESENTANTE';
    bool isSubmitting = false;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setStateDialog) {
            return AlertDialog(
              title: const Text('Registrar Nuevo Usuario'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                      controller: nombreController,
                      decoration: const InputDecoration(labelText: 'Nombre Completo'),
                    ),
                    TextField(
                      controller: emailController,
                      keyboardType: TextInputType.emailAddress,
                      decoration: const InputDecoration(labelText: 'Correo Electrónico'),
                    ),
                    TextField(
                      controller: passwordController,
                      obscureText: true,
                      decoration: const InputDecoration(labelText: 'Contraseña temporal'),
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<String>(
                      value: rolSeleccionado,
                      decoration: const InputDecoration(labelText: 'Rango / Rol'),
                      items: ['REPRESENTANTE', 'INSPECTOR', 'ADMINISTRADOR']
                          .map((r) => DropdownMenuItem(value: r, child: Text(r)))
                          .toList(),
                      onChanged: (val) {
                        if (val != null) setStateDialog(() => rolSeleccionado = val);
                      },
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
                          if (emailController.text.isEmpty || passwordController.text.isEmpty || nombreController.text.isEmpty) {
                            return;
                          }
                          setStateDialog(() => isSubmitting = true);
                          try {
                            await _apiService.registrarUsuario(
                              emailController.text.trim(),
                              passwordController.text.trim(),
                              rolSeleccionado,
                              nombreController.text.trim(),
                            );
                            if (context.mounted) {
                              Navigator.pop(context); // Cierra el modal
                              _cargarUsuarios(); // Recarga la lista de usuarios
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Usuario creado exitosamente')),
                              );
                            }
                          } catch (e) {
                            setStateDialog(() => isSubmitting = false);
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text(e.toString().replaceAll('Exception: ', ''))),
                              );
                            }
                          }
                        },
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.blueGrey[800], foregroundColor: Colors.white),
                  child: isSubmitting ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : const Text('Guardar'),
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
      appBar: AppBar(
        title: const Text('Gestión de Usuarios', style: TextStyle(color: Colors.white)),
        backgroundColor: Colors.blueGrey[800],
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _errorMessage.isNotEmpty
              ? Center(child: Text(_errorMessage, style: const TextStyle(color: Colors.red)))
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _usuarios.length,
                  itemBuilder: (context, index) {
                    final usuario = _usuarios[index];
                    return Card(
                      elevation: 2,
                      margin: const EdgeInsets.only(bottom: 10),
                      child: ListTile(
                        leading: CircleAvatar(
                          backgroundColor: usuario.rol == 'ADMINISTRADOR' ? Colors.blueGrey : (usuario.rol == 'INSPECTOR' ? Colors.teal : Colors.amber),
                          child: Icon(
                            usuario.rol == 'ADMINISTRADOR' ? Icons.security : (usuario.rol == 'INSPECTOR' ? Icons.badge : Icons.family_restroom),
                            color: Colors.white,
                          ),
                        ),
                        title: Text(usuario.nombreCompleto, style: const TextStyle(fontWeight: FontWeight.bold)),
                        subtitle: Text('${usuario.email} • ${usuario.rol}'),
                        trailing: Switch(
                          value: usuario.isActive,
                          onChanged: (val) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Función de activar/desactivar pendiente en backend')),
                            );
                          },
                        ),
                      ),
                    );
                  },
                ),
      floatingActionButton: FloatingActionButton(
        onPressed: _mostrarDialogoCrear,
        backgroundColor: Colors.blueGrey[800],
        foregroundColor: Colors.white,
        child: const Icon(Icons.add),
      ),
    );
  }
}