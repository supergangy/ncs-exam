library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../widgets.dart';
import 'search_screen.dart';
import 'keywords_screen.dart';
import 'marks_screen.dart';
import 'stats_screen.dart';
import 'settings_screen.dart';

class MoreScreen extends StatefulWidget {
  const MoreScreen({super.key});
  @override
  State<MoreScreen> createState() => _MoreScreenState();
}

class _MoreScreenState extends State<MoreScreen> {
  @override
  Widget build(BuildContext context) {
    final repo = Repo.instance;
    final markCount = Store.instance.mark.length;

    Widget row(String title, String subtitle, Widget screen, {int? count}) => RowTile(
          title: title,
          subtitle: subtitle,
          trailing: count != null && count > 0
              ? Text('$count', style: const TextStyle(fontWeight: FontWeight.w700))
              : null,
          onTap: () => Navigator.of(context)
              .push(MaterialPageRoute(builder: (_) => screen))
              .then((_) => setState(() {})),
        );

    return Scaffold(
      appBar: AppBar(title: const Text('더보기')),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          row('검색', '발문·선지·해설을 가로질러 찾습니다', const SearchScreen()),
          row('키워드', '과목을 가로지르는 용어', const KeywordsScreen(),
              count: repo.bank.keywords.length),
          row('북마크 · 확인 필요', '표시해 둔 문항', const MarksScreen(), count: markCount),
          row('통계', '과목별 정답률', const StatsScreen()),
          row('설정', '기록 관리 · 관리자 모드', const SettingsScreen()),
        ],
      ),
    );
  }
}
