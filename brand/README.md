# 브랜드 자산

로고 원본 한 장에서 앱·웹·안드로이드가 쓰는 아이콘을 전부 만든다.

```bash
python brand/logo.py      # logo-src.jpg → brand/out/
python brand/deploy.py    # brand/out/ → app/ web/public/ mobile/
```

`brand/out/` 은 중간 산출물이라 커밋하지 않는다. **커밋되는 것은 배포된 자리의 파일들**이다.
도안이 바뀌면 원본을 갈고 위 두 줄을 다시 돌린다.

## 원본

`logo-src.jpg` — 흰 캔버스 위에 연회색 둥근 사각형 카드, 그 안에 파랑→보라 화살표 심볼.

카드색 `#F8FAFC` 과 캔버스 흰색은 채도가 거의 같아 알파 마스크로 갈라지지 않는다.
그래서 **심볼만 채도로 뽑고 카드는 새로 그린다** — 어떤 크기로 내도 모서리가 선명하다.

채도 임계는 실측값이다. 배경·드롭섀도가 `sat 12~14`, 심볼이 `sat 130~150`이라
`SAT_LO=40` 으로 자른다. 12 로 잡으면 원본 드롭섀도가 얼룩으로 딸려 온다.

## 아이콘은 쓰이는 자리마다 규칙이 다르다

한 장을 복사해 돌려 쓰면 어딘가는 깎인다.

| 쓰임 | 파일 | 규칙 |
|---|---|---|
| 웹 `any` | `icon-{192,512}.png` | 카드째 보인다. 여백 20% |
| 웹 `maskable` | `icon-maskable-512.png` | 런처가 **원형으로 깎는다**. 배경을 꽉 채우고 심볼은 가운데 60% |
| 파비콘 | `favicon-32.png`, `icon.svg` | 32px 에서 형태가 남아야 하므로 여백을 10% 로 줄여 그린 뒤 축소 |
| 안드로이드 legacy | `mipmap-*/ic_launcher.png` | 카드 + 심볼. 마스크가 없다 |
| 안드로이드 adaptive | `mipmap-*/ic_launcher_foreground.png` | 108dp 중 **가운데 72dp만 확실히 보인다**. 배경은 `ic_launcher_background.xml` 이 따로 준다 |
| 안드로이드 monochrome | 위 foreground 재사용 | 실루엣으로 쓰인다 — **알파가 곧 형태다** |

## 색

액센트는 로고에서 딴 `#6366F1` 이다. 흰 배경 대비 **4.57:1** 로 AA(4.5)를 넘는다 —
여유가 크지 않으므로 본문 텍스트 색으로는 쓰지 않고 액센트로만 쓴다.

값은 `web/src/styles/tokens.css` 와 `tools/ui_kit.py` 두 곳이 출처다. 도면과 화면이 같은 색이어야 한다.

## 이름

표시 이름은 **NCS PASS** 다 (이전 이름: NCS 기출은행).

`brand/rename.py` 가 표시 이름을 바꾼다. **내부 키는 건드리지 않는다** —
아래 넷은 바꾸면 기존 사용자의 기록을 잃는다.

| 키 | 자리 | 바꾸면 |
|---|---|---|
| `ncsbank.v1` | localStorage · SharedPreferences | 학습 기록 전체를 못 읽는다 |
| `ncsbank.db` | SQLite 파일명 | 앱 안의 기록 테이블을 못 찾는다 |
| `'ncs-bank'` | `backup.dart` 의 `backupApp` | 예전 백업 파일을 복원할 때 봉투 대조에서 걸린다 |
| `com.supergangy.ncs_bank` | 안드로이드 패키지 | 별개 앱이 되어 업데이트가 끊긴다 |
