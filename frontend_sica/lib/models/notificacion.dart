class NotificacionUsuario {
  final int id;
  final bool leida;
  final String? fechaLectura;
  final int notificacionId;
  final String titulo;
  final String mensaje;
  final String tipo;
  final String fechaCreacion;
  final String emisorNombre;

  NotificacionUsuario({
    required this.id,
    required this.leida,
    this.fechaLectura,
    required this.notificacionId,
    required this.titulo,
    required this.mensaje,
    required this.tipo,
    required this.fechaCreacion,
    required this.emisorNombre,
  });

  factory NotificacionUsuario.fromJson(Map<String, dynamic> json) {
    return NotificacionUsuario(
      id: json['id'],
      leida: json['leida'],
      fechaLectura: json['fecha_lectura'],
      notificacionId: json['notificacion_id'],
      titulo: json['titulo'],
      mensaje: json['mensaje'],
      tipo: json['tipo'],
      fechaCreacion: json['fecha_creacion'],
      emisorNombre: json['emisor_nombre'],
    );
  }
}