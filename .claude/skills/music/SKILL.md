---
name: music
description: 광고 영상에 배경음악을 넣을 때 사용. 구글 Gemini(Lyria)로 영상 길이·BPM에 맞는 연주곡을 만들거나(유료 API 또는 무료 Gemini 앱), 사용자 음원을 넣고, 박자를 재서 첫 박을 영상 시작에 맞춘다.
argument-hint: "[영상이름] [원하는 분위기 또는 음악 파일]"
---

# 배경음악 넣기

요청: $ARGUMENTS

## 1. 음원 고르기
1. 사용자가 음원 파일을 주면: 사용 권한이 정리된 곡인지(직접 구매·라이선스, 무료 라이선스) 한 번 확인하고 3번으로.
2. 새 곡은 구글 Gemini 의 음악 모델(Lyria)로 만듭니다. 두 갈래가 있습니다.
   - **Gemini API (자동, 유료)**: 무료 등급이 없습니다. 영상이 28초 이하면 30초 곡으로 약 0.04달러, 더 길면 약 0.08달러.
     반드시 사용자에게 비용을 말하고 허락을 받은 뒤 실행합니다.
     `python tools/music.py gen <영상> --mood keynote --bpm 120 --yes`
     키가 없으면 사용자가 Google AI Studio(aistudio.google.com)에서 키를 만들고 결제를 연결한 뒤 `python tools/music.py key <키>` (PC마다 한 번).
   - **Gemini 앱 (무료, 손으로)**: `python tools/music.py prompt <영상> --mood cafe` 가 영어 프롬프트를 줍니다.
     사용자가 gemini.google.com 에 붙여 넣어 연주곡을 만들고 MP3 로 받아 오면 3번으로. Gemini 앱은 30초 곡을 만들어서 28초 넘는 영상에는 짧아요(그때는 API 나 Vids). 하루 생성 수가 정해져 있고, 광고에 쓰기 전 약관 확인을 권합니다.
   - Google Vids 음악 생성도 됩니다(아래 참고).
3. Artlist 같은 다른 유료 서비스는 무료·무제한 범위인지 먼저 확인하고, 비용을 알리고 허락을 받은 뒤에만 씁니다.

분위기(--mood): minimal, keynote, cafe, lofi, citypop, travel, cinematic, funk. 직접 쓰려면 `--prompt "warm acoustic guitar, soft shaker, cozy cafe"` (영어가 잘 먹힘).
박자에 맞춰 짠 필름(keynote·uimorph·showreel)은 120BPM 이므로 `--bpm 120`.

## 2. 박자 맞추기
- `music.py gen` 은 곡을 `videos/<영상>/music/` 에 저장하고, 박자를 재서 첫 다운비트(마디 첫 박)를 `music.start` 에 넣습니다. 영상 0초 = 곡의 첫 박.
- 받은 파일을 직접 넣을 때: `python tools/music.py beats 곡.mp3 --bpm 120` → 나온 `downbeat` 를 `--start` 로.
- 앱에서는 음원을 넣기만 하면 자동으로 잽니다. 사진형·글자형은 음악 탭 "장면 바뀌는 순간을 박자에 맞추기"로 장면 길이를 2박 단위로 맞출 수 있습니다.

## 3. 합치기
`python tools/finalize.py <영상> <형식|all> --music <곡 파일> [--start 첫다운비트] [--volume 1.0] [--fade-in 0] [--fade-out 2]`
- 음악 크기를 -14 LUFS(유튜브·인스타 기준)로 맞추고 봉우리는 리미터로 누릅니다. `--volume` 은 그 뒤에 곱합니다.
- 곡이 영상보다 길면 영상 길이에 맞춰 자르고 끝에서 페이드아웃합니다.
- video.json 에 `music` 이 있으면 앱의 MP4 만들기가 같은 값으로 합칩니다.
- 결과를 `ffprobe` 로 확인하고(오디오 aac, 길이), 사용자에게 휴대폰으로 소리를 들어 봐 달라고 부탁합니다.

## Google Vids 로 음악 만들기 (해 본 방법)
1. `python tools/finalize.py <영상> tall` 로 무음 트랙이 든 MP4를 만듭니다(오디오 트랙이 없으면 Vids가 거절). 10MB가 넘으면 `--split <초>`.
2. 파일을 구글 드라이브에 올립니다. Vids 업로드 버튼보다 드라이브를 거치는 쪽이 안정적이었습니다.
3. Vids에서 영상 비율에 맞는 빈 프로젝트를 만들고, 오른쪽 "Drive 및 포토"에서 영상을 넣습니다. 전체 길이를 확인합니다.
4. 삽입 > 음악 생성: "전체" 길이, "연주곡" 켜기. 프롬프트는 영어로 분위기·악기·BPM을 적습니다.
5. 생성된 곡을 삽입하고 음악 클립의 "소리" 설정에서 페이드인 0.5초, 페이드아웃 2~3초.
6. 파일 > "Drive로 내보내기" → 드라이브 "Google Vids 내보내기" 폴더에 저장됩니다.
7. Vids 탭이 최소화되거나 가려져 있으면 음악 생성이 100%에서 멈춥니다. 창을 화면에 띄워 둔 채로 기다립니다.

## (고급) 내 PC에서 무료로
NVIDIA 그래픽카드가 있는 PC에서는 오픈소스 ACE-Step 1.5(MIT)를 설치해 무료로 만들 수 있습니다. 약 13GB를 내려받습니다.
`python tools/music.py setup` → `python tools/music.py gen <영상> --engine ace --bpm 120`. 다 쓰면 `python tools/music.py stop` 으로 그래픽 메모리를 비웁니다.
