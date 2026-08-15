import 'asistencia.dart';

class DashboardMetrics {
  final int totalPresentes;
  final int totalIntrusos;
  final List<Asistencia> asistencias;

  DashboardMetrics({
    required this.totalPresentes,
    required this.totalIntrusos,
    required this.asistencias,
  });

  factory DashboardMetrics.fromJson(Map<String, dynamic> json) {
    // Convertimos la lista JSON de asistencias en una lista de objetos Asistencia de Dart
    var asistenciasList = json['asistencias'] as List;
    List<Asistencia> asistenciasMapeadas = asistenciasList.map((i) => Asistencia.fromJson(i)).toList();

    return DashboardMetrics(
      totalPresentes: json['total_presentes'],
      totalIntrusos: json['total_intrusos'],
      asistencias: asistenciasMapeadas,
    );
  }
}