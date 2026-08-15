class Estudiante {
  final int id;
  final String uuid;
  final String nombreCompleto;
  final int cursoId;
  final String cursoNombre;
  final int? representanteId;
  final String representanteNombre;

  Estudiante({
    required this.id,
    required this.uuid,
    required this.nombreCompleto,
    required this.cursoId,
    required this.cursoNombre,
    this.representanteId,
    required this.representanteNombre,
  });

  factory Estudiante.fromJson(Map<String, dynamic> json) {
    return Estudiante(
      id: json['id'],
      uuid: json['uuid'],
      nombreCompleto: json['nombre_completo'],
      cursoId: json['curso_id'] ?? 0,
      cursoNombre: json['curso_nombre'] ?? 'Desconocido',
      representanteId: json['representante_id'],
      representanteNombre: json['representante_nombre'] ?? 'Sin Asignar',
    );
  }
}