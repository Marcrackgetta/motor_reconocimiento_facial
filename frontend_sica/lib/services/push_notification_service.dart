import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_database/firebase_database.dart';
import 'package:flutter/material.dart';
import '../main.dart'; // Importamos el main para usar la llave global

class PushNotificationService {
  final FirebaseMessaging _fcm = FirebaseMessaging.instance;

  Future<void> initialize() async {
    NotificationSettings settings = await _fcm.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      debugPrint('Permisos de notificación concedidos.');
      
      String? token = await _fcm.getToken();
      if (token != null) {
        await _saveTokenToDatabase(token);
      }

      _fcm.onTokenRefresh.listen(_saveTokenToDatabase);

      // Maneja las notificaciones cuando la app ESTÁ ABIERTA
      FirebaseMessaging.onMessage.listen((RemoteMessage message) {
        final title = message.notification?.title ?? 'Nueva Alerta';
        final body = message.notification?.body ?? '';
        
        debugPrint('Mensaje recibido en primer plano: $title');

        // Dispara una tarjeta emergente visual dentro de la app
        scaffoldMessengerKey.currentState?.showSnackBar(
          SnackBar(
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.notifications_active, color: Colors.amber),
                    const SizedBox(width: 8),
                    Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16))),
                  ],
                ),
                const SizedBox(height: 6),
                Text(body, style: const TextStyle(fontSize: 14)),
              ],
            ),
            backgroundColor: Colors.blueGrey[900],
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            margin: const EdgeInsets.all(20),
            duration: const Duration(seconds: 6),
          ),
        );
      });
    }
  }

  Future<void> _saveTokenToDatabase(String token) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user != null) {
      final dbRef = FirebaseDatabase.instance.ref();
      await dbRef.child('Usuarios/${user.uid}').update({
        'fcm_token': token,
      });
    }
  }
}