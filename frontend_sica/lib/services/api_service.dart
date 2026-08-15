import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/curso.dart';
import '../models/estudiante.dart';
import '../models/dashboard_metrics.dart';
import '../models/usuario.dart';

class ApiService {
  static const String baseUrl = "http://127.0.0.1:8000/api/v1";

  Future<Map<String, String>> _getHeaders() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('token') ?? '';
    return {
      "Content-Type": "application/json",
      "Authorization": "Bearer $token",
    };
  }

  Future<DashboardMetrics> fetchDashboardMetrics() async {
    final headers = await _getHeaders();
    final response = await http.get(Uri.parse('$baseUrl/dashboard/'), headers: headers);
    if (response.statusCode == 200) {
      return DashboardMetrics.fromJson(json.decode(response.body));
    } else {
      throw Exception('Error al cargar métricas');
    }
  }

  Future<List<Estudiante>> fetchEstudiantes() async {
    final headers = await _getHeaders();
    final response = await http.get(Uri.parse('$baseUrl/estudiantes/'), headers: headers);
    if (response.statusCode == 200) {
      Iterable jsonList = json.decode(response.body);
      return jsonList.map((model) => Estudiante.fromJson(model)).toList();
    } else {
      throw Exception('Error al cargar estudiantes');
    }
  }

  Future<List<Curso>> fetchCursos() async {
    final headers = await _getHeaders();
    final response = await http.get(Uri.parse('$baseUrl/cursos/'), headers: headers);
    if (response.statusCode == 200) {
      Iterable jsonList = json.decode(response.body);
      return jsonList.map((model) => Curso.fromJson(model)).toList();
    } else {
      throw Exception('Error al cargar los cursos');
    }
  }

  Future<List<Usuario>> fetchUsuarios() async {
    final headers = await _getHeaders();
    final response = await http.get(Uri.parse('$baseUrl/usuarios/'), headers: headers);
    if (response.statusCode == 200) {
      Iterable jsonList = json.decode(response.body);
      return jsonList.map((model) => Usuario.fromJson(model)).toList();
    } else {
      throw Exception('Error al cargar la lista de usuarios');
    }
  }

  Future<List<Usuario>> fetchUsuariosPorRol(String rol) async {
    final headers = await _getHeaders();
    final response = await http.get(Uri.parse('$baseUrl/usuarios/rol/$rol'), headers: headers);
    if (response.statusCode == 200) {
      Iterable jsonList = json.decode(response.body);
      return jsonList.map((model) => Usuario.fromJson(model)).toList();
    } else {
      throw Exception('Error al cargar usuarios por rol');
    }
  }

  Future<bool> registrarUsuario(String email, String password, String rol, String nombreCompleto) async {
    final headers = await _getHeaders();
    final response = await http.post(
      Uri.parse('$baseUrl/usuarios/registrar'),
      headers: headers,
      body: json.encode({"email": email, "password": password, "rol": rol, "nombre_completo": nombreCompleto}),
    );
    if (response.statusCode == 200) {
      return true;
    } else {
      final error = json.decode(response.body);
      throw Exception(error['detail'] ?? 'Error al registrar usuario');
    }
  }

  Future<bool> crearEstudiante(String uuid, String nombreCompleto, int cursoId, int? representanteId) async {
    final headers = await _getHeaders();
    final response = await http.post(
      Uri.parse('$baseUrl/estudiantes/nuevo'),
      headers: headers,
      body: json.encode({
        "uuid": uuid,
        "nombre_completo": nombreCompleto,
        "curso_id": cursoId,
        "representante_id": representanteId,
      }),
    );
    if (response.statusCode == 200) {
      return true;
    } else {
      throw Exception('Error al crear y asignar el estudiante');
    }
  }

  /// NUEVA FUNCIÓN: Crear Curso y Asignar Inspector
  Future<bool> crearCurso(String nombre, int? inspectorId) async {
    final headers = await _getHeaders();
    final response = await http.post(
      Uri.parse('$baseUrl/cursos/'),
      headers: headers,
      body: json.encode({
        "nombre": nombre,
        "inspector_id": inspectorId,
      }),
    );
    if (response.statusCode == 200) {
      return true;
    } else {
      throw Exception('Error al crear el curso');
    }
  }
}