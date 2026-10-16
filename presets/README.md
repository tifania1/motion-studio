# 상황 프리셋

상황마다 폴더 하나예요. 앱의 "영상 추가"와 `python tools/new_video.py <영상> --brand <브랜드> --preset <상황>` 이 이 폴더를 읽어요.

- `preset.json`
  - `name`, `summary`, `look`: 앱의 상황 카드에 보이는 글
  - `template`: 쓸 템플릿 (`templates/` 안 이름), `formats`: 만들 형식, `seconds`: 길이
  - `photos`: `{need, hint}` 필요한 사진 수와 어떤 사진인지
  - `ask`: Claude에게 문구를 맡길 때 적어 달라고 할 정보, `brief`: 요청 예시
  - `check`: 올리기 전에 확인할 것
  - `music`: `{mood, bpm, prompt, sections}` 구글 Gemini 음악 힌트 (sections 는 [시작초, 끝초, 설명])
  - `content`: 예시 문구 (없으면 템플릿의 example.json)
  - `group`: `"free"` 면 앱의 '직접 만들기' 줄에 보임 (장면 쌓기)
- `direction.md`: 연출 프롬프트. 새 영상 폴더에 복사되고, 앱의 "Claude에게 문구 맡기기"와 "Claude Code에게 이 연출로 맡기기"가 함께 써요.

새 상황을 만들 때는 기존 상황과 첫눈에 확 다르게 보이도록 바탕·구도·핵심 소품·움직임이 다른 템플릿을 고르거나 새로 만들어요(`/new-template`).
