import '../models/estudiante.dart';

class ApiService {
  // 1. Obtener la lista de estudiantes
  Future<List<Estudiante>> fetchEstudiantes() async {
    return [];
  }

  // 2. Registrar Token FCM para notificaciones Push
  Future<void> registrarTokenFCM(String token, String plataforma) async {
    // Lógica de Firebase pendiente
  }

  // 3. Obtener el historial de notificaciones (Bandeja)
  // Usamos 'dynamic' para silenciar el conflicto con el modelo antiguo 'NotificacionUsuario'
  Future<dynamic> fetchMisNotificaciones() async {
    return [];
  }

  // 4. Marcar notificación como leída
  Future<void> marcarNotificacionLeida(dynamic id) async {
    // Lógica de Firebase pendiente
  }

  // 5. Envío de justificaciones
  Future<void> enviarNotificacion(dynamic arg1, dynamic arg2, dynamic arg3, dynamic arg4, dynamic arg5) async {
    // Lógica de Firebase pendiente
  }
  
  Future<void> enviarJustificacion(dynamic datos) async {
    // Lógica de Firebase pendiente
  }
  
  // 6. Obtener el historial de asistencia del estudiante
  Future<List<dynamic>> fetchHistorial(String uuid) async {
    return [];
  }

  // 7. Métricas del Dashboard 
  Future<dynamic> fetchDashboardMetrics() async {
    return {};
  }
}