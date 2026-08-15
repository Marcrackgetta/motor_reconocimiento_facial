import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class AuthService {
  static const String baseUrl = "http://127.0.0.1:8000/api/v1/auth";

  /// Envía las credenciales al backend y guarda el JWT si es exitoso.
  /// Retorna el ROL del usuario como un String (ej. 'ADMINISTRADOR')
  Future<String> login(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/login'),
        headers: {"Content-Type": "application/json"},
        body: json.encode({
          "email": email,
          "password": password,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        
        // Instanciamos SharedPreferences para guardar datos en el dispositivo
        final prefs = await SharedPreferences.getInstance();
        
        // Guardamos el token y los datos del usuario
        await prefs.setString('token', data['access_token']);
        await prefs.setString('rol', data['rol']);
        await prefs.setString('nombre', data['nombre_completo']);
        
        // Convertimos explícitamente a String para evitar errores de tipo
        return data['rol'].toString(); 
      } else if (response.statusCode == 401) {
        throw Exception('Correo o contraseña incorrectos');
      } else {
        throw Exception('Error del servidor: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('No se pudo conectar con el servidor SICA.');
    }
  }

  /// Borra el token guardado para cerrar la sesión
  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
  }

  /// Verifica si el usuario ya tiene un token guardado (sesión activa)
  Future<bool> isLoggedIn() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.containsKey('token');
  }
}