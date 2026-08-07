library;

import 'package:flutter/material.dart';
import 'models.dart';
import 'store.dart';
import 'theme.dart';

class Progress {
  final int n, done, ok;
  Progress(this.n, this.done, this.ok);
  int get rate => done == 0 ? 0 : (ok / done * 100).round();
  int get barPct => n == 0 ? 0 : (done / n * 100).round();
}

Progress computeProgress(List<Item> items) {
  int done = 0, ok = 0;
  for (final it in items) {
    final l = Store.instance.last(it.id);
    if (l != null) {
      done++;
      if (l.ok) ok++;
    }
  }
  return Progress(items.length, done, ok);
}

String progText(Progress p) {
  if (p.done == 0) return '${p.n}문항';
  return '${p.done}/${p.n} · 정답률 ${p.rate}%';
}

class SectionTitle extends StatelessWidget {
  final String text;
  const SectionTitle(this.text, {super.key});
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(2, 18, 2, 8),
      child: Text(text,
          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: c.faint)),
    );
  }
}

class ProgressBar extends StatelessWidget {
  final Progress p;
  const ProgressBar(this.p, {super.key});
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final good = p.done == p.n && p.n > 0;
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(3),
        child: LinearProgressIndicator(
          value: p.n == 0 ? 0 : p.done / p.n,
          minHeight: 4,
          backgroundColor: c.line,
          valueColor: AlwaysStoppedAnimation(good ? c.ok : c.brand),
        ),
      ),
    );
  }
}

class RiskBadge extends StatelessWidget {
  final String risk; // low · mid · high
  const RiskBadge(this.risk, {super.key});
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final Color bg, fg;
    switch (risk) {
      case 'low':
        bg = c.okSoft; fg = c.ok; break;
      case 'mid':
        bg = c.warnSoft; fg = c.warn; break;
      default:
        bg = c.noSoft; fg = c.no;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(6)),
      child: Text(risk.toUpperCase(),
          style: TextStyle(color: fg, fontSize: 11, fontWeight: FontWeight.w800)),
    );
  }
}

/// 목록의 한 줄 — 웹 `.row` 와 같다.
class RowTile extends StatelessWidget {
  final String title;
  final String? subtitle;
  final Widget? trailing;
  final Progress? progress;
  final VoidCallback? onTap;
  const RowTile({
    super.key, required this.title, this.subtitle, this.trailing,
    this.progress, this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
          color: c.card, borderRadius: BorderRadius.circular(14),
          border: Border.all(color: c.line),
        ),
        child: Row(children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title, style: TextStyle(fontWeight: FontWeight.w600, color: c.ink,
                  fontSize: 15.5)),
              if (subtitle != null)
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text(subtitle!, style: TextStyle(fontSize: 12.5, color: c.faint)),
                ),
              if (progress != null) ProgressBar(progress!),
            ]),
          ),
          if (trailing != null) trailing!
          else if (onTap != null)
            Icon(Icons.chevron_right, color: c.faint),
        ]),
      ),
    );
  }
}

/// 큰 카드 — 웹 `.hero` (직렬 카드).
class HeroCard extends StatelessWidget {
  final String title, subtitle, footer;
  final Progress progress;
  final VoidCallback onTap;
  const HeroCard({
    super.key, required this.title, required this.subtitle,
    required this.footer, required this.progress, required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(18),
        margin: const EdgeInsets.only(bottom: 10),
        decoration: BoxDecoration(
          color: c.card, borderRadius: BorderRadius.circular(18),
          border: Border.all(color: c.line),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800,
              color: c.ink, letterSpacing: -0.5)),
          const SizedBox(height: 3),
          Text(subtitle, style: TextStyle(color: c.faint, fontSize: 13)),
          const SizedBox(height: 10),
          Text(footer, style: TextStyle(color: c.dim, fontSize: 13)),
          ProgressBar(progress),
        ]),
      ),
    );
  }
}

/// 강조 카드(이어하기) — 웹 `.resume`.
class ResumeCard extends StatelessWidget {
  final String title, subtitle;
  final VoidCallback onTap;
  const ResumeCard({super.key, required this.title, required this.subtitle, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        margin: const EdgeInsets.only(bottom: 10),
        decoration: BoxDecoration(
          color: AppColors.of(context).brand, borderRadius: BorderRadius.circular(16),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700,
              fontSize: 16)),
          const SizedBox(height: 3),
          Text(subtitle, style: const TextStyle(color: Colors.white70, fontSize: 12.5)),
        ]),
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  final String title, body;
  const EmptyState({super.key, required this.title, required this.body});
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 48, horizontal: 24),
      child: Column(children: [
        Text(title, style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: c.dim)),
        const SizedBox(height: 6),
        Text(body, textAlign: TextAlign.center, style: TextStyle(color: c.faint)),
      ]),
    );
  }
}

class ChipButton extends StatelessWidget {
  final String label;
  final int? count;
  final bool on;
  final VoidCallback onTap;
  const ChipButton({super.key, required this.label, this.count, this.on = false,
      required this.onTap});
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(999),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          color: on ? c.brand : c.card,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: on ? c.brand : c.line),
        ),
        child: Text(
          count != null ? '$label  $count' : label,
          style: TextStyle(color: on ? Colors.white : c.dim, fontSize: 13.5),
        ),
      ),
    );
  }
}
