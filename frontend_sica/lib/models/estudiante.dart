class Estudiante {
  final int id;
  final String uuid;
  final String nombreCompleto;
  final int? cursoId;
  final String cursoNombre;
  final int? representanteId;
  final String representanteNombre;
  
  // NUEVAS VARIABLES PARA LA EXPOSICIÓN
  final String ultimoEstado;
  final String ultimaHora;

  Estudiante({
    required this.id,
    required this.uuid,
    required this.nombreCompleto,
    this.cursoId,
    required this.cursoNombre,
    this.representanteId,
    required this.representanteNombre,
    this.ultimoEstado = "AUSENTE",
    this.ultimaHora = "--:--",
  });

  factory Estudiante.fromJson(Map<String, dynamic> json) {
    return Estudiante(
      id: json['id'],
      uuid: json['uuid'],
      nombreCompleto: json['nombre_completo'],
      cursoId: json['curso_id'],
      cursoNombre: json['curso_nombre'],
      representanteId: json['representante_id'],
      representanteNombre: json['representante_nombre'],
      ultimoEstado: json['ultimo_estado'] ?? 'AUSENTE',
      ultimaHora: json['ultima_hora'] ?? '--:--',
    );
  }
}