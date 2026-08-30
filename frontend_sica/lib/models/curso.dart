class Curso {
  final int id;
  final String nombre;
  final int? inspectorId;
  final String? inspectorNombre;
  final String? jornada;

  Curso({
    required this.id,
    required this.nombre,
    this.inspectorId,
    this.inspectorNombre,
    this.jornada,
  });

  factory Curso.fromJson(Map<String, dynamic> json) {
    return Curso(
      id: json['id'],
      nombre: json['nombre'],
      inspectorId: json['inspector_id'],
      // Proveemos valores por defecto seguros en caso de valores nulos
      inspectorNombre: json['inspector_nombre'] ?? 'Sin Asignar',
      jornada: json['jornada'] ?? 'Matutino', 
    );
  }
}