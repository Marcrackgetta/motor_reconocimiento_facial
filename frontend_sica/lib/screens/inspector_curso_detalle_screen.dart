import 'package:flutter/material.dart';
import '../models/curso.dart';

class InspectorCursoDetalleScreen extends StatefulWidget {
  final Curso curso;

  const InspectorCursoDetalleScreen({super.key, required this.curso});

  @override
  State<InspectorCursoDetalleScreen> createState() => _InspectorCursoDetalleScreenState();
}

class _InspectorCursoDetalleScreenState extends State<InspectorCursoDetalleScreen> {
  // Opciones para el filtro de asistencia
  final List<String> _periodos = ['Diario', 'Semanal', 'Mensual', 'Anual'];
  String _periodoSeleccionado = 'Diario';

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        backgroundColor: Colors.grey[100],
        appBar: AppBar(
          title: const Text('Detalle del Curso', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          backgroundColor: Colors.teal[600],
          iconTheme: const IconThemeData(color: Colors.white),
          bottom: const TabBar(
            labelColor: Colors.white,
            unselectedLabelColor: Colors.white60,
            indicatorColor: Colors.white,
            indicatorWeight: 4,
            tabs: [
              Tab(icon: Icon(Icons.people), text: 'Lista del curso'),
              Tab(icon: Icon(Icons.fact_check), text: 'Registro asistencia'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _construirTabListaCurso(),
            _construirTabAsistencia(),
          ],
        ),
      ),
    );
  }

  // 1. PESTAÑA: LISTA DEL CURSO
  Widget _construirTabListaCurso() {
    return Column(
      children: [
        _construirCabeceraInformacion(widget.curso.nombre),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: 5, // Número estático para visualización temporal de UI
            itemBuilder: (context, index) {
              return Card(
                elevation: 1,
                margin: const EdgeInsets.only(bottom: 10),
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: Colors.grey[300],
                    child: const Icon(Icons.person, color: Colors.black54),
                  ),
                  title: Text('Estudiante ${index + 1}', style: const TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Text('ID: EST-00${index + 1}'),
                  trailing: const Icon(Icons.info_outline, color: Colors.teal),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  // 2. PESTAÑA: REGISTRO DE ASISTENCIA
  Widget _construirTabAsistencia() {
    return Column(
      children: [
        _construirCabeceraInformacion('Consultar Asistencia'),
        
        // Controles de Filtro y Exportación
        Container(
          color: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // Dropdown de Período
              Row(
                children: [
                  const Icon(Icons.calendar_month, color: Colors.black54),
                  const SizedBox(width: 8),
                  DropdownButton<String>(
                    value: _periodoSeleccionado,
                    underline: Container(),
                    style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.teal, fontSize: 16),
                    icon: const Icon(Icons.arrow_drop_down, color: Colors.teal),
                    items: _periodos.map((String value) {
                      return DropdownMenuItem<String>(
                        value: value,
                        child: Text(value),
                      );
                    }).toList(),
                    onChanged: (String? newValue) {
                      setState(() {
                        if (newValue != null) _periodoSeleccionado = newValue;
                      });
                    },
                  ),
                ],
              ),
              
              // Botón fantasma para futura exportación a Excel
              ElevatedButton.icon(
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Función de exportación a Excel en desarrollo.')),
                  );
                },
                icon: const Icon(Icons.download, size: 18),
                label: const Text('Excel'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.green[600], // Verde característico de Excel
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ],
          ),
        ),
        
        const Divider(height: 1),
        
        // Lista de Registros filtrados
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: 3, // Visualización temporal
            itemBuilder: (context, index) {
              return Card(
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                  side: BorderSide(color: Colors.grey[300]!),
                ),
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  leading: const Icon(Icons.check_circle, color: Colors.green),
                  title: const Text('Estudiante Ejemplo', style: TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: Text('Período: $_periodoSeleccionado \nCámara: Entrada Principal'),
                  isThreeLine: true,
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  // Widget de cabecera reutilizable para ambas pestañas
  Widget _construirCabeceraInformacion(String texto) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      color: Colors.teal[50],
      child: Text(
        texto.toUpperCase(),
        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.teal[900]),
        textAlign: TextAlign.center,
      ),
    );
  }
}