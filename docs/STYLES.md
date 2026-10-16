# 스타일 라이브러리

잘 만든 프로덕트 모션(keyframe.gallery 등)에서 배운 **보는 방식과 움직이는 방식**을 스타일로 모아 둔 곳이에요.
템플릿이 "무슨 장면이 나오나"라면, 스타일은 "어떤 결로 보이고 움직이나"예요. 영상마다 스타일 하나를 고를 수 있어요.

```
styles/<스타일>/
  style.json   엔진·장면 쌓기·앱이 읽는 값 (색, 글꼴, 질감, 모양, 움직임)
  style.md     사람과 Claude 가 읽는 스타일 카드 (보는 느낌, 대표 장면, 다시 만드는 법)
  thumb.jpg    앱의 스타일 고르기 썸네일 (python tools/styles.py thumbs 로 만듦)
```

배운 영상의 화면을 그대로 가져오지 않아요. 색·글자·질감·움직임의 원리만 적고, 장면은 우리 엔진으로 새로 만들어요.
브랜드 로고·캐릭터·고유한 그림은 따라 그리지 않아요.

## 영상에 쓰기

video.json 에 `"style": "<스타일>"` 을 넣으면 (앱: 연출 탭 → 스타일 → 스타일 고르기)

1. **질감(look)** 이 모든 템플릿 위에 깔려요: 종이, 필름 그레인, 하프톤, 디더, 주사선, 비네트, 색 입히기, 액자, 색 번짐(rgbSplit), 손그림 선 떨림(boil). `"styleLook": false` 면 끔.
2. **글꼴(type)** 이 바뀌어요 (`"styleFonts": false` 면 브랜드 글꼴 그대로). 스타일 글꼴에 없는 글자는 브랜드 글꼴로 보여요.
3. **색(colors)** 은 `"styleColors": true` 일 때만 바뀌어요. 기본은 브랜드 색. 팔레트의 나머지 색은 `--pal1~3` 으로 그라디언트 덩어리에 쓰여요.
4. **장면 쌓기(scenes)** 는 `scenes` 값으로 바탕 무늬·정렬·카드 모양·강조 방식·전환·이징까지 따라가요.
   `rough: true` 면 카드·막대·번호에 손으로 그은 테두리가 한 획씩 그어지고 막대는 빗금으로 칠해져요.
5. **끊어 그리기(motion.stepped)** 를 정하면 렌더와 미리보기 모두 초당 그 장 수로 끊겨 스톱모션·셀 애니메이션처럼 보여요.
6. Claude 에게 문구·구성을 맡기거나 Claude Code 에게 연출을 맡길 때 style.md 가 함께 건네져요.

video.json 의 `look` 으로 스타일 질감 하나하나를 덮어쓸 수 있어요. 예: `"look": {"grain": 0, "boil": 0}` (그레인·선 떨림만 끄기).

## 명령

```
python tools/styles.py                 # 묶음별 목록
python tools/styles.py show <스타일>    # 스타일 카드
python tools/styles.py check           # 빠진 값, 글꼴 파일, 글자·바탕 대비, 전환·이징 이름 점검
python tools/styles.py thumbs          # 썸네일(styles/<스타일>/thumb.jpg) 새로 만들기. style.json 이 바뀐 것만, --all 이면 전부
```

새 스타일을 더한 뒤에는 `check` 와 `thumbs` 를 돌리고 thumb.jpg 를 열어 봐요. 이름이 `zz-` 나 `_` 로 시작하는 폴더는 시험용이라 목록에 안 나와요.

엔진에서 쓰는 도구: `S.style`(스타일 값), `S.look`(질감 값), `S.q(t)`(끊어 그리기 시각), 전환 `S.tr.blur·whip·blocks`, 손그림 선 `Studio.M.rough('line'|'ellipse'|'rect', …)`.

## style.json

```json
{
  "id": "hand-marker-notes",
  "name": "마커 노트",
  "group": "손그림",
  "summary": "종이 위 마커로 쓴 메모처럼. 선이 살짝 떨리고, 강조는 손으로 친 동그라미",
  "tags": ["손그림", "따뜻함", "교육"],
  "hand": true,
  "source": { "site": "keyframe.gallery", "ref": "어디서 배웠는지 (영상 주소나 mux 재생 ID)", "at": "12.4–16.0초", "note": "무엇을 배웠는지" },
  "palette": ["#F4EDE0", "#1E1B18", "#E8553D", "#2F6BFF"],
  "colors": { "bg": "#F4EDE0", "onBg": "#1E1B18", "onBgMuted": "rgba(30,27,24,.7)", "paper": "#1E1B18", "ink": "#F4EDE0",
              "accent": "#E8553D", "accentInk": "#FFFFFF", "pattern": "rgba(30,27,24,.08)", "glow": "rgba(232,85,61,.25)" },
  "type": { "display": ["Caveat", "Nanum Pen"], "heading": ["Nanum Pen"] },
  "fonts": [ { "family": "Caveat", "weight": "400 700", "file": "fonts/Caveat-Variable.woff2" },
             { "family": "Nanum Pen", "weight": 400, "file": "fonts/NanumPenScript-Regular.woff2" } ],
  "look": { "paper": "warm", "grain": 0.12, "boil": { "amount": 1.2, "fps": 8 } },
  "shape": { "radius": "calc(var(--u) * 1)", "stroke": "hand" },
  "motion": { "pace": "보통", "bpm": 100, "ease": "back.out(1.4)", "stagger": 1.2, "transitions": ["cut", "push"], "stepped": 8 },
  "scenes": { "bg": "grid", "align": "left", "card": "paper", "marker": "circle", "weight": 400, "tracking": 0, "case": "none", "rough": true,
              "title": "write", "frame": "none", "deco": ["doodles"], "number": "count", "scale": 1, "schemes": ["dark", "paper"] },
  "signature": ["글자가 써지듯 한 획씩 나타남", "강조할 말에 손으로 동그라미"],
  "fits": ["수강생 모집", "교육·강의 소개", "공지"],
  "avoid": ["반짝이는 그라디언트", "유리 질감"]
}
```

| 키 | 뜻 |
|---|---|
| `group` | 타이포 · 제품 UI · 그라디언트·빛 · 3D·사물 · 그래픽·도형 · 레트로·픽셀 · 손그림 · 콜라주·사진 · 다이어그램·데이터 · 시네마틱 |
| `palette` | 대표 색 4~6개 (썸네일·카드용) |
| `colors` | "스타일 색 쓰기"를 켰을 때 브랜드 색 대신 쓰는 값 (brand.json 의 colors 와 같은 키) |
| `type`·`fonts` | 스타일 글꼴. `fonts/` 안 파일만. 한글이 없는 영문 글꼴은 한글 글꼴을 뒤에 같이 적음 |
| `look` | 질감. `paper`(warm·cream·cool·white·kraft·gray 또는 색) `paperTone` `fiber` · `grain`(0~0.3) `grainFps` · `halftone`(0~0.4) `halftoneSize` · `dither` `ditherSize` · `scanlines` · `vignette` · `tint`(색) `tintMode` `tintAmount` · `frame`(액자 두께) · `rgbSplit`({amount, jitter, fps}) · `boil`({amount 0.5~2, fps 6~12, scale}) |
| `shape` | `radius`(CSS 길이, 템플릿의 `--radius`), `stroke`(`hand` 면 손으로 그린 선) |
| `motion` | `pace`(빠름·보통·느림), `bpm`, `ease`(GSAP 이징 이름), `stagger`(글자·어절 사이 간격 배수), `transitions`(장면 쌓기 전환 순서), `stepped`(초당 장 수 4~24. 정하면 움직임이 스톱모션처럼 끊김) |
| `scenes` | 장면 쌓기 모양: `bg`(solid·grid·dots·lines·mesh·aurora·none) `align`(center·left) `card`(flat·glass·outline·paper·shadow) `marker`(highlight·underline·circle·color) `weight`(제목 굵기) `tracking`(자간 em) `case`(upper 면 꼬리표 대문자) `rough`(손그림 선) `schemes`(장면 바탕 순서, 예: `["dark", "paper"]` 면 강조색 바탕을 안 씀. dark 는 스타일·브랜드의 bg) |
| `scenes.title` | 큰 글이 들어오는 방식: `rise`(기본, 아래에서) · `type`(타자, 커서 깜빡) · `slot`(어절이 위에서 떨어져 슬롯처럼 멈춤) · `scramble`(기호에서 글자로 맞춰짐) · `blur`(흐림에서 선명) · `pop`(글자마다 톡) · `mask`(줄마다 선 아래에서 올라옴) · `write`(왼쪽부터 손으로 쓰듯, 끊어서) · `stamp`(크게 쾅) · `fade` |
| `scenes.frame` | 글 장면을 담는 틀: `none` · `window`(앱 창, 위 막대와 점 셋) · `browser`(주소창) · `phone`(폰 화면) · `panel`(콘티 칸, 손 테두리와 번호) · `terminal`(검은 창, 고정폭 글꼴) · `card`(떠 있는 둥근 카드) · `poster`(여백 테두리와 재단 표시) |
| `scenes.deco` | 장면에 깔리는 소품(최대 3개): `cursor`(커서가 강조 말로 와서 누름) · `handles`(제목 둘레 선택 상자와 손잡이) · `orb`(숨 쉬는 빛 구슬) · `rings`(동심원 선) · `dots`(점 판) · `marks`(눈금·재단 표시) · `doodles`(손그림 별·화살표·밑줄) · `stickers`(기운 스티커 꼬리표) · `bubbles`(말풍선) · `speedlines`(만화 집중선) · `scribble`(큰 마커 낙서) · `shapes`(원·네모·세모 흩어짐) · `streaks`(빛줄기가 뒤로 지나감) · `ticker`(아래 흐르는 띠 글) |
| `scenes.number` | 숫자 장면: `count`(기본, 올라감) · `odometer`(자리마다 굴러감) · `scramble`(무작위 숫자에서 맞춰짐) |
| `scenes.scale` | 큰 글 크기 배수(0.8~1.4). 포스터처럼 꽉 채우면 1.25 이상 |
| `signature` | 이 스타일을 알아보게 하는 움직임 1~3개 (Claude Code 가 연출할 때 꼭 넣음) |
| `fits`·`avoid` | 어울리는 상황 / 피할 것 |

## style.md (스타일 카드)

```
# 마커 노트 (손그림)
한 줄: …
## 보는 느낌        화면 구성, 여백, 색 쓰는 비율
## 색               역할별 색과 비율 (바탕 70 · 글자 20 · 강조 10 같은)
## 글자             글꼴 성격, 굵기, 크기 대비, 정렬, 줄 간격
## 질감과 모양       종이·그레인·선 두께·모서리·그림자
## 움직임           속도(BPM), 이징, 들어오고 나가는 방식, 머무는 시간
## 전환             장면을 잇는 방법
## 대표 장면         2~4개. 무엇이 어떻게 움직이는지 + 우리 엔진으로 만드는 법 (S.fx, S.tr, Studio.M)
## 어울리는 곳 / 피할 것
## 배운 곳           사이트, 영상, 몇 초쯤, 무엇을 배웠는지
```

## 스타일 고르기 (Claude 가 쓸 때)

- 브랜드 말투와 상황에 맞게 고르고, 한 영상에는 스타일 하나만.
- `signature` 움직임은 영상에 한 번 이상 넣고, `avoid` 는 지켜요.
- 손그림 계열(`hand: true`)은 글이 적고 따뜻한 상황(교육, 공지, 인사, 모집)에 잘 맞아요.
