/// 낱개 풀이 — 웹 `#/q?...` 의 solo 모드와 같다.
/// 채점하지 않고 정답을 즉시 보여 주며, 앞으로만 이동한다(회차 응시와 다른 규칙).
library;

import 'package:flutter/material.dart';
import '../repo.dart';
import '../store.dart';
import '../theme.dart';
import '../widgets.dart';
import '../html_view.dart';

class QuestionScreen extends StatefulWidget {
  final List<Item> pool;
  final String title;
  const QuestionScreen({super.key, required this.pool, this.title = ''});

  @override
  State<QuestionScreen> createState() => _QuestionScreenState();
}

class _QuestionScreenState extends State<QuestionScreen> {
  int at = 0;
  int? chosen;
  bool graded = false;
  int right = 0;
  final List<String> memoDraft = [];

  Item get item => widget.pool[at];

  void _pick(int n) {
    if (graded) return;
    setState(() => chosen = n);
  }

  Future<void> _grade() async {
    final ok = chosen == item.an;
    if (ok) right++;
    await Store.instance.record(item.id, chosen, ok);
    setState(() => graded = true);
  }

  void _next() {
    if (at >= widget.pool.length - 1) {
      Navigator.of(context).pushReplacement(MaterialPageRoute(
        builder: (_) => _ResultPage(pool: widget.pool, right: right),
      ));
      return;
    }
    setState(() {
      at++;
      chosen = null;
      graded = false;
    });
  }

  Future<void> _toggleMark({bool? bookmark, bool? flag}) async {
    await Store.instance.toggleMark(item.id, bookmark: bookmark, flag: flag);
    setState(() {});
  }

  Future<void> _promptMemo() async {
    final cur = Store.instance.markOf(item.id);
    final ctl = TextEditingController(text: cur.memo);
    final memo = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('무엇이 이상한가요?'),
        content: TextField(controller: ctl, autofocus: true, maxLines: 3,
            decoration: const InputDecoration(hintText: '그냥 확인만 눌러도 됩니다')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('취소')),
          FilledButton(onPressed: () => Navigator.pop(ctx, ctl.text), child: const Text('확인')),
        ],
      ),
    );
    if (memo == null) return;
    if (memo.trim().isEmpty) {
      await Store.instance.toggleMark(item.id, flag: !cur.flag);
    } else {
      await Store.instance.setMemo(item.id, memo.trim());
    }
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final m = Store.instance.markOf(item.id);
    final admin = Store.instance.admin ? (Repo.instance.admin?[item.id]) : null;

    return Scaffold(
      appBar: AppBar(title: Text('${at + 1} / ${widget.pool.length}')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 90),
          children: [
            LinearProgressIndicator(
              value: at / widget.pool.length, minHeight: 3,
              backgroundColor: c.line,
              valueColor: AlwaysStoppedAnimation(c.brand),
            ),
            const SizedBox(height: 10),
            Row(children: [
              _MetaChip(item.sj), const SizedBox(width: 6), _MetaChip(item.ty),
              if (item.rd != null) ...[
                const SizedBox(width: 6),
                _MetaChip('${Repo.instance.round(item.rd!)?.title ?? item.rd} ${item.no}번'),
              ],
              if (item.df != null) ...[const SizedBox(width: 6), _MetaChip('난이도 ${item.df}')],
              if (admin?.rk != null) ...[const SizedBox(width: 6), RiskBadge(admin!.rk!)],
              const Spacer(),
              IconButton(
                icon: Icon(m.bookmark ? Icons.star : Icons.star_border,
                    color: m.bookmark ? c.brand : c.faint, size: 22),
                onPressed: () => _toggleMark(bookmark: !m.bookmark),
              ),
              IconButton(
                icon: Icon(m.flag ? Icons.flag : Icons.outlined_flag,
                    color: m.flag ? c.warn : c.faint, size: 20),
                onPressed: _promptMemo,
              ),
            ]),
            if (item.pg != null) ...[
              if (Repo.instance.passage(item.pg!).lead != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(Repo.instance.passage(item.pg!).lead!,
                      style: TextStyle(color: c.dim, fontSize: 13.5)),
                ),
              HtmlBox(Repo.instance.passage(item.pg!).body),
            ] else if (item.ld != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(item.ld!, style: TextStyle(color: c.dim, fontSize: 13.5)),
              ),
            if (item.mt != null) HtmlBox(item.mt!),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(plainText(item.st),
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600,
                      color: c.ink, height: 1.5)),
            ),
            ...List.generate(item.ch.length, (n) => _ChoiceTile(
                  n: n, text: item.ch[n], selected: chosen == n + 1,
                  correct: graded && n + 1 == item.an,
                  wrong: graded && n + 1 == chosen && chosen != item.an,
                  graded: graded,
                  each: item.ea != null && n < item.ea!.length ? item.ea![n] : null,
                  onTap: () => _pick(n + 1),
                )),
            if (graded) ...[
              const SizedBox(height: 12),
              _Verdict(ok: chosen == item.an, answer: item.an, chosen: chosen),
              if (item.ex != null) ...[
                const SizedBox(height: 10),
                _Labeled('해설', HtmlBox(item.ex!)),
              ],
              if (admin != null) ...[
                const SizedBox(height: 10),
                _AdminBox(admin),
              ],
            ],
          ],
        ),
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 8, 14, 10),
          child: SizedBox(
            width: double.infinity, height: 48,
            child: FilledButton(
              onPressed: graded ? _next : (chosen == null ? null : _grade),
              child: Text(graded
                  ? (at >= widget.pool.length - 1 ? '끝내기' : '다음 문제')
                  : '확인'),
            ),
          ),
        ),
      ),
    );
  }
}

class _MetaChip extends StatelessWidget {
  final String text;
  const _MetaChip(this.text);
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    return Text(text, style: TextStyle(color: c.faint, fontSize: 12.5));
  }
}

class _ChoiceTile extends StatelessWidget {
  final int n;
  final String text;
  final bool selected, correct, wrong, graded;
  final String? each;
  final VoidCallback onTap;
  const _ChoiceTile({
    required this.n, required this.text, required this.selected,
    required this.correct, required this.wrong, required this.graded,
    required this.each, required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    Color border = c.line, bg = c.card, circleColor = c.bg, circleFg = c.dim;
    if (selected && !graded) {
      border = c.brand; bg = c.brandSoft; circleColor = c.brand; circleFg = Colors.white;
    }
    if (correct) {
      border = c.ok; bg = c.okSoft; circleColor = c.ok; circleFg = Colors.white;
    } else if (wrong) {
      border = c.no; bg = c.noSoft; circleColor = c.no; circleFg = Colors.white;
    }
    return InkWell(
      onTap: graded ? null : onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        margin: const EdgeInsets.only(bottom: 7),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
        decoration: BoxDecoration(
          color: bg, borderRadius: BorderRadius.circular(12),
          border: Border.all(color: border, width: 1.4),
        ),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(
            width: 24, height: 24,
            decoration: BoxDecoration(color: circleColor, shape: BoxShape.circle,
                border: Border.all(color: border)),
            alignment: Alignment.center,
            child: Text(circ[n], style: TextStyle(color: circleFg, fontSize: 12,
                fontWeight: FontWeight.w700)),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(plainText(text), style: TextStyle(color: c.ink, fontSize: 15)),
              if (graded && each != null && each!.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 5),
                  child: Text(stripLead(plainText(each)),
                      style: TextStyle(color: c.dim, fontSize: 13)),
                ),
            ]),
          ),
        ]),
      ),
    );
  }
}

class _Verdict extends StatelessWidget {
  final bool ok;
  final int answer;
  final int? chosen;
  const _Verdict({required this.ok, required this.answer, required this.chosen});
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(color: ok ? c.okSoft : c.noSoft,
          borderRadius: BorderRadius.circular(14)),
      child: Row(children: [
        Text(ok ? '맞았습니다' : '틀렸습니다',
            style: TextStyle(color: ok ? c.ok : c.no, fontWeight: FontWeight.w800, fontSize: 15)),
        const Spacer(),
        Text(ok ? '정답 ${circ[answer - 1]}'
            : '정답은 ${circ[answer - 1]} (고른 것 ${chosen != null ? circ[chosen! - 1] : "없음"})',
            style: TextStyle(color: ok ? c.ok : c.no, fontSize: 12.5)),
      ]),
    );
  }
}

class _Labeled extends StatelessWidget {
  final String label;
  final Widget child;
  const _Labeled(this.label, this.child);
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Padding(
        padding: const EdgeInsets.only(bottom: 4, left: 2),
        child: Text(label, style: TextStyle(color: c.faint, fontSize: 12, fontWeight: FontWeight.w700)),
      ),
      child,
    ]);
  }
}

class _AdminBox extends StatelessWidget {
  final AdminInfo a;
  const _AdminBox(this.a);
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final rows = <Widget>[];
    if (a.ev != null) rows.add(_kv(c, '후기', a.ev!));
    for (final k in ['근거', '설계', '함정', '검증']) {
      final v = a.wy?[k];
      if (v is String && v.isNotEmpty) rows.add(_kv(c, k, v));
    }
    if (a.sn != null) rows.add(_kv(c, '스냅샷', a.sn!));
    if (a.rd != null) rows.add(_kv(c, '회차', a.rd!));
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: c.warnSoft, borderRadius: BorderRadius.circular(14),
        border: Border.all(color: c.warn, width: 1, style: BorderStyle.solid),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('출제자용 — 위험도 ${(a.rk ?? '—').toUpperCase()}',
            style: TextStyle(color: c.warn, fontWeight: FontWeight.w800, fontSize: 12.5)),
        const SizedBox(height: 8),
        ...rows,
      ]),
    );
  }

  Widget _kv(AppColors c, String k, String v) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: RichText(
          text: TextSpan(children: [
            TextSpan(text: '$k  ', style: TextStyle(color: c.warn, fontWeight: FontWeight.w800,
                fontSize: 12.5)),
            TextSpan(text: plainText(v).replaceAll('**', ''),
                style: TextStyle(color: c.ink, fontSize: 12.5)),
          ]),
        ),
      );
}

class _ResultPage extends StatelessWidget {
  final List<Item> pool;
  final int right;
  const _ResultPage({required this.pool, required this.right});

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final rate = pool.isEmpty ? 0 : (right / pool.length * 100).round();
    final miss = pool.where((i) => Store.instance.isWrong(i.id)).toList();
    return Scaffold(
      appBar: AppBar(title: const Text('결과')),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          Row(children: [
            Expanded(child: _kpi(c, '${pool.length}', '푼 문항')),
            Expanded(child: _kpi(c, '$right', '맞힘')),
            Expanded(child: _kpi(c, '$rate%', '정답률')),
          ]),
          if (miss.isEmpty)
            const EmptyState(title: '전부 맞혔습니다', body: '다음 분류로 넘어가 보세요.')
          else ...[
            SectionTitle('틀린 문제 ${miss.length}개'),
            ...miss.map((i) => RowTile(
                  title: plainText(i.st).length > 40
                      ? '${plainText(i.st).substring(0, 40)}…' : plainText(i.st),
                  subtitle: '${i.sj} · ${i.ty}',
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => QuestionScreen(pool: [i]))),
                )),
          ],
          const SizedBox(height: 8),
          ResumeCard(title: '홈으로', subtitle: '다른 과목·유형 고르기',
              onTap: () => Navigator.of(context).popUntil((r) => r.isFirst)),
        ],
      ),
    );
  }

  Widget _kpi(AppColors c, String v, String k) => Container(
        margin: const EdgeInsets.symmetric(horizontal: 4),
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(color: c.card, borderRadius: BorderRadius.circular(14),
            border: Border.all(color: c.line)),
        child: Column(children: [
          Text(v, style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: c.ink)),
          Text(k, style: TextStyle(fontSize: 11.5, color: c.faint)),
        ]),
      );
}
