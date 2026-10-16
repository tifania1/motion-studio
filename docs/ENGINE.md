# 엔진 API (새 템플릿을 만들 때)

템플릿은 `templates/<이름>/index.html` 한 파일입니다. build.py가 아래 자리표시자를 채웁니다.

```html
<title>/*@TITLE@*/</title>
<style>
/*@FONTFACES@*/   브랜드 글꼴 (쓰인 글자만 잘라 넣음)
/*@BRAND_CSS@*/   :root { --bg --on-bg --on-bg-muted --paper --ink --accent --accent-ink --pattern --glow --font-display --font-heading --font-body }
/*@ENGINE_CSS@*/  엔진 기본 스타일
...템플릿 CSS...
</style>
<div id="viewport"><div id="stage"><div id="cam"></div></div></div>
<script>/*@GSAP@*/</script>
<script>/*@DATA@*/</script>
<script>/*@ENGINE_JS@*/</script>
<script> ...템플릿 코드: Studio.start(S => { ... }) ... </script>
```

함께 `templates/<이름>/example.json`(content 예시)을 두면 `new_video.py` 가 새 영상에 채워 줍니다.

## 화면과 단위

- `#stage` 는 형식 크기(예: 1080×1920) 그대로이고 브라우저 창에 맞게 축소됩니다. 장면은 `#cam` 안에 `<section class="scene">` 로 넣습니다(처음엔 숨김).
- `.safe` 는 세이프존 안쪽 상자입니다. 글자는 여기에 둡니다.
- CSS 변수: `--W`, `--H`, `--u`(짧은 변의 1%), `--safe-t/b/l/r`. 루트에 `data-format="tall|portrait|square|wide"`.

## Studio (S)

| 이름 | 설명 |
|---|---|
| `S.W`, `S.H`, `S.key`, `S.is('tall','portrait')` | 크기와 형식 |
| `S.safe` | `{top,bottom,left,right}` px |
| `S.brand`, `S.content`, `S.img(key)` | brand.json(공개 항목), video.json content, 이미지 data URI |
| `S.$`, `S.$$`, `S.h(html)`, `S.esc(text)` | DOM 도우미. 문구는 꼭 `S.esc` 로 넣기 |
| `S.tl` | GSAP 타임라인(일시정지 상태). 모든 사건은 여기에 시각을 정해 넣음 |
| `S.ambient(t => {...})` | 계속 움직이는 효과. t의 순수 함수여야 함 |
| `S.setDuration(초)` | 영상 길이. 안 정하면 타임라인 길이 |
| `S.start(async S => {...})` | 글꼴·이미지 로드 후 compose 실행, 렌더러/플레이어 연결 |

글자 도우미

- `S.fit(el, {max, maxLines, keepLines, keepMin, maxHeight})`: 상자에 맞게 글자 크기를 줄임. `\n` 으로 나눈 줄 수를 먼저 지키려 함
- `S.words(el)`, `S.chars(el)`: 어절·글자 단위 `<span>` 으로 쪼개 배열 반환 (안의 태그는 사라짐)
- `S.mark(el, '구절')`: 구절을 `.mark` 로 감쌈 → `S.fx.marker` 로 형광펜

효과 `S.fx.*(대상, 시각t, 옵션)`

`rise`(아래에서 올라옴), `pop`(튀어나옴), `slide`(옆에서), `fade`, `out`, `reveal`(왼쪽부터 드러남), `marker`, `stamp`(도장),
`kenburns(img, t, 길이, {from, to, x0, x1})`, `counter(el, t, 길이, from, to, {format})`, `shake(t, 세기)`, `bob(el, 진폭, 속도, 위상)`

전환 `S.tr.*(B, 이전장면, 다음장면)` — B는 다음 장면이 다 보이는 시각

`cut`, `fade`, `wipe`(색 막대 3개), `iris`(원형), `push`(밀어내기), `zoom`, `blades`(6장 조리개), `flood`(검은 원이 덮었다 오므라듦),
`blur`(흐려지며 겹침), `whip`(빠르게 밀며 가로 흔들림 번짐), `blocks`(격자 칸이 차례로 덮었다 걷힘, `{color, n}`)

결 템플릿 공통 (docs/TEMPLATES.md '결 템플릿')

- `S.story(content)`: 공통 content 를 정리해 돌려줌 `{kicker, title, highlight, points[], number|null, photos[{key, src}], photoSlots[], cta{headline, button, sub}, note, logo{img, text, sub}}`. 빈 값은 빠져 있음
- `S.fx.enter(el, t, {highlight, kind, def, d, cps})`: 큰 글 등장. 종류는 kind > 스타일 `scenes.title` > def > rise.
  rise · type(타자와 커서) · slot · scramble · blur · pop · mask(줄마다 선 아래에서) · write(줄마다 끊어 쓰듯) · stamp · fade. 다 들어오는 시각을 돌려줌.
  el 은 글만 든 요소(안의 태그는 없어짐), 크기 맞춤(S.fit)을 먼저 하고 부름. 강조 어절은 `.hl` 클래스
- `S.fx.num(el, t, d, value, {kind, decimals})`: 숫자. count · odometer · scramble (스타일 `scenes.number`). el 에는 숫자만
- `S.ease(기본)`, `S.stg(간격)`, `S.sty()`: 스타일의 이징·간격 배수·장면 힌트(없으면 기본값). `S.easeFn(기본)` 은 S.ambient 안에서 쓸 이징 함수.
  `S.numText(1200)` → "1,200", `S.numText(2026, 0, true)` → "2026"(쉼표 없이, `S.fx.num` 에는 `{plain: true}`)
- 엔진이 쓰는 클래스 이름은 템플릿에서 다른 뜻으로 쓰지 않아요: `.scene .safe .fill .mask .mark .ch .wd .hl .caret .slw .sli .mln .mli .odo .odo-s .m-*`, id `#cam #stage #viewport #ui #bar #cover #seek #time #pp #fs #fx-*`

스타일 (docs/STYLES.md)

- `S.style`: 영상에 고른 스타일의 `id·name·motion·shape·scenes` (없으면 null). `S.style.motion.ease`·`stagger`·`transitions` 를 템플릿이 따라가면 스타일이 살아나요
- `S.look`: 질감 값. 엔진이 `#fx-look` 층(종이·그레인·하프톤·디더·주사선·비네트·색조·액자)과 `#cam` 필터(선 떨림 boil, 색 번짐 rgbSplit)를 알아서 깔아요
- `S.q(t)`: 끊어 그리기(`motion.stepped`) 시각. 엔진이 `__seek` 와 재생에 이미 적용하니 보통은 쓸 일이 없어요

## 발표 자료 (deck)

- `S.stops = [장마다 등장이 끝나는 시각…]`, `S.stopEnter = [숫자로 건너뛸 때 시작 시각…]` 을 compose 안에서 정하면 영상 플레이어 대신 발표 플레이어가 떠요.
  다음 장은 앞 장의 stop 부터 다음 stop 까지 재생하고 멈춰요. 클리커·방향키·스페이스·Enter, 숫자+Enter, Home·End, B·.(검은 화면) W·,(흰 화면), F5·F(전체 화면), 주소 `#번호`.
- `S.idle(it => …)`: 장이 멈춰 있어도 천천히 움직이는 것(그라디언트 덩어리 등). 발표에서는 화면을 연 뒤 흐른 초, 영상에서는 t 를 받아요.
- 렌더 모드에서는 `window.__STOPS` 가 생겨요(`tools/deck.py` 가 씀).

## 모션 도구 Studio.M (engine/motion.js)

한 컷으로 이어지는 필름(키노트·UI 모프·쇼릴)을 짤 때 씁니다. GSAP 타임라인 대신 `S.ambient(render)` 하나에서 매 프레임 모든 스타일을 t로 계산하는 방식에 맞춰져 있습니다.

| 이름 | 설명 |
|---|---|
| `M.spring(t, 'snappy'\|{f, z})` | 0→1 스프링 닫힌 식 (f: 진동수 Hz, z: 감쇠비). 프리셋 snappy·smooth·soft·pop·lead·trail |
| `M.anim([[t0, v0], [t1, v1, spec], …], t)` | 목표가 여러 번 바뀌는 값. 바뀔 때마다 스프링 하나씩 더한 합이라 시간의 순수 함수. 배열 값 가능. spec 에 `{d, e}` 를 주면 이징 |
| `M.at(keys, t)` | 계단 값(글자·상태 이름) |
| `M.beat(n)`, `M.bar(n)`, `M.bpm` | 박자 격자 (`content.bpm`, 기본 120) |
| `M.prog`, `M.ease.*`, `M.lerp`, `M.clamp`, `M.color(a, b, k)` | 기본 수학 |
| `M.box(el, {x, y, w, h, r, bg, o, s, rot})` | 가운데 기준 둥근 사각형 하나를 계속 모프 |
| `M.camera(world, cx, cy, zoom)` | 화면 녹화 앱 같은 확대·이동 (world 는 1080×1080 판) |
| `M.Cursor(parent)` + `M.cursorAt(경로, 클릭, t)` | 클릭·길게 누르기·드래그하는 커서. 경로 `[[도착시각, x, y, 이동시간], …]`, 클릭 `[t \| [t, 누르는시간]]` |
| `M.Iris(svgG)` → `.set(cx, cy, R, open)` | 6장 조리개 (날개 = 육각형 꼭짓점 둘 + 양쪽 변 연장선 + 짧은 호) |
| `M.floodRadius(x, y)` | 화면 네 모서리를 넘는 플러드 반지름 |
| `M.rise(el, k)` | 마스크 선 아래에서 글자가 올라옴 (부모 `.mask` 는 overflow hidden) |
| `M.swap(el, k)` | 짧게 흐려지며 내용 바꾸기 (UI 모프용, 키노트에선 쓰지 않음) |
| `M.type(text, t, t0, cps)` | 타자 치기 |
| `M.rough('line'\|'ellipse'\|'rect', o)` | 손으로 그은 선의 SVG 경로 d (시드 고정). 선 `{x1,y1,x2,y2}`, 동그라미 `{cx,cy,rx,ry,turns}`, 상자 `{x,y,w,h,over}` |
| `M.Glass(host)` → `.set({w, h, r, strength, band, tint})` | 리퀴드 글래스. host 안 `.m-glass-in` 에 뒤 장면 복제를 넣고 위치를 맞춰 줌(변위 지도는 크기가 바뀔 때만 다시 그림) |
| `M.place(el, x, y, {s, sx, sy, rot, o, ax, ay, blur})` | 요소를 (x, y)에 둠. ax·ay 는 요소 안 기준점(0.5 = 가운데), o 가 0이면 숨김 |
| `M.draw(path, k)` | SVG 선 그리기 (0 → 1) |
| `M.inout(t, 들어옴, 나감, 스프링, 나가는 길이)` | 들어올 때 0→1(스프링), 나갈 때 1→2 |
| `M.swing(t, t0, 처음 각도, f, z)` | 감쇠 진자 (매달린 간판·가격표) |
| `M.rng(시드)` | 시드가 있는 난수 (지도 길, 글자판 순서처럼 매번 같아야 할 때) |

필름 템플릿은 `templates/<이름>/template.json` 에 `formats`, 추가 글꼴(`fonts`: 가변 글꼴이면 `"weight": "100 900"`, `"stretch": "62% 125%"`), 렌더 품질(`render`)을 둡니다.

## 지켜야 할 것

- 렌더러는 `window.__seek(t)` 로 아무 시각이나 찍습니다. 화면이 t만으로 정해지게 하세요.
  `setInterval`, rAF 루프, CSS animation/transition, `Date.now()`, 시드 없는 `Math.random()` 금지.
- `fromTo` 는 시작 상태를 바로 적용하므로 같은 요소에 여러 트윈을 걸 때 순서를 주의합니다.
- 외부 리소스 금지(글꼴·이미지·스크립트 모두 build가 넣음).
- 네 형식 모두 `render.py <영상> all sheet` 로 확인합니다. 9:16은 `--safe` 로 세이프존도 봅니다.
- 박자 필름은 `render.py <영상> square beats 1 0.5`(반 박마다 한 장)로 보고, MP4 를 뽑은 뒤 `qa.py` 로 한 프레임 튐과 1초 넘는 멈춤, 루프 이음새를 확인합니다.
- id 이름이 엔진 플레이어와 겹치지 않게 합니다(`ui`, `bar`, `cover`, `seek`, `time`, `pp`, `fs` 는 엔진이 씀).

## 길이 늘이기·줄이기 (content.stretch)

`content.stretch` 가 1이 아니면 `S.start` 가 끝난 뒤 타임라인 속도를 `1/stretch` 로 바꿉니다(0.7~1.8로 제한).
템플릿은 원래 시간표 그대로 짜면 되고, 렌더러가 쓰는 `window.__DURATION`·`window.__seek(t)` 는 늘인 바깥 시간 기준입니다. 원래 길이는 `window.__BASE_DURATION`.
