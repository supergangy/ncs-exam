/// 웹앱 app.css 의 CSS 변수를 그대로 옮긴 색상표.
library;

import 'package:flutter/material.dart';

class AppColors {
  final Color bg, card, line, ink, dim, faint, brand, brandSoft;
  final Color ok, okSoft, no, noSoft, warn, warnSoft;

  const AppColors({
    required this.bg, required this.card, required this.line, required this.ink,
    required this.dim, required this.faint, required this.brand,
    required this.brandSoft, required this.ok, required this.okSoft,
    required this.no, required this.noSoft, required this.warn, required this.warnSoft,
  });

  static const light = AppColors(
    bg: Color(0xFFF4F5F7), card: Color(0xFFFFFFFF), line: Color(0xFFE2E5EA),
    ink: Color(0xFF16181D), dim: Color(0xFF5D6470), faint: Color(0xFF8D94A0),
    brand: Color(0xFF1C4E80), brandSoft: Color(0xFFE8EFF7),
    ok: Color(0xFF17734A), okSoft: Color(0xFFE4F4EC),
    no: Color(0xFFB3261E), noSoft: Color(0xFFFDECEB),
    warn: Color(0xFF8A5A00), warnSoft: Color(0xFFFDF3E0),
  );

  static const dark = AppColors(
    bg: Color(0xFF14161A), card: Color(0xFF1D2026), line: Color(0xFF2C313A),
    ink: Color(0xFFE8EAEE), dim: Color(0xFFA2A9B6), faint: Color(0xFF767E8C),
    brand: Color(0xFF7AA9DD), brandSoft: Color(0xFF1E2A38),
    ok: Color(0xFF6CC496), okSoft: Color(0xFF16281F),
    no: Color(0xFFF08B84), noSoft: Color(0xFF2C1A19),
    warn: Color(0xFFE0B060), warnSoft: Color(0xFF2A2214),
  );

  static AppColors of(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark ? dark : light;
}

const circ = ['①', '②', '③', '④', '⑤', '⑥', '⑦'];

ThemeData buildTheme(Brightness b) {
  final c = b == Brightness.dark ? AppColors.dark : AppColors.light;
  final base = ThemeData(
    brightness: b,
    useMaterial3: true,
    scaffoldBackgroundColor: c.bg,
    colorScheme: ColorScheme(
      brightness: b,
      primary: c.brand, onPrimary: Colors.white,
      secondary: c.brand, onSecondary: Colors.white,
      surface: c.card, onSurface: c.ink,
      error: c.no, onError: Colors.white,
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: c.card, foregroundColor: c.ink, elevation: 0,
      surfaceTintColor: Colors.transparent,
      titleTextStyle: TextStyle(color: c.ink, fontSize: 17, fontWeight: FontWeight.w700),
    ),
    cardColor: c.card,
    dividerColor: c.line,
    fontFamily: 'Pretendard',
  );
  return base;
}
