library;

import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../theme.dart';
import '../widgets.dart';

// 암호는 평문으로 두지 않는다. 웹판(app/app.js)과 같은 해시 — 그래도 보안 장치는 아니다.
const _adminHash =
    'aa790a259912f75b16643edc4862b87fc60ca9cbf4c359da002a56c7294257f4';

String _sha256Hex(String s) => sha256.convert(utf8.encode(s)).toString();

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _pwCtl = TextEditingController();
  String _btnLabel = '켜기';
  bool _busy = false;

  @override
  void dispose() {
    _pwCtl.dispose();
    super.dispose();
  }

  Future<void> _turnOn() async {
    if (_busy) return;
    final v = _pwCtl.text;
    if (_sha256Hex(v) != _adminHash) {
      setState(() => _btnLabel = '암호가 다릅니다');
      await Future.delayed(const Duration(milliseconds: 1400));
      if (mounted) setState(() => _btnLabel = '켜기');
      return;
    }
    setState(() => _busy = true);
    try {
      await Store.instance.setAdmin(true);
      await Repo.instance.loadAdmin();
    } catch (_) {
      // 파일이 없으면 배지만 안 나온다. 저장이 실패해도 버튼은 풀어 줘야 한다.
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _turnOff() async {
    await Store.instance.setAdmin(false);
    if (!mounted) return;
    setState(() {});
  }

  Future<void> _resetAll() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('기록 전부 지우기'),
        content: const Text('푼 기록·오답노트·복습 일정이 모두 사라집니다. 계속할까요?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('취소')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('지우기')),
        ],
      ),
    );
    if (ok == true) {
      await Store.instance.reset();
      if (!mounted) return;
      setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final repo = Repo.instance;
    final admin = Store.instance.admin;
    final n = Store.instance.att.length;

    return Scaffold(
      appBar: AppBar(title: const Text('설정')),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          const SectionTitle('관리자 모드'),
          _field(
            c,
            child: admin
                ? Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('켜져 있습니다',
                        style: TextStyle(color: c.ink, fontWeight: FontWeight.w600)),
                    const SizedBox(height: 4),
                    Text('문제 화면에 위험도와 출제 이유서가 함께 나옵니다.',
                        style: TextStyle(color: c.faint, fontSize: 12.5)),
                    const SizedBox(height: 10),
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton(onPressed: _turnOff, child: const Text('끄기')),
                    ),
                  ])
                : Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('관리자 암호',
                        style: TextStyle(color: c.ink, fontWeight: FontWeight.w600)),
                    const SizedBox(height: 6),
                    TextField(
                      controller: _pwCtl,
                      obscureText: true,
                      autocorrect: false,
                      decoration: const InputDecoration(
                          hintText: '암호를 입력하세요', border: OutlineInputBorder()),
                      onSubmitted: (_) => _turnOn(),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '출제자용입니다. 문항의 위험도(low·mid·high)와 '
                      '출제 이유서(근거·설계·함정·검증)를 문제 화면에서 함께 봅니다.\n'
                      '주의 — 이것은 화면 표시를 가리는 장치일 뿐 보안 장치가 아닙니다. '
                      '앱 파일을 뜯을 줄 아는 사람은 우회할 수 있습니다.',
                      style: TextStyle(color: c.faint, fontSize: 12.5),
                    ),
                    const SizedBox(height: 10),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton(
                          onPressed: _busy ? null : _turnOn, child: Text(_btnLabel)),
                    ),
                  ]),
          ),
          const SectionTitle('기록'),
          _field(
            c,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('이 기기에 $n문항의 기록이 있습니다',
                  style: TextStyle(color: c.ink, fontWeight: FontWeight.w600)),
              const SizedBox(height: 4),
              Text(
                '푼 기록과 복습 일정은 이 기기에만 저장됩니다. 서버로 올라가지 않으므로 '
                '다른 기기와 공유되지 않고, 앱을 지우면 함께 사라집니다.',
                style: TextStyle(color: c.faint, fontSize: 12.5),
              ),
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child:
                    OutlinedButton(onPressed: _resetAll, child: const Text('기록 전부 지우기')),
              ),
            ]),
          ),
          const SectionTitle('문항'),
          _field(
            c,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${repo.bank.n}문항 · 키워드 ${repo.bank.keywords.length}개',
                  style: TextStyle(color: c.ink, fontWeight: FontWeight.w600)),
              const SizedBox(height: 4),
              Text(
                '문항은 앱 안에 들어 있습니다. 비행기 모드에서도 전부 풀립니다.\n'
                '모두 자작 문항이며 기출을 복원한 것이 아닙니다.',
                style: TextStyle(color: c.faint, fontSize: 12.5),
              ),
            ]),
          ),
        ],
      ),
    );
  }

  Widget _field(AppColors c, {required Widget child}) => Container(
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: 4),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            color: c.card,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: c.line)),
        child: child,
      );
}
