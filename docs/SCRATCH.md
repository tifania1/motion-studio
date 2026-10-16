# 처음부터 새로 짜는 영상

템플릿으로는 안 되는 영상을 Claude Code 가 그 영상만을 위해 처음부터 짜는 방법이에요.
앱의 "영상 추가 → 처음부터 새로 짜기"나 `python tools/new_video.py <영상> --brand <브랜드> --scratch "원하는 영상 설명"` 으로 만들면
이런 영상 폴더가 생겨요.

```
videos/<영상>/
  video.json     template 없음, "src": "scene.html", "scratch": true, brief(사용자가 적은 설명), content(글)
  scene.html     시작 파일(engine/starter.html 복사본). 여기를 새로 짭니다
  direction.md   사용자가 적은 설명과 형식
  photos/        사진과 credits.json
```

## 짜는 순서

1. `videos/<영상>/direction.md`, `brands/<브랜드>/brand.json`(voice, about, notes), `CLAUDE.md`(모션·엔진·문구 원칙), `docs/ENGINE.md` 를 읽어요.
   video.json 에 `style` 이 있으면 `styles/<스타일>/style.md`(스타일 카드)와 `docs/STYLES.md` 도 읽고, 그 결(색 비율·글자·질감·움직임·전환)로 짜요.
   질감(look)·글꼴·색 변수는 build 가 알아서 입히니 직접 그리지 않아도 돼요. `S.style.motion`(ease·stagger·bpm)을 타임라인에 쓰고,
   `signature` 움직임은 한 번 이상 넣고 `avoid` 는 피해요. 사용자가 스타일을 안 골랐는데 어울리는 게 있으면 `python tools/styles.py` 목록에서 권해 봐요.
2. 설명이 짧거나 사실 정보(가격·날짜·수치·이름)가 비어 있으면 먼저 사용자에게 물어봐요. 지어내지 않아요.
3. 장면 계획을 짧게 정리해서 보여 줘요: 장면마다 몇 초, 무엇이 보이는지, 기억에 남을 핵심 소품이나 움직임 하나.
   기존 템플릿(`docs/TEMPLATES.md`)으로 충분하면 그 템플릿을 쓰는 게 낫다고 말해 줘요. 장면 쌓기(`scenes`)로 되는 구성이면 그쪽을 권해요.
4. `scene.html` 을 짜요. 자리표시자(`/*@TITLE@*/`, `/*@FONTFACES@*/`, `/*@BRAND_CSS@*/`, `/*@ENGINE_CSS@*/`, `/*@GSAP@*/`, `/*@DATA@*/`, `/*@ENGINE_JS@*/`)는 그대로 둬요.
   다 짜면 맨 위 `MS-STARTER` 줄을 지워요(앱이 이 줄로 "아직 시작 파일"인지 알아봐요).
5. `python tools/check.py <영상>` → `python tools/build.py <영상>` → `python tools/render.py <영상> all sheet` → `python tools/render.py <영상> tall sheet --safe`
   로 장면 모음을 만들고 **sheet 이미지를 직접 열어 봐요.** 글자 넘침, 겹침, 세이프존, 전환 중 빈 화면을 고쳐요.
6. 사용자에게 무엇을 만들었는지, 앱의 어디서 글과 사진을 고치면 되는지 짧게 알려 줘요.

## 꼭 지킬 것

- **글은 content 에.** 화면에 나오는 글·숫자·사진 키는 모두 `video.json` 의 `content` 에 두고 `S.content` 로 읽어요.
  앱의 문구 탭이 content 를 훑어 칸을 자동으로 만들어요. 그래서 구조는 단순하게:
  문자열, 숫자, 문자열 배열, `[글, 글]` 짝 배열, 객체 배열, 깊이 2까지의 객체.
  사진 칸은 키 이름을 `photo`, `photos`, `image`, `images` 로 하거나 값을 `"photo1"` 처럼 써요(앱의 "빈 사진 칸 자동 채우기"가 찾아 채워요).
- **네 비율.** `video.json` 의 `formats` 에 있는 비율을 모두 지원해요. 크기는 `--u`(짧은 변의 1%) 기준, 비율별 배치는 `[data-format="tall"]` 이나 `S.is('tall')`.
  사용자가 한 비율만 원하면 `formats` 를 그 비율로 줄여요.
- **시간의 순수 함수.** 모든 움직임은 `S.tl` 에 시각을 정해 넣거나 `S.ambient(t => ...)`. `setInterval`, rAF 루프, CSS animation·transition, `Date.now()`, 시드 없는 `Math.random()` 은 쓰지 않아요(`M.rng(시드)`는 됨).
- **세이프존.** 글자·로고·버튼은 `.safe` 안(또는 `S.safe` 로 계산한 자리). 배경과 장식은 밖으로 나가도 돼요.
- 글자는 꼭 `S.esc` 로 넣고, 길어질 수 있는 글은 `S.fit` 으로 맞춰요. 빈 값에도 깨지지 않게.
- 색은 브랜드 변수(`--bg --on-bg --on-bg-muted --paper --ink --accent --accent-ink --pattern --glow`)만, 글꼴은 `--font-display/heading/body`.
  영문 큰 글자에 가변 글꼴이 필요하면 `video.json` 에 `"fonts": [{"family": "Archivo", "weight": "100 900", "stretch": "62% 125%", "file": "fonts/Archivo-Variable.woff2"}]` (Geist·Geist Mono 도 있어요).
- 외부 주소(CDN, 웹 글꼴, 원격 이미지)는 쓰지 않아요. 사진은 `python tools/photo.py add|get` 으로 넣고 `S.img(키)` 로 써요.
- 길이 슬라이드(`content.stretch`)는 엔진이 알아서 처리해요. 장면은 원래 시간표로 짜면 돼요. 음악 박자에 맞춘 필름이면 `content.bpm` 을 넣어요(그러면 늘이기를 안 해요).
- 문구 원칙(CLAUDE.md)을 지켜요: 자연스러운 한국어, "~가 아닙니다, ~입니다" 대조 구문 없이, 근거 없는 최상급 표현과 지어낸 후기·수치 없이.

## 다 짠 뒤

- 같은 연출을 다른 영상에도 쓰고 싶어 하면 `/new-template` 으로 템플릿으로 옮길 수 있다고 알려 줘요.
- 앱을 켜 둔 채 고쳤으면 미리보기의 "다시 그리기"를 누르면 바로 보여요.
