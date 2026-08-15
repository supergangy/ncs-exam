library;

import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import '../reminder.dart';
import '../reminder_plan.dart';
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

  // ───────────────────────────────────────────────────────── 백업·복원

  void _toast(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  Future<void> _exportBackup() async {
    final now = DateTime.now();
    final stamp = '${now.year}${now.month.toString().padLeft(2, '0')}'
        '${now.day.toString().padLeft(2, '0')}';
    try {
      final dir = await getTemporaryDirectory();
      final file = File('${dir.path}/ncsbank-backup-$stamp.json');
      await file.writeAsString(
          const JsonEncoder.withIndent('  ').convert(Store.instance.exportMap(now)));
      await Share.shareXFiles([XFile(file.path)],
          text: 'NCS 기출은행 기록 백업 — 새 기기에서 설정 › 기록 › 백업 불러오기');
    } catch (e) {
      _toast('내보내지 못했습니다: $e');
    }
  }

  Future<void> _importBackup() async {
    Backup backup;
    try {
      final picked = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['json'],
        withData: true,
      );
      if (picked == null || picked.files.isEmpty) return; // 취소
      final f = picked.files.single;
      final raw = f.bytes != null
          ? utf8.decode(f.bytes!)
          : await File(f.path!).readAsString();
      backup = readBackup(jsonDecode(raw));
    } on FormatException catch (e) {
      _toast(e.message);
      return;
    } catch (e) {
      _toast('백업을 읽지 못했습니다: $e');
      return;
    }

    if (!mounted) return;
    final cur = Store.instance.snapshot();
    final b = backup.data;
    final when = backup.at == null
        ? '만든 날짜 없음'
        : '${backup.at!.year}년 ${backup.at!.month}월 ${backup.at!.day}일';
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('백업 불러오기'),
        content: Column(mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('백업 · $when\n'
              '  ${b.attCount}문항 기록 · 회차 ${b.examCount}건 · 표시 ${b.markCount}건'),
          const SizedBox(height: 10),
          Text('지금\n'
              '  ${cur.attCount}문항 기록 · 회차 ${cur.examCount}건 · 표시 ${cur.markCount}건'),
          const SizedBox(height: 14),
          const Text('지금 기록은 전부 사라지고 백업으로 바뀝니다.'),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('취소')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, true), child: const Text('덮어쓰기')),
        ],
      ),
    );
    if (ok != true) return;

    await Store.instance.importAll(b);
    if (Store.instance.admin) {
      try {
        await Repo.instance.loadAdmin();
      } catch (_) {/* 배지만 안 나온다 */}
    }
    if (!mounted) return;
    setState(() {});
    _toast('${b.attCount}문항 기록을 되살렸습니다.');
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
          const SectionTitle('글자 크기'),
          _field(
            c,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Wrap(spacing: 8, runSpacing: 8, children: [
                for (final (label, v) in textScaleSteps)
                  ChipButton(
                    label: label,
                    on: (Store.instance.textScale - v).abs() < 0.01,
                    onTap: () async {
                      await Store.instance.setTextScale(v);
                      if (!mounted) return;
                      setState(() {});
                    },
                  ),
              ]),
              const SizedBox(height: 12),
              // 미리보기는 실제 발문과 같은 크기로 둔다 — 고르는 즉시 이만큼 커진다.
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                    color: c.bg, borderRadius: BorderRadius.circular(10)),
                child: Text(
                  '다음 자료에 대한 설명으로 옳은 것만을 <보기>에서 모두 고르면?',
                  style: TextStyle(
                      fontSize: 17, fontWeight: FontWeight.w600, color: c.ink, height: 1.5),
                ),
              ),
              const SizedBox(height: 6),
              Text('문제·지문·해설이 모두 이 배율로 나옵니다.',
                  style: TextStyle(color: c.faint, fontSize: 12.5)),
            ]),
          ),
          const SectionTitle('복습 알림'),
          _field(
            c,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(
                  child: Text(
                    Store.instance.remind
                        ? '매일 ${ReminderPlan.fromMinuteOfDay(Store.instance.remindAt).label} 에 알립니다'
                        : '꺼져 있습니다',
                    style: TextStyle(color: c.ink, fontWeight: FontWeight.w600),
                  ),
                ),
                Switch(value: Store.instance.remind, onChanged: _toggleRemind),
              ]),
              const SizedBox(height: 4),
              // 매일 「없습니다」가 오면 알림을 꺼 버린다. 쌓인 날에만 보낸다.
              Text('복습할 문항이 쌓인 날에만 옵니다. 없는 날은 오지 않습니다.',
                  style: TextStyle(color: c.faint, fontSize: 12.5)),
              if (Store.instance.remind) ...[
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    onPressed: _pickRemindTime,
                    child: const Text('시각 바꾸기'),
                  ),
                ),
              ],
            ]),
          ),
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
                '다른 기기와 공유되지 않고, 앱을 지우면 함께 사라집니다.\n'
                '폰을 바꾸기 전에 백업을 내보내 두세요.',
                style: TextStyle(color: c.faint, fontSize: 12.5),
              ),
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                    onPressed: _exportBackup, child: const Text('백업 내보내기')),
              ),
              const SizedBox(height: 6),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                    onPressed: _importBackup, child: const Text('백업 불러오기')),
              ),
              const SizedBox(height: 6),
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

  /// 기록이 바뀌면 예약도 다시 건다 — 예전 예약은 틀린 개수를 들고 있다.
  Future<void> _reschedule() => Reminder.instance
      .reschedule(allIds: Repo.instance.bank.items.map((i) => i.id));

  Future<void> _toggleRemind(bool on) async {
    final messenger = ScaffoldMessenger.of(context); // await 전에 잡는다
    if (on) {
      final granted = await Reminder.instance.requestPermission();
      if (!granted) {
        // 거절해도 설정은 켜 둔다 — 나중에 시스템에서 허용하면 바로 온다.
        messenger.showSnackBar(const SnackBar(
          content: Text('알림 권한이 없습니다. 시스템 설정에서 허용하면 바로 옵니다.'),
        ));
      }
    }
    await Store.instance.setRemind(on: on);
    await _reschedule();
    if (!mounted) return;
    setState(() {});
  }

  Future<void> _pickRemindTime() async {
    final cur = ReminderPlan.fromMinuteOfDay(Store.instance.remindAt);
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay(hour: cur.hour, minute: cur.minute),
    );
    if (picked == null) return;
    await Store.instance.setRemind(minuteOfDay: picked.hour * 60 + picked.minute);
    await _reschedule();
    if (!mounted) return;
    setState(() {});
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
