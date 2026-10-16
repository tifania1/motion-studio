# 모션 스튜디오

여러 광고 계정(브랜드)의 짧은 광고 영상을 모션 그래픽으로 만드는 작업 폴더입니다.
브랜드마다 색·글꼴·로고·마스코트·말투를 `brands/<브랜드>/brand.json` 에 두고, 영상마다 문구와 사진을 `videos/<영상>/video.json` 에 적으면
같은 엔진이 9:16(릴스·쇼츠), 4:5, 1:1, 16:9 네 가지 비율로 만들어 냅니다.
HTML + GSAP으로 장면을 짜고, 헤드리스 크로미움으로 한 프레임씩 찍어 MP4로 뽑습니다.

사용자는 유니티 개발자이고 Windows PC에서 이 폴더를 씁니다. 대답과 문구는 한국어로 합니다.

## 폴더

- `brands/<슬러그>/brand.json` 브랜드 키트: colors, fonts, type, pattern, logo/logoText/logoSub, mascot, assets, voice(말투), about(참고 정보), notes(꼭 지킬 규칙)
- `brands/_template/` 새 브랜드의 틀 · `brands/bax/` Bax(태국 왕자 고양이) · `brands/haru-cafe/` 템플릿 예시용 가상 카페
- `videos/<영상>/video.json` 영상 설정과 문구, `videos/<영상>/photos/` 사진과 `credits.json`(출처)
- `templates/promo/` 사진형 광고: 훅 → 사진 장면들 → 장점 → 숫자 → CTA
- `templates/kinetic/` 글자형 광고: 짧은 문장 장면(beats) → CTA. 사진이 없을 때, 세일·이벤트·공지
- `engine/studio.js`, `engine/studio.css` 공용 엔진(타임라인, 효과, 전환, 세이프존, 플레이어)
- `tools/` 명령들, `fonts/` 한글 전체가 들어간 Noto Sans/Serif KR과 Cinzel, `vendor/gsap.min.js`
- `docs/TEMPLATES.md` 템플릿별 content 항목 설명, `docs/ENGINE.md` 엔진 API(새 템플릿을 만들 때)
- `out/<영상>/<형식>/` 결과물(지워도 다시 만들 수 있음), `out/_app/` 앱이 쓰는 임시 파일
- `tools/app.py` + `app/` 화면으로 쓰는 앱(GUI). 바탕화면 "모션 스튜디오" 아이콘이 이걸 띄웁니다. 사용자가 앱 화면을 고쳐 달라고 하면 `app/app.js`, `app/app.css` 를 고칩니다

## 명령

Windows에서 `python` 이 안 잡히면 `py -3` 으로 바꿔 실행합니다.

```
python tools/list.py                                   # 브랜드·영상 목록과 상태
python tools/new_brand.py <슬러그> --name "이름" [--palette 로고.png] [--accent "#hex"] [--light] [--logo f] [--mascot f]
python tools/new_video.py <영상> --brand <슬러그> [--template promo|kinetic] [--formats tall,portrait]
python tools/photo.py search "영어 검색어"              # 위키미디어 CC0·CC BY 사진 찾기
python tools/photo.py get <영상> "File:이름.jpg" --as <키>   # 받기 + 출처 기록 + assets 등록
python tools/photo.py add <영상> 내사진.jpg --as <키>        # 사용자 사진 넣기
python tools/check.py <영상>                            # 빠진 파일·긴 문구·출처·광고 표현 점검
python tools/build.py <영상> [형식]                     # out/<영상>/<형식>/<영상>-<형식>.html (브라우저로 열어 미리보기)
python tools/render.py <영상> all sheet [--safe]        # 검수용 장면 모음 sheet.png (세이프존 겹쳐 보기)
python tools/render.py <영상> tall shots 1.2 5.0        # 지정 초의 PNG
python tools/render.py <영상> all video                 # master.mp4 (무음, 시간이 걸림)
python tools/finalize.py <영상> all [--music 곡.mp3]    # 업로드용 <영상>_<형식>.mp4 (음악 없으면 무음 오디오 트랙)
python tools/photo.py credits <영상>                    # 게시글에 붙일 사진 출처 CREDITS.md
python tools/cutout.py 입력.png 출력.png                # 배경 지우기 (requirements-tools.txt 필요)
```

## 앱과 같이 쓸 때

- 사용자는 앱에서 계정·문구·사진·음악을 만지고, 앱의 "Codex 열기"로 이 폴더에서 Codex를 엽니다. 둘은 같은 파일(brand.json, video.json)을 씁니다.
- 앱이 쓰는 video.json 추가 항목: `brief`(Codex에게 맡긴 요청 메모), `music`(`{"file":"music.mp3","volume":0.8,"fadeIn":0.5,"fadeOut":2.5,"start":0}`). MP4를 만들 때 `music` 이 있으면 `finalize.py --music` 으로 합칩니다.
- 앱의 "Codex에게 문구 맡기기"는 `Codex -p` 로 content JSON 초안만 받습니다. 파일은 앱이 고칩니다.

## 작업 순서 (광고 영상 하나)

1. `brand.json` 의 voice, about, notes 를 먼저 읽습니다. notes 는 반드시 지킵니다.
2. 사진이 있으면 promo, 없으면 kinetic. 다른 연출이 필요하면 새 템플릿을 만듭니다(`/new-template`).
3. 문구를 쓰고, 사실 정보는 검색으로 확인합니다(아래 문구 원칙).
4. `new_video.py` → video.json 의 content 채우기 → 사진 넣기 → `check.py`
5. `build.py` → `render.py <영상> all sheet` 와 `render.py <영상> tall sheet --safe` → **sheet 이미지를 Read로 직접 열어 봅니다.**
   글자 넘침·겹침, 세이프존 침범, 사진 초점(focus), 전환 중 빈 화면, 오탈자를 확인하고 고칩니다.
6. 사용자가 원하면 `render.py ... video` → `finalize.py` → `ffprobe` 로 길이·해상도·오디오 트랙을 확인하고 경로를 알려 줍니다.

## 엔진 규칙 (렌더 결과가 어긋나지 않게)

- 모든 움직임은 GSAP 타임라인 `S.tl` 에 시각을 정해 넣거나, 시간 t의 순수 함수 `S.ambient(t => ...)` 로 만듭니다.
  렌더러가 `window.__seek(t)` 로 아무 시점이나 찍기 때문입니다. `setInterval`, `requestAnimationFrame` 루프, CSS `animation`/`transition`, `Date.now()`, 시드 없는 `Math.random()` 은 쓰지 않습니다.
- 크기는 `--u`(짧은 변의 1%) 기준으로 잡아 네 비율에서 같은 느낌이 나게 합니다. 비율별 배치는 `[data-format="tall"]` 같은 CSS로 나눕니다.
- 외부 주소(CDN, 웹 글꼴, 원격 이미지)를 쓰지 않습니다. build가 글꼴·이미지·GSAP을 한 파일에 넣습니다.

## 세이프존 (플랫폼 UI가 덮는 영역)

- 9:16 기본은 `reels`(위 270px, 아래 672px, 좌우 65px). 스토리는 `stories`(아래 384px), 쇼츠만 올리면 `shorts`(위 288, 아래 480, 오른쪽 140).
  `video.json` 의 `"safe": {"tall": "reels"}` 로 고르고, 직접 `{"top":..,"bottom":..,"left":..,"right":..}` 도 됩니다.
- 글자, 로고, 버튼은 세이프존 안에만 둡니다. 배경과 마스코트 일부는 밖으로 나가도 됩니다.
- 4:5·1:1·16:9 는 가장자리 54px(16:9는 좌우 96px)만 비웁니다.

## 문구 원칙

- 사람이 실제로 말하듯 자연스러운 한국어로 씁니다. "~가 아닙니다, ~입니다" 같은 대조 구문은 쓰지 않습니다.
- 브랜드 voice 의 말투(해요체, 반말 등)를 따릅니다. 한 장면 한 메시지, 줄바꿈은 `\n` 으로 직접 넣습니다.
- 훅은 첫 2초 안에 읽히게 짧게(24자 안쪽). 숫자·혜택·질문이 잘 먹힙니다.
- 영업시간·가격·수상·순위 같은 사실은 넣기 전에 검색으로 확인하고, 바뀌기 쉬운 정보 옆이나 엔딩에 "가기 전에 확인하세요" 같은 안내를 둡니다.
- 광고 표현: "최고·1위·최초·유일·100%·무조건" 같은 말은 근거가 있을 때만 씁니다. 지어낸 후기·평점·인증, 실제와 다른 할인·가격,
  의료·효능 단정은 넣지 않습니다. 협찬·제휴 콘텐츠면 "광고" 또는 "유료 광고 포함" 표시를 넣습니다.
- 가상 브랜드(haru-cafe 등)로 만든 예시에는 "템플릿 예시용 가상 브랜드입니다" 같은 표시를 남깁니다.

## 이미지

- 우선순위: 사용자가 준 사진 → CC0·퍼블릭 도메인 → CC BY(화면에 `Photo: 저작자 · 라이선스` 표시). CC BY-SA, NC, ND 는 광고에 쓰지 않습니다.
- 실제 그 가게·상품 사진이 아니면 "참고 사진"이라고 표시합니다. 실존 인물 사진을 추천·보증처럼 쓰지 않습니다.
- 위키미디어는 `tools/photo.py` 로 받습니다(표준 크기 썸네일, User-Agent, 요청 간격, 429 재시도가 들어 있음).
- 영상용 이미지를 새로 그려야 하면, 사용자는 ChatGPT 웹에서 고화질로 만드는 쪽을 선호합니다. 프롬프트를 정리해 드리고, 받은 파일은 `photo.py add` 로 넣습니다.
- 투명 배경이 필요한 로고·마스코트·제품은 `tools/cutout.py` 로 배경을 지웁니다.

## 비용이 드는 도구

- Artlist, Kling 같은 생성 도구는 유료 크레딧이 들 수 있습니다. 생성하기 전에 무료·무제한 범위인지 먼저 확인하고, 반드시 사용자에게 비용을 알리고 허락을 받습니다.

## 배경음악

- 사용자가 음원 파일을 주면 `finalize.py <영상> all --music 곡.mp3 [--volume 0.8] [--fade-out 2.5]`.
- 무료로 새 곡이 필요하면 Google Vids 음악 생성(Lyria)을 씁니다. 자세한 순서는 `/music` 스킬에 있습니다.
- 오디오 트랙이 없는 MP4는 일부 서비스(Google Vids 등)가 거절하므로 finalize 는 음악이 없어도 무음 트랙을 넣습니다.

## 검수와 전달

- 무엇이든 만든 뒤에는 직접 확인하고 전달합니다. sheet 이미지를 열어 보고, 영상은 `ffprobe -v error -show_entries format=duration:stream=codec_name,width,height -of compact <파일>` 로 확인합니다.
- 전달할 때는 파일 경로, 길이, 비율, 확인한 점, 남은 확인 사항(사실 정보, 출처)을 짧게 알려 줍니다.

## 스킬 (슬래시 명령)

- `/new-brand` 광고 계정 추가 · `/new-ad` 광고 영상 만들기 · `/ad-review` 올리기 전 검수
- `/render-mp4` 업로드용 MP4 뽑기 · `/music` 배경음악 · `/new-template` 새 연출 템플릿
