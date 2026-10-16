# 먹 붓글씨 (손그림)

한 줄: 한지 위 굵은 붓글씨 한 줄과 빨간 낙관. 큰 여백 속에서 붓 획이 쓸며 드러나고, 강조는 붓으로 그린 동그라미예요.

## 보는 느낌
- 가운데 정렬. 붓글씨 한 줄(많아야 두 줄)이 화면 가운데보다 조금 위에, 나머지는 넓게 비워요.
- 작은 설명은 붓글씨 아래 아주 작게. 오른쪽 아래에 빨간 낙관 하나.
- 장식은 먹 번짐 원 하나, 또는 붓으로 그은 가로 획 하나.

## 색
- 한지 80 · 먹 17 · 주홍 낙관 3.
- 한지(#EFE6D2), 먹(#161412). 강조는 낙관 주홍(#C2352B) 하나뿐.
- 보조로 옅은 먹(#7A6A55)을 설명 글에.

## 글자
- 제목은 나눔손글씨 붓(Nanum Brush), 짧은 변의 12~16%로 크게. 줄 간격 1.0, 자간 0.
- 설명 글은 브랜드 글꼴 그대로(붓글씨는 작게 쓰면 읽기 어려워요).

## 질감과 모양
- 종이(cream) + 섬유 진하게(0.6) + 그레인 0.08. 한지 결이 보이게.
- 선 떨림은 아주 약하게(0.5, 초당 6번). 붓 획이 매끈해야 해서 끊어 그리기는 쓰지 않아요.
- 카드는 종이(paper)를 겹쳐 놓은 느낌, 모서리 거의 없음(0.4u).

## 움직임
- 80BPM, 느리게. power3.out 으로 빠르게 시작해 천천히 멈춰요. 어절 간격 1.6배.
- 한 장면에 2박 넘게 머물러요. 여백이 말하게.

## 전환
- 색 막대(wipe)를 붓 획처럼 한 방향으로, 또는 서서히(fade).

## 대표 장면

1. 붓 획처럼 드러나는 제목
   ```
   // 가림막이 획 방향(왼→오른쪽)으로 걷힘. 가장자리를 부드럽게 하려면 mask 그라디언트
   ttl.style.webkitMaskImage = 'linear-gradient(90deg, #000 45%, transparent 55%)';
   ttl.style.webkitMaskSize = '220% 100%';
   tl.fromTo(ttl, { webkitMaskPosition: '100% 0' }, { webkitMaskPosition: '0% 0', duration: .8, ease: 'power3.out' }, T0 + .1);
   ```
2. 원상(붓 동그라미) 강조
   - 장면 쌓기는 marker: circle + rough. 직접 짤 때 M.rough('ellipse', {turns: 1.06}) 를 굵게(글자 높이의 12%) 0.7초에.
3. 낙관 찍기
   ```
   // 빨간 네모 도장(브랜드 이름 두세 글자, 흰 글씨). 크게 → 제자리로 빠르게 + 아주 작은 흔들림
   tl.fromTo(seal, { scale: 1.6, autoAlpha: 0, rotation: -6 }, { scale: 1, autoAlpha: 1, rotation: -3, duration: .22, ease: 'power4.in' }, tEnd);
   S.fx.shake(tEnd + .22, .4 * u);
   ```

## 어울리는 곳 / 피할 것
- 어울리는 곳: 명절·시즌 인사, 전통 음식·차·한식, 개업·축하, 브랜드 철학 한 줄, 공연·전시.
- 피할 것: 글이 많은 장면, 작은 글씨 목록, 네온·형광색, 빠른 컷.

## 배운 곳
- 직접 정리. 갤러리 영상에서 배운 게 아니고, 캘리그래피·서예 포스터 영상에서 널리 쓰는 방식(여백 비율, 획 방향으로 드러나기, 낙관으로 마무리)으로 정리했어요.
- 갤러리에서 배운 손그림 결은 따로 있어요: marker-scrawl-montage, chalk-math-board, doodle-faces-strikeout, manga-panel-bubbles, river-line-lettering, serif-marker-word, ink-gesture-blobs, navy-etching-plates.
