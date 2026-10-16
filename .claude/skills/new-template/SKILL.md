---
name: new-template
description: promo·kinetic 으로 표현하기 어려운 새 연출(제품 회전 소개, 전후 비교, 순위, 캐릭터가 말하는 영상 등)을 재사용 가능한 템플릿으로 만들 때 사용.
argument-hint: "[템플릿 이름] [원하는 연출]"
---

# 새 템플릿 만들기

요청: $ARGUMENTS

1. `docs/ENGINE.md` 와 `docs/TEMPLATES.md` 를 읽고, 기존 템플릿(`templates/kinetic/index.html` 이 짧아 출발점으로 좋음)을 살펴봅니다.
   캐릭터가 말하고 장소를 소개하는 긴 연출은 `videos/bax-bangkok/tall.html` 을 참고합니다.
   한 컷으로 이어지는 박자 필름(모프·카메라·커서·조리개·유리)은 `templates/uimorph`(짧음)·`templates/keynote` 와 `docs/ENGINE.md` 의 모션 도구(Studio.M)를 출발점으로 합니다. 이때는 CLAUDE.md 의 "모션 원칙"을 따릅니다.
   스타일 묶음(결)의 템플릿을 하나 더 만드는 거라면 결 템플릿 10개(`typeslam` 등, `docs/TEMPLATES.md` '결 템플릿')처럼 공통 content(이야기)를 그대로 읽게 짭니다.
   `S.story()`, 큰 글은 `S.fx.enter`, 숫자는 `S.fx.num`(스타일 scenes.title·number 를 따름), 프리셋은 `"group": "look"` 과 기본 `"style"`.
   그래야 사용자가 연출 탭 '결 바꾸기'로 문구를 그대로 둔 채 템플릿만 바꿀 수 있어요.
2. 장면 구성과 content 항목(JSON 구조)을 먼저 정하고 사용자에게 짧게 보여 줍니다.
3. `templates/<이름>/index.html` 과 `templates/<이름>/example.json` 을 만듭니다.
   - 브랜드 색·글꼴은 CSS 변수만 쓰고, 크기는 `--u` 기준, 비율별 배치는 `[data-format=...]` 로.
   - 움직임은 `S.tl` 과 `S.ambient` 로만. 글자는 `S.esc` 로 넣고 `S.fit` 으로 크기 맞춤.
   - 글자·버튼은 `.safe` 안에.
4. 예시 영상을 만들어 검증합니다: `python tools/new_video.py <이름>-demo --brand haru-cafe --template <이름>` →
   content 채우기 → build → `render.py <이름>-demo all sheet` 와 `tall sheet --safe` → sheet 를 열어 네 비율 모두 확인.
   박자 필름이면 `render.py <이름>-demo square beats 1 0.5` 로 반 박마다 보고, video 렌더 뒤 `qa.py` 로 튐·멈춤·루프를 확인합니다.
   다른 브랜드(예: bax)로도 한 번 빌드해 색·글꼴이 바뀌어도 괜찮은지 봅니다.
5. `docs/TEMPLATES.md` 에 새 템플릿의 content 설명을 추가하고, `tools/check.py` 의 LIMITS 에 새 문구 항목 권장 길이를 넣습니다.
