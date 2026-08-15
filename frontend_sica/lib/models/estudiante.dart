class Estudiante {
  final int id;
  final String uuid;
  final String nombreCompleto;
  final int cursoId;
  final String cursoNombre;

  Estudiante({
    required this.id,
    required this.uuid,
    required this.nombreCompleto,
    required this.cursoId,
    required this.cursoNombre,
  });

  factory Estudiante.fromJson(Map<String, dynamic> json) {
    return Estudiante(
      id: json['id'],
      uuid: json['uuid'],
      nombreCompleto: json['nombre_completo'],
      cursoId: json['curso_id'],
      cursoNombre: json['curso_nombre'],
    );
  }
}