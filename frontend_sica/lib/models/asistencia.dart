class Asistencia {
  final int id;
  final String estudianteUuid;
  final String cameraId;
  final double timestamp;
  final String bloqueHorario;
  final String estado;
  final String fechaRegistro;

  Asistencia({
    required this.id,
    required this.estudianteUuid,
    required this.cameraId,
    required this.timestamp,
    required this.bloqueHorario,
    required this.estado,
    required this.fechaRegistro,
  });

  factory Asistencia.fromJson(Map<String, dynamic> json) {
    return Asistencia(
      id: json['id'],
      estudianteUuid: json['estudiante_uuid'],
      cameraId: json['camera_id'],
      // Usamos .toDouble() para evitar errores si Python envía un entero en lugar de decimal
      timestamp: json['timestamp'].toDouble(), 
      bloqueHorario: json['bloque_horario'],
      estado: json['estado'],
      fechaRegistro: json['fecha_registro'],
    );
  }
}