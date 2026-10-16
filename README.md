# 모션 스튜디오

여러 광고 계정의 짧은 광고 영상을 모션 그래픽으로 만드는 폴더입니다.
Claude Code(Opus 5.5)를 이 폴더에서 열고 말로 시키면 됩니다. 바탕화면의 **모션 스튜디오 (Claude Code)** 바로가기로 열 수 있습니다.

## 앱으로 쓰기

바탕화면의 **모션 스튜디오** 아이콘을 누르면 앱 창이 열려요(폴더 안 `StudioApp.cmd` 로도 열 수 있어요).

- 왼쪽: 광고 계정과 영상 목록. 계정 이름 옆 화살표로 접고 펼 수 있고, 위의 **모두 접기**로 한 번에 접어요. 영상 옆 네모 4칸은 9:16, 4:5, 1:1, 16:9 상태예요(채워진 칸은 MP4 완성).
- **영상 추가**를 누르면 상황부터 골라요: 신메뉴 출시, 세일, 매장 오픈, 시즌 인사, 수강생 모집, 행사 안내, 채용, 앱 기능 소개, 공지, 채널 홍보, 여행 하이라이트, 숫자로 보는 성과. 상황마다 화면 구성이 완전히 다른 템플릿과 예시 문구, 길이, 음악 분위기, 연출 프롬프트가 함께 들어가요.
- 가운데: 문구, 사진, 설정. 고치면 바로 저장돼요. "Claude에게 문구 맡기기"에 알릴 내용을 적으면 브랜드 말투로 초안을 써 줘요. 옆의 **모델**(Opus 꼼꼼·Sonnet 균형·Haiku 빠름)과 **노력**(낮음~최대)을 맡기기 전에 고를 수 있고, 고른 값은 이 PC의 모든 영상과 Claude Code 열기에 같이 쓰여요.
- 오른쪽: 움직이는 미리보기. 비율을 바꿔 보고, 세이프존을 켜서 플랫폼 버튼에 가리는 곳을 확인하세요.
- 가운데 탭은 작업 순서대로 **1 문구 → 2 사진 → 3 음악 → 4 연출 → 5 올리기**예요. 끝난 단계엔 초록 체크가 붙어요. 영상 제목·형식·장면 길이는 **설정** 탭에 있어요.
- 아래 빨간 **MP4 만들기**로 업로드용 영상을 뽑아요.
- 음악 탭의 **음악 만들기**: 구글 Gemini 로 영상 길이·박자에 맞는 연주곡을 만들어요. API 키가 있으면 자동(곡당 약 0.04~0.08달러, 누를 때마다 비용 확인), 없으면 Gemini 앱에서 무료로 만들어 받은 MP3 를 끌어다 놓으면 돼요. 박자는 앱이 재서 첫 박을 맞춰요.
- 사진 탭의 "무료 사진 찾기"는 광고에 써도 되는 사진(CC0, CC BY)만 보여 주고, 출처 표시도 알아서 넣어요.
- 연출 탭 맨 위 **영상 길이**: 슬라이드나 15초·20초 버튼으로 길이를 맞춰요(움직임 전체가 같은 비율로 빨라지거나 느려져요). 사진형·글자형은 장면 길이를 나눠 맞춰요.
- 연출 탭의 **연출 프롬프트**: 그 상황의 장면·박자·전환·글 규칙이에요. 고쳐서 저장할 수 있고, 문구·사진·음악을 넣은 뒤 모델과 노력 정도를 고르고 **Claude Code에게 이 연출로 맡기기**를 누르면 Claude Code가 이 프롬프트대로 영상을 다듬기 시작해요.
- **올리기** 탭: 유튜브 제목·설명, 인스타 캡션, 해시태그를 적거나 Claude에게 맡기고, 플랫폼별 영상·커버·글·체크리스트를 모은 **업로드 안내 묶음**을 만들어요. 유튜브는 채널을 연결해 두면 바로 올릴 수 있어요(준비 순서는 `docs/UPLOAD.md`).
- 화면으로 안 되는 연출은 오른쪽 위 **Claude Code 열기**로 말로 부탁하면 돼요.

## Claude Code에 이렇게 시켜 보세요

```
/new-brand 민트 필라테스. 로고는 C:\Users\나\Desktop\mint-logo.png, 말투는 친근한 해요체
/new-ad 민트 필라테스 10월 체험 수업 1회 무료, 릴스랑 피드용으로
/ad-review mint-oct-trial
/render-mp4 mint-oct-trial all
/music mint-oct-trial 밝고 경쾌한 분위기
```

슬래시 없이 "하루한잔 겨울 신메뉴 광고 영상 만들어줘"처럼 말해도 됩니다.

## 들어 있는 것

| 폴더 | 내용 |
|---|---|
| `brands/` | 광고 계정별 브랜드 키트(색, 글꼴, 로고, 마스코트, 말투, 규칙). `bax`, `haru-cafe`(가상 예시), `_template` |
| `videos/` | 영상별 설정·문구·사진. 예시: `bax-bangkok`(60초 원본), `bax-bangkok-promo`, `haru-spring-promo`, `haru-weekend-event`, 필름 4편 `studio-showreel`, `haru-ui-morph`, `haru-launch-film`, `bax-channel-film` |
| `templates/` | `promo`(사진형), `kinetic`(글자형), 필름 `keynote`·`uimorph`·`showreel`, 상황별 `menu`·`sale`·`opening`·`greeting`·`academy`·`event`·`hiring`·`notice`·`travel`·`stats`. 새 연출은 `/new-template` 로 추가 |
| `presets/` | 상황 프리셋 12개. 상황마다 `preset.json`(템플릿·길이·필요한 사진·확인할 것·음악)과 `direction.md`(연출 프롬프트) |
| `out/` | 결과물. `out/<영상>/<형식>/` 아래에 미리보기 HTML, 장면 모음, MP4 |

형식: `tall` 9:16(릴스·쇼츠·틱톡), `portrait` 4:5(인스타 피드), `square` 1:1, `wide` 16:9(유튜브)

## 직접 실행할 때

```
python tools/list.py
python tools/presets.py                                                      # 상황 프리셋 목록
python tools/new_video.py mint-oct-sale --brand mint --preset sale            # 상황 프리셋으로 새 영상
python tools/build.py haru-spring-promo
python tools/render.py haru-spring-promo all sheet
python tools/render.py haru-spring-promo tall video
python tools/finalize.py haru-spring-promo tall --music 곡.mp3
python tools/music.py gen haru-launch-film --mood keynote --bpm 120 --yes   # Gemini 로 음악 (유료, 키 필요)
python tools/render.py haru-launch-film square beats 1 0.5                    # 반 박마다 한 장 검수
python tools/qa.py haru-launch-film                                           # 한 프레임 튐·멈춤·루프 검사
python tools/upload.py kit haru-weekend-event                                 # 업로드 안내 묶음 (docs/UPLOAD.md)
python tools/make_installer.py                                                # 완전한 설치 파일 dist/MotionStudioSetup.zip (풀어서 점검까지)
```

`python` 이 안 되면 `py -3` 으로 바꿔 실행하세요. 미리보기 HTML은 더블클릭하면 브라우저에서 재생됩니다(스페이스: 재생/정지, ←/→: 2초 이동, F: 전체 화면, 네모 버튼: 세이프존 보기).

## 알아 둘 점

- 사진은 직접 찍은 것, CC0·퍼블릭 도메인, CC BY(화면에 출처 표시)만 씁니다. 게시글에 붙일 출처는 `python tools/photo.py credits <영상>` 으로 `videos/<영상>/CREDITS.md` 에 만들어집니다.
- Artlist 같은 유료 생성 도구는 쓰기 전에 Claude가 먼저 물어봅니다.
- 글꼴: Noto Sans/Serif KR, Cinzel, Archivo, Geist (SIL Open Font License, `fonts/` 안의 라이선스 파일 참고). 애니메이션: GSAP 3.12.5.
- 필름 템플릿은 60fps에 서브프레임 4장을 섞어 모션 블러를 넣어서, 20초 영상 하나 렌더에 10분 안팎 걸려요.
