import 'package:flutter/material.dart';
import '../models/curso.dart';
import 'inspector_curso_detalle_screen.dart';

class InspectorCursosScreen extends StatelessWidget {
  final String jornada;
  final List<Curso> cursos;

  const InspectorCursosScreen({super.key, required this.jornada, required this.cursos});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: Text('Cursos - $jornada', style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
        backgroundColor: Colors.teal[600],
        iconTheme: const IconThemeData(color: Colors.white),
        elevation: 0,
      ),
      body: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: cursos.length,
        itemBuilder: (context, index) {
          final curso = cursos[index];
          
          return Card(
            elevation: 2,
            margin: const EdgeInsets.only(bottom: 12),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: ListTile(
              contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
              leading: CircleAvatar(
                backgroundColor: Colors.teal[100],
                child: Icon(Icons.school, color: Colors.teal[700]),
              ),
              title: Text(
                curso.nombre.toUpperCase(),
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              trailing: ElevatedButton(
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => InspectorCursoDetalleScreen(curso: curso),
                    ),
                  );
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.teal[600],
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                ),
                child: const Text('VER CURSO'),
              ),
            ),
          );
        },
      ),
    );
  }
}