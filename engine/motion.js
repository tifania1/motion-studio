/* Motion Studio — 모션 도구 (Studio.M)
 * 키노트·UI 모프 같은 "한 컷으로 이어지는" 영상을 위한 도구 모음입니다.
 * 모든 값은 시간 t 의 순수 함수입니다. render(t) 한 함수가 매 프레임 스타일을 계산하고,
 * 이전 프레임의 상태를 기억하지 않습니다(그래야 아무 시점이나 똑같이 찍힘).
 *
 *   const M = Studio.M;
 *   M.spring(t)                      0→1 스프링 (닫힌 식)
 *   M.anim(keys, t)                  여러 번 목표가 바뀌는 값 = 바뀔 때마다 스프링 하나씩 더한 합
 *   M.beat(n)                        n번째 박의 시각 (content.bpm, 기본 120)
 *   M.camera(el, cx, cy, zoom)       화면 녹화 앱처럼 확대·이동
 *   M.Cursor(parent)                 클릭·드래그하는 커서
 *   M.irisBlades(svgGroup, ...)      6장 조리개
 *   M.box(el, {x,y,w,h,r})           둥근 사각형 하나를 계속 모양 바꾸기(모프)
 *   M.rise(el, k)                    마스크 선 아래에서 글자가 올라옴
 *   M.Glass(el, src)                 리퀴드 글래스 (뒤 장면 복제 + 변위 지도 + 테두리 빛)
 *   M.scramble(text, k, o)           무작위 글자에서 앞부터 차례로 맞춰지는 글 (시드 고정)
 *   M.roll(digit, k, turns)          주행거리계 자리 하나의 위치
 */
(function () {
  'use strict';
  const S = window.Studio;
  if (!S) return;
  const M = S.M = {};

  /* ---------- 기본 수학 ---------- */
  const clamp = M.clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = M.lerp = (a, b, k) => a + (b - a) * k;
  M.prog = (t, t0, d) => d <= 0 ? (t >= t0 ? 1 : 0) : clamp((t - t0) / d);
  M.mix = (a, b, k) => Array.isArray(a) ? a.map((v, i) => lerp(v, b[i], k)) : lerp(a, b, k);
  const E = M.ease = {
    linear: k => k,
    inQuad: k => k * k, outQuad: k => 1 - (1 - k) * (1 - k), inOutQuad: k => k < .5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2,
    inCubic: k => k ** 3, outCubic: k => 1 - (1 - k) ** 3, inOutCubic: k => k < .5 ? 4 * k ** 3 : 1 - (-2 * k + 2) ** 3 / 2,
    inQuart: k => k ** 4, outQuart: k => 1 - (1 - k) ** 4, inOutQuart: k => k < .5 ? 8 * k ** 4 : 1 - (-2 * k + 2) ** 4 / 2,
    outQuint: k => 1 - (1 - k) ** 5, inOutQuint: k => k < .5 ? 16 * k ** 5 : 1 - (-2 * k + 2) ** 5 / 2,
    inExpo: k => k === 0 ? 0 : 2 ** (10 * k - 10), outExpo: k => k === 1 ? 1 : 1 - 2 ** (-10 * k),
    inOutExpo: k => k === 0 ? 0 : k === 1 ? 1 : k < .5 ? 2 ** (20 * k - 10) / 2 : (2 - 2 ** (-20 * k + 10)) / 2,
    inOutSine: k => -(Math.cos(Math.PI * k) - 1) / 2, outSine: k => Math.sin(k * Math.PI / 2),
    outCirc: k => Math.sqrt(1 - (k - 1) ** 2), inCirc: k => 1 - Math.sqrt(1 - k * k),
  };

  /* ---------- 스프링 (닫힌 식 계단 응답) ----------
   * f: 고유 진동수(Hz), z: 감쇠비. z<1 이면 살짝 넘쳤다 돌아옴. 프롬프트 규칙대로 기본은 거의 안 넘침. */
  const SP = M.SP = {
    snappy: { f: 3.0, z: .86 },   // UI 기본
    smooth: { f: 2.0, z: 1 },     // 넘침 없음
    soft: { f: 1.3, z: .95 },     // 카메라
    pop: { f: 3.4, z: .7 },       // 아이콘이 0에서 튀어나올 때 (조금 넘침)
    lead: { f: 4.2, z: .8 },      // 늘어나는 앞쪽 끝
    trail: { f: 2.3, z: .9 },     // 따라오는 뒤쪽 끝
  };
  M.spring = (t, o) => {
    if (t <= 0) return 0;
    o = typeof o === 'string' ? SP[o] : (o || SP.snappy);
    const w = 2 * Math.PI * (o.f ?? 3), z = o.z ?? .86;
    if (z < 1) { const wd = w * Math.sqrt(1 - z * z); return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + (z * w / wd) * Math.sin(wd * t)); }
    if (z === 1) return 1 - Math.exp(-w * t) * (1 + w * t);
    const q = Math.sqrt(z * z - 1), r1 = -w * (z - q), r2 = -w * (z + q);
    return 1 + (r2 * Math.exp(r1 * t) - r1 * Math.exp(r2 * t)) / (r1 - r2);
  };

  /* 한 키의 진행도 0→1. spec: 스프링 이름/객체, 또는 {d: 길이, e: 'outCubic'} */
  function stepK(t, t0, spec) {
    if (spec && spec.d != null) {
      const k = M.prog(t, t0, spec.d);
      return (typeof spec.e === 'function' ? spec.e : E[spec.e || 'inOutCubic'])(k);
    }
    return M.spring(t - t0, spec);
  }
  M.stepK = stepK;

  /* 여러 번 바뀌는 값. keys = [[t0, v0], [t1, v1, spec], ...]
   * 값 = v0 + Σ (v_i − v_{i−1}) · step(t − t_i). 바뀔 때마다 스프링 하나를 더하므로 시간의 순수 함수. 배열 값도 됨. */
  M.anim = function (keys, t, def) {
    const first = keys[0][1];
    if (Array.isArray(first)) {
      const out = first.slice();
      for (let i = 1; i < keys.length; i++) {
        const [ti, vi, sp] = keys[i];
        if (t <= ti) break;
        const k = stepK(t, ti, sp || def), prev = keys[i - 1][1];
        for (let j = 0; j < out.length; j++) out[j] += (vi[j] - prev[j]) * k;
      }
      return out;
    }
    let v = first;
    for (let i = 1; i < keys.length; i++) {
      const [ti, vi, sp] = keys[i];
      if (t <= ti) break;
      v += (vi - keys[i - 1][1]) * stepK(t, ti, sp || def);
    }
    return v;
  };
  // 계단 값 (문자열·상태 이름): t 직전의 마지막 키 값
  M.at = function (keys, t) { let v = keys[0][1]; for (const [ti, vi] of keys) { if (t >= ti) v = vi; else break; } return v; };

  /* ---------- 박자 ---------- */
  M.bpm = +(S.content.bpm || 120);
  M.beatLen = 60 / M.bpm;
  M.beat = n => n * M.beatLen;            // n번째 박(0부터)의 시각
  M.bar = n => n * 4 * M.beatLen;

  /* ---------- 색 ---------- */
  function hexRgb(h) { h = String(h).replace('#', ''); if (h.length === 3) h = h.split('').map(c => c + c).join(''); const n = parseInt(h, 16); return [n >> 16 & 255, n >> 8 & 255, n & 255]; }
  M.rgb = hexRgb;
  M.color = (a, b, k) => { const A = Array.isArray(a) ? a : hexRgb(a), B = Array.isArray(b) ? b : hexRgb(b); return `rgb(${A.map((v, i) => Math.round(lerp(v, B[i], clamp(k)))).join(',')})`; };

  /* ---------- 요소 다루기 ---------- */
  const px = v => (Math.round(v * 100) / 100) + 'px';
  M.px = px;
  // 둥근 사각형 하나 (가운데 x,y 기준). 크기·반경·색을 매 프레임 바꾸면 "같은 모양이 계속 변하는" 모프가 됨
  M.box = function (el, o) {
    const st = el.style;
    if (o.w != null) st.width = px(Math.max(0, o.w));
    if (o.h != null) st.height = px(Math.max(0, o.h));
    if (o.x != null) st.left = px(o.x - (o.w ?? el.offsetWidth) / 2);
    if (o.y != null) st.top = px(o.y - (o.h ?? el.offsetHeight) / 2);
    if (o.r != null) st.borderRadius = px(Math.max(0, Math.min(o.r, (o.w ?? 1e9) / 2, (o.h ?? 1e9) / 2)));
    if (o.bg != null) st.background = o.bg;
    if (o.o != null) st.opacity = clamp(o.o).toFixed(3);
    if (o.s != null || o.rot != null) st.transform = `rotate(${(o.rot || 0).toFixed(3)}deg) scale(${(o.s ?? 1).toFixed(4)})`;
    // 크기가 0이면 숨김. 그 밖에는 인라인 값을 비워서 클래스(.hid 등)로 켜고 끈 상태를 따름
    st.visibility = (o.o != null && o.o <= .001) || (o.w != null && o.w <= .1) || (o.h != null && o.h <= .1) ? 'hidden' : '';
  };
  M.show = (el, on) => { el.style.visibility = on ? 'inherit' : 'hidden'; };   // 숨긴 부모 아래 자식이 비쳐 보이지 않게 inherit
  /* 요소 하나를 (x, y)에 둠. ax·ay 는 요소 안 기준점(0.5 = 가운데). o<=0 이면 숨김. 요소는 position:absolute, left/top 0 */
  M.place = function (el, x, y, { s = 1, sx = 1, sy = 1, rot = 0, o = 1, ax = .5, ay = .5, blur = 0 } = {}) {
    const st = el.style;
    st.transform = `translate(${px(x)}, ${px(y)}) translate(${(-ax * 100).toFixed(2)}%, ${(-ay * 100).toFixed(2)}%) rotate(${rot.toFixed(3)}deg) scale(${(s * sx).toFixed(4)}, ${(s * sy).toFixed(4)})`;
    st.transformOrigin = `${(ax * 100).toFixed(1)}% ${(ay * 100).toFixed(1)}%`;
    st.opacity = clamp(o).toFixed(3);
    st.filter = blur > .05 ? `blur(${blur.toFixed(2)}px)` : '';
    st.visibility = o <= .001 || Math.abs(s * sx) < .001 || Math.abs(s * sy) < .001 ? 'hidden' : 'inherit';
  };
  /* SVG 선 그리기: k=0 안 보임 → 1 다 그려짐 */
  M.draw = function (path, k) {
    if (!path._len) { path._len = path.getTotalLength ? path.getTotalLength() || 1 : 1; path.style.strokeDasharray = path._len + ' ' + path._len; }
    path.style.strokeDashoffset = (path._len * (1 - clamp(k))).toFixed(2);
    path.style.visibility = k <= .001 ? 'hidden' : 'inherit';
  };
  /* 손으로 그린 선: 직선·타원을 살짝 흔들린 SVG 경로로 (시드가 같으면 늘 같은 모양)
     M.rough('line', {x1, y1, x2, y2, amp, seed}) · M.rough('ellipse', {cx, cy, rx, ry, amp, turns, seed})
     M.rough('rect', {x, y, w, h, amp, seed, over}) 네 변을 따로 긋고 모서리에서 살짝 삐져나옴(over, 기본 짧은 변의 4%)
     그리기: <path d="..." fill="none" stroke="..."> 를 M.draw(path, k) 나 strokeDashoffset 트윈으로 */
  M.rough = function (kind, o = {}) {
    const r = M.rng(o.seed || 1), amp = o.amp ?? 1;
    if (kind === 'rect') {
      const { x, y, w, h } = o, ov = o.over ?? Math.min(w, h) * .04, j = () => (r() - .5) * ov;
      const sides = [[x - ov * r(), y + j(), x + w + ov * r(), y + j()], [x + w + j(), y - ov * r(), x + w + j(), y + h + ov * r()],
        [x + w + ov * r(), y + h + j(), x - ov * r(), y + h + j()], [x + j(), y + h + ov * r(), x + j(), y - ov * r()]];
      return sides.map(([x1, y1, x2, y2], i) => M.rough('line', { x1, y1, x2, y2, amp: amp * .7, seed: (o.seed || 1) * 7 + i })).join(' ');
    }
    const pts = [];
    if (kind === 'line') {
      const n = 14, dx = o.x2 - o.x1, dy = o.y2 - o.y1, L = Math.hypot(dx, dy) || 1, nx = -dy / L, ny = dx / L;
      const w1 = r() * 6.28, w2 = r() * 6.28, bow = (r() - .5) * 2.2 * amp;
      for (let i = 0; i <= n; i++) {
        const k = i / n, off = (Math.sin(k * Math.PI) * bow + Math.sin(k * 7 + w1) * .5 * amp + Math.sin(k * 13 + w2) * .25 * amp) * L * .006;
        pts.push([o.x1 + dx * k + nx * off, o.y1 + dy * k + ny * off]);
      }
    } else {
      const turns = o.turns ?? 1.12, n = 48, a0 = -2.2 + r() * .6, w = r() * 6.28;
      for (let i = 0; i <= n; i++) {
        const k = i / n, a = a0 + k * turns * Math.PI * 2, j = 1 + (Math.sin(a * 2 + w) * .05 + (k - .5) * .07) * amp;
        pts.push([o.cx + Math.cos(a) * o.rx * j, o.cy + Math.sin(a) * o.ry * j * (1 + Math.sin(a + w) * .03 * amp)]);
      }
    }
    let d = `M ${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
    for (let i = 1; i < pts.length - 1; i++) { const mx = (pts[i][0] + pts[i + 1][0]) / 2, my = (pts[i][1] + pts[i + 1][1]) / 2; d += ` Q ${pts[i][0].toFixed(1)} ${pts[i][1].toFixed(1)} ${mx.toFixed(1)} ${my.toFixed(1)}`; }
    const lp = pts[pts.length - 1];
    return d + ` L ${lp[0].toFixed(1)} ${lp[1].toFixed(1)}`;
  };
  /* 시드가 있는 난수 (같은 시드면 늘 같은 수열) */
  M.rng = function (seed) { let a = (seed >>> 0) || 1; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; };
  /* 들어왔다 나가는 진행도: [0..1] 들어옴(스프링), 나갈 때 1→2 (inCubic). 나가는 시각 tOut 이 없으면 계속 1 */
  M.inout = (t, tIn, tOut, spIn = 'snappy', dOut = .35) => {
    if (t < tIn) return 0;
    if (tOut != null && t >= tOut) return 1 + E.inCubic(M.prog(t, tOut, dOut));
    return Math.min(1.2, M.spring(t - tIn, spIn));
  };
  /* 화면 전체가 아주 천천히 떠다님 (읽는 동안 화면이 완전히 멈추지 않게). el 은 화면을 꽉 채운 판 */
  M.drift = (el, t, a = 1) => {
    const u = Math.min(S.W, S.H) / 100;
    el.style.transformOrigin = '50% 50%';
    el.style.transform = `translate(${(Math.sin(t * .7) * .35 * u * a).toFixed(2)}px, ${(Math.cos(t * .55) * .3 * u * a).toFixed(2)}px) scale(${(1 + .012 * a + Math.sin(t * .45) * .008 * a).toFixed(4)})`;
  };
  /* 감쇠 진자: 처음 각도 a0 에서 흔들리다 멈춤 */
  M.swing = (t, t0, a0, f = 1.1, z = .16) => { if (t < t0) return a0; const w = 2 * Math.PI * f, dt = t - t0; return a0 * Math.exp(-z * w * dt) * Math.cos(w * Math.sqrt(1 - z * z) * dt); };
  // 마스크 선 아래에서 올라오는 글자: 부모(.mask)는 overflow:hidden, k=0 숨음 → 1 제자리, k>1 은 위로 빠짐(나갈 때 1→2)
  M.rise = function (el, k) {
    const y = k <= 1 ? (1 - k) * 110 : -(k - 1) * 110;
    el.style.transform = `translateY(${y.toFixed(2)}%)`;
    el.style.visibility = (k <= 0 || k >= 2) ? 'hidden' : 'inherit';
  };
  // 짧게 흐려지며 내용 바꾸기 (UI 모프 영상 전용. 키노트 영상은 흐림 금지)
  M.swap = function (el, k) { // k: -1(들어오기 전) .. 0(보임) .. 1(나감)
    const a = Math.abs(k);
    el.style.opacity = (1 - clamp(a)).toFixed(3);
    el.style.filter = a > .001 && a < .999 ? `blur(${(a * 6).toFixed(2)}px)` : 'none';
    el.style.transform = `scale(${(1 - .06 * a).toFixed(4)})`;
    el.style.visibility = a >= .999 ? 'hidden' : 'inherit';
  };
  // 타자 치기: t0부터 초당 cps 글자
  M.type = (text, t, t0, cps = 18) => text.slice(0, clamp(Math.floor((t - t0) * cps), 0, text.length));
  // 깜빡임: t0 전에는 늘 켜짐, 그 뒤로 period 초마다 반은 켜지고 반은 꺼짐 (타자 커서)
  M.blink = (t, t0 = 0, period = .5) => t < t0 || ((t - t0) % period) < period / 2;
  /* 글자 맞추기(스크램블): 앞 글자부터 차례로 제 글자로 맞춰짐. k 0→1 진행도.
     맞춰지기 직전 win 글자는 pool 의 무작위 글자로 돌고, 그 뒤 글자는 o.blank(기본 빈칸, o.noise 면 무작위 글자).
     무작위 글자는 frame(보통 Math.floor(t * 초당 장 수))과 seed 로만 정해져서 같은 시각이면 늘 같음.
     pool: 글자열 또는 (원래 글자 → 글자열) 함수. 공백은 그대로. o.array 면 글자 배열(아직 안 나온 글자는 null) */
  const SCR_POOL = '#%&*+=<>/?!$@0123456789ABCDEFGHJKLMNPRSTUVWXYZ';
  M.scramble = function (text, k, o = {}) {
    const cs = [...String(text)], n = cs.length, win = Math.max(1, o.win ?? 4), front = clamp(k) * (n + win);
    const r = M.rng((((o.seed || 1) * 7919) ^ ((o.frame || 0) * 104729)) >>> 0);
    const out = cs.map((c, i) => {
      const x = r();
      if (/\s/.test(c) || i < front - win) return c;
      if (i >= front && !o.noise) return o.array ? null : (o.blank ?? ' ');
      const p = [...(typeof o.pool === 'function' ? o.pool(c) : (o.pool || SCR_POOL))];
      return p.length ? p[Math.floor(x * p.length)] : c;
    });
    return o.array ? out : out.join('');
  };
  // 주행거리계 자리 하나: 0 에서 출발해 turns 바퀴 돈 뒤 digit 에 멈추는 위치 (0~10 소수, 10 은 다시 0). 화면에는 0~9 다음에 0 을 한 칸 더 둔 세로 띠를 위치 × 칸 높이만큼 올림
  M.roll = (digit, k, turns = 1) => ((+digit + 10 * Math.max(0, Math.round(turns))) * clamp(k)) % 10;

  /* ---------- 카메라 ----------
   * world 는 W×H 크기의 판. (cx, cy)를 화면 가운데에 두고 zoom 배 확대. transform-origin 0 0.
   * 카메라가 확대하는 요소에는 will-change 를 쓰지 않습니다(글자가 흐려짐). */
  M.camera = function (el, cx, cy, zoom, rot = 0) {
    el.style.transformOrigin = '0 0';
    el.style.transform = `translate(${px(S.W / 2)}, ${px(S.H / 2)}) scale(${zoom.toFixed(5)}) rotate(${rot.toFixed(3)}deg) translate(${px(-cx)}, ${px(-cy)})`;
  };

  /* ---------- 커서 ---------- */
  const CURSOR_SVG = '<svg viewBox="0 0 28 34" width="28" height="34" aria-hidden="true"><path d="M3 2 L3 26 L9.2 20.4 L13.4 30.6 L17.6 28.8 L13.5 18.8 L22 18.8 Z" fill="#0b0b0c" stroke="#fff" stroke-width="2.2" stroke-linejoin="round"/></svg>';
  const HAND_SVG = '<svg viewBox="0 0 28 34" width="28" height="34" aria-hidden="true"><path d="M10 3.5c1.4 0 2.4 1 2.4 2.4v8.2l.4-.1V12c0-1.3 1-2.3 2.3-2.3s2.3 1 2.3 2.3v1.4c.3-1.1 1.3-1.9 2.4-1.9 1.3 0 2.3 1 2.3 2.3v1.7c.4-.9 1.2-1.4 2.1-1.4 1.3 0 2.2 1 2.2 2.3v6.4c0 5-3.8 9.2-9 9.2h-1.6c-3 0-5.2-1.2-6.9-3.6L4 20.6c-.8-1.1-.6-2.6.5-3.4 1-.8 2.5-.6 3.3.4l.9 1.2V5.9C8.7 4.5 8.7 3.5 10 3.5z" fill="#fff" stroke="#0b0b0c" stroke-width="1.8" stroke-linejoin="round"/></svg>';
  M.Cursor = function (parent, o = {}) {
    const el = S.h(`<div class="m-cursor"><div class="m-cur-ring"></div><div class="m-cur-arrow">${CURSOR_SVG}</div><div class="m-cur-hand">${HAND_SVG}</div></div>`);
    parent.appendChild(el);
    const ring = el.querySelector('.m-cur-ring'), arrow = el.querySelector('.m-cur-arrow'), hand = el.querySelector('.m-cur-hand');
    const size = o.size || 1;
    return {
      el,
      /* x, y: 끝점 좌표(world). down: 0..1 누른 정도. clickK: 0..1 클릭 물결 진행. hand: 손가락 모양 */
      set(x, y, { down = 0, ring: rk = -1, hand: hk = false, o: op = 1, s = 1 } = {}) {
        el.style.transform = `translate(${px(x)}, ${px(y)}) scale(${(size * s * (1 - .14 * down)).toFixed(4)})`;
        el.style.opacity = clamp(op).toFixed(3);
        el.style.visibility = op <= .001 ? 'hidden' : 'inherit';
        arrow.style.visibility = hk ? 'hidden' : 'inherit';
        hand.style.visibility = hk ? 'inherit' : 'hidden';
        if (rk >= 0 && rk < 1) {
          ring.style.visibility = 'inherit';
          ring.style.transform = `translate(-50%, -50%) scale(${(.3 + rk * 1.4).toFixed(3)})`;
          ring.style.opacity = ((1 - rk) * .55).toFixed(3);
        } else ring.style.visibility = 'hidden';
      },
    };
  };
  /* 커서 경로: pts = [[t, x, y], ...] 사이를 부드럽게(inOutCubic) 이동. clicks = [t...] */
  M.cursorAt = function (pts, clicks, t, o = {}) {
    let x = pts[0][1], y = pts[0][2];
    for (let i = 1; i < pts.length; i++) {
      const [t1, x1, y1, d] = pts[i], t0 = pts[i - 1][0];
      const dur = d ?? Math.min(.55, Math.max(.2, t1 - t0));
      const k = E.inOutCubic(M.prog(t, t1 - dur, dur));
      x = lerp(x, x1, k); y = lerp(y, y1, k);
    }
    let down = 0, ring = -1;
    for (const c of clicks || []) {
      const ct = Array.isArray(c) ? c[0] : c, hold = Array.isArray(c) ? c[1] : 0;
      // 누르기 0.06초 전부터 내려가고, 놓을 때 스프링으로 복귀
      const press = M.prog(t, ct - .06, .06) - M.spring(t - (ct + hold + .02), SP.snappy);
      down = Math.max(down, clamp(press));
      if (t >= ct && t < ct + .45) ring = (t - ct) / .45;
    }
    return { x, y, down, ring };
  };

  /* ---------- 6장 조리개 ----------
   * 가운데 (cx, cy), 바깥 원 반지름 R, 안쪽 육각형 반지름 r(0이면 닫힘).
   * 날개 하나 = 육각형 꼭짓점 둘 + 양쪽 변의 연장선 + 두 연장선 사이의 짧은 호. 여섯 장이 빈틈없이 맞물립니다. */
  M.irisPaths = function (cx, cy, R, r, rot = 0) {
    const out = [], V = [], D = [];
    for (let k = 0; k < 6; k++) {
      const a = rot + k * Math.PI / 3;
      V.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
      const ea = rot + (k + .5) * Math.PI / 3 + Math.PI / 2;   // 변 V_k→V_{k+1} 의 방향
      D.push([Math.cos(ea), Math.sin(ea)]);
    }
    const hit = (p, d) => { // p 에서 d 방향 반직선이 원(R)과 만나는 점
      const ox = p[0] - cx, oy = p[1] - cy, b = ox * d[0] + oy * d[1], c = ox * ox + oy * oy - R * R;
      const s = -b + Math.sqrt(Math.max(0, b * b - c));
      return [p[0] + d[0] * s, p[1] + d[1] * s];
    };
    for (let k = 0; k < 6; k++) {
      const k1 = (k + 1) % 6, km = (k + 5) % 6;
      const P = hit(V[k1], D[k]);       // 이 변의 연장선 끝
      const Q = hit(V[k], D[km]);       // 앞 변의 연장선 끝
      let a1 = Math.atan2(P[1] - cy, P[0] - cx), a2 = Math.atan2(Q[1] - cy, Q[0] - cx);
      let da = a2 - a1; while (da > Math.PI) da -= 2 * Math.PI; while (da < -Math.PI) da += 2 * Math.PI;
      let d = `M${V[k][0].toFixed(2)} ${V[k][1].toFixed(2)}L${V[k1][0].toFixed(2)} ${V[k1][1].toFixed(2)}L${P[0].toFixed(2)} ${P[1].toFixed(2)}`;
      const n = 10;
      for (let j = 1; j <= n; j++) { const a = a1 + da * j / n; d += `L${(cx + R * Math.cos(a)).toFixed(2)} ${(cy + R * Math.sin(a)).toFixed(2)}`; }
      out.push({ d: d + 'Z', seam: [V[k1], P] });
    }
    return out;
  };
  // svg 안에 날개 6장을 그려 두고 매 프레임 open(0 닫힘 … 1 열림)만 바꿈
  M.Iris = function (svg, o = {}) {
    const NS = 'http://www.w3.org/2000/svg';
    const g = document.createElementNS(NS, 'g');
    svg.appendChild(g);
    const blades = [], seams = [];
    for (let k = 0; k < 6; k++) {
      const p = document.createElementNS(NS, 'path');
      p.setAttribute('fill', o.fill || '#111214');
      g.appendChild(p); blades.push(p);
    }
    for (let k = 0; k < 6; k++) {
      const l = document.createElementNS(NS, 'path');
      l.setAttribute('stroke', o.seam || 'rgba(255,255,255,.16)'); l.setAttribute('stroke-width', o.seamW || 1.5); l.setAttribute('fill', 'none');
      g.appendChild(l); seams.push(l);
    }
    return {
      g,
      set(cx, cy, R, open, rot0 = 0) {
        // 다 열릴 무렵에는 날개 바깥 원을 키워서, 육각형 구멍이 R 원(과 그 안의 사각형)을 완전히 벗어난 뒤에 숨김
        // (바깥 원을 그대로 두면 열린 순간 모서리에 남은 날개 조각이 한 프레임에 사라져 튐)
        const o = clamp(open), sm = clamp((o - .55) / .45), Rd = R * (1 + .36 * sm * sm * (3 - 2 * sm));
        const r = Rd * 1.02 * o;
        g.style.visibility = open >= .999 ? 'hidden' : 'inherit';
        const rot = rot0 + (1 - o) * Math.PI / 6;    // 닫힐수록 비틀림
        M.irisPaths(cx, cy, Rd, r, rot).forEach((b, k) => {
          blades[k].setAttribute('d', b.d);
          seams[k].setAttribute('d', `M${b.seam[0][0].toFixed(2)} ${b.seam[0][1].toFixed(2)}L${b.seam[1][0].toFixed(2)} ${b.seam[1][1].toFixed(2)}`);
        });
      },
    };
  };

  /* ---------- 화면을 덮는 검은 물결(플러드) ----------
   * (x, y)에서 원이 커져 화면 네 모서리를 넘을 때까지. 반쯤만 덮인 프레임이 생기지 않게 약 0.3초, 모서리 너머까지 키움. */
  M.floodRadius = (x, y, W = S.W, H = S.H) => Math.max(Math.hypot(x, y), Math.hypot(W - x, y), Math.hypot(x, H - y), Math.hypot(W - x, H - y)) * 1.08;

  /* ---------- 리퀴드 글래스 ----------
   * backdrop-filter:url() 은 크로미움에서 변위 지도를 잘못 읽으므로, 유리 요소마다 뒤 장면(src) 복제를 들고
   * SVG 필터(feImage 로 둥근 사각형 거리장 → feDisplacementMap 세 번, 채널마다 조금씩 다른 세기 = 색 번짐)를 겁니다.
   * 크기가 바뀔 때만 거리장 이미지를 다시 만듭니다(2px 단위로 묶어서). */
  let glassN = 0;
  M.Glass = function (host, o = {}) {
    const id = 'mg' + (++glassN);
    const NS = 'http://www.w3.org/2000/svg';
    let defs = document.getElementById('m-glass-defs');
    if (!defs) {
      defs = document.createElementNS(NS, 'svg');
      defs.id = 'm-glass-defs';
      defs.setAttribute('width', '0'); defs.setAttribute('height', '0');
      defs.style.position = 'absolute';
      document.body.appendChild(defs);
    }
    const f = document.createElementNS(NS, 'filter');
    f.setAttribute('id', id); f.setAttribute('x', '0'); f.setAttribute('y', '0'); f.setAttribute('width', '1'); f.setAttribute('height', '1');
    f.setAttribute('color-interpolation-filters', 'sRGB');
    f.innerHTML = `<feImage result="map" preserveAspectRatio="none" x="0" y="0"/>
      <feDisplacementMap in="SourceGraphic" in2="map" scale="0" xChannelSelector="R" yChannelSelector="G" result="dR"/>
      <feColorMatrix in="dR" type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" result="r"/>
      <feDisplacementMap in="SourceGraphic" in2="map" scale="0" xChannelSelector="R" yChannelSelector="G" result="dG"/>
      <feColorMatrix in="dG" type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0" result="g"/>
      <feDisplacementMap in="SourceGraphic" in2="map" scale="0" xChannelSelector="R" yChannelSelector="G" result="dB"/>
      <feColorMatrix in="dB" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0" result="b"/>
      <feBlend in="r" in2="g" mode="screen" result="rg"/><feBlend in="rg" in2="b" mode="screen"/>`;
    defs.appendChild(f);
    const img = f.querySelector('feImage'), dms = f.querySelectorAll('feDisplacementMap');
    host.classList.add('m-glass');
    // 뒤 장면 복제(inner)와 테두리 빛(rim)은 맨 아래에 깔고, host 에 원래 있던 내용(글자·아이콘)이 그 위에 오게 함
    const inner = S.h('<div class="m-glass-in"></div>');
    const rim = S.h('<div class="m-glass-rim"></div>');
    host.insertBefore(rim, host.firstChild);
    host.insertBefore(inner, host.firstChild);
    inner.style.filter = `url(#${id})`;
    let lastKey = '';
    const canvas = document.createElement('canvas');
    function mapFor(w, h, r, band) {
      // 가장자리 띠(band) 안에서만 바깥쪽(법선) 방향으로 밀어내는 지도. 가운데는 128(변위 없음)
      const sc = .5, W = Math.max(2, Math.round(w * sc)), H = Math.max(2, Math.round(h * sc));
      canvas.width = W; canvas.height = H;
      const ctx = canvas.getContext('2d'), im = ctx.createImageData(W, H), d = im.data;
      const rr = Math.min(r, w / 2, h / 2) * sc, bw = band * sc, hw = W / 2, hh = H / 2;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        const px_ = x + .5 - hw, py_ = y + .5 - hh;
        const qx = Math.abs(px_) - (hw - rr), qy = Math.abs(py_) - (hh - rr);
        const ox = Math.max(qx, 0), oy = Math.max(qy, 0);
        const sd = Math.hypot(ox, oy) + Math.min(Math.max(qx, qy), 0) - rr;   // 둥근 사각형 부호 거리 (안쪽 음수)
        let nx, ny;
        if (qx > 0 && qy > 0) { const L = Math.hypot(ox, oy) || 1; nx = ox / L * Math.sign(px_); ny = oy / L * Math.sign(py_); }
        else if (qx > qy) { nx = Math.sign(px_); ny = 0; } else { nx = 0; ny = Math.sign(py_); }
        const depth = clamp(-sd / bw);                   // 가장자리 0 → 띠 안쪽 1
        const m = (1 - depth) ** 2;                      // 가장자리일수록 세게
        const i = (y * W + x) * 4;
        d[i] = 128 - nx * m * 127; d[i + 1] = 128 - ny * m * 127; d[i + 2] = 128; d[i + 3] = 255;
      }
      ctx.putImageData(im, 0, 0);
      return canvas.toDataURL();
    }
    return {
      el: host, inner, rim, id,
      /* w,h,r: 유리 크기와 반경. srcEl: 뒤 장면 복제 요소(inner 안에 넣어 둔 것). ox,oy: 그 복제를 옮길 양
         strength: 굴절 세기(px), band: 굴절 띠 폭(px) */
      set({ w, h, r, strength = 26, band = 22, tint = .12, light = 1 }) {
        const key = [Math.round(w / 2), Math.round(h / 2), Math.round(r / 2), Math.round(band)].join(',');
        if (key !== lastKey) {
          lastKey = key;
          const url = mapFor(w, h, r, band);
          img.setAttribute('href', url);
          img.setAttribute('width', w); img.setAttribute('height', h);
        }
        dms[0].setAttribute('scale', (strength * 1.08).toFixed(2));
        dms[1].setAttribute('scale', strength.toFixed(2));
        dms[2].setAttribute('scale', (strength * .92).toFixed(2));
        host.style.setProperty('--tint', tint.toFixed(3));
        host.style.setProperty('--light', light.toFixed(3));
      },
    };
  };
})();
