"""keyframe.gallery 영상에서 스타일을 자동으로 배우기 (Claude API, AI 계정에서 고른 키).

    python tools/learn_gallery.py run --list out/_app/learn/gallery.json [--budget 90] [--max 80]
    python tools/learn_gallery.py status

단계
  1. 훑기(Sonnet): 아직 안 본 영상마다 스토리보드 12장을 한 장으로 보고, 광고 모션으로 쓸 만한지·지금 라이브러리에 없는 결인지 점수
  2. 고르기(Opus): 훑은 결과에서 서로 겹치지 않는 결을 최대 --max 개 고름
  3. 쓰기(Opus): 고른 영상의 프레임을 촘촘히 보고 style.json·style.md 작성 → styles.py check (오류면 한 번 고침)
  4. 점검(Opus): 썸네일을 만들어 원본 프레임과 비교, 7점 이상이면 styles/ 에 남기고 아니면 한 번 고친 뒤 다시 보고,
     그래도 모자라면 styles/_review/ 로 옮김(목록·설치 파일에는 안 나옴)

원본 영상의 그림은 임시 폴더(%TEMP%/ms-learn)에만 받고 끝나면 지워요. 프로젝트에는 원리(색 비율·글꼴 성격·질감·움직임)만 남아요.
진행 상태는 out/_app/learn/state.json 에 남아서 끊겨도 이어서 돌아요. 쓴 돈이 --budget 에 닿으면 멈춰요.
"""
import base64
import concurrent.futures as cf
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT  # noqa: E402

LEARN = ROOT / "out" / "_app" / "learn"
STATE = LEARN / "state.json"
TMP = Path(tempfile.gettempdir()) / "ms-learn"
SDIR = ROOT / "styles"
API_URL = os.environ.get("MOTION_STUDIO_ANTHROPIC_URL") or "https://api.anthropic.com/v1/messages"
OPUS, SONNET = "claude-opus-5-5", "claude-sonnet-5-5"
PRICES = {OPUS: (4, 20), SONNET: (2, 10)}
TEMPLATES = ["typeslam", "uidemo", "sketchbook", "dataflow", "terminal", "collage", "stage", "glow", "brandmark", "cinema"]
LOCK = threading.Lock()


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with LOCK:
        with open(LEARN / "learn.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")


# ------------------------------------------------------------------ 상태·비용
def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"usd": 0.0, "videos": {}, "picked": [], "done": {}}


def save_state(st):
    with LOCK:
        tmp = STATE.with_suffix(".tmp")
        tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, STATE)


class Budget(Exception):
    pass


def call(st, key, model, system, content, max_tokens=4000, effort=None, budget=90.0, history=None):
    """Messages API 한 번 (스트리밍). 비용을 상태에 더함. (답 글, 메시지 기록)"""
    import agent
    if st["usd"] >= budget:
        raise Budget()
    msgs = (history or []) + [{"role": "user", "content": content}]
    body = {"model": model, "max_tokens": max_tokens, "stream": True, "messages": msgs,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]}
    if effort:
        body["output_config"] = {"effort": effort}
    for tries in range(1, 6):
        try:
            out, usage, _ = agent._stream(body, key, lambda n: None)
            break
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")[:300]
            if e.code in (429, 500, 502, 503, 529) and tries < 5:
                time.sleep(tries * 20)
                continue
            raise RuntimeError(f"HTTP {e.code}: {raw}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if tries < 5:
                time.sleep(tries * 10)
                continue
            raise RuntimeError(str(e))
    pin, pout = PRICES[model]
    cw, cr = int(usage.get("cache_creation_input_tokens") or 0), int(usage.get("cache_read_input_tokens") or 0)
    usd = (int(usage.get("input_tokens") or 0) * pin + cw * pin * 1.25 + cr * pin * .1 + int(usage.get("output_tokens") or 0) * pout) / 1e6
    with LOCK:
        st["usd"] += usd
    text = "".join(b.get("text", "") for b in out if b.get("type") == "text")
    clean = [{k: v for k, v in b.items() if not k.startswith("_")} for b in out]
    return text, msgs + [{"role": "assistant", "content": clean}]


def jpart(text, want=None):
    """답에서 JSON 하나 꺼내기"""
    cands = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S) or re.findall(r"(\{.*\})", text, re.S)
    for c in reversed(cands):
        try:
            d = json.loads(c)
            if not want or all(k in d for k in want):
                return d
        except json.JSONDecodeError:
            continue
    raise ValueError("JSON 을 찾지 못했어요")


# ------------------------------------------------------------------ 프레임
def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": "MotionStudio/1.0 (style learning)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def storyboard(pid):
    """(길이, [(시각, PIL 이미지)])"""
    from PIL import Image
    j = json.loads(fetch(f"https://image.mux.com/{pid}/storyboard.json"))
    sp = Image.open(io.BytesIO(fetch(j["url"]))).convert("RGB")
    tw, th = j["tile_width"], j["tile_height"]
    return j["duration"], [(t["start"], sp.crop((t["x"], t["y"], t["x"] + tw, t["y"] + th))) for t in j["tiles"]]


def sheet(tiles, cols=4, w=320, label=True):
    from PIL import Image, ImageDraw
    if not tiles:
        return None
    h = int(w * tiles[0][1].height / tiles[0][1].width)
    rows = (len(tiles) + cols - 1) // cols
    S = Image.new("RGB", (cols * (w + 4) + 4, rows * (h + 4) + 4), (18, 18, 20))
    d = ImageDraw.Draw(S)
    for n, (t, im) in enumerate(tiles):
        x, y = 4 + (n % cols) * (w + 4), 4 + (n // cols) * (h + 4)
        S.paste(im.resize((w, h)), (x, y))
        if label:
            d.rectangle((x, y, x + 46, y + 14), fill=(0, 0, 0))
            d.text((x + 3, y + 2), f"{t:.1f}s", fill=(255, 220, 0))
    return S


def jpg_block(im, q=80):
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}}


def pick(tiles, n):
    if len(tiles) <= n:
        return tiles
    return [tiles[min(len(tiles) - 1, int((i + .5) * len(tiles) / n))] for i in range(n)]


# ------------------------------------------------------------------ 라이브러리 요약
def catalog():
    rows = []
    for f in sorted(SDIR.glob("*/style.json")):
        if f.parent.name.startswith(("_", "zz-")):
            continue
        try:
            s = json.loads(f.read_text(encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        rows.append(f"- {s['id']} [{s.get('group')}] → {s.get('template')}: {s.get('summary', '')[:110]}")
    return "\n".join(rows)


def used_mux():
    out = set()
    for f in SDIR.glob("**/style.json"):
        out |= set(re.findall(r"mux:([A-Za-z0-9]+)", f.read_text(encoding="utf-8-sig")))
    return out


def font_entries():
    seen = {}
    for f in SDIR.glob("*/style.json"):
        try:
            for e in json.loads(f.read_text(encoding="utf-8-sig")).get("fonts", []):
                if (ROOT / e.get("file", "")).exists():
                    seen[(e["family"], str(e.get("weight")), e.get("style", ""))] = e
        except Exception:  # noqa: BLE001
            pass
    return "\n".join(json.dumps(v, ensure_ascii=False) for _, v in sorted(seen.items()))


# ------------------------------------------------------------------ 1. 훑기
TRIAGE_SYS = """당신은 광고 모션 그래픽 디자이너예요. 사용자는 HTML+GSAP 엔진으로 여러 광고 계정의 짧은 광고 영상(릴스·쇼츠)을 만들고,
잘 만든 프로덕트 모션 영상에서 '보는 결·움직이는 결'(색 비율, 글자 성격, 질감, 움직임·전환 방식)을 배워 스타일 라이브러리에 모으고 있어요.
지금 라이브러리에 있는 스타일:
{catalog}

영상 하나의 스토리보드(시간 순서 12장, 왼쪽 위에 초)를 보고 판단해 주세요.
- usable: 광고 모션 그래픽 스타일로 배울 만한가 (실사 촬영 위주, 화면 녹화만 계속, 말하는 사람 위주면 false)
- novelty 0~10: 위 라이브러리와 얼마나 다른 결인가 (10 = 전혀 없는 결, 3 이하 = 거의 같은 것이 있음)
- quality 0~10: 디자인 완성도
- closest: 가장 비슷한 기존 스타일 id
- group: 타이포 · 제품 UI · 그라디언트·빛 · 3D·사물 · 그래픽·도형 · 레트로·픽셀 · 손그림 · 콜라주·사진 · 다이어그램·데이터 · 시네마틱 중 하나
- hand: 손그림 결인가 (true/false)
- one_line: 이 결을 한국어 한 줄로(45자 안쪽, 회사·제품 이름 없이)
출력은 ```json 코드 블록 하나: {{"usable": true, "novelty": 7, "quality": 8, "closest": "...", "group": "...", "hand": false, "one_line": "..."}}"""


def triage_one(st, key, sysmsg, vid, pid, title, budget):
    try:
        dur, tiles = storyboard(pid)
    except Exception as e:  # noqa: BLE001
        return {"error": f"storyboard {e}"}
    im = sheet(pick(tiles, 12), cols=4, w=300)
    text, _ = call(st, key, SONNET, sysmsg, [jpg_block(im, 78), {"type": "text", "text": f"영상 길이 {dur:.0f}초. 판단 JSON 만 주세요."}],
                   max_tokens=1200, effort="low", budget=budget)
    d = jpart(text, ("usable", "novelty"))
    d["dur"] = dur
    return d


def stage_triage(st, key, gallery, budget, workers=4):
    used = used_mux()
    todo = [(str(v), pid, t) for v, pid, t, *_ in gallery if pid not in used and (str(v) not in st["videos"] or st["videos"][str(v)].get("error"))]
    log(f"1단계 훑기: {len(todo)}개 (이미 배운 {len(used)}개는 뺌)")
    sysmsg = TRIAGE_SYS.format(catalog=catalog())
    done = 0

    def job(row):
        vid, pid, title = row
        try:
            r = triage_one(st, key, sysmsg, vid, pid, title, budget)
        except Budget:
            raise
        except Exception as e:  # noqa: BLE001
            r = {"error": str(e)[:200]}
        r.update(pid=pid, title=title)
        return vid, r

    with cf.ThreadPoolExecutor(workers) as ex:
        futs = [ex.submit(job, r) for r in todo]
        for f in cf.as_completed(futs):
            try:
                vid, r = f.result()
            except Budget:
                log("예산에 닿아 훑기를 멈춰요")
                for g in futs:
                    g.cancel()
                break
            st["videos"][vid] = r
            done += 1
            if done % 20 == 0:
                save_state(st)
                log(f"  훑기 {done}/{len(todo)} · 누적 {st['usd']:.2f}달러")
    save_state(st)


# ------------------------------------------------------------------ 2. 고르기
def stage_pick(st, key, budget, max_n, more=False):
    taken = set(st["picked"]) | set(st["done"])
    nmin, qmin = (4, 7) if more else (5, 6)
    cands = [(v, r) for v, r in st["videos"].items() if r.get("usable") and not r.get("error") and v not in taken
             and r.get("novelty", 0) >= nmin and r.get("quality", 0) >= qmin]
    cands.sort(key=lambda x: -(x[1]["novelty"] * 1.2 + x[1]["quality"]))
    cands = cands[:220]
    log(f"2단계 고르기: 후보 {len(cands)}개 → 최대 {max_n}개")
    if not cands:
        return
    lines = "\n".join(f"{v} | {r['group']} | 새로움 {r['novelty']} 완성도 {r['quality']} | 비슷한 기존: {r.get('closest')} | {r['one_line']}" for v, r in cands)
    sysmsg = "당신은 스타일 라이브러리를 큐레이션하는 모션 디자이너예요. 서로 겹치지 않고, 기존 라이브러리에 없는 결을 골라요."
    text, _ = call(st, key, OPUS, sysmsg, [{"type": "text", "text": f"""기존 라이브러리:
{catalog()}

후보 (영상번호 | 묶음 | 점수 | 비슷한 기존 | 한 줄):
{lines}

광고 모션 그래픽에 쓸 새 스타일로 최대 {max_n}개를 골라 주세요.
- 후보끼리 결이 겹치면 더 나은 하나만
- 묶음이 한쪽에 몰리지 않게 (손그림·레트로·콜라주·시네마틱 같은 결도 챙기기)
- 기존 스타일과 거의 같은 것은 빼기
출력: ```json {{"picked": ["영상번호", ...]}}```"""}], max_tokens=6000, effort="medium", budget=budget)
    new = [str(x) for x in jpart(text, ("picked",))["picked"] if str(x) in st["videos"] and str(x) not in taken][:max_n]
    st["picked"] = st["picked"] + new
    save_state(st)
    log(f"  새로 고른 {len(new)}개 (모두 {len(st['picked'])}개)")


# ------------------------------------------------------------------ 3·4. 쓰기와 점검
def write_sys():
    docs = (ROOT / "docs" / "STYLES.md").read_text(encoding="utf-8-sig")
    ex = []
    for sid in ("marker-scrawl-montage", "glitch-block-grotesk", "ember-orb-dark"):
        d = SDIR / sid
        if d.exists():
            ex.append(f"### 예시 {sid}/style.json\n{(d / 'style.json').read_text(encoding='utf-8-sig')}\n### 예시 {sid}/style.md\n{(d / 'style.md').read_text(encoding='utf-8-sig')}")
    return f"""당신은 모션 스튜디오의 스타일 라이브러리에 새 스타일을 더하는 모션 디자이너예요.
영상 프레임을 보고 그 '보는 결·움직이는 결'의 원리(색 비율, 글자 성격, 질감, 움직임 속도·이징, 전환, 대표 움직임)를 배워
style.json 과 style.md 를 써요. 원본의 로고·캐릭터·고유 그림·문구는 따라 하지 않고, 회사·제품 이름은 id·name·글 어디에도 쓰지 않아요.
글은 사람이 말하듯 자연스러운 한국어로, "~가 아닙니다, ~입니다" 같은 대조 구문 없이 써요.

규칙 (docs/STYLES.md 전체):
{docs}

쓸 수 있는 글꼴 (fonts 에는 이 줄을 그대로 복사, type 에는 family 이름. 영문 글꼴 뒤에 한글 글꼴을 같이):
{font_entries()}

template 은 결 템플릿 10개 중 하나: {', '.join(TEMPLATES)} (각자 화면 구성이 달라요: typeslam 큰 글자 쇼, uidemo 앱 화면 시연, sketchbook 손그림 노트,
dataflow 점·선 흐름도, terminal 레트로 터미널·픽셀, collage 종이 콜라주, stage 3D 사물 무대, glow 빛·그라디언트, brandmark 도형·격자 브랜드, cinema 어두운 시네마틱)
colors 는 9개 키 모두, onBg/bg 대비 4.5 이상, accentInk/accent 대비 4.5 이상. look 은 영상에 실제로 그 질감이 있을 때만.
style.md 는 예시와 같은 목차로, '대표 장면'에는 우리 엔진(S.fx, S.tr, Studio.M)으로 만드는 법을 짧은 코드로.
'배운 곳'에는 keyframe.gallery 와 mux 재생 ID, 몇 초쯤, 무엇을 배웠는지.

{chr(10).join(ex)}"""


EFFORT = {"write": "medium"}


def write_one(st, key, sysmsg, vid, budget):
    r = st["videos"][vid]
    pid = r["pid"]
    dur, tiles = storyboard(pid)
    from PIL import Image
    a = sheet(pick(tiles, 24), cols=6, w=240)
    big = []
    for t in [dur * f for f in (.12, .35, .6, .85)]:
        try:
            big.append((t, Image.open(io.BytesIO(fetch(f"https://image.mux.com/{pid}/thumbnail.jpg?width=640&time={t:.2f}"))).convert("RGB")))
        except Exception:  # noqa: BLE001
            pass
    b = sheet(big, cols=2, w=560) if big else None
    content = [{"type": "text", "text": f"영상 길이 {dur:.1f}초, mux 재생 ID {pid}. 훑기 메모: {r.get('one_line')} (묶음 {r.get('group')}, 비슷한 기존 {r.get('closest')})\n시간 순서 24장:"},
               jpg_block(a, 80)]
    if b:
        content += [{"type": "text", "text": "큰 프레임 4장:"}, jpg_block(b, 82)]
    content.append({"type": "text", "text": f"""이미 있는 id 와 겹치지 않는 새 id(영문 소문자·하이픈, 결을 설명)로 스타일을 써 주세요. 기존 목록:
{catalog()}
출력: ```json {{"style_json": {{...}}, "style_md": "..."}}``` 코드 블록 하나"""})
    text, hist = call(st, key, OPUS, sysmsg, content, max_tokens=32000, effort=EFFORT["write"], budget=budget)
    d = jpart(text, ("style_json", "style_md"))
    return d, hist, [a] + ([b] if b else [])


def save_style(d, folder=None):
    sj = d["style_json"]
    sid = re.sub(r"[^a-z0-9-]", "", str(sj.get("id", "")).lower())[:48] or f"learned-{int(time.time())}"
    base = folder or SDIR
    if (SDIR / sid).exists() and folder is None:
        sid += "-2"
    sj["id"] = sid
    p = base / sid
    p.mkdir(parents=True, exist_ok=True)
    (p / "style.json").write_text(json.dumps(sj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (p / "style.md").write_text(d["style_md"].strip() + "\n", encoding="utf-8")
    return sid


def py(args, timeout=600):
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":
        exe = exe.with_name("python.exe")
    kw = {"creationflags": 0x08000000} if os.name == "nt" else {}
    r = subprocess.run([str(exe)] + args, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"), **kw)
    return r.returncode, (r.stdout + r.stderr)


def check(sid):
    code, out = py(["tools/styles.py", "check", sid])
    errs = [l.strip() for l in out.splitlines() if "오류" in l]
    return code == 0 and not errs, "\n".join(l for l in out.splitlines() if "NOT subset" not in l)[-1500:]


def review(st, key, sid, refs, budget):
    from PIL import Image
    th = SDIR / sid / "thumb.jpg"
    text, _ = call(st, key, OPUS, "당신은 모션 디자인 리뷰어예요. 짧고 정확하게 판단해요.", [
        {"type": "text", "text": "원본 영상 프레임:"}, *[jpg_block(x, 75) for x in refs],
        {"type": "text", "text": f"우리 엔진에 이 스타일({sid})을 입혀 만든 썸네일(같은 예시 문구, 두 장면):"}, jpg_block(Image.open(th).convert("RGB"), 85),
        {"type": "text", "text": f"""style.json:
{(SDIR / sid / 'style.json').read_text(encoding='utf-8')}

중요: 썸네일의 화면 구성과 소품(동전·비눗방울·찢긴 종이·노트·터미널 창·빛 구슬·도형 마크 같은 것)은 style.json 의 template(결 템플릿)이 정해요.
스타일이 바꿀 수 있는 것은 색과 그 비율, 글꼴 성격·굵기·대소문자·자간·크기 배수, 질감(look), 장면 힌트(scenes 의 bg·card·marker·frame·deco·schemes·rough),
큰 글·숫자 등장 방식, 모서리, 움직임 값뿐이에요. 템플릿 고유 소품이 원본에 없다는 이유로 깎지 말고, 스타일이 다룰 수 있는 부분만 보고 매겨 주세요.
다만 다른 결 템플릿({', '.join(TEMPLATES)})이 이 결을 훨씬 잘 담겠다면 fix 에 바꿀 template 을 적어도 돼요.

0~10점: 위 범위에서 원본의 결(색 비율·글자 성격·질감·분위기)을 잘 옮겼는지 + 광고 화면으로 깔끔한지(글 넘침·겹침·대비).
7점 아래면 style.json 에서 무엇을 어떻게 바꿀지 구체적으로(키와 값) 적어 주세요.
출력: ```json {{"score": 8, "why": "한 줄", "fix": "고칠 점 또는 빈 문자열"}}```"""}], max_tokens=4000, effort="medium", budget=budget)
    return jpart(text, ("score",))


def to_review(sid):
    (SDIR / "_review").mkdir(exist_ok=True)
    shutil.rmtree(SDIR / "_review" / sid, ignore_errors=True)
    if (SDIR / sid).exists():
        shutil.move(str(SDIR / sid), str(SDIR / "_review" / sid))


def verify(st, key, sysmsg, vid, sid, refs, budget):
    """썸네일 → 비교 점수 → 7점 아래면 한 번 고치고 다시. 남기거나 _review 로."""
    try:
        if not (SDIR / sid / "thumb.jpg").exists():
            py(["tools/styles.py", "thumbs", sid], timeout=600)
        if not (SDIR / sid / "thumb.jpg").exists():
            raise RuntimeError("썸네일이 안 만들어졌어요")
        rv = review(st, key, sid, refs, budget)
        if rv.get("score", 0) < 7 and rv.get("fix"):
            sj = json.loads((SDIR / sid / "style.json").read_text(encoding="utf-8"))
            text, _ = call(st, key, OPUS, sysmsg, [{"type": "text", "text": f"""이 style.json 을 리뷰대로 고쳐 주세요. id 는 그대로. template 을 바꾸라는 말이 있으면 바꿔도 돼요.
리뷰: {rv.get('why')} / 고칠 점: {rv.get('fix')}
{json.dumps(sj, ensure_ascii=False, indent=1)}
출력: ```json {{"style_json": {{...}}}}```"""}], max_tokens=16000, effort="medium", budget=budget)
            nj = jpart(text, ("style_json",))["style_json"]
            nj["id"] = sid
            (SDIR / sid / "style.json").write_text(json.dumps(nj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            ok, _ = check(sid)
            if ok:
                py(["tools/styles.py", "thumbs", sid], timeout=600)
                rv = review(st, key, sid, refs, budget)
        keep = rv.get("score", 0) >= 7
        if not keep:
            to_review(sid)
        st["done"][vid].update(id=sid, result="kept" if keep else "review", score=rv.get("score"), why=rv.get("why"), v2=True)
        log(f"  점검 {sid}: {rv.get('score')}점 {'남김' if keep else '_review 로'} · {str(rv.get('why'))[:80]} · 누적 {st['usd']:.2f}달러")
    except Budget:
        raise
    except Exception as e:  # noqa: BLE001
        st["done"][vid].update(result="review-error", log=str(e)[:200])
        to_review(sid)
        log(f"  점검 {sid} 실패, _review 로: {e}")
    save_state(st)


def refs_for(pid):
    from PIL import Image
    dur, tiles = storyboard(pid)
    a = sheet(pick(tiles, 24), cols=6, w=240)
    big = []
    for t in [dur * f for f in (.12, .35, .6, .85)]:
        try:
            big.append((t, Image.open(io.BytesIO(fetch(f"https://image.mux.com/{pid}/thumbnail.jpg?width=640&time={t:.2f}"))).convert("RGB")))
        except Exception:  # noqa: BLE001
            pass
    return [a] + ([sheet(big, cols=2, w=560)] if big else [])


def stage_recheck(st, key, budget):
    """이번에 쓴 스타일(남김·검토 폴더·점검 전)을 새 기준으로 다시 점검"""
    sysmsg = write_sys()
    todo = [(v, r["id"]) for v, r in st["done"].items() if r.get("id") and not r.get("v2")
            and r.get("result") in ("written", "review", "review-error", "review-unchecked")]
    try:   # 끊기기 전에 새 기준으로 이미 본 것은 건너뜀 (기록에서 찾음)
        lines = (LEARN / "learn.log").read_text(encoding="utf-8").splitlines()
        k = max(i for i, l in enumerate(lines) if "다시 점검:" in l)
        seen = {m.group(1) for l in lines[k:] for m in [re.search(r"점검 (\S+): \d+점", l)] if m}
        todo = [(v, s) for v, s in todo if s not in seen]
        for v, r in st["done"].items():
            if r.get("id") in seen:
                r["v2"] = True
    except ValueError:
        pass
    log(f"다시 점검: {len(todo)}개")
    for vid, sid in todo:
        if (SDIR / "_review" / sid).exists() and not (SDIR / sid).exists():
            shutil.move(str(SDIR / "_review" / sid), str(SDIR / sid))
        if not (SDIR / sid).exists():
            continue
        try:
            refs = refs_for(st["videos"][vid]["pid"])
        except Exception as e:  # noqa: BLE001
            log(f"  {sid} 원본 프레임을 못 받음: {e}")
            to_review(sid)
            continue
        verify(st, key, sysmsg, vid, sid, refs, budget)


def stage_write(st, key, budget, workers=3):
    sysmsg = write_sys()
    # 쓰기는 남은 예산의 55% 까지, 나머지는 점검 몫 (이어 돌릴 때도 점검할 돈이 남게)
    wbudget = st["usd"] + max(0.0, budget - st["usd"]) * .55
    todo = [v for v in st["picked"] if v not in st["done"]]
    log(f"3·4단계 쓰기와 점검: {len(todo)}개")

    def job(vid):
        refs = None
        try:
            d, hist, refs = write_one(st, key, sysmsg, vid, wbudget)
            with LOCK:
                sid = save_style(d)
            ok, out = check(sid)
            if not ok:
                text, hist = call(st, key, OPUS, sysmsg, [{"type": "text", "text": f"styles.py check 결과에 오류가 있어요. 고친 전체 JSON 을 같은 형식으로 다시 주세요.\n{out}"}],
                                  max_tokens=24000, effort="medium", budget=wbudget, history=hist)
                d = jpart(text, ("style_json", "style_md"))
                d["style_json"]["id"] = sid
                shutil.rmtree(SDIR / sid, ignore_errors=True)
                with LOCK:
                    save_style(d)
                ok, out = check(sid)
                if not ok:
                    return vid, {"id": sid, "result": "check-fail", "log": out[-400:]}
            return vid, {"id": sid, "result": "written", "refs": refs}
        except Budget:
            raise
        except Exception as e:  # noqa: BLE001
            return vid, {"result": "error", "log": str(e)[:300]}

    written = []
    with cf.ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(job, v): v for v in todo}
        for f in cf.as_completed(futs):
            try:
                vid, r = f.result()
            except Budget:
                log("예산에 닿아 쓰기를 멈춰요")
                break
            refs = r.pop("refs", None)
            st["done"][vid] = r
            save_state(st)
            log(f"  쓰기 {vid} → {r.get('id')} {r['result']} · 누적 {st['usd']:.2f}달러")
            if r["result"] == "written":
                written.append((vid, r["id"], refs))

    # 점검: 썸네일(한 번에) → 비교 → 모자라면 한 번 고치고 다시
    if not written:
        return
    ids = [w[1] for w in written]
    log(f"썸네일 {len(ids)}개 만드는 중")
    for k in range(0, len(ids), 10):
        py(["tools/styles.py", "thumbs"] + ids[k:k + 10], timeout=1800)
    for vid, sid, refs in written:
        try:
            verify(st, key, sysmsg, vid, sid, refs, budget)
        except Budget:
            log("예산에 닿아 점검을 멈춰요. 점검 못 한 스타일은 styles/_review 로 옮겨요")
            for v2, s2, _ in written:
                if st["done"].get(v2, {}).get("result") == "written" and (SDIR / s2).exists():
                    (SDIR / "_review").mkdir(exist_ok=True)
                    shutil.move(str(SDIR / s2), str(SDIR / "_review" / s2))
                    st["done"][v2]["result"] = "review-unchecked"
            break
        save_state(st)


# ------------------------------------------------------------------ 실행
def main():
    a = sys.argv[1:]
    LEARN.mkdir(parents=True, exist_ok=True)
    st = load_state()
    if not a or a[0] == "status":
        res = {}
        for r in st["done"].values():
            res[r.get("result")] = res.get(r.get("result"), 0) + 1
        print(json.dumps({"usd": round(st["usd"], 2), "triaged": len(st["videos"]), "picked": len(st["picked"]), "results": res}, ensure_ascii=False))
        return
    opt = lambda n, d=None: a[a.index(n) + 1] if n in a else d  # noqa: E731
    budget, max_n = float(opt("--budget", 90)), int(opt("--max", 80))
    gallery = json.loads(Path(opt("--list", str(LEARN / "gallery.json"))).read_text(encoding="utf-8"))
    import accounts
    name, key = accounts.active("claude")
    if not key:
        sys.exit("Claude API 키가 없어요")
    log(f"시작 · 계정 '{name}' · 예산 {budget}달러 · 지금까지 {st['usd']:.2f}달러")
    TMP.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":   # 도는 동안만 PC 가 절전에 들어가지 않게 (끝나면 저절로 풀림)
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
        except Exception:  # noqa: BLE001
            pass
    try:
        if "--skip-triage" not in a:
            stage_triage(st, key, gallery, min(budget, st["usd"] + max(5.0, budget * .25)))
        if "--recheck" in a:
            stage_recheck(st, key, budget)
        if "--effort" in a:
            EFFORT["write"] = opt("--effort")
        if "--more" in a:
            stage_pick(st, key, budget, max_n, more=True)
        elif not st["picked"] or "--repick" in a:
            stage_pick(st, key, budget, max_n)
        stage_write(st, key, budget)
    except Budget:
        log("예산에 닿아 멈췄어요")
    finally:
        save_state(st)
        shutil.rmtree(TMP, ignore_errors=True)
        log(f"끝 · 누적 {st['usd']:.2f}달러")


if __name__ == "__main__":
    main()
