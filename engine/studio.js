/* Motion Studio engine
 * 모든 영상이 공유하는 런타임. build.py가 HTML에 그대로 넣어 줍니다.
 *
 * 규칙(중요): 화면은 "시간 t의 순수 함수"여야 합니다.
 *   - 등장·퇴장 같은 사건은 Studio.tl(GSAP 타임라인)에 넣고,
 *   - 계속 움직이는 효과(회전, 흔들림, 반짝임)는 Studio.ambient(t => ...)로 넣습니다.
 *   - setInterval, requestAnimationFrame 루프, CSS 무한 애니메이션은 쓰지 않습니다.
 *     렌더러가 window.__seek(t)로 아무 시점이나 정확히 찍기 때문입니다.
 */
(function () {
  'use strict';

  const FORMATS = {
    tall: { w: 1080, h: 1920, label: '9:16' },
    portrait: { w: 1080, h: 1350, label: '4:5' },
    square: { w: 1080, h: 1080, label: '1:1' },
    wide: { w: 1920, h: 1080, label: '16:9' },
  };
  // 글자·로고를 두면 안 되는 가장자리 (px). 플랫폼 UI가 덮는 영역 기준의 제작 가이드입니다.
  const SAFE_PRESETS = {
    reels: { top: 270, bottom: 672, left: 65, right: 65 },   // Meta 릴스 광고 (가장 엄격, 9:16 기본값)
    stories: { top: 270, bottom: 384, left: 65, right: 65 }, // Meta 스토리
    shorts: { top: 288, bottom: 480, left: 65, right: 140 }, // 유튜브 쇼츠 (오른쪽 버튼 영역 포함, 보수적)
    feed: { top: 54, bottom: 54, left: 54, right: 54 },      // 4:5, 1:1 피드
    wide: { top: 54, bottom: 54, left: 96, right: 96 },      // 16:9
    none: { top: 0, bottom: 0, left: 0, right: 0 },
  };

  const fmtKey = (window.__FORMAT && window.__FORMAT.key) || 'tall';
  const F = Object.assign({ key: fmtKey }, FORMATS[fmtKey] || FORMATS.tall, window.__FORMAT || {});
  const content = window.__CONTENT || {};
  const brand = window.__BRAND || {};
  const assets = window.__ASSETS || {};
  const safeName = (window.__SAFE_ZONE && window.__SAFE_ZONE[F.key]) ||
    { tall: 'reels', portrait: 'feed', square: 'feed', wide: 'wide' }[F.key];
  const safe = typeof safeName === 'object' ? safeName : (SAFE_PRESETS[safeName] || SAFE_PRESETS.none);

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const h = html => { const t = document.createElement('template'); t.innerHTML = html.trim(); return t.content.firstElementChild; };
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const tl = gsap.timeline({ paused: true });
  const ambients = [];
  const idles = [];   // 발표 자료: 장이 멈춰 있는 동안에도 천천히 움직이는 것 (그라디언트 덩어리 등). fn(멈춘 뒤 흐른 초)

  const S = window.Studio = {
    F, W: F.w, H: F.h, key: F.key, safe, safeName, brand, content, assets,
    tl, dur: 0, fps: window.__FPS || 30,
    $, $$, h, esc,
    img: key => (key && assets[key]) || '',
    ambient(fn) { ambients.push(fn); },
    // 시간과 따로 도는 느린 배경 움직임. 영상에서는 t 를 그대로 받고, 발표 자료에서는 화면을 연 뒤 흐른 시간(렌더·PDF 는 0)을 받음
    idle(fn) { idles.push(fn); },
    tick(t) { for (const fn of ambients) fn(t); overlayTick(t); const it = S.idleT == null ? t : S.idleT; for (const fn of idles) fn(it); },
    setDuration(d) { S.dur = d; },
    is: (...keys) => keys.includes(F.key),
  };

  /* ---------- stage ---------- */
  const root = document.documentElement;
  root.dataset.format = F.key;
  const vars = { '--W': F.w + 'px', '--H': F.h + 'px', '--u': (Math.min(F.w, F.h) / 100) + 'px',
    '--safe-t': safe.top + 'px', '--safe-b': safe.bottom + 'px', '--safe-l': safe.left + 'px', '--safe-r': safe.right + 'px' };
  for (const [k, v] of Object.entries(vars)) root.style.setProperty(k, v);
  function fitStage() {
    const st = $('#stage'); if (!st) return;
    st.style.setProperty('--s', Math.min(innerWidth / F.w, innerHeight / F.h));
  }
  addEventListener('resize', fitStage);

  /* ---------- text helpers ---------- */
  // 글자 단위로 쪼개기. \n 은 줄바꿈으로 유지, 공백은 그대로.
  S.chars = function (el) {
    const text = el.textContent; el.textContent = '';
    const out = [];
    for (const line of text.split('\n')) {
      if (out.length) el.appendChild(document.createElement('br'));
      for (const c of line) { const s = document.createElement('span'); s.className = 'ch'; s.textContent = c; el.appendChild(s); out.push(s); }
    }
    return out;
  };
  // 단어 단위로 쪼개기 (한국어는 어절)
  S.words = function (el) {
    const text = el.textContent; el.textContent = '';
    const out = [];
    text.split('\n').forEach((line, li) => {
      if (li) el.appendChild(document.createElement('br'));
      line.split(/(\s+)/).forEach(part => {
        if (!part) return;
        if (/^\s+$/.test(part)) { el.appendChild(document.createTextNode(part)); return; }
        const s = document.createElement('span'); s.className = 'wd'; s.textContent = part; el.appendChild(s); out.push(s);
      });
    });
    return out;
  };
  // 상자 안에 들어가도록 글자 크기를 줄임. maxLines를 주면 줄 수도 제한.
  // 글자 크기 자동 맞춤. 작성자가 \n 으로 나눈 줄 수를 먼저 지키려고 하고(keepMin 까지 줄임),
  // 그래도 안 되면 maxLines 안에서 줄바꿈을 허용합니다.
  S.fit = function (el, { max, min, maxLines, maxHeight, keepLines = true, keepMin = .62 } = {}) {
    const cs = getComputedStyle(el);
    let size = max || parseFloat(cs.fontSize); min = min || size * 0.4;
    const lh = () => parseFloat(getComputedStyle(el).lineHeight) || size * 1.2;
    const over = (lines) => {
      if (el.scrollWidth > el.clientWidth + 1) return true;
      const hgt = el.offsetHeight;
      if (maxHeight && hgt > maxHeight + 1) return true;
      if (lines && hgt > lh() * lines + 2) return true;
      return false;
    };
    const set = v => { size = v; el.style.fontSize = v + 'px'; };
    const explicit = (el.textContent.match(/\n/g) || []).length + 1;
    if (keepLines && maxLines && explicit < maxLines) {
      const floor = Math.max(min, (max || size) * keepMin);
      set(max || size);
      while (over(explicit) && size > floor) set(size * 0.95);
      if (!over(explicit)) return size;
    }
    set(max || parseFloat(cs.fontSize));
    while (over(maxLines) && size > min) set(size * 0.94);
    return size;
  };
  // 텍스트 안의 특정 구절을 강조 span으로 감쌈 (마커 효과용)
  S.mark = function (el, phrase) {
    if (!phrase) return null;
    const html = el.innerHTML, i = el.textContent.indexOf(phrase);
    if (i < 0) return null;
    el.innerHTML = esc(el.textContent.slice(0, i)) + '<span class="mark">' + esc(phrase) + '</span>' + esc(el.textContent.slice(i + phrase.length));
    return $('.mark', el);
  };

  /* ---------- tweens (모두 타임라인 시각 t에 추가) ---------- */
  const fx = S.fx = {
    rise(targets, t, o = {}) { return tl.fromTo(targets, { y: o.y ?? 60, autoAlpha: 0, rotation: o.rot ?? 0 }, { y: 0, autoAlpha: 1, rotation: 0, duration: o.d ?? .5, ease: o.ease || 'back.out(1.8)', stagger: o.stagger ?? .04 }, t); },
    pop(targets, t, o = {}) { return tl.fromTo(targets, { scale: o.from ?? 0, autoAlpha: 0 }, { scale: 1, autoAlpha: 1, duration: o.d ?? .45, ease: o.ease || 'back.out(2.4)', stagger: o.stagger ?? .08 }, t); },
    slide(targets, t, o = {}) { const dir = o.dir || 'left', dist = o.dist ?? 120; const from = { autoAlpha: 0 }; from[dir === 'left' || dir === 'right' ? 'x' : 'y'] = (dir === 'left' || dir === 'up' ? -1 : 1) * dist; return tl.fromTo(targets, from, { x: 0, y: 0, autoAlpha: 1, duration: o.d ?? .55, ease: o.ease || 'power3.out', stagger: o.stagger ?? .08 }, t); },
    fade(targets, t, o = {}) { return tl.fromTo(targets, { autoAlpha: 0 }, { autoAlpha: 1, duration: o.d ?? .4, ease: 'none', stagger: o.stagger ?? 0 }, t); },
    out(targets, t, o = {}) { return tl.to(targets, { autoAlpha: 0, y: o.y ?? -30, duration: o.d ?? .3, ease: 'power2.in', stagger: o.stagger ?? .03 }, t); },
    reveal(el, t, o = {}) { return tl.fromTo(el, { clipPath: 'inset(0 100% 0 0)' }, { clipPath: 'inset(0 0% 0 0)', duration: o.d ?? .6, ease: o.ease || 'power3.inOut' }, t); },
    marker(markEl, t, o = {}) { if (!markEl) return; return tl.fromTo(markEl, { '--mk': '0%' }, { '--mk': '100%', duration: o.d ?? .5, ease: 'power2.out' }, t); },
    stamp(el, t, o = {}) { tl.fromTo(el, { scale: 2.4, rotation: o.rot ?? -25, autoAlpha: 0 }, { scale: 1, rotation: o.to ?? -8, autoAlpha: 1, duration: .35, ease: 'power4.in' }, t); fx.shake(t + .35, 8); },
    kenburns(img, t, d, o = {}) { return tl.fromTo(img, { scale: o.from ?? 1.18, xPercent: o.x0 ?? 2, yPercent: o.y0 ?? 0 }, { scale: o.to ?? 1.02, xPercent: o.x1 ?? -2, yPercent: o.y1 ?? 0, duration: d, ease: 'power1.out' }, t); },
    counter(el, t, d, from, to, o = {}) { const obj = { v: from }; const fmt = o.format || (v => Math.round(v).toLocaleString('ko-KR')); el.textContent = fmt(from); return tl.to(obj, { v: to, duration: d, ease: o.ease || 'power2.out', onUpdate: () => { el.textContent = fmt(obj.v); } }, t); },
    shake(t, amt = 10) { return tl.to('#cam', { keyframes: { x: [0, -amt, amt * .8, -amt * .5, amt * .3, 0], y: [0, amt * .6, -amt * .5, amt * .3, 0, 0] }, duration: .32, ease: 'none' }, t); },
    bob(el, amp = 6, speed = .7, phase = 0) { S.ambient(t => { el.style.translate = `0 ${(Math.sin(t * Math.PI * 2 * speed + phase) * amp).toFixed(2)}px`; }); },
  };

  /* ---------- 결 템플릿 공통: 이야기(story)와 스타일 따르기 ----------
     결 템플릿 10개(typeslam·uidemo·sketchbook·dataflow·terminal·collage·stage·glow·brandmark·cinema)는 같은 content 를 읽어요.
     content = { kicker, title, highlight, points[], number{prefix, value, suffix, label, source}, photos[], cta{headline, button, sub}, note }
     그래서 같은 문구로 템플릿만 바꿔도 영상이 통째로 달라져요. (docs/TEMPLATES.md '결 템플릿') */
  S.story = function (c = content) {
    const str = v => (v == null ? '' : String(v)).trim();
    const n = c.number && typeof c.number === 'object' ? c.number : null;
    const raw = n ? String(n.value == null ? '' : n.value).replace(/,/g, '').trim() : '';
    const val = raw !== '' && isFinite(+raw) ? +raw : null;
    const cta = c.cta && typeof c.cta === 'object' ? c.cta : {};
    const slots = (Array.isArray(c.photos) ? c.photos : []).map(str).filter(Boolean).slice(0, 4);
    return {
      kicker: str(c.kicker), title: str(c.title), highlight: str(c.highlight),
      points: (Array.isArray(c.points) ? c.points : []).map(str).filter(Boolean).slice(0, 5),
      number: val == null ? null : { prefix: str(n.prefix), value: val, suffix: str(n.suffix), label: str(n.label), source: str(n.source),
        decimals: (raw.split('.')[1] || '').length },
      photos: slots.map(k => ({ key: k, src: S.img(k) })).filter(p => p.src),   // 실제로 들어 있는 사진만
      photoSlots: slots,                                                         // 미리보기에서 빈 자리를 보여 줄 때
      cta: { headline: str(cta.headline), button: str(cta.button), sub: str(cta.sub) },
      note: str(c.note),
      logo: { img: brand.logo ? S.img(brand.logo) : '', text: str(brand.logoText || brand.name), sub: str(brand.logoSub) },
    };
  };
  // 숫자 꾸미기: 1200 → "1,200", 소수 자리 유지
  S.numText = (v, dec = 0, plain = false) => plain ? Number(v).toFixed(dec) : Number(v).toLocaleString('ko-KR', { minimumFractionDigits: dec, maximumFractionDigits: dec });   // plain: 쉼표 없이 (연도 등)
  // 스타일 따르기 (스타일이 없으면 템플릿 기본값)
  const SMo = () => (S.style && S.style.motion) || {};
  S.ease = def => SMo().ease || def;                 // 주요 등장 이징
  S.easeFn = def => gsap.parseEase(S.ease(def)) || (k => k);   // S.ambient 안에서 쓸 이징 함수
  S.stg = x => x * (+SMo().stagger || 1);           // 어절·항목 사이 간격
  S.sty = () => (S.style && S.style.scenes) || {};  // 장면 힌트(title·number·frame·deco …)

  // 글자를 어절 안 글자로 쪼갬 (강조 어절 표시 유지). { words, chars }
  function splitWC(el, hl) {
    const words = S.words(el), chars = [];
    words.forEach(w => {
      if (hl.has(w.textContent)) w.classList.add('hl');
      const t = w.textContent; w.textContent = '';
      for (const c of t) { const s = document.createElement('span'); s.className = 'ch'; s.textContent = c; w.appendChild(s); chars.push(s); }
    });
    return { words, chars };
  }
  // 줄마다 묶기 (mask·write): 어절의 화면 위치로 줄을 나눠 줄 상자 <span class="mln"><span class="mli">…</span></span>
  function splitLines(el, words) {
    const rows = [];
    words.forEach(w => { const y = Math.round(w.offsetTop); const r = rows.find(r => Math.abs(r.y - y) < 4); r ? r.ws.push(w) : rows.push({ y, ws: [w] }); });
    rows.sort((a, b) => a.y - b.y);
    el.textContent = '';
    return rows.map(r => {
      const ln = document.createElement('span'), li = document.createElement('span');
      ln.className = 'mln'; li.className = 'mli';
      r.ws.forEach((w, i) => { if (i) li.appendChild(document.createTextNode(' ')); li.appendChild(w); });
      ln.appendChild(li); el.appendChild(ln); return li;
    });
  }
  /* 큰 글 등장. 종류는 o.kind > 스타일 scenes.title > o.def > 'rise'
     rise(아래에서) · type(타자, 커서) · slot(어절이 위에서 떨어져 멈춤) · scramble(기호에서 글자로) · blur(흐림에서 선명)
     pop(글자마다 톡) · mask(줄마다 선 아래에서) · write(줄마다 왼쪽부터 끊어 쓰듯) · stamp(도장처럼 쿵) · fade
     el 안의 태그는 없어져요(글만). o.highlight: 강조 어절(.hl 클래스). 다 들어오는 시각을 돌려줌 */
  fx.enter = function (el, t, o = {}) {
    if (!el || !el.textContent.trim()) return t;
    const kind = o.kind || S.sty().title || o.def || 'rise';
    const hl = new Set(String(o.highlight || '').split(/\s+/).filter(Boolean));
    const ease = o.ease || S.ease('power3.out'), k = o.d || 1, M = S.M;
    if (kind === 'type' || kind === 'pop') {
      const { chars } = splitWC(el, hl), n = chars.length;
      if (kind === 'pop') { tl.fromTo(chars, { scale: 0, autoAlpha: 0 }, { scale: 1, autoAlpha: 1, duration: .32 * k, ease: 'back.out(2.2)', stagger: S.stg(.022) }, t); return t + .32 * k + S.stg(.022) * n; }
      const cps = (o.cps || 20) / k, d = n / cps, caret = document.createElement('span'); caret.className = 'caret';
      const show = i => { chars.forEach((c, j) => { c.style.display = j < i ? '' : 'none'; }); const last = chars[i - 1]; if (last) last.after(caret); else el.prepend(caret); };
      let shown = -1;
      S.ambient(tt => {   // 시간의 순수 함수: 앞뒤 어디로 찾아가도 같은 글자 수
        const i = Math.max(0, Math.min(n, Math.round((tt - t) * cps)));
        if (i !== shown) { show(i); shown = i; }
        caret.style.opacity = tt < t - .6 || tt > t + d + (o.caretHold ?? 1.2) ? 0 : (M ? (M.blink(tt, t + d, .5) ? 1 : 0) : 1);
      });
      return t + d;
    }
    const words = kind === 'mask' || kind === 'write' ? null : S.words(el);
    if (words) words.forEach(w => { if (hl.has(w.textContent)) w.classList.add('hl'); });
    const n = words ? words.length : 0;
    switch (kind) {
      case 'slot': {
        words.forEach(w => { const inner = document.createElement('span'); inner.className = 'sli'; while (w.firstChild) inner.appendChild(w.firstChild); w.appendChild(inner); w.classList.add('slw'); });
        tl.fromTo(words.map(w => w.firstChild), { yPercent: -115 }, { yPercent: 0, duration: .45 * k, ease: S.ease('back.out(1.4)'), stagger: S.stg(.08) }, t);
        return t + .45 * k + S.stg(.08) * n;
      }
      case 'scramble': {
        const orig = words.map(w => w.textContent), d = .8 * k;
        words.forEach((w, i) => {
          const t0 = t + S.stg(.05) * i, pool = '#%&*+=<>/?!' + orig[i];
          S.ambient(tt => { const kk = (tt - t0) / d; w.textContent = kk <= 0 ? '' : kk >= 1 || !M ? orig[i] : M.scramble(orig[i], kk, { seed: i + 1, frame: Math.floor(tt * 26), pool, noise: true }); });
        });
        return t + d + S.stg(.05) * n;
      }
      case 'blur':
        tl.fromTo(words, { filter: 'blur(.45em)', autoAlpha: 0, scale: 1.06 }, { filter: 'blur(0em)', autoAlpha: 1, scale: 1, duration: .6 * k, ease, stagger: S.stg(.07) }, t);
        return t + .6 * k + S.stg(.07) * n;
      case 'stamp':
        tl.fromTo(words, { scale: 1.9, autoAlpha: 0 }, { scale: 1, autoAlpha: 1, duration: .26 * k, ease: 'power4.in', stagger: S.stg(.13) }, t);
        fx.shake(t + .26 * k + S.stg(.13) * (n - 1), 6);
        return t + .26 * k + S.stg(.13) * n + .3;
      case 'fade':
        tl.fromTo(el, { autoAlpha: 0 }, { autoAlpha: 1, duration: .55 * k, ease: 'none' }, t);
        return t + .55 * k;
      case 'mask': case 'write': {
        const ws = S.words(el); ws.forEach(w => { if (hl.has(w.textContent)) w.classList.add('hl'); });
        const lis = splitLines(el, ws);
        if (kind === 'mask') { tl.fromTo(lis, { yPercent: 110 }, { yPercent: 0, duration: .6 * k, ease: S.ease('power4.out'), stagger: S.stg(.1) }, t); return t + .6 * k + S.stg(.1) * lis.length; }
        let tt = t;
        lis.forEach(li => { const d = Math.max(.35, li.textContent.length * .045) * k; tl.fromTo(li, { clipPath: 'inset(-20% 100% -20% 0)' }, { clipPath: 'inset(-20% 0% -20% 0)', duration: d, ease: `steps(${Math.max(4, Math.round(d * 12))})` }, tt); tt += d + .05; });
        return tt;
      }
      default:   // rise
        tl.fromTo(words, { y: '.55em', autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: .55 * k, ease, stagger: S.stg(.06) }, t);
        return t + .55 * k + S.stg(.06) * n;
    }
  };
  /* 숫자 등장. 종류는 o.kind > 스타일 scenes.number > 'count'
     count(0에서 올라감) · odometer(자리마다 굴러가 멈춤) · scramble(무작위 숫자에서 맞춰짐). el 에는 숫자만 들어감 */
  fx.num = function (el, t, d, value, o = {}) {
    if (!el) return t;
    const kind = o.kind || S.sty().number || 'count', dec = o.decimals || 0, M = S.M, txt = S.numText(value, dec, o.plain);
    if (kind === 'odometer' && M) {
      el.textContent = '';
      const cols = [...txt].map((c, i) => {
        if (!/\d/.test(c)) { const s = document.createElement('span'); s.textContent = c; el.appendChild(s); return null; }
        const col = document.createElement('span'), strip = document.createElement('span');
        col.className = 'odo'; strip.className = 'odo-s';
        for (let j = 0; j <= 10; j++) { const dd = document.createElement('span'); dd.textContent = j % 10; strip.appendChild(dd); }
        col.appendChild(strip); el.appendChild(col); return { strip, digit: +c, i };
      }).filter(Boolean);
      const nCols = cols.length;
      cols.forEach((c, j) => { c.j = j; });
      S.ambient(tt => {   // 왼쪽 자리일수록 더 많이 돌고 조금 늦게 멈춤
        cols.forEach(c => { const kk = M.clamp((tt - t) / d * 1.12 - (nCols - 1 - c.j) * .03); c.strip.style.transform = `translateY(${(-M.roll(c.digit, M.ease.outCubic(kk), 1 + (nCols - c.j))).toFixed(3)}em)`; });
      });
      return t + d;
    }
    if (kind === 'scramble' && M) {
      S.ambient(tt => { const kk = (tt - t) / d; el.textContent = kk >= 1 ? txt : M.scramble(txt, Math.max(0, kk), { pool: '0123456789', noise: true, seed: 3, frame: Math.floor(Math.max(0, tt) * 30) }); });
      return t + d;
    }
    fx.counter(el, t, d, 0, value, { format: v => S.numText(v, dec, o.plain) });
    return t + d;
  };

  /* ---------- scene transitions (B = 새 장면이 완전히 보이는 시각) ---------- */
  const tr = S.tr = {
    cut(B, from, to) { tl.set(from, { autoAlpha: 0 }, B); tl.set(to, { autoAlpha: 1 }, B); },
    fade(B, from, to, d = .4) { tl.set(to, { autoAlpha: 0 }, B - d); tl.to(to, { autoAlpha: 1, duration: d, ease: 'none' }, B - d); tl.set(from, { autoAlpha: 0 }, B); },
    wipe(B, from, to, colors) {
      const bars = $$('#fx-wipe i'); const cols = colors || [cssVar('--accent'), cssVar('--bg'), cssVar('--paper')];
      bars.forEach((b, i) => tl.set(b, { background: cols[i % cols.length] }, B - .6));
      tl.fromTo(bars, { xPercent: -130 }, { xPercent: 0, duration: .42, ease: 'power3.in', stagger: .06 }, B - .54);
      tl.set(from, { autoAlpha: 0 }, B); tl.set(to, { autoAlpha: 1 }, B);
      tl.to([...bars].reverse(), { xPercent: 130, duration: .46, ease: 'power3.out', stagger: .06 }, B + .02);
    },
    iris(B, from, to, cx = F.w / 2, cy = F.h / 2) {
      const R = Math.hypot(F.w, F.h) * 1.1, ring = $('#fx-ring');
      tl.set(to, { autoAlpha: 1, clipPath: `circle(0px at ${cx}px ${cy}px)` }, B - .5);
      tl.to(to, { clipPath: `circle(${R}px at ${cx}px ${cy}px)`, duration: .6, ease: 'power3.in' }, B - .5);
      tl.set(ring, { autoAlpha: 1, left: cx, top: cy, xPercent: -50, yPercent: -50, width: 0, height: 0 }, B - .5);
      tl.to(ring, { width: R * 2, height: R * 2, duration: .6, ease: 'power3.in' }, B - .5);
      tl.set(ring, { autoAlpha: 0 }, B + .1); tl.set(from, { autoAlpha: 0 }, B + .1); tl.set(to, { clipPath: 'none' }, B + .1);
    },
    push(B, from, to, dir = 1) {
      const dx = F.w * dir;
      tl.set(to, { autoAlpha: 1, x: dx }, B - .42);
      tl.to(to, { x: 0, duration: .78, ease: 'power3.inOut' }, B - .42);
      tl.to(from, { x: -dx * .55, duration: .78, ease: 'power3.inOut' }, B - .42);
      tl.set(from, { autoAlpha: 0, x: 0 }, B + .37);
    },
    // 6장 조리개가 닫혔다가 새 장면 위에서 열림 (그리기는 motion.js 의 M.Iris)
    blades(B, from, to, o = {}) {
      tl.set(from, { autoAlpha: 0 }, B); tl.set(to, { autoAlpha: 1 }, B);
      overlayTr.push({ kind: 'blades', B, close: o.close ?? .42, open: o.open ?? .42, hold: o.hold ?? .06, cx: o.cx ?? F.w / 2, cy: o.cy ?? F.h / 2 });
    },
    // 검은 원이 화면을 덮었다가 오므라들며 새 장면을 보여 줌
    flood(B, from, to, o = {}) {
      tl.set(from, { autoAlpha: 0 }, B); tl.set(to, { autoAlpha: 1 }, B);
      overlayTr.push({ kind: 'flood', B, grow: o.grow ?? .32, shrink: o.shrink ?? .42, hold: o.hold ?? .08, cx: o.cx ?? F.w / 2, cy: o.cy ?? F.h / 2, color: o.color });
    },
    zoom(B, from, to) {
      tl.set(to, { autoAlpha: 0, scale: 1.25 }, B - .45);
      tl.to(from, { scale: .85, autoAlpha: 0, duration: .45, ease: 'power2.in' }, B - .45);
      tl.to(to, { scale: 1, autoAlpha: 1, duration: .55, ease: 'power3.out' }, B - .3);
      tl.set(from, { scale: 1 }, B + .3);
    },
    // 앞 장면은 흐려지며 사라지고, 다음 장면은 흐림에서 선명해짐
    blur(B, from, to, d = .55) {
      const u = Math.min(F.w, F.h) / 100;
      tl.set(to, { autoAlpha: 0, filter: `blur(${(4 * u).toFixed(1)}px)` }, B - d);
      tl.to(from, { autoAlpha: 0, filter: `blur(${(4 * u).toFixed(1)}px)`, duration: d, ease: 'power2.in' }, B - d);
      tl.to(to, { autoAlpha: 1, filter: 'blur(0px)', duration: d + .15, ease: 'power2.out' }, B - d * .6);
      tl.set(from, { filter: 'none' }, B + .2); tl.set(to, { filter: 'none' }, B + d * .4 + .2);
    },
    // 옆으로 휙 넘김. 움직이는 동안 가로 방향으로만 번짐 (dir: 1 왼쪽으로, -1 오른쪽으로)
    whip(B, from, to, dir = 1) {
      const dx = F.w * dir, d = .5;
      tl.set(to, { autoAlpha: 1, x: dx }, B - d / 2);
      tl.to(to, { x: 0, duration: d, ease: 'expo.inOut' }, B - d / 2);
      tl.to(from, { x: -dx, duration: d, ease: 'expo.inOut' }, B - d / 2);
      tl.set(from, { autoAlpha: 0, x: 0 }, B + d / 2);
      overlayTr.push({ kind: 'whip', B, d, els: [from, to] });
    },
    // 정사각 칸들이 정해진 순서로 덮었다가 걷힘 (픽셀·레트로)
    blocks(B, from, to, o = {}) {
      tl.set(from, { autoAlpha: 0 }, B); tl.set(to, { autoAlpha: 1 }, B);
      overlayTr.push({ kind: 'blocks', B, cover: o.cover ?? .35, open: o.open ?? .35, color: o.color, n: o.n || 12 });
    },
  };
  const overlayTr = [];
  // 조리개·플러드는 GSAP 트윈 대신 시간 함수로 그림 (여러 전환이 같은 덮개를 쓰므로 아무 시점으로 건너뛰어도 정확하게)
  function overlayTick(t) {
    const M = S.M; if (!M || !overlayTr.length) return;
    let iris = null, flood = null;
    for (const o of overlayTr) {
      if (o.kind === 'blades' && t >= o.B - o.close && t < o.B + o.hold + o.open) iris = o;
      if (o.kind === 'flood' && t >= o.B - o.grow && t < o.B + o.hold + o.shrink) flood = o;
    }
    whipTick(t); blocksTick(t);
    const svg = $('#fx-iris'), fl = $('#fx-flood');
    if (svg) {
      if (!svg._iris) svg._iris = M.Iris(svg, { fill: darkest(), seam: 'rgba(255,255,255,.18)', seamW: 2 });
      if (iris) {
        const R = M.floodRadius(iris.cx, iris.cy);
        const k = t < iris.B ? M.ease.inCubic(M.prog(t, iris.B - iris.close, iris.close))   // 닫힘
          : 1 - M.ease.outCubic(M.prog(t, iris.B + iris.hold, iris.open));                    // 열림
        svg.style.visibility = 'inherit';
        svg._iris.set(iris.cx, iris.cy, R, 1 - k);
      } else svg.style.visibility = 'hidden';
    }
    if (fl) {
      if (flood) {
        const R = M.floodRadius(flood.cx, flood.cy);
        const k = t < flood.B ? M.ease.inCubic(M.prog(t, flood.B - flood.grow, flood.grow))
          : 1 - M.ease.inOutCubic(M.prog(t, flood.B + flood.hold, flood.shrink));
        const r = R * k;
        fl.style.visibility = r > .5 ? 'inherit' : 'hidden';
        fl.style.width = fl.style.height = (2 * r).toFixed(1) + 'px';
        fl.style.left = (flood.cx - r).toFixed(1) + 'px'; fl.style.top = (flood.cy - r).toFixed(1) + 'px';
        fl.style.background = flood.color || darkest();
      } else fl.style.visibility = 'hidden';
    }
  }
  // whip: 옮기는 동안만 가로 방향 흐림 (SVG 필터 하나를 같이 씀, t 의 함수)
  function whipTick(t) {
    const list = overlayTr.filter(o => o.kind === 'whip');
    if (!list.length) return;
    let f = $('#fx-whip-f');
    if (!f) { document.body.appendChild(h('<svg width="0" height="0" style="position:absolute" aria-hidden="true"><filter id="fx-whip-f" x="-20%" y="0" width="140%" height="100%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="0 0"/></filter></svg>')); f = $('#fx-whip-f'); }
    const g = f.querySelector('feGaussianBlur'), u = Math.min(F.w, F.h) / 100;
    let amt = 0, act = null;
    for (const o of list) { const k = (t - (o.B - o.d / 2)) / o.d; if (k > 0 && k < 1) { amt = Math.sin(Math.PI * k); act = o; } }
    for (const o of list) for (const el of o.els) if (el.style.filter && el.style.filter.includes('fx-whip-f') && o !== act) el.style.filter = '';
    if (act) { g.setAttribute('stdDeviation', `${(amt * 6 * u).toFixed(1)} 0`); for (const el of act.els) el.style.filter = 'url(#fx-whip-f)'; }
  }
  // blocks: 칸마다 정해진(시드) 시각에 켜졌다 꺼짐
  function blocksTick(t) {
    const list = overlayTr.filter(o => o.kind === 'blocks');
    if (!list.length) return;
    let box = $('#fx-blocks');
    const o = list.find(x => t >= x.B - x.cover && t < x.B + x.open);
    if (!o) { if (box) box.style.visibility = 'hidden'; return; }
    const cols = o.n, sz = F.w / cols, rows = Math.ceil(F.h / sz);
    if (!box || box._n !== cols) {
      if (box) box.remove();
      box = h('<div id="fx-blocks"></div>'); box._n = cols; ($('#cam') || $('#stage')).appendChild(box);
      const r = S.M ? S.M.rng(7) : Math.random;
      box._cells = [];
      for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) {
        const c = document.createElement('i'); Object.assign(c.style, { left: x * sz + 'px', top: y * sz + 'px', width: Math.ceil(sz) + 1 + 'px', height: Math.ceil(sz) + 1 + 'px' });
        box.appendChild(c); box._cells.push([c, r(), r()]);
      }
    }
    box.style.visibility = 'inherit';
    const col = o.color || darkest();
    for (const [c, a, b] of box._cells) {
      const on = t >= o.B - o.cover + a * o.cover * .85 && t < o.B + b * o.open * .9;
      c.style.visibility = on ? 'inherit' : 'hidden'; c.style.background = col;
    }
  }
  function cssVar(n) { return getComputedStyle(root).getPropertyValue(n).trim(); }
  // 브랜드 색 중 가장 어두운 색 (조리개·플러드용). 둘 다 밝으면 거의 검정
  function darkest() {
    if (darkest.v) return darkest.v;
    const lum = c => { const m = /^#?([0-9a-f]{6})$/i.exec(c || ''); if (!m) return 1; const n = parseInt(m[1], 16); return (.299 * (n >> 16 & 255) + .587 * (n >> 8 & 255) + .114 * (n & 255)) / 255; };
    const c = [cssVar('--bg'), cssVar('--ink'), cssVar('--on-bg')].filter(Boolean).sort((a, b) => lum(a) - lum(b))[0];
    return (darkest.v = c && lum(c) < .25 ? c : '#121214');
  }
  S.cssVar = cssVar;

  /* ---------- overlays ---------- */
  function ensureOverlays() {
    const cam = $('#cam') || $('#stage');
    if (!$('#fx-wipe')) { cam.appendChild(h('<div id="fx-wipe"><i></i><i></i><i></i></div>')); gsap.set('#fx-wipe i', { xPercent: -130, skewX: -14, visibility: 'visible' }); }
    if (!$('#fx-ring')) cam.appendChild(h('<div id="fx-ring"></div>'));
    if (!$('#fx-iris')) { const sv = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); sv.id = 'fx-iris'; sv.setAttribute('viewBox', `0 0 ${F.w} ${F.h}`); cam.appendChild(sv); }
    if (!$('#fx-flood')) cam.appendChild(h('<div id="fx-flood"></div>'));
    if (content.progress !== false && !$('#fx-prog')) cam.appendChild(h('<div id="fx-prog"></div>'));
    if (window.__SAFE || location.hash === '#safe') {
      cam.appendChild(h(`<div id="fx-safe"><b style="top:0;height:${safe.top}px;left:0;right:0"></b><b style="bottom:0;height:${safe.bottom}px;left:0;right:0"></b><b style="top:0;bottom:0;left:0;width:${safe.left}px"></b><b style="top:0;bottom:0;right:0;width:${safe.right}px"></b><span>${esc(F.label)} · ${esc(typeof safeName === 'string' ? safeName : 'custom')} safe zone</span></div>`));
    }
  }

  /* ---------- 룩: 스타일이 정한 질감 ----------
     window.__LOOK = { paper, paperTone, fiber, grain, grainFps, halftone, dither, scanlines, vignette, tint, tintMode, boil: {amount, fps, scale} }
     (styles/<스타일>/style.json 의 look 이나 video.json 의 look 에서 build.py 가 넣음)
     모두 t 의 순수 함수: 그레인·선 떨림은 초당 fps 장씩 바뀌는 프레임 번호로 고정된 무늬를 고름 */
  const LOOK = window.__LOOK || null;
  S.look = LOOK;
  S.style = window.__STYLE || null;
  const seeded = seed => { let a = (seed >>> 0) || 1; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; };
  const svgURL = s => `url("data:image/svg+xml;charset=utf-8,${encodeURIComponent(s)}")`;
  function noiseURL(size, seed, contrast = 1) {
    const c = document.createElement('canvas'); c.width = c.height = size;
    const g = c.getContext('2d'), im = g.createImageData(size, size), r = seeded(seed);
    for (let i = 0; i < size * size; i++) { const v = 128 + (r() - .5) * 255 * contrast; im.data[i * 4] = im.data[i * 4 + 1] = im.data[i * 4 + 2] = v; im.data[i * 4 + 3] = 255; }
    g.putImageData(im, 0, 0); return `url(${c.toDataURL('image/png')})`;
  }
  function bayerURL() {   // 4×4 순서 디더 무늬
    const B = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5], c = document.createElement('canvas'); c.width = c.height = 4;
    const g = c.getContext('2d'), im = g.createImageData(4, 4);
    B.forEach((b, i) => { const v = Math.round(b / 15 * 255); im.data[i * 4] = im.data[i * 4 + 1] = im.data[i * 4 + 2] = v; im.data[i * 4 + 3] = 255; });
    g.putImageData(im, 0, 0); return `url(${c.toDataURL('image/png')})`;
  }
  function applyLook() {
    if (!LOOK || $('#fx-look')) return;
    const stage = $('#stage'), cam = $('#cam'), u = Math.min(F.w, F.h) / 100, k = x => x == null ? 0 : x === true ? 1 : +x;
    const L = h('<div id="fx-look"></div>'); stage.appendChild(L);
    const add = (css) => { const d = document.createElement('i'); Object.assign(d.style, css); L.appendChild(d); return d; };
    const ticks = [];
    if (LOOK.tint) add({ backgroundColor: LOOK.tint, mixBlendMode: LOOK.tintMode || 'soft-light', opacity: k(LOOK.tintAmount ?? .35) });
    if (LOOK.paper) {
      const tone = { warm: '#efe3c8', cream: '#f4ecd8', cool: '#e2e8ec', white: '#f7f6f2', kraft: '#d6bc93', gray: '#e4e2dd' }[LOOK.paper] || LOOK.paper;
      add({ backgroundColor: tone, mixBlendMode: 'multiply', opacity: k(LOOK.paperTone ?? .55) });
      // 종이 섬유: 프랙털 노이즈 (한 번만 그려 두고 고정)
      add({ backgroundImage: svgURL(`<svg xmlns="http://www.w3.org/2000/svg" width="640" height="640"><filter id="f" x="0" y="0"><feTurbulence type="fractalNoise" baseFrequency=".8" numOctaves="4" seed="11" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="table" tableValues="0 .55"/></feComponentTransfer></filter><rect width="100%" height="100%" filter="url(#f)"/></svg>`),
        backgroundSize: `${64 * u}px ${64 * u}px`, mixBlendMode: 'multiply', opacity: k(LOOK.fiber ?? .45) });
    }
    if (LOOK.halftone) {
      const s = (+LOOK.halftoneSize || 1.2) * u;
      add({ backgroundImage: 'radial-gradient(circle, rgba(0,0,0,.55) 0 34%, transparent 36%)', backgroundSize: `${s}px ${s}px`, mixBlendMode: 'multiply', opacity: k(LOOK.halftone) });
    }
    if (LOOK.dither) add({ backgroundImage: bayerURL(), backgroundSize: `${(+LOOK.ditherSize || .8) * u}px ${(+LOOK.ditherSize || .8) * u}px`, imageRendering: 'pixelated', mixBlendMode: 'overlay', opacity: k(LOOK.dither) });
    if (LOOK.scanlines) add({ backgroundImage: `repeating-linear-gradient(0deg, rgba(0,0,0,.5) 0 ${.18 * u}px, transparent ${.18 * u}px ${.5 * u}px)`, mixBlendMode: 'multiply', opacity: k(LOOK.scanlines) });
    if (LOOK.vignette) add({ background: 'radial-gradient(ellipse at 50% 50%, transparent 52%, rgba(0,0,0,.65) 100%)', opacity: k(LOOK.vignette) });
    if (LOOK.grain) {
      const g = add({ backgroundImage: noiseURL(256, 5, 1), backgroundSize: `${Math.round(2.4 * u * 10)}px`, mixBlendMode: 'overlay', opacity: k(LOOK.grain), inset: '-10%' });
      const fps = +LOOK.grainFps || 12;
      ticks.push(t => { const r = seeded(1 + Math.floor(t * fps)); g.style.transform = `translate(${(r() * 8 - 4).toFixed(2)}%, ${(r() * 8 - 4).toFixed(2)}%)`; });
    }
    if (LOOK.frame) {   // 둘레 액자 (가운데만 둥글게 뚫림)
      const fr = typeof LOOK.frame === 'object' ? LOOK.frame : { width: +LOOK.frame };
      const w = (+fr.width || 2.4) * u;
      add({ inset: w + 'px', borderRadius: (+fr.radius || 2) * u + 'px', boxShadow: `0 0 0 ${Math.max(F.w, F.h)}px ${fr.color || 'var(--paper)'}` });
    }
    const boil = LOOK.boil ? (typeof LOOK.boil === 'object' ? LOOK.boil : { amount: +LOOK.boil }) : null;
    const rgb = LOOK.rgbSplit ? (typeof LOOK.rgbSplit === 'object' ? LOOK.rgbSplit : { amount: +LOOK.rgbSplit }) : null;
    if ((boil || rgb) && cam) {
      // 손그림 선 떨림(boil, 초당 fps 번 무늬가 바뀜)과 RGB 어긋남(rgbSplit)을 필터 하나로
      const src = boil ? 'b' : 'SourceGraphic', sh = rgb ? (+rgb.amount || 1) * .3 * u : 0;
      const ch = (m, dx, name) => `<feColorMatrix in="${src}" type="matrix" values="${m}" result="${name}c"/><feOffset in="${name}c" dx="${dx}" dy="0" result="${name}"/>`;
      const svg = h(`<svg id="fx-look-defs" width="0" height="0" style="position:absolute" aria-hidden="true"><filter id="fx-look-f" x="-2%" y="-2%" width="104%" height="104%" color-interpolation-filters="sRGB">
        ${boil ? `<feTurbulence type="turbulence" baseFrequency="${boil.scale || .018}" numOctaves="2" seed="1" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="${((+boil.amount || 1) * .35 * u).toFixed(2)}" xChannelSelector="R" yChannelSelector="G" result="b"/>` : ''}
        ${rgb ? ch('1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0', sh.toFixed(1), 'r') + ch('0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0', 0, 'g') + ch('0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0', (-sh).toFixed(1), 'bl')
          + '<feBlend in="r" in2="g" mode="screen" result="rg"/><feBlend in="rg" in2="bl" mode="screen"/>' : ''}
      </filter></svg>`);
      document.body.appendChild(svg);
      cam.style.filter = 'url(#fx-look-f)';
      if (boil) {
        const turb = svg.querySelector('feTurbulence'), fps = +boil.fps || 8;
        let last = -1;
        ticks.push(t => { const f = 1 + (Math.floor(t * fps) % 6); if (f !== last) { turb.setAttribute('seed', f); last = f; } });
      }
      if (rgb && rgb.jitter) {   // 어긋남 폭이 프레임마다 조금씩 바뀜 (홀로그램·글리치)
        const offs = [...svg.querySelectorAll('feOffset')], fps = +rgb.fps || 12;
        ticks.push(t => { const r = seeded(3 + Math.floor(t * fps)), j = sh * (1 + (r() - .5) * 2 * rgb.jitter); offs[0].setAttribute('dx', j.toFixed(1)); offs[2].setAttribute('dx', (-j).toFixed(1)); });
      }
    }
    if (ticks.length) S.ambient(t => ticks.forEach(fn => fn(t)));
  }

  /* ---------- player (렌더 모드가 아닐 때만) ---------- */
  function player() {
    const ui = h(`<div id="ui">
      <button id="cover" type="button" aria-label="재생"><span class="pb"><svg viewBox="0 0 24 24"><path d="M7 4v16l13-8z"/></svg><span id="coverLabel">재생</span></span></button>
      <div id="bar">
        <button id="pp" type="button" aria-label="재생"><svg viewBox="0 0 24 24"><path id="ppIcon" d="M7 4v16l13-8z"/></svg></button>
        <input id="seek" type="range" min="0" max="${Math.round(S.dur * 10)}" step="1" value="0" aria-label="재생 위치">
        <span id="time"></span>
        <button id="safeBtn" type="button" aria-label="세이프존 보기" title="세이프존"><svg viewBox="0 0 24 24"><path d="M3 3h18v18H3zm3 3v12h12V6z"/></svg></button>
        <button id="fs" type="button" aria-label="전체 화면"><svg viewBox="0 0 24 24"><path d="M4 4h6v2H6v4H4zm10 0h6v6h-2V6h-4zM4 14h2v4h4v2H4zm14 0h2v6h-6v-2h4z"/></svg></button>
      </div></div>`);
    document.body.appendChild(ui);
    const cover = $('#cover'), bar = $('#bar'), seek = $('#seek'), time = $('#time'), ppIcon = $('#ppIcon');
    const PLAY = 'M7 4v16l13-8z', PAUSE = 'M6 4h4v16H6zm8 0h4v16h-4z';
    const fmt = s => { s = Math.max(0, Math.floor(s)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
    let scrub = false, was = false, idle;
    const K = S.stretch || 1;
    const sync = () => { const t = tl.time(); if (!scrub) seek.value = Math.round(t * 10); time.textContent = fmt(t * K) + ' / ' + fmt(S.dur * K); ppIcon.setAttribute('d', tl.paused() ? PLAY : PAUSE); };
    const show = () => { bar.classList.remove('idle'); document.body.classList.remove('hide-cursor'); clearTimeout(idle); idle = setTimeout(() => { if (!tl.paused() && !scrub) { bar.classList.add('idle'); document.body.classList.add('hide-cursor'); } }, 2200); };
    const play = () => { cover.hidden = true; if (tl.time() >= S.dur - .01) tl.time(0); tl.play(); show(); sync(); };
    const toggle = () => tl.paused() ? play() : (tl.pause(), show(), sync());
    const jump = d => { tl.time(Math.max(0, Math.min(S.dur, tl.time() + d / K))); S.tick(tl.time()); show(); sync(); };
    tl.eventCallback('onUpdate', () => {
      let t = tl.time();
      if (S.q(t) !== t && t < S.dur - 1e-3) { t = S.q(t); tl.render(t, true, true); }   // 재생 중에도 끊어서 그림 (재생 위치는 그대로 흐름)
      S.tick(t); sync();
    });
    tl.eventCallback('onComplete', () => { $('#coverLabel').textContent = '다시 보기'; cover.hidden = false; show(); sync(); });
    cover.onclick = () => { tl.time(0); play(); };
    $('#pp').onclick = toggle;
    $('#fs').onclick = () => { try { document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen().catch(() => {}); } catch (e) {} };
    $('#safeBtn').onclick = () => { const s = $('#fx-safe'); if (s) s.remove(); else { window.__SAFE = true; ensureOverlays(); } };
    seek.oninput = () => { if (!scrub) { scrub = true; was = !tl.paused(); tl.pause(); } cover.hidden = true; const t = seek.value / 10; tl.time(t); S.tick(t); time.textContent = fmt(t * K) + ' / ' + fmt(S.dur * K); };
    seek.onchange = () => { scrub = false; if (was) tl.play(); show(); sync(); };
    addEventListener('mousemove', show);
    addEventListener('keydown', e => {
      if (e.target === seek && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) return;
      if ((e.key === ' ' || e.key === 'Enter') && e.target.closest && e.target.closest('button')) return;
      if (e.key === ' ' || e.key === 'k' || e.key === 'Enter') { e.preventDefault(); cover.hidden ? toggle() : (tl.time(0), play()); }
      else if (e.key === 'ArrowRight' || e.key === 'PageDown') { e.preventDefault(); cover.hidden = true; jump(2); }
      else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { e.preventDefault(); cover.hidden = true; jump(-2); }
      else if (e.key === 'f' || e.key === 'F5') { e.preventDefault(); $('#fs').click(); }
    });
    const poster = Math.min(S.dur, content.poster ?? S.dur * .25);
    tl.time(poster); S.tick(poster); sync(); show();
  }

  /* ---------- 발표 자료 플레이어 (템플릿이 S.stops 를 정하면 영상 플레이어 대신) ----------
     장마다 등장이 끝나는 시각(S.stops)에서 멈추고, 넘기면 다음 장의 전환과 등장을 끝까지 재생해요.
     클리커: PageDown·PageUp·방향키·스페이스·Enter, F5·Shift+F5 전체 화면, B·. 검은 화면, W·, 흰 화면, 숫자+Enter 장 이동, Home·End.
     전환 중에 누른 키는 버리지 않고 차례로 처리하고(밀리면 조금 빨리), 커서와 막대는 가만히 있으면 숨어요. */
  function deckPlayer() {
    const stops = S.stops, enter = S.stopEnter || stops.map((_, i) => i ? stops[i - 1] : 0), n = stops.length;
    const ui = h(`<div id="ui" class="deck">
      <div id="dk-blank" hidden></div>
      <div id="dk-goto" hidden></div>
      <div id="bar" class="dk-bar">
        <button id="dk-prev" type="button" aria-label="이전 장"><svg viewBox="0 0 24 24"><path d="M15.4 7.4 14 6l-6 6 6 6 1.4-1.4L10.8 12z"/></svg></button>
        <span id="dk-no"></span>
        <button id="dk-next" type="button" aria-label="다음 장"><svg viewBox="0 0 24 24"><path d="M8.6 16.6 10 18l6-6-6-6-1.4 1.4 4.6 4.6z"/></svg></button>
        <span class="dk-help">→ 다음 · ← 이전 · 숫자+Enter 이동 · B 검은 화면 · F5 전체 화면</span>
        <button id="fs" type="button" aria-label="전체 화면"><svg viewBox="0 0 24 24"><path d="M4 4h6v2H6v4H4zm10 0h6v6h-2V6h-4zM4 14h2v4h4v2H4zm14 0h2v6h-6v-2h4z"/></svg></button>
      </div></div>`);
    document.body.appendChild(ui);
    const bar = $('#bar'), no = $('#dk-no'), blankEl = $('#dk-blank'), gotoEl = $('#dk-goto');
    let cur = -1, anim = null, queue = [], digits = '', digitTimer, idleTimer;
    const t0 = performance.now();
    const render = t => { const ti = S.q(t); tl.time(ti, false); S.tick(ti); };
    const label = () => { no.textContent = `${Math.max(1, cur + 1)} / ${n}`; };
    const mark = () => { try { history.replaceState(null, '', '#' + (cur + 1)); } catch (e) { /* file:// 에서 막히면 그냥 둠 */ } };
    const done = () => {
      anim = null; label(); mark();
      if (queue.length) run(queue.shift());
    };
    function play(i) {   // i 장의 전환+등장을 재생
      const from = i === cur + 1 ? (i ? stops[i - 1] : 0) : enter[i];
      cur = i; label();
      const st = { t: from }, speed = 1 + Math.min(queue.length, 3) * .9;
      render(from);
      anim = gsap.to(st, { t: stops[i], duration: Math.max(.01, stops[i] - from), ease: 'none', onUpdate: () => render(st.t), onComplete: done });
      anim.timeScale(speed);
    }
    function jump(i) { cur = i; render(stops[i]); label(); mark(); }
    function run(cmd) {
      if (cmd === 'next') { if (cur < n - 1) play(cur + 1); else done(); }
      else if (cmd === 'prev') { if (cur > 0) jump(cur - 1); done(); }
      else if (cmd === 'home') { if (cur !== 0) play(0); else done(); }
      else if (cmd === 'end') { jump(n - 1); done(); }
      else if (typeof cmd === 'number') { const i = Math.max(0, Math.min(n - 1, cmd)); if (i === cur) done(); else if (i === cur + 1) play(i); else if (i < cur) { jump(i); done(); } else play(i); }
    }
    const send = cmd => { if (anim) { queue.push(cmd); if (anim.timeScale() < 2.5) anim.timeScale(2.5); } else run(cmd); };
    const setBlank = c => { if (!c || blankEl.dataset.c === c) { blankEl.hidden = true; blankEl.dataset.c = ''; } else { blankEl.hidden = false; blankEl.dataset.c = c; blankEl.style.background = c === 'w' ? '#fff' : '#000'; } };
    const fs = () => { try { document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen().catch(() => {}); } catch (e) { /* 막힌 창이면 그냥 둠 */ } };
    const showUI = () => { bar.classList.remove('idle'); document.body.classList.remove('hide-cursor'); clearTimeout(idleTimer); idleTimer = setTimeout(() => { bar.classList.add('idle'); document.body.classList.add('hide-cursor'); }, 1800); };
    const showDigits = () => { gotoEl.hidden = !digits; gotoEl.textContent = digits ? `${digits}장으로 · Enter` : ''; clearTimeout(digitTimer); if (digits) digitTimer = setTimeout(() => { digits = ''; showDigits(); }, 3500); };
    addEventListener('keydown', e => {
      if (e.ctrlKey || e.altKey || e.metaKey) return;
      const k = e.key;
      if (k === 'F5' || (k === 'f' || k === 'F')) { e.preventDefault(); fs(); return; }
      if (k === 'b' || k === 'B' || k === '.') { e.preventDefault(); setBlank('b'); return; }
      if (k === 'w' || k === 'W' || k === ',') { e.preventDefault(); setBlank('w'); return; }
      if (!blankEl.hidden && k !== 'Shift') { e.preventDefault(); setBlank(null); return; }   // 가린 화면에서는 먼저 걷기만
      if (/^[0-9]$/.test(k)) { digits = (digits + k).slice(-3); showDigits(); return; }
      if (k === 'Backspace' && digits) { digits = digits.slice(0, -1); showDigits(); return; }
      if (k === 'Escape') { if (digits) { digits = ''; showDigits(); } return; }
      if (k === 'Enter' && digits) { e.preventDefault(); const i = parseInt(digits, 10) - 1; digits = ''; showDigits(); send(i); return; }
      if (e.target && e.target.closest && e.target.closest('button') && (k === ' ' || k === 'Enter')) return;
      if (['PageDown', 'ArrowRight', 'ArrowDown', ' ', 'Enter', 'n', 'N'].includes(k)) { e.preventDefault(); send('next'); }
      else if (['PageUp', 'ArrowLeft', 'ArrowUp', 'Backspace', 'p', 'P'].includes(k)) { e.preventDefault(); send('prev'); }
      else if (k === 'Home') { e.preventDefault(); send('home'); }
      else if (k === 'End') { e.preventDefault(); send('end'); }
    });
    $('#viewport').addEventListener('click', () => { if (!blankEl.hidden) return setBlank(null); send('next'); });
    blankEl.addEventListener('click', () => setBlank(null));
    $('#viewport').addEventListener('contextmenu', e => { e.preventDefault(); send('prev'); });
    $('#dk-prev').onclick = () => send('prev');
    $('#dk-next').onclick = () => send('next');
    $('#fs').onclick = fs;
    addEventListener('mousemove', showUI);
    // 멈춘 장에서도 배경이 숨 쉬듯 (재생 시각과 따로, 화면을 연 뒤 흐른 시간)
    const loop = () => { S.idleT = (performance.now() - t0) / 1000; if (!anim) for (const fn of idles) fn(S.idleT); requestAnimationFrame(loop); };
    S.idleT = 0; requestAnimationFrame(loop);
    const want = parseInt((location.hash || '').slice(1), 10);
    render(0); showUI();
    if (want > 1 && want <= n) { jump(want - 2); send(want - 1); }
    else send(0);
  }

  /* ---------- 시작 ---------- */
  S.start = async function (compose) {
    fitStage();
    try { await document.fonts.ready; } catch (e) {}
    await Promise.all($$('img').map(i => (i.decode ? i.decode().catch(() => {}) : 0)));
    ensureOverlays();
    applyLook();
    await compose(S);
    if (!S.dur) S.dur = tl.duration();
    tl.to({}, { duration: S.dur }, 0);
    // 길이 늘이기·줄이기 (content.stretch): 장면 시간표는 그대로 두고 전체 속도만 바꿈. 바깥(재생·렌더) 시간 = 안쪽 시간 × k
    // 박자에 맞춘 필름(content.bpm 이 있는 키노트·UI 모프·쇼릴)은 늘이면 음악과 어긋나서 무시
    const k = content.bpm || S.stops ? 1 : Math.min(1.8, Math.max(.6, +content.stretch || 1));
    S.stretch = k;
    if (k !== 1) tl.timeScale(1 / k);
    const prog = $('#fx-prog');
    if (prog) S.ambient(t => { prog.style.transform = `scaleX(${Math.min(1, t / S.dur).toFixed(4)})`; });
    window.__DURATION = S.dur * k;
    window.__BASE_DURATION = S.dur;
    // 스톱모션처럼 끊어 보이기 (스타일 motion.stepped = 초당 장 수, 예: 손그림 8~12). 렌더·미리보기 모두 같은 장으로
    const step = Math.max(0, +((S.style && S.style.motion && S.style.motion.stepped) || 0));
    S.q = step ? (t => Math.floor(t * step + 1e-6) / step) : (t => t);
    window.__seek = t => { const ti = S.q(t / k); tl.time(ti, false); S.tick(ti); };
    if (S.stops) { window.__STOPS = S.stops.slice(); window.__SLIDES = S.stops.length; }   // 발표 자료: 장마다 등장이 끝나는 시각 (PDF·장 모음)
    window.__ready = true;
    if (window.__RENDER) { document.body.classList.add('render'); window.__seek(0); return; }
    if (S.stops && S.stops.length) return deckPlayer();
    player();
  };
})();
