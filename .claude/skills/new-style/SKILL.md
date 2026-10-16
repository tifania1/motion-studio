---
name: new-style
description: 잘 만든 모션 영상(keyframe.gallery 영상, 사용자가 준 참고 영상·링크)에서 보는 결·움직이는 결을 배워 styles/ 에 새 스타일로 더할 때 사용.
argument-hint: "[참고 영상 주소나 설명] [원하는 스타일 이름]"
---

# 새 스타일 더하기

요청: $ARGUMENTS

1. `docs/STYLES.md`(형식과 규칙)와 비슷한 스타일 카드 2~3개(`styles/<id>/style.md`)를 먼저 읽고, `python tools/styles.py` 로 이미 있는 스타일과 겹치는지 봅니다.
2. 참고 영상을 직접 봅니다. keyframe.gallery 영상은 mux 재생 ID 로 스토리보드(`https://image.mux.com/<ID>/storyboard.json`)와
   큰 프레임(`https://image.mux.com/<ID>/thumbnail.jpg?width=960&time=<초>`)을 받아 0.1~0.25초 간격으로 붙여 보면 이징·속도·전환을 잴 수 있어요.
   받은 그림은 임시 폴더에만 두고 프로젝트 폴더에는 넣지 않아요(남의 작품).
3. 원리만 배워요: 색 비율, 글자 성격, 질감, 움직임 속도와 이징, 전환, 대표 움직임. 브랜드 로고·캐릭터·고유 그림은 따라 그리지 않아요.
4. `styles/<id>/style.json` 과 `style.md` 를 씁니다. id 는 결을 설명하는 영문(회사·제품 이름은 넣지 않음), name 은 짧은 한국어.
   - `template`: 결 템플릿 10개 중 가장 어울리는 것(typeslam·uidemo·sketchbook·dataflow·terminal·collage·stage·glow·brandmark·cinema)
   - `scenes.title`(rise·type·slot·scramble·blur·pop·mask·write·stamp·fade), `scenes.number`(count·odometer·scramble): 큰 글·숫자 등장 방식
   - `colors` 9개(대비: onBg/bg 4.5 이상), 글꼴은 `fonts/` 안 파일만, `look` 은 질감이 실제로 있을 때만
   - `source`: 사이트, 영상(mux:<ID>), 몇 초, 무엇을 배웠는지
5. `python tools/styles.py check <id>` → `python tools/styles.py thumbs <id>` → `styles/<id>/thumb.jpg` 를 열어 봅니다.
   짝 템플릿으로 예시 영상을 만들어(`new_video.py ... --preset <template>`, video.json 에 `"style": "<id>", "styleColors": true`) sheet 로 확인합니다.
6. 글은 자연스러운 한국어로, "~가 아닙니다, ~입니다" 같은 대조 구문 없이.
