# 모션 스튜디오

여러 광고 계정(브랜드)의 짧은 광고 영상을 모션 그래픽으로 만드는 작업 폴더입니다.
브랜드마다 색·글꼴·로고·마스코트·말투를 `brands/<브랜드>/brand.json` 에 두고, 영상마다 문구와 사진을 `videos/<영상>/video.json` 에 적으면
같은 엔진이 9:16(릴스·쇼츠), 4:5, 1:1, 16:9 네 가지 비율로 만들어 냅니다.
HTML + GSAP으로 장면을 짜고, 헤드리스 크로미움으로 한 프레임씩 찍어 MP4로 뽑습니다.

사용자는 유니티 개발자이고 Windows PC에서 이 폴더를 씁니다. 대답과 문구는 한국어로 합니다.

## 폴더

- `brands/<슬러그>/brand.json` 브랜드 키트: colors, fonts, type, pattern, logo/logoText/logoSub, mascot, assets, voice(말투), about(참고 정보), notes(꼭 지킬 규칙)
- `brands/_template/` 새 브랜드의 틀 · `brands/bax/` Bax(태국 왕자 고양이) · `brands/haru-cafe/` 템플릿 예시용 가상 카페 · `brands/lumenta-demo/` 기업용 템플릿 예시용 가상 기업(밝은 바탕)
- `videos/<영상>/video.json` 영상 설정과 문구, `videos/<영상>/photos/` 사진과 `credits.json`(출처)
- `templates/promo/` 사진형 광고: 훅 → 사진 장면들 → 장점 → 숫자 → CTA
- `templates/kinetic/` 글자형 광고: 짧은 문장 장면(beats) → CTA. 사진이 없을 때, 세일·이벤트·공지
- `templates/scenes/` 장면 쌓기(자유 구성): 표지·문장·사진·숫자·목록·단계·비교·인용·막대 그래프·사진 여러 장·로고 장면(content.scenes)을 원하는 순서로 → CTA. 상황에 맞는 템플릿이 없을 때
- `templates/keynote/` 1:1 키노트 필름(한 컷으로 이어짐, 루프). `content.film` 이 `launch`(런칭·주문, 54박) 또는 `channel`(채널 브랜딩, 40박)
- `templates/uimorph/` 1:1 UI 모프 루프(도형 하나가 버튼→…→토스트→버튼, 120BPM 7마디 14초)
- `templates/showreel/` 1:1 15초 쇼릴(30박)
- 필름 세 가지는 `templates/<이름>/template.json` 에 글꼴(Archivo·Geist 가변 글꼴)과 렌더 품질(60fps, 모션 블러, 1440px)이 들어 있음
- 상황 프리셋용 템플릿 10개(네 비율): `menu` 신메뉴 쇼케이스, `sale` 세일 가격표, `opening` 매장 오픈, `greeting` 시즌 인사 카드, `academy` 수강생 모집 노트,
  `event` 행사 티켓, `hiring` 채용 메신저, `notice` 공지 안내판, `travel` 여행 지도, `stats` 성과 대시보드. 항목은 `docs/TEMPLATES.md`
- 기업용 상황 템플릿 4개(네 비율): `company` 회사 소개(설계도 → 명함), `product` 제품·서비스 소개(엉킨 선 → 제품 창), `timeline` 연혁(연도 자·주행거리계 연도), `news` 소식 발표(뉴스 화면·협약·투자·수상·인증·출시)
- 결 템플릿 10개(네 비율, 모두 같은 content 를 읽음): `typeslam` 타이포 쇼, `uidemo` 제품 화면 시연, `sketchbook` 손그림 노트, `dataflow` 데이터 흐름, `terminal` 레트로 터미널,
  `collage` 종이 콜라주, `stage` 사물 무대, `glow` 빛과 그라디언트, `brandmark` 도형으로 짜는 브랜드, `cinema` 시네마틱.
  공통 content `{kicker, title, highlight, points[], number{prefix,value,suffix,label,source}, photos[], cta{headline,button,sub}, note}` 라서 문구는 그대로 두고 템플릿만 바꿀 수 있음(앱 연출 탭 '결 바꾸기').
  엔진 `S.story()`·`S.fx.enter`·`S.fx.num` 이 공통 부분을 맡고, 큰 글·숫자 등장 방식은 스타일의 `scenes.title`·`scenes.number` 를 따라감
- `templates/deck/` 발표 자료(16:9, `template.json` 의 `"deck": true`): `content.slides` 의 장(cover·agenda·section·bullets·cards·statement·number·stats·chart·compare·steps·image·quote·closing)을 한 장씩 넘겨요.
  엔진 발표 플레이어가 장마다 등장이 끝나는 시각(`S.stops`)에서 멈추고 클리커·방향키·숫자+Enter·B/W·F5 로 다뤄요. 강조색 도형(#dk-mo)이 장을 따라 모양을 바꿔요.
  `tools/deck.py pdf|sheet <발표>` 로 PDF·장 모음, `tools/deck.py source <발표> <파일>` 로 PPTX·PDF·DOCX·HWPX·TXT 자료를 `source.md`(와 photos/source*.jpg)로 넣어요. 항목은 `docs/TEMPLATES.md` 'deck'
- 처음부터 짜는 영상: template 없이 `videos/<영상>/scene.html`(시작 파일 `engine/starter.html`)과 `"scratch": true`. 짜는 순서와 규칙은 `docs/SCRATCH.md`
- `presets/<상황>/` 프리셋 27개(상황 17개 + 결 템플릿 10개, 결 프리셋은 `"group": "look"` 과 기본 `"style"`): `preset.json`(템플릿·형식·길이·필요한 사진·물어볼 정보·확인할 것·음악)과 `direction.md`(연출 프롬프트).
  신메뉴 출시·세일·매장 오픈·시즌 인사·수강생 모집·행사 안내·채용·앱 기능 소개(uimorph)·공지·채널 홍보(keynote channel)·여행 하이라이트·숫자로 보는 성과,
  기업용: 회사 소개·제품·서비스 소개·연혁·마일스톤·소식 발표, 그리고 `custom` 장면 쌓기(`"group": "free"` 라 앱에서 '직접 만들기' 줄에 보임)
- `styles/<스타일>/` 스타일 라이브러리 180개(손그림 13개). `styles/_review/` 는 자동 학습에서 점검(7점)을 넘지 못해 따로 빼 둔 후보라 목록에 나오지 않음(손봐서 styles/ 로 옮기면 쓸 수 있음): keyframe.gallery 같은 잘 만든 프로덕트 모션에서 배운 보는 결·움직이는 결. style.json 의 `template` 은 어울리는 결 템플릿. `style.json`(색·글꼴·질감·모양·움직임·장면 쌓기 모양), `style.md`(스타일 카드), `thumb.jpg`.
  video.json 의 `style` 로 고르고(앱: 연출 탭 → 스타일), `styleColors`(스타일 색, 기본 끔)·`styleFonts`(기본 켬)·`styleLook`(질감, 기본 켬). 규칙과 키는 `docs/STYLES.md`
- `engine/studio.js`, `engine/studio.css` 공용 엔진(타임라인, 효과, 전환, 세이프존, 플레이어, 스타일 질감 층)
- `engine/motion.js` 모션 도구(Studio.M): 닫힌 식 스프링, 박자 격자, 카메라, 커서, 6장 조리개, 플러드, 마스크 선 글자, 리퀴드 글래스
- `tools/` 명령들, `fonts/` 한글 전체가 들어간 Noto Sans/Serif KR과 Cinzel, 손글씨 나눔손글씨 펜·붓, 개구, Caveat(영문), 한글 명조 고운바탕, 한글 픽셀 갈무리11, Instrument Serif·Silkscreen(영문), `vendor/gsap.min.js`
- `docs/TEMPLATES.md` 템플릿별 content 항목 설명, `docs/ENGINE.md` 엔진 API(새 템플릿을 만들 때), `docs/SCRATCH.md` 처음부터 짜는 영상
- `out/<영상>/<형식>/` 결과물(지워도 다시 만들 수 있음), `out/_app/` 앱이 쓰는 임시 파일
- `installer/` 설치 파일 재료(install.ps1, Install_MotionStudio.cmd, README.txt, 예시 목록 examples.json), `dist/` 만든 설치 파일(지워도 됨)
- `tools/app.py` + `app/` 화면으로 쓰는 앱(GUI). 바탕화면 "모션 스튜디오" 아이콘이 이걸 띄웁니다. 사용자가 앱 화면을 고쳐 달라고 하면 `app/app.js`, `app/app.css` 를 고칩니다

## 명령

Windows에서 `python` 이 안 잡히면 `py -3` 으로 바꿔 실행합니다.

```
python tools/list.py                                   # 브랜드·영상 목록과 상태
python tools/new_brand.py <슬러그> --name "이름" [--palette 로고.png] [--accent "#hex"] [--light] [--logo f] [--mascot f]
python tools/new_video.py <영상> --brand <슬러그> [--template promo|kinetic] [--formats tall,portrait]
python tools/new_video.py <영상> --brand <슬러그> --preset <상황>   # 상황 프리셋으로 (연출 프롬프트가 videos/<영상>/direction.md 로)
python tools/new_video.py <영상> --brand <슬러그> --scratch "원하는 영상 설명"   # 템플릿 없이 처음부터 (docs/SCRATCH.md)
python tools/presets.py                                # 상황 프리셋 목록 · python tools/presets.py show <상황> 연출 프롬프트
python tools/styles.py                                 # 스타일 목록 · show <스타일> 스타일 카드 · check 점검 · thumbs 썸네일
python tools/learn_gallery.py status                   # API 로 갤러리 스타일 자동 학습 진행 상황 (run --budget <달러> 로 돌림, 점검 통과만 styles/ 에 남김)
python tools/deck.py pdf <발표>                         # 발표 자료 PDF (장마다 등장이 끝난 화면, 3840×2160) · sheet 는 검수용 장 모음 slides.png
python tools/deck_pptx.py <발표>                        # 고칠 수 있는 PowerPoint: 글 상자·도형·그림, 장마다 등장 애니메이션, 강조 도형 모핑 전환, 발표 메모, 글꼴 포함
python tools/deck.py source <발표> 자료.pptx             # 가진 자료의 글·그림을 발표 폴더에 (Claude 가 구성할 때 source.md 를 읽음)
python tools/photo.py search "영어 검색어"              # 위키미디어 CC0·CC BY 사진 찾기
python tools/photo.py get <영상> "File:이름.jpg" --as <키>   # 받기 + 출처 기록 + assets 등록
python tools/photo.py add <영상> 내사진.jpg --as <키>        # 사용자 사진 넣기
python tools/check.py <영상>                            # 빠진 파일·긴 문구·출처·광고 표현 점검
python tools/build.py <영상> [형식]                     # out/<영상>/<형식>/<영상>-<형식>.html (브라우저로 열어 미리보기)
python tools/render.py <영상> all sheet [--safe]        # 검수용 장면 모음 sheet.png (세이프존 겹쳐 보기)
python tools/render.py <영상> tall shots 1.2 5.0        # 지정 초의 PNG
python tools/render.py <영상> all video                 # master.mp4 (무음, 시간이 걸림. video.json/template.json 의 render 로 60fps·모션 블러·해상도)
python tools/render.py <영상> square beats [묶음] [밀기]  # 박마다 한 장씩 찍은 beats.png (밀기 0.5 = 반 박 뒤)
python tools/qa.py <영상> [형식]                         # master.mp4 프레임 검사: 한 프레임 튐, 1초 넘는 멈춤, 루프 이음새
python tools/finalize.py <영상> all [--music 곡.mp3]    # 업로드용 <영상>_<형식>.mp4 (음악은 -14 LUFS 로 맞춤, 없으면 무음 트랙)
python tools/music.py gen <영상> --mood cafe --yes      # 구글 Gemini(Lyria)로 연주곡 생성 → 박자 분석 → video.json music 연결 (유료, 곡당 0.04~0.08달러)
python tools/music.py prompt <영상> --mood keynote      # Gemini 앱(무료)에 붙여 넣을 프롬프트
python tools/music.py beats 곡.mp3 [--bpm 120]          # BPM·첫 다운비트 분석
python tools/photo.py credits <영상>                    # 게시글에 붙일 사진 출처 CREDITS.md
python tools/cutout.py 입력.png 출력.png                # 배경 지우기 (requirements-tools.txt 필요)
python tools/upload.py kit <영상>                       # 업로드 안내 묶음 out/<영상>/upload/ (플랫폼별 영상·커버·글·체크리스트)
python tools/upload.py youtube-upload <영상> [tall|wide] [--privacy private]   # 연결된 채널로 유튜브 업로드 (docs/UPLOAD.md)
python tools/make_installer.py [--with-renders]         # 완전한 설치 파일 dist/MotionStudioSetup.zip (예시 브랜드·영상만, 풀어서 점검까지)
python tools/update.py [--check|--rollback]             # GitHub 저장소에서 새 버전 받기 (앱이 켜질 때 자동으로 돎)
```

## 앱과 같이 쓸 때

- 사용자는 앱에서 계정·문구·사진·음악을 만지고, 앱의 "Claude Code 열기"로 이 폴더에서 Claude Code를 엽니다. 둘은 같은 파일(brand.json, video.json)을 씁니다.
- 앱이 쓰는 video.json 추가 항목: `brief`(Claude에게 맡긴 요청 메모), `music`(`{"file":"music/gemini-….mp3","volume":0.9,"fadeIn":0,"fadeOut":2,"start":0.52,"bpm":120}`). `start` 는 곡의 첫 다운비트라 영상 0초에 박이 맞습니다. MP4를 만들 때 `music` 이 있으면 `finalize.py --music` 으로 합칩니다.
- 앱의 "음악 만들기": Gemini API(자동, 비용 확인 대화상자) 또는 Gemini 앱(무료, 프롬프트 복사 → 받은 MP3 끌어다 놓기). 받은 곡은 앱이 박자를 재서 `start`·`bpm` 을 채웁니다. 사진형·글자형은 "장면 바뀌는 순간을 박자에 맞추기" 버튼이 장면 길이를 2박 단위로 맞춥니다.
- API 키는 앱 오른쪽 위 "AI 계정"(또는 `python tools/accounts.py`)에서 Claude·Gemini 키를 여러 개 저장해 두고 골라 씁니다. 사용자 폴더 `.motion-studio/accounts.json` 에만 저장되고(Windows 는 DPAPI 암호화), 프로젝트 폴더에는 저장하지 않습니다. 키 값을 화면·로그·파일에 그대로 쓰지 않습니다.
- 앱의 Claude 연결 방식(`settings.json` 의 `claude_engine`): 기본은 이 PC의 Claude Code 로그인(`claude -p`), `api` 면 고른 Claude API 계정으로 Messages API 를 바로 부릅니다(모델 opus→claude-opus-5-5, sonnet→claude-sonnet-5-5, haiku→claude-haiku-5-5, 노력은 `output_config.effort`). 작업 기록에 쓴 토큰과 대략의 요금이 남습니다.
  고른 쪽으로 앱의 모든 Claude 작업이 돕니다. API 방식이면 Claude Code 창을 열지 않고, "Claude Code 열기"·"Claude Code에게 맡기기"·"처음부터 새로 짜기" 대신 앱 안 "Claude에게 부탁하기 (API)"(`tools/agent.py`)가 같은 일을 합니다:
  이 CLAUDE.md 를 시스템 프롬프트로 받고 list_files·read_file·write_file·edit_file·run_tool(check·build·render 등)·view_image 도구로 파일을 고치고 빌드·장면 모음 확인까지 합니다.
  tools/ app/ installer/ vendor/ fonts/ out/ 은 고치지 않고, 유료 생성(music gen 등)은 돌리지 않습니다. 대화는 `out/_app/agent/<세션>.json` 에 남아 '이어서 부탁하기'로 계속하고, 부탁 한 번 예산(`settings.json` 의 `agent_budget`, 기본 3달러)을 넘으면 멈춥니다.
  구독 방식이면 모든 작업이 이 PC의 Claude Code 로그인으로 돌고, 앱은 ANTHROPIC_API_KEY 를 빼고 Claude Code 를 엽니다.
- 앱에서 고른 Claude 모델·노력 정도는 사용자 폴더 `.motion-studio/settings.json` 의 `claude_model`(opus·sonnet·haiku, 비우면 기본: 문구는 Opus, 업로드 글·사진 검색어는 Sonnet)과 `claude_effort`(low~max, 비우면 기본)에 저장되고 앱의 모든 `claude -p` 호출과 "Claude Code 열기"에 `--model`·`--effort` 로 붙습니다.
- 앱의 영상 탭은 작업 순서대로 문구 → 사진 → 음악 → 연출 → 올리기, 그 뒤에 설정·고급입니다. 연출 탭의 "Claude Code에게 이 연출로 맡기기"는 앞 단계가 비어 있으면 먼저 확인합니다.
- 앱의 "Claude에게 문구 맡기기"는 `claude -p` 로 content JSON 초안만 받습니다. 파일은 앱이 고칩니다. 영상에 `direction.md` 가 있으면 그 연출 프롬프트도 함께 보냅니다.
- 앱의 사진 자동 찾기: Claude 가 검색어를 정해 위키미디어에서 후보를 찾은 뒤, 칸마다 후보 썸네일을 번호 붙인 한 장으로 모아 Claude 가 직접 보고
  지금 상황(브랜드·요청 메모·첫 문장·스타일·칸 옆 문구)에 어울리는지 0~10점과 이유를 매겨 점수 순으로 놓습니다. 6점 아래는 흐리게 보이고 미리 고르지 않으며,
  어울리는 후보가 없는 칸은 Claude 가 준 새 검색어로 한 번 더 찾아 다시 검토합니다.
- 앱의 "영상 추가"는 상황 프리셋을 먼저 고르게 합니다. 만들어진 영상의 video.json 에는 `preset`(상황 이름), `target`(길이), `musicHint`(음악 분위기·BPM·구간)가 들어갑니다.
  아래 '직접 만들기' 줄: 장면 쌓기(scenes, 앱 문구 탭에서 장면을 더하고 옮기고 종류를 바꿈, "Claude에게 구성·문구 맡기기"가 장면 종류와 순서까지 짬),
  처음부터 새로 짜기(설명을 적으면 scratch 영상을 만들고 Claude Code 를 `docs/SCRATCH.md` 대로 짜 달라는 말로 엶), 템플릿 고르기.
- 처음부터 짠 영상도 화면 글은 video.json 의 content 에 두고 HTML 에서 S.content 로 읽습니다. 그래야 앱 문구 탭이 칸을 자동으로 만들어 고칠 수 있어요.
  scene.html 맨 위의 `MS-STARTER` 줄은 "아직 시작 파일"이라는 표시라 다 짜면 지웁니다.
- 앱의 "올리기" 탭: video.json 의 `upload`(title, description, caption, hashtags, coverAt, privacy, paid, done)와 brand.json 의 `social`(instagram, youtube, hashtags, footer)을 씁니다.
  유튜브는 OAuth 로 계정(브랜드)마다 채널을 연결해 바로 올리고(검수 전 프로젝트는 비공개로만 올라감), 인스타그램은 안내 묶음으로 올립니다. 토큰은 사용자 폴더 `.motion-studio/` 에만 저장합니다.
  유튜브 업로드는 공개 게시라 사용자가 앱에서 직접 누르거나, Claude Code 에서는 사용자 확인을 받은 뒤에만 실행합니다.
- 앱의 연출 탭 "스타일": 스타일을 고르면 video.json 에 `style` 이 들어가고, Claude 에게 문구를 맡기거나 Claude Code 를 열 때 그 스타일 카드(style.md)를 따르라는 말이 같이 갑니다.
  스타일이 있는 영상을 다듬을 때는 `styles/<스타일>/style.md` 를 읽고 signature 움직임을 넣고 avoid 를 피합니다.
- 앱의 "Claude Code에게 이 연출로 맡기기"는 Claude Code 를 열면서 `videos/<영상>/direction.md 의 연출 프롬프트대로 다듬어 줘` 로 시작합니다. 이때는 direction.md 를 먼저 읽고 그 장면·박자·글 규칙을 따릅니다.

## 발표 자료 만들 때

- `/new-deck` 스킬. `python tools/new_video.py <발표> --brand <브랜드> --template deck` 로 만들고 `content.slides` 를 씁니다.
- 자료가 있으면 `videos/<발표>/source.md` 를 먼저 읽고 그 사실만 씁니다. 화면 글은 짧게(제목 26자, 글머리 30자 안쪽), 자세한 말은 장마다 `notes`(발표 메모, 화면에 안 나옴)에.
- 첫 장 cover, 마지막 closing. 덩어리가 여럿이면 agenda 와 section. 숫자는 number·stats·chart, 전후는 compare, 일정은 steps.
- 검수: `build.py <발표>` → `deck.py sheet <발표>` → `out/<발표>/wide/slides.png` 를 Read 로 열어 넘침·겹침을 봅니다. 전달은 HTML(발표용), `deck_pptx.py`(PowerPoint, 고칠 수 있음), `deck.py pdf`(나눠 주기).

## 작업 순서 (광고 영상 하나)

1. `brand.json` 의 voice, about, notes 를 먼저 읽습니다. notes 는 반드시 지킵니다.
2. 상황에 맞는 프리셋이 있으면 그걸로 시작합니다(`python tools/presets.py`). 없으면 사진이 있으면 promo, 없으면 kinetic. 다른 연출이 필요하면 새 템플릿을 만듭니다(`/new-template`).
   영상 폴더에 `direction.md` 가 있으면 먼저 읽고 그 연출을 따릅니다. 새 템플릿·새 상황을 만들 때는 기존 영상과 첫눈에 확 달라 보이게(바탕·구도·핵심 소품·움직임) 짭니다.
3. 문구를 쓰고, 사실 정보는 검색으로 확인합니다(아래 문구 원칙).
4. `new_video.py` → video.json 의 content 채우기 → 사진 넣기 → `check.py`
5. `build.py` → `render.py <영상> all sheet` 와 `render.py <영상> tall sheet --safe` → **sheet 이미지를 Read로 직접 열어 봅니다.**
   글자 넘침·겹침, 세이프존 침범, 사진 초점(focus), 전환 중 빈 화면, 오탈자를 확인하고 고칩니다.
6. 사용자가 원하면 `render.py ... video` → `finalize.py` → `ffprobe` 로 길이·해상도·오디오 트랙을 확인하고 경로를 알려 줍니다.

## 모션 원칙 (필름 템플릿, 새 연출을 짤 때)

- 박자 격자 위에서 짭니다. 120BPM 이면 1박 0.5초, 박마다 무언가가 일어나게. `M.beat(n)` 을 씁니다.
- 움직임은 스프링(`M.spring`, `M.anim`)으로. 넘침은 아주 조금만(감쇠비 0.8 이상). 바운스 이징, 파티클, 글로우는 쓰지 않습니다.
- 키노트 스타일에서는 장면을 자르거나 서서히 겹치지 않습니다. 앞 장면의 물건이 모양을 바꿔(모프) 다음 장면이 되게, 또는 검은 플러드·조리개로 잇습니다.
- 드래그는 누르는 동안 커서 위치로 값을 직접 계산하고, 놓으면 그 자리에서 스프링으로 돌아갑니다.
- 루프 영상은 마지막 프레임 = 첫 프레임(커서 위치·속도 포함). `qa.py` 의 루프 검사로 확인합니다.
- 카메라가 확대하는 요소에는 `will-change` 를 쓰지 않습니다(글자가 흐려짐). 숨긴 부모 안 자식은 `visibility: inherit` 로.
- 검수: `render.py <영상> square beats 1 0.5` 로 반 박마다 한 장 → `render.py … video` → `qa.py` 로 한 프레임 튐 확인.

## 엔진 규칙 (렌더 결과가 어긋나지 않게)

- 모든 움직임은 GSAP 타임라인 `S.tl` 에 시각을 정해 넣거나, 시간 t의 순수 함수 `S.ambient(t => ...)` 로 만듭니다.
  렌더러가 `window.__seek(t)` 로 아무 시점이나 찍기 때문입니다. `setInterval`, `requestAnimationFrame` 루프, CSS `animation`/`transition`, `Date.now()`, 시드 없는 `Math.random()` 은 쓰지 않습니다.
- `content.stretch`(0.7~1.6, 앱 연출 탭의 영상 길이 슬라이드)는 엔진이 전체 속도를 바꿔 길이를 늘이고 줄입니다. 템플릿은 원래 시간표로 짜고, `window.__DURATION`·`__seek` 는 늘인 바깥 시간 기준입니다(필름 템플릿은 박자 때문에 쓰지 않음).
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
- 구글 Gemini API 의 음악(Lyria)도 무료 등급이 없습니다(영상 28초 이하는 30초 곡 0.04달러, 더 길면 0.08달러). `music.py gen` 은 `--yes` 없이는 비용만 알리고 멈춥니다. 사용자에게 허락을 받은 뒤에만 `--yes` 를 붙입니다.

## 배경음악

- 사용자가 음원 파일을 주면 `music.py beats` 로 박을 재고 `finalize.py <영상> all --music 곡.mp3 --start <첫 다운비트>`.
- 새 곡: 구글 Gemini. 자동(유료, 키 필요)은 `music.py gen`, 무료는 Gemini 앱에서 `music.py prompt` 의 문장으로 만들어 받은 MP3 를 넣습니다. Google Vids 음악 생성도 됩니다. 자세한 순서는 `/music` 스킬.
- 박자에 맞춘 필름(키노트·UI 모프·쇼릴)은 120BPM 으로 짰으니 곡도 120BPM 으로 만듭니다.
- 오디오 트랙이 없는 MP4는 일부 서비스(Google Vids 등)가 거절하므로 finalize 는 음악이 없어도 무음 트랙을 넣습니다.

## 검수와 전달

- 무엇이든 만든 뒤에는 직접 확인하고 전달합니다. sheet 이미지를 열어 보고, 영상은 `ffprobe -v error -show_entries format=duration:stream=codec_name,width,height -of compact <파일>` 로 확인합니다.
- 전달할 때는 파일 경로, 길이, 비율, 확인한 점, 남은 확인 사항(사실 정보, 출처)을 짧게 알려 줍니다.

## 고치기와 배포

- 프로그램 코드의 원본은 GitHub 공개 저장소 `tifania1/motion-studio`(main)입니다(첫 화면은 README.md, 그림은 docs/media). 저장소에는 `.gitignore` 의 허용 목록에 있는 프로그램 파일
  (.claude app docs engine fonts installer presets styles templates tools vendor, 맨 위 md·cmd·requirements·update.json)만 들어가고,
  brands·videos·out·dist·API 키는 올리지 않습니다.
- 앱이 켜질 때 `tools/update.py` 가 저장소의 새 버전을 받아 적용합니다(`update.json` 의 repo). 임시 폴더에서 파이썬 문법을 먼저 보고, 바뀔 파일을 백업
  (사용자 폴더 `.motion-studio/update/backup`)한 뒤 덮어쓰고, 앱을 불러 봐서 안 되면 되돌리고 그 버전은 건너뜁니다. 적용한 버전은 이 폴더의 `.version`.
  `python tools/update.py --check` 확인만 · `--rollback` 바로 전 버전으로 · 사용자 폴더 `.motion-studio/update/off` 파일이 있거나 `--no-update` 면 꺼짐.
- 그래서 코드를 고치면 저장소에 커밋하고 push 해야 다른 PC와 다음 실행에 남습니다. 이 PC에서만 고친 파일은 다음 버전에서 그 파일이 안 바뀌면 그대로 두지만,
  같은 파일이 저장소에서 바뀌면 새 버전으로 덮이고 고친 것은 백업에만 남습니다. 고친 뒤에는 check·build·sheet 로 확인하고, 앱을 다시 켜야 적용된다고 알려 줍니다.
- 커밋 메시지 첫 줄은 사용자가 읽는 "바뀐 점"으로 앱 업데이트 창에 그대로 나옵니다. 사람이 말하듯 짧은 한국어로 씁니다(예: "발표 자료 PPT 만들기 버튼이 창을 줄여도 보이게").
- 새 PC에 처음 설치할 때는 완전한 설치 파일을 씁니다: `python tools/make_installer.py`. 먼저 `installer/README.txt` 의 "이번 버전에서 새로 생긴 것"을 고치고, 점검이 통과한 zip 만 전달합니다.
  설치한 뒤에는 자동 업데이트로 최신이 됩니다.
- 설치 파일에는 `installer/examples.json` 에 적힌 예시 브랜드·영상만 들어갑니다. 사용자의 다른 광고 계정 자료는 넣지 않습니다(`--all` 은 본인 PC 옮길 때만).
- 이미 설치한 PC에서 설치 파일을 다시 실행하면 백업(문서\motion-studio-backup-날짜) 후 엔진·템플릿·도구·스킬만 바꾸고 brands·videos 는 없는 파일만 더합니다.

## 스킬 (슬래시 명령)

- `/new-brand` 광고 계정 추가 · `/new-ad` 광고 영상 만들기 · `/ad-review` 올리기 전 검수
- `/render-mp4` 업로드용 MP4 뽑기 · `/music` 배경음악 · `/new-template` 새 연출 템플릿 · `/new-style` 참고 영상에서 새 스타일 배우기 · `/new-deck` 발표 자료 만들기
