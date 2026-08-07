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
      // 글자 크기는 여기 한 곳에서 건다. 크기가 화면마다 코드에 박혀 있어
      // 개별로는 손댈 수 없고, MediaQuery 를 타면 flutter_html 이 그리는
      // 자료·해설까지 함께 커진다.
      builder: (ctx, child) => ListenableBuilder(
        listenable: Store.instance,
        builder: (ctx2, _) {
          final mq = MediaQuery.of(ctx2);
          return MediaQuery(
            data: mq.copyWith(
              textScaler: TextScaler.linear(
                  mq.textScaler.scale(1) * Store.instance.textScale),
            ),
            child: child ?? const SizedBox.shrink(),
          );
        },
      ),
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
    _ready = _boot();
  }

  Future<void> _boot() async {
    await Future.wait([Repo.instance.load(), Store.instance.load()]);
    // 관리자 모드를 켠 채로 앱을 껐다면 다시 켤 때도 위험도·이유서가 나와야 한다.
    // 이걸 빠뜨리면 설정에서 한 번 더 토글해야만 보였다.
    if (Store.instance.admin) {
      try {
        await Repo.instance.loadAdmin();
      } catch (_) {
        // 에셋이 없으면 배지만 안 나온다. 앱이 멎을 이유는 아니다.
      }
    }
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

class _ShellState extends State<_Shell> with WidgetsBindingObserver {
  int _tab = 0;

  // const 목록이면 안 된다 — 위젯이 같으면 Flutter 가 아예 갱신을 건너뛰어
  // 탭 다섯 개가 부팅 때 숫자에 얼어붙는다.
  final _screens = <Widget>[
    const HomeScreen(),
    const ExamsScreen(),
    const ReviewScreen(),
    const WrongScreen(),
    const MoreScreen(),
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // 홈 버튼으로 나가면 미뤄 둔 저장이 남아 있을 수 있다. 여기서 흘려보낸다.
    if (state == AppLifecycleState.paused || state == AppLifecycleState.hidden) {
      Store.instance.flush();
    }
  }

  @override
  Widget build(BuildContext context) {
    final repo = Repo.instance;
    return Scaffold(
      body: IndexedStack(index: _tab, children: _screens),
      bottomNavigationBar: ListenableBuilder(
        listenable: Store.instance,
        builder: (context, _) {
          final ids = repo.bank.items.map((i) => i.id);
          final due = Store.instance.dueIds(ids).length;
          final wrong = Store.instance.wrongCount(ids);
          final sitting = Store.instance.sit != null;
          return NavigationBar(
            selectedIndex: _tab,
            onDestinationSelected: (i) => setState(() => _tab = i),
            destinations: [
              const NavigationDestination(icon: Icon(Icons.home_outlined),
                  selectedIcon: Icon(Icons.home), label: '홈'),
              NavigationDestination(
                icon: Badge(isLabelVisible: sitting, child: const Icon(Icons.edit_note_outlined)),
                selectedIcon: Badge(isLabelVisible: sitting, child: const Icon(Icons.edit_note)),
                label: '회차',
              ),
              NavigationDestination(
                icon: Badge(label: Text('$due'), isLabelVisible: due > 0,
                    child: const Icon(Icons.refresh_outlined)),
                selectedIcon: Badge(label: Text('$due'), isLabelVisible: due > 0,
                    child: const Icon(Icons.refresh)),
                label: '복습',
              ),
              NavigationDestination(
                icon: Badge(label: Text('$wrong'), isLabelVisible: wrong > 0,
                    child: const Icon(Icons.error_outline)),
                selectedIcon: Badge(label: Text('$wrong'), isLabelVisible: wrong > 0,
                    child: const Icon(Icons.error)),
                label: '오답',
              ),
              const NavigationDestination(icon: Icon(Icons.more_horiz),
                  selectedIcon: Icon(Icons.more_horiz), label: '더보기'),
            ],
          );
        },
      ),
    );
  }
}
