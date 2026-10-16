/* 모션 스튜디오 앱 화면 */
'use strict';

/* ---------------------------------------------------------------- 도구 */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const clone = o => JSON.parse(JSON.stringify(o));
const debounce = (fn, ms) => {
  let t, pending = false, last = [];
  const d = (...a) => { last = a; pending = true; clearTimeout(t); t = setTimeout(() => { pending = false; fn(...last); }, ms); };
  d.flush = () => { if (!pending) return Promise.resolve(); clearTimeout(t); pending = false; return fn(...last); };  // 기다리던 것만 바로 실행
  d.now = (...a) => { clearTimeout(t); pending = false; return fn(...a); };                                              // 무조건 바로 실행
  d.cancel = () => { clearTimeout(t); pending = false; };
  return d;
};

const FMT = {
  tall: { label: '9:16', name: '릴스·쇼츠', w: 1080, h: 1920 },
  portrait: { label: '4:5', name: '피드', w: 1080, h: 1350 },
  square: { label: '1:1', name: '피드', w: 1080, h: 1080 },
  wide: { label: '16:9', name: '유튜브', w: 1920, h: 1080 },
};
const FMT_KEYS = Object.keys(FMT);
const LIMITS = { 'hook.headline': 24, 'hook.kicker': 14, 'visuals.title': 18, 'visuals.sub': 22, 'benefits.title': 14, 'benefits.items': 18,
  'proof.label': 24, 'cta.headline': 22, 'cta.button': 10, 'cta.sub': 30, 'beats.text': 22, 'beats.kicker': 12, 'beats.sub': 24, 'beats.items': 16,
  'upload.title': 100 };
const TRANS = { '': '기본', push: '밀어내기', wipe: '색 막대', zoom: '확대', iris: '원형', blades: '조리개', flood: '검은 물결', fade: '서서히', cut: '바로 바뀜' };
const TEMPLATE_INFO = {
  promo: { name: '사진형', desc: '첫 문장 → 사진 장면 → 장점 → 숫자 → 행동 유도' },
  kinetic: { name: '글자형', desc: '사진 없이 짧은 문장으로. 세일·이벤트·공지' },
  keynote: { name: '키노트 필름', desc: '1:1 한 컷 필름. 워드마크 → 사진 격자 → 유리·폰·맥 → 주문 상태 → 다시 워드마크 (런칭 27초 / 채널 20초 루프)', film: true },
  uimorph: { name: 'UI 모프', desc: '1:1 도형 하나가 버튼·플레이어·토글·차트·검색창으로 변하는 14초 루프', film: true },
  showreel: { name: '쇼릴', desc: '1:1 15초 쇼릴. 글자·도형·사진·UI·숫자·비율 프레임을 박자에 맞춰', film: true },
  menu: { name: '신메뉴 쇼케이스', desc: '둥근 접시 위 메뉴 사진, 돌아가는 둘레 글자, 스티커 태그, 매달린 가격표', auto: true },
  sale: { name: '세일 가격표', desc: '흐르는 띠, 슬롯처럼 꽂히는 할인율, 줄이 그어지는 가격표', auto: true },
  opening: { name: '매장 오픈', desc: '셔터가 올라가고 간판이 OPEN으로, 지도 핀, 영수증 혜택', auto: true },
  greeting: { name: '시즌 인사 카드', desc: '선으로 그려지는 계절 그림, 봉투 속 카드, 펜으로 쓰는 인사말', auto: true },
  academy: { name: '수강생 모집 노트', desc: '모눈 노트를 넘기며 시간표·커리큘럼·남은 자리, 포스트잇', auto: true },
  event: { name: '행사 티켓', desc: '티켓에 일시·장소가 찍히고 뒤집어 프로그램, 디데이 도장, 찢어서 신청', auto: true },
  hiring: { name: '채용 메신저', desc: '화면 전체가 메신저 대화, 채용 카드 말풍선, 지원 시트', auto: true },
  notice: { name: '공지 안내판', desc: '공항 출발 안내판처럼 글자판이 차르륵 넘어가는 공지', auto: true },
  travel: { name: '여행 지도', desc: '종이 지도 위 점선 길, 핀과 폴라로이드, 마지막엔 사진 부채꼴', auto: true },
  stats: { name: '성과 대시보드', desc: '카드를 하나씩 확대하며 숫자가 굴러 맞춰지고 그래프가 그려짐', auto: true },
  company: { name: '회사 소개 (설계도)', desc: '설계도 격자 위에 회사 이름이 선으로 그려지고, 하는 일 블록·숫자·함께하는 곳을 지나 명함이 뒤집히며 연락처', auto: true },
  product: { name: '제품·서비스 소개', desc: '엉킨 선이 펴져 제품 창이 되고, 기능 카드·단계 점·문의 버튼까지 선 하나로 이어짐', auto: true },
  timeline: { name: '연혁 (연도 자)', desc: '긴 줄자 위로 연도가 주행거리계처럼 굴러 이정표마다 멈추고, 카드가 자에서 펼쳐짐', auto: true },
  news: { name: '소식 발표 (뉴스)', desc: '뉴스 속보 화면처럼 띠가 쓸고 지나가고 자막 바·티커, 협약·투자·수상·인증·출시마다 다른 소품', auto: true },
  deck: { name: '발표 자료', desc: '넘길 때마다 한 장씩 모션으로 등장하는 16:9 발표 자료' },
  scenes: { name: '장면 쌓기', desc: '표지·문장·사진·숫자·목록·단계·비교·인용·그래프·사진 여러 장·로고 장면을 원하는 순서로 쌓아요' },
  // 결 템플릿 10개: 모두 같은 content(이야기)를 읽어서 문구는 그대로 두고 템플릿만 바꿀 수 있어요
  typeslam: { name: '타이포 쇼', desc: '화면을 꽉 채운 큰 글자가 박마다 잘린 채 부딪히고, 반대로 흐르는 글자 띠·떨어져 쌓이는 글자·거대 숫자, 색 반전으로 끝', auto: true, look: '타이포' },
  uidemo: { name: '제품 화면 시연', desc: '앱 창·폰 화면에서 커서가 타자 치고 누르며 카메라가 다가가요. 입력창의 한 줄이 체크 목록이 되고, 대시보드 숫자와 갤러리를 지나 큰 버튼을 누르며 끝나요', auto: true, look: '제품 UI' },
  sketchbook: { name: '손그림 노트', desc: '스프링 노트에 손글씨 제목·한 획 동그라미, 체크리스트, 손 타원 속 숫자, 폴라로이드, 도장 찍힌 마지막 장. 한 장씩 위로 넘어가요', auto: true, look: '손그림' },
  dataflow: { name: '데이터 흐름', desc: '점 하나에서 선이 뻗어 항목마다 노드가 생기고 신호 점이 달리는 선을 카메라가 따라가요. 선들이 모여 원형 게이지 숫자, 끝 노드가 버튼이 되며 전체 지도로 물러나요', auto: true, look: '다이어그램·데이터' },
  terminal: { name: '레트로 터미널', desc: '터미널 창에서 첫 문장이 타자로 쳐지고, 진행 막대와 ✓ 줄, 점 전광판 숫자, 디더링 사진 창, 깜빡이는 프롬프트 버튼', auto: true, look: '레트로·픽셀' },
  collage: { name: '종이 콜라주', desc: '찢긴 종이판이 장면마다 덮이고 스티커 꼬리표·색 종이 띠 제목·테이프 쪽지·톱니 스티커 숫자·리소 톤 사진이 박마다 붙어요', auto: true, look: '콜라주·사진' },
  stage: { name: '사물 무대', desc: '촬영 무대 위로 로고 동전이 돌며 떠오르고, 장점은 궤도를 도는 비눗방울에, 숫자는 동전 앞면에, 마지막엔 소품이 뒤로 모이며 유리 버튼', auto: true, look: '3D·사물' },
  glow: { name: '빛과 그라디언트', desc: '숨 쉬는 빛 구슬이 열려 흐린 오로라가 되고, 유리 알약·빛 고리 숫자·둥근 빛 창 사진을 지나 빛이 도는 버튼으로', auto: true, look: '그라디언트·빛' },
  brandmark: { name: '도형으로 짜는 브랜드', desc: '격자 위 도형이 선택 핸들을 달고 모양을 바꾸며 마크가 되고, 박마다 색면이 갈리다 로고 락업으로 끝나요', auto: true, look: '그래픽·도형' },
  cinema: { name: '시네마틱', desc: '레터박스 속 천천히 다가오는 사진, 장 번호 자막, 빛 번짐, 초공간 빛줄기 속 숫자, 빛을 받는 로고', auto: true, look: '시네마틱' },
};
const LOOK_TPLS = Object.keys(TEMPLATE_INFO).filter(k => TEMPLATE_INFO[k].look);
// 템플릿마다 따로 쓰는 권장 글자 수 (tools/check.py 의 LIMITS_BY_TPL 과 같게)
const LIMITS_TPL = {
  scenes: { 'scenes.kicker': 14, 'scenes.text': 40, 'scenes.sub': 30, 'scenes.items': 18, 'scenes.left': 24, 'scenes.right': 24, 'scenes.leftLabel': 8, 'scenes.rightLabel': 8, 'scenes.by': 14, 'scenes.role': 20, note: 40 },
  company: { label: 24, name: 16, mission: 40, highlight: 12, pillarsTitle: 14, 'pillars.title': 12, 'pillars.desc': 22, factsTitle: 14, 'facts.label': 12, 'facts.unit': 3, source: 40, partnersTitle: 14, partners: 10, 'card.slogan': 20, 'card.address': 36, note: 30 },
  product: { 'problem.title': 22, 'problem.pains': 12, 'product.name': 12, 'product.tagline': 26, 'features.title': 10, 'features.desc': 20, 'flow.title': 14, 'flow.steps': 8, 'result.label': 22, 'result.source': 40 },
  timeline: { 'milestones.title': 12, 'milestones.text': 22, 'now.title': 22, 'now.sub': 26, badgeUnit: 6 },
  news: { 'partner.name': 14, 'partner.deal': 24, 'amount.round': 10, 'award.name': 22, 'launch.name': 14, 'launch.sub': 30, 'quote.text': 50, ticker: 25, plan: 30, topic: 8, facts: 18 },
};
const STORY_LIMITS = { kicker: 14, title: 30, highlight: 12, points: 18, 'number.prefix': 6, 'number.suffix': 6, 'number.label': 22, 'number.source': 40, 'cta.headline': 24, 'cta.button': 10, 'cta.sub': 30, note: 40 };
Object.keys(TEMPLATE_INFO).filter(k => TEMPLATE_INFO[k].look).forEach(k => { LIMITS_TPL[k] = STORY_LIMITS; });
const limitOf = key => ((LIMITS_TPL[(S.detail && S.detail.video.template) || ''] || {})[key]) || LIMITS[key];
const isAuto = tpl => !!(TEMPLATE_INFO[tpl] || {}).auto;
const isFilm = tpl => !!(TEMPLATE_INFO[tpl] || {}).film;

async function api(path, body) {
  const opt = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Studio': '1' }, body: JSON.stringify(body) };
  let r;
  try { r = await fetch(path, opt); }
  catch (e) { throw new Error('앱 서버에 연결하지 못했어요. 잠시 뒤 다시 해 보고, 계속되면 앱을 껐다 켜 주세요.'); }
  let data = {};
  try { data = await r.json(); } catch (e) { /* 빈 응답 */ }
  if (!r.ok || data.error) throw new Error(data.error || `요청 실패 (${r.status})`);
  return data;
}
async function upload(file) {
  if (file.size > 50 * 1024 * 1024) throw new Error(`파일이 너무 커요 (${Math.round(file.size / 1048576)}MB). 50MB 안쪽으로 줄여서 넣어 주세요.`);
  if (/\.(heic|heif|svg)$/i.test(file.name)) throw new Error('HEIC·SVG 파일은 쓸 수 없어요. JPG나 PNG로 바꿔서 넣어 주세요.');
  const r = await fetch('/api/upload?name=' + encodeURIComponent(file.name), { method: 'POST', headers: { 'X-Studio': '1' }, body: file });
  let data = {};
  try { data = await r.json(); } catch (e) { /* 빈 응답 */ }
  if (!r.ok || data.error) throw new Error(data.error || '파일을 올리지 못했습니다');
  return data;
}
function toast(msg, err) {
  const t = document.createElement('div');
  t.className = 'toast' + (err ? ' err' : '');
  t.textContent = msg;
  t.setAttribute('role', err ? 'alert' : 'status');
  document.body.appendChild(t);
  setTimeout(() => t.remove(), err ? 6000 : 3200);
}
const fail = e => { console.error(e); toast(e.message || String(e), true); };

function getPath(o, path) { return path.split('.').reduce((a, k) => (a == null ? undefined : a[k]), o); }
function setPath(o, path, val) {
  const ks = path.split('.');
  let cur = o;
  ks.slice(0, -1).forEach((k, i) => {
    if (cur[k] == null || typeof cur[k] !== 'object') cur[k] = /^\d+$/.test(ks[i + 1]) ? [] : {};
    cur = cur[k];
  });
  const last = ks[ks.length - 1];
  if (val === undefined) { if (Array.isArray(cur)) cur.splice(+last, 1); else delete cur[last]; } else cur[last] = val;
}
const ratioIcon = (f, cls = '') => `<i class="ratio ${f} ${cls}" aria-hidden="true"></i>`;
const lenOf = s => String(s || '').replace(/\n/g, '').length;

/* ---------------------------------------------------------------- 상태 */
const S = {
  state: null,        // /api/state
  sel: null,          // {type:'video'|'brand', id}
  detail: null,       // /api/video
  brand: null,        // brand.json (편집 중)
  tab: 'copy',
  fmt: 'tall',
  safe: false,
  previewUrl: {},
  jobs: {},
  jobDone: {},
  undo: null,
  pub: null,          // /api/publish (올리기 탭)
  pubAi: null,        // Claude 업로드 글 초안
};

/* ---------------------------------------------------------------- 시작 */
/* 앱 서버가 꺼졌을 때 (창을 오래 내려 두었거나 서버가 멈춤) */
function offlineScreen() {
  if ($('.boot-fail')) return;
  document.body.insertAdjacentHTML('beforeend', `<div class="boot-fail"><div class="bf-card">
    <h2>앱 서버와 연결이 끊겼어요</h2>
    <p>저장되지 않은 수정이 있다면 서버가 다시 켜진 뒤 한 번 더 해 주세요.</p>
    <ol><li>이 창을 닫고 바탕화면의 <b>모션 스튜디오</b>를 다시 눌러 주세요.</li>
      <li>자주 그러면 <b>문서\\motion-studio\\out\\_app\\app.log</b> 파일을 보내 주세요.</li></ol>
    <button class="btn solid" type="button" onclick="location.reload()">다시 연결</button></div></div>`);
}
function bootFail(e) {
  const msg = e && e.message ? e.message : String(e || '');
  document.body.insertAdjacentHTML('beforeend', `<div class="boot-fail"><div class="bf-card">
    <h2>앱 서버에 연결하지 못했어요</h2>
    <p>화면은 열렸는데 뒤에서 일하는 프로그램(파이썬)이 응답하지 않아요. <span class="hint">(${esc(msg)})</span></p>
    <ol>
      <li>이 창을 닫고 바탕화면의 <b>모션 스튜디오</b>를 다시 눌러 보세요.</li>
      <li>그래도 같으면 <b>문서\\motion-studio\\StudioApp_debug.cmd</b> 를 더블클릭해 보세요. 검은 창에 오류가 나오면 그 화면을 보내 주세요.</li>
      <li>기록 파일: <b>문서\\motion-studio\\out\\_app\\app.log</b></li>
    </ol>
    <button class="btn solid" type="button" onclick="location.reload()">다시 시도</button></div></div>`);
}
async function boot() {
  // 앱 서버가 막 켜지는 중이거나 잠깐 바쁠 수 있어 몇 번 다시 시도하고, 그래도 안 되면 안내 화면
  let lastErr = null;
  for (let i = 0; i < 6 && !S.state; i++) {
    try { S.state = await api('/api/state'); } catch (e) { lastErr = e; await new Promise(r => setTimeout(r, 1000 + i * 500)); }
  }
  if (!S.state) return bootFail(lastErr);
  syncHeader();
  renderRail();
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.get('v') && S.state.videos.some(v => v.name === h.get('v'))) await selectVideo(h.get('v'));
  else if (h.get('b') && S.state.brands.some(b => b.slug === h.get('b'))) await selectBrand(h.get('b'));
  else goHome();
  for (const j of S.state.jobs || []) if (j.status === 'running') trackJob(j);
  api('/api/update/notice').then(r => r.notice && showUpdateNotice(r.notice)).catch(() => {});
  const ping = () => fetch('/api/ping').then(r => { if (r.ok) S.offline = 0; }).catch(() => { if (++S.offline >= 3) offlineScreen(); });
  S.offline = 0;
  setInterval(ping, 5000);
  ping();
  document.addEventListener('visibilitychange', () => { if (!document.hidden) ping(); });
  addEventListener('focus', ping);
  addEventListener('pagehide', () => { try { navigator.sendBeacon('/api/bye', new Blob(['{}'], { type: 'application/json' })); } catch (e) { /* 무시 */ } });
  $('#openOut').onclick = () => api('/api/open', { path: S.sel && S.sel.type === 'video' ? `out/${S.sel.id}` : 'out' }).catch(fail);
  $('#openCC').onclick = () => isApi() ? dlgAgent(S.sel && S.sel.type === 'video' ? S.sel.id : null) : openClaudeCode({});
  $('#openAcct').onclick = () => dlgAccounts();
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); saveVideo.flush(); saveBrand.flush(); }
  });
  window.addEventListener('beforeunload', () => { saveVideo.flush(); saveBrand.flush(); });
}

function showUpdateNotice(n) {
  if (n.error) return toast('새 버전을 받다가 문제가 생겨서 지금 버전 그대로 켰어요.', true);
  const notes = (n.notes || []).map(t => `<li>${esc(t)}</li>`).join('');
  const kept = (n.kept || []).length ? `<p class="hint">이 PC에서 고친 파일 ${n.kept.length}개는 이번 버전에서 안 바뀌어서 그대로 뒀어요.</p>` : '';
  const edits = (n.local_edits || []).length ? `<p class="hint">이 PC에서 고친 파일 ${n.local_edits.length}개가 새 버전으로 바뀌었어요. 고쳤던 것은 사용자 폴더 .motion-studio\\update\\backup 에 있어요.</p>` : '';
  openDlg(`<div class="dlg-h"><h2>새 버전으로 업데이트했어요</h2><button class="icon-btn" data-close type="button" aria-label="닫기">×</button></div>
    <div class="dlg-b">${notes ? `<p>바뀐 점</p><ul>${notes}</ul>` : `<p>바뀐 파일 ${n.changed || 0}개를 새로 받았어요.</p>`}${n.pip ? `<p class="hint">${esc(n.pip)}</p>` : ''}${kept}${edits}</div>
    <div class="dlg-f"><button class="btn solid" data-close type="button">확인</button></div>`);
}

async function refreshState() {
  S.state = await api('/api/state');
  syncHeader();
  renderRail();
}

/* ---------------------------------------------------------------- 왼쪽 목록 */
function chipHtml(b) {
  const c = b.colors || {};
  return `<span class="chip" style="background:${esc(c.bg || '#888')}"><i style="background:${esc(c.accent || '#ccc')}"></i></span>`;
}
/* 브랜드 접기/펼치기: 이 PC 화면 설정이라 브라우저 저장소에 둠 */
const FOLD_KEY = 'ms.fold';
S.fold = (() => { try { return new Set(JSON.parse(localStorage.getItem(FOLD_KEY) || '[]')); } catch (e) { return new Set(); } })();
function saveFold() { try { localStorage.setItem(FOLD_KEY, JSON.stringify([...S.fold])); } catch (e) { /* 저장 못 해도 이번 실행 동안은 유지 */ } }
function renderRail() {
  const st = S.state;
  const sel = S.sel || {};
  const curBrand = sel.type === 'brand' ? sel.id : sel.type === 'video' ? (st.videos.find(v => v.name === sel.id) || {}).brand : null;
  const allFolded = st.brands.length && st.brands.every(b => S.fold.has(b.slug));
  $('#rail').innerHTML = `
    <div class="rail-head"><h2>광고 계정</h2><div class="rail-acts">
      ${st.brands.length > 1 ? `<button class="btn ghost small" data-act="fold-all" type="button" title="${allFolded ? '모든 계정 펼치기' : '모든 계정 접기'}">${allFolded ? '모두 펼치기' : '모두 접기'}</button>` : ''}
      <button class="btn ghost small" data-act="new-brand" type="button">계정 추가</button></div></div>
    ${st.brands.map(b => {
      const vids = st.videos.filter(v => v.brand === b.slug);
      const folded = S.fold.has(b.slug);
      return `<div class="acct ${folded ? 'folded' : ''}">
        <div class="acct-line">
          <button class="fold-btn" data-act="fold" data-id="${esc(b.slug)}" type="button" aria-expanded="${!folded}" title="${folded ? '펼치기' : '접기'}"><svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5 6 7.5 9 4.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
          <button class="acct-row ${sel.type === 'brand' && sel.id === b.slug ? 'on' : ''}" data-act="brand" data-id="${esc(b.slug)}" type="button" title="브랜드 설정">
            ${chipHtml(b)}<span class="nm">${esc(b.name)}</span>${folded && vids.length ? `<span class="cnt">${vids.length}</span>` : ''}</button>
        </div>
        ${folded ? '' : `<div class="vids">
          ${vids.map(v => `<button class="vid-row ${sel.type === 'video' && sel.id === v.name ? 'on' : ''}" data-act="video" data-id="${esc(v.name)}" type="button">
            <span class="t">${esc(v.title)}</span>${v.template === 'deck' ? '<span class="deck-tag">발표</span>' : ''}
            <span class="ratios" title="형식별 상태 (채워진 칸: MP4 완성)">${(v.formats || []).map(f => ratioIcon(f, v.status ? v.status[f] === 'mp4' ? 'mp4' : v.status[f] !== 'none' ? 'built' : '' : '')).join('')}</span>
          </button>`).join('')}
          <div class="add-row"><button class="btn ghost small add-vid" data-act="new-video" data-brand="${esc(b.slug)}" type="button">영상 추가</button><button class="btn ghost small add-vid" data-act="new-deck" data-brand="${esc(b.slug)}" type="button">발표 자료 추가</button></div>
        </div>`}
      </div>`;
    }).join('')}
    ${st.videos.filter(v => !v.brand).map(v => `<div class="acct"><button class="vid-row" data-act="video" data-id="${esc(v.name)}" type="button"><span class="t">${esc(v.title)}</span></button></div>`).join('')}`;
}
$('#rail').addEventListener('click', e => {
  const b = e.target.closest('[data-act]');
  if (!b) return;
  const act = b.dataset.act;
  if (act === 'brand') selectBrand(b.dataset.id);
  if (act === 'video') selectVideo(b.dataset.id);
  if (act === 'new-brand') dlgNewBrand();
  if (act === 'new-video') dlgNewVideo(b.dataset.brand);
  if (act === 'new-deck') dlgNewDeck(b.dataset.brand);
  if (act === 'fold') { const id = b.dataset.id; S.fold.has(id) ? S.fold.delete(id) : S.fold.add(id); saveFold(); renderRail(); }
  if (act === 'fold-all') {
    const all = S.state.brands.every(x => S.fold.has(x.slug));
    S.fold = all ? new Set() : new Set(S.state.brands.map(x => x.slug));
    saveFold(); renderRail();
  }
});

function renderCrumbs() {
  const c = $('#crumbs');
  if (!S.sel) { c.innerHTML = ''; return; }
  if (S.sel.type === 'brand') { c.innerHTML = `<b>${esc(S.brand ? S.brand.name : S.sel.id)}</b><span class="sep">/</span><span>브랜드 설정</span>`; return; }
  const v = S.detail && S.detail.video;
  const b = v && S.state.brands.find(x => x.slug === v.brand);
  c.innerHTML = `<span>${esc(b ? b.name : '')}</span><span class="sep">/</span><b>${esc(v ? v.title : S.sel.id)}</b>`;
}
function setSaveState(text, cls = '') { const s = $('#saveState'); s.textContent = text; s.className = 'save-state ' + cls; }

/* ---------------------------------------------------------------- 선택 */
function goHome() {
  saveVideo.flush(); saveBrand.flush();
  S.sel = null; S.detail = null; S.brand = null;
  history.replaceState(null, '', '#');
  renderRail(); renderCrumbs();
  const hasBrands = S.state.brands.length > 0;
  $('#editor').innerHTML = `<div class="welcome">
    <h1>어떤 광고를 만들까요?</h1>
    <p>왼쪽에서 광고 계정을 고르거나 새로 만드세요. 문구와 사진을 넣으면 오른쪽에서 바로 움직이는 미리보기가 나와요.</p>
    <ol class="flow">
      <li><div><b>광고 계정 만들기</b><span>로고나 대표 색만 있으면 색 조합을 알아서 맞춰요.</span></div></li>
      <li><div><b>영상 추가</b><span>사진이 있으면 사진형, 없으면 글자형을 고르세요.</span></div></li>
      <li><div><b>문구와 사진 넣기</b><span>문구는 Claude에게 초안을 맡길 수 있어요.</span></div></li>
      <li><div><b>MP4 만들기</b><span>릴스·쇼츠(9:16), 피드(4:5, 1:1), 유튜브(16:9)를 한 번에 뽑아요.</span></div></li>
    </ol>
    <button class="btn solid" type="button" id="wNew">${hasBrands ? '새 광고 계정 만들기' : '첫 광고 계정 만들기'}</button>
  </div>`;
  $('#wNew').onclick = () => dlgNewBrand();
  $('#stage').innerHTML = `<div></div><div class="frame-wrap"><div class="stage-empty"><b>미리보기</b>영상을 고르면 여기에 9:16, 4:5, 1:1, 16:9로 바로 보여요.</div></div><div></div>`;
}

async function selectVideo(name) {
  saveVideo.flush(); saveBrand.flush();
  try {
    S.detail = await api('/api/video?name=' + encodeURIComponent(name));
  } catch (e) { return fail(e); }
  S.sel = { type: 'video', id: name }; S.brand = null; S.undo = null; S.lenGaveUp = false;
  const fm = S.detail.video.formats || FMT_KEYS;
  if (!fm.includes(S.fmt)) S.fmt = fm[0];
  // 직접 짠 영상도 같은 탭을 씀. 아직 짜기 전(시작 파일)이면 연출 탭에서 Claude Code 에게 맡기게
  if (S.detail.starter && S.tab === 'copy') S.tab = 'direct';
  if (!['copy', 'photos', 'music', 'direct', 'settings', 'publish', 'advanced'].includes(S.tab)) S.tab = 'copy';
  S.pub = null; S.pubAi = null;
  if (S.fold.has(S.detail.video.brand)) { S.fold.delete(S.detail.video.brand); saveFold(); }
  history.replaceState(null, '', '#v=' + encodeURIComponent(name));
  renderRail(); renderCrumbs(); renderEditor(); renderStage();
  requestPreview.now(true);
}

async function selectBrand(slug) {
  saveVideo.flush(); saveBrand.flush();
  try {
    const r = await api('/api/brand?slug=' + encodeURIComponent(slug));
    S.brand = r.brand;
    S.brand.slug = slug;
    S.brand.colors = S.brand.colors || {};
    S.brand.type = S.brand.type || {};
    S.brand.fonts = S.brand.fonts || [];
  } catch (e) { return fail(e); }
  S.sel = { type: 'brand', id: slug }; S.detail = null;
  history.replaceState(null, '', '#b=' + encodeURIComponent(slug));
  renderRail(); renderCrumbs(); renderBrandEditor(); renderBrandStage();
}

/* ---------------------------------------------------------------- 저장 */
const saveVideo = debounce(async () => {
  if (!S.detail) return;
  const name = S.detail.name, video = S.detail.video;
  setSaveState('저장하는 중', 'busy');
  try {
    const r = await api('/api/video/save', { name, video });
    const same = S.detail && S.detail.name === name;
    if (same) S.detail.status = r.status;
    setSaveState('저장됨');
    const sv = S.state.videos.find(v => v.name === name);
    if (sv) { sv.title = video.title; sv.formats = video.formats; sv.status = r.status; }
    renderRail(); renderCrumbs();
    if (S.needPreview) { S.needPreview = false; if (same) requestPreview(); }
  } catch (e) { setSaveState('저장 못 함', 'err'); fail(e); }
}, 650);

function changed(preview = true) { if (preview) S.needPreview = true; setSaveState('수정됨', 'busy'); saveVideo(); }

const saveBrand = debounce(async () => {
  if (!S.brand || !S.sel || S.sel.type !== 'brand') return;
  const slug = S.sel.id, brand = S.brand;
  setSaveState('저장하는 중', 'busy');
  try {
    const r = await api('/api/brand/save', { slug, brand });
    const i = S.state.brands.findIndex(b => b.slug === slug);
    if (i >= 0) S.state.brands[i] = r.summary;
    setSaveState('저장됨');
    renderRail(); renderCrumbs();
  } catch (e) { setSaveState('저장 못 함', 'err'); fail(e); }
}, 600);

/* ---------------------------------------------------------------- 미리보기 */
let previewSeq = 0;
const requestPreview = debounce(async (first) => {
  if (!S.detail) return;
  const name = S.detail.name, fmt = S.fmt, seq = ++previewSeq;
  const frame = $('#frame');
  if (frame) frame.classList.add('loading');
  if (!first) setSaveState('미리보기 만드는 중', 'busy');
  try {
    const r = await api('/api/preview', { name, format: fmt });
    if (seq !== previewSeq || !S.detail || S.detail.name !== name) return;
    S.previewUrl[name + ':' + r.format] = r.url;
    loadIframe();
    setSaveState('저장됨');
  } catch (e) {
    if (seq === previewSeq) { setSaveState('미리보기 실패', 'err'); fail(e); }
    const f = $('#frame'); if (f) f.classList.remove('loading');
  }
}, 900);

function loadIframe() {
  const f = $('#frame');
  if (!f || !S.detail) return;
  const url = S.previewUrl[S.detail.name + ':' + S.fmt];
  if (!url) return;
  const ifr = $('iframe', f);
  let keep = '';   // 발표 자료: 고친 뒤 다시 그려도 보던 장에서 이어 봄
  if (S.detail.video.template === 'deck') try { const h = ifr.contentWindow.location.hash; if (/^#\d+$/.test(h)) keep = h; } catch (e) { /* 아직 안 열림 */ }
  const src = url + (S.safe && !keep ? '&safe=1#safe' : keep);
  ifr.onload = () => f.classList.remove('loading');
  if (ifr.getAttribute('src') !== src) ifr.setAttribute('src', src); else f.classList.remove('loading');
}

function fitFrame() {
  const wrap = $('#frameWrap'), f = $('#frame');
  if (!wrap || !f) return;
  const { w, h } = FMT[S.fmt];
  const cs = getComputedStyle(wrap);
  const aw = wrap.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  const ah = wrap.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
  const s = Math.max(.05, Math.min(aw / w, ah / h));
  f.style.width = Math.floor(w * s) + 'px';
  f.style.height = Math.floor(h * s) + 'px';
}
const ro = new ResizeObserver(() => fitFrame());

function renderStage() {
  const d = S.detail;
  if (!d) return;
  const fm = d.video.formats || FMT_KEYS;
  const out = d.outputs[S.fmt] || {};
  if (d.video.template === 'deck') return renderDeckStage();
  $('#stage').innerHTML = `
    <div class="stage-bar">
      <div class="fmts" role="tablist" aria-label="비율">
        ${FMT_KEYS.map(f => `<button class="fmt ${f === S.fmt ? 'on' : ''}" data-fmt="${f}" role="tab" aria-selected="${f === S.fmt}" type="button" ${fm.includes(f) ? '' : 'disabled title="설정 탭에서 이 형식을 켜면 볼 수 있어요"'}>${ratioIcon(f)}${FMT[f].label}</button>`).join('')}
      </div>
      <span class="grow"></span>
      <label class="toggle" title="플랫폼 버튼·글자가 덮는 영역을 빨갛게 보여 줘요"><input type="checkbox" id="safeT" ${S.safe ? 'checked' : ''}>세이프존</label>
      <button class="btn small" id="reload" type="button" title="미리보기를 다시 만듭니다">다시 그리기</button>
    </div>
    <div class="frame-wrap" id="frameWrap">
      <div class="frame loading" id="frame"><iframe title="영상 미리보기" allow="fullscreen"></iframe><div class="busy">미리보기 만드는 중</div></div>
    </div>
    <div class="stage-foot">
      <button class="btn small" id="sheetBtn" type="button" title="12장면을 한 장에 모아 확인">장면 모음</button>
      <button class="btn small" id="checkBtn" type="button" title="빠진 파일, 긴 문구, 출처, 광고 표현 점검">점검</button>
      <span class="out-link">${out.mp4 ? `<a href="#" id="playOut">${FMT[S.fmt].label} 완성본 보기</a>` : ''}</span>
      <span class="grow" style="flex:1"></span>
      <button class="btn rec" id="recBtn" type="button">MP4 만들기</button>
    </div>`;
  $$('.fmt[data-fmt]').forEach(b => b.onclick = () => { if (b.disabled) return; S.fmt = b.dataset.fmt; renderStage(); if (S.previewUrl[d.name + ':' + S.fmt]) loadIframe(); else requestPreview.now(true); });
  $('#safeT').onchange = e => { S.safe = e.target.checked; loadIframe(); };
  $('#reload').onclick = () => requestPreview.now(true);
  $('#sheetBtn').onclick = () => runSheet();
  $('#checkBtn').onclick = () => dlgCheck();
  $('#recBtn').onclick = () => dlgRender();
  const po = $('#playOut'); if (po) po.onclick = e => { e.preventDefault(); dlgPlay([{ format: S.fmt, url: out.mp4 }]); };
  ro.disconnect(); ro.observe($('#frameWrap'));
  fitFrame();
  if (S.previewUrl[d.name + ':' + S.fmt]) loadIframe();
}

function renderDeckStage() {
  const d = S.detail, out = d.outputs.wide || {};
  S.fmt = 'wide';
  $('#stage').innerHTML = `
    <div class="stage-bar"><span class="hint">미리보기를 누르거나 → ← 로 넘겨 보세요. 숫자+Enter 로 그 장으로 가요.</span><span class="grow"></span>
      <button class="btn small" id="reload" type="button" title="미리보기를 다시 만듭니다">다시 그리기</button></div>
    <div class="frame-wrap" id="frameWrap">
      <div class="frame loading" id="frame"><iframe title="발표 미리보기" allow="fullscreen"></iframe><div class="busy">미리보기 만드는 중</div></div>
    </div>
    <div class="stage-foot">
      <button class="btn small" id="sheetBtn" type="button" title="모든 장의 마지막 화면을 한 장에 모아 확인">장 모음</button>
      <button class="btn small" id="checkBtn" type="button" title="빠진 파일, 긴 문구, 출처 점검">점검</button>
      <span class="out-link">${out.pptx ? '<a href="#" id="openPptx">PPT 열기</a>' : ''}${out.pptx && out.pdf ? ' · ' : ''}${out.pdf ? '<a href="#" id="openPdf">PDF 보기</a>' : ''}</span>
      <span class="grow" style="flex:1"></span>
      <button class="btn" id="pdfBtn" type="button" title="장마다 등장이 끝난 화면을 모아 고해상도 PDF로 (나눠 주기·인쇄용)">PDF</button>
      <button class="btn" id="pptxBtn" type="button" title="PowerPoint 파일로. 글·도형을 고칠 수 있고, 장마다 등장 애니메이션과 모핑 전환이 들어가요">PPT 만들기</button>
      <button class="btn rec" id="presentBtn" type="button" title="브라우저에서 발표 화면을 열어요. F5 전체 화면, 클리커로 넘겨요">발표 시작</button>
    </div>`;
  $('#reload').onclick = () => requestPreview.now(true);
  $('#sheetBtn').onclick = () => runSheet();
  $('#checkBtn').onclick = () => dlgCheck();
  $('#pdfBtn').onclick = () => deckPdf();
  $('#pptxBtn').onclick = () => deckPptx();
  const ox = $('#openPptx'); if (ox) ox.onclick = e => { e.preventDefault(); api('/api/deck/open-file', { name: d.name, kind: 'pptx' }).catch(fail); };
  $('#presentBtn').onclick = () => deckPresent();
  const op = $('#openPdf'); if (op) op.onclick = e => { e.preventDefault(); window.open(out.pdf, '_blank'); };
  ro.disconnect(); ro.observe($('#frameWrap'));
  fitFrame();
  if (S.previewUrl[d.name + ':wide']) loadIframe(); else requestPreview.now(true);
}

/* ---------------------------------------------------------------- 편집: 영상 */
function renderEditor() {
  const d = S.detail;
  const v = d.video;
  // 작업 순서대로: 문구 → 사진 → 음악 → 연출 → 올리기, 그 뒤에 설정·고급
  const st = stepState();
  const steps = v.template === 'deck' ? [['copy', '구성·문구'], ['photos', '사진'], ['direct', '연출']] : [['copy', '문구'], ['photos', '사진'], ['music', '음악'], ['direct', '연출'], ['publish', '올리기']];
  const tabs = steps.map(([k, l], i) => [k, `<span class="tab-no ${st[k] ? 'done' : ''}">${st[k] ? '✓' : i + 1}</span>${l}`]).concat([['settings', '설정'], ['advanced', '고급']]);
  const firstExtra = steps.length;
  const ti = TEMPLATE_INFO[v.template] || { name: v.template ? v.template : d.scratch ? '처음부터 짠 영상' : '직접 만든 영상' };
  const scroll = $('#editor').scrollTop;
  $('#editor').innerHTML = `
    <div class="ed-head">
      <div class="ed-title"><h1>${esc(v.title || d.name)}</h1>
        <button class="btn ghost small" data-act="duplicate" type="button" title="이 영상을 복사해 다른 버전이나 다른 계정용으로 만들기">복제</button></div>
      <div class="ed-sub">${esc(ti.name)} · ${esc(d.name)}</div>
      <div class="tabs" role="tablist">${tabs.map(([k, l], i) => `<button class="tab ${S.tab === k ? 'on' : ''} ${i === firstExtra ? 'gap' : ''}" data-tab="${k}" role="tab" aria-selected="${S.tab === k}" type="button">${l}</button>`).join('')}</div>
    </div>
    <div class="ed-body" id="edBody"></div>`;
  $$('.tab', $('#editor')).forEach(t => t.onclick = () => { S.tab = t.dataset.tab; renderEditor(); });
  const body = $('#edBody');
  if (S.tab === 'copy') body.innerHTML = isFilm(v.template) ? filmEditor(v.content || {}) : d.custom ? customCopy()
    : v.template === 'deck' ? deckAiPanel() + deckEditor(v.content || {})
    : aiPanel() + (isAuto(v.template) ? filmEditor(v.content || {}) : v.template === 'kinetic' ? kineticEditor(v.content || {}) : v.template === 'promo' ? promoEditor(v.content || {}) : v.template === 'scenes' ? scenesEditor(v.content || {}) : customNote());
  else if (S.tab === 'music') body.innerHTML = musicTab();
  else if (S.tab === 'direct') body.innerHTML = (v.template === 'deck' ? '' : lengthPanel()) + lookPanel() + stylePanel() + (directionPanel() || '<section class="sec"><p class="hint" style="margin:0">이 영상은 연출 프롬프트가 없어요. 오른쪽 위 "Claude Code 열기"로 말로 부탁하면 돼요.</p></section>');
  else if (S.tab === 'photos') body.innerHTML = photosTab();
  else if (S.tab === 'settings') body.innerHTML = settingsTab();
  else if (S.tab === 'publish') { body.innerHTML = publishTab(); if (!S.pub) loadPub(); }
  else body.innerHTML = advancedTab();
  $('#editor').scrollTop = scroll;
  bindDrop();
}

/* ---------------------------------------------------------------- 올리기 (유튜브·인스타) */
const PRIV = [['private', '비공개'], ['unlisted', '일부 공개'], ['public', '공개']];
async function loadPub(render = true) {
  if (!S.detail) return;
  const name = S.detail.name;
  try { await saveVideo.flush(); const r = await api('/api/publish?name=' + encodeURIComponent(name)); if (S.detail && S.detail.name === name) { S.pub = r; if (render && S.tab === 'publish') renderEditor(); } }
  catch (e) { fail(e); }
}
const pubDirty = debounce(() => loadPub(false).then(() => { const box = $('#pubFinal'); if (box) box.outerHTML = pubFinal(); }), 900);
function pubFinal() {
  const P = S.pub;
  if (!P) return '<div id="pubFinal" class="hint">불러오는 중…</div>';
  return `<div id="pubFinal" class="pub-final">${P.platforms.map(p => { const t = P.texts[p.id] || {}; return `<details class="pub-prev"><summary><b>${esc(p.name)}</b><span class="hint"> · ${esc(p.fmt)}${S.detail.status[p.fmt] === 'mp4' ? ' · MP4 있음' : ' · MP4 없음'}</span>${t.notes && t.notes.length ? `<span class="warn"> · 확인 ${t.notes.length}</span>` : ''}</summary>
    ${t.title ? `<div class="pv-k">제목</div><pre>${esc(t.title)}</pre>` : ''}<div class="pv-k">${p.site === 'youtube' ? '설명' : '캡션'}</div><pre>${esc(t.text || '')}</pre>
    ${(t.notes || []).map(n => `<div class="warn">· ${esc(n)}</div>`).join('')}
    <div class="row-acts"><button class="btn ghost small" data-act="pub-copy" data-p="${esc(p.id)}" type="button">${p.site === 'youtube' ? '제목·설명 복사' : '캡션 복사'}</button></div></details>`; }).join('')}</div>`;
}
function publishTab() {
  const d = S.detail, v = d.video, P = S.pub;
  const tags = ((v.upload || {}).hashtags || (P && P.meta.hashtags) || []).join(' ');
  const yts = P ? P.platforms.filter(p => p.site === 'youtube') : [];
  const ig = P ? P.platforms.filter(p => p.site === 'instagram') : [];
  const yt = P ? P.youtube : null, soc = P ? P.social : {};
  const done = P ? P.done : {};
  const ai = S.pubAi;
  const ph = P ? P.meta : {};
  return `
  <section class="sec"><div class="sec-h"><h3>올릴 글</h3></div>
    <p class="hint" style="margin-top:0">비워 둔 칸은 영상 문구로 채워져요. 사진 출처(CC BY)와 유료 광고 표시는 끝에 자동으로 붙어요.</p>
    <div class="ai-mini"><input type="text" id="pubBrief" placeholder="Claude에게 덧붙일 말 (예: 망원동 주민 대상, 주말 방문 유도)">${modelSelect()}<button class="btn solid small" data-act="pub-ai" type="button" ${S.state.claude ? '' : 'disabled'}>Claude에게 맡기기</button></div>
    ${ai ? `<div class="pub-ai"><div class="pv-k">Claude 초안${ai.busy ? ' · 쓰는 중…' : ''}</div>${ai.busy ? '' : `
      ${ai.title ? `<pre><b>제목</b>\n${esc(ai.title)}</pre>` : ''}${ai.description ? `<pre><b>설명</b>\n${esc(ai.description)}</pre>` : ''}${ai.caption ? `<pre><b>캡션</b>\n${esc(ai.caption)}</pre>` : ''}
      ${ai.hashtags ? `<pre>${esc([].concat(ai.hashtags).join(' '))}</pre>` : ''}${ai.notes ? `<div class="hint">${esc(ai.notes)}</div>` : ''}
      <div class="row-acts"><button class="btn solid small" data-act="pub-ai-apply" type="button">이 글로 채우기</button><button class="btn ghost small" data-act="pub-ai-close" type="button">닫기</button></div>`}</div>` : ''}
    ${yts.length || !P ? fText('upload.title', '유튜브 제목', { ph: ph.title || '' }) : ''}
    ${yts.length || !P ? fText('upload.description', '유튜브 설명', { multi: true, rows: 4, ph: ph.description || '' }) : ''}
    ${ig.length || !P ? fText('upload.caption', '인스타 캡션', { multi: true, rows: 4, ph: ph.caption || '', hint: '첫 줄이 「더 보기」 전에 보여요.' }) : ''}
    <div class="field"><label class="lbl" for="f_upload_hashtags">해시태그 <span class="cnt ${tags.split(' ').filter(Boolean).length > 5 ? 'over' : ''}">${tags.split(' ').filter(Boolean).length}개</span></label>
      <input id="f_upload_hashtags" type="text" data-path="upload.hashtags" data-type="tags" value="${esc(tags)}" placeholder="${esc((ph.hashtags || []).join(' '))}">
      <div class="hint">인스타그램은 5개까지만 들어가요. 비우면 계정 공통 해시태그를 써요.</div></div>
    <div class="row">${fText('upload.coverAt', '커버로 쓸 장면 (초)', { num: true, ph: '비우면 30% 지점' })}
      <div class="field"><span class="lbl">&nbsp;</span>${fCheck('upload.paid', '협찬·유료 광고예요 (#광고 표시)')}</div></div>
    <div class="pv-k" style="margin-top:6px">플랫폼별 최종 글</div>${pubFinal()}
  </section>
  <section class="sec"><div class="sec-h"><h3>업로드 안내 묶음</h3></div>
    <p class="hint" style="margin-top:0">플랫폼마다 영상 파일, 커버·썸네일, 복사해서 붙일 글, 체크리스트를 한 폴더에 모아 줘요. 인스타 릴스는 이 묶음으로 올려요.</p>
    <div class="row-acts"><button class="btn solid" data-act="pub-kit" type="button">안내 만들기</button>
      ${P && P.kit ? `<button class="btn ghost" data-act="pub-kit-open" type="button">안내 열기</button><button class="btn ghost" data-act="pub-kit-folder" type="button">폴더 열기</button>` : ''}</div>
    ${P && P.platforms.some(p => S.detail.status[p.fmt] !== 'mp4') ? `<div class="mp4-need"><span>올리는 파일은 MP4예요. 아직 MP4가 없는 형식(${[...new Set(P.platforms.filter(p => S.detail.status[p.fmt] !== 'mp4').map(p => FMT[p.fmt] ? FMT[p.fmt].label : p.fmt))].join(', ')})은 글과 커버만 들어가요.</span><button class="btn rec small" data-act="pub-mp4" type="button">MP4 만들기</button></div>` : ''}
  </section>
  <section class="sec"><div class="sec-h"><h3>유튜브에 바로 올리기</h3></div>
    ${!P ? '<p class="hint">불러오는 중…</p>' : !yts.length ? '<p class="hint" style="margin-top:0">9:16 이나 16:9 형식이 있어야 유튜브에 올릴 수 있어요.</p>' : !yt.client ? `
      <p class="hint" style="margin-top:0">PC마다 한 번, 구글 클라우드에서 OAuth 클라이언트(데스크톱 앱)를 만들어 JSON 파일을 넣어 주세요. 순서는 docs/UPLOAD.md 에 있어요.</p>
      <ol class="steps"><li>구글 클라우드 콘솔에서 프로젝트를 만들고 <b>YouTube Data API v3</b> 사용 설정</li><li>OAuth 동의 화면: 외부, 앱 이름 입력, 내 구글 계정을 테스트 사용자로 추가 → 게시 상태를 <b>프로덕션</b>으로 (테스트 상태면 7일마다 다시 연결해야 해요)</li><li>사용자 인증 정보 → OAuth 클라이언트 ID → 유형 <b>데스크톱 앱</b> → JSON 다운로드</li></ol>
      <div class="row-acts"><button class="btn ghost" data-act="open-web" data-url="https://console.cloud.google.com/apis/library/youtube.googleapis.com" type="button">구글 클라우드 열기</button>
      <label class="btn solid">JSON 파일 넣기<input type="file" accept=".json,application/json" data-act="yt-client" hidden></label></div>` : !yt.connected ? `
      <p class="hint" style="margin-top:0">이 계정(${esc(S.state.brands.find(b => b.slug === v.brand)?.name || v.brand)})에 쓸 유튜브 채널을 연결하세요. 브라우저가 열리면 채널을 고르고 허용을 누르면 돼요. '확인되지 않은 앱' 화면이 나오면 고급 → 계속을 누르세요.</p>
      <div class="row-acts"><button class="btn solid" data-act="yt-connect" type="button">유튜브 채널 연결</button></div>` : `
      <div class="yt-ch"><span>연결된 채널 <b>${esc(yt.channel || '(이름 없음)')}</b></span><button class="btn ghost small" data-act="yt-disconnect" type="button">연결 끊기</button></div>
      ${yts.map(p => { const dn = done[p.id]; const has = S.detail.status[p.fmt] === 'mp4'; return `<div class="yt-row"><div><b>${esc(p.name)}</b><span class="hint"> · ${esc(p.fmt)} · ${has ? 'MP4 있음' : 'MP4 없음'}</span>
        ${dn ? `<div class="hint">올린 영상: <a href="#" data-act="yt-open" data-url="${esc(dn.url)}">${esc(dn.url)}</a> · ${esc(PRIV.find(x => x[0] === dn.privacy)?.[1] || dn.privacy)} · ${esc(dn.at)}</div>` : ''}</div>
        <div class="row-acts"><select data-yt-priv="${esc(p.id)}">${PRIV.map(([k, l]) => `<option value="${k}" ${(v.upload && v.upload.privacy || 'private') === k ? 'selected' : ''}>${l}</option>`).join('')}</select>
        <button class="btn solid small" data-act="yt-upload" data-p="${esc(p.id)}" data-f="${esc(p.fmt)}" type="button" ${has ? '' : 'disabled'}>${dn ? '한 번 더 올리기' : '올리기'}</button></div></div>`; }).join('')}
      <p class="hint">검수받지 않은 구글 클라우드 프로젝트로 올린 영상은 유튜브가 비공개로 바꿔요. 올린 뒤 유튜브 스튜디오에서 공개로 바꾸면 돼요.</p>`}
  </section>
  <section class="sec"><div class="sec-h"><h3>인스타그램</h3></div>
    <p class="hint" style="margin-top:0">인스타그램 자동 업로드는 Meta 개발자 앱과 페이스북 페이지 연결이 필요해서, 지금은 위 안내 묶음으로 올려요. 안내 묶음의 영상과 cover.jpg 를 휴대폰으로 옮겨 올리거나 PC 인스타그램의 '만들기'로 올리면 돼요.</p>
    <div class="row-acts"><button class="btn ghost" data-act="open-web" data-url="https://www.instagram.com/" type="button">인스타그램 열기</button></div>
  </section>
  <section class="sec"><div class="sec-h"><h3>이 계정 공통</h3></div>
    <div class="row"><div class="field"><label class="lbl" for="socIg">인스타 계정</label><input id="socIg" data-soc="instagram" value="${esc(soc.instagram || '')}" placeholder="@계정"></div>
      <div class="field"><label class="lbl" for="socYt">유튜브 채널</label><input id="socYt" data-soc="youtube" value="${esc(soc.youtube || '')}" placeholder="@채널"></div></div>
    <div class="field"><label class="lbl" for="socTags">공통 해시태그</label><input id="socTags" data-soc="hashtags" value="${esc((soc.hashtags || []).join(' '))}" placeholder="#망원동카페 #핸드드립"></div>
    <div class="field"><label class="lbl" for="socFoot">설명·캡션 끝에 늘 붙일 말</label><textarea id="socFoot" rows="2" data-soc="footer" placeholder="예) 영업시간과 위치는 프로필 링크에서 확인하세요">${esc(soc.footer || '')}</textarea></div>
    <div class="row-acts"><button class="btn ghost small" data-act="soc-save" type="button">계정 공통 저장</button></div>
  </section>`;
}
async function ytClient(file) {
  if (!file) return;
  try { const up = await upload(file); await api('/api/youtube/client', { upload: up.id }); toast('OAuth 클라이언트를 등록했어요. 이제 채널을 연결하세요'); await loadPub(); }
  catch (e) { fail(e); }
}
async function pubAction(act, b) {
  const d = S.detail, name = d.name;
  if (act === 'pub-ai') {
    S.pubAi = { busy: true }; renderEditor();
    try {
      await saveVideo.flush();
      const job = await api('/api/job/publish-ai', { name, brief: ($('#pubBrief') || {}).value || '' });
      trackJob(job, j => { S.pubAi = j.status === 'done' ? j.result : null; if (S.detail && S.detail.name === name && S.tab === 'publish') renderEditor(); });
    } catch (e) { S.pubAi = null; renderEditor(); fail(e); }
    return;
  }
  if (act === 'pub-ai-apply') {
    const a = S.pubAi || {}, u = d.video.upload || (d.video.upload = {});
    for (const k of ['title', 'description', 'caption']) if (a[k]) u[k] = a[k];
    if (a.hashtags) u.hashtags = [].concat(a.hashtags).map(x => '#' + String(x).replace(/^#+/, '').replace(/\s+/g, '')).filter(x => x.length > 1);
    S.pubAi = null; changed(false); await saveVideo.flush(); await loadPub(); toast('Claude 글로 채웠어요. 고칠 데가 있으면 바로 고치세요'); return;
  }
  if (act === 'pub-ai-close') { S.pubAi = null; return renderEditor(); }
  if (act === 'pub-copy') { const t = S.pub && S.pub.texts[b.dataset.p]; if (t) await copyText(t.title ? `${t.title}\n\n${t.text}` : t.text); return toast('복사했어요'); }
  if (act === 'pub-kit') {
    await saveVideo.flush();
    try { const job = await api('/api/job/publish-kit', { name }); trackJob(job, async j => { if (j.status !== 'done') return; await loadPub(); toast('업로드 안내를 만들었어요'); api('/api/publish/open', { name }).catch(() => {}); }); } catch (e) { fail(e); }
    return;
  }
  if (act === 'pub-mp4') return dlgRender();
  if (act === 'pub-kit-open') return api('/api/publish/open', { name }).catch(fail);
  if (act === 'pub-kit-folder') return api('/api/open', { path: `out/${name}/upload` }).catch(fail);
  if (act === 'yt-connect') {
    try { const job = await api('/api/job/youtube-connect', { brand: d.video.brand }); trackJob(job, async j => { if (j.status === 'done') { toast(`유튜브 채널을 연결했어요: ${j.result.channel || ''}`); await loadPub(); } }); toast('브라우저에서 채널을 고르고 허용을 눌러 주세요'); } catch (e) { fail(e); }
    return;
  }
  if (act === 'yt-disconnect') { if (!confirm('이 계정의 유튜브 연결을 끊을까요? 다시 연결하면 돼요.')) return; try { await api('/api/youtube/disconnect', { brand: d.video.brand }); await loadPub(); } catch (e) { fail(e); } return; }
  if (act === 'yt-open') return api('/api/publish/open', { name, url: b.dataset.url }).catch(fail);
  if (act === 'yt-upload') {
    const pid = b.dataset.p, fmt = b.dataset.f, priv = ($(`[data-yt-priv="${pid}"]`) || {}).value || 'private';
    const t = S.pub && S.pub.texts[pid];
    if (t && t.notes && t.notes.some(n => /줄여|< >|제목이 비어/.test(n))) return toast(t.notes.join(' / '), true);
    if (!confirm(`${t ? t.name : '유튜브'}에 ${PRIV.find(x => x[0] === priv)[1]}로 올릴까요?\n\n제목: ${t ? t.title : ''}`)) return;
    await saveVideo.flush();
    try {
      const job = await api('/api/job/youtube-upload', { name, fmt, privacy: priv });
      trackJob(job, async j => {
        if (j.status !== 'done') return;
        const fresh = await api('/api/video?name=' + encodeURIComponent(name));
        if (S.detail && S.detail.name === name) { S.detail.video.upload = fresh.video.upload; await loadPub(); }
        toast(j.result.note ? `올렸어요. ${j.result.note}` : '유튜브에 올렸어요', !!j.result.note);
      });
    } catch (e) { fail(e); }
    return;
  }
  if (act === 'soc-save') {
    const social = {};
    $$('[data-soc]').forEach(el => { social[el.dataset.soc] = el.value; });
    try { await saveVideo.flush(); S.pub = await api('/api/publish/save', { name, upload: {}, social }); renderEditor(); toast('계정 공통 설정을 저장했어요'); } catch (e) { fail(e); }
  }
}

/* 필름 템플릿(키노트·UI 모프·쇼릴): content 를 훑어 글자 칸과 사진 고르기를 자동으로 만듦 */
const FILM_LABEL = { wordmark: '워드마크 (마침표는 자동)', label: '알약 안 라벨', button: '버튼', island: '아일랜드 문구', toast: '토스트', note: '안내 문구 (가상 브랜드 표시 등)',
  credit: '사진 출처 줄', tagline: '태그라인', sub: '아랫줄', title: '제목', word: '유리 글자 (영문 추천)', time: '시계', date: '날짜', song: '곡 제목', artist: '아티스트',
  logo: '로고', nav: '내비 버튼', headline: '헤드라인', product: '상품 이름', price: '가격', cta: '주문 버튼', tab: '브라우저 탭 제목', prompt: '터미널 명령',
  name: '채널 이름', subscribe: '구독 버튼', subscribed: '구독 후 버튼', notifyTitle: '알림 제목', notify: '알림 내용', placeholder: '검색창 안내', photoText: '사진 위 글자',
  tabs: '탭', items: '항목', lines: '터미널 줄', states: '상태 모프', formats: '비율', counter: '숫자', glass: '유리 장면', site: '사파리 페이지', build: '터미널 장면',
  channel: '채널 페이지', desk: '책상 장면', wall: '벽 액자', track: '플레이어 곡', chart: '차트', palette: '⌘K 검색', app: '앱 화면', steps: '타이핑 순서', videos: '영상 목록',
  number: '큰 숫자', artistName: '아티스트', unit: '단위', text: '문구', value: '값',
  photos: '사진 (격자 순서: 가운데·위·오른쪽·아래·왼쪽·모서리 넷)', tiles: '사진 격자 (5번째가 확대돼요)', works: '폰 세 대에 차례로 보일 사진',
  kicker: '첫 큰 글자 (영문 추천)', desc: '설명', tags: '스티커 태그', priceNote: '가격 아랫줄', ring: '둘레 글자', tag: '행사 이름 (작게)', marquee: '띠 글자 (영문)',
  prefix: '숫자 앞 (예: 최대)', percent: '할인율 숫자', off: '할인율 아래 딱지', periodLabel: '기간 제목', period: '기간', periodNote: '기간 알약', conds: '조건',
  soon: '셔터 안내문', soonSub: '안내문 아랫줄', dateText: '날짜 (글로)', sign: '간판 (닫힘 · 열림)', map: '지도', place: '장소', address: '주소', hint: '길 안내', from: '출발 역',
  perks: '영수증 (오픈 혜택)', timeLabel: '영업시간 제목', openWord: '마지막 큰 글자', motif: '계절 그림', season: '시즌 이름', lines: '인사말 (한 줄씩)', schedule: '일정',
  days: '날짜 · 요일 · 상태', curriculum: '커리큘럼', seats: '정원', start: '개강일', circle: '동그라미 칠 낱말', photoCaption: '사진 아래 글', header: '맨 위 작은 글',
  kind: '영문 꼬리표', day: '요일 (영문)', programTitle: '뒷면 제목', program: '프로그램 (시간 · 내용)', dday: '디데이', ddayNote: '도장 아랫줄', admit: '반쪽 아래 글',
  chatName: '대화 상대 이름', status: '상태 글', chat: '대화 (누가 · 말)', job: '채용 카드', placeholder: '입력창 안내', rows: '줄', footer: '아래 작은 글', end: '마지막 판 (가게 이름 · 계정)',
  stamp: '도장 글자 (영문)', stampSub: '도장 아랫줄', stops: '들른 곳 (이름 · 사진 · 한 줄)', stats: '숫자 카드', thanks: '마지막 인사', source: '숫자 출처',
  unit: '단위', viz: '그래프', series: '그래프 값 (쉼표로)', max: '목표 값', total: '전체 자리', left: '남은 자리', slots: '수업 칸 (요일 번호 · 시간)', cta: '마무리',
  button: '버튼', items: '항목', notes: '메모', label: '꼬리표', name: '이름', price: '가격', time: '시간', date: '날짜', headline: '헤드라인', sub: '아랫줄', note: '안내 문구' };
Object.assign(FILM_LABEL, { mission: '미션 (줄바꿈으로 2~3줄)', highlight: '강조할 구절 (문장 안 그대로)', pillarsTitle: '하는 일 제목', pillars: '하는 일 (아이콘 · 이름 · 한 줄)', symbol: '아이콘',
  factsTitle: '숫자 제목', partnersTitle: '함께하는 곳 제목', partners: '함께하는 곳 (한 줄에 하나, 로고는 사진 키)', card: '명함', slogan: '슬로건', site: '웹사이트', email: '이메일', tel: '전화',
  problem: '문제', pains: '불편 태그 (2~3개)', product: '제품', tagline: '한 줄 소개', features: '핵심 기능 (2~4개)', spot: '커서가 누를 자리 (가로, 세로 0~1)', flow: '쓰는 흐름', result: '효과 숫자 (근거 없으면 비우기)',
  milestones: '이정표 (3~7개, 오래된 것부터)', year: '연도 (2019.06 처럼 써도 돼요)', now: '마지막 문장 (지금)', badgeUnit: '기념 숫자 단위 (주년·년)', photo: '사진',
  topic: '화면 꼬리표 (비우면 종류에 맞게)', partner: '협약 상대 (업무협약)', deal: '협약 이름', amount: '금액 (투자 유치)', round: '라운드 (예: 시리즈 A)', by: '누가 (주최·기관·투자사·말한 사람)',
  award: '상·인증 (수상·인증 획득)', launch: '새 제품 (신규 출시)', quote: '인용 (실제로 한 말만, 비우면 장면 없음)', ticker: '아래 흐르는 띠 (문장들)', plan: '앞으로의 계획 (마무리 한 줄)' });
// 같은 키 이름이 템플릿마다 뜻이 다를 때 (경로 'result.label' 처럼 적으면 그 자리만)
const TPL_LABEL = {
  company: { label: '영문 꼬리표', name: '회사 이름 (비우면 브랜드 이름)', facts: '숫자 (값 · 단위 · 이름)', 'facts.label': '숫자 아래 이름', 'facts.value': '값', source: '숫자 출처 · 기준 시점',
    'pillars.title': '이름', 'pillars.desc': '한 줄', 'card.address': '주소' },
  product: { 'features.icon': '아이콘', 'problem.title': '질문형 제목', 'product.name': '제품 이름', 'product.photo': '스크린샷 (비우면 선 그림 화면)', 'features.title': '기능 이름', 'features.desc': '한 줄',
    'result.number': '숫자 (비우면 장면을 빼요)', 'result.label': '숫자 설명', 'result.source': '숫자 근거 · 출처', 'flow.steps': '단계 (3~4개)', 'flow.title': '흐름 제목' },
  timeline: { label: '영문 꼬리표', badge: '기념 숫자 (비우면 안 보여요)', 'milestones.title': '제목', 'milestones.text': '한 줄', 'now.title': '마지막 문장', 'now.sub': '아랫줄' },
  news: { kind: '범퍼 영문 꼬리표', badge: '딱지 (짧게)', type: '소식 종류', facts: '핵심 사실 (이름 · 값)', 'partner.name': '상대 이름', 'partner.photo': '상대 로고 (받은 파일만)',
    'amount.value': '금액', 'award.name': '상·인증 이름', 'launch.name': '제품 이름', 'launch.photo': '제품 사진', 'quote.text': '한 말', 'quote.by': '말한 사람 · 직함' },
};
const STORY_LABEL = { kicker: '꼬리표 (작게, 비워도 돼요)', title: '첫 문장 (훅, 줄바꿈은 엔터)', highlight: '강조 어절 (첫 문장 안 그대로)', points: '장점·기능·단계 (2~5개)',
  number: '숫자 (값을 비우면 장면이 빠져요)', 'number.prefix': '숫자 앞 (예: 최대)', 'number.value': '값', 'number.suffix': '단위', 'number.label': '숫자 설명', 'number.source': '근거 · 출처 (꼭)',
  photos: '사진 (0~4장, 없으면 사진 없는 모양)', cta: '마무리', 'cta.headline': '마무리 문장', 'cta.button': '버튼', 'cta.sub': '주소 · 아랫줄', note: '안내 문구 (가상 표시·기준일)' };
Object.keys(TEMPLATE_INFO).filter(k => TEMPLATE_INFO[k].look).forEach(k => { TPL_LABEL[k] = STORY_LABEL; });
const TPL_SELECT = {
  company: { symbol: [['chip', '칩 (기술·AI)'], ['chart', '그래프 (분석·성장)'], ['people', '사람 (팀·교육)'], ['globe', '지구 (해외·연결)'], ['cube', '큐브 (제품·3D)'], ['cloud', '구름 (클라우드·서비스)'], ['shield', '방패 (보안·품질)'], ['book', '책 (교육·콘텐츠)'], ['factory', '공장 (제조·생산)'], ['spark', '반짝임 (아이디어·새로움)']] },
  product: { icon: [['chart', '차트·분석'], ['bolt', '빠름·자동화'], ['shield', '보안'], ['link', '연결·연동'], ['users', '팀·협업'], ['bell', '알림'], ['clock', '시간 절약'], ['doc', '문서·보고서'], ['chat', '대화·상담'], ['spark', 'AI']] },
  news: { type: [['mou', '업무협약 (MOU)'], ['invest', '투자 유치'], ['award', '수상'], ['cert', '인증 획득'], ['launch', '신규 출시']] },
};
// [글, 글] 짝 목록의 칸 이름 (템플릿별, 경로 기준)
const COLS_TPL = {
  news: { facts: ['이름', '값'] }, event: { program: ['시간', '내용'] }, notice: { rows: ['날짜', '내용'] }, travel: { stops: ['장소', '사진', '한 줄'] },
  sale: { items: ['이름', '원래 가격', '할인가', '도장 글자'] }, greeting: { 'schedule.days': ['날짜', '요일', '상태'] }, academy: { 'schedule.slots': ['요일 번호 (0부터)', '시간'] },
  timeline: { milestones: ['연도', '제목', '한 줄', '사진'] }, keynote: { 'build.app.items': ['이름', '설명', '사진'], 'channel.videos': ['제목', '사진'] },
};
const colLabel = (path, j) => { const c = (COLS_TPL[tplOf()] || {})[relPath(path)]; return c && c[j] ? c[j] : String(j + 1); };
const tplOf = () => (S.detail && S.detail.video.template) || '';
const relPath = path => path.replace(/^content\./, '').replace(/\.\d+(?=\.|$)/g, '');
// 점 없는 키는 맨 위 칸에만 씀 (예: company 의 label 은 맨 위 꼬리표, facts 안의 label 은 따로)
const labelOf = (key, path) => { const t = TPL_LABEL[tplOf()] || {}, rel = relPath(path); return t[rel] || (!rel.includes('.') && t[key]) || FILM_LABEL[key] || key; };
const selectFor = key => (TPL_SELECT[tplOf()] || {})[key] || FILM_SELECT[key];
const FILM_SELECT = { viz: [['bars', '막대'], ['ring', '고리 (목표 대비)'], ['line', '선 (추세)'], ['dots', '점 (개수)']],
  motif: [['moon', '달 (추석)'], ['snow', '눈송이 (겨울·연말)'], ['flower', '꽃 (봄)'], ['leaf', '잎 (가을)'], ['sun', '해 (여름)']] };
const CHAT_WHO = [['them', '가게'], ['me', '보는 사람'], ['card', '채용 카드']];
const FILM_PHOTO_KEYS = new Set(['art', 'next', 'photo', 'banner', 'avatar', 'mascot', 'wide']);
const isPhotoKey = x => typeof x === 'string' && (/^photo\d+$/.test(x) || S.detail.assets.some(a => a.key === x) || S.detail.brandAssets.some(a => a.key === x));
const FILM_PHOTO_ARRAYS = new Set(['photos', 'tiles', 'works']);
const FILM_SKIP = new Set(['film', 'stretch', 'progress', 'bpm', 'hero', 'tipIndex', 'values', 'route', 'icon', 'roasts', 'sizes', 'colors']);
function filmPhotoOptions(cur) {
  const keys = [...S.detail.assets.map(a => a.key), ...S.detail.brandAssets.map(a => a.key)];
  const opts = keys.map(k => [k, k]);
  if (cur && !keys.includes(cur)) opts.unshift([cur, cur + ' (없음)']);
  return [['', '사진 고르기'], ...opts];
}
function filmField(path, key, val, depth) {
  const label = labelOf(key, path), sel = selectFor(key);
  if (FILM_SKIP.has(key) && !(TPL_SELECT[tplOf()] || {})[key]) return '';
  if (key === 'percent' && typeof val === 'object') return '';
  if (sel && typeof val === 'string') return fSelect(path, label, !val ? [['', '고르기 (비우면 기본)'], ...sel] : sel.some(([k]) => k === val) ? sel : [[val, val + ' (목록에 없음)'], ...sel]);
  if (typeof val === 'string') return FILM_PHOTO_KEYS.has(key) || /^photo\d+$/.test(val) ? fSelect(path, label, filmPhotoOptions(val)) : fText(path, label, { multi: val.includes('\n'), rows: (val.match(/\n/g) || []).length + 1 });
  if (typeof val === 'number') return fText(path, label, { num: true });
  if (Array.isArray(val) && val.length && val.every(x => typeof x === 'number')) return fText(path, label, { nums: true });
  if (key === 'chat' && Array.isArray(val)) {
    return `<div class="field"><span class="lbl">${esc(label)}</span>${val.map((it, i) => `<div class="row chat-row">${fSelect(`${path}.${i}.0`, `${i + 1}`, CHAT_WHO)}${it[0] === 'card' ? '<div class="field"><span class="lbl">&nbsp;</span><div class="hint">아래 채용 카드가 이 자리에 와요</div></div>' : fText(`${path}.${i}.1`, '말')}</div>`).join('')}</div>`;
  }
  if (Array.isArray(val)) {
    if (FILM_PHOTO_ARRAYS.has(key)) {
      return `<div class="field"><span class="lbl">${esc(label)} (순서대로)</span><div class="row3">${val.map((k, i) => fSelect(`${path}.${i}`, `${i + 1}`, filmPhotoOptions(k))).join('')}</div></div>`;
    }
    if (val.every(x => typeof x === 'string')) return fLines(path, label);
    // [글자, 사진키] 같은 짝 / {text: …} 객체 목록: 줄마다 옮기기·빼기, 끝에 추가
    const n = val.length, base = label.replace(/\s*\(.*\)$/, '');
    // 사진 칸인 열: 어느 줄이든 사진 키가 있거나 열 이름이 '사진'이면 (비운 칸도 사진 고르기로 남게)
    const photoCols = new Set();
    val.forEach(it => Array.isArray(it) && it.forEach((x, j) => { if (isPhotoKey(x) || colLabel(path, j) === '사진') photoCols.add(j); }));
    return `<div class="field arr"><span class="lbl">${esc(label)}</span>${val.map((it, i) => {
      let inner = '';
      if (Array.isArray(it)) inner = `<div class="row">${it.map((x, j) => typeof x === 'number' ? fText(`${path}.${i}.${j}`, colLabel(path, j), { num: true }) : typeof x !== 'string' ? '' : photoCols.has(j) ? fSelect(`${path}.${i}.${j}`, '사진', filmPhotoOptions(x)) : /^#[0-9a-f]{3,8}$/i.test(x) ? '' : fText(`${path}.${i}.${j}`, colLabel(path, j))).join('')}</div>`;
      else if (it && typeof it === 'object') inner = `<div class="row">${Object.entries(it).map(([k2, v2]) => filmField(`${path}.${i}.${k2}`, k2, v2, depth + 1)).join('')}</div>`;
      else return '';
      return `<div class="item mini">${itemHead(String(i + 1), path, i, n)}${inner}</div>`;
    }).join('')}<button class="btn ghost small add-line" data-act="add-item" data-path="${esc(path)}" type="button">${esc(base)} 추가</button></div>`;
  }
  if (val && typeof val === 'object' && depth < 2) {
    const inner = Object.entries(val).map(([k2, v2]) => filmField(`${path}.${k2}`, k2, v2, depth + 1)).join('');
    return inner ? `<section class="sec sub"><div class="sec-h"><h3>${esc(label)}</h3></div>${inner}</section>` : '';
  }
  return '';
}
// 배열에 줄을 더할 때: 마지막 줄과 같은 모양으로, 글은 비우고 숫자·고르기 값은 그대로
function blankLike(x, key) {
  if (Array.isArray(x)) return x.map(y => blankLike(y));
  if (x && typeof x === 'object') { const o = {}; for (const [k, y] of Object.entries(x)) o[k] = blankLike(y, k); return o; }
  if (typeof x === 'string') {
    if ((key && (selectFor(key) || FILM_SKIP.has(key))) || /^#[0-9a-f]{3,8}$/i.test(x)) return x;
    if (!key && x && isPhotoKey(x)) return freePhotoKeys(1)[0];   // [글, 사진키] 짝의 사진 칸
    return '';
  }
  return x;
}
function filmEditor(c) {
  const v = S.detail.video, info = TEMPLATE_INFO[v.template] || {};
  const top = Object.entries(c).filter(([k, x]) => typeof x !== 'object' || Array.isArray(x));
  const objs = Object.entries(c).filter(([k, x]) => x && typeof x === 'object' && !Array.isArray(x));
  return `${info.desc ? `<div class="sec"><p class="sec-note" style="margin:0">${esc(info.desc)}. 글자와 사진만 바꾸면 움직임은 그대로 따라와요. 연출 자체를 바꾸려면 4번 연출 탭에서 Claude Code에게 맡기세요.</p></div>` : ''}
    <section class="sec"><div class="sec-h"><h3>문구와 사진</h3></div>${top.map(([k, x]) => filmField('content.' + k, k, x, 0)).join('')}</section>
    ${objs.map(([k, x]) => filmField('content.' + k, k, x, 0)).join('')}`;
}

function customNote() {
  return `<div class="sec"><p class="sec-note" style="margin:0">이 영상은 템플릿 없이 직접 짠 영상이라 문구 칸이 없어요. 고칠 내용은 Claude Code에 말로 부탁하거나 고급 탭에서 설정을 바꾸세요.</p></div>`;
}
// 템플릿 없이 짠 영상: content 에 글이 있으면 자동 칸으로 고치게 함
function customCopy() {
  const d = S.detail, c = d.video.content || {};
  if (d.starter) return `<section class="sec"><div class="sec-h"><h3>아직 짜기 전이에요</h3></div>
    <p class="sec-note">적어 둔 설명으로 Claude Code가 이 영상만의 연출을 처음부터 짜요. Claude Code 창에서 장면 계획을 먼저 보여 주고, 빠진 정보는 물어봐요. 다 짜면 여기에 문구 칸이 생겨요.</p>
    ${d.video.brief ? `<div class="ask"><b>적어 둔 설명</b> ${esc(d.video.brief)}</div>` : ''}
    <div class="row-acts">${ccOK() ? modelSelect() + '<button class="btn solid small" data-act="cc-direction" type="button">' + (isApi() ? 'Claude에게 맡기기 (API)' : 'Claude Code에게 맡기기') + '</button>' : `<span class="hint">${isApi() ? 'Claude API 키가 없어요.' : '이 컴퓨터에서 Claude Code를 찾지 못했어요.'}</span>`}</div></section>`;
  const editable = Object.keys(c).some(k => !FILM_SKIP.has(k));
  if (!editable) return customNote();
  return `<div class="sec"><p class="sec-note" style="margin:0">${d.scratch ? '처음부터 짠 영상이에요.' : '템플릿 없이 직접 짠 영상이에요.'} 글과 사진은 여기서 고치고, 움직임·장면을 바꾸려면 4번 연출 탭에서 Claude Code에게 맡기세요.</p></div>`
    + aiPanel() + filmEditor(c);
}

/* 공용 입력 칸 */
function counter(path, val) {
  const key = path.replace(/^content\./, '').replace(/\.\d+(?=\.|$)/g, '');
  const lim = limitOf(key);
  if (!lim) return '';
  const n = lenOf(val);
  return `<span class="cnt ${n > lim ? 'over' : ''}" data-cnt="${esc(path)}" data-lim="${lim}">${n}/${lim}</span>`;
}
function fText(path, label, o = {}) {
  const val = getPath(S.detail.video, path);
  const v = val == null ? '' : val;
  const id = 'f_' + path.replace(/\W/g, '_');
  const input = o.multi
    ? `<textarea id="${id}" class="${o.big ? 'big' : ''}" rows="${o.rows || 2}" data-path="${esc(path)}" placeholder="${esc(o.ph || '')}">${esc(v)}</textarea>`
    : `<input id="${id}" type="${o.num ? 'number' : 'text'}" ${o.num ? 'step="any" data-type="num"' : o.nums ? 'data-type="nums"' : ''} data-path="${esc(path)}" value="${esc(Array.isArray(v) ? v.join(', ') : v)}" placeholder="${esc(o.ph || '')}">`;
  return `<div class="field"><label class="lbl" for="${id}">${esc(label)}${counter(path, v)}</label>${input}${o.hint ? `<div class="hint">${esc(o.hint)}</div>` : ''}</div>`;
}
function fSelect(path, label, options, o = {}) {
  const val = getPath(S.detail.video, path);
  const id = 'f_' + path.replace(/\W/g, '_');
  return `<div class="field"><label class="lbl" for="${id}">${esc(label)}</label><select id="${id}" data-path="${esc(path)}" ${o.type ? `data-type="${o.type}"` : ''}>
    ${options.map(([k, l]) => `<option value="${esc(k)}" ${String(val == null ? '' : val) === String(k) ? 'selected' : ''}>${esc(l)}</option>`).join('')}</select></div>`;
}
function fCheck(path, label, o = {}) {
  let val = getPath(S.detail.video, path);
  if (val === undefined) val = o.def;
  if (o.invert) val = !val;
  return `<label class="check"><input type="checkbox" data-path="${esc(path)}" data-type="bool" ${o.invert ? 'data-invert="1"' : ''} ${val ? 'checked' : ''}>${esc(label)}</label>`;
}
function fLines(path, label, o = {}) {
  const arr = getPath(S.detail.video, path) || [];
  return `<div class="field list-lines"><span class="lbl">${esc(label)}</span>
    ${arr.map((t, i) => `<div class="li"><input type="text" data-path="${esc(path)}.${i}" value="${esc(t)}" aria-label="${esc(label)} ${i + 1}">${counter(path + '.' + i, t)}
      <button class="icon-btn" data-act="del" data-path="${esc(path)}" data-i="${i}" type="button" title="빼기" aria-label="빼기">×</button></div>`).join('')}
    <button class="btn ghost small add-line" data-act="add-line" data-path="${esc(path)}" type="button">${esc(o.add || '항목 추가')}</button></div>`;
}
const itemHead = (label, path, i, n, extra = '') => `<div class="item-h"><b>${esc(label)}</b>${extra}
  <button class="icon-btn" data-act="up" data-path="${path}" data-i="${i}" type="button" ${i === 0 ? 'disabled' : ''} title="위로" aria-label="위로">↑</button>
  <button class="icon-btn" data-act="down" data-path="${path}" data-i="${i}" type="button" ${i === n - 1 ? 'disabled' : ''} title="아래로" aria-label="아래로">↓</button>
  <button class="icon-btn" data-act="del" data-path="${path}" data-i="${i}" type="button" title="빼기" aria-label="빼기">×</button></div>`;

async function copyText(t) {
  try { await navigator.clipboard.writeText(t); return true; } catch (e) {
    const ta = document.createElement('textarea'); ta.value = t; document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); } catch (e2) { /* 복사 막힘 */ } ta.remove(); return false;
  }
}
/* 상황 프리셋의 연출 프롬프트 (videos/<영상>/direction.md) */
function directionPanel() {
  const d = S.detail, pr = d.preset;
  if (!d.direction && !pr) return '';
  const open = !!S.dirOpen;
  const step = '';
  return `<section class="sec dir-panel"><div class="sec-h"><h3>${step}연출 다듬기${pr ? ` · ${esc(pr.name)}` : ''}</h3>
      <button class="btn ghost small" data-act="dir-toggle" type="button">${open ? '접기' : '펼쳐 보기'}</button></div>
    ${pr && pr.summary ? `<p class="sec-note" style="margin-top:0">${esc(pr.summary)}</p>` : ''}
    ${d.starter ? '<p class="hint" style="margin-top:0">아래 설명대로 Claude Code가 이 영상만의 연출을 처음부터 짜요. Claude Code 창에서 장면 계획을 먼저 보여 주고 진행해요.</p>'
      : !isFilm(d.video.template) ? '<p class="hint" style="margin-top:0">문구·사진·음악을 넣은 다음, 움직임·장면 구성을 더 다듬고 싶을 때 Claude Code에게 이 연출 프롬프트로 맡겨요.</p>' : ''}
    ${open ? `<textarea id="dirText" rows="16" class="dir-text" spellcheck="false">${esc(d.direction || '')}</textarea>
      <div class="dir-foot"><button class="btn ghost small" data-act="dir-save" type="button">고친 내용 저장</button><span class="hint">이 영상 폴더의 direction.md 에만 저장돼요.</span></div>` : ''}
    ${pr && (pr.check || []).length ? `<div class="dir-check"><b>올리기 전에 확인</b>${pr.check.map(x => `<span>${esc(x)}</span>`).join('')}</div>` : ''}
    <div class="dir-acts">${ccOK() ? modelSelect() + `<button class="btn solid small" data-act="cc-direction" type="button">${(isApi() ? 'Claude에게 ' : 'Claude Code에게 ') + (d.starter ? '처음부터 맡기기' : '이 연출로 맡기기') + (isApi() ? ' (API)' : '')}</button>` : ''}
      <button class="btn small" data-act="dir-copy" type="button">프롬프트 복사</button></div>
  </section>`;
}
/* 결 템플릿끼리 바꾸기: 10개가 같은 content 를 읽어서 문구는 그대로 두고 화면만 통째로 바뀜 */
function lookPanel() {
  const v = S.detail.video;
  if (!LOOK_TPLS.includes(v.template)) return '';
  const ps = (S.state.presets || []).filter(p => p.group === 'look');
  return `<section class="sec"><div class="sec-h"><h3>결 바꾸기</h3><span class="hint">문구·사진은 그대로</span></div>
    <p class="sec-note">같은 문구로 화면 구성과 움직임이 완전히 다른 템플릿으로 바꿔요. 스타일을 따로 고르지 않았다면 그 결에 어울리는 스타일도 같이 바뀌어요.</p>
    <div class="look-chips">${ps.map(p => `<button type="button" class="chipf ${p.template === v.template ? 'on' : ''}" data-act="look-tpl" data-t="${esc(p.template)}">${esc(p.name)}</button>`).join('')}</div></section>`;
}
/* 스타일: 잘 만든 프로덕트 모션에서 배운 보는 결·움직이는 결 (styles/<이름>, docs/STYLES.md) */
const STYLE_GROUPS = ['타이포', '제품 UI', '그라디언트·빛', '3D·사물', '그래픽·도형', '레트로·픽셀', '손그림', '콜라주·사진', '다이어그램·데이터', '시네마틱'];
const styleOf = id => (S.state.styles || []).find(x => x.id === id) || null;
const palDots = st => `<span class="pal">${(st.palette || []).slice(0, 6).map(c => `<i style="background:${esc(c)}"></i>`).join('')}</span>`;
function stylePanel() {
  const v = S.detail.video, all = S.state.styles || [];
  if (!all.length) return '';
  const st = v.style ? styleOf(v.style) : null;
  const tplNote = v.template === 'scenes' ? '장면 쌓기는 바탕 무늬·카드 모양·강조 방식·전환·이징까지 스타일을 따라가요.'
    : isFilm(v.template) ? '필름 템플릿에는 질감과 색만 입혀져요(글꼴과 움직임은 필름 그대로). 움직임까지 바꾸려면 아래에서 Claude Code에게 맡기세요.'
    : '이 템플릿에는 질감·글꼴·색이 입혀져요. 움직임까지 스타일대로 바꾸려면 아래에서 Claude Code에게 맡기세요.';
  if (!st) return `<section class="sec style-panel"><div class="sec-h"><h3>스타일</h3><span class="hint">${all.length}개 · 손그림 ${all.filter(x => x.hand).length}개</span></div>
    <p class="sec-note">잘 만든 프로덕트 모션에서 배운 결을 입혀요. 종이·그레인 같은 질감, 글꼴, 전환과 움직임 빠르기가 바뀌어요.${v.style ? ` (고른 스타일 '${esc(v.style)}' 을 찾지 못했어요)` : ''}</p>
    <div class="row-acts"><button class="btn solid small" data-act="style-pick" type="button">스타일 고르기</button></div></section>`;
  const on = (k, def) => (v[k] === undefined ? def : !!v[k]);
  return `<section class="sec style-panel"><div class="sec-h"><h3>스타일 · ${esc(st.name)}</h3><span class="hint">${esc(st.group || '')}${st.hand ? ' · 손그림' : ''}</span></div>
    <div class="style-now">${st.thumb ? `<img src="${esc(st.thumb)}" alt="">` : '<div class="noth"></div>'}
      <div><p class="sec-note" style="margin:0 0 6px">${esc(st.summary || '')}</p>${palDots(st)}
        ${(st.signature || []).length ? `<ul class="sig">${st.signature.slice(0, 3).map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}</div></div>
    <div class="style-opts">
      <label class="check"><input type="checkbox" data-type="bool" data-path="styleFonts" ${on('styleFonts', true) ? 'checked' : ''}>스타일 글꼴</label>
      <label class="check"><input type="checkbox" data-type="bool" data-path="styleColors" ${on('styleColors', false) ? 'checked' : ''}>스타일 색 (끄면 브랜드 색)</label>
      <label class="check"><input type="checkbox" data-type="bool" data-path="styleLook" ${on('styleLook', true) ? 'checked' : ''}>질감 ${st.look && st.look.length ? `<span class="hint">${esc(st.look.map(k => LOOK_NAMES[k] || k).filter((x, i, a) => a.indexOf(x) === i).join('·'))}</span>` : ''}</label></div>
    <p class="hint">${tplNote}</p>
    <div class="row-acts"><button class="btn small" data-act="style-pick" type="button">바꾸기</button>
      <button class="btn ghost small" data-act="style-card" type="button">스타일 카드 보기</button>
      <button class="btn ghost small" data-act="style-clear" type="button">스타일 빼기</button></div></section>`;
}
const LOOK_NAMES = { paper: '종이', paperTone: '종이', fiber: '종이', grain: '그레인', grainFps: '그레인', halftone: '망점', halftoneSize: '망점', dither: '디더', ditherSize: '디더',
  scanlines: '주사선', vignette: '비네트', tint: '색조', tintMode: '색조', tintAmount: '색조', frame: '액자', boil: '선 떨림', rgbSplit: '색 번짐' };
function dlgStyle() {
  const all = S.state.styles || [], v = S.detail.video;
  const f = S.styleFilter || (S.styleFilter = { group: '', hand: false, q: '' });
  let sel = v.style || '';
  const groups = STYLE_GROUPS.filter(g => all.some(x => x.group === g));
  const list = () => all.filter(x => (!f.group || x.group === f.group) && (!f.hand || x.hand)
    && (!f.q || [x.name, x.summary, (x.tags || []).join(' '), (x.fits || []).join(' ')].join(' ').toLowerCase().includes(f.q.toLowerCase())));
  const card = x => `<label class="scard"><input type="radio" name="stPick" value="${esc(x.id)}" ${x.id === sel ? 'checked' : ''}>
      ${x.thumb ? `<img src="${esc(x.thumb)}" alt="" loading="lazy">` : '<div class="noth"></div>'}
      <b>${esc(x.name)}${x.hand ? ' <em>손그림</em>' : ''}</b><span class="look">${esc(x.summary || '')}</span>
      <span class="meta">${esc(x.group || '')}${palDots(x)}</span></label>`;
  const info = () => { const x = styleOf(sel); return x ? `<b>${esc(x.name)}</b>${x.template && TEMPLATE_INFO[x.template] ? ` · 어울리는 템플릿: ${esc(TEMPLATE_INFO[x.template].name)}` : ''}${(x.fits || []).length ? ` · 어울리는 곳: ${esc(x.fits.join(', '))}` : ''}${(x.avoid || []).length ? `<br><span class="hint">피할 것: ${esc(x.avoid.join(', '))}</span>` : ''}` : '<span class="hint">스타일을 하나 골라 주세요</span>'; };
  openDlg(`<div class="dlg-h"><h2>스타일 고르기</h2><button class="icon-btn" data-close type="button" aria-label="닫기">×</button></div>
    <div class="dlg-b">
      <div class="st-filter"><button type="button" class="chipf ${!f.group ? 'on' : ''}" data-g="">전체 ${all.length}</button>${groups.map(g => `<button type="button" class="chipf ${f.group === g ? 'on' : ''}" data-g="${esc(g)}">${esc(g)} ${all.filter(x => x.group === g).length}</button>`).join('')}
        <label class="check"><input type="checkbox" id="stHand" ${f.hand ? 'checked' : ''}>손그림만</label>
        <input type="search" id="stQ" placeholder="찾기 (예: 따뜻함, 교육, 어두운)" value="${esc(f.q)}"></div>
      <div class="style-grid" id="stGrid"></div>
      <p class="st-info" id="stInfo"></p>
    </div>
    <div class="dlg-f"><button class="btn ghost" data-close type="button">취소</button><button class="btn solid" id="stUse" type="button">이 스타일 쓰기</button></div>`, true);
  const draw = () => {
    const ls = list();
    $('#stGrid').innerHTML = ls.length ? ls.map(card).join('') : '<p class="hint">맞는 스타일이 없어요</p>';
    $('#stInfo').innerHTML = info();
    $$('.chipf', $('#dlg')).forEach(b => b.classList.toggle('on', b.dataset.g === f.group));
  };
  draw();
  $('#dlg').querySelector('.st-filter').onclick = e => { const b = e.target.closest('.chipf'); if (b) { f.group = b.dataset.g; draw(); } };
  $('#stHand').onchange = e => { f.hand = e.target.checked; draw(); };
  $('#stQ').oninput = e => { f.q = e.target.value.trim(); draw(); };
  $('#stGrid').onchange = e => { if (e.target.name === 'stPick') { sel = e.target.value; $('#stInfo').innerHTML = info(); } };
  $('#stGrid').ondblclick = e => { if (e.target.closest('.scard')) $('#stUse').click(); };
  $('#stUse').onclick = () => {
    if (!sel) return toast('스타일을 하나 골라 주세요', true);
    v.style = sel; closeDlg(); changed(); renderEditor();
    toast(`스타일: ${(styleOf(sel) || {}).name || sel}`);
  };
}
async function dlgStyleCard() {
  const id = S.detail.video.style;
  try {
    const st = await api('/api/style?id=' + encodeURIComponent(id));
    openDlg(`<div class="dlg-h"><h2>${esc(st.name || id)}</h2><button class="icon-btn" data-close type="button" aria-label="닫기">×</button></div>
      <div class="dlg-b"><pre class="st-card">${esc(st.card || '(스타일 카드가 없어요)')}</pre></div>
      <div class="dlg-f"><button class="btn ghost" data-act-x="copy" type="button">복사</button><button class="btn solid" data-close type="button">닫기</button></div>`, true);
    $('[data-act-x=copy]', $('#dlg')).onclick = () => copyText(st.card || '').then(() => toast('스타일 카드를 복사했어요'));
  } catch (e) { fail(e); }
}
/* Claude 모델·노력 정도: 이 PC의 앱 전체 설정 (문구·업로드 글·사진 검색어, Claude Code 열기에 같이 쓰임) */
function modelSelect() {
  const st = S.state, ms = st.claudeModels || [], es = st.claudeEfforts || [];
  if (!ms.length) return '';
  const conn = st.claudeEngine === 'api' ? `API · ${st.claudeAccount || '키 없음'}` : 'Claude Code 로그인';
  return `<span class="model-pick"><button class="linkbtn conn" data-act="accounts" type="button" title="Claude를 무엇으로 부를지, 어느 API 계정을 쓸지 바꿔요">연결: ${esc(conn)}</button><label title="Claude에게 맡길 때 쓸 모델. 기본은 문구·연출은 Opus, 업로드 글·사진 검색어는 Sonnet. 이 PC의 모든 영상에 같이 적용돼요."><span>모델</span><select data-act="claude-model">${ms.map(([k, l]) => `<option value="${esc(k)}" ${(st.claudeModel || '') === k ? 'selected' : ''}>${esc(l)}</option>`).join('')}</select></label>
    ${es.length ? `<label title="얼마나 깊게 생각할지. 높을수록 꼼꼼하지만 느리고 사용량이 더 들어요."><span>노력</span><select data-act="claude-effort">${es.map(([k, l]) => `<option value="${esc(k)}" ${(st.claudeEffort || '') === k ? 'selected' : ''}>${esc(l)}</option>`).join('')}</select></label>` : ''}</span>`;
}
async function setClaudeOpt(kind, val) {
  try {
    const r = await api('/api/claude-model', { [kind]: val });
    S.state.claudeModel = r.claudeModel; S.state.claudeEffort = r.claudeEffort;
    const ml = (S.state.claudeModels.find(x => x[0] === r.claudeModel) || [, '기본'])[1], el = (S.state.claudeEfforts.find(x => x[0] === r.claudeEffort) || [, '기본'])[1];
    toast(`Claude 설정: 모델 ${ml} · 노력 ${el}`); renderEditor();
  } catch (e) { fail(e); }
}
function aiPanel() {
  const st = S.state;
  const v = S.detail.video;
  const open = S.aiOpen !== false;
  const aiTitle = v.template === 'scenes' ? 'Claude에게 구성·문구 맡기기' : 'Claude에게 문구 맡기기';
  if (!st.claude) return `<div class="ai closed"><div class="ai-h"><h3>${aiTitle}</h3></div><div class="hint">${st.claudeEngine === 'api' ? 'Claude API 키가 없어서 쓸 수 없어요.' : '이 컴퓨터에서 Claude Code를 찾지 못해 쓸 수 없어요.'} <button class="linkbtn" data-act="accounts" type="button">AI 계정 열기</button></div></div>`;
  return `<div class="ai ${open ? '' : 'closed'}" id="ai">
    <div class="ai-h"><h3>${aiTitle}</h3><button class="btn ghost small" data-act="ai-toggle" type="button">${open ? '접기' : '펼치기'}</button></div>
    ${S.detail.preset && (S.detail.preset.ask || []).length ? `<div class="ask"><b>${esc(S.detail.preset.name)}</b> 영상이에요. 이런 걸 적어 주면 잘 써요: ${S.detail.preset.ask.map(esc).join(' · ')}</div>` : ''}
    <textarea id="brief" data-path="brief" placeholder="${esc(S.detail.preset && S.detail.preset.brief ? S.detail.preset.brief : '무엇을 알리는 광고인지 적어 주세요. 예) 10월 한 달 체험 수업 1회 무료. 평일 저녁 7시 반, 프로필 링크로 예약')}">${esc(v.brief || '')}</textarea>
    ${LEN_TPLS.includes(v.template) ? `<div class="len-pick" role="radiogroup" aria-label="영상 길이"><span class="lbl">영상 길이</span>
      ${[['', '알아서']].concat(LENGTHS.map(n => [String(n), n + '초'])).map(([k, l]) => `<label><input type="radio" name="aiLen" value="${k}" ${String(v.target || '') === k ? 'checked' : ''}><span>${l}</span></label>`).join('')}
    </div>` : ''}
    <div class="ai-foot"><span class="hint">${v.template === 'scenes' ? '적은 내용에 맞게 장면 종류와 순서, 문구까지 짜요. 길이를 고르면 장면 수와 장면 길이를 그 길이에 맞춰요.' : LEN_TPLS.includes(v.template) ? '브랜드 말투와 규칙에 맞춰 초안을 써요. 길이를 고르면 장면 수와 장면 길이를 그 길이에 맞춰요.' : '브랜드 말투와 규칙, 연출 프롬프트에 맞춰 칸마다 들어갈 글을 써요. 움직임과 길이는 그대로예요.'}</span>
      ${modelSelect()}
      ${S.undo ? '<button class="btn ghost small" data-act="ai-undo" type="button">되돌리기</button>' : ''}
      <button class="btn solid small" data-act="ai-run" type="button">초안 받기</button></div>
  </div>`;
}

function imageOptions(cur) {
  const keys = S.detail.assets.map(a => a.key);
  const opts = keys.map(k => [k, k]);
  if (cur && !keys.includes(cur)) opts.unshift([cur, cur + ' (없음)']);
  return [['', '사진 고르기'], ...opts];
}
function assetUrl(key) {
  const a = S.detail.assets.find(x => x.key === key) || S.detail.brandAssets.find(x => x.key === key);
  return a ? a.url : null;
}
function focusPick(i, v, base = 'content.visuals') {
  const url = assetUrl(v.image);
  const f = v.focus || [.5, .5];
  return `<figure class="focus-pick" data-act="focus" data-i="${i}" data-base="${base}" title="사진에서 꼭 보여야 할 곳을 누르세요" style="margin:0">
    ${url ? `<img src="${esc(url)}" alt="" style="object-position:${f[0] * 100}% ${f[1] * 100}%"><span class="dot" style="left:${f[0] * 100}%;top:${f[1] * 100}%"></span><figcaption>눌러서 초점 정하기</figcaption>` : '<div class="empty">사진 탭에서 사진을 넣고 여기서 고르세요</div>'}</figure>`;
}

function promoEditor(c) {
  const vis = c.visuals || [];
  const hasBen = !!(c.benefits && (c.benefits.items || []).length);
  const hasProof = !!(c.proof && c.proof.number != null);
  return `
  <section class="sec"><div class="sec-h"><span class="step">1</span><h3>첫 장면</h3></div>
    <p class="sec-note">첫 2초에 멈추게 하는 장면이에요. 짧을수록 크게 보여요.</p>
    ${fText('content.hook.kicker', '작은 꼬리표', { ph: '예) 이번 주 새 원두' })}
    ${fText('content.hook.headline', '큰 문장', { multi: true, big: true, ph: '줄을 바꾸려면 Enter' })}
    <div class="row">${fText('content.hook.highlight', '형광펜 칠할 말', { hint: '큰 문장 안에 있는 말 그대로' })}${fText('content.hook.sub', '아래 작은 문장')}</div>
  </section>
  <section class="sec"><div class="sec-h"><span class="step">2</span><h3>사진 장면</h3><button class="btn ghost small" data-act="add-visual" type="button">장면 추가</button></div>
    ${vis.length ? '' : '<p class="sec-note">사진 장면이 없어요. 사진 탭에서 사진을 넣고 장면을 추가하세요.</p>'}
    ${vis.map((v, i) => `<div class="item">${itemHead(`사진 장면 ${i + 1}`, 'content.visuals', i, vis.length, `<button class="btn ghost small" data-act="auto-one" data-i="${i}" type="button" title="이 장면 문구에 맞는 무료 사진 찾기">사진 찾기</button>`)}
      <div class="item-grid">${focusPick(i, v)}<div>
        ${fSelect(`content.visuals.${i}.image`, '사진', imageOptions(v.image))}
        ${fText(`content.visuals.${i}.title`, '제목', { multi: true })}
        ${fText(`content.visuals.${i}.sub`, '설명')}
        <div class="row">${fText(`content.visuals.${i}.credit`, '출처 표시', { ph: 'Photo: 이름 · CC BY 2.0' })}${fSelect(`content.visuals.${i}.pan`, '사진 움직임', [['', '오른쪽으로'], ['left', '왼쪽으로']])}</div>
      </div></div></div>`).join('')}
  </section>
  <section class="sec ${hasBen ? '' : 'off'}"><div class="sec-h"><span class="step">3</span><h3>장점</h3>${toggleSec('benefits', hasBen)}</div>
    ${hasBen ? fText('content.benefits.title', '제목', { multi: true, rows: 2 }) + fLines('content.benefits.items', '항목', { add: '장점 추가' }) : ''}
  </section>
  <section class="sec ${hasProof ? '' : 'off'}"><div class="sec-h"><span class="step">4</span><h3>숫자로 보여 주기</h3>${toggleSec('proof', hasProof)}</div>
    ${hasProof ? `<p class="sec-note">근거 있는 숫자만 넣으세요. 숫자가 올라가며 세어져요.</p>
      <div class="row3">${fText('content.proof.number', '숫자', { num: true })}${fText('content.proof.suffix', '단위', { ph: '%, 일, 명, 년' })}${fText('content.proof.from', '세기 시작 숫자', { num: true, ph: '0' })}</div>
      ${fText('content.proof.label', '설명', { multi: true })}
      <div style="display:flex;gap:18px;flex-wrap:wrap">${fCheck('content.proof.plain', '쉼표 없이 (연도 등)')}${fCheck('content.proof.count', '세지 않고 그대로', { invert: true, def: true })}</div>` : ''}
  </section>
  <section class="sec"><div class="sec-h"><span class="step">5</span><h3>마지막 장면</h3></div>
    ${fText('content.cta.headline', '큰 문장', { multi: true, big: true })}
    <div class="row">${fText('content.cta.button', '버튼 문구')}${fText('content.cta.sub', '아래 작은 글', { ph: '@계정 · 고지 문구' })}</div>
  </section>`;
}
function toggleSec(key, on) {
  return `<label class="check"><input type="checkbox" data-act="sec-toggle" data-key="${key}" ${on ? 'checked' : ''}>넣기</label>`;
}

function beatType(b) {
  if (b.type) return b.type;
  if (b.number != null) return 'number';
  if (b.items) return 'list';
  return String(b.text || '').length > 18 ? 'line' : 'big';
}

/* 영상 길이 계산·맞추기 (템플릿의 기본 길이와 같아야 함) */
const PROMO_D = { hook: 3, visual: 2.6, benefits: 3.2, proof: 2.4, cta: 3.4 };
const KIN_D = { big: 1.9, line: 2.6, number: 2.4, list: 3.4 };
const r1 = x => Math.round(x * 10) / 10;
function totalLength(c, tpl) {
  c = c || {};
  if (tpl === 'promo') {
    const D = Object.assign({}, PROMO_D, c.durations || {});
    const hasB = !!(c.benefits && (c.benefits.items || []).length), hasP = !!(c.proof && c.proof.number != null);
    return D.hook + (c.visuals || []).length * D.visual + (hasB ? D.benefits : 0) + (hasP ? D.proof : 0) + D.cta;
  }
  if (tpl === 'kinetic') return (c.beats || []).reduce((a, b) => a + (b.dur || KIN_D[beatType(b)]), 0) + (c.ctaDur || 3.4);
  if (tpl === 'scenes') return (c.scenes || []).filter(b => b && typeof b === 'object').reduce((a, b) => a + sceneDur(b), 0) + (+c.ctaDur > 0 ? +c.ctaDur : 3.4);
  return null;
}
// 장면 길이를 같은 비율로 늘이거나 줄여 목표 길이에 맞춤. 너무 늘어지거나 급해지지 않게 0.7~1.8배 안에서만.
function fitLength(c, tpl, target) {
  const cur = totalLength(c, tpl);
  if (!cur || !target) return { total: cur, exact: false };
  const f = Math.min(1.8, Math.max(0.7, target / cur));
  if (tpl === 'promo') {
    const base = Object.assign({}, PROMO_D, c.durations || {});
    const d = {};
    for (const k of Object.keys(PROMO_D)) d[k] = r1(base[k] * f);
    c.durations = d;
    const diff = target - totalLength(c, tpl);
    if (Math.abs(diff) <= 1.2) d.cta = r1(Math.max(2.2, d.cta + diff));
  } else if (tpl === 'kinetic' || tpl === 'scenes') {
    if (tpl === 'kinetic') for (const b of c.beats || []) b.dur = r1((b.dur || KIN_D[beatType(b)]) * f);
    else for (const b of c.scenes || []) b.dur = r1(sceneDur(b) * f);
    c.ctaDur = r1((c.ctaDur || 3.4) * f);
    const diff = target - totalLength(c, tpl);
    if (Math.abs(diff) <= 1.2) c.ctaDur = r1(Math.max(2.2, c.ctaDur + diff));
  }
  const total = r1(totalLength(c, tpl));
  return { total, exact: Math.abs(total - target) < .15 };
}
const LENGTHS = [15, 20, 30, 45, 60];
const LEN_TPLS = ['promo', 'kinetic', 'scenes'];   // 장면 길이로 영상 길이를 맞추는 템플릿
function kineticEditor(c) {
  const beats = c.beats || [];
  const TYPES = [['big', '큰 글자'], ['line', '문장'], ['number', '숫자'], ['list', '목록']];
  return `
  <section class="sec"><div class="sec-h"><h3>문장 장면</h3><button class="btn ghost small" data-act="add-beat" type="button">장면 추가</button></div>
    <p class="sec-note">짧은 장면을 차례로 보여 주고 마지막 장면으로 끝나요. 큰 글자는 18자 안쪽이 보기 좋아요.</p>
    ${beats.map((b, i) => {
      const t = beatType(b);
      const p = `content.beats.${i}`;
      return `<div class="item">${itemHead(`장면 ${i + 1}`, 'content.beats', i, beats.length)}
        <div class="row">
          <div class="field"><label class="lbl" for="bt${i}">종류</label><select id="bt${i}" data-act="beat-type" data-i="${i}">${TYPES.map(([k, l]) => `<option value="${k}" ${k === t ? 'selected' : ''}>${l}</option>`).join('')}</select></div>
          ${fSelect(`${p}.scheme`, '바탕', [['', '순서대로'], ['dark', '브랜드 배경'], ['accent', '강조색'], ['paper', '밝은 바탕']])}
        </div>
        ${fText(`${p}.kicker`, '작은 꼬리표')}
        ${t === 'number' ? `<div class="row3">${fText(`${p}.prefix`, '앞말', { ph: '최대' })}${fText(`${p}.number`, '숫자', { num: true })}${fText(`${p}.suffix`, '단위', { ph: '%' })}</div>
            <div style="display:flex;gap:18px;margin-bottom:12px">${fCheck(`${p}.count`, '세지 않고 그대로', { invert: true, def: true })}${fCheck(`${p}.plain`, '쉼표 없이')}</div>`
          : fText(`${p}.text`, t === 'list' ? '목록 제목' : '문장', { multi: t !== 'list', big: t === 'big' })}
        ${t === 'big' || t === 'line' ? fText(`${p}.highlight`, t === 'big' ? '색 바꿀 단어' : '형광펜 칠할 말') : ''}
        ${t === 'list' ? fLines(`${p}.items`, '항목') : ''}
        ${fText(`${p}.sub`, '아래 작은 문장')}
      </div>`;
    }).join('')}
  </section>
  <section class="sec"><div class="sec-h"><h3>마지막 장면</h3></div>
    ${fText('content.cta.headline', '큰 문장', { multi: true, big: true })}
    <div class="row">${fText('content.cta.button', '버튼 문구')}${fText('content.cta.sub', '아래 작은 글', { ph: '@계정 · 고지 문구' })}</div>
  </section>`;
}

/* 장면 쌓기 (scenes 템플릿) */
const SCENE_TYPES = [['title', '표지'], ['text', '문장'], ['photo', '사진'], ['number', '숫자'], ['list', '목록'], ['steps', '단계'], ['compare', '비교'], ['quote', '인용'], ['chart', '막대 그래프'], ['gallery', '사진 여러 장'], ['logo', '로고']];
const SCHEMES_KO = [['', '순서대로'], ['dark', '브랜드 배경'], ['accent', '강조색'], ['paper', '밝은 바탕']];
// 아직 안 쓴 사진 키 (사진 탭에 넣었지만 장면에 안 쓴 것 → 없으면 photo1 같은 빈 자리)
function strings(o, out = new Set()) {
  if (typeof o === 'string') out.add(o);
  else if (Array.isArray(o)) o.forEach(x => strings(x, out));
  else if (o && typeof o === 'object') Object.values(o).forEach(x => strings(x, out));
  return out;
}
function freePhotoKeys(n) {
  const used = strings(S.detail.video.content || {});
  const out = S.detail.assets.map(a => a.key).filter(k => !used.has(k));
  let k = 1;
  const taken = new Set([...used, ...S.detail.assets.map(a => a.key)]);
  while (out.length < n) { while (taken.has('photo' + k)) k++; out.push('photo' + k); taken.add('photo' + k); }
  return out.slice(0, n);
}
const SCENE_NEW = {
  title: () => ({ type: 'title', kicker: '', text: '', sub: '' }),
  text: () => ({ type: 'text', text: '' }),
  photo: () => ({ type: 'photo', image: freePhotoKeys(1)[0], text: '', sub: '' }),
  number: () => ({ type: 'number', number: '', suffix: '', text: '' }),
  list: () => ({ type: 'list', text: '', items: ['', '', ''] }),
  steps: () => ({ type: 'steps', text: '', items: ['', '', ''] }),
  compare: () => ({ type: 'compare', text: '', leftLabel: '지금까지', left: '', rightLabel: '이제는', right: '' }),
  quote: () => ({ type: 'quote', text: '', by: '', role: '' }),
  chart: () => ({ type: 'chart', text: '', unit: '', bars: [['', 0], ['', 0], ['', 0]] }),
  gallery: () => ({ type: 'gallery', text: '', images: freePhotoKeys(3) }),
  logo: () => ({ type: 'logo', text: '' }),
};
function sceneType(b) {   // templates/scenes 와 같은 규칙
  if (SCENE_TYPES.some(x => x[0] === b.type)) return b.type;
  if (b.number != null && b.number !== '') return 'number';
  if (Array.isArray(b.items) && b.items.length) return 'list';
  if (b.bars) return 'chart';
  if (b.images) return 'gallery';
  return 'text';
}
const sceneName = b => (SCENE_TYPES.find(x => x[0] === sceneType(b)) || [, '장면'])[1];
function sceneDur(b) {     // templates/scenes 의 defDur 와 같은 식
  if (+b.dur > 0) return +b.dur;
  const L = x => Array.isArray(x) ? x.length : 0;
  const t = sceneType(b), n = t === 'chart' ? L(b.bars) : t === 'gallery' ? L(b.images) : L(b.items);
  if (t === 'text') { const sz = b.size === 'big' || b.size === 'line' ? b.size : lenOf(b.text) > 18 ? 'line' : 'big'; return sz === 'big' ? 1.9 : 2.6; }
  return { title: 2.6, photo: 2.8, number: 2.4, list: 2 + .45 * Math.min(n, 6), steps: 2 + .45 * Math.min(n, 5), compare: 3.4, quote: 3.6,
    chart: 2.4 + .2 * Math.min(n, 7), gallery: 2.2 + .35 * Math.min(n, 4), logo: 2.2 }[t];
}
function barsField(p, b) {
  const bars = b.bars || [];
  return `<div class="field arr"><span class="lbl">막대 (이름 · 값, 7개까지 · 마지막 막대가 강조돼요)</span>${bars.map((x, i) => `<div class="bar-row">${fText(`${p}.bars.${i}.0`, '이름', { ph: '예) 2025' })}${fText(`${p}.bars.${i}.1`, '값', { ph: '1,200' })}
      <button class="icon-btn" data-act="del" data-path="${p}.bars" data-i="${i}" type="button" title="빼기" aria-label="막대 빼기">×</button></div>`).join('')}
    ${bars.length < 7 ? `<button class="btn ghost small add-line" data-act="add-item" data-path="${p}.bars" type="button">막대 추가</button>` : ''}</div>`;
}
function galleryField(p, b) {
  const ims = b.images || [];
  return `<div class="field"><span class="lbl">사진 (4장까지, 순서대로)</span><div class="row">${ims.map((k, i) => `<div class="gal-pick">${fSelect(`${p}.images.${i}`, `${i + 1}`, filmPhotoOptions(k))}
      <button class="icon-btn" data-act="del" data-path="${p}.images" data-i="${i}" type="button" title="빼기" aria-label="사진 칸 빼기">×</button></div>`).join('')}</div>
    ${ims.length < 4 ? `<button class="btn ghost small add-line" data-act="scene-img-add" data-i="${p.split('.').pop()}" type="button">사진 칸 추가</button>` : ''}</div>`;
}
function scenesEditor(c) {
  const sc = c.scenes || [];
  const items = sc.map((b, i) => {
    const t = sceneType(b), p = `content.scenes.${i}`;
    const K = fText(`${p}.kicker`, '작은 꼬리표');
    const BG = `<div class="row">${fSelect(`${p}.image`, '바탕 사진 (선택)', filmPhotoOptions(b.image))}${b.image ? fText(`${p}.credit`, '사진 출처 표시', { ph: 'Photo: 이름 · CC BY 2.0' }) : '<div class="field"></div>'}</div>`;
    let f = '';
    if (t === 'title') f = K + fText(`${p}.text`, '제목', { multi: true, big: true }) + `<div class="row">${fText(`${p}.highlight`, '색 바꿀 단어')}${fText(`${p}.sub`, '아랫줄')}</div>` + BG;
    if (t === 'text') f = K + fText(`${p}.text`, '문장', { multi: true, big: true, hint: '18자 안쪽이면 단어가 크게 박히고, 길면 형광펜 문장이 돼요' })
      + `<div class="row">${fText(`${p}.highlight`, '강조할 말')}${fSelect(`${p}.size`, '글자 크기', [['', '자동'], ['big', '아주 크게'], ['line', '문장 (형광펜)']])}</div>` + fText(`${p}.sub`, '아랫줄') + BG;
    if (t === 'photo') f = `<div class="item-grid">${focusPick(i, b, 'content.scenes')}<div>
        <div class="row">${fSelect(`${p}.image`, '사진', filmPhotoOptions(b.image))}${fSelect(`${p}.layout`, '배치', [['', '사진 가득'], ['split', '사진과 글 나눔']])}</div>
        ${K}${fText(`${p}.text`, '제목', { multi: true })}${fText(`${p}.sub`, '설명')}
        <div class="row">${fText(`${p}.credit`, '출처 표시', { ph: 'Photo: 이름 · CC BY 2.0' })}${fSelect(`${p}.pan`, '사진 움직임', [['', '오른쪽으로'], ['left', '왼쪽으로']])}</div></div></div>`;
    if (t === 'number') f = K + `<div class="row3">${fText(`${p}.prefix`, '앞말', { ph: '최대' })}${fText(`${p}.number`, '숫자', { ph: '1,250' })}${fText(`${p}.suffix`, '단위', { ph: '%' })}</div>`
      + fText(`${p}.text`, '설명', { multi: true }) + fText(`${p}.sub`, '아랫줄 (근거·기준)')
      + `<div style="display:flex;gap:18px;margin-bottom:12px">${fCheck(`${p}.count`, '세지 않고 그대로', { invert: true, def: true })}${fCheck(`${p}.plain`, '쉼표 없이 (연도 등)')}</div>` + BG;
    if (t === 'list' || t === 'steps') f = K + fText(`${p}.text`, t === 'list' ? '목록 제목' : '제목')
      + fLines(`${p}.items`, t === 'list' ? '항목 (6개까지)' : '단계 (5개까지)', { add: t === 'list' ? '항목 추가' : '단계 추가' }) + BG;
    if (t === 'compare') f = K + fText(`${p}.text`, '제목') + `<div class="row">${fText(`${p}.leftLabel`, '왼쪽 딱지', { ph: '지금까지' })}${fText(`${p}.rightLabel`, '오른쪽 딱지', { ph: '이제는' })}</div>
      <div class="row">${fText(`${p}.left`, '왼쪽 (전)', { multi: true })}${fText(`${p}.right`, '오른쪽 (후)', { multi: true })}</div>` + BG;
    if (t === 'quote') f = fText(`${p}.text`, '인용 (실제로 한 말만)', { multi: true, rows: 3 })
      + `<div class="row">${fText(`${p}.by`, '말한 사람')}${fText(`${p}.role`, '직함·소속')}</div><div class="row">${fText(`${p}.highlight`, '강조할 말')}${fSelect(`${p}.image`, '얼굴 사진 (선택)', filmPhotoOptions(b.image))}</div>`
      + (b.image ? fText(`${p}.credit`, '사진 출처 표시') : '');
    if (t === 'chart') f = K + `<div class="row">${fText(`${p}.text`, '제목')}${fText(`${p}.unit`, '단위', { ph: '억, %, 명' })}</div>` + barsField(p, b) + fText(`${p}.sub`, '아랫줄 (출처·기준)') + BG;
    if (t === 'gallery') f = K + fText(`${p}.text`, '제목') + galleryField(p, b) + fText(`${p}.credit`, '출처 표시') + fText(`${p}.sub`, '아랫줄');
    if (t === 'logo') f = '<p class="hint" style="margin-top:0">계정 설정의 로고를 크게 보여 줘요.</p>' + fText(`${p}.text`, '로고 아래 한 줄') + fText(`${p}.sub`, '아랫줄') + BG;
    const fullPhoto = t === 'photo' && b.image && b.layout !== 'split';
    return `<div class="item scene-item" id="sc${i}">${itemHead(`${i + 1}. ${sceneName(b)}`, 'content.scenes', i, sc.length, `<button class="btn ghost small" data-act="scene-dup" data-i="${i}" type="button" title="이 장면을 바로 아래에 복사">복사</button>`)}
      <div class="row"><div class="field"><label class="lbl" for="st${i}">종류</label><select id="st${i}" data-act="scene-type" data-i="${i}">${SCENE_TYPES.map(([k, l]) => `<option value="${k}" ${k === t ? 'selected' : ''}>${l}</option>`).join('')}</select></div>
        ${fullPhoto ? '<div class="field"></div>' : fSelect(`${p}.scheme`, '바탕', SCHEMES_KO)}</div>
      ${f}</div>`;
  }).join('');
  return `<section class="sec"><div class="sec-h"><h3>장면</h3><span class="len-now">${sc.length}개 · ${r1(totalLength(c, 'scenes'))}초</span></div>
    <p class="sec-note">위에서부터 차례로 보여 주고 마지막 장면으로 끝나요. 종류를 바꿔도 큰 글은 그대로 남아요.</p>
    ${items || '<p class="sec-note">아직 장면이 없어요. 아래에서 장면을 더하거나, 위의 Claude에게 맡기기로 구성을 받아 보세요.</p>'}
    <div class="scene-add"><span class="lbl">장면 더하기</span><div>${SCENE_TYPES.map(([k, l]) => `<button class="btn small" data-act="scene-add" data-t="${k}" type="button">＋ ${l}</button>`).join('')}</div></div>
  </section>
  <section class="sec"><div class="sec-h"><h3>마지막 장면</h3></div>
    ${fText('content.cta.headline', '큰 문장', { multi: true, big: true })}
    <div class="row">${fText('content.cta.button', '버튼 문구')}${fText('content.cta.sub', '아래 작은 글', { ph: '@계정 · 주소' })}</div>
    ${fText('content.note', '맨 아래 작은 안내 (선택)', { ph: '예) 유료 광고 포함' })}
  </section>`;
}
function setSceneType(i, t) {
  const b = S.detail.video.content.scenes[i], nb = SCENE_NEW[t](), own = ['photo', 'quote', 'gallery'];
  if (own.includes(sceneType(b)) && !own.includes(t)) for (const k of ['image', 'credit', 'focus', 'layout', 'pan']) delete b[k];
  for (const [k, x] of Object.entries(nb)) if (k === 'type' || b[k] === undefined) b[k] = x;
  if ((t === 'list' || t === 'steps') && !(b.items || []).length) b.items = ['', ''];
  changed(); renderEditor();
}

/* ---------------------------------------------------------------- 발표 자료 (deck 템플릿) */
const SLIDE_TYPES = [['cover', '표지'], ['agenda', '목차'], ['section', '구분'], ['bullets', '글머리'], ['cards', '카드'], ['statement', '한 문장'], ['number', '숫자'],
  ['stats', '숫자 여러 개'], ['chart', '막대 그래프'], ['compare', '비교'], ['steps', '단계·일정'], ['image', '사진'], ['quote', '인용'], ['closing', '마무리']];
const DECK_MIN = [5, 10, 15, 20, 30];
const isDeck = () => !!(S.detail && S.detail.video.template === 'deck');
const slideType = b => SLIDE_TYPES.some(x => x[0] === b.type) ? b.type : (Array.isArray(b.items) && b.items.length ? 'bullets' : 'statement');
const slideName = b => (SLIDE_TYPES.find(x => x[0] === slideType(b)) || [, '장'])[1];
const SLIDE_NEW = {
  cover: () => ({ type: 'cover', kicker: '', title: '', sub: '' }),
  agenda: () => ({ type: 'agenda', title: '목차', items: ['', '', ''] }),
  section: () => ({ type: 'section', title: '', sub: '' }),
  bullets: () => ({ type: 'bullets', title: '', items: ['', '', ''] }),
  cards: () => ({ type: 'cards', title: '', items: ['', '', ''] }),
  statement: () => ({ type: 'statement', text: '', highlight: '' }),
  number: () => ({ type: 'number', number: '', suffix: '', text: '' }),
  stats: () => ({ type: 'stats', title: '', stats: [['', ''], ['', ''], ['', '']] }),
  chart: () => ({ type: 'chart', title: '', unit: '', bars: [['', 0], ['', 0], ['', 0]] }),
  compare: () => ({ type: 'compare', title: '', leftLabel: '지금', left: '', rightLabel: '앞으로', right: '' }),
  steps: () => ({ type: 'steps', title: '', items: ['', '', ''] }),
  image: () => ({ type: 'image', image: freePhotoKeys(1)[0], layout: 'split', title: '', text: '' }),
  quote: () => ({ type: 'quote', text: '', by: '', role: '' }),
  closing: () => ({ type: 'closing', title: '감사합니다', sub: '' }),
};
function deckAiPanel() {
  const st = S.state, v = S.detail.video, d = S.detail;
  if (!st.claude) return `<div class="ai closed"><div class="ai-h"><h3>Claude에게 구성·문구 맡기기</h3></div><div class="hint">${st.claudeEngine === 'api' ? 'Claude API 키가 없어서 쓸 수 없어요.' : '이 컴퓨터에서 Claude Code를 찾지 못해 쓸 수 없어요.'} <button class="linkbtn" data-act="accounts" type="button">AI 계정 열기</button></div></div>`;
  const open = S.aiOpen !== false;
  return `<div class="ai ${open ? '' : 'closed'}" id="ai">
    <div class="ai-h"><h3>Claude에게 구성·문구 맡기기</h3><button class="btn ghost small" data-act="ai-toggle" type="button">${open ? '접기' : '펼치기'}</button></div>
    <textarea id="brief" data-path="brief" placeholder="무슨 발표인지 적어 주세요. 누구 앞에서, 무엇을 말하고, 듣는 사람이 무엇을 하길 바라는지. 예) 다음 주 팀장 회의. 3분기 성과(연결 설비 1,240곳, 정확도 92%)와 하반기 계획 세 가지, 일정은 10월~1월">${esc(v.brief || '')}</textarea>
    <div class="deck-src">${d.source ? `<span class="src-chip" title="Claude가 이 자료를 바탕으로 짜요">자료: <b>${esc(d.source.file)}</b> · 글 ${d.source.chars.toLocaleString()}자</span>
        <button class="btn ghost small" data-act="deck-source-remove" type="button">빼기</button>` : '<span class="hint">가진 자료가 있으면 넣어 주세요. 그 내용으로 발표를 다시 짜요.</span>'}
      <label class="btn small">${d.source ? '다른 자료' : '자료 넣기'}<input type="file" data-act="deck-source" accept=".pptx,.pdf,.docx,.hwpx,.txt,.md" hidden></label>
      <span class="hint">PPTX · PDF · DOCX · HWPX · TXT</span></div>
    <div class="len-pick" role="radiogroup" aria-label="발표 시간"><span class="lbl">발표 시간</span>
      ${[['', '알아서']].concat(DECK_MIN.map(n => [String(n), n + '분'])).map(([k, l]) => `<label><input type="radio" name="aiLen" value="${k}" ${String(v.target || '') === k ? 'checked' : ''}><span>${l}</span></label>`).join('')}
    </div>
    <div class="ai-foot"><span class="hint">요청${d.source ? '과 자료' : ''}에 맞게 장 구성(표지·목차·구분·숫자·그래프 …)과 화면 글, 발표 메모까지 짜요. 숫자와 사실은 적은 것만 써요.</span>
      ${modelSelect()}
      ${S.undo ? '<button class="btn ghost small" data-act="ai-undo" type="button">되돌리기</button>' : ''}
      <button class="btn solid small" data-act="ai-run" type="button">초안 받기</button></div>
  </div>`;
}
function pairsField(p, b, key, label, max, ph) {
  const rows = Array.isArray(b[key]) ? b[key] : [];
  return `<div class="field arr"><span class="lbl">${esc(label)}</span>${rows.map((x, i) => `<div class="bar-row">${fText(`${p}.${key}.${i}.0`, ph[0], { ph: ph[2] })}${fText(`${p}.${key}.${i}.1`, ph[1], { ph: ph[3] })}
      <button class="icon-btn" data-act="del" data-path="${p}.${key}" data-i="${i}" type="button" title="빼기" aria-label="빼기">×</button></div>`).join('')}
    ${rows.length < max ? `<button class="btn ghost small add-line" data-act="add-item" data-path="${p}.${key}" type="button">추가</button>` : ''}</div>`;
}
function deckEditor(c) {
  const sl = c.slides || [];
  const items = sl.map((b, i) => {
    const t = slideType(b), p = `content.slides.${i}`;
    const K = fText(`${p}.kicker`, '작은 꼬리표 (선택)');
    const T = (lab = '제목') => fText(`${p}.title`, lab, { multi: true });
    const PIPE = '"머리말 | 설명" 처럼 | 로 나누면 두 줄로 보여요';
    let f = '';
    if (t === 'cover') f = K + fText(`${p}.title`, '발표 제목', { multi: true, big: true }) + `<div class="row">${fText(`${p}.highlight`, '색 바꿀 단어')}${fText(`${p}.sub`, '발표자 · 날짜')}</div>`;
    if (t === 'agenda') f = T('목차 제목') + fLines(`${p}.items`, '항목 (10개까지)', { add: '항목 추가' });
    if (t === 'section') f = `<div class="row">${fText(`${p}.title`, '구분 제목')}${fText(`${p}.number`, '번호', { ph: '자동 (01, 02 …)' })}</div>` + fText(`${p}.sub`, '아랫줄');
    if (t === 'bullets') f = K + T() + fLines(`${p}.items`, '항목 (7개까지)', { add: '항목 추가', hint: PIPE }) + fText(`${p}.sub`, '출처·기준 (선택)');
    if (t === 'cards') f = K + T() + fLines(`${p}.items`, '카드 (3~6개, "카드 제목 | 설명")', { add: '카드 추가' }) + fText(`${p}.sub`, '출처·기준 (선택)');
    if (t === 'statement') f = K + fText(`${p}.text`, '한 문장', { multi: true, big: true }) + `<div class="row">${fText(`${p}.highlight`, '강조할 말')}${fText(`${p}.sub`, '아랫줄')}</div>`;
    if (t === 'number') f = K + fText(`${p}.title`, '위 작은 글 (선택)') + `<div class="row3">${fText(`${p}.prefix`, '앞말', { ph: '약' })}${fText(`${p}.number`, '숫자', { ph: '1240' })}${fText(`${p}.suffix`, '단위', { ph: '곳' })}</div>`
      + fText(`${p}.text`, '숫자 뜻') + fText(`${p}.sub`, '출처·기준') + `<div style="display:flex;gap:18px;margin-bottom:12px">${fCheck(`${p}.count`, '세지 않고 그대로', { invert: true, def: true })}${fCheck(`${p}.plain`, '쉼표 없이 (연도 등)')}</div>`;
    if (t === 'stats') f = T() + pairsField(p, b, 'stats', '숫자 (4개까지 · 마지막이 강조돼요)', 4, ['값', '설명', '1,240곳', '연결된 설비']) + fText(`${p}.sub`, '출처·기준');
    if (t === 'chart') f = `<div class="row">${fText(`${p}.title`, '제목')}${fText(`${p}.unit`, '단위', { ph: '억, %, 명' })}</div>` + pairsField(p, b, 'bars', '막대 (8개까지 · 마지막 막대가 강조돼요)', 8, ['이름', '값', '1분기', '420']) + fText(`${p}.sub`, '출처·기준');
    if (t === 'compare') f = T() + `<div class="row">${fText(`${p}.leftLabel`, '왼쪽 딱지', { ph: '지금' })}${fText(`${p}.rightLabel`, '오른쪽 딱지', { ph: '앞으로' })}</div>
      <div class="row">${fText(`${p}.left`, '왼쪽 (줄마다 한 항목)', { multi: true, rows: 4 })}${fText(`${p}.right`, '오른쪽 (줄마다 한 항목)', { multi: true, rows: 4 })}</div>`;
    if (t === 'steps') f = T() + fLines(`${p}.items`, '단계 (5개까지, "10월 | 설계")', { add: '단계 추가' }) + fText(`${p}.sub`, '아랫줄 (선택)');
    if (t === 'image') f = `<div class="item-grid">${focusPick(i, b, 'content.slides')}<div>
        <div class="row">${fSelect(`${p}.image`, '사진', filmPhotoOptions(b.image))}${fSelect(`${p}.layout`, '배치', [['split', '왼쪽 사진 · 오른쪽 글'], ['full', '사진 가득']])}</div>
        ${K}${T()}${fText(`${p}.text`, '설명 (짧은 문단)', { multi: true })}${fText(`${p}.credit`, '출처 표시', { ph: 'Photo: 이름 · CC BY 2.0' })}</div></div>`;
    if (t === 'quote') f = fText(`${p}.text`, '인용 (실제로 한 말만)', { multi: true, rows: 3 }) + `<div class="row">${fText(`${p}.by`, '말한 사람')}${fText(`${p}.role`, '직함·소속')}</div>
      <div class="row">${fText(`${p}.highlight`, '강조할 말')}${fSelect(`${p}.image`, '얼굴 사진 (선택)', filmPhotoOptions(b.image))}</div>`;
    if (t === 'closing') f = fText(`${p}.title`, '큰 글', { multi: true }) + fText(`${p}.sub`, '아랫줄 (연락처·질문 안내)');
    return `<div class="item scene-item" id="sl${i}">${itemHead(`${i + 1}. ${slideName(b)}`, 'content.slides', i, sl.length, `<button class="btn ghost small" data-act="slide-dup" data-i="${i}" type="button" title="이 장을 바로 아래에 복사">복사</button><button class="btn ghost small" data-act="slide-go" data-i="${i}" type="button" title="미리보기에서 이 장 보기">보기</button>`)}
      <div class="row"><div class="field"><label class="lbl" for="slt${i}">종류</label><select id="slt${i}" data-act="slide-type" data-i="${i}">${SLIDE_TYPES.map(([k, l]) => `<option value="${k}" ${k === t ? 'selected' : ''}>${l}</option>`).join('')}</select></div><div class="field"></div></div>
      ${f}${fText(`${p}.notes`, '발표 메모 (화면에는 안 나와요)', { multi: true, rows: 2 })}</div>`;
  }).join('');
  return `<section class="sec"><div class="sec-h"><h3>발표 정보</h3></div>
    <div class="row">${fText('content.title', '발표 제목 (바닥글에 보여요)')}${fSelect('content.scheme', '바탕', [['', '스타일대로'], ['dark', '브랜드 배경'], ['paper', '밝은 바탕']])}</div></section>
  <section class="sec"><div class="sec-h"><h3>장</h3><span class="len-now">${sl.length}장</span></div>
    <p class="sec-note">위에서부터 한 장씩 넘어가요. 넘길 때마다 그 장의 글과 숫자가 움직이며 들어오고, 강조색 도형이 장을 따라 모양을 바꿔요.</p>
    ${items || '<p class="sec-note">아직 장이 없어요. 아래에서 장을 더하거나, 위의 Claude에게 맡기기로 구성을 받아 보세요.</p>'}
    <div class="scene-add"><span class="lbl">장 더하기</span><div>${SLIDE_TYPES.map(([k, l]) => `<button class="btn small" data-act="slide-add" data-t="${k}" type="button">＋ ${l}</button>`).join('')}</div></div>
  </section>`;
}
function setSlideType(i, t) {
  const b = S.detail.video.content.slides[i], nb = SLIDE_NEW[t]();
  // 큰 글은 옮겨 둠 (title ↔ text)
  if (!b.title && b.text && t !== 'statement' && t !== 'quote') { b.title = b.text; delete b.text; }
  if (!b.text && b.title && (t === 'statement' || t === 'quote')) { b.text = b.title; delete b.title; }
  for (const [k, x] of Object.entries(nb)) if (k === 'type' || b[k] === undefined) b[k] = x;
  changed(); renderEditor();
}
function normSlides(c) {
  if (!c || !Array.isArray(c.slides)) { if (c) c.slides = []; return c; }
  const strs = x => Array.isArray(x) ? x.filter(y => y != null && typeof y !== 'object').map(String) : typeof x === 'string' ? x.split('\n').filter(Boolean) : [];
  const pairs = x => Array.isArray(x) ? x.filter(y => Array.isArray(y)).map(y => [String(y[0] ?? ''), y[1] ?? '']) : [];
  c.slides = c.slides.filter(b => b && typeof b === 'object' && !Array.isArray(b)).map(b => {
    if (b.items !== undefined) b.items = strs(b.items);
    if (b.stats !== undefined) b.stats = pairs(b.stats).map(y => [y[0], String(y[1])]);
    if (b.bars !== undefined) b.bars = pairs(b.bars);
    for (const k of ['title', 'text', 'sub', 'kicker', 'left', 'right', 'by', 'role', 'notes', 'highlight', 'number']) if (b[k] != null && typeof b[k] !== 'string') b[k] = Array.isArray(b[k]) ? b[k].join('\n') : String(b[k]);
    return b;
  });
  return c;
}
function summarizeDeck(c) {
  return (c.slides || []).map((b, i) => {
    const t = slideType(b);
    const main = t === 'number' ? `${b.prefix || ''}${b.number || ''}${b.suffix || ''}${b.text ? '  ' + b.text : ''}` : (b.title || b.text || '');
    const extra = t === 'compare' ? [`${b.leftLabel || '왼쪽'}: ${(b.left || '').replace(/\n/g, ' · ')}`, `${b.rightLabel || '오른쪽'}: ${(b.right || '').replace(/\n/g, ' · ')}`]
      : t === 'chart' ? [(b.bars || []).map(x => `${x[0]} ${x[1]}${b.unit || ''}`).join(' · ')]
      : t === 'stats' ? [(b.stats || []).map(x => `${x[0]} ${x[1]}`).join(' · ')]
      : t === 'quote' ? [[b.by, b.role].filter(Boolean).join(' · ')] : t === 'image' ? [`사진: ${b.image || '없음'}`] : [];
    return `<div class="scene"><b>${i + 1}. ${esc(slideName(b))}</b><div>${esc([b.kicker, main, ...(b.items || []).map(x => '· ' + x), ...extra, b.sub].filter(Boolean).join('\n'))}${b.notes ? `<div class="hint" style="margin-top:4px">메모: ${esc(b.notes)}</div>` : ''}</div></div>`;
  }).join('');
}
async function addDeckSource(file) {
  if (!file) return;
  try {
    saveVideo.flush();
    toast('자료에서 글을 뽑는 중이에요');
    const up = await upload(file);
    const r = await api('/api/deck/source', { name: S.detail.name, upload: up.id });
    S.detail = r; renderEditor();
    toast(`자료를 넣었어요 · 글 ${r.added.chars.toLocaleString()}자${r.added.images.length ? `, 그림 ${r.added.images.length}장 (사진 탭)` : ''}. 이제 초안 받기를 눌러 주세요`);
  } catch (e) { fail(e); }
}
function deckGo(i) {   // 미리보기에서 그 장으로 (iframe 주소의 #번호)
  try { const w = $('#frame iframe').contentWindow; w.location.hash = '#' + (i + 1); w.location.reload(); } catch (e) { /* 미리보기가 아직 없음 */ }
}
async function deckPdf() {
  saveVideo.flush();
  try {
    const job = await api('/api/job/deck-pdf', { name: S.detail.name });
    toast('PDF를 만드는 중이에요. 장마다 등장이 끝난 화면을 모아요');
    trackJob(job, j => {
      if (j.status !== 'done') return;
      openDlg(`<div class="dlg-h"><h2>PDF를 만들었어요</h2><button class="icon-btn" data-close type="button" aria-label="닫기">×</button></div>
        <div class="dlg-b"><p>장마다 마지막 화면을 한 쪽씩 모았어요. 나눠 주거나 인쇄할 때 써요.</p><p class="hint">${esc(j.result.path)}</p></div>
        <div class="dlg-f"><button class="btn ghost" data-close type="button">닫기</button><a class="btn" href="${esc(j.result.url)}" target="_blank" rel="noopener">PDF 보기</a><button class="btn solid" id="pdfFolder" type="button">폴더 열기</button></div>`);
      $('#pdfFolder').onclick = () => api('/api/open', { path: `out/${S.detail.name}/wide` }).catch(fail);
      selectVideo(S.detail.name);
    });
  } catch (e) { fail(e); }
}
async function deckPptx() {
  saveVideo.flush();
  try {
    const job = await api('/api/job/deck-pptx', { name: S.detail.name });
    toast('PPT를 만드는 중이에요. 글꼴을 파일에 넣느라 1~2분 걸려요');
    trackJob(job, j => {
      if (j.status !== 'done') return;
      openDlg(`<div class="dlg-h"><h2>PPT를 만들었어요</h2><button class="icon-btn" data-close type="button" aria-label="닫기">×</button></div>
        <div class="dlg-b"><p>글과 도형을 PowerPoint에서 바로 고칠 수 있어요. 장이 열리면 글과 항목이 차례로 들어오고, 장 사이는 '모핑' 전환으로 강조 도형이 모양을 바꿔요. 발표 메모는 슬라이드 노트에 들어 있어요.</p>
          <p class="hint">${esc(j.result.path)}</p></div>
        <div class="dlg-f"><button class="btn ghost" data-close type="button">닫기</button><button class="btn" id="pxFolder" type="button">폴더 열기</button><button class="btn solid" id="pxOpen" type="button">PowerPoint로 열기</button></div>`);
      $('#pxFolder').onclick = () => api('/api/open', { path: `out/${S.detail.name}/wide` }).catch(fail);
      $('#pxOpen').onclick = () => api('/api/deck/open-file', { name: S.detail.name, kind: 'pptx' }).catch(fail);
      selectVideo(S.detail.name);
    });
  } catch (e) { fail(e); }
}
async function deckPresent() {
  saveVideo.flush();
  try { await api('/api/deck/present', { name: S.detail.name }); toast('브라우저에서 열었어요. F5를 누르면 전체 화면, 클리커나 → 로 넘겨요'); } catch (e) { fail(e); }
}
function dlgNewDeck(brand) {
  const st = S.state;
  openDlg(`<div class="dlg-h"><h2>발표 자료 추가</h2><button class="icon-btn" data-close type="button" aria-label="닫기">×</button></div>
    <form id="ndForm"><div class="dlg-b">
      <p class="hint" style="margin-top:0">넘길 때마다 한 장씩 모션으로 등장하는 16:9 발표 자료예요. 클리커로 넘기고, PDF로도 뽑을 수 있어요.</p>
      <div class="field"><label class="lbl" for="ndBrief">무슨 발표인가요?</label>
        <textarea id="ndBrief" rows="4" placeholder="누구 앞에서, 무엇을 말하고, 듣는 사람이 무엇을 하길 바라는지. 숫자나 날짜가 있으면 같이 적어 주세요."></textarea></div>
      <div class="field"><span class="lbl">가진 자료 (선택)</span><input type="file" id="ndFile" accept=".pptx,.pdf,.docx,.hwpx,.txt,.md">
        <span class="hint">PPTX · PDF · DOCX · HWPX · TXT. 넣으면 그 내용으로 다시 짜요(PPTX·DOCX 안 그림은 사진으로 들어가요).</span></div>
      <div class="len-pick" role="radiogroup" aria-label="발표 시간"><span class="lbl">발표 시간</span>
        ${[['', '알아서']].concat(DECK_MIN.map(n => [String(n), n + '분'])).map(([k, l], i) => `<label><input type="radio" name="ndLen" value="${k}" ${i === 2 ? 'checked' : ''}><span>${l}</span></label>`).join('')}</div>
      <div class="field"><label class="lbl" for="ndBrand">계정</label><select id="ndBrand">${st.brands.map(b => `<option value="${esc(b.slug)}" ${b.slug === brand ? 'selected' : ''}>${esc(b.name)}</option>`).join('')}</select></div>
      <div class="row"><div class="field"><label class="lbl" for="ndTitle">발표 제목</label><input id="ndTitle" type="text" required placeholder="예) 하반기 계획 보고"></div>
      <div class="field"><label class="lbl" for="ndName">영문 이름</label><input id="ndName" type="text" required pattern="[a-z0-9][a-z0-9\\-]*" value="${esc(suggestSlug((brand || 'deck') + '-deck'))}"></div></div>
      <label class="check"><input type="checkbox" id="ndAI" ${st.claude ? 'checked' : 'disabled'}>만들고 바로 Claude에게 구성·문구 맡기기${st.claude ? '' : ' (AI 계정이 필요해요)'}</label>
    </div>
    <div class="dlg-f"><button class="btn ghost" data-close type="button">취소</button><button class="btn solid" type="submit">만들기</button></div></form>`, true);
  $('#ndBrand').onchange = e => { $('#ndName').value = suggestSlug(e.target.value + '-deck'); };
  $('#ndForm').onsubmit = async e => {
    e.preventDefault();
    const brief = ($('#ndBrief').value || '').trim(), file = $('#ndFile').files[0], ai = $('#ndAI').checked;
    if (ai && brief.length < 5 && !file) { $('#ndBrief').focus(); return toast('무슨 발표인지 한두 문장 적거나 자료를 넣어 주세요', true); }
    const btn = $('#ndForm [type=submit]'); btn.disabled = true; btn.textContent = '만드는 중…';
    try {
      const title = $('#ndTitle').value.trim(), len = ($('[name=ndLen]:checked') || {}).value;
      const r = await api('/api/video/create', { name: $('#ndName').value.trim(), brand: $('#ndBrand').value, formats: ['wide'], title, template: 'deck' });
      closeDlg();
      await refreshState();
      S.tab = 'copy'; S.aiOpen = true; S.fmt = 'wide';
      await selectVideo(r.name);
      const v = S.detail.video;
      v.brief = brief || `${title} 발표`; if (len) v.target = +len;
      v.content = Object.assign({}, v.content, { title });
      changed(); await saveVideo.flush();
      if (file) await addDeckSource(file);
      if (ai) { renderEditor(); runAI(); toast('Claude에게 발표 구성을 부탁했어요. 1~3분쯤 걸려요'); }
      else toast('발표 자료를 만들었어요. 장을 더하거나 Claude에게 구성을 맡겨 보세요');
    } catch (err) { btn.disabled = false; btn.textContent = '만들기'; fail(err); }
  };
}

/* 사진 탭 */
function photosTab() {
  const d = S.detail;
  const canAuto = d.video.template === 'promo' || /"photo\d+"/.test(JSON.stringify(d.video.content || {})) || isAuto(d.video.template) || isFilm(d.video.template);
  return `${canAuto ? `<section class="sec" id="autoSec">${autoSection()}</section>` : ''}
  <section class="sec"><div class="sec-h"><h3>이 영상의 사진</h3></div>
    ${d.assets.length ? `<div class="photos">${d.assets.map(a => {
      const c = a.credit || {};
      return `<div class="photo"><div class="img">${a.url ? `<img src="${esc(a.url)}" alt="${esc(a.key)}">` : ''}</div>
        <div class="meta"><b>${esc(a.key)}</b><span>${esc(c.license || '')}${c.author ? ' · ' + esc(c.author) : ''}</span>
        <button class="btn ghost small" data-act="photo-remove" data-key="${esc(a.key)}" type="button">빼기</button></div></div>`;
    }).join('')}</div>` : '<p class="sec-note">아직 사진이 없어요.</p>'}
  </section>
  <section class="sec"><div class="sec-h"><h3>내 사진 넣기</h3></div>
    <label class="drop" id="drop"><input type="file" id="photoFile" accept="image/*" multiple hidden>
      사진 파일을 끌어다 놓거나 눌러서 고르세요. 직접 찍었거나 사용 권한이 있는 사진만 넣어 주세요.</label>
  </section>
  <section class="sec"><div class="sec-h"><h3>무료 사진 찾기</h3></div>
    <p class="sec-note">위키미디어 공용에서 광고에 써도 되는 사진(CC0, CC BY)만 보여 줘요. 영어로 찾으면 더 많이 나와요. CC BY 사진은 화면 출처가 자동으로 들어가요.</p>
    <form class="search" id="psearch"><input type="text" id="pq" placeholder="예) latte art, pilates studio" aria-label="사진 검색어"><button class="btn solid" type="submit">찾기</button></form>
    <div class="results" id="presults"></div>
  </section>`;
}
function autoSection() {
  const st = S.auto && S.auto.name === S.detail.name ? S.auto : null;
  const promo = S.detail.video.template === 'promo';
  const vis = promo ? (S.detail.video.content || {}).visuals || [] : null;
  const head = `<div class="sec-h"><h3>${promo ? '장면에 맞는 사진 자동으로 찾기' : '빈 사진 칸 자동으로 채우기'}</h3>
    <button class="btn solid small" data-act="auto-find" type="button" ${st && st.busy ? 'disabled' : ''}>${st && st.busy ? '찾는 중…' : st ? '처음부터 다시 찾기' : '자동으로 찾기'}</button></div>
    <p class="sec-note">${promo ? '사진 장면 문구를' : '사진 칸 옆 문구(장소 이름, 메뉴 이름 등)를'} 보고 ${S.state.claude ? 'Claude가 검색어를 정해' : '그 문구로'} 광고에 써도 되는 무료 사진(CC0, CC BY)을 칸마다 찾아 오고, ${S.state.claude ? 'Claude가 사진을 직접 보며 이 광고의 주제·상황과 어울리는지 검토해 점수 순으로 놓아요.' : ''} 마음에 드는 사진을 고르고 넣기를 누르세요.</p>`;
  if (!st) return head;
  if (st.busy && !Object.keys(st.scenes).length) return head + '<p class="hint">찾는 중이에요. 보통 20초쯤 걸려요.</p>';
  const ids = Object.keys(st.scenes).map(Number).sort((a, b) => a - b).filter(i => !vis || i < vis.length);
  const n = ids.filter(i => st.picks[i]).length;
  return head + (st.notes ? `<div class="ai-note">${esc(st.notes)}</div>` : '') + ids.map(i => {
    const sc = st.scenes[i];
    const v = vis ? vis[i] || {} : { title: sc.label || '' };
    return `<div class="auto-scene"><div class="auto-h"><b>${vis ? '사진 장면' : '사진 칸'} ${i + 1}</b><span>${esc(String(v.title || '').replace(/\n/g, ' '))}</span></div>
      <form class="search" data-auto-q="${i}"><input type="text" value="${esc(sc.queries.join(', '))}" aria-label="장면 ${i + 1} 검색어 (쉼표로 여러 개)"><button class="btn small" type="submit" ${st.busy ? 'disabled' : ''}>다시 찾기</button></form>
      ${sc.reviewed ? `<p class="hint auto-rv">Claude가 이 광고에 어울리는지 보고 점수 순으로 놓았어요${sc.candidates.some(c => c.review && c.review.ok) ? '' : ' · 어울리는 사진이 없어서 비워 뒀어요'}.</p>` : ''}
      <div class="cands">${sc.candidates.map(c => { const rv = c.review; return `<button class="cand ${st.picks[i] === c.title ? 'on' : ''} ${rv && !rv.ok ? 'bad' : ''}" data-act="auto-pick" data-i="${i}" data-title="${esc(c.title)}" type="button" title="${esc(`${rv ? `Claude 검토 ${rv.score}/10 · ${rv.why}\n` : ''}${c.title.replace(/^File:/, '')}\n${c.license} · ${c.author} · ${c.width}×${c.height}`)}"><img src="${esc(c.thumb)}" alt="" loading="lazy"><span>${esc(c.license)}</span>${rv ? `<em class="rv ${rv.ok ? 'ok' : ''}">${rv.score} · ${esc(rv.why)}</em>` : ''}</button>`; }).join('')}
        <button class="cand skip ${!st.picks[i] ? 'on' : ''}" data-act="auto-pick" data-i="${i}" data-title="" type="button">넣지 않기</button></div>
      ${sc.candidates.length ? '' : '<p class="hint">맞는 사진을 못 찾았어요. 검색어를 바꿔 다시 찾아 보세요.</p>'}</div>`;
  }).join('') + `<div class="auto-foot"><button class="btn solid" data-act="auto-apply" type="button" ${n && !st.busy ? '' : 'disabled'}>고른 사진 넣기${n ? ` (${n}장)` : ''}</button></div>`;
}
function renderAuto() { const box = $('#autoSec'); if (box) { box.innerHTML = autoSection(); bindAuto(); } }
function bindAuto() {
  $$('form[data-auto-q]').forEach(f => f.onsubmit = e => {
    e.preventDefault();
    const i = +f.dataset.autoQ;
    const qs = $('input', f).value.split(',').map(x => x.trim()).filter(Boolean);
    if (qs.length) runAuto([i], { [i]: qs });
  });
}
// reset: 처음부터 다시 찾기(이전 후보를 지움). 한 장면만 찾을 때는 다른 장면 후보를 그대로 둠.
async function runAuto(scenes, queries, reset) {
  await saveVideo.flush();
  const name = S.detail.name;
  if (!S.auto || S.auto.name !== name || reset) S.auto = { name, scenes: {}, picks: {}, notes: '' };
  const st = S.auto;
  st.busy = true; renderAuto();
  try {
    const job = await api('/api/job/autophoto', { name, scenes, queries: queries || null });
    trackJob(job, j => {
      st.busy = false;
      if (j.status === 'done') {
        for (const sc of j.result.scenes) { st.scenes[sc.i] = sc; const top = sc.candidates[0]; st.picks[sc.i] = top && (!top.review || top.review.ok) ? top.title : ''; }
        st.notes = j.result.notes || '';
      }
      if (S.auto === st) renderAuto();
    });
  } catch (e) { st.busy = false; renderAuto(); fail(e); }
}
function missingScenes() {
  const vis = (S.detail.video.content || {}).visuals || [];
  const miss = vis.map((v, i) => (!v.image || !S.detail.assets.some(a => a.key === v.image)) ? i : -1).filter(i => i >= 0);
  return miss.length ? miss : vis.map((_, i) => i);
}
async function applyAuto() {
  const st = S.auto, name = S.detail.name;
  const picks = Object.entries(st.picks).filter(([, t]) => t).map(([i, title]) => ({ i: +i, title }));
  if (!picks.length) return;
  await saveVideo.flush();
  st.busy = true; renderAuto();
  try {
    const job = await api('/api/job/autophoto-apply', { name, picks });
    trackJob(job, async j => {
      st.busy = false;
      if (j.status !== 'done' || !S.detail || S.detail.name !== name) return renderAuto();
      const fresh = await api('/api/video?name=' + encodeURIComponent(name));
      S.detail.assets = fresh.assets; S.detail.video.assets = fresh.video.assets;
      const vc = S.detail.video.content, vis = vc.visuals || [];
      const promo = S.detail.video.template === 'promo', credits = [];
      let sceneCredit = false;
      for (const p of j.result.placed) {
        if (promo) {
          if (!vis[p.i]) continue;
          vis[p.i].image = p.key;
          if (p.credit_line) vis[p.i].credit = p.credit_line; else delete vis[p.i].credit;
        } else {
          const sc = st.scenes[p.i]; if (!sc) continue;
          for (const path of sc.paths || []) {
            setPath(S.detail.video, 'content.' + path, p.key);
            const m = /^scenes\.(\d+)\./.exec(path);
            if (m && p.credit_line) { const it = vc.scenes[+m[1]]; it.credit = [...new Set([...(it.credit ? it.credit.split(' / ') : []), p.credit_line])].join(' / '); sceneCredit = true; }
          }
          if (p.credit_line && !/^scenes\./.test((sc.paths || [])[0] || '')) credits.push(p.credit_line);
        }
        delete st.scenes[p.i]; delete st.picks[p.i];
      }
      const roomForCredit = 'credit' in vc;
      if (credits.length && roomForCredit) vc.credit = [...new Set([...(vc.credit ? [vc.credit] : []), ...credits])].join(' / ');
      changed(); renderEditor();
      const needCredit = j.result.placed.some(p => p.credit_line);
      toast(`사진 ${j.result.placed.length}장을 넣었어요${needCredit ? (promo || sceneCredit || (credits.length && roomForCredit) ? '. 출처 표시도 넣었어요' : '. 이 영상엔 출처 칸이 없어서 게시글에 출처를 붙여 주세요 (사진 탭 아래 출처)') : ''}`, needCredit && !(promo || sceneCredit || roomForCredit));
    });
  } catch (e) { st.busy = false; renderAuto(); fail(e); }
}

function bindDrop() {
  const kf = $('#keyForm');
  if (kf) kf.onsubmit = async e => {
    e.preventDefault();
    const key = $('#gemKey').value.trim();
    if (!key) return;
    try { S.musicStatus = await api('/api/music/key', { key }); renderEditor(); toast('키를 저장했어요'); } catch (err) { fail(err); }
  };
  const ms = $('#musicSec');
  if (ms) {
    ms.ondragover = e => { e.preventDefault(); ms.classList.add('over'); };
    ms.ondragleave = () => ms.classList.remove('over');
    ms.ondrop = e => { e.preventDefault(); ms.classList.remove('over'); const f = [...e.dataTransfer.files].find(x => /^(audio|video)\//.test(x.type) || /\.(mp3|wav|m4a|flac|ogg|mp4)$/i.test(x.name)); if (f) setMusicFile(f); };
  }
  const lf = $('#lenForm');
  if (lf) lf.onsubmit = e => {
    e.preventDefault();
    const v = S.detail.video, target = +$('#lenTarget').value;
    const r = fitLength(v.content, v.template, target);
    changed(); renderEditor();
    toast(r.exact ? `${target}초로 맞췄어요` : `장면 수 때문에 ${r.total}초까지만 맞췄어요. 장면을 ${r.total < target ? '늘리면' : '줄이면'} ${target}초에 맞출 수 있어요`, !r.exact);
  };
  bindAuto();
  const drop = $('#drop');
  if (!drop) return;
  $('#photoFile').onchange = e => addPhotos([...e.target.files]);
  drop.ondragover = e => { e.preventDefault(); drop.classList.add('over'); };
  drop.ondragleave = () => drop.classList.remove('over');
  drop.ondrop = e => { e.preventDefault(); drop.classList.remove('over'); addPhotos([...e.dataTransfer.files].filter(f => f.type.startsWith('image/'))); };
  $('#psearch').onsubmit = async e => {
    e.preventDefault();
    const q = $('#pq').value.trim();
    if (!q) return;
    const box = $('#presults');
    box.innerHTML = '<p class="hint">찾는 중…</p>';
    try {
      const r = await api('/api/photo/search?q=' + encodeURIComponent(q));
      box.innerHTML = r.results.length ? r.results.map((p, i) => `<div class="result"><div class="img">${p.thumb ? `<img src="${esc(p.thumb)}" alt="" loading="lazy">` : ''}</div>
        <div class="meta"><b>${esc(p.license)}</b> · ${esc(p.author.slice(0, 40))}<br>${p.width}×${p.height}${Math.max(p.width, p.height) < 1600 ? ' <span class="lic-warn">작음</span>' : ''}
        <div style="display:flex;gap:6px;margin-top:6px"><button class="btn small" data-act="photo-get" data-title="${esc(p.title)}" type="button">넣기</button>
        <a class="btn ghost small" href="${esc(p.page)}" target="_blank" rel="noopener">원본</a></div></div></div>`).join('')
        : '<p class="hint">조건에 맞는 사진이 없어요. 다른 말로 찾아 보세요.</p>';
    } catch (err) { box.innerHTML = ''; fail(err); }
  };
}
async function addPhotos(files) {
  if (!files.length) return;
  await saveVideo.flush();
  for (const f of files) {
    try {
      setSaveState(`사진 올리는 중: ${f.name}`, 'busy');
      const up = await upload(f);
      const r = await api('/api/photo/add', { name: S.detail.name, upload: up.id });
      S.detail = r.detail;
      toast(`${r.photo.key} 로 넣었어요`);
    } catch (e) { fail(e); }
  }
  setSaveState('저장됨');
  autoFillVisuals();
  renderEditor();
  requestPreview();
}
function autoFillVisuals() {
  // 사진형 영상에서 비어 있는 사진 장면에 새 사진을 차례로 채움
  const v = S.detail.video;
  if (v.template !== 'promo') return;
  const c = v.content || (v.content = {});
  const used = new Set((c.visuals || []).map(x => x.image).filter(Boolean));
  const free = S.detail.assets.map(a => a.key).filter(k => !used.has(k));
  let changedAny = false;
  for (const vis of c.visuals || []) {
    if (!S.detail.assets.some(a => a.key === vis.image) && free.length) {
      vis.image = free.shift();
      const a = S.detail.assets.find(x => x.key === vis.image);
      if (a && a.credit && a.credit.credit_line && !vis.credit) vis.credit = a.credit.credit_line;
      changedAny = true;
    }
  }
  if (changedAny) changed();
}

/* 설정 탭 */
/* 음악 탭: 넣은 곡 + 음악 만들기 */
function musicTab() {
  const d = S.detail, v = d.video, c = v.content || {};
  const m = d.music || {};
  const tpl = v.template;
  return `
  <section class="sec drop-ok" id="musicSec"><div class="sec-h"><h3>배경음악</h3></div>
    ${m.file ? `<div class="field"><span class="lbl">${esc(m.name || m.file)}</span><audio controls src="${esc(m.url || '')}" style="width:100%"></audio></div>
      <div class="row">
        <div class="field"><label class="lbl" for="mVol">음량 <span class="cnt">${Math.round((m.volume ?? 1) * 100)}%</span></label><input id="mVol" type="range" min="0" max="1.5" step="0.05" value="${m.volume ?? 1}" data-music="volume"></div>
        <div class="field"><label class="lbl" for="mStart">곡 시작 위치(초)</label><input id="mStart" type="number" step="0.1" min="0" value="${m.start ?? 0}" data-music="start"></div>
      </div>
      <div class="row">
        <div class="field"><label class="lbl" for="mFi">처음 페이드(초)</label><input id="mFi" type="number" step="0.1" min="0" value="${m.fadeIn ?? .5}" data-music="fadeIn"></div>
        <div class="field"><label class="lbl" for="mFo">끝 페이드(초)</label><input id="mFo" type="number" step="0.1" min="0" value="${m.fadeOut ?? 2.5}" data-music="fadeOut"></div>
      </div>
      <div style="display:flex;gap:8px"><label class="btn small">다른 곡으로<input type="file" accept="audio/*,video/mp4" hidden data-act="music-file"></label><button class="btn ghost small danger" data-act="music-remove" type="button">음악 빼기</button></div>`
    : `<p class="sec-note">음원 파일을 고르거나 여기에 끌어다 놓으면, 박자를 재서 곡의 첫 박을 영상 시작에 맞추고 MP4를 만들 때 길이에 맞춰 잘라 넣어요. 사용 권한이 있는 곡만 넣어 주세요. Gemini 앱이나 Google Vids에서 받은 파일도 그대로 넣으면 돼요.</p>
      <label class="btn">음원 고르기<input type="file" accept="audio/*,video/mp4" hidden data-act="music-file"></label>`}
    ${m.file && m.bpm && LEN_TPLS.includes(tpl) ? `<div class="beat-snap"><span>${r1(m.bpm)} BPM · 첫 박을 ${(+m.start || 0).toFixed(2)}초에서 시작</span>
      <button class="btn small" data-act="beat-snap" type="button">장면 바뀌는 순간을 박자에 맞추기</button></div>` : ''}
  </section>
  ${musicGenBox(m, c)}`;
}

/* 작업 단계별로 끝났는지 (탭 번호 옆 체크 표시용) */
function emptyPhotoKeys() {
  const d = S.detail, have = new Set((d.assets || []).filter(a => a.url).map(a => a.key));
  const used = new Set((JSON.stringify(d.video.content || {}).match(/"(photo\d+)"/g) || []).map(x => x.slice(1, -1)));
  for (const vis of (d.video.content || {}).visuals || []) if (vis && vis.image !== undefined) used.add(vis.image || '');
  return [...used].filter(k => !have.has(k));
}
function stepState() {
  const d = S.detail, v = d.video;
  const usesPhotos = /"photo\d+"|"image"/.test(JSON.stringify(v.content || {}));
  return {
    copy: !!String(v.brief || '').trim(),
    photos: usesPhotos ? emptyPhotoKeys().length === 0 : true,
    music: !!(d.music && d.music.file),
    direct: false,
    publish: !!((v.upload || {}).done && Object.keys(v.upload.done).length),
  };
}

function settingsTab() {
  const d = S.detail, v = d.video, c = v.content || {};
  const m = d.music || {};
  const tpl = v.template;
  return `
  <section class="sec"><div class="sec-h"><h3>기본</h3></div>
    ${fText('title', '영상 제목')}
    <div class="field"><span class="lbl">만들 형식</span><div class="fmt-checks">
      ${FMT_KEYS.map(f => `<label><input type="checkbox" data-act="fmt-toggle" data-f="${f}" ${(v.formats || []).includes(f) ? 'checked' : ''}>${ratioIcon(f)}${FMT[f].label} ${FMT[f].name}</label>`).join('')}</div></div>
    ${fSelect('safe.tall', '9:16 비울 영역', [['reels', '릴스 광고 (가장 넉넉하게)'], ['stories', '스토리'], ['shorts', '유튜브 쇼츠'], ['none', '비우지 않음']])}
    ${tpl ? fCheck('content.progress', '아래 진행 막대 보이기', { def: true }) : ''}
  </section>
  ${tpl === 'promo' ? `<section class="sec"><div class="sec-h"><h3>장면 길이와 전환</h3></div>
    <p class="sec-note">비워 두면 기본값을 써요. 단위는 초.</p>
    <div class="row3">${[['hook', '첫 장면', 3], ['visual', '사진 장면마다', 2.6], ['benefits', '장점', 3.2], ['proof', '숫자', 2.4], ['cta', '마지막', 3.4]].map(([k, l, def]) => fText(`content.durations.${k}`, l, { num: true, ph: String(def) })).join('')}</div>
    <div class="row">${[['visual', '사진 장면으로'], ['benefits', '장점으로'], ['proof', '숫자로'], ['cta', '마지막으로']].map(([k, l]) => fSelect(`content.transitions.${k}`, l + ' 넘어갈 때', Object.entries(TRANS))).join('')}</div>
  </section>` : ''}
  ${tpl === 'scenes' ? `<section class="sec"><div class="sec-h"><h3>장면 길이와 전환</h3></div>
    <p class="sec-note">비워 두면 장면 종류에 맞는 기본 길이를 써요. 단위는 초.</p>
    <div class="row">${fText('content.ctaDur', '마지막 장면 길이', { num: true, ph: '3.4' })}${fSelect('content.ctaTransition', '마지막으로 넘어갈 때', Object.entries(TRANS))}</div>
    ${(c.scenes || []).map((b, i) => `<div class="row">${fText(`content.scenes.${i}.dur`, `${i + 1}. ${sceneName(b)} 길이`, { num: true, ph: String(r1(sceneDur(Object.assign({}, b, { dur: 0 })))) })}${i ? fSelect(`content.scenes.${i}.transition`, `${i + 1}번으로 넘어갈 때`, Object.entries(TRANS)) : '<div class="field"></div>'}</div>`).join('')}
  </section>` : ''}
  ${tpl === 'kinetic' ? `<section class="sec"><div class="sec-h"><h3>장면 길이와 전환</h3></div>
    <div class="row">${fText('content.ctaDur', '마지막 장면 길이(초)', { num: true, ph: '3.4' })}${fSelect('content.ctaTransition', '마지막으로 넘어갈 때', Object.entries(TRANS))}</div>
    ${(c.beats || []).map((b, i) => `<div class="row">${fText(`content.beats.${i}.dur`, `장면 ${i + 1} 길이(초)`, { num: true, ph: '기본' })}${fSelect(`content.beats.${i}.transition`, `장면 ${i + 1}로 넘어갈 때`, Object.entries(TRANS))}</div>`).join('')}
  </section>` : ''}
`;
}

/* 음악 만들기: 구글 Gemini API(자동, 유료 몇십 원) 또는 Gemini 앱(무료, 손으로) */
const MOODS_KO = [['keynote', '키노트·런칭 (밝고 깔끔)'], ['minimal', '미니멀 일렉트로닉'], ['cafe', '따뜻한 어쿠스틱 카페'], ['lofi', '로파이'],
  ['citypop', '시티팝'], ['travel', '여행 브이로그 (트로피컬)'], ['cinematic', '시네마틱 예고편'], ['funk', '펑키 디스코']];
function previewSeconds() {
  try { const w = $('#frame iframe').contentWindow; if (w && w.__DURATION) return +w.__DURATION; } catch (e) { /* 아직 안 열림 */ }
  const v = S.detail.video;
  return totalLength(v.content, v.template) || null;
}
function musicGenBox(m, c) {
  const st = S.musicStatus;
  const hint = S.detail.video.musicHint || null;
  const g = S.musicGen || (S.musicGen = { engine: 'gemini', mood: m.mood || (hint ? 'preset' : S.detail.video.template === 'promo' ? 'minimal' : 'keynote'), prompt: '', bpm: c.bpm || (hint && hint.bpm) || m.bpm || 120 });
  if (!st) { loadMusicStatus(); return `<section class="sec" id="musicGen"><div class="sec-h"><h3>음악 만들기</h3></div><p class="sec-note">확인하는 중…</p></section>`; }
  const gm = st.gemini || {}, usd = gm.prices || { clip: .04, song: .08 };
  const sec = previewSeconds();
  const cost = sec && sec <= (gm.clipMax || 30) - 2 ? usd.clip : usd.song;  // music.py track_seconds 와 같은 기준
  const keyBox = `<form class="search" id="keyForm"><input id="gemKey" type="password" placeholder="AIza로 시작하는 키" autocomplete="off"><button class="btn solid" type="submit">키 저장</button></form>
      <p class="hint">Google AI Studio(aistudio.google.com)에서 "API 키 만들기" 후 결제를 연결해 주세요. 키는 이 PC의 사용자 폴더에만 저장돼요. <button class="linkbtn" data-act="open-web" data-url="https://aistudio.google.com/apikey" type="button">AI Studio 열기</button></p>`;
  const controls = `<div class="row">
      <div class="field"><label class="lbl" for="mMood">분위기</label><select id="mMood" data-mgen="mood">${hint ? `<option value="preset" ${g.mood === 'preset' ? 'selected' : ''}>이 상황에 맞춘 음악 (추천)</option>` : ''}${MOODS_KO.map(([k, l]) => `<option value="${k}" ${g.mood === k ? 'selected' : ''}>${l}</option>`).join('')}<option value="custom" ${g.mood === 'custom' ? 'selected' : ''}>직접 적기</option></select></div>
      <div class="field"><label class="lbl" for="mBpm">빠르기 (BPM)</label><input id="mBpm" type="number" min="60" max="200" step="1" value="${esc(g.bpm)}" data-mgen="bpm"></div>
    </div>
    ${g.mood === 'custom' ? `<div class="field"><label class="lbl" for="mPrompt">원하는 음악 (영어로 쓰면 더 잘 알아들어요)</label><textarea id="mPrompt" rows="2" data-mgen="prompt" placeholder="warm acoustic guitar, soft shaker, cozy morning cafe">${esc(g.prompt)}</textarea></div>` : ''}`;
  let body;
  if (g.engine === 'gemini') {
    body = gm.key ? `${controls}
      <button class="btn solid" data-act="music-gen" type="button">${m.file && m.engine === 'gemini' ? '다시 만들기' : '음악 만들기'} · 약 ${cost}달러</button>
      <span class="hint" style="margin-left:6px">키 …${esc(gm.keyTail)} <button class="linkbtn" data-act="music-key-clear" type="button">바꾸기</button></span>`
      : `<div class="notice"><b>Gemini API 키를 한 번 넣어 주세요.</b> Lyria 음악은 무료 등급이 없어서 결제가 연결된 키가 필요해요. 영상이 28초 이하면 30초 곡으로 약 ${usd.clip}달러, 더 길면 약 ${usd.song}달러예요.${keyBox}</div>${controls}`;
  } else {
    body = `${controls}
      <ol class="steps"><li><b>프롬프트 복사하고 Gemini 열기</b>를 누르세요. 평소 쓰는 브라우저에서 Gemini가 열려요.</li>
        <li>Gemini 입력창에 붙여 넣고 보내요. 음악 만들기 도구가 따로 보이면 그걸 고르고 "연주곡"으로 해 주세요.</li>
        <li>곡이 나오면 MP3로 내려받아 위 <b>배경음악</b> 칸에 넣어요. 박자는 앱이 재서 첫 박을 맞춰요.</li></ol>
      <button class="btn solid" data-act="music-app" type="button">프롬프트 복사하고 Gemini 열기</button>
      <p class="hint">무료 계정은 하루에 만들 수 있는 곡 수가 정해져 있어요. 광고에 쓰기 전 Gemini 약관을 한 번 확인해 주세요.</p>`;
  }
  const hist = (m.history || []).filter(h => h.file !== m.file);
  return `<section class="sec" id="musicGen"><div class="sec-h"><h3>음악 만들기</h3></div>
    <p class="sec-note">구글 Gemini의 음악 모델(Lyria)로 영상 길이에 맞는 연주곡을 만들어요.</p>
    <div class="len-pick" role="radiogroup" aria-label="만드는 방법">
      <label><input type="radio" name="mEngine" value="gemini" ${g.engine === 'gemini' ? 'checked' : ''}><span>Gemini API · 자동</span></label>
      <label><input type="radio" name="mEngine" value="app" ${g.engine === 'app' ? 'checked' : ''}><span>Gemini 앱 · 무료</span></label></div>
    ${body}
    ${hist.length ? `<div class="mhist"><span class="lbl">전에 만든 곡</span>${hist.map(h => `<div class="mh"><audio controls preload="none" src="${esc(h.url || '')}"></audio><button class="btn small" data-act="music-pick" data-file="${esc(h.file)}" type="button">이 곡 쓰기</button></div>`).join('')}</div>` : ''}
  </section>`;
}
async function loadMusicStatus(force) {
  if (loadMusicStatus.busy) return;
  if (S.musicStatus && !force) return;
  loadMusicStatus.busy = true;
  try { S.musicStatus = await api('/api/music/status'); } catch (e) { S.musicStatus = { gemini: {} }; }
  loadMusicStatus.busy = false;
  if (S.tab === 'music' && S.detail) renderEditor();
}
function musicBody(extra) {
  const g = S.musicGen;
  return Object.assign({ name: S.detail.name, mood: g.mood === 'custom' || g.mood === 'preset' ? '' : g.mood, prompt: g.mood === 'custom' ? g.prompt : '', bpm: g.bpm, seconds: previewSeconds() || '' }, extra || {});
}
async function runMusic() {
  const g = S.musicGen, d = S.detail, gm = S.musicStatus.gemini || {}, usd = gm.prices || {};
  if (g.mood === 'custom' && !(g.prompt || '').trim()) return toast('원하는 음악을 한 줄 적어 주세요', true);
  const sec = previewSeconds();
  const cost = sec && sec <= (gm.clipMax || 30) - 2 ? usd.clip : usd.song;  // music.py track_seconds 와 같은 기준
  openDlg(`<div class="dlg-h"><h2>Gemini로 음악 만들기</h2><button class="icon-btn" data-close type="button" aria-label="닫기">×</button></div>
    <div class="dlg-b"><p>구글 Gemini API 요금 약 <b>${cost}달러</b>가 키를 만든 구글 계정으로 청구돼요.${sec ? ` 영상 ${r1(sec)}초에 맞춘 연주곡을 받아요.` : ''}</p>
      <p class="hint">돈을 쓰지 않으려면 닫고 "Gemini 앱 · 무료"를 골라 주세요.</p></div>
    <div class="dlg-f"><button class="btn ghost" data-close type="button">취소</button><button class="btn solid" id="lyGo" type="button">만들기 (약 ${cost}달러)</button></div>`);
  $('#lyGo').onclick = async () => {
    closeDlg();
    try {
      await saveVideo.flush();
      const job = await api('/api/job/music', musicBody({ engine: 'gemini', yes: true }));
      toast('Gemini가 곡을 만드는 중이에요. 30초~1분 걸려요');
      trackJob(job, j => {
        if (j.status !== 'done') return;
        const r = j.result || {};
        if (r.detail && S.detail && S.detail.name === d.name) { S.detail = r.detail; renderEditor(); }
        toast(`음악을 넣었어요${r.bpm ? ' · ' + r1(r.bpm) + ' BPM' : ''}`);
      });
    } catch (e) { fail(e); }
  };
}
async function musicApp() {
  const g = S.musicGen;
  if (g.mood === 'custom' && !(g.prompt || '').trim()) return toast('원하는 음악을 한 줄 적어 주세요', true);
  try {
    const b = musicBody();
    const qs = new URLSearchParams({ name: b.name, mood: b.mood, prompt: b.prompt, bpm: b.bpm, seconds: b.seconds }).toString();
    const r = await api('/api/music/prompt?' + qs);
    let copied = false;
    try { await navigator.clipboard.writeText(r.prompt); copied = true; } catch (e) { /* 클립보드 막힘 */ }
    await api('/api/open-web', { url: 'https://gemini.google.com/app' });
    if (copied) toast('프롬프트를 복사했어요. Gemini 입력창에 붙여 넣으세요');
    else openDlg(`<div class="dlg-h"><h2>Gemini에 붙여 넣을 프롬프트</h2><button class="icon-btn" data-close type="button" aria-label="닫기">×</button></div>
      <div class="dlg-b"><textarea rows="7" readonly style="width:100%">${esc(r.prompt)}</textarea></div>
      <div class="dlg-f"><button class="btn solid" data-close type="button">닫기</button></div>`);
  } catch (e) { fail(e); }
}
// 장면 길이를 2박 단위로 반올림해서 장면이 바뀌는 순간이 박에 떨어지게 함 (곡은 첫 박부터 시작)
function snapBeats(c, tpl, beat, per = 2) {
  const unit = beat * per, q = x => Math.max(unit, Math.round(x / unit) * unit);
  const r3 = x => Math.round(x * 1000) / 1000;
  if (tpl === 'promo') {
    const base = Object.assign({}, PROMO_D, c.durations || {});
    const dd = {};
    for (const k of Object.keys(PROMO_D)) dd[k] = r3(q(base[k]));
    c.durations = dd;
  } else if (tpl === 'kinetic') {
    for (const b of c.beats || []) b.dur = r3(q(b.dur || KIN_D[beatType(b)]));
    c.ctaDur = r3(q(c.ctaDur || 3.4));
  } else if (tpl === 'scenes') {
    for (const b of c.scenes || []) b.dur = r3(q(sceneDur(b)));
    c.ctaDur = r3(q(c.ctaDur || 3.4));
  }
  return totalLength(c, tpl);
}

/* 연출 탭 맨 위: 영상 길이. 사진형·글자형은 장면 길이로 맞추고, 상황 템플릿은 전체 속도(content.stretch)로 늘이고 줄임 */
function baseSeconds() {
  try { const w = $('#frame iframe').contentWindow; if (w && w.__BASE_DURATION) return +w.__BASE_DURATION; if (w && w.__DURATION) return +w.__DURATION / (+(S.detail.video.content || {}).stretch || 1); } catch (e) { /* 아직 안 열림 */ }
  return null;
}
function lengthPanel() {
  const v = S.detail.video, c = v.content || {}, tpl = v.template;
  if (LEN_TPLS.includes(tpl)) return lengthBox(c, tpl);
  if (isFilm(tpl)) return `<section class="sec"><div class="sec-h"><h3>영상 길이</h3></div><p class="sec-note" style="margin:0">이 필름은 120BPM 박자에 맞춰 짜여 있어서 길이를 바꾸지 않아요. 길이를 바꾸려면 아래에서 Claude Code에게 맡기세요.</p></section>`;
  const base = baseSeconds(), k = +c.stretch || 1;
  if (!base && S.detail.custom && S.lenGaveUp) return `<section class="sec"><div class="sec-h"><h3>영상 길이</h3></div><p class="sec-note" style="margin:0">이 영상은 길이 슬라이드를 쓸 수 없어요. 길이를 바꾸려면 아래에서 Claude Code에게 맡기세요.</p></section>`;
  // 미리보기가 뜨면 기본 길이를 알 수 있어서 몇 번 다시 봄. 직접 짠 옛 영상은 길이를 안 알려 줄 수 있어 6초쯤 뒤 그만둠
  const poll = n => setTimeout(() => {
    if (S.tab !== 'direct' || $('#stretchRange')) return;
    if (baseSeconds()) return renderEditor();
    if (S.detail.custom && n >= 4) { S.lenGaveUp = true; return renderEditor(); }
    if (n < 8) poll(n + 1);
  }, 1500);
  if (!base && !lengthPanel.polling) { lengthPanel.polling = true; poll(1); setTimeout(() => { lengthPanel.polling = false; }, 13000); }
  const marks = base ? LENGTHS.filter(n => n >= base * .7 - .01 && n <= base * 1.6 + .01) : [];
  return `<section class="sec" id="lenSec"><div class="sec-h"><h3>영상 길이</h3><span class="len-now" id="stretchNow">${base ? `${r1(base * k)}초` : '확인 중…'}</span></div>
    <p class="sec-note">슬라이드로 늘이거나 줄이면 모든 움직임이 같은 비율로 느려지거나 빨라져요. 기본 길이는 ${base ? r1(base) + '초' : '미리보기가 뜨면 보여요'}.</p>
    ${base ? `<input type="range" id="stretchRange" min="0.7" max="1.6" step="0.05" value="${k}" data-base="${base}" aria-label="영상 길이">
      <div class="stretch-scale"><span>짧게 · 빠르게</span><span>기본</span><span>길게 · 느리게</span></div>
      <div class="row-acts">${marks.map(n => `<button class="btn small ${Math.abs(base * k - n) < .3 ? 'solid' : ''}" data-act="stretch-to" data-sec="${n}" type="button">${n}초</button>`).join('')}
        <button class="btn ghost small" data-act="stretch-to" data-sec="${r1(base)}" type="button">기본으로</button></div>` : ''}
  </section>`;
}
function setStretch(k) {
  const c = S.detail.video.content || (S.detail.video.content = {});
  k = Math.round(Math.min(1.6, Math.max(.7, k)) * 100) / 100;
  if (Math.abs(k - 1) < .01) delete c.stretch; else c.stretch = k;
  changed(); renderEditor();
}
function lengthBox(c, tpl) {
  const t = totalLength(c, tpl);
  return `<section class="sec"><div class="sec-h"><h3>영상 길이</h3><span class="len-now">지금 ${r1(t)}초</span></div>
    <p class="sec-note">목표 길이를 고르면 장면마다 길이를 같은 비율로 늘이거나 줄여서 맞춰요. 너무 많이 늘어나면 장면을 추가하는 게 보기 좋아요.</p>
    <form class="search" id="lenForm"><select id="lenTarget" aria-label="목표 길이">${LENGTHS.map(n => `<option value="${n}" ${Math.abs(n - t) < 3 ? 'selected' : ''}>${n}초</option>`).join('')}</select>
      <button class="btn solid" type="submit">이 길이로 맞추기</button></form></section>`;
}

/* 고급 탭 */
function advancedTab() {
  return `<section class="sec"><div class="sec-h"><h3>설정 원본</h3></div>
    <p class="sec-note">video.json 을 바로 고칠 수 있어요. 잘못 고치면 미리보기가 안 나올 수 있으니 조심하세요.</p>
    <textarea id="rawJson" rows="24" style="font-family:ui-monospace,Consolas,monospace;font-size:12.5px" spellcheck="false">${esc(JSON.stringify(S.detail.video, null, 2))}</textarea>
    <div style="display:flex;gap:8px;margin-top:10px"><button class="btn solid" data-act="raw-apply" type="button">적용</button>
      <button class="btn ghost" data-act="open-folder" type="button">영상 폴더 열기</button></div></section>
  <section class="sec"><div class="sec-h"><h3>Claude Code로 고치기</h3></div>
    <p class="sec-note">새 연출이 필요하거나 화면으로 안 되는 수정은 Claude Code에 말로 부탁하세요. 예) "${esc(S.detail.name)} 영상 첫 장면에 마스코트가 손을 흔들게 해 줘"</p>
    <button class="btn" data-act="open-cc" type="button">Claude Code 열기</button></section>`;
}

/* 편집 이벤트 */
function writeField(path, val) {
  if (val === undefined && /\.\d+(\.|$)/.test(path)) val = '';   // 목록 안 칸: 빼지 않고 비움
  setPath(S.detail.video, path, val);
}
function readInput(el) {
  const t = el.dataset.type;
  if (t === 'bool') { const v = el.checked; return el.dataset.invert ? !v : v; }
  if (t === 'num' || el.type === 'number') { if (el.value === '') return undefined; const n = Number(el.value); return Number.isFinite(n) ? n : undefined; }
  if (t === 'nums') return el.value.split(/[,\s]+/).map(Number).filter(Number.isFinite);
  if (t === 'tags') return [...new Set(el.value.split(/[,\s]+/).map(x => x.replace(/^#+/, '')).filter(Boolean).map(x => '#' + x))];
  if (el.tagName === 'SELECT' && el.value === '') return undefined;
  return el.value;
}
$('#editor').addEventListener('input', e => {
  const el = e.target;
  if (S.sel && S.sel.type === 'brand') return onBrandInput(e);
  if (el.dataset.music) return onMusicInput(el);
  if (el.dataset.mgen) { S.musicGen[el.dataset.mgen] = el.dataset.mgen === 'bpm' ? Number(el.value) : el.value; if (el.dataset.mgen === 'mood') renderEditor(); return; }
  if (el.id === 'stretchRange') { const n = $('#stretchNow'); if (n) n.textContent = `${r1(+el.dataset.base * +el.value)}초`; return; }
  if (!el.dataset.path || !S.detail) return;
  if (el.type === 'checkbox' || el.tagName === 'SELECT') return;
  writeField(el.dataset.path, readInput(el));
  const cnt = $(`[data-cnt="${CSS.escape(el.dataset.path)}"]`);
  if (cnt) { const n = lenOf(el.value); cnt.textContent = `${n}/${cnt.dataset.lim}`; cnt.classList.toggle('over', n > +cnt.dataset.lim); }
  if (el.dataset.path === 'title') { const h = $('.ed-title h1'); if (h) h.textContent = el.value || S.detail.name; }
  if (el.dataset.path.startsWith('upload.')) { pubDirty(); return changed(false); }
  changed(!['title', 'brief'].includes(el.dataset.path));
});
$('#editor').addEventListener('change', e => {
  const el = e.target;
  if (S.sel && S.sel.type === 'brand') return onBrandChange(e);
  if (!S.detail) return;
  if (el.name === 'mEngine') { S.musicGen.engine = el.value; return renderEditor(); }
  if (el.dataset.mgen === 'mood') return;
  if (el.name === 'aiLen') { if (el.value) S.detail.video.target = +el.value; else delete S.detail.video.target; changed(false); return; }
  if (el.dataset.act === 'fmt-toggle') {
    const v = S.detail.video, f = el.dataset.f;
    let fm = (v.formats || []).filter(x => x !== f);
    if (el.checked) fm = FMT_KEYS.filter(x => fm.includes(x) || x === f);
    if (!fm.length) { el.checked = true; return toast('형식을 하나 이상 골라 주세요', true); }
    v.formats = fm;
    if (!fm.includes(S.fmt)) S.fmt = fm[0];
    changed(); renderStage(); return;
  }
  if (el.dataset.act === 'sec-toggle') return toggleSection(el.dataset.key, el.checked);
  if (el.dataset.act === 'beat-type') return setBeatType(+el.dataset.i, el.value);
  if (el.dataset.act === 'scene-type') return setSceneType(+el.dataset.i, el.value);
  if (el.dataset.act === 'slide-type') return setSlideType(+el.dataset.i, el.value);
  if (el.dataset.act === 'deck-source') return addDeckSource(el.files[0]);
  if (el.dataset.act === 'music-file') return setMusicFile(el.files[0]);
  if (el.dataset.music) return onMusicInput(el, true);
  if (el.id === 'stretchRange') return setStretch(+el.value);
  if (el.dataset.act === 'yt-client') return ytClient(el.files[0]);
  if (el.dataset.act === 'claude-model') return setClaudeOpt('model', el.value);
  if (el.dataset.act === 'claude-effort') return setClaudeOpt('effort', el.value);
  if (el.dataset.path && (el.type === 'checkbox' || el.tagName === 'SELECT') && el.dataset.path.startsWith('upload.')) {
    setPath(S.detail.video, el.dataset.path, readInput(el)); pubDirty(); return changed(false);
  }
  if (el.dataset.path && (el.type === 'checkbox' || el.tagName === 'SELECT')) {
    writeField(el.dataset.path, readInput(el));
    if (/\.images?(\.\d+)?$/.test(el.dataset.path)) {
      const a = S.detail.assets.find(x => x.key === el.value);
      const base = el.dataset.path.replace(/\.images?(\.\d+)?$/, '');
      if (/\.images\.\d+$/.test(el.dataset.path)) {   // 사진 여러 장: 쓰는 사진들의 출처를 모아 한 줄로
        const it = getPath(S.detail.video, base), lines = (it.images || []).map(k => ((S.detail.assets.find(x => x.key === k) || {}).credit || {}).credit_line).filter(Boolean);
        setPath(S.detail.video, base + '.credit', lines.length ? [...new Set(lines)].join(' / ') : undefined);
      } else if (a && a.credit) setPath(S.detail.video, base + '.credit', a.credit.credit_line || undefined);
      changed(); return renderEditor();
    }
    changed();
  }
});
$('#editor').addEventListener('click', async e => {
  const b = e.target.closest('[data-act]');
  if (!b || (S.sel && S.sel.type === 'brand')) return onBrandClick(e);
  const act = b.dataset.act, v = S.detail && S.detail.video;
  if (!v) return;
  const arrOf = p => { let a = getPath(v, p); if (!Array.isArray(a)) { a = []; setPath(v, p, a); } return a; };
  if (act === 'focus') {
    const r = b.getBoundingClientRect();
    const x = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)), y = Math.min(1, Math.max(0, (e.clientY - r.top) / r.height));
    setPath(v, `${b.dataset.base || 'content.visuals'}.${b.dataset.i}.focus`, [Math.round(x * 100) / 100, Math.round(y * 100) / 100]);
    changed(); return renderEditor();
  }
  if (act === 'add-visual') {
    v.content = v.content || {};
    const used = new Set((v.content.visuals || []).map(x => x.image));
    const free = S.detail.assets.find(a => !used.has(a.key));
    arrOf('content.visuals').push({ image: free ? free.key : '', title: '', sub: '', credit: free && free.credit ? free.credit.credit_line || '' : '', focus: [.5, .5] });
    changed(); return renderEditor();
  }
  if (act === 'add-beat') { arrOf('content.beats').push({ text: '' }); changed(); return renderEditor(); }
  if (act === 'add-item') { const a = arrOf(b.dataset.path); a.push(a.length ? blankLike(clone(a[a.length - 1])) : ''); changed(); return renderEditor(); }
  if (act === 'scene-add') {
    const sc = arrOf('content.scenes'); sc.push(SCENE_NEW[b.dataset.t]()); changed(); renderEditor();
    const el = $('#sc' + (sc.length - 1)); if (el) { el.scrollIntoView({ block: 'center' }); const f = $('textarea, input', el); if (f) f.focus({ preventScroll: true }); }
    return;
  }
  if (act === 'slide-add') {
    const sl = arrOf('content.slides'), t = b.dataset.t, nb = SLIDE_NEW[t]();
    if (t === 'closing' || !sl.length || sl[sl.length - 1].type !== 'closing') sl.push(nb); else sl.splice(sl.length - 1, 0, nb);   // 마무리 장 앞에 끼움
    changed(); renderEditor();
    const k = sl.indexOf(nb), el = $('#sl' + k); if (el) { el.scrollIntoView({ block: 'center' }); const f = $('textarea, input', el); if (f) f.focus({ preventScroll: true }); }
    return;
  }
  if (act === 'slide-dup') { const sl = arrOf('content.slides'), i = +b.dataset.i; sl.splice(i + 1, 0, clone(sl[i])); changed(); return renderEditor(); }
  if (act === 'slide-go') return deckGo(+b.dataset.i);
  if (act === 'deck-source-remove') { try { await saveVideo.flush(); S.detail = await api('/api/deck/source', { name: S.detail.name, remove: true }); renderEditor(); toast('자료를 뺐어요 (사진 탭의 그림은 그대로 있어요)'); } catch (err) { fail(err); } return; }
  if (act === 'scene-dup') { const sc = arrOf('content.scenes'), i = +b.dataset.i; sc.splice(i + 1, 0, clone(sc[i])); changed(); return renderEditor(); }
  if (act === 'scene-img-add') { const sc = arrOf('content.scenes'), it = sc[+b.dataset.i]; (it.images || (it.images = [])).push(freePhotoKeys(1)[0]); changed(); return renderEditor(); }
  if (act === 'add-line') { arrOf(b.dataset.path).push(''); changed(); renderEditor(); const ins = $$(`[data-path^="${CSS.escape(b.dataset.path)}."]`); if (ins.length) ins[ins.length - 1].focus(); return; }
  if (act === 'del' || act === 'up' || act === 'down') {
    const a = arrOf(b.dataset.path), i = +b.dataset.i;
    // 객체·짝 목록의 마지막 줄은 지우지 않고 비움 (다 지우면 다음에 더할 때 모양을 알 수 없어서). 장면 목록은 비워도 됨
    if (act === 'del' && a.length === 1 && a[0] && typeof a[0] === 'object' && b.dataset.path !== 'content.scenes' && b.dataset.path !== 'content.slides') { a[0] = blankLike(a[0]); toast('마지막 줄은 지우지 않고 비워 두었어요'); }
    else if (act === 'del') a.splice(i, 1);
    else { const j = act === 'up' ? i - 1 : i + 1; if (j < 0 || j >= a.length) return; [a[i], a[j]] = [a[j], a[i]]; }
    changed(); return renderEditor();
  }
  if (act === 'ai-toggle') { const box = $('#ai'); box.classList.toggle('closed'); S.aiOpen = !box.classList.contains('closed'); b.textContent = S.aiOpen ? '접기' : '펼치기'; return; }
  if (act === 'ai-run') return runAI();
  if (act === 'ai-undo') { if (S.undo) { v.content = S.undo; S.undo = null; changed(); renderEditor(); toast('Claude 초안을 적용하기 전으로 되돌렸어요'); } return; }
  if (act === 'photo-remove') { try { await saveVideo.flush(); S.detail = await api('/api/photo/remove', { name: S.detail.name, key: b.dataset.key }); renderEditor(); requestPreview(); } catch (err) { fail(err); } return; }
  if (act === 'photo-get') return getWikiPhoto(b);
  if (act === 'auto-find') return runAuto(S.detail.video.template === 'promo' ? missingScenes() : null, null, true);
  if (act === 'auto-one') { S.tab = 'photos'; renderEditor(); return runAuto([+b.dataset.i]); }
  if (act === 'auto-pick') { S.auto.picks[+b.dataset.i] = b.dataset.title; return renderAuto(); }
  if (act === 'auto-apply') return applyAuto();
  if (act === 'music-gen') return runMusic();
  if (act === 'music-app') return musicApp();
  if (act === 'open-web') return api('/api/open-web', { url: b.dataset.url }).catch(fail);
  if (act === 'music-key-clear') return dlgAccounts('gemini');
  if (act === 'music-pick') { try { await saveVideo.flush(); S.detail = await api('/api/music/pick', { name: S.detail.name, file: b.dataset.file }); renderEditor(); toast('이 곡으로 바꿨어요'); } catch (err) { fail(err); } return; }
  if (act === 'beat-snap') {
    const m = S.detail.music || {}, c = v.content || (v.content = {});
    const beat = m.beat || 60 / m.bpm;
    const total = snapBeats(c, v.template, beat);
    changed(); renderEditor(); toast(`장면 길이를 박자에 맞췄어요 · 전체 ${r1(total)}초`); return;
  }
  if (act === 'music-remove') { try { await saveVideo.flush(); S.detail = await api('/api/music', { name: S.detail.name, remove: true }); renderEditor(); } catch (err) { fail(err); } return; }
  if (act === 'raw-apply') {
    try {
      const nv = JSON.parse($('#rawJson').value);
      await api('/api/video/save', { name: S.detail.name, video: nv, raw: true });
      await selectVideo(S.detail.name); toast('적용했어요');
    } catch (err) { fail(err.name === 'SyntaxError' ? new Error('JSON 형식이 맞지 않아요: ' + err.message) : err); }
    return;
  }
  if (act === 'open-folder') return api('/api/open', { path: `videos/${S.detail.name}` }).catch(fail);
  if (act === 'open-cc') return openClaudeCode({});
  if (act === 'accounts') return dlgAccounts();
  if (act === 'cc-direction' && !isFilm(v.template) && !S.detail.starter) {
    const st = stepState(), left = [];
    if (!st.copy) left.push('문구 (아직 예시 문구)');
    if (!st.photos) left.push(`사진 (빈 칸 ${emptyPhotoKeys().length}개)`);
    if (!st.music) left.push('음악');
    if (left.length && !confirm(`아직 안 한 단계가 있어요: ${left.join(', ')}\n\n확인: 지금 상태로 ${isApi() ? 'Claude' : 'Claude Code'}에게 맡기기 (빈 정보는 Claude가 물어봐요)\n취소: ${left[0].split(' ')[0]} 단계부터 하기`)) {
      S.tab = !st.copy ? 'copy' : !st.photos ? 'photos' : 'music'; if (S.tab === 'copy') S.aiOpen = true; renderEditor();
      const t = S.tab === 'copy' && $('#brief'); if (t) t.focus({ preventScroll: true }); return;
    }
  }
  if (act === 'cc-direction') { saveVideo.flush(); const st0 = S.detail.starter; return openClaudeCode({ name: S.detail.name }, st0 ? 'Claude Code 창을 열었어요. 장면 계획을 확인하고 진행해 주세요' : 'Claude Code 창을 열고 연출 프롬프트를 건넸어요'); }
  if (act === 'dir-toggle') { S.dirOpen = !S.dirOpen; return renderEditor(); }
  if (act === 'look-tpl') {
    if (b.dataset.t === v.template) return;
    try {
      await saveVideo.flush();
      S.detail = await api('/api/video/look', { name: S.detail.name, template: b.dataset.t });
      renderEditor(); requestPreview();
      toast(`${(TEMPLATE_INFO[b.dataset.t] || {}).name || b.dataset.t}(으)로 바꿨어요`);
    } catch (err) { fail(err); }
    return;
  }
  if (act === 'style-pick') return dlgStyle();
  if (act === 'style-card') return dlgStyleCard();
  if (act === 'style-clear') { delete v.style; delete v.styleColors; delete v.styleFonts; delete v.styleLook; changed(); return renderEditor(); }
  if (act === 'dir-copy') return copyText(S.detail.direction || '').then(() => toast('연출 프롬프트를 복사했어요'));
  if (act === 'dir-save') { const t = $('#dirText').value; return api('/api/direction', { name: S.detail.name, text: t }).then(() => { S.detail.direction = t; toast('연출 프롬프트를 저장했어요'); }).catch(fail); }
  if (act === 'duplicate') return dlgDuplicate();
  if (act === 'stretch-to') { const base = baseSeconds(); if (base) setStretch(+b.dataset.sec / base); return; }
  if (/^(pub-|yt-|soc-)/.test(act)) return pubAction(act, b);
});

function toggleSection(key, on) {
  const c = S.detail.video.content || (S.detail.video.content = {});
  S._backup = S._backup || {};
  if (on) {
    c[key] = S._backup[key] || (key === 'proof' ? { number: 100, suffix: '%', label: '' } : { title: '', items: ['', ''] });
  } else {
    S._backup[key] = c[key];
    delete c[key];
  }
  changed(); renderEditor();
}
function setBeatType(i, t) {
  const b = S.detail.video.content.beats[i];
  delete b.type;
  if (t === 'number') { if (b.number == null) b.number = 0; delete b.items; }
  else if (t === 'list') { delete b.number; if (!b.items) b.items = ['', '']; }
  else { delete b.number; delete b.items; if (beatType(b) !== t) b.type = t; }
  changed(); renderEditor();
}
async function getWikiPhoto(btn) {
  btn.disabled = true; btn.textContent = '받는 중';
  try {
    const job = await api('/api/photo/get', { name: S.detail.name, title: btn.dataset.title });
    trackJob(job, async j => {
      if (j.status !== 'done') { btn.disabled = false; btn.textContent = '넣기'; return; }
      btn.textContent = '넣었어요';
      const keep = S.detail.name;
      const fresh = await api('/api/video?name=' + encodeURIComponent(keep));
      if (!S.detail || S.detail.name !== keep) return;
      S.detail.assets = fresh.assets; S.detail.video.assets = fresh.video.assets;
      (fresh.video.content.visuals || []).forEach((fv, k) => { const cv = (S.detail.video.content.visuals || [])[k]; if (cv && !cv.credit && fv.credit) cv.credit = fv.credit; });
      autoFillVisuals();
      requestPreview();
      const box = $('#presults'); const html = box ? box.innerHTML : '';
      renderEditor();
      if (box && $('#presults')) $('#presults').innerHTML = html;
      toast(`${j.result.key} 로 넣었어요${j.result.credit_line ? ' (출처 표시 자동)' : ''}`);
    });
  } catch (e) { btn.disabled = false; btn.textContent = '넣기'; fail(e); }
}
const saveMusic = debounce(async patch => {
  try { S.detail.music = (await api('/api/music', Object.assign({ name: S.detail.name }, patch))).music; } catch (e) { fail(e); }
}, 500);
let musicPatch = {};
function onMusicInput(el) {
  musicPatch[el.dataset.music] = Number(el.value);
  if (el.dataset.music === 'volume') { const c = el.parentElement.querySelector('.cnt'); if (c) c.textContent = Math.round(el.value * 100) + '%'; }
  const p = musicPatch; saveMusic(p);
}
async function setMusicFile(file) {
  if (!file) return;
  try {
    await saveVideo.flush();
    setSaveState('음원 올리는 중', 'busy');
    const up = await upload(file);
    S.detail = await api('/api/music', { name: S.detail.name, upload: up.id });
    setSaveState('저장됨'); renderEditor();
    const m = S.detail.music || {};
    toast(m.bpm ? `음원을 넣었어요 · ${r1(m.bpm)} BPM, 첫 박 ${(+m.start || 0).toFixed(2)}초부터` : '음원을 넣었어요. MP4를 만들 때 함께 들어가요.');
  } catch (e) { fail(e); }
}

/* ---------------------------------------------------------------- Claude 문구 */
async function runAI() {
  const brief = ($('#brief').value || '').trim();
  if (brief.length < 5) return toast('무엇을 알리는 광고인지 한두 문장 적어 주세요', true);
  S.detail.video.brief = brief;
  saveVideo.flush();
  const btn = $('[data-act="ai-run"]'); if (btn) { btn.disabled = true; btn.textContent = '쓰는 중…'; }
  try {
    const job = await api('/api/job/ai', { name: S.detail.name, brief, target: S.detail.video.target || null });
    const name = S.detail.name;
    trackJob(job, j => {
      const b2 = $('[data-act="ai-run"]'); if (b2) { b2.disabled = false; b2.textContent = '초안 받기'; }
      if (j.status === 'done' && S.detail && S.detail.name === name) dlgAIResult(j.result);
    });
  } catch (e) { if (btn) { btn.disabled = false; btn.textContent = '초안 받기'; } fail(e); }
}
function summarize(c, tpl) {
  const rows = [];
  const add = (k, v) => { if (v) rows.push(`<div class="scene"><b>${esc(k)}</b><div>${esc(v)}</div></div>`); };
  if (tpl === 'promo') {
    if (c.hook) add('첫 장면', [c.hook.kicker, c.hook.headline, c.hook.sub].filter(Boolean).join('\n'));
    (c.visuals || []).forEach((v, i) => add(`사진 ${i + 1} (${v.image || '-'})`, [v.title, v.sub].filter(Boolean).join('\n')));
    if (c.benefits) add('장점', [c.benefits.title, ...(c.benefits.items || []).map(x => '· ' + x)].join('\n'));
    if (c.proof) add('숫자', `${c.proof.number}${c.proof.suffix || ''}  ${c.proof.label || ''}`);
  } else if (tpl === 'kinetic') {
    (c.beats || []).forEach((b, i) => add(`장면 ${i + 1}`, [b.kicker, b.number != null ? `${b.prefix || ''}${b.number}${b.suffix || ''}` : b.text, ...(b.items || []).map(x => '· ' + x), b.sub].filter(Boolean).join('\n')));
  } else if (tpl === 'deck') {
    return summarizeDeck(c) || `<pre>${esc(JSON.stringify(c, null, 2))}</pre>`;
  } else if (tpl === 'scenes') {
    (c.scenes || []).filter(b => b && typeof b === 'object').forEach((b, i) => {
      const t = sceneType(b);
      const main = t === 'number' ? `${b.prefix || ''}${b.number}${b.suffix || ''}${b.text ? '  ' + b.text : ''}` : b.text;
      const extra = t === 'compare' ? [`${b.leftLabel || '전'}: ${b.left || ''}`, `${b.rightLabel || '후'}: ${b.right || ''}`]
        : t === 'chart' ? [(b.bars || []).map(x => `${x[0]} ${x[1]}${b.unit || ''}`).join(' · ')]
        : t === 'quote' ? [[b.by, b.role].filter(Boolean).join(' · ')]
        : t === 'photo' || t === 'gallery' ? [`사진: ${[b.image, ...(b.images || [])].filter(Boolean).join(', ') || '없음'}`] : [];
      add(`${i + 1}. ${sceneName(b)}`, [b.kicker, main, ...(b.items || []).map(x => '· ' + x), ...extra, b.sub].filter(Boolean).join('\n'));
    });
  } else {
    // 그 밖의 템플릿: 글자 칸을 차례로 보여 줌 (사진 키·설정 값은 뺌)
    const lines = [];
    const walk = (o, label) => {
      if (typeof o === 'string') { if (o && !/^photo\d+$/.test(o) && !/^#[0-9a-f]{3,8}$/i.test(o) && !isPhotoKey(o)) lines.push([label, o]); return; }
      if (Array.isArray(o)) { if (o.every(x => typeof x === 'string') && o.length && o.every(x => x.length < 30)) lines.push([label, o.filter(x => !isPhotoKey(x)).join(' · ')]); else o.forEach(x => walk(x, label)); return; }
      if (o && typeof o === 'object') for (const [k, v] of Object.entries(o)) { if (k === 'cta' || FILM_SKIP.has(k)) continue; walk(v, FILM_LABEL[k] || k); }
    };
    walk(c, '');
    const grouped = [];
    for (const [k, v] of lines) { const last = grouped[grouped.length - 1]; if (last && last[0] === k) last[1] += '\n' + v; else grouped.push([k, v]); }
    grouped.slice(0, 30).forEach(([k, v]) => add(k || '문구', v));
  }
  if (c.cta) add('마지막', [c.cta.headline, c.cta.button && `[${c.cta.button}]`, c.cta.sub].filter(Boolean).join('\n'));
  return rows.join('') || `<pre>${esc(JSON.stringify(c, null, 2))}</pre>`;
}
// Claude 가 돌려준 장면 목록을 템플릿이 읽는 모양으로 (이상한 값이 와도 창이 안 깨지게)
function normScenes(c) {
  if (!c || !Array.isArray(c.scenes)) { if (c) c.scenes = []; return c; }
  const strs = x => Array.isArray(x) ? x.filter(y => y != null && typeof y !== 'object').map(String) : typeof x === 'string' ? x.split('\n').filter(Boolean) : [];
  c.scenes = c.scenes.filter(b => b && typeof b === 'object' && !Array.isArray(b)).map(b => {
    if (b.items !== undefined) b.items = strs(b.items);
    if (b.images !== undefined) b.images = strs(b.images);
    if (b.bars !== undefined) b.bars = Array.isArray(b.bars) ? b.bars.filter(x => Array.isArray(x)).map(x => [String(x[0] ?? ''), x[1] ?? 0]) : [];
    for (const k of ['text', 'sub', 'kicker', 'left', 'right', 'by', 'role']) if (b[k] != null && typeof b[k] !== 'string') b[k] = String(b[k]);
    return b;
  });
  return c;
}
function dlgAIResult(r) {
  const v = S.detail.video;
  const nc0 = clone(r.content);
  if (v.template === 'scenes') normScenes(nc0);
  if (v.template === 'deck') normSlides(nc0);
  for (const k of ['durations', 'transitions', 'progress', 'ctaDur', 'ctaTransition', 'schemes', 'mascot', 'ctaMascot', 'stretch']) if (v.content && v.content[k] !== undefined && nc0[k] === undefined && !(r.target && (k === 'durations' || k === 'ctaDur'))) nc0[k] = v.content[k];
  if (!LEN_TPLS.includes(v.template) && v.content) for (const [k, x] of Object.entries(v.content)) if (nc0[k] === undefined) nc0[k] = clone(x);
  if (v.template === 'scenes' && v.content && v.content.note !== undefined && nc0.note === undefined) nc0.note = v.content.note;
  const fit = v.template === 'deck' ? { total: 0 } : r.target && LEN_TPLS.includes(v.template) ? fitLength(nc0, v.template, r.target) : { total: totalLength(nc0, v.template) };
  const lenNote = fit.total ? (r.target && !fit.exact ? `영상 길이 ${fit.total}초 (장면 수 때문에 ${r.target}초에 딱 맞추지 못했어요. 장면을 ${fit.total < r.target ? '늘리면' : '줄이면'} 맞출 수 있어요)` : `영상 길이 ${r1(fit.total)}초`) : '';
  const have = new Set(S.detail.assets.map(a => a.key));
  const emptyPhotos = v.template === 'scenes' || v.template === 'deck' ? new Set((JSON.stringify(nc0.scenes || nc0.slides || []).match(/"photo\d+"/g) || []).map(x => x.slice(1, -1)).filter(k => !have.has(k))).size
    : (nc0.visuals || []).filter(x => !x.image || !have.has(x.image)).length;
  openDlg(`<div class="dlg-h"><h2>Claude가 쓴 초안</h2></div>
    <div class="dlg-b">${r.notes ? `<div class="ai-note">${esc(r.notes)}</div>` : ''}
      ${v.template === 'deck' ? `<p class="len-note">${(nc0.slides || []).length}장${emptyPhotos ? ` · 사진이 비어 있는 장 ${emptyPhotos}개는 사진 탭에서 채울 수 있어요` : ''}</p>` : ''}${lenNote ? `<p class="len-note">${esc(lenNote)}${emptyPhotos ? ` · 사진이 비어 있는 장면 ${emptyPhotos}개는 사진 탭의 자동 찾기로 채울 수 있어요` : ''}</p>` : ''}
      <div class="ai-result">${summarize(nc0, v.template)}</div></div>
    <div class="dlg-f"><button class="btn ghost" data-close type="button">버리기</button><button class="btn solid" id="aiApply" type="button">적용</button></div>`);
  $('#aiApply').onclick = () => {
    S.undo = clone(v.content || {});
    v.content = nc0;
    closeDlg(); changed(); renderEditor();
    toast('초안을 적용했어요. 마음에 안 들면 되돌리기를 누르세요.');
  };
}

/* ---------------------------------------------------------------- 편집: 브랜드 */
const COLOR_FIELDS = [['bg', '배경'], ['onBg', '배경 위 글자'], ['accent', '강조색'], ['accentInk', '강조색 위 글자'], ['paper', '밝은 바탕'], ['ink', '밝은 바탕 위 글자']];
function renderBrandEditor() {
  const b = S.brand;
  const st = S.state;
  const assets = b.assets || {};
  const fam = [...new Set((b.fonts || []).map(f => f.family))];
  const hasSerif = (b.fonts || []).some(f => /Serif/i.test(f.file));
  const logoUrl = b.logo && assets[b.logo] ? `/brands/${b.slug}/${assets[b.logo]}?m=${Date.now()}` : null;
  const mascotUrl = b.mascot && assets[b.mascot] ? `/brands/${b.slug}/${assets[b.mascot]}?m=${Date.now()}` : null;
  const vids = st.videos.filter(v => v.brand === b.slug);
  $('#editor').innerHTML = `
  <div class="ed-head"><div class="ed-title"><h1>${esc(b.name)}</h1><button class="btn solid small" data-bact="new-video" type="button">영상 추가</button><button class="btn small" data-bact="new-deck" type="button">발표 자료 추가</button></div>
    <div class="ed-sub">브랜드 설정 · ${esc(b.slug)} · 영상 ${vids.length}개</div>
    <div class="tabs"><span class="tab on">브랜드</span></div></div>
  <div class="ed-body">
    <section class="sec"><div class="sec-h"><h3>소개와 말투</h3></div>
      ${bText('name', '브랜드 이름')}
      ${bText('description', '어떤 계정인지 한 줄')}
      ${bText('voice.tone', '말투', { multi: true, ph: '예) 친근한 해요체, 이모지는 쓰지 않음, 짧은 문장' })}
      ${bLines('about', '참고 정보 (한 줄에 하나)', '대표 상품, 매장 위치, 운영 시간 확인 방법')}
      ${bLines('notes', '꼭 지킬 규칙 (한 줄에 하나)', '예) 경쟁사 이름 쓰지 않기, 가격은 "부터"를 붙이기')}
      <p class="hint">Claude가 문구를 쓸 때 말투와 규칙을 그대로 따라요.</p>
    </section>
    <section class="sec"><div class="sec-h"><h3>색</h3></div>
      <div class="colors">${COLOR_FIELDS.map(([k, l]) => colorField(k, l, (b.colors || {})[k])).join('')}</div>
      <div class="contrast" id="contrast">${contrastHtml(b.colors || {})}</div>
    </section>
    <section class="sec"><div class="sec-h"><h3>로고와 마스코트</h3></div>
      <div class="row">
        <div class="field"><span class="lbl">로고</span><div class="asset-box"><div class="pv">${logoUrl ? `<img src="${esc(logoUrl)}" alt="로고">` : '<span class="hint">없음</span>'}</div>
          <div class="acts"><label class="btn small">${logoUrl ? '바꾸기' : '올리기'}<input type="file" accept="image/*" hidden data-bact="asset" data-key="logo"></label>
          ${logoUrl ? '<button class="btn ghost small danger" data-bact="asset-remove" data-key="logo" type="button">빼기</button>' : ''}</div></div></div>
        <div class="field"><span class="lbl">마스코트·캐릭터</span><div class="asset-box"><div class="pv">${mascotUrl ? `<img src="${esc(mascotUrl)}" alt="마스코트">` : '<span class="hint">없음</span>'}</div>
          <div class="acts"><label class="btn small">${mascotUrl ? '바꾸기' : '올리기'}<input type="file" accept="image/*" hidden data-bact="asset" data-key="mascot"></label>
          ${mascotUrl ? '<button class="btn ghost small danger" data-bact="asset-remove" data-key="mascot" type="button">빼기</button>' : ''}</div></div></div>
      </div>
      <label class="check" style="margin-bottom:10px"><input type="checkbox" id="cutoutOn" ${st.rembg ? 'checked' : ''}>올릴 때 배경 지우기 ${st.rembg ? '' : '<span class="hint">(AI 도구가 없어서 단색 배경만 지워요)</span>'}</label>
      ${logoUrl ? '' : `<div class="row">${bText('logoText', '글자 로고')}${bText('logoSub', '글자 로고 아래 작은 글')}</div>`}
    </section>
    <section class="sec"><div class="sec-h"><h3>글꼴과 무늬</h3></div>
      <div class="row">
        ${bSelect('type.heading', '제목 글꼴', fam.map(f => [f, fontLabel(b, f)]))}
        ${bSelect('type.body', '본문 글꼴', fam.map(f => [f, fontLabel(b, f)]))}
      </div>
      ${hasSerif ? '' : '<button class="btn ghost small" data-bact="add-serif" type="button" style="margin-bottom:12px">명조 제목 글꼴 추가</button>'}
      ${bSelect('pattern', '배경 무늬', [['dots', '점'], ['grid', '격자'], ['rays', '햇살']])}
    </section>
  </div>`;
}
function fontLabel(b, fam) {
  const f = (b.fonts || []).find(x => x.family === fam);
  if (!f) return fam;
  return /Serif/i.test(f.file) ? `${fam} (명조)` : /Cinzel/i.test(f.file) ? `${fam} (영문 장식체)` : `${fam} (고딕)`;
}
function bText(path, label, o = {}) {
  const val = getPath(S.brand, path) || '';
  const id = 'b_' + path.replace(/\W/g, '_');
  return `<div class="field"><label class="lbl" for="${id}">${esc(label)}</label>${o.multi ? `<textarea id="${id}" data-bpath="${path}" rows="2" placeholder="${esc(o.ph || '')}">${esc(val)}</textarea>` : `<input id="${id}" type="text" data-bpath="${path}" value="${esc(val)}" placeholder="${esc(o.ph || '')}">`}</div>`;
}
function bLines(path, label, ph) {
  const arr = getPath(S.brand, path) || [];
  const id = 'b_' + path;
  return `<div class="field"><label class="lbl" for="${id}">${esc(label)}</label><textarea id="${id}" data-bpath="${path}" data-lines="1" rows="3" placeholder="${esc(ph || '')}">${esc(arr.join('\n'))}</textarea></div>`;
}
function bSelect(path, label, options) {
  const val = getPath(S.brand, path) || '';
  const id = 'b_' + path.replace(/\W/g, '_');
  return `<div class="field"><label class="lbl" for="${id}">${esc(label)}</label><select id="${id}" data-bpath="${path}">${options.map(([k, l]) => `<option value="${esc(k)}" ${k === val ? 'selected' : ''}>${esc(l)}</option>`).join('')}</select></div>`;
}
function colorField(k, label, val) {
  const hex = /^#[0-9a-f]{6}$/i.test(val || '') ? val : '#888888';
  return `<div class="color"><span class="cl">${esc(label)}</span><input type="color" value="${esc(hex)}" data-color="${k}" aria-label="${esc(label)}"><input type="text" value="${esc(val || '')}" data-color-text="${k}" aria-label="${esc(label)} 값"></div>`;
}
function hexRgb(h) { const m = /^#?([0-9a-f]{6})$/i.exec(h || ''); if (!m) return null; const n = parseInt(m[1], 16); return [n >> 16 & 255, n >> 8 & 255, n & 255]; }
function lum(c) { const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }; return .2126 * f(c[0]) + .7152 * f(c[1]) + .0722 * f(c[2]); }
function contrastRatio(a, b) { const A = hexRgb(a), B = hexRgb(b); if (!A || !B) return null; const x = lum(A), y = lum(B); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05); }
function contrastHtml(c) {
  return [['onBg', 'bg', '배경 글자'], ['accentInk', 'accent', '버튼 글자'], ['ink', 'paper', '밝은 바탕 글자'], ['accent', 'bg', '강조색과 배경']].map(([a, b, l]) => {
    const r = contrastRatio(c[a], c[b]);
    return r == null ? '' : `<span class="${r < 3 ? 'low' : ''}" title="4.5 이상이면 넉넉해요. 3 아래면 잘 안 보일 수 있어요">${l} ${r.toFixed(1)}</span>`;
  }).join('');
}
function onBrandInput(e) {
  const el = e.target;
  if (el.dataset.color) { S.brand.colors[el.dataset.color] = el.value.toUpperCase(); const t = $(`[data-color-text="${el.dataset.color}"]`); if (t) t.value = el.value.toUpperCase(); }
  else if (el.dataset.colorText) {
    const v = el.value.trim();
    if (!/^#[0-9a-f]{6}$/i.test(v) && !/^rgba?\([\d\s.,%]+\)$/i.test(v)) return;
    S.brand.colors[el.dataset.colorText] = v;
    const c = $(`[data-color="${el.dataset.colorText}"]`); if (c && /^#[0-9a-f]{6}$/i.test(v)) c.value = v;
  }
  else if (el.dataset.bpath) {
    const val = el.dataset.lines ? el.value.split('\n').map(s => s.trim()).filter(Boolean) : el.value;
    if (el.dataset.bpath === 'voice.tone') { S.brand.voice = S.brand.voice || {}; }
    setPath(S.brand, el.dataset.bpath, val);
    if (el.dataset.bpath === 'name') $('.ed-title h1').textContent = el.value;
  } else return;
  if (el.dataset.color || el.dataset.colorText) {
    const c = S.brand.colors;
    // 배경·강조색에 따라 무늬·빛 색도 맞춤
    const on = hexRgb(c.onBg), ac = hexRgb(c.accent);
    if (on) { c.pattern = `rgba(${on.join(',')},.08)`; c.onBgMuted = `rgba(${on.join(',')},.75)`; }
    if (ac) c.glow = `rgba(${ac.join(',')},.35)`;
    $('#contrast').innerHTML = contrastHtml(c);
  }
  renderBrandStage();
  saveBrand();
}
function onBrandChange(e) {
  const el = e.target;
  if (el.dataset.bact === 'asset') return uploadBrandAsset(el.dataset.key, el.files[0]);
  if (el.tagName === 'SELECT' && el.dataset.bpath) { setPath(S.brand, el.dataset.bpath, el.value); if (el.dataset.bpath === 'type.heading') S.brand.type.display = el.value; renderBrandStage(); saveBrand(); }
}
async function onBrandClick(e) {
  const b = e.target.closest('[data-bact]');
  if (!b) return;
  const act = b.dataset.bact;
  if (act === 'new-video') return dlgNewVideo(S.brand.slug);
  if (act === 'new-deck') return dlgNewDeck(S.brand.slug);
  if (act === 'add-serif') {
    S.brand.fonts.push({ family: 'BrandSerif', weight: 900, file: 'fonts/NotoSerifKR-Black.woff2' });
    S.brand.type.heading = 'BrandSerif'; S.brand.type.display = 'BrandSerif';
    saveBrand(); renderBrandEditor(); renderBrandStage(); return;
  }
  if (act === 'asset-remove') {
    try { saveBrand.flush(); await api('/api/brand/asset', { slug: S.brand.slug, key: b.dataset.key, remove: true }); await selectBrand(S.brand.slug); } catch (err) { fail(err); }
  }
}
async function uploadBrandAsset(key, file) {
  if (!file) return;
  try {
    saveBrand.flush();
    const up = await upload(file);
    const cut = $('#cutoutOn') && $('#cutoutOn').checked;
    const r = await api('/api/brand/asset', { slug: S.brand.slug, key, upload: up.id, cutout: cut });
    const slug = S.brand.slug;
    if (r.job) {
      toast('배경을 지우는 중이에요. 처음엔 1~2분 걸릴 수 있어요.');
      trackJob(r.job, async j => { if (j.status === 'done' && j.result && j.result.note) toast(j.result.note, true); if (S.sel && S.sel.id === slug) await selectBrand(slug); await refreshState(); });
    }
    await selectBrand(slug); await refreshState();
  } catch (e) { fail(e); }
}

/* 브랜드 미리보기 */
const loadedFonts = new Set();
function ensureBrandFonts(b) {
  for (const f of b.fonts || []) {
    const key = b.slug + ':' + f.family + ':' + f.weight;
    if (loadedFonts.has(key)) continue;
    loadedFonts.add(key);
    const url = f.file.startsWith('fonts/') ? '/' + f.file : `/brands/${b.slug}/${f.file}`;
    const ff = new FontFace(`B_${b.slug}_${f.family}`, `url(${url})`, { weight: String(f.weight || 400) });
    ff.load().then(x => { document.fonts.add(x); }).catch(() => {});
  }
}
function renderBrandStage() {
  const b = S.brand; if (!b) return;
  ensureBrandFonts(b);
  const c = b.colors || {};
  const fh = `"B_${b.slug}_${(b.type || {}).heading}", "StudioSans", sans-serif`;
  const fb = `"B_${b.slug}_${(b.type || {}).body}", "StudioSans", sans-serif`;
  const assets = b.assets || {};
  const logo = b.logo && assets[b.logo] ? `/brands/${b.slug}/${assets[b.logo]}` : null;
  const mascot = b.mascot && assets[b.mascot] ? `/brands/${b.slug}/${assets[b.mascot]}` : null;
  $('#stage').innerHTML = `<div class="stage-bar"><span style="font-weight:700;font-size:13px">브랜드 미리보기</span><span class="grow"></span></div>
    <div class="frame-wrap"><div class="poster" style="background:${esc(c.bg)};color:${esc(c.onBg)};font-family:${esc(fb)}">
      <div class="p-logo" style="font-family:${esc(fh)};color:${esc(c.accent)}">${logo ? `<img src="${esc(logo)}" alt="">` : esc(b.logoText || b.name)}</div>
      <span class="p-kick" style="background:${esc(c.accent)};color:${esc(c.accentInk)}">이번 주 소식</span>
      <div class="p-head" style="font-family:${esc(fh)}">새로운 소식을\n<span class="p-mark" style="background-image:linear-gradient(${esc(c.accent)},${esc(c.accent)})">전해 드려요</span></div>
      <span class="p-btn" style="background:${esc(c.accent)};color:${esc(c.accentInk)}">자세히 보기</span>
      ${mascot ? `<img class="p-mascot" src="${esc(mascot)}" alt="">` : ''}
    </div></div>
    <div class="stage-foot"><span class="out-link">색과 글꼴을 바꾸면 바로 반영돼요. 실제 영상은 영상을 추가해서 보세요.</span></div>`;
}

/* ---------------------------------------------------------------- 작업 */
function trackJob(job, onDone) {
  S.jobs[job.id] = job;
  if (onDone) S.jobDone[job.id] = onDone;
  renderJobs();
  if (!pollJobs.running) pollJobs();
}
async function pollJobs() {
  pollJobs.running = true;
  while (Object.values(S.jobs).some(j => j.status === 'running')) {
    await new Promise(r => setTimeout(r, 900));
    for (const id of Object.keys(S.jobs)) {
      const j = S.jobs[id];
      if (j.status !== 'running') continue;
      try {
        const nj = await api('/api/job?id=' + id);
        S.jobs[id] = nj;
        if (nj.status !== 'running') finishJob(nj);
      } catch (e) { j.status = 'error'; j.error = e.message; finishJob(j); }
    }
    renderJobs();
  }
  pollJobs.running = false;
  renderJobs();
}
function finishJob(j) {
  const cb = S.jobDone[j.id];
  delete S.jobDone[j.id];
  if (j.status === 'error') toast(`${j.title}: ${j.error}`, true);
  if (cb) { try { cb(j); } catch (e) { console.error(e); } }
  if (j.status !== 'error') setTimeout(() => { delete S.jobs[j.id]; renderJobs(); }, 5000);
  if (j.kind === 'render' || j.kind === 'sheet') refreshState().catch(() => {});
}
function renderJobs() {
  const box = $('#jobs');
  const list = Object.values(S.jobs);
  box.innerHTML = list.map(j => `<div class="jobcard ${j.status}">
    <div class="jh"><span>${esc(j.title)}</span>${j.status === 'running' ? `<button class="btn ghost small" data-cancel="${j.id}" type="button">취소</button>` : j.status === 'error' ? `<button class="icon-btn" data-dismiss="${j.id}" type="button" aria-label="닫기">×</button>` : '<b style="color:var(--ok);font-size:12px">완료</b>'}</div>
    <div class="prog ${j.kind === 'render' ? 'rec' : ''}"><i style="width:${Math.round((j.status === 'done' ? 1 : j.progress || 0) * 100)}%"></i></div>
    <div class="jl">${esc(j.status === 'error' ? j.error : (j.log && j.log.length ? j.log[j.log.length - 1] : '준비 중'))}</div></div>`).join('');
  $$('[data-cancel]', box).forEach(b => b.onclick = () => api('/api/job/cancel', { id: b.dataset.cancel }).catch(fail));
  $$('[data-dismiss]', box).forEach(b => b.onclick = () => { delete S.jobs[b.dataset.dismiss]; renderJobs(); });
  const dj = $('#dlgJob');
  if (dj && S.jobs[dj.dataset.id]) updateDlgJob(S.jobs[dj.dataset.id]);
  updateAgentLive();
}

/* ---------------------------------------------------------------- 대화상자 */
function openDlg(html, wide) {
  const d = $('#dlg');
  d.className = wide ? 'wide' : '';
  d.innerHTML = html;
  $$('[data-close]', d).forEach(b => b.onclick = () => closeDlg());
  if (!d.open) d.showModal();
  const f = $('input:not([type=hidden]), textarea, select', d);
  if (f) f.focus();
}
function closeDlg() { const d = $('#dlg'); if (d.open) d.close(); d.innerHTML = ''; }
$('#dlg').addEventListener('cancel', () => setTimeout(() => { $('#dlg').innerHTML = ''; }, 0));

/* ---------------------------------------------------------------- AI 계정 (API 키 여러 개, 골라 쓰기) */
const isApi = () => !!(S.state && S.state.claudeEngine === 'api');
/* 연출을 맡길 수 있는지: API 모드면 키가 있어야, 구독 모드면 Claude Code 가 있어야 */
const ccOK = () => isApi() ? !!S.state.claude : !!(S.state && S.state.claudeCode);
function syncHeader() {
  const b = $('#openCC'); if (!b || !S.state) return;
  b.textContent = isApi() ? 'Claude에게 부탁 (API)' : 'Claude Code 열기';
  b.title = isApi() ? 'API 계정으로 Claude에게 파일 고치기·빌드·검수를 맡겨요' : '이 폴더에서 Claude Code를 엽니다';
}
function openClaudeCode(body, msg) {
  if (isApi()) return dlgAgent(body && body.name);
  return api('/api/claude-code', body).then(() => toast(msg || 'Claude Code 창을 열었어요')).catch(fail);
}

/* API 모드의 작업 도우미: Claude 가 API 로 파일을 읽고 고치고 빌드·장면 모음 확인까지 */
async function dlgAgent(name, opts = {}) {
  let A;
  try { A = await api('/api/agent/session', { name: name || null, session: opts.fresh ? null : (opts.session || null) }); } catch (e) { return fail(e); }
  if (opts.fresh) A = { ...A, session: null, transcript: [], usd: 0 };
  const running = () => S.agentJob && S.jobs[S.agentJob] && S.jobs[S.agentJob].status === 'running';
  const vname = name ? ((S.state.videos || []).find(v => v.name === name) || {}).title || name : '';
  const msgs = () => A.transcript.length ? A.transcript.map(m => m.role === 'tool'
      ? `<div class="ag-tool">${esc(m.text)}</div>`
      : `<div class="ag-msg ${m.role}"><b>${m.role === 'user' ? '나' : 'Claude'}</b><div>${esc(m.text)}</div></div>`).join('')
    : `<p class="hint">아직 나눈 대화가 없어요. 아래에 부탁할 말을 적고 보내면 Claude가 파일을 읽고 고치고, 빌드와 장면 모음까지 직접 보고 확인해요.</p>`;
  const draw = () => {
    const prefill = A.transcript.length ? '' : (opts.text || A.suggest || '');
    openDlg(`<div class="dlg-h"><h2>Claude에게 부탁하기 <span class="hint">API${vname ? ' · ' + esc(vname) : ''}</span></h2><button class="icon-btn" data-close type="button" aria-label="닫기">×</button></div>
      <div class="dlg-b agent">
        <div class="ag-meta hint">계정 '${esc(S.state.claudeAccount || '')}' · 모델 ${esc(A.model)} · 한 번 부탁 예산 ${A.budget}달러${A.session ? ` · 이 대화 누적 약 ${Number(A.usd).toFixed(2)}달러` : ''}
          <button class="linkbtn" data-ag="new" type="button" ${A.session ? '' : 'hidden'}>새 대화</button></div>
        <div class="ag-log" id="agLog">${msgs()}<div class="ag-live" id="agLive"></div></div>
        <form id="agForm" class="ag-form"><textarea id="agText" rows="3" placeholder="${A.session ? '이어서 부탁할 말 (예: 9:16 세이프존 침범 고쳐 줘 / 가격은 4,500원이야)' : '부탁할 말'}">${esc(prefill)}</textarea>
          <div class="ag-acts">${modelSelect()}<button class="btn solid small" type="submit" id="agSend">${A.session ? '이어서 부탁하기' : '보내기'}</button></div></form>
        <p class="hint">Claude가 쓴 만큼 API 요금이 나가요(Opus 기준 영상 하나 다듬기에 보통 1~3달러). 한 번 부탁이 예산을 넘으면 멈추고, '계속해 줘'로 이어 갈 수 있어요. 앱·도구 파일은 고치지 않아요.</p>
      </div><div class="dlg-f"><button class="btn ghost" data-close type="button">닫기</button></div>`, true);
    const d = $('#dlg');
    const log = $('#agLog', d); log.scrollTop = log.scrollHeight;
    const nb = $('[data-ag=new]', d); if (nb) nb.onclick = () => dlgAgent(name, { fresh: true });
    $$('[data-act=claude-model],[data-act=claude-effort]', d).forEach(el => el.onchange = async () => { await setClaudeOpt(el.dataset.act === 'claude-model' ? 'model' : 'effort', el.value); dlgAgent(name, { session: A.session }); });
    $$('[data-act=accounts]', d).forEach(el => el.onclick = () => dlgAccounts());
    if (running()) setBusy(true);
    $('#agForm', d).onsubmit = async e => {
      e.preventDefault();
      if (running()) return;
      const text = $('#agText', d).value.trim();
      if (!text) return $('#agText', d).focus();
      setBusy(true);
      A.transcript.push({ role: 'user', text });
      const lv = $('#agLive', d); lv.insertAdjacentHTML('beforebegin', `<div class="ag-msg user"><b>나</b><div>${esc(text)}</div></div>`); $('#agText', d).value = '';
      try {
        const j = await api('/api/agent/run', { name: name || null, text, session: A.session });
        A.session = j.session; S.agentJob = j.id;
        trackJob(j, async done => {
          S.agentJob = null;
          if (name && S.detail && S.detail.name === name) { try { await selectVideo(name); } catch (_) { /* 다시 열 때 갱신 */ } }
          if ($('#agLog')) dlgAgent(name, { session: A.session });
          if (done.status === 'done') toast(`Claude가 끝냈어요 · 이 대화 누적 약 ${Number((done.result || {}).usd || 0).toFixed(2)}달러`);
        });
      } catch (err) { setBusy(false); fail(err); }
    };
  };
  const setBusy = on => { const b = $('#agSend'); if (b) { b.disabled = on; b.textContent = on ? 'Claude가 일하는 중…' : (A.session ? '이어서 부탁하기' : '보내기'); } };
  draw();
}
function updateAgentLive() {
  const lv = $('#agLive'); if (!lv || !S.agentJob) return;
  const j = S.jobs[S.agentJob]; if (!j) return;
  lv.innerHTML = (j.log || []).slice(-14).map(l => `<div class="ag-tool">${esc(l)}</div>`).join('') + (j.status === 'running' ? '<div class="ag-tool ag-dots">일하는 중…</div>' : '');
  const lg = $('#agLog'); if (lg) lg.scrollTop = lg.scrollHeight;
}
async function dlgAccounts(tab) {
  let A;
  try { A = await api('/api/accounts', { op: 'list' }); } catch (e) { return fail(e); }
  S.acctTab = tab || S.acctTab || 'claude';
  const apply = r => {
    A = r;
    Object.assign(S.state, r.status || {});
    syncHeader();
    draw();
    if (S.detail) renderEditor();
  };
  const call = async (body, okMsg) => { try { apply(await api('/api/accounts', body)); if (okMsg) toast(okMsg); return true; } catch (e) { fail(e); return false; } };
  const rows = p => {
    const P = A[p];
    if (!P.items.length) return `<p class="hint acct-empty">저장된 키가 없어요. 아래에서 넣어 주세요.</p>`;
    return `<ul class="acct-list">${P.items.map(it => {
      const on = it.id === P.active;
      const chk = it.checked ? `<span class="acct-chk ${it.ok ? 'ok' : 'bad'}">${it.ok ? '확인됨' : '안 됨'} · ${esc(it.checked)}</span>` : '';
      return `<li class="${on ? 'on' : ''}"><label class="acct-pick"><input type="radio" name="acct-${p}" value="${esc(it.id)}" ${on ? 'checked' : ''}>
        <b>${esc(it.name)}</b><span class="acct-tail">…${esc(it.tail)}</span></label>${chk}
        <span class="acct-acts"><button class="linkbtn" data-a="test" data-id="${esc(it.id)}" type="button">확인</button>
        <button class="linkbtn" data-a="rename" data-id="${esc(it.id)}" type="button">이름</button>
        <button class="linkbtn" data-a="remove" data-id="${esc(it.id)}" type="button">지우기</button></span></li>`;
    }).join('')}</ul>`;
  };
  const draw = () => {
    const p = S.acctTab, P = A[p], eng = A.engine;
    const claudeTop = p === 'claude' ? `<div class="acct-engine"><span class="lbl">앱의 Claude 기능을 무엇으로 돌릴까요?</span>
        <label class="check"><input type="radio" name="acctEngine" value="code" ${eng !== 'api' ? 'checked' : ''}>Claude Code 로그인 <span class="hint">(Pro·Max 구독, 이 PC의 Claude Code${(A.status || {}).claudeCode ? '' : ' — 지금 이 PC에서 못 찾음'})</span></label>
        <label class="check"><input type="radio" name="acctEngine" value="api" ${eng === 'api' ? 'checked' : ''}>Claude API 키 <span class="hint">(아래에서 고른 계정, 쓴 만큼 요금)</span></label>
        <p class="hint">둘 중 고른 쪽으로 앱의 모든 Claude 작업이 돌아가요. API로 두면 문구·구성 맡기기, 업로드 글, 사진 검색어는 물론 연출 짜기·다듬기도 Claude Code 창 대신 앱 안 'Claude에게 부탁하기'에서 고른 키로 돌아가요(파일 읽고 고치기, 빌드, 장면 모음 확인까지). 구독으로 두면 모두 이 PC의 Claude Code 로그인으로 돌아가요. API 요금은 100만 토큰당 Opus 4/20달러, Sonnet 2/10달러(입력/출력)쯤이고, 작업 기록에 쓴 토큰과 대략의 요금이 남아요.</p>
        ${eng === 'api' ? `<label class="acct-budget">부탁 한 번 예산 <input id="acctBudget" type="number" min="0.5" max="50" step="0.5" value="${esc(A.budget || 3)}"> 달러 <span class="hint">(넘으면 멈추고 물어봐요)</span></label>` : ''}</div>` : '';
    openDlg(`<div class="dlg-h"><h2>AI 계정</h2><button class="icon-btn" data-close type="button" aria-label="닫기">×</button></div>
      <div class="dlg-b acct">
        <div class="look-chips acct-tabs"><button type="button" class="chipf ${p === 'claude' ? 'on' : ''}" data-tab="claude">Claude</button><button type="button" class="chipf ${p === 'gemini' ? 'on' : ''}" data-tab="gemini">Gemini (음악)</button></div>
        ${claudeTop}
        <span class="lbl">${esc(P.label)} 계정 ${P.items.length ? '<span class="hint">· 동그라미를 누르면 그 계정으로 바뀌어요</span>' : ''}</span>
        ${rows(p)}
        <form class="acct-add" id="acctAdd"><input id="acctName" type="text" maxlength="30" placeholder="이름 (예: 회사 계정)"><input id="acctKey" type="password" autocomplete="off" placeholder="${esc(P.hint)}"><button class="btn solid small" type="submit">추가하고 쓰기</button></form>
        <p class="hint">키는 이 PC 사용자 폴더(.motion-studio)에만, Windows에서는 이 사용자만 풀 수 있게 암호화해서 저장해요. 화면에는 끝 네 자리만 보여요.
          ${p === 'claude' ? '<button class="linkbtn" data-web="https://console.anthropic.com/settings/keys" type="button">Claude 콘솔에서 키 만들기</button>' : '<button class="linkbtn" data-web="https://aistudio.google.com/apikey" type="button">AI Studio에서 키 만들기</button>'}</p>
        ${p === 'claude' && A.envClaude ? '<p class="hint">이 PC에 ANTHROPIC_API_KEY 환경 변수가 있어요. Claude Code 로그인 방식에서는 앱이 그 변수를 빼고 Claude Code를 열어요.</p>' : ''}
      </div><div class="dlg-f"><button class="btn solid" data-close type="button">닫기</button></div>`, true);
    const d = $('#dlg');
    $$('[data-tab]', d).forEach(b => b.onclick = () => { S.acctTab = b.dataset.tab; draw(); });
    const bud = $('#acctBudget', d); if (bud) bud.onchange = () => call({ op: 'budget', budget: +bud.value || 3 }, `부탁 한 번 예산을 ${+bud.value || 3}달러로 바꿨어요`);
    $$('[name=acctEngine]', d).forEach(r => r.onchange = () => {
      if (r.value === 'api' && !A.claude.items.length) toast('API 키를 하나 넣어야 API로 돌아가요', true);
      call({ op: 'engine', engine: r.value }, r.value === 'api' ? 'Claude를 API 키로 쓰도록 바꿨어요' : 'Claude Code 로그인으로 쓰도록 바꿨어요');
    });
    $$(`[name=acct-${p}]`, d).forEach(r => r.onchange = () => call({ op: 'use', provider: p, id: r.value }, `'${P.items.find(x => x.id === r.value).name}' 계정으로 바꿨어요`));
    $$('[data-a]', d).forEach(b => b.onclick = async () => {
      const id = b.dataset.id, it = P.items.find(x => x.id === id);
      if (b.dataset.a === 'remove') { if (confirm(`'${it.name}' 키를 지울까요? 이 PC에서만 지워지고, 키 자체는 콘솔에 그대로 있어요.`)) call({ op: 'remove', provider: p, id }, '지웠어요'); }
      else if (b.dataset.a === 'rename') { const n = prompt('새 이름', it.name); if (n && n.trim()) call({ op: 'rename', provider: p, id, name: n.trim() }); }
      else { b.textContent = '확인 중…'; try { const r = await api('/api/accounts', { op: 'test', provider: p, id }); apply(r); toast(r.test.msg, !r.test.ok); } catch (e) { fail(e); draw(); } }
    });
    $$('[data-web]', d).forEach(b => b.onclick = () => api('/api/open-web', { url: b.dataset.web }).catch(fail));
    $('#acctAdd', d).onsubmit = async e => {
      e.preventDefault();
      const key = $('#acctKey', d).value.trim();
      if (!key) return $('#acctKey', d).focus();
      const ok = await call({ op: 'add', provider: p, name: $('#acctName', d).value.trim(), key }, '키를 저장하고 이 계정으로 바꿨어요');
      if (ok && p === 'gemini' && S.detail) { try { S.musicStatus = await api('/api/music/status'); renderEditor(); } catch (_) { /* 음악 칸은 다음에 그릴 때 갱신 */ } }
    };
  };
  draw();
}

function suggestSlug(prefix) {
  const d = new Date();
  const base = `${prefix}-${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
  let s = base, i = 2;
  while (S.state.videos.some(v => v.name === s)) s = `${base}-${i++}`;
  return s;
}

function dlgNewBrand() {
  openDlg(`<div class="dlg-h"><h2>광고 계정 추가</h2><button class="icon-btn" data-close type="button" aria-label="닫기">×</button></div>
    <form id="nbForm"><div class="dlg-b">
      <div class="row"><div class="field"><label class="lbl" for="nbName">계정 이름</label><input id="nbName" type="text" required placeholder="예) 민트 필라테스"></div>
      <div class="field"><label class="lbl" for="nbSlug">영문 이름</label><input id="nbSlug" type="text" required pattern="[a-z0-9][a-z0-9\\-]*" placeholder="예) mint-pilates"><div class="hint">폴더 이름으로 써요. 영문 소문자·숫자·하이픈</div></div></div>
      <div class="field"><label class="lbl" for="nbLogo">로고 (있으면)</label><input id="nbLogo" type="file" accept="image/*"><div class="hint">로고에서 색을 뽑아 배경·강조색을 정해요.</div></div>
      <div class="row"><div class="field"><label class="lbl" for="nbAccent">강조색</label><div class="color" style="grid-template-columns:38px 1fr"><input type="color" id="nbAccentC" value="#F28C28" aria-label="강조색"><input id="nbAccent" type="text" placeholder="로고가 있으면 비워 두세요"></div></div>
      <div class="field"><span class="lbl">분위기</span><div class="choice" style="grid-template-columns:1fr 1fr"><label><input type="radio" name="nbTone" value="dark" checked><b>어두운 배경</b></label><label><input type="radio" name="nbTone" value="light"><b>밝은 배경</b></label></div></div></div>
      <label class="check"><input type="checkbox" id="nbSerif">제목을 명조로</label>
    </div>
    <div class="dlg-f"><button class="btn ghost" data-close type="button">취소</button><button class="btn solid" type="submit">만들기</button></div></form>`);
  $('#nbAccentC').oninput = e => { $('#nbAccent').value = e.target.value.toUpperCase(); };
  $('#nbForm').onsubmit = async e => {
    e.preventDefault();
    const btn = $('#nbForm [type=submit]'); btn.disabled = true; btn.textContent = '만드는 중…';
    try {
      const body = { slug: $('#nbSlug').value.trim(), name: $('#nbName').value.trim(), accent: $('#nbAccent').value.trim() || null,
        light: $('[name=nbTone]:checked').value === 'light', serif: $('#nbSerif').checked };
      const lf = $('#nbLogo').files[0];
      if (lf) { const up = await upload(lf); body.logo = up.id; body.palette = up.id; }
      const r = await api('/api/brand/create', body);
      closeDlg();
      await refreshState();
      await selectBrand(r.brand.slug);
      (r.messages || []).forEach(m => toast(m));
    } catch (err) { btn.disabled = false; btn.textContent = '만들기'; fail(err); }
  };
}

const tplOrder = ts => [...ts].filter(t => t !== 'deck').sort((a, b) => (a === 'promo' ? -1 : b === 'promo' ? 1 : a.localeCompare(b)));
function dlgNewVideo(brand) {
  const st = S.state;
  const all = st.presets || [];
  const presets = all.filter(p => p.group !== 'free' && p.group !== 'look'), freeP = all.filter(p => p.group === 'free'), lookP = all.filter(p => p.group === 'look');
  const lookCard = p => { const sty = styleOf(p.style); return `<label class="pcard lookc"><input type="radio" name="nvPreset" value="${esc(p.id)}">
          ${sty && sty.thumb ? `<img src="${esc(sty.thumb)}" alt="" loading="lazy">` : ''}<b>${esc(p.name)}</b><span class="look">${esc(p.look || '')}</span>
          <span class="meta">${sty ? `스타일 ${esc(sty.name)}` : ''}</span></label>`; };
  const card = (p, checked) => `<label class="pcard"><input type="radio" name="nvPreset" value="${esc(p.id)}" ${checked ? 'checked' : ''}>
          <b>${esc(p.name)}</b><span class="look">${esc(p.look || '')}</span>
          <span class="meta">${(p.photos && p.photos.need) ? `사진 ${p.photos.need}장` : '사진 없이'} · ${Math.round(p.seconds || 0)}초${(p.formats || []).length === 1 ? ' · 1:1' : ''}</span></label>`;
  openDlg(`<div class="dlg-h"><h2>영상 추가</h2><button class="icon-btn" data-close type="button" aria-label="닫기">×</button></div>
    <form id="nvForm"><div class="dlg-b">
      ${presets.length ? `<div class="field"><span class="lbl">어떤 상황인가요?</span>
        <div class="preset-grid">${presets.map((p, i) => card(p, i === 0)).join('')}</div></div>` : ''}
      ${lookP.length ? `<div class="field"><span class="lbl">결로 고르기 <span class="hint">같은 문구로 결만 바꿔 볼 수 있어요</span></span>
        <div class="preset-grid look-grid">${lookP.map(lookCard).join('')}</div></div>` : ''}
      <div class="field"><span class="lbl">직접 만들기</span>
        <div class="preset-grid">${freeP.map(p => card(p, !presets.length)).join('')}
          <label class="pcard free"><input type="radio" name="nvPreset" value="__scratch" ${ccOK() ? '' : 'disabled'}><b>처음부터 새로 짜기</b><span class="look">원하는 영상을 글로 적으면 Claude Code가 그 영상만의 연출을 짜요</span>
            <span class="meta">${ccOK() ? (isApi() ? 'Claude API · 시간이 좀 걸려요' : 'Claude Code · 시간이 좀 걸려요') : (isApi() ? 'API 키가 있어야 해요' : 'Claude Code가 있어야 해요')}</span></label>
          <label class="pcard free"><input type="radio" name="nvPreset" value="" ${!presets.length && !freeP.length ? 'checked' : ''}><b>템플릿 고르기</b><span class="look">템플릿을 골라 처음부터</span><span class="meta">사진형 · 글자형 · 필름</span></label>
        </div></div>
      <p class="hint" id="nvSum"></p>
      <div class="field" id="nvScratchBox" hidden><label class="lbl" for="nvBrief">어떤 영상을 원하나요?</label>
        <textarea id="nvBrief" rows="4" placeholder="예) 우리 센서가 공장 설비에 붙어 데이터를 보내고, 대시보드가 불량 신호를 미리 알려 주는 과정을 그림처럼 보여 주는 20초 영상. 마지막엔 홈페이지 주소."></textarea>
        <label class="check"><input type="checkbox" id="nvOpenCC" checked>만들고 바로 Claude Code 열기</label></div>
      <div class="field"><label class="lbl" for="nvBrand">광고 계정</label><select id="nvBrand">${st.brands.map(b => `<option value="${esc(b.slug)}" ${b.slug === brand ? 'selected' : ''}>${esc(b.name)}</option>`).join('')}</select></div>
      <div class="row"><div class="field"><label class="lbl" for="nvTitle">영상 제목</label><input id="nvTitle" type="text" required placeholder="예) 10월 체험 수업"></div>
      <div class="field"><label class="lbl" for="nvName">영문 이름</label><input id="nvName" type="text" required pattern="[a-z0-9][a-z0-9\\-]*" value="${esc(suggestSlug(brand || 'ad'))}"></div></div>
      <div class="field" id="nvTplBox" hidden><span class="lbl">종류</span><div class="choice">${tplOrder(st.templates).map((t, i) => { const ti = TEMPLATE_INFO[t] || { name: t, desc: '' }; return `<label><input type="radio" name="nvTpl" value="${esc(t)}" ${i === 0 ? 'checked' : ''}><b>${esc(ti.name)}</b><span>${esc(ti.desc)}</span></label>`; }).join('')}</div></div>
      <div class="field"><span class="lbl">만들 형식</span><div class="fmt-checks">${FMT_KEYS.map(f => `<label data-f="${f}"><input type="checkbox" name="nvFmt" value="${f}" checked>${ratioIcon(f)}${FMT[f].label} ${FMT[f].name}</label>`).join('')}</div></div>
    </div>
    <div class="dlg-f"><button class="btn ghost" data-close type="button">취소</button><button class="btn solid" type="submit">만들기</button></div></form>`, true);
  const val = () => { const el = $('[name=nvPreset]:checked'); return el ? el.value : ''; };
  const pick = () => all.find(p => p.id === val()) || null;
  const sync = () => {
    const pr = pick(), scratch = val() === '__scratch';
    $('#nvTplBox').hidden = !!pr || scratch;
    $('#nvScratchBox').hidden = !scratch;
    $('#nvBrief').required = scratch;
    const allowed = pr ? pr.formats || FMT_KEYS : FMT_KEYS;
    $$('.fmt-checks label[data-f]').forEach(l => { const on = allowed.includes(l.dataset.f); l.hidden = !on; const cb = $('input', l); cb.checked = on; });
    $('#nvTitle').placeholder = pr ? `예) ${pr.name}` : scratch ? '예) 센서 데이터 흐름 소개' : '예) 10월 체험 수업';
    $('#nvSum').textContent = scratch ? '템플릿으로 안 되는 영상을 Claude Code가 이 영상만을 위해 처음부터 짜요. 장면 계획을 먼저 보여 주고, 빠진 정보는 물어봐요.'
      : pr ? `${pr.summary || ''}${pr.photos && pr.photos.need ? ` 필요한 사진: ${pr.photos.hint}.` : ''}` : '사진형·글자형·필름 템플릿 중에서 직접 골라요.';
  };
  $$('[name=nvPreset]').forEach(r => r.onchange = sync);
  sync();
  $('#nvBrand').onchange = e => { $('#nvName').value = suggestSlug(e.target.value); };
  $('#nvForm').onsubmit = async e => {
    e.preventDefault();
    const formats = $$('[name=nvFmt]:checked').map(x => x.value);
    if (!formats.length) return toast('형식을 하나 이상 골라 주세요', true);
    const pr = pick(), scratch = val() === '__scratch';
    const brief = ($('#nvBrief').value || '').trim();
    if (scratch && brief.length < 5) { $('#nvBrief').focus(); return toast('어떤 영상을 원하는지 한두 문장 적어 주세요', true); }
    const btn = $('#nvForm [type=submit]'); btn.disabled = true;
    try {
      const body = { name: $('#nvName').value.trim(), brand: $('#nvBrand').value, formats, title: $('#nvTitle').value.trim() };
      if (scratch) Object.assign(body, { scratch: true, brief, openClaude: $('#nvOpenCC').checked });
      else Object.assign(body, { template: pr ? pr.template : $('[name=nvTpl]:checked').value, preset: pr ? pr.id : null });
      const r = await api('/api/video/create', body);
      closeDlg();
      await refreshState();
      S.tab = scratch ? 'direct' : 'copy'; S.aiOpen = true; S.dirOpen = false; S.musicGen = null;
      await selectVideo(r.name);
      if (scratch && isApi() && body.openClaude) dlgAgent(r.name);
      else if (scratch) toast(r.claudeOpened ? 'Claude Code 창을 열었어요. 거기서 장면 계획을 확인하고 진행해 주세요' : '영상을 만들었어요. 연출 탭에서 Claude Code에게 맡겨 주세요');
      else if (pr && pr.template === 'scenes') toast('장면 쌓기 영상을 만들었어요. 무엇을 알릴지 적고 구성을 받아 보거나, 장면을 직접 더하세요');
      else if (pr) toast(`${pr.name} 영상을 만들었어요. 무엇을 알릴지 적고 초안을 받아 보세요`);
    } catch (err) { btn.disabled = false; fail(err); }
  };
}

function dlgDuplicate() {
  const d = S.detail, st = S.state;
  openDlg(`<div class="dlg-h"><h2>영상 복제</h2><button class="icon-btn" data-close type="button" aria-label="닫기">×</button></div>
    <form id="dpForm"><div class="dlg-b">
      <p class="hint" style="margin-top:0">문구 버전을 나눠 시험하거나, 같은 구성을 다른 계정에 쓸 때 편해요.</p>
      <div class="field"><label class="lbl" for="dpBrand">광고 계정</label><select id="dpBrand">${st.brands.map(b => `<option value="${esc(b.slug)}" ${b.slug === d.video.brand ? 'selected' : ''}>${esc(b.name)}</option>`).join('')}</select></div>
      <div class="row"><div class="field"><label class="lbl" for="dpTitle">새 제목</label><input id="dpTitle" type="text" value="${esc((d.video.title || d.name) + ' B')}"></div>
      <div class="field"><label class="lbl" for="dpName">새 영문 이름</label><input id="dpName" type="text" required pattern="[a-z0-9][a-z0-9\\-]*" value="${esc(d.name + '-b')}"></div></div>
    </div><div class="dlg-f"><button class="btn ghost" data-close type="button">취소</button><button class="btn solid" type="submit">복제</button></div></form>`);
  $('#dpForm').onsubmit = async e => {
    e.preventDefault();
    try {
      saveVideo.flush();
      const r = await api('/api/video/duplicate', { name: d.name, newName: $('#dpName').value.trim(), title: $('#dpTitle').value.trim(), brand: $('#dpBrand').value });
      closeDlg(); await refreshState(); await selectVideo(r.name); toast('복제했어요');
    } catch (err) { fail(err); }
  };
}

async function dlgCheck() {
  saveVideo.flush();
  try {
    const r = await api('/api/check?name=' + encodeURIComponent(S.detail.name));
    const items = r.errors.map(x => `<li class="e"><em>고칠 것</em><span>${esc(x)}</span></li>`).concat(r.notes.map(x => `<li class="n"><em>확인</em><span>${esc(x)}</span></li>`));
    openDlg(`<div class="dlg-h"><h2>점검 결과</h2><button class="icon-btn" data-close type="button" aria-label="닫기">×</button></div>
      <div class="dlg-b">${items.length ? `<ul class="issues">${items.join('')}</ul>` : '<p>걸리는 게 없어요. 장면 모음으로 화면도 한 번 확인해 보세요.</p>'}</div>
      <div class="dlg-f"><button class="btn solid" data-close type="button">확인</button></div>`);
  } catch (e) { fail(e); }
}

async function runSheet() {
  saveVideo.flush();
  const name = S.detail.name, fmt = S.fmt, safe = S.safe;
  try {
    const job = await api('/api/job/sheet', { name, formats: [fmt], safe });
    toast(S.detail.video.template === 'deck' ? '장 모음을 만드는 중이에요' : '장면 모음을 만드는 중이에요');
    trackJob(job, j => {
      if (j.status !== 'done') return;
      const s = j.result.sheets[0];
      openDlg(`<div class="dlg-h"><h2>${j.result.deck ? '장 모음' : `장면 모음 · ${FMT[fmt].label}${safe ? ' · 세이프존' : ''}`}</h2><button class="icon-btn" data-close type="button" aria-label="닫기">×</button></div>
        <div class="dlg-b"><p class="hint" style="margin-top:0">${j.result.deck ? '장마다 등장이 끝난 화면이에요. 글자 넘침, 겹침, 사진 초점을 확인하세요.' : '영상 전체에서 고르게 12장면을 뽑았어요. 글자 넘침, 겹침, 사진 초점을 확인하세요.'}</p><img class="sheet-img" src="${esc(s.url)}" alt="장면 모음"></div>
        <div class="dlg-f"><button class="btn solid" data-close type="button">닫기</button></div>`, true);
    });
  } catch (e) { fail(e); }
}

function dlgRender() {
  saveVideo.flush();
  const d = S.detail, fm = d.video.formats || FMT_KEYS;
  if (!S.state.ffmpeg) return toast('ffmpeg가 없어 MP4를 만들 수 없어요. 설치 프로그램을 다시 실행해 주세요.', true);
  const m = d.music || {};
  openDlg(`<div class="dlg-h"><h2>MP4 만들기</h2><button class="icon-btn" data-close type="button" aria-label="닫기">×</button></div>
    <div class="dlg-b" id="rBody">
      <div class="field"><span class="lbl">형식</span><div class="fmt-checks">${fm.map(f => `<label><input type="checkbox" name="rFmt" value="${f}" checked>${ratioIcon(f)}${FMT[f].label} ${FMT[f].name}</label>`).join('')}</div></div>
      <p class="hint">${m.file ? `배경음악: ${esc(m.name || m.file)} (음량 ${Math.round((m.volume ?? 1) * 100)}%)` : '배경음악 없이 무음 트랙으로 만들어요. 음악은 3번 음악 탭에서 넣을 수 있어요.'}</p>
      ${fm.some(f => (d.outputs[f] || {}).master) ? `<label class="check"><input type="checkbox" id="rReuse">화면은 전에 만든 그대로 두고 음악만 다시 합치기 (몇 초면 끝나요)</label>` : ''}
      <p class="hint">${isFilm(d.video.template) ? '필름 템플릿은 60fps 모션 블러라 20초 영상 하나에 10분 안팎 걸려요.' : '20초 영상 한 형식에 1~2분쯤 걸려요.'} 창을 닫아도 아래 작업 알림에서 계속 진행돼요.</p>
    </div>
    <div class="dlg-f"><button class="btn ghost" data-close type="button">닫기</button><button class="btn rec" id="rGo" type="button">만들기 시작</button></div>`);
  $('#rGo').onclick = async () => {
    const formats = $$('[name=rFmt]:checked').map(x => x.value);
    if (!formats.length) return toast('형식을 하나 이상 골라 주세요', true);
    try {
      const job = await api('/api/job/render', { name: d.name, formats, reuse: !!($('#rReuse') && $('#rReuse').checked) });
      $('#rBody').innerHTML = `<div id="dlgJob" data-id="${job.id}"><div class="prog rec"><i></i></div><div class="joblog"></div></div>`;
      $('#rGo').remove();
      trackJob(job, j => {
        if (j.status === 'done') {
          toast('MP4가 완성됐어요');
          if (S.detail && S.detail.name === d.name) api('/api/video?name=' + encodeURIComponent(d.name)).then(x => { S.detail.outputs = x.outputs; S.detail.status = x.status; renderStage(); }).catch(() => {});
          const dj = $('#dlgJob');
          if (dj && dj.dataset.id === j.id) showOutputs(j.result);
        }
      });
    } catch (e) { fail(e); }
  };
}
function updateDlgJob(j) {
  const dj = $('#dlgJob'); if (!dj) return;
  const i = $('.prog i', dj); if (i) i.style.width = Math.round((j.status === 'done' ? 1 : j.progress || 0) * 100) + '%';
  const lg = $('.joblog', dj); if (lg && j.log) { lg.textContent = j.log.slice(-12).join('\n'); lg.scrollTop = lg.scrollHeight; }
  if (j.status === 'error' && lg) lg.textContent += '\n\n' + j.error;
}
function showOutputs(r) {
  const body = $('#rBody'); if (!body) return;
  body.innerHTML = `<p style="margin:0 0 4px">다 만들었어요. 바로 올릴 수 있는 MP4예요.</p>
    <div class="outs">${r.files.map(f => `<figure><video src="${esc(f.url)}" controls preload="metadata"></video><figcaption>${ratioIcon(f.format)}${FMT[f.format].label} ${FMT[f.format].name}</figcaption></figure>`).join('')}</div>`;
  const foot = $('#dlg .dlg-f');
  if (foot && !$('#openOuts')) { const b = document.createElement('button'); b.className = 'btn solid'; b.id = 'openOuts'; b.type = 'button'; b.textContent = '폴더 열기'; b.onclick = () => api('/api/open', { path: `out/${S.detail ? S.detail.name : ''}` }).catch(fail); foot.appendChild(b); }
}
function dlgPlay(files) {
  openDlg(`<div class="dlg-h"><h2>완성본</h2><button class="icon-btn" data-close type="button" aria-label="닫기">×</button></div>
    <div class="dlg-b"><div class="outs" style="grid-template-columns:1fr">${files.map(f => `<figure><video src="${esc(f.url)}" controls autoplay style="max-height:70vh"></video></figure>`).join('')}</div></div>
    <div class="dlg-f"><button class="btn ghost" id="pOpen" type="button">폴더 열기</button><button class="btn solid" data-close type="button">닫기</button></div>`);
  $('#pOpen').onclick = () => api('/api/open', { path: `out/${S.detail.name}/${files[0].format}` }).catch(fail);
}

boot();
