class Usuario {
  final int id;
  final String email;
  final String rol;
  final String nombreCompleto;
  final bool isActive;

  Usuario({
    required this.id,
    required this.email,
    required this.rol,
    required this.nombreCompleto,
    required this.isActive,
  });

  factory Usuario.fromJson(Map<String, dynamic> json) {
    return Usuario(
      id: json['id'],
      email: json['email'],
      rol: json['rol'],
      nombreCompleto: json['nombre_completo'],
      isActive: json['is_active'] ?? true,
    );
  }
}