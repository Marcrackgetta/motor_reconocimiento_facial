import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart'; // Nos permite usar kIsWeb y debugPrint
import 'api_service.dart';

class PushNotificationService {
  static final FirebaseMessaging _firebaseMessaging = FirebaseMessaging.instance;
  static final ApiService _apiService = ApiService();

  static Future<void> iniciarYRegistrarToken() async {
    // 1. Solicitar permisos al usuario (El navegador mostrará un aviso: "¿Permitir notificaciones?")
    NotificationSettings settings = await _firebaseMessaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      debugPrint('[FCM] Permiso concedido por el usuario.');
      
      try {
        // 2. Obtener el Token único que identifica a este navegador/computadora
        String? token = await _firebaseMessaging.getToken();
        
        if (token != null) {
          debugPrint('[FCM] Token generado correctamente: $token');
          
          // 3. Determinar la plataforma para enviarla al backend
          String plataforma = kIsWeb ? 'WEB' : 'ESCRITORIO_MOVIL';
          
          // 4. Enviar el token a PostgreSQL a través de FastAPI
          await _apiService.registrarTokenFCM(token, plataforma);
          debugPrint('[FCM] Token guardado en el backend exitosamente.');
        }
      } catch (e) {
        debugPrint('[FCM] Error obteniendo el token FCM: $e');
      }
    } else {
      debugPrint('[FCM] El usuario denegó los permisos de notificación.');
    }

    // 5. Escuchar notificaciones silenciosas cuando la aplicación está abierta (Primer plano)
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      debugPrint('[FCM] ¡Notificación recibida en primer plano!');
      if (message.notification != null) {
        debugPrint('Título: ${message.notification!.title}');
        debugPrint('Cuerpo: ${message.notification!.body}');
      }
    });
  }
}