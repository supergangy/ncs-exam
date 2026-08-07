library;

import 'package:flutter/material.dart';
import 'repo.dart';
import 'store.dart';
import 'theme.dart';
import 'screens/home_screen.dart';
import 'screens/exams_screen.dart';
import 'screens/review_screen.dart';
import 'screens/wrong_screen.dart';
import 'screens/more_screen.dart';

void main() {
  runApp(const NcsBankApp());
}

class NcsBankApp extends StatelessWidget {
  const NcsBankApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'NCS 기출은행',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(Brightness.light),
      darkTheme: buildTheme(Brightness.dark),
      themeMode: ThemeMode.system,
      home: const _Boot(),
    );
  }
}

class _Boot extends StatefulWidget {
  const _Boot();
  @override
  State<_Boot> createState() => _BootState();
}

class _BootState extends State<_Boot> {
  late final Future<void> _ready;

  @override
  void initState() {
    super.initState();
    _ready = Future.wait([Repo.instance.load(), Store.instance.load()]);
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<void>(
      future: _ready,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }
        if (snap.hasError) {
          return Scaffold(
            body: Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text('문항을 불러오지 못했습니다.\n${snap.error}', textAlign: TextAlign.center),
              ),
            ),
          );
        }
        return const _Shell();
      },
    );
  }
}

class _Shell extends StatefulWidget {
  const _Shell();
  @override
  State<_Shell> createState() => _ShellState();
}

class _ShellState extends State<_Shell> {
  int _tab = 0;

  static const _screens = [
    HomeScreen(),
    ExamsScreen(),
    ReviewScreen(),
    WrongScreen(),
    MoreScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _tab, children: _screens),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home), label: '홈'),
          NavigationDestination(icon: Icon(Icons.edit_note_outlined),
              selectedIcon: Icon(Icons.edit_note), label: '회차'),
          NavigationDestination(icon: Icon(Icons.refresh_outlined),
              selectedIcon: Icon(Icons.refresh), label: '복습'),
          NavigationDestination(icon: Icon(Icons.error_outline),
              selectedIcon: Icon(Icons.error), label: '오답'),
          NavigationDestination(icon: Icon(Icons.more_horiz),
              selectedIcon: Icon(Icons.more_horiz), label: '더보기'),
        ],
      ),
    );
  }
}
