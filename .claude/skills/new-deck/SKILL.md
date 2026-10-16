---
name: new-deck
description: 모션 그래픽 발표 자료(16:9, 넘길 때마다 한 장씩 움직이며 등장)를 만들 때 사용. 주제·메모나 가진 자료(PPTX·PDF·DOCX·HWPX·TXT)로 장 구성과 화면 글, 발표 메모를 쓰고 빌드·장 모음 검수·PDF까지 한다.
argument-hint: "[브랜드] [무슨 발표인지, 자료 파일 경로, 발표 시간]"
---

# 발표 자료 만들기

요청: $ARGUMENTS

## 1. 파악
- `brands/<브랜드>/brand.json` 의 voice, about, notes 를 읽습니다. 계정이 없으면 `/new-brand` 를 먼저 제안합니다.
- 누구 앞에서 하는 발표인지, 꼭 전할 것, 듣는 사람이 할 일, 발표 시간(장마다 30초~1분)을 정리합니다.
- 자료 파일이 있으면 `python tools/deck.py source <발표> <파일>` 로 넣고 `videos/<발표>/source.md` 를 읽습니다. 자료에 있는 사실·숫자만 씁니다.

## 2. 만들기
- `python tools/new_video.py <발표> --brand <브랜드> --template deck --title "발표 제목"`
- `content.title` 과 `content.slides` 를 씁니다. 장 종류와 칸은 `docs/TEMPLATES.md` 의 'deck'.
  - 첫 장 cover, 마지막 closing. 덩어리가 여럿이면 agenda + section(2~5개).
  - 숫자 하나 number, 여러 개 stats, 기간별 값 chart, 전후 compare, 순서·일정 steps, 나열 bullets·cards, 남길 말 statement, 실제로 한 말만 quote.
  - 화면 글은 짧게(제목 26자, 글머리 30자 안쪽), "머리말 | 설명" 으로 두 줄. 자세한 말은 장마다 `notes`.
  - 사람이 실제로 말하듯 자연스러운 한국어. "~가 아닙니다, ~입니다" 같은 대조 구문은 쓰지 않습니다. 숫자·날짜·이름을 지어내지 않습니다.
- 결을 바꾸려면 `"style": "<스타일>"` (`python tools/styles.py`), 스타일 색까지 쓰려면 `"styleColors": true`.

## 3. 검수
- `python tools/check.py <발표>` → `python tools/build.py <발표>` → `python tools/deck.py sheet <발표>`
- `out/<발표>/wide/slides.png` 를 Read 로 열어 글 넘침·겹침·빈 사진 자리·오탈자를 보고 고칩니다.
- 넘김을 직접 보려면 `out/<발표>/wide/<발표>-wide.html` 을 브라우저로 엽니다(→ 다음, ← 이전, 숫자+Enter, F5 전체 화면).

## 4. 전달
- 발표용: `out/<발표>/wide/<발표>-wide.html` 한 파일(인터넷 없이 열림). PowerPoint 로 고치고 싶으면 `python tools/deck_pptx.py <발표>`(애니메이션·모핑·발표 메모 포함). 나눠 줄 PDF: `python tools/deck.py pdf <발표>`.
- 장 수, 확인할 사실(자료에 없던 값), 비어 있는 사진 자리를 짧게 알려 줍니다.
