/// 문항 번호 띠 — 화면 위쪽에 붙어 지금 어디인지 보여 주고, 누르면 그리로 간다.
/// 낱개 풀이와 회차 응시가 함께 쓴다.
library;

import 'package:flutter/material.dart';
import 'theme.dart';

enum NavMark { none, done, ok, no, flag }

class QuestionStrip extends StatefulWidget implements PreferredSizeWidget {
  final int count;
  final int current;
  /// i번째 칸에 붙일 표시. 채점 전이면 done/none, 채점 후면 ok/no.
  final NavMark Function(int i) markOf;
  /// i번째 칸에 쓸 숫자. 회차는 실제 문항 번호, 낱개는 i+1.
  final String Function(int i) labelOf;
  final void Function(int i) onTap;

  const QuestionStrip({
    super.key, required this.count, required this.current,
    required this.markOf, required this.labelOf, required this.onTap,
  });

  @override
  Size get preferredSize => const Size.fromHeight(46);

  @override
  State<QuestionStrip> createState() => _QuestionStripState();
}

class _QuestionStripState extends State<QuestionStrip> {
  static const _w = 42.0;
  final _ctl = ScrollController();

  @override
  void didUpdateWidget(QuestionStrip old) {
    super.didUpdateWidget(old);
    if (old.current != widget.current) _center();
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _center(animate: false);
    });
  }

  @override
  void dispose() {
    _ctl.dispose();
    super.dispose();
  }

  void _center({bool animate = true}) {
    if (!_ctl.hasClients) return;
    final vw = _ctl.position.viewportDimension;
    final target = (widget.current * _w + _w / 2 - vw / 2)
        .clamp(0.0, _ctl.position.maxScrollExtent);
    if (animate) {
      _ctl.animateTo(target,
          duration: const Duration(milliseconds: 220), curve: Curves.easeOut);
    } else {
      _ctl.jumpTo(target);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    return Container(
      height: 46,
      decoration: BoxDecoration(
        color: c.card,
        border: Border(bottom: BorderSide(color: c.line)),
      ),
      child: ListView.builder(
        controller: _ctl,
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        itemExtent: _w,
        itemCount: widget.count,
        itemBuilder: (ctx, i) {
          final here = i == widget.current;
          final mk = widget.markOf(i);
          final (Color fg, Color bg, Color line) = switch (mk) {
            NavMark.ok => (c.ok, c.okSoft, c.ok),
            NavMark.no => (c.no, c.noSoft, c.no),
            NavMark.flag => (c.warn, c.warnSoft, c.warn),
            NavMark.done => (c.brand, c.brandSoft, c.brand),
            NavMark.none => (c.faint, c.card, c.line),
          };
          return Padding(
            padding: const EdgeInsets.symmetric(horizontal: 2.5),
            child: InkWell(
              onTap: () => widget.onTap(i),
              borderRadius: BorderRadius.circular(9),
              child: Container(
                decoration: BoxDecoration(
                  color: here ? c.ink : bg,
                  borderRadius: BorderRadius.circular(9),
                  border: Border.all(
                      color: here ? c.ink : line, width: here ? 2 : 1),
                ),
                alignment: Alignment.center,
                child: Text(
                  widget.labelOf(i),
                  style: TextStyle(
                    fontSize: 12.5,
                    fontWeight: here ? FontWeight.w800 : FontWeight.w600,
                    color: here ? c.card : fg,
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
