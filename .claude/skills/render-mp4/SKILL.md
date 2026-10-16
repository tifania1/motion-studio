---
name: render-mp4
description: 광고 영상을 업로드용 MP4로 뽑을 때 사용. 프레임 렌더, 음악 합치기, 무음 트랙, 결과 확인까지 한다.
argument-hint: "[영상이름] [형식들 또는 all] [음악 파일]"
---

# 영상 파일 뽑기

요청: $ARGUMENTS

1. 영상 이름과 형식을 정합니다(없으면 video.json 의 formats 전부). 먼저 `python tools/check.py <영상>` 과 sheet 검수가 끝났는지 확인하고, 안 했으면 `/ad-review` 순서로 빠르게 봅니다.
2. `python tools/build.py <영상> [형식]` → `python tools/render.py <영상> <형식|all> video`
   - 20초 영상 한 형식에 몇 분 걸립니다. 진행 로그가 나오니 기다립니다.
3. `python tools/finalize.py <영상> <형식|all> [--music 곡] [--volume 0.85] [--fade-in 0.5] [--fade-out 2.5] [--start 초]`
   - 음악이 없으면 무음 오디오 트랙이 들어갑니다. 음악이 필요하면 `/music`.
   - Google Vids 에 올릴 60초 안팎 영상이 10MB를 넘으면 `--split <초>` 로 두 조각을 함께 만듭니다.
4. 결과 확인:
   `ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height -of compact out/<영상>/<형식>/<영상>_<형식>.mp4`
   길이, 해상도, h264+aac 두 트랙을 확인하고, `python tools/render.py <영상> <형식> shots <몇 초>` 로 한두 장면을 찍어 열어 봅니다.
5. 사용 가능한 경우 `python tools/photo.py credits <영상>` 으로 게시글용 사진 출처를 만듭니다.
6. 파일 경로(탐색기에서 열 위치), 길이, 비율별 용도(9:16 릴스·쇼츠, 4:5 피드, 1:1 피드, 16:9 유튜브), 게시글에 넣을 출처 문구를 알려 줍니다.
