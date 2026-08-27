# -*- coding: utf-8 -*-
"""프로젝트 표시 이름을 「NCS 기출은행」 → 「NCS PASS」 로 바꾼다.

**표시 이름과 내부 키를 가른다.** 아래 넷은 바꾸면 기존 사용자 데이터를 잃는다.

  ncsbank.v1        localStorage · SharedPreferences 키 — 학습 기록 전체
  ncsbank.db        SQLite 파일명 — 앱 안의 기록 테이블
  'ncs-bank'        backup.dart 의 `backupApp` — 복원 시 봉투를 대조하는 값
  com.supergangy.ncs_bank  안드로이드 패키지 — 바꾸면 별개 앱이 되어 업데이트가 끊긴다

바꾸는 것은 사람이 읽는 문자열과, 데이터에 얽히지 않은 식별자(Dart 클래스명·배포 URL)뿐이다.
"""
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent.parent

OLD_LONG, OLD_SHORT, NEW = "NCS 기출은행", "기출은행", "NCS PASS"

# 건드리면 안 되는 것 — 치환 뒤 이 패턴들이 그대로 있는지 검사한다
KEEP = ["ncsbank.v1", "ncsbank.db", "'ncs-bank'", "ncsbank.migrated", "com.supergangy.ncs_bank"]

# 파일 단위 치환 — (경로, [(전, 후, 예상건수)])
EXPLICIT = [
    ("app/sw.js", [("ncsbank-v11", "ncsbank-v12", 1)]),          # 캐시 버전만 올린다. 이름은 키가 아니지만 굳이 바꾸지 않는다
    ("mobile/lib/main.dart", [("NcsBankApp", "NcsPassApp", 3)]),
    ("mobile/test/widget_test.dart", [("NcsBankApp", "NcsPassApp", 1)]),
    ("mobile/lib/screens/settings_screen.dart", [("ncsbank-backup-", "ncspass-backup-", 1)]),
    ("tools/deploy_check.py", [("ncs-exam-app", "ncs-pass-app", 1)]),
]

TEXT_EXT = {".py", ".js", ".jsx", ".mjs", ".html", ".css", ".json", ".md",
            ".yml", ".yaml", ".dart", ".xml", ".webmanifest", ".svg", ".j2"}


def tracked():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
                         encoding="utf-8").stdout
    for line in out.splitlines():
        p = ROOT / line
        if p.suffix.lower() in TEXT_EXT and p.is_file():
            yield line, p


changed, total = [], 0

# 1) 표시 이름 — 긴 형태를 먼저 치환해야 「NCS NCS PASS」 가 되지 않는다
for rel, p in tracked():
    s = p.read_text(encoding="utf-8")
    n_long = s.count(OLD_LONG)
    s2 = s.replace(OLD_LONG, NEW)
    n_short = s2.count(OLD_SHORT)
    s2 = s2.replace(OLD_SHORT, NEW)
    if s2 != s:
        p.write_text(s2, encoding="utf-8")
        changed.append((rel, n_long, n_short))
        total += n_long + n_short

print("■ 표시 이름 치환 — %d개 파일 · %d건" % (len(changed), total))
for rel, a, b in sorted(changed, key=lambda x: -(x[1] + x[2])):
    print("   %-46s 긴 %d · 짧은 %d" % (rel, a, b))

# 2) 파일 단위 치환
print()
print("■ 식별자·버전")
for rel, rules in EXPLICIT:
    p = ROOT / rel
    if not p.exists():
        print("   %-46s 없음 — 건너뜀" % rel)
        continue
    s = p.read_text(encoding="utf-8")
    for old, new, want in rules:
        got = s.count(old)
        if got != want:
            print("   !! %-43s '%s' %d건 (기대 %d) — 건너뜀" % (rel, old, got, want))
            continue
        s = s.replace(old, new)
        print("   %-46s %s → %s (%d)" % (rel, old, new, got))
    p.write_text(s, encoding="utf-8")

# 3) 지켜야 할 키가 살아 있는지
print()
print("■ 내부 키 확인 — 하나라도 사라지면 기존 기록을 잃는다")
for k in KEEP:
    hits = subprocess.run(["git", "grep", "-c", "-F", k], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8").stdout
    n = sum(int(x.rsplit(":", 1)[1]) for x in hits.splitlines() if ":" in x)
    print("   %-28s %s (%d건)" % (k, "살아 있음" if n else "!! 사라졌다 !!", n))

# 4) 남은 옛 이름
print()
left = subprocess.run(["git", "grep", "-n", "-E", "기출은행"], cwd=ROOT,
                      capture_output=True, text=True, encoding="utf-8").stdout.strip()
print("■ 남은 「기출은행」:", ("없음" if not left else "\n" + left))
