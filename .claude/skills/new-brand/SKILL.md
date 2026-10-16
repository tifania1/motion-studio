---
name: new-brand
description: 새 광고 계정(브랜드)을 스튜디오에 추가할 때 사용. 브랜드 색·글꼴·로고·마스코트·말투·규칙을 brand.json으로 만들고 샘플 영상으로 모양을 확인한다.
argument-hint: "[브랜드 이름] [로고 파일이나 색 등 아는 정보]"
---

# 광고 계정(브랜드) 추가

요청: $ARGUMENTS

1. 아래 정보를 사용자 메시지와 첨부에서 먼저 찾고, 빠진 것만 한 번에 물어봅니다(모르면 기본값으로 진행해도 된다고 알려 주기).
   - 브랜드 이름과 슬러그(영문 소문자·하이픈. 없으면 제안)
   - 무엇을 하는 계정인지, 주요 고객
   - 대표 색 또는 로고 이미지(색을 뽑을 수 있음), 어두운/밝은 배경 선호
   - 로고, 마스코트·캐릭터 이미지(있으면)
   - 말투(해요체/반말, 이모지 여부, 자주 쓰는 말), 꼭 넣을 문구·금지 표현
2. 실행:
   `python tools/new_brand.py <슬러그> --name "<이름>" [--palette 로고.png] [--accent "#hex"] [--light] [--logo 로고.png] [--mascot 캐릭터.png] [--serif]`
   - 출력된 대비 값이 3 아래면 색을 조정합니다.
   - 로고·마스코트에 배경이 있으면 `python tools/cutout.py 원본 brands/<슬러그>/assets/<이름>.png` 로 지우고 결과를 열어 확인합니다.
3. `brands/<슬러그>/brand.json` 을 채웁니다.
   - `description`: 한 줄 소개 · `voice.tone`: 말투 · `about`: 대표 상품, 위치, 참고 링크
   - `notes`: 꼭 지킬 규칙(법적 고지, 금지 표현, 경쟁사 언급 금지 등)
   - `pattern`: dots / grid / rays 중 브랜드 분위기에 맞는 것, `logoText`/`logoSub`: 로고 이미지가 없을 때 글자 로고
   - 다른 글꼴이 필요하면 `fonts/` 에 woff2 를 넣고 `fonts` 와 `type` 에 등록합니다(상업 이용 가능한 글꼴인지 라이선스 확인).
4. 모양 확인용 샘플을 만듭니다.
   `python tools/new_video.py <슬러그>-sample --brand <슬러그> --template kinetic --formats tall,square`
   content 를 브랜드 말투로 짧게 바꾼 뒤 `python tools/build.py <슬러그>-sample` → `python tools/render.py <슬러그>-sample all sheet`
   sheet 를 열어 색 대비, 로고, 글꼴을 확인하고 필요하면 brand.json 을 고쳐 다시 봅니다.
5. 사용자에게 만든 브랜드 요약(색, 글꼴, 말투, 규칙)과 sheet 경로를 알려 주고, 바로 광고 영상을 만들 수 있다고 안내합니다(`/new-ad`).
