import 'package:flutter/material.dart';
import 'dashboard_screen.dart';
import 'cameras_screen.dart';
import 'notifications_screen.dart';
import 'profile_screen.dart';

class MainScreen extends StatefulWidget {
  final String rol;
  final String email;

  const MainScreen({super.key, required this.rol, required this.email});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _currentIndex = 0;
  late final List<Widget> _screens;
  late final List<BottomNavigationBarItem> _navItems;

  @override
  void initState() {
    super.initState();
    _initializeScreens();
  }

  void _initializeScreens() {
    _screens = [];
    _navItems = [];

    final rolLower = widget.rol.toLowerCase();

    // Administrador, Rector e Inspector ven todo.
    // Docente no ve Cámaras.
    // Representante no ve Dashboard ni Cámaras.

    final canSeeDashboard = rolLower != 'representante';
    final canSeeCameras = [
      'administrador',
      'rector',
      'inspector',
    ].contains(rolLower);

    if (canSeeDashboard) {
      _screens.add(DashboardScreen(rol: widget.rol, email: widget.email));
      _navItems.add(
        const BottomNavigationBarItem(
          icon: Icon(Icons.dashboard),
          label: 'Dashboard',
        ),
      );
    }

    if (canSeeCameras) {
      _screens.add(const CamerasScreen());
      _navItems.add(
        const BottomNavigationBarItem(
          icon: Icon(Icons.videocam),
          label: 'Cámaras',
        ),
      );
    }

    // Todos ven Notificaciones y Perfil
    _screens.add(const NotificationsScreen());
    _navItems.add(
      const BottomNavigationBarItem(
        icon: Icon(Icons.notifications),
        label: 'Alertas',
      ),
    );

    _screens.add(ProfileScreen(rol: widget.rol, email: widget.email));
    _navItems.add(
      const BottomNavigationBarItem(icon: Icon(Icons.person), label: 'Perfil'),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _currentIndex, children: _screens),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        type: BottomNavigationBarType.fixed,
        backgroundColor: Colors.white,
        selectedItemColor: Colors.blue.shade900,
        unselectedItemColor: Colors.grey,
        items: _navItems,
      ),
    );
  }
}
