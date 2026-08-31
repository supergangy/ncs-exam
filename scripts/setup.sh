#!/usr/bin/env bash
# 새 환경을 이 저장소가 돌 수 있는 상태로 만든다.
#
#   bash scripts/setup.sh
#
# 클라우드 세션·Codespaces·CI·새 노트북이 모두 이것 하나를 부른다. 「무엇을 깔아야
# 하나」를 사람이 기억하지 않게 하려는 것이다 — 기억에 맡기면 언젠가 빠뜨린다.
#
# **없는 것은 없다고 말하고 넘어간다.** 크롬이나 Flutter 가 없어도 문항 집필과
# 웹 작업은 그대로 되므로, 하나가 없다고 전체를 세우지 않는다. 무엇이 되고
# 무엇이 안 되는지는 마지막 표가 말한다.
set -uo pipefail

cd "$(dirname "$0")/.."
ok=() no=()

say() { printf '\n\033[1m%s\033[0m\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

# ── 파이썬 — 문항·빌드·검증의 뼈대 ──────────────────────────────────
say '파이썬'
# **이름 차례로 고르지 않는다.** 윈도 개발 PC 의 `python3` 는 판을 못 말하는
# 껍데기라(「Python」만 찍고 pip 이 실패한다) 이름만 보면 그것을 집는다.
# 실제로 판을 말할 수 있는지 물어보고 고른다.
PY=
for c in python3 python py; do
  have "$c" || continue
  v=$("$c" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null) || continue
  case "$v" in
    3.*) PY=$c; echo "   $c — 파이썬 $v"; break ;;
  esac
done
if [ -n "$PY" ]; then
  $PY -m pip install --quiet --upgrade pip 2>/dev/null
  if $PY -m pip install --quiet -r requirements.txt; then
    ok+=("파이썬 의존성 4개 (jinja2 · Pillow · markdown · pypdf)")
  else
    no+=("파이썬 의존성 — pip install -r requirements.txt 가 실패했다")
  fi
else
  no+=("파이썬 3 — 문항 집필·빌드·내보내기가 전부 막힌다")
fi

# ── 노드 — 웹판(vite) ───────────────────────────────────────────────
say '웹 (vite)'
if have npm; then
  echo "   node $(node --version) · npm $(npm --version)"
  (cd web && npm ci --silent 2>/dev/null || npm install --silent) \
    && ok+=("웹 의존성 (web/node_modules)")
else
  no+=("노드 — 웹 빌드·시험 87개가 막힌다")
fi

# ── 크롬 — PDF 를 굽는 데 쓴다 ──────────────────────────────────────
#    `build.py` 가 헤드리스 크롬으로 조판 높이를 재고 PDF 로 인쇄한다.
#    pip 으로 오지 않으므로 여기서 찾아보고, 없으면 apt 로 한 번 시도한다.
say 'PDF (헤드리스 크롬)'
CHROME=
for c in google-chrome google-chrome-stable chromium chromium-browser; do
  have "$c" && CHROME=$c && break
done
if [ -z "$CHROME" ]; then
  if have apt-get && [ "$(id -u)" = 0 ]; then
    echo '   없다 — apt 로 chromium 을 받아 본다'
    apt-get update -qq && apt-get install -y -qq chromium >/dev/null 2>&1
    have chromium && CHROME=chromium
  else
    # 윈도 개발 PC 에는 크롬이 PATH 밖에 깔려 있다. build.py 가 알아서 찾는다
    echo '   PATH 에서 못 찾았다 (build.py 는 따로 찾아본다)'
  fi
fi
if [ -n "$CHROME" ]; then
  echo "   $CHROME — $($CHROME --version 2>/dev/null | head -1)"
  ok+=("PDF 굽기 ($CHROME)")
else
  no+=("크롬 — python build.py 가 막힌다 (문항 집필·검증은 된다)")
fi

# ── Flutter — 앱판 ─────────────────────────────────────────────────
#    검사 스크립트(`mobile/tool/check_*.dart`)는 순수 Dart 라 Dart 만 있어도 돈다.
say '앱 (Flutter)'
if have flutter; then
  echo "   $(flutter --version 2>/dev/null | head -1)"
  (cd mobile && flutter pub get >/dev/null) && ok+=("앱 의존성 (mobile/.dart_tool)")
elif have dart; then
  echo "   dart 만 있다 — 검사 스크립트는 돌지만 APK 는 못 굽는다"
  no+=("Flutter — APK 빌드가 막힌다 (검사 10개는 dart 로 된다)")
else
  no+=("Flutter/Dart — 앱 검사 376건과 APK 빌드가 막힌다")
fi

# ── 무엇이 되나 ─────────────────────────────────────────────────────
say '준비됐다'
for x in "${ok[@]:-}"; do [ -n "$x" ] && echo "   ✔ $x"; done
if [ "${#no[@]}" -gt 0 ] && [ -n "${no[0]:-}" ]; then
  say '없는 것'
  for x in "${no[@]}"; do echo "   — $x"; done
fi

cat <<'END'

무엇을 어디서 돌리나는 CLAUDE.md 「검사」 절을 본다. 가장 짧은 한 벌 —

  python tools/export_bank.py --check          문항 844건 점검
  cd web && node --test test/*.test.js         웹 87개
  cd mobile && dart run tool/check_pool.dart   앱 검사 (10개 중 하나)
END
