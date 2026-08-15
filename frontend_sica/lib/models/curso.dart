class Curso {
  final int id;
  final String nombre;
  final String jornada;

  Curso({required this.id, required this.nombre, required this.jornada});

  factory Curso.fromJson(Map<String, dynamic> json) {
    String nombreCurso = json['nombre'] ?? '';
    
    // Lógica para derivar la jornada automáticamente a partir del nombre del curso
    // Ejemplo: Si el nombre es "2° Informática B Matutino", la jornada será "Matutina"
    String jornadaDerivada = "Desconocida";
    String nombreLower = nombreCurso.toLowerCase();
    
    if (nombreLower.contains('matutin')) {
      jornadaDerivada = "Matutina";
    } else if (nombreLower.contains('vespertin')) {
      jornadaDerivada = "Vespertina";
    } else if (nombreLower.contains('nocturn')) {
      jornadaDerivada = "Nocturna";
    }

    return Curso(
      id: json['id'],
      nombre: nombreCurso,
      // Si el backend envía la jornada explícitamente, la usamos. Si no, usamos la derivada.
      jornada: json.containsKey('jornada') ? json['jornada'] : jornadaDerivada,
    );
  }
}