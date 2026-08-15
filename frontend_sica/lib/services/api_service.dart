import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/curso.dart';
import '../models/estudiante.dart';
import '../models/dashboard_metrics.dart';

class ApiService {
  static const String baseUrl = "http://127.0.0.1:8000/api/v1";

  /// Función auxiliar para obtener las cabeceras con el Token JWT
  Future<Map<String, String>> _getHeaders() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('token') ?? '';
    return {
      "Content-Type": "application/json",
      "Authorization": "Bearer $token", // Aquí inyectamos el JWT de seguridad
    };
  }

  /// Obtiene las métricas y la tabla de asistencias para el Dashboard
  Future<DashboardMetrics> fetchDashboardMetrics() async {
    final headers = await _getHeaders();
    final response = await http.get(Uri.parse('$baseUrl/dashboard/'), headers: headers);

    if (response.statusCode == 200) {
      final Map<String, dynamic> jsonResponse = json.decode(response.body);
      return DashboardMetrics.fromJson(jsonResponse);
    } else {
      throw Exception('Error al cargar métricas: ${response.statusCode}');
    }
  }

  /// Obtiene la lista de todos los estudiantes registrados
  Future<List<Estudiante>> fetchEstudiantes() async {
    final headers = await _getHeaders();
    final response = await http.get(Uri.parse('$baseUrl/estudiantes/'), headers: headers);

    if (response.statusCode == 200) {
      Iterable jsonList = json.decode(response.body);
      return jsonList.map((model) => Estudiante.fromJson(model)).toList();
    } else {
      throw Exception('Error al cargar estudiantes: ${response.statusCode}');
    }
  }

  /// Obtiene la lista de cursos disponibles (Requerido por el Inspector)
  Future<List<Curso>> fetchCursos() async {
    final headers = await _getHeaders();
    final response = await http.get(Uri.parse('$baseUrl/cursos/'), headers: headers);

    if (response.statusCode == 200) {
      Iterable jsonList = json.decode(response.body);
      return jsonList.map((model) => Curso.fromJson(model)).toList();
    } else {
      throw Exception('Error al cargar los cursos: ${response.statusCode}');
    }
  }

  /// Crea un nuevo estudiante enviando un JSON mediante POST
  Future<bool> crearEstudiante(String uuid, String nombreCompleto, int cursoId) async {
    final headers = await _getHeaders();
    final response = await http.post(
      Uri.parse('$baseUrl/estudiantes/nuevo'),
      headers: headers,
      body: json.encode({
        "uuid": uuid,
        "nombre_completo": nombreCompleto,
        "curso_id": cursoId,
      }),
    );

    if (response.statusCode == 200) {
      final jsonResponse = json.decode(response.body);
      if (jsonResponse.containsKey("error")) {
        throw Exception(jsonResponse["error"]);
      }
      return true;
    } else {
      throw Exception('Error de red al crear el estudiante');
    }
  }
}