---
name: new-ad
description: 브랜드의 광고·홍보용 짧은 모션 그래픽 영상(릴스·쇼츠·피드)을 만들 때 사용. 문구 작성, 사진 준비, video.json 작성, 빌드, 네 비율 검수까지 한다.
argument-hint: "[브랜드] [무엇을 알리는 광고인지, 기간·혜택·사진 등]"
---

# 광고 영상 만들기

요청: $ARGUMENTS

## 1. 파악
- `python tools/list.py` 로 브랜드를 찾고 `brands/<브랜드>/brand.json` 의 voice, about, notes 를 읽습니다. 없는 브랜드면 `/new-brand` 를 먼저 제안합니다.
- 알릴 내용, 혜택·기간·가격, 행동 유도(방문, 예약, 저장, 프로필 링크), 올릴 곳(릴스/쇼츠/피드/유튜브), 사진 유무를 정리합니다.
  광고 내용이 분명하면 바로 진행하고, 혜택·가격처럼 지어내면 안 되는 정보가 비어 있을 때만 묻습니다.
- 형식: 릴스·쇼츠·틱톡은 tall, 인스타 피드는 portrait, 정사각 피드는 square, 유튜브 일반은 wide. 모르면 네 개 모두.

## 2. 상황과 문구
- 먼저 상황 프리셋이 맞는지 봅니다: `python tools/presets.py` (신메뉴 출시, 세일, 매장 오픈, 시즌 인사, 수강생 모집, 행사 안내, 채용, 앱 기능 소개, 공지, 채널 홍보, 여행 하이라이트, 숫자로 보는 성과,
  기업용: 회사 소개, 제품·서비스 소개, 연혁·마일스톤, 소식 발표).
  맞는 게 있으면 `python tools/presets.py show <상황>` 으로 연출 프롬프트를 읽고 그 장면 구성·글 규칙·확인할 것을 따릅니다.
- 맞는 상황이 없으면 장면 쌓기(`custom` 프리셋, `scenes` 템플릿): 표지·문장·사진·숫자·목록·단계·비교·인용·그래프·사진 여러 장·로고 장면을 내용에 맞게 골라 쌓습니다.
  짧은 사진 광고면 promo, 글자만이면 kinetic 도 됩니다(`docs/TEMPLATES.md`).
- 템플릿으로 안 되는 연출이면 처음부터 짭니다: `python tools/new_video.py <영상> --brand <브랜드> --scratch "원하는 영상 설명"` 후 `docs/SCRATCH.md` 를 따릅니다.
- 화면 구성부터 확 다르게 가고 싶으면 결 템플릿 10개 중에서 고릅니다(같은 문구로 바꿔 볼 수 있음, `docs/TEMPLATES.md` '결 템플릿'):
  타이포 쇼(typeslam) · 제품 화면 시연(uidemo) · 손그림 노트(sketchbook) · 데이터 흐름(dataflow) · 레트로 터미널(terminal) ·
  종이 콜라주(collage) · 사물 무대(stage) · 빛과 그라디언트(glow) · 도형으로 짜는 브랜드(brandmark) · 시네마틱(cinema).
  `python tools/new_video.py <영상> --brand <브랜드> --preset <템플릿>` 이면 어울리는 스타일까지 기본으로 들어가요.
- 화면의 결을 바꾸고 싶으면 스타일을 고릅니다: `python tools/styles.py` (타이포·제품 UI·그라디언트·빛·손그림 등 묶음별), `python tools/styles.py show <스타일>`.
  video.json 에 `"style": "<스타일>"`(브랜드 색 대신 스타일 색까지 쓰려면 `"styleColors": true`). 질감·글꼴은 모든 템플릿에, 바탕·카드·강조·전환은 장면 쌓기에 입혀집니다(`docs/STYLES.md`).
  손그림 스타일은 글이 적고 따뜻한 상황(교육, 공지, 인사, 모집)에 잘 맞습니다.
- CLAUDE.md 의 문구 원칙을 지킵니다. 자연스러운 한국어, 대조 구문 금지, 브랜드 말투, 훅 24자 안쪽.
- 사실 정보(가격, 영업시간, 수상, 수치)는 사용자 자료나 검색으로 확인한 것만 씁니다. 숫자 장면은 근거 있는 숫자로.
- 문구 초안을 장면 순서대로 짧게 보여 주고, 사용자가 자리에 있으면 의견을 받은 뒤 진행합니다.

## 3. 영상 폴더와 사진
- 상황 프리셋: `python tools/new_video.py <영상이름> --brand <브랜드> --preset <상황>` (템플릿·예시 문구·형식·길이·음악 힌트·direction.md 가 들어감)
- 그 밖: `python tools/new_video.py <영상이름> --brand <브랜드> --template <scenes|promo|kinetic> --formats <...>`
- 사진: 사용자 파일은 `python tools/photo.py add <영상> 파일 --as <키>`.
  찾아야 하면 `python tools/photo.py search "영어 검색어"` → 고른 뒤 `python tools/photo.py get <영상> "File:..." --as <키>` (CC BY 는 credit 자동 기입).
  받은 사진은 Read로 열어 내용과 품질을 확인합니다. 실제 그 가게·상품이 아니면 sub 에 "(참고 사진)".
- 새로 그려야 할 이미지는 ChatGPT 웹 고화질 생성용 프롬프트를 정리해 드리고, 받으면 add 로 넣습니다.
- video.json 의 content 를 채웁니다. 사진마다 `focus` 를 피사체 위치에 맞춥니다. 프리셋 영상은 예시 문구 구조(키, 배열 길이)를 그대로 두고 글만 바꿉니다.

## 4. 점검과 검수
- `python tools/check.py <영상>` 의 오류는 모두 고치고, 확인 항목은 판단해서 처리합니다.
- `python tools/build.py <영상>` → `python tools/render.py <영상> all sheet` → `python tools/render.py <영상> tall sheet --safe`
- 모든 sheet 를 Read로 열어 봅니다: 글자 넘침·겹침, 세이프존 침범, 사진 초점, 마스코트 위치, 빈 화면, 오탈자, 색 대비.
  문제가 있으면 문구 길이, focus, durations, 템플릿 CSS를 고치고 다시 확인합니다.

## 5. 전달
- 미리보기 HTML(`out/<영상>/<형식>/<영상>-<형식>.html`)과 sheet 경로, 길이, 확인한 점을 알려 줍니다.
- 영상 파일까지 원하면 `/render-mp4`, 음악은 `/music`. 사용자가 처음부터 영상 파일을 원했다면 바로 이어서 진행합니다.
