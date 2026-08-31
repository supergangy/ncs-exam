# 이 저장소에서 일하는 법

NCS 봉투모의고사를 만들어 **웹앱과 안드로이드 앱으로 배포**하는 프로젝트다.
PDF 는 중간 산출물이고, 최종 산출물은 배포된 앱이다.

터미널·브라우저·클라우드·휴대폰 어디서 열어도 이 파일이 규율을 들고 있다.
자세한 것은 아래 문서가 맡는다 — 여기는 **어긋나면 되돌리기 어려운 것**만 적는다.

| 무엇 | 어디 |
|---|---|
| 문항 설계 규격 (선지·해설·HTML·정답 분포) | [`SPEC.md`](SPEC.md) |
| 집필 규칙 번호 (1-2 · 4-7 · 4-13 …) | [`docs/PLAYBOOK.md`](docs/PLAYBOOK.md) |
| 앱·배포 파이프라인 | [`docs/BANK.md`](docs/BANK.md) |
| 지금 어디까지 왔나 | [`docs/PLAN.md`](docs/PLAN.md) |
| 회차별 사양·근거 | `rounds/<회차>/README.md` |
| 앱 판올림 이력 | [`mobile/CHANGELOG.md`](mobile/CHANGELOG.md) |

---

## 처음 한 번

```bash
bash scripts/setup.sh
```

무엇이 준비됐고 무엇이 없는지 표로 말해 준다. 하나가 없어도 세우지 않는다 —
크롬이 없으면 PDF 만 못 굽고 문항 작업은 그대로 된다.

## 절대 커밋하지 않는 것

- `corpus/raw/` · `corpus/parsed/` — 시판 교재 원문. **상용 저작물이다**
- `reviews/raw/` — 필기후기 원문. 작성자 저작물이다. `db.json` 의 분류 결과만 커밋한다
- `out/<회차>/*_출제이유.pdf` 를 배포 자산으로 옮기는 일 — 함정 설계가 새어 나간다.
  같은 내용이 `admin.json` 에 있고 그것은 관리자 모드에서만 받는다

커밋 전에 한 번 본다 —

```bash
git diff --cached --name-only | grep -E "^(reviews/raw|corpus/)|출제이유" && echo "!! 멈춰라"
```

## 사용자에게 물어야 하는 것

**모의고사 설계를 바꾸는 결정.** 회차의 문항 수·시간·영역 배분, 어느 기관을
기준으로 삼을지, 후기 데이터를 어떻게 읽을지 — 선택지로 제시하고 사용자가 고른다.
집필·검증·리팩터링은 묻지 않고 진행한다.

후기를 근거로 쓸 때는 **③ 신뢰도 분석이 먼저다**(`README.md` 「제작 순서」).
「몇 명이 독립적으로 같은 말을 했는가」가 그 정보의 무게다.

## 검사

작업 단위가 끝나면 해당하는 것을 돌린다. **전부 통과해야 커밋한다.**

```bash
# 문항 — 844건
python tools/export_bank.py --check              # 선지 수·정답 범위·id 중복
python tools/selfcheck.py --round r7_cs          # PLAYBOOK 10가지 (회차마다)
python rounds/r7_cs/verify.py                    # 계산형 답을 다시 구한다 (r5·r6·r7)

# 웹 — 87개
cd web && node --test test/*.test.js
cd web && node tool/check_ui.mjs                 # 화면 규칙 (var() 미정의·지문 누락 …)

# 앱 — 376건 (dart 만 있어도 돈다)
cd mobile && for f in tool/check_*.dart; do dart run "$f"; done
```

`flutter analyze` 는 한글 경로에서 LSP 핸드셰이크에 죽는다. 앱 정적 검사는
GitHub Actions 가 맡는다(`.github/workflows/apk.yml`).

**알려진 지적 하나** — r6 의 24번 `<보기>` 조합형이 규칙 4-7 을 위배한다
(한 개만 판정해도 답이 나온다). 별건으로 고치는 중이라 CI 에서는 경고로만 낸다.

## 배포 — 웹과 APK 는 함께

한쪽만 올리면 조용히 벌어진다. 실제로 앱만 526문항에 멈춰 있던 적이 있다.

```bash
python tools/export_bank.py                              # bank.json → 앱·웹 세 곳
cd web && npx vite build && node tool/make_sw.mjs && cd ..
python tools/deploy_web.py --dry                          # 남길 것·지울 것을 먼저
python tools/deploy_web.py
python tools/deploy_check.py                              # 배포본이 로컬과 같은가

python mobile/tool/build_apk.py                           # ASCII 경로에서 굽는다
gh release create v1.x.0 <apk> --notes-file <노트>
```

`sw.js` 를 다시 만드는 것을 잊지 마라 — 판 도장이 파일 목록·크기·생성기 바이트에서
나오므로, 안 만들면 옛 껍데기가 계속 나가고 그 안의 묶음 이름은 이미 사라져
**흰 화면**이 된다.

## 커밋

- 제목은 **짧은 명사형** — 「이름·로고 교체」 「전산직에도 회차를」.
  문학적 서술은 쓰지 않는다
- 본문에는 **무엇이 문제였고 왜 그렇게 고쳤는지**를 적는다. 측정값이 있으면 그 값을
- 작업 단위가 끝나면 **묻지 않고 커밋·푸시**한다. 다만 위의 「절대 커밋하지 않는 것」은
  매번 확인한다
- 끝에 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

---

## 환경마다 되는 것이 다르다

| | 이 PC (윈도우) | 클라우드·리눅스 | GitHub Actions |
|---|---|---|---|
| 문항 집필·검증 | ○ | ○ | ○ |
| 웹 빌드·시험 | ○ | ○ | ○ |
| 앱 검사 (`check_*.dart`) | ○ | ○ | ○ |
| `python build.py` (PDF) | ○ | 크롬이 있으면 ○ | 안 돌린다 |
| APK 빌드 | △ `build_apk.py` 우회 | ○ 그냥 `flutter build` | ○ 태그를 밀면 |
| 웹 배포 | ○ | 토큰이 있으면 ○ | 안 돌린다 |

**△ 인 이유** — 이 PC 는 사용자 이름에 한글이 들어 있어 Flutter 3.44 의 AOT
스냅샷터가 경로를 깨뜨린다. `mobile/tool/build_apk.py` 가 `C:\dev\ncs_bank` 로
사본을 두고 굽는다. **리눅스에는 그 문제가 없다** — 클라우드에서는 `mobile/` 에서
바로 `flutter build apk --release` 를 하면 된다.

`out/<회차>/*.pdf` 는 **커밋되어 있다.** 그래서 크롬이 없는 환경에서도
`export_bank.py` 가 앱·웹 자산을 만들 수 있다 — PDF 를 다시 굽는 것만 못 한다.

## 클라우드에서 여러 작업을 나눠 돌릴 때

작업을 **파일이 겹치지 않게** 잘라야 서로 밟지 않는다. 이 저장소에서 잘 갈리는 선 —

| 작업 | 주로 만지는 곳 |
|---|---|
| 새 회차 집필 | `rounds/<새 회차>/` (새 폴더라 충돌이 없다) |
| 웹 화면 | `web/src/` |
| 앱 화면 | `mobile/lib/` |
| 문항 손질 | `bank/_common/<과목>.py` |

**`app/data/bank.json` 은 거의 모든 작업이 건드린다.** 내보내기가 다시 만드는
산출물이므로, 충돌이 나면 고치려 들지 말고 한쪽을 받아들인 뒤
`python tools/export_bank.py` 를 다시 돌린다. 같은 파일이
`mobile/assets/data/` 와 `web/public/data/` 에도 복사되므로 셋을 함께 본다.
