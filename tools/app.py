"""모션 스튜디오 앱 (화면으로 쓰는 버전).

실행:
    python tools/app.py            # 앱 창이 열림 (Windows는 Edge/Chrome 앱 창, 없으면 기본 브라우저)
    python tools/app.py --no-window  # 서버만 켜고 주소를 출력
    python tools/app.py --port 8800

이 컴퓨터 안(127.0.0.1)에서만 열리고, 창을 닫으면 작업 중이 아닐 때 잠시 뒤 스스로 꺼집니다.
"""
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
import urllib.request
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FORMATS, ROOT, load_json  # noqa: E402

APP_DIR = ROOT / "app"
OUT = ROOT / "out"
APPDATA = OUT / "_app"          # 앱이 쓰는 임시 파일 (올린 파일, 앱 창 설정, 기록)
UPLOADS = APPDATA / "uploads"
LOG_FILE = APPDATA / "app.log"
VERSION = "1.0"


def _build_id():
    """앱 코드(tools, app) 지문. 새 버전을 설치했는데 예전 앱 서버가 아직 떠 있으면 이 값이 달라서 알아챔."""
    import hashlib
    h = hashlib.sha1()
    root = Path(__file__).resolve().parents[1]
    for d in ("tools", "app", "engine"):
        for f in sorted((root / d).glob("*.*")):
            if f.suffix in (".py", ".js", ".css", ".html"):
                try:
                    h.update(f.name.encode() + f.read_bytes())
                except OSError:
                    pass
    return h.hexdigest()[:12]


BUILD = _build_id()
IS_WIN = os.name == "nt"
NO_WINDOW = 0x08000000 if IS_WIN else 0
SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")

mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("image/webp", ".webp")
# 윈도 레지스트리에 잘못 등록된 형식이 있어도 앱 화면이 깨지지 않게 직접 정함
for _t, _e in (("text/css", ".css"), ("text/html", ".html"), ("application/json", ".json"), ("image/svg+xml", ".svg"),
               ("image/png", ".png"), ("image/jpeg", ".jpg"), ("video/mp4", ".mp4"), ("audio/mpeg", ".mp3"), ("audio/wav", ".wav")):
    mimetypes.add_type(_t, _e)


def safe_float(x, default=None):
    try:
        return float(x) if x not in (None, "") else default
    except (TypeError, ValueError):
        raise ApiError("숫자 값이 올바르지 않아요")


def friendly_error(e):
    """파이썬 예외를 사용자가 알아들을 한국어로. 모르는 예외면 원래 글."""
    name, msg = type(e).__name__, str(e)
    low = msg.lower()
    if name == "UnidentifiedImageError" or "cannot identify image file" in low:
        return "이 그림 파일은 열 수 없어요. JPG나 PNG로 바꿔서 넣어 주세요 (아이폰 HEIC, SVG 는 안 돼요)."
    if name in ("JSONDecodeError",) or "expecting property name" in low or "expecting value" in low:
        return (f"설정 파일(JSON)이 깨져 있어요: {msg}. 그 영상이나 계정 폴더의 video.json·brand.json 을 메모장으로 열어 "
                "줄 번호 근처의 쉼표·따옴표·괄호를 확인해 주세요. (영상이 열리면 고급 탭에서도 고칠 수 있어요)")
    if name in ("URLError", "TimeoutError", "ConnectionResetError", "ConnectionRefusedError", "ConnectionAbortedError", "socket.timeout", "timeout") \
            or "urlopen error" in low or "winerror 10060" in low or "winerror 10061" in low or "getaddrinfo" in low or "timed out" in low:
        return "인터넷에 연결하지 못했어요. 인터넷·회사 프록시·방화벽을 확인하고 다시 시도해 주세요."
    if name == "FileNotFoundError" and ("ffmpeg" in low or "ffprobe" in low or "winerror 2" in low):
        return "ffmpeg 를 찾지 못했어요. 설치 프로그램을 다시 실행하거나, 명령 창에서 winget install Gyan.FFmpeg 로 설치한 뒤 앱을 다시 켜 주세요."
    if name == "PermissionError" or "winerror 32" in low or "winerror 5" in low:
        return "파일을 다른 프로그램이 쓰고 있어서 바꾸지 못했어요. 그 파일·폴더를 연 창(탐색기, 동영상 플레이어)을 닫고 다시 시도해 주세요."
    if ("timeout" in low and ("wait_for_function" in low or "__ready" in low)) or "미리보기 화면이 준비되지" in msg:
        return "영상 화면을 준비하지 못했어요(60초 넘게 걸림). 문구에 이상한 값이 없는지 보고, 미리보기가 뜨는지 확인한 뒤 다시 해 주세요."
    if "executable doesn't exist" in low or "playwright install" in low:
        return (f'렌더링용 크로미움이 없어요. 명령 창에서 "{python_exe()}" -m playwright install chromium 을 실행한 뒤 다시 해 주세요.')
    if name == "MemoryError":
        return "메모리가 모자라요. 다른 프로그램을 닫고 다시 시도해 주세요."
    return msg


def log(msg):
    try:
        APPDATA.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + str(msg) + "\n")
    except Exception:
        pass
    if sys.stdout:
        try:
            print(msg, flush=True)
        except Exception:
            pass


class ApiError(Exception):
    def __init__(self, msg, status=400):
        super().__init__(msg)
        self.status = status


def python_exe():
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe" and exe.with_name("python.exe").exists():
        return str(exe.with_name("python.exe"))
    return sys.executable


def child_env():
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def find_claude():
    override = os.environ.get("MOTION_STUDIO_CLAUDE")
    if override:
        return [sys.executable, override] if override.endswith(".py") else [override]
    p = shutil.which("claude")
    if p:
        return [p]
    for cand in (Path.home() / ".local" / "bin" / "claude.exe", Path.home() / ".local" / "bin" / "claude"):
        if cand.exists():
            return [str(cand)]
    return None


def claude_engine():
    """앱의 Claude 기능을 무엇으로 돌릴지: 'api'(AI 계정에서 고른 Claude API 키) 또는 'code'(이 PC의 Claude Code 로그인)."""
    try:
        import accounts
        return accounts.engine()
    except Exception:  # noqa: BLE001
        return "code"


def claude_api_account():
    """(이름, 키) — API 로 쓰도록 골라 두었고 키가 있을 때만"""
    try:
        import accounts
        return accounts.active("claude")
    except Exception:  # noqa: BLE001
        return None, ""


def claude_available():
    """앱 안 Claude 작업(문구·업로드 글·사진 검색어)을 돌릴 수 있는지."""
    if claude_engine() == "api":
        return bool(claude_api_account()[1])
    return bool(find_claude())


def claude_missing_text():
    if claude_engine() == "api":
        return "Claude API 키가 없어요. 오른쪽 위 'AI 계정'에서 키를 넣거나, 연결 방식을 'Claude Code 로그인'으로 바꿔 주세요."
    return "Claude Code를 찾을 수 없습니다. 설치 프로그램을 다시 실행하거나, 오른쪽 위 'AI 계정'에서 Claude API 키로 쓰도록 바꿔 주세요."


def claude_code_env():
    """Claude Code 창·claude 명령에 줄 환경 변수. API 방식이면 고른 키를, 로그인 방식이면 키를 빼서 구독 로그인을 쓰게."""
    env = child_env()
    if claude_engine() == "api":
        key = claude_api_account()[1]
        if key:
            env["ANTHROPIC_API_KEY"] = key
    else:
        env.pop("ANTHROPIC_API_KEY", None)
    return env


# ------------------------------------------------------------------ 작업 대기열
class Job:
    def __init__(self, kind, title):
        self.id = uuid.uuid4().hex[:10]
        self.kind, self.title = kind, title
        self.status = "running"
        self.log = []
        self.progress = 0.0
        self.result = None
        self.error = None
        self.started = time.time()
        self.ended = None
        self.proc = None
        self.cancelled = False

    def add(self, line):
        line = line.rstrip()
        if line:
            self.log.append(line)
            if len(self.log) > 400:
                self.log = self.log[-400:]

    def as_dict(self, full=True):
        d = {"id": self.id, "kind": self.kind, "title": self.title, "status": self.status, "progress": round(self.progress, 3),
             "error": self.error, "started": self.started, "ended": self.ended}
        if full:
            d["log"] = self.log[-80:]
            d["result"] = self.result
        return d


JOBS = {}
JOB_LOCK = threading.Lock()
BUILD_LOCK = threading.Lock()


def running_jobs():
    return [j for j in JOBS.values() if j.status == "running"]


def start_job(kind, title, fn):
    job = Job(kind, title)
    with JOB_LOCK:
        JOBS[job.id] = job
        if len(JOBS) > 60:
            for k in sorted(JOBS, key=lambda k: JOBS[k].started)[:-60]:
                if JOBS[k].status != "running":
                    del JOBS[k]

    def run():
        try:
            job.result = fn(job)
            job.status = "cancelled" if job.cancelled else "done"
            job.progress = 1.0 if job.status == "done" else job.progress
        except SystemExit as e:
            job.status, job.error = ("cancelled", None) if job.cancelled else ("error", str(e.code if e.code is not None else "중단됨"))
        except Exception as e:  # noqa: BLE001
            if job.cancelled:
                job.status, job.error = "cancelled", None
            else:
                job.status, job.error = "error", friendly_error(e)
                log(traceback.format_exc())
        job.ended = time.time()
    threading.Thread(target=run, daemon=True).start()
    return job


PW_FIXED = [False]


def run_cmd(job, args, weight=(0.0, 1.0), cwd=ROOT, stdin_text=None, parse=None, check=True, env=None):
    """하위 명령을 실행하며 출력 줄을 작업 기록에 쌓고, 진행률을 계산.
    렌더용 크로미움이 없다는 오류면(설치 중 내려받기 실패, playwright 업데이트 뒤) 한 번 설치하고 다시 실행."""
    try:
        return _run_cmd_once(job, args, weight, cwd, stdin_text, parse, check, env)
    except RuntimeError as e:
        msg = str(e)
        if PW_FIXED[0] or job.cancelled or not ("Executable doesn't exist" in msg or "playwright install" in msg):
            raise
        PW_FIXED[0] = True
        job.add("렌더링용 크로미움이 없어서 지금 설치해요 (처음 한 번, 1~3분).")
        try:
            _run_cmd_once(job, [python_exe(), "-m", "playwright", "install", "chromium"], (weight[0], weight[0]), cwd, None, False, True, None)
        except RuntimeError:
            raise RuntimeError("렌더링용 크로미움을 설치하지 못했어요. 인터넷을 확인하고, 명령 창에서 "
                               f'"{python_exe()}" -m playwright install chromium 을 실행해 주세요.')
        return _run_cmd_once(job, args, weight, cwd, stdin_text, parse, check, env)


def _run_cmd_once(job, args, weight=(0.0, 1.0), cwd=ROOT, stdin_text=None, parse=None, check=True, env=None):
    a, b = weight
    job.add("$ " + " ".join(str(x) for x in args[1:] if not str(x).startswith("{")))
    proc = subprocess.Popen(args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
                            env=dict(child_env(), **(env or {})), creationflags=NO_WINDOW)
    job.proc = proc
    if stdin_text is not None:
        def feed():
            try:
                proc.stdin.write(stdin_text.encode("utf-8"))
                proc.stdin.close()
            except Exception:
                pass
        threading.Thread(target=feed, daemon=True).start()
    out = []
    for raw in proc.stdout:
        line = raw.decode("utf-8", "replace")
        out.append(line)
        if parse is None:
            job.add(line)
        m = re.search(r"(?:프레임|장면|단계) (\d+)/(\d+)", line)
        if m and int(m.group(2)):
            job.progress = a + (b - a) * int(m.group(1)) / int(m.group(2))
    proc.wait()
    job.proc = None
    if job.cancelled:
        raise RuntimeError("취소했습니다")
    if proc.returncode != 0 and check:
        tail = "".join(out[-6:]).strip()
        code = proc.returncode & 0xFFFFFFFF
        if code in (0xC0000005, 0xC0000409, 0xC000001D, 0xC0000135):
            tail = (tail + "\n" if tail else "") + (f"프로그램이 비정상 종료됐어요 (코드 {code}). "
                                                     "Microsoft Visual C++ 재배포 패키지가 없거나 이 PC와 맞지 않는 모듈일 수 있어요.")
        raise RuntimeError(tail or f"명령이 실패했습니다 (코드 {proc.returncode})")
    job.progress = b
    return "".join(out)


def tool(name):
    return [python_exe(), "-X", "utf8", str(ROOT / "tools" / name)]


# ------------------------------------------------------------------ 데이터 읽기
def brand_dir(slug):
    if not SLUG.fullmatch(slug or ""):
        raise ApiError("브랜드 이름이 올바르지 않습니다")
    d = ROOT / "brands" / slug
    if not (d / "brand.json").exists():
        raise ApiError(f"브랜드를 찾을 수 없습니다: {slug}", 404)
    return d


def video_path(name):
    if not SLUG.fullmatch(name or ""):
        raise ApiError("영상 이름이 올바르지 않습니다")
    d = ROOT / "videos" / name
    if not (d / "video.json").exists():
        raise ApiError(f"영상을 찾을 수 없습니다: {name}", 404)
    return d


def rel_url(path):
    return "/" + Path(path).resolve().relative_to(ROOT).as_posix()


def asset_url(base, p):
    for b in (base, ROOT):
        f = (b / p)
        if f.exists():
            try:
                return rel_url(f) + f"?m={int(f.stat().st_mtime)}"
            except ValueError:
                return None
    return None


def brand_summary(slug):
    d = ROOT / "brands" / slug
    b = load_json(d / "brand.json")
    assets = b.get("assets") or {}
    return {"slug": slug, "name": b.get("name", slug), "description": b.get("description", ""), "colors": b.get("colors", {}),
            "logo": asset_url(d, assets[b["logo"]]) if b.get("logo") in assets else None,
            "mascot": asset_url(d, assets[b["mascot"]]) if b.get("mascot") in assets else None,
            "logoText": b.get("logoText", ""), "fonts": b.get("fonts", []), "type": b.get("type", {})}


def video_status(name, v):
    st = {}
    for f in v.get("formats") or list(FORMATS):
        od = OUT / name / f
        mp4 = od / f"{name}_{f}.mp4"
        st[f] = "mp4" if mp4.exists() else "master" if (od / "master.mp4").exists() else \
            "built" if (od / f"{name}-{f}.html").exists() else "none"
    return st


def style_list():
    """앱의 스타일 고르기용 목록 (styles/<이름>/style.json 요약 + 썸네일 주소)."""
    try:
        from styles import list_styles, summary
        out = []
        for st in list_styles():
            sm = summary(st)
            th = ROOT / "styles" / st["id"] / "thumb.jpg"
            sm["thumb"] = rel_url(th) + f"?m={int(th.stat().st_mtime)}" if th.exists() else None
            out.append(sm)
        return out
    except Exception as e:  # noqa: BLE001  스타일 하나가 깨져도 앱은 뜨게
        log(f"스타일 목록을 읽지 못함: {e}")
        return []


def style_card(sid, limit=7000):
    """영상에 고른 스타일의 카드(style.md)와 지킬 점. 없으면 빈 문자열."""
    if not sid:
        return ""
    try:
        from styles import get_style
        st = get_style(sid)
    except Exception:  # noqa: BLE001
        return ""
    keep = {k: st.get(k) for k in ("name", "group", "summary", "signature", "fits", "avoid") if st.get(k)}
    return json.dumps(keep, ensure_ascii=False, indent=1) + "\n" + (st.get("card") or "").strip()[:limit]


def state():
    brands = []
    for p in sorted((ROOT / "brands").iterdir()):
        if (p / "brand.json").exists() and not p.name.startswith("_"):
            try:
                brands.append(brand_summary(p.name))
            except Exception as e:  # noqa: BLE001  하나가 깨져도 앱 전체가 멈추지 않게
                log(f"brands/{p.name}/brand.json 을 읽지 못함: {e}")
                brands.append({"slug": p.name, "name": f"{p.name} (brand.json 오류)", "description": friendly_error(e),
                               "colors": {}, "logo": None, "mascot": None, "logoText": p.name, "fonts": [], "type": {}, "error": friendly_error(e)})
    videos = []
    for p in sorted((ROOT / "videos").iterdir()):
        if (p / "video.json").exists():
            try:
                v = load_json(p / "video.json")
            except Exception as e:  # noqa: BLE001
                videos.append({"name": p.name, "title": p.name, "brand": None, "error": f"video.json 오류: {e}"})
                continue
            videos.append({"name": p.name, "title": v.get("title", p.name), "brand": v.get("brand"),
                           "template": v.get("template"), "formats": v.get("formats") or list(FORMATS),
                           "status": video_status(p.name, v), "updated": (p / "video.json").stat().st_mtime})
    templates = sorted(p.name for p in (ROOT / "templates").iterdir() if (p / "index.html").exists())
    fonts = sorted(p.name for p in (ROOT / "fonts").glob("*.woff2"))
    # rembg 는 실제로 불러오지 않고 깔려 있는지만 봄 (불러오면 onnxruntime 때문에 느리거나, PC에 따라 앱이 통째로 죽을 수 있음)
    try:
        import importlib.util
        has_rembg = importlib.util.find_spec("rembg") is not None
    except Exception:  # noqa: BLE001
        has_rembg = False
    try:
        from presets import list_presets
        presets = [{k: pr.get(k) for k in ("id", "group", "name", "summary", "look", "template", "formats", "seconds", "photos", "ask", "brief", "check", "music", "style")}
                   for pr in list_presets()]
    except Exception:  # noqa: BLE001
        presets = []
    return {"version": VERSION, "styles": style_list(), "brands": brands, "videos": videos, "templates": templates, "fonts": fonts, "presets": presets,
            "formats": {k: list(v) for k, v in FORMATS.items()}, "claude": claude_available(), "claudeCode": bool(find_claude()),
            "claudeEngine": claude_engine(), "claudeAccount": claude_api_account()[0] if claude_engine() == "api" else None,
            "claudeModel": claude_model(), "claudeModels": CLAUDE_MODELS, "claudeEffort": claude_effort(), "claudeEfforts": CLAUDE_EFFORTS, "rembg": has_rembg,
            "ffmpeg": bool(shutil.which("ffmpeg")), "jobs": [j.as_dict(False) for j in JOBS.values()]}


def video_detail(name):
    d = video_path(name)
    v = load_json(d / "video.json")
    sys.path.insert(0, str(ROOT / "tools"))
    from photo import load_credits
    credits = {c.get("file"): c for c in load_credits(d)}
    va = v.get("assets") or {}
    nested = any(k in FORMATS or k == "common" for k in va)
    flat = dict(va.get("common", {})) if nested else dict(va)
    assets = []
    for k, p in flat.items():
        url = asset_url(d, p)
        c = credits.get(Path(p).name) if p.startswith("photos/") else None
        assets.append({"key": k, "path": p, "url": url, "credit": c})
    bdir = ROOT / "brands" / v.get("brand", "")
    brand_assets = []
    if (bdir / "brand.json").exists():
        b = load_json(bdir / "brand.json")
        for k, p in (b.get("assets") or {}).items():
            brand_assets.append({"key": k, "url": asset_url(bdir, p)})
    music = v.get("music") or {}
    if music.get("file"):
        music = dict(music, url=asset_url(d, music["file"]))
    history = []
    if (d / "music").is_dir():
        for f in sorted((d / "music").iterdir(), key=lambda x: -x.stat().st_mtime)[:12]:
            if f.suffix.lower() in (".mp3", ".wav", ".m4a", ".flac", ".ogg"):
                history.append({"file": "music/" + f.name, "name": f.name, "url": asset_url(d, "music/" + f.name)})
    music = dict(music, history=history) if (music or history) else music
    outputs = {}
    for f in v.get("formats") or list(FORMATS):
        od = OUT / name / f
        o = {}
        for key, fn in (("html", f"{name}-{f}.html"), ("sheet", "sheet.png"), ("sheetSafe", "sheet-safe.png"),
                        ("master", "master.mp4"), ("mp4", f"{name}_{f}.mp4")):
            if (od / fn).exists():
                o[key] = rel_url(od / fn) + f"?m={int((od / fn).stat().st_mtime)}"
        outputs[f] = o
    direction = (d / "direction.md").read_text(encoding="utf-8-sig") if (d / "direction.md").exists() else ""
    preset = None
    if v.get("preset"):
        try:
            from presets import get_preset
            pr = get_preset(v["preset"])
            preset = {k: pr.get(k) for k in ("id", "name", "summary", "look", "photos", "ask", "brief", "check", "music")}
        except Exception:  # noqa: BLE001
            preset = {"id": v["preset"], "name": v["preset"]}
    starter = False
    if not v.get("template"):
        src = v.get("src", "index.html")
        first = src.get("tall") or next(iter(src.values()), "") if isinstance(src, dict) else src
        try:
            starter = "MS-STARTER" in (d / first).read_text(encoding="utf-8-sig")[:400]
        except OSError:
            starter = False
    deck = v.get("template") == "deck"
    if deck:
        for ext in ("pdf", "pptx"):
            fp = OUT / name / "wide" / f"{name}.{ext}"
            if fp.exists():
                outputs.setdefault("wide", {})[ext] = rel_url(fp) + f"?m={int(fp.stat().st_mtime)}"
    source = None
    if (d / "source.md").exists():
        source = {"file": v.get("source") or "source.md", "chars": len((d / "source.md").read_text(encoding="utf-8-sig"))}
    return {"name": name, "video": v, "assets": assets, "brandAssets": brand_assets, "nested": nested, "deck": deck, "source": source,
            "custom": not v.get("template"), "scratch": bool(v.get("scratch")), "starter": starter,
            "music": music, "outputs": outputs, "status": video_status(name, v),
            "direction": direction, "preset": preset}


def validate_video(v):
    if not isinstance(v, dict):
        raise ApiError("영상 설정 형식이 올바르지 않습니다")
    if not (ROOT / "brands" / str(v.get("brand", "")) / "brand.json").exists():
        raise ApiError("브랜드를 찾을 수 없습니다")
    if v.get("template") and not (ROOT / "templates" / v["template"] / "index.html").exists():
        raise ApiError("템플릿을 찾을 수 없습니다")
    fm = v.get("formats") or []
    if not fm or any(f not in FORMATS for f in fm):
        raise ApiError("형식을 하나 이상 골라 주세요")


def merge_missing(src, dst):
    """src 에만 있는 키를 dst 에 채워 넣음 (dst 값 우선)."""
    for k, val in src.items():
        if k not in dst:
            dst[k] = val
        elif isinstance(val, dict) and isinstance(dst[k], dict):
            merge_missing(val, dst[k])
    return dst


def write_json(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for k in range(8):   # 백신·OneDrive 가 잠깐 파일을 잡고 있으면 조금 기다렸다 다시
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if k == 7:
                raise
            time.sleep(.25)


def upload_path(upload_id):
    if not re.fullmatch(r"[0-9a-f]{12}_[\w.\-가-힣 ()]+", upload_id or ""):
        raise ApiError("올린 파일을 찾을 수 없습니다")
    p = UPLOADS / upload_id
    if not p.exists():
        raise ApiError("올린 파일을 찾을 수 없습니다")
    return p


def next_photo_key(vdir):
    v = load_json(vdir / "video.json")
    va = v.get("assets") or {}
    if any(k in FORMATS or k == "common" for k in va):
        keys = set()
        for grp in va.values():
            if isinstance(grp, dict):
                keys |= set(grp)
    else:
        keys = set(va)
    # 문구(content)가 이미 가리키는 키도 피합니다. 예시 문구의 photo1처럼 파일은 아직 없어도
    # 다른 장면이 쓰고 있으면, 같은 키를 주면 두 장면에 같은 사진이 들어갑니다.
    c = v.get("content") or {}
    for group in ("visuals", "beats"):
        for it in c.get(group) or []:
            if isinstance(it, dict) and it.get("image"):
                keys.add(str(it["image"]))
    for k in ("image", "bg", "heroImage"):
        if isinstance(c.get(k), str):
            keys.add(c[k])
    keys |= set(re.findall(r'"(photo\d+)"', json.dumps(c)))   # 다른 템플릿의 빈 사진 칸(photo3 등)
    i = 1
    while f"photo{i}" in keys:
        i += 1
    return f"photo{i}"


# ------------------------------------------------------------------ AI 문구
DECK_TYPES_HELP = """장 종류(type)와 칸:
- cover 표지: kicker(작은 꼬리표), title(제목, \n 으로 두 줄까지), highlight(색 바꿀 단어, 제목 속 어절 그대로), sub(발표자·날짜)
- agenda 목차: title, items(문자열 배열, 10개까지)
- section 구분(강조색이 화면을 채우는 장): title, sub (number 는 비우면 01, 02 로 자동)
- bullets 글머리: kicker, title, items(7개까지. "굵은 머리말 | 설명" 처럼 | 로 나누면 두 줄), sub(출처·기준)
- cards 카드: kicker, title, items(3~6개, "카드 제목 | 설명")
- statement 한 문장: kicker, text(크게 보일 한두 줄), highlight, sub
- number 숫자 하나: kicker, title(위 작은 글), prefix, number(숫자만, 예 "1240" 또는 "3.5"), suffix(단위), text(숫자 뜻), sub(출처·기준)
- stats 숫자 여러 개: title, stats([["1,240곳", "연결된 설비"], ["92%", "정확도"]] 처럼 [값, 설명] 2~4개), sub
- chart 막대 그래프: title, unit, bars([["1분기", 420], ["2분기", 760]] 처럼 [이름, 값] 2~8개, 마지막 막대가 강조), sub
- compare 비교: title, leftLabel, left(줄마다 한 항목, \n 으로 나눔), rightLabel, right
- steps 단계·일정: title, items(2~5개, "단계 이름 | 설명")
- image 사진과 글: image(사진 키), layout("split" 왼쪽 사진 / "full" 꽉 찬 사진), kicker, title, text(짧은 문단) 또는 items, credit(출처)
- quote 인용: text(실제로 한 말만), highlight, by, role
- closing 마무리: title(예 "감사합니다"), sub(연락처·질문 안내)
모든 장에 notes(발표자 메모, 화면에는 안 나옴)를 넣을 수 있음."""


def deck_prompt(name, brief, target=None):
    d = video_path(name)
    v = load_json(d / "video.json")
    b = load_json(ROOT / "brands" / v["brand"] / "brand.json")
    brand_info = {k: b.get(k) for k in ("name", "description", "voice", "about", "notes")}
    src = (d / "source.md").read_text(encoding="utf-8-sig")[:40000] if (d / "source.md").exists() else ""
    detail = video_detail(name)
    photos = [{"key": a["key"], "about": (a.get("credit") or {}).get("title", ""), "credit": (a.get("credit") or {}).get("credit_line", "")} for a in detail["assets"]]
    card = style_card(v.get("style"), 3000)
    ex_text = (ROOT / "templates" / "deck" / "example.json").read_text(encoding="utf-8-sig")
    ex = json.loads(ex_text)
    cur = v.get("content", {})
    cur_text = "" if cur.get("slides") == ex.get("slides") else json.dumps(cur, ensure_ascii=False, indent=1)[:6000]   # 아직 예시 그대로면 넘기지 않음 (예시 숫자를 따라 쓰지 않게)
    length = ""
    if target:
        lo, hi = max(4, round(target * .9)), max(6, round(target * 1.4))
        length = f"- 발표 시간은 약 {target}분. 장 수는 {lo}~{hi}장 정도로 맞춤(장마다 30초~1분).\n"
    return f"""당신은 발표 자료를 잘 만드는 기획자입니다. 아래 브랜드·요청{'·자료' if src else ''}를 보고
모션 그래픽 발표 자료(16:9, 넘길 때마다 한 장씩 움직이며 등장) 의 content JSON 을 써 주세요.

[브랜드]
{json.dumps(brand_info, ensure_ascii=False, indent=1)}

[요청]
{brief.strip()}

{('[자료 (사용자가 넣은 파일에서 뽑은 글. 이 내용을 바탕으로 발표를 다시 짬)]' + chr(10) + src + chr(10)) if src else ''}
[{DECK_TYPES_HELP}]

[예시 구조 (모양만 참고. 예시의 글과 숫자는 쓰지 않음)]
{ex_text}

{('[지금 들어 있는 content (사용자가 손본 것. 요청에 맞게 고쳐 씀)]' + chr(10) + cur_text + chr(10)) if cur_text else ''}
[쓸 수 있는 사진 키]
{json.dumps(photos, ensure_ascii=False)}

{('[스타일 (화면의 결. 글의 호흡을 이 결에 맞춤)]' + chr(10) + card + chr(10)) if card else ''}
지켜 주세요:
- 사람이 실제로 말하듯 자연스러운 한국어. 브랜드 말투(voice)를 따름. "~가 아닙니다, ~입니다" 같은 대조 구문은 쓰지 않음.
- 첫 장은 cover, 마지막 장은 closing. 내용이 길면 agenda 와 section 으로 덩어리를 나눔(section 은 2~5개).
- 한 장에 한 메시지. 화면 글은 짧게: 제목 26자 안쪽, 글머리 한 줄 30자 안쪽. 자세한 말은 그 장의 notes 에 씀.
- 장 종류를 내용에 맞게 섞어 씀: 숫자 하나는 number, 숫자 여러 개는 stats, 기간별 값은 chart, 전과 후는 compare, 순서·일정은 steps, 나열은 bullets 나 cards, 꼭 남길 말은 statement.
- 요청·자료·브랜드 정보에 있는 사실만 씀. 숫자·날짜·이름·인용을 지어내지 않음. 확인이 필요한 값은 notes(맨 바깥)에 적음.
- 사진 장(image)의 image 에는 위 사진 키만 씀. 사진이 없으면 image 장은 빼거나 "photo1" 같은 빈 자리 값을 씀(사용자가 사진 탭에서 채움).
{length}- content 맨 바깥에 title(발표 제목, 바닥글에 보임)을 넣음.
- 파일을 읽거나 고치지 말고 답만 하세요.

출력: 맨 끝에 ```json 코드 블록 하나로 {{"content": {{"title": "...", "slides": [...]}}, "notes": "사용자에게 짧게 남길 말(확인할 사실 등)"}} 를 주세요.
"""


def ai_prompt(name, brief, target=None):
    d = video_path(name)
    v = load_json(d / "video.json")
    b = load_json(ROOT / "brands" / v["brand"] / "brand.json")
    tpl = v.get("template") or ""
    docs = (ROOT / "docs" / "TEMPLATES.md").read_text(encoding="utf-8-sig")
    sec = re.search(rf"## {re.escape(tpl)} .*?(?=\n## |\Z)", docs, re.S) if tpl else None
    sec_text = sec.group(0) if sec else ""
    pj = ROOT / "presets" / tpl / "preset.json"
    if tpl and pj.exists() and json.loads(pj.read_text(encoding="utf-8-sig")).get("group") == "look":
        common = re.search(r"## 결 템플릿 .*?(?=\n## |\Z)", docs, re.S)   # 결 템플릿은 공통 content 설명도 함께
        if common:
            sec_text = common.group(0) + "\n\n" + sec_text
    example_p = ROOT / "templates" / tpl / "example.json"
    example = example_p.read_text(encoding="utf-8-sig") if tpl and example_p.exists() else "{}"
    detail = video_detail(name)
    photos = [{"key": a["key"], "credit": (a.get("credit") or {}).get("credit_line", ""),
               "about": (a.get("credit") or {}).get("title", "")} for a in detail["assets"]]
    limits = {}
    try:
        from check import limits_for
        limits = limits_for(tpl)
    except Exception:
        pass
    brand_info = {k: b.get(k) for k in ("name", "description", "voice", "about", "notes")}
    direction = (d / "direction.md").read_text(encoding="utf-8-sig") if (d / "direction.md").exists() else ""
    if direction:
        direction = "[연출 프롬프트 (이 영상의 상황별 연출. 장면 구성과 글 규칙을 따름)]\n" + direction.strip()[:6000] + "\n"
    card = style_card(v.get("style"), 3500)
    if card:
        direction += ("\n[스타일 (화면의 결. 글의 길이·호흡·말맛을 이 결에 맞춤. 장면 쌓기면 어울리는 장면 종류를 고르고 avoid 는 피함)]\n" + card + "\n")
    keep = ""
    if tpl == "scenes":
        keep = ("- 장면 종류와 순서는 요청에 맞게 직접 고름. 보통 5~9개. 첫 장면은 title 이나 짧은 text(첫 2초에 멈추게 하는 훅).\n"
                "- 내용에 맞는 종류를 섞어 씀: 숫자 하나는 number, 순서·절차는 steps, 전과 후는 compare, 기간별 값은 chart, 항목 나열은 list, 사진은 photo·gallery, 브랜드 강조는 logo.\n"
                "- 모든 장면의 큰 글은 text 칸에 씀(종류마다 칸 이름은 [템플릿 설명] 참고). quote 는 요청에 실제로 한 말과 말한 사람이 있을 때만.\n"
                "- photo·gallery 의 사진에는 위 사진 키를 쓰고, 모자라면 \"photo1\", \"photo2\" 처럼 아직 없는 자리 값을 씀(사용자가 '사진 자동 찾기'로 채움). 사진이 어울리지 않는 영상이면 빼도 됨.\n"
                "- scheme·dur·transition 은 꼭 필요할 때만 넣음(비우면 바탕색과 길이가 알아서 정해짐).\n")
    elif tpl not in ("promo", "kinetic"):
        keep = ("- 지금 content 의 구조(키 이름, 배열 길이, 숫자·설정 값)를 그대로 두고 글자만 바꿈. 사진 키 값(photo1 같은 값이나 위 사진 키)은 그대로 둠.\n"
                "- 영상에 들어갈 수치(가격, 날짜, 숫자 카드)는 요청에 있는 값만. 없으면 지금 값을 두고 notes 에 확인해 달라고 적음.\n")
    timing = ""
    if target:
        if tpl == "promo":
            timing = (f"- 영상 길이는 약 {target}초. 장면별 기본 길이: 첫 장면 3초, 사진 장면 하나 2.6초, 장점 3.2초, 숫자 2.4초, 마지막 3.4초.\n"
                      "  이 길이에 맞게 사진 장면 수와 장점·숫자 장면을 넣을지 정함(길이는 나중에 자동으로 정확히 맞춤).\n"
                      "  사진 키가 모자라면 새 사진 장면의 image 를 빈 문자열로 둠. 사용자가 '사진 자동 찾기'로 채움.\n")
        elif tpl == "kinetic":
            timing = (f"- 영상 길이는 약 {target}초. 장면별 기본 길이: 큰 글자 1.9초, 문장 2.6초, 숫자 2.4초, 목록 3.4초, 마지막 3.4초.\n"
                      "  이 길이에 맞게 장면 수를 정함(길이는 나중에 자동으로 정확히 맞춤).\n")
        elif tpl == "scenes":
            timing = (f"- 영상 길이는 약 {target}초. 장면별 기본 길이: title 2.6초, 짧은 text 1.9초·긴 text 2.6초, photo 2.8초, number 2.4초, "
                      "list·steps 2초+항목마다 0.45초, compare 3.4초, quote 3.6초, chart 2.4초+막대마다 0.2초, gallery 2.2초+사진마다 0.35초, logo 2.2초, 마지막 3.4초.\n"
                      "  이 길이에 맞게 장면 수를 정함(길이는 나중에 자동으로 정확히 맞춤).\n")
    what = f"모션 그래픽 템플릿 '{tpl}' 에 들어갈 content JSON" if tpl else "템플릿 없이 직접 짠 영상(HTML 이 content 의 글을 읽어 씀)의 content JSON"
    return f"""당신은 짧은 SNS 광고 영상(릴스·쇼츠·피드)의 카피라이터입니다. 아래 브랜드와 요청을 보고
{what} 을 새로 써 주세요.

[브랜드]
{json.dumps(brand_info, ensure_ascii=False, indent=1)}

[요청]
{brief.strip()}

[템플릿 설명]
{sec_text}

[예시 구조]
{example}

[지금 들어 있는 content (참고용, 필요하면 바꿔도 됨)]
{json.dumps(v.get('content', {}), ensure_ascii=False, indent=1)}

[쓸 수 있는 사진 키]
{json.dumps(photos, ensure_ascii=False)}

[글자 수 권장 상한 (줄바꿈 제외)]
{json.dumps(limits, ensure_ascii=False)}

{direction}
지켜 주세요:
- 사람이 실제로 말하듯 자연스러운 한국어. 브랜드 말투(voice)를 따름. "~가 아닙니다, ~입니다" 같은 대조 구문은 쓰지 않음.
- 브랜드 notes 규칙은 반드시 지킴.
- 요청과 브랜드 정보에 있는 사실만 씀. 가격·할인·기간·수치·수상·후기·평점을 지어내지 않음. 근거 있는 숫자가 없으면 숫자 장면(proof 또는 number beat)은 빼도 됨.
- "최고·1위·유일·100%·무조건" 같은 표현은 요청에 근거가 있을 때만.
- 한 장면에 한 메시지. 줄바꿈은 \\n 으로 직접 넣고, 한 줄은 짧게.
- 사진 장면의 image 에는 위 사진 키만 씀. 사진이 모자라면 장면 수를 줄임. credit 값은 사진 키 목록에 있는 값을 그대로 씀.
- 파일을 읽거나 고치지 말고 답만 하세요.
{keep}
{timing}
출력: 맨 끝에 ```json 코드 블록 하나로 {{"content": {{...}}, "notes": "사용자에게 짧게 남길 말(확인할 사실 등)"}} 를 주세요.
"""


def extract_json(text, want=None):
    """Claude 답에서 JSON 객체를 찾음. ```json 블록을 먼저 보고, 없으면 본문의 모든 { 위치에서 읽어 보고 가장 큰 객체를 씀.
    want 에 키 이름을 주면 그 키가 있는 객체를 먼저 고름."""
    text = str(text or "")
    cands = []
    for blk in re.findall(r"```(?:json|JSON)?\s*(.*?)```", text, re.S):
        try:
            v = json.loads(blk.strip())
            if isinstance(v, dict):
                cands.append(v)
        except json.JSONDecodeError:
            pass
    if not cands:
        dec = json.JSONDecoder()
        for m in re.finditer(r"\{", text):
            try:
                v, _ = dec.raw_decode(text, m.start())
            except json.JSONDecodeError:
                continue
            if isinstance(v, dict):
                cands.append(v)
    if want:
        hit = [c for c in cands if any(k in c for k in want)]
        if hit:
            cands = hit
    if cands:
        return max(cands, key=lambda c: len(json.dumps(c, ensure_ascii=False)))
    raise RuntimeError("Claude 답에서 JSON을 찾지 못했습니다. 한 번 더 시도해 보세요.")


def claude_json(job, prompt, instruction, want=None, model=None, weight=(.1, .95), images=None):
    """claude_text + extract_json. 답에 JSON이 없으면(질문만 하거나 형식이 깨지면) 한 번 더 부탁함. images: 같이 볼 이미지 파일 경로 목록"""
    text = claude_text(job, prompt, instruction, weight=weight, model=model, images=images)
    try:
        return extract_json(text, want)
    except RuntimeError:
        job.add("답에 JSON이 없어서 한 번 더 부탁하는 중이에요.")
        retry = (prompt + "\n\n[앞선 답]\n" + text.strip()[:4000] +
                 "\n\n앞선 답에 형식에 맞는 JSON 이 없었어요. 질문하지 말고, 정보가 모자란 칸은 지금 값을 그대로 두고 notes 에 확인할 점을 적은 뒤, "
                 "맨 끝에 ```json 코드 블록 하나만 주세요.")
        text2 = claude_text(job, retry, instruction, weight=(weight[1] - .05, weight[1]), model=model, images=images)
        try:
            return extract_json(text2, want)
        except RuntimeError:
            said = re.sub(r"\s+", " ", text2 or text).strip()[:240]
            raise RuntimeError(f"Claude가 JSON 대신 이렇게 답했어요: \"{said}\" 요청을 조금 더 구체적으로 적어 다시 시도해 주세요.")


CLAUDE_MODELS = [["", "기본"], ["opus", "Opus · 꼼꼼"], ["sonnet", "Sonnet · 균형"], ["haiku", "Haiku · 빠름"]]
CLAUDE_EFFORTS = [["", "기본"], ["low", "낮음 · 빠름"], ["medium", "보통"], ["high", "높음"], ["xhigh", "아주 높음"], ["max", "최대 · 느림"]]


def claude_model():
    """앱에서 고른 Claude 모델 (사용자 폴더 .motion-studio/settings.json 의 claude_model). 비어 있으면 작업별 기본값."""
    try:
        import music
        m = music.settings().get("claude_model") or ""
    except Exception:  # noqa: BLE001
        m = ""
    return m if m in {k for k, _ in CLAUDE_MODELS} else ""


def claude_effort():
    """앱에서 고른 노력 정도 (settings.json 의 claude_effort). 비어 있으면 Claude Code 기본값."""
    try:
        import music
        e = music.settings().get("claude_effort") or ""
    except Exception:  # noqa: BLE001
        e = ""
    return e if e in {k for k, _ in CLAUDE_EFFORTS} else ""


def claude_flags(model=None):
    """claude 명령에 붙일 --model / --effort."""
    out = []
    m = claude_model() or model
    if m:
        out += ["--model", m]
    if claude_effort():
        out += ["--effort", claude_effort()]
    return out


def claude_text(job, prompt, instruction, weight=(.1, .95), model=None, images=None):
    """claude -p 로 프롬프트(표준 입력)를 보내고 답 텍스트를 돌려줌. 앱에서 모델을 골라 두었으면 그 모델로.
    AI 계정에서 'Claude API 키로' 를 골라 두었으면 Claude API 를 바로 부름."""
    if claude_engine() == "api":
        return claude_api_text(job, prompt, instruction, weight=weight, model=model, images=images)
    claude = find_claude()
    if not claude:
        raise RuntimeError("Claude Code를 찾을 수 없습니다.")
    args = claude + ["-p", instruction, "--output-format", "json", "--permission-mode", "dontAsk"]
    if images:   # Claude Code 는 이미지 파일을 Read 도구로 열어 봄
        args += ["--allowedTools", "Read"]
        prompt += "\n\n[같이 볼 이미지 파일 — Read 도구로 하나씩 꼭 열어 보고 판단하세요]\n" + "\n".join(str(Path(x).resolve()) for x in images)
    flags = claude_flags(model)
    if flags:
        args += flags
        job.add("Claude 설정: " + " ".join(flags[i + 1] for i in range(0, len(flags), 2)))
    out = run_cmd(job, args, weight=weight, stdin_text=prompt, parse=False, check=False, env=claude_code_env())
    payload = {}
    for line in reversed(out.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                cand = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(cand, dict) and "result" in cand:
                payload = cand
                break
    if not payload:
        raise RuntimeError(claude_error_text(out) or ("Claude Code 응답을 읽지 못했습니다: " + out.strip()[-300:]))
    if payload.get("is_error"):
        raise RuntimeError(claude_error_text(str(payload.get("result") or "")) or str(payload.get("result") or "Claude 실행 오류"))
    return str(payload.get("result") or "")


# Claude API 모델 (2026-10 기준, docs.claude.com 모델 목록). 요금은 100만 토큰당 달러 (입력, 출력)
API_MODELS = {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5"}
API_PRICES = {"claude-opus-5-5": (4, 20), "claude-sonnet-5-5": (2, 10), "claude-haiku-5-5": (.1, .5)}
API_URL = os.environ.get("MOTION_STUDIO_ANTHROPIC_URL") or "https://api.anthropic.com/v1/messages"


def agent_budget():
    try:
        import music
        b = float(music.settings().get("agent_budget") or 3)
    except Exception:  # noqa: BLE001
        b = 3.0
    return max(.5, min(50.0, b))


def agent_job(name=None, text="", sid=None):
    """API 모드에서 Claude Code 창 대신: Claude 가 API 로 파일을 읽고 고치고 빌드·장면 모음 확인까지 하는 작업."""
    import agent
    acct, key = claude_api_account()
    if not key:
        raise ApiError(claude_missing_text())
    nm = video_path(name).name if name else None
    s = agent.load(sid) if sid else None
    text = (text or "").strip() or (claude_first_message(nm) if nm else "")
    if not text:
        raise ApiError("부탁할 말을 적어 주세요")
    if not s:
        s = agent.new_session(nm, text)
    model, eff, budget = claude_model() or "opus", claude_effort(), agent_budget()

    def run(job):
        job.add(f"Claude API · 계정 '{acct}' · {agent.MODELS.get(model, model)}" + (f" · 노력 {eff}" if eff else "") + f" · 한 번 예산 {budget:.1f}달러")
        try:
            reply, stop = agent.run(s, text, key, model=model, effort=eff, budget=budget, log=job.add,
                                    cancelled=lambda: job.cancelled, progress=lambda k: setattr(job, "progress", k))
        except agent.Stop:
            return {"session": s["id"], "reply": "", "usd": round(s["usd"], 3), "stop": "cancelled"}
        except RuntimeError as e:
            m = re.match(r"HTTP (\d+): (.*)", str(e), re.S)
            raise RuntimeError(claude_api_error(int(m.group(1)), m.group(2)) if m else claude_api_error(0, str(e)))
        except OSError as e:
            raise RuntimeError(claude_api_error(0, str(e)))
        return {"session": s["id"], "reply": reply, "usd": round(s["usd"], 3), "stop": stop}
    job = start_job("agent", "Claude에게 부탁하기 (API)", run)
    d = job.as_dict()
    d["session"] = s["id"]
    return d


def agent_session(name=None, sid=None):
    import agent
    nm = video_path(name).name if name else None
    s = agent.load(sid) if sid else agent.latest(nm)
    out = {"session": None, "transcript": [], "usd": 0, "suggest": claude_first_message(nm) if nm else "", "budget": agent_budget(),
           "model": claude_model() or "opus"}
    if s:
        out.update({"session": s["id"], "transcript": agent.transcript(s), "usd": round(s.get("usd", 0), 3), "created": s.get("created")})
    return out


def claude_status_bits():
    return {"claude": claude_available(), "claudeCode": bool(find_claude()), "claudeEngine": claude_engine(),
            "claudeAccount": claude_api_account()[0] if claude_engine() == "api" else None}


def claude_api_text(job, prompt, instruction, weight=(.1, .95), model=None, images=None):
    """Claude API(Messages, 스트리밍)로 답 텍스트를 받음. 키는 AI 계정에서 고른 것."""
    import urllib.error
    import urllib.request
    name, key = claude_api_account()
    if not key:
        raise RuntimeError(claude_missing_text())
    alias = claude_model() or model or "opus"
    mid = API_MODELS.get(alias, alias)
    eff = claude_effort()
    body = {"model": mid, "max_tokens": 64000 if eff in ("xhigh", "max") else 32000, "stream": True,
            "messages": [{"role": "user", "content": _api_content(prompt + "\n\n" + instruction, images)}]}
    if eff:
        body["output_config"] = {"effort": eff}
    job.add(f"Claude API · 계정 '{name}' · {mid}" + (f" · 노력 {eff}" if eff else ""))
    tries = 0
    while True:
        tries += 1
        req = urllib.request.Request(API_URL, data=json.dumps(body).encode("utf-8"), method="POST", headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json", "accept": "text/event-stream"})
        try:
            resp = urllib.request.urlopen(req, timeout=600)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            try:
                err = json.loads(raw).get("error") or {}
            except Exception:  # noqa: BLE001
                err = {"message": raw[:300]}
            msg = str(err.get("message") or "")
            if e.code == 400 and "output_config" in body and ("effort" in msg.lower() or "output_config" in msg):
                job.add(f"이 모델은 노력 '{eff}' 를 받지 않아서 기본으로 다시 보내요.")
                body.pop("output_config")
                continue
            if e.code in (429, 500, 502, 503, 529) and tries < 3:
                job.add(f"Claude 서버가 바빠서 {tries * 10}초 뒤 다시 보내요.")
                time.sleep(tries * 10)
                continue
            raise RuntimeError(claude_api_error(e.code, msg))
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(claude_api_error(0, str(e)))
        break
    text, usage = [], {"in": 0, "out": 0}
    lo, hi = weight
    with resp:
        for raw in resp:
            if job.cancelled:
                raise RuntimeError("취소했어요")
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            try:
                ev = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            kind = ev.get("type")
            if kind == "message_start":
                u = (ev.get("message") or {}).get("usage") or {}
                usage["in"] = int(u.get("input_tokens") or 0)
            elif kind == "content_block_delta" and (ev.get("delta") or {}).get("type") == "text_delta":
                text.append(ev["delta"].get("text") or "")
                n = sum(len(x) for x in text)
                job.progress = lo + (hi - lo) * min(.95, n / 3000)
            elif kind == "message_delta":
                usage["out"] = int(((ev.get("usage") or {}).get("output_tokens")) or usage["out"])
            elif kind == "error":
                err = ev.get("error") or {}
                raise RuntimeError(claude_api_error(0, f"{err.get('type', '')} {err.get('message', '')}"))
    pin, pout = API_PRICES.get(mid, (0, 0))
    usd = (usage["in"] * pin + usage["out"] * pout) / 1e6
    job.add(f"사용량: 입력 {usage['in']:,} · 출력 {usage['out']:,} 토큰" + (f" (약 {usd:.3f}달러)" if usd else ""))
    job.progress = hi
    return "".join(text)


def _api_content(text, images=None):
    if not images:
        return text
    import base64
    blocks = []
    for pth in images:
        blocks.append({"type": "text", "text": f"[이미지: {Path(pth).name}]"})
        blocks.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                   "data": base64.b64encode(Path(pth).read_bytes()).decode("ascii")}})
    blocks.append({"type": "text", "text": text})
    return blocks


def claude_api_error(code, msg):
    m = (msg or "").lower()
    if code == 401 or "invalid x-api-key" in m or "authentication" in m:
        return "Claude API 키가 맞지 않거나 지워졌어요. 'AI 계정'에서 키를 확인하거나 다른 계정으로 바꿔 주세요."
    if "credit balance" in m or "billing" in m:
        return "이 API 계정의 크레딧이 모자라요. console.anthropic.com 에서 결제를 확인하거나 'AI 계정'에서 다른 계정으로 바꿔 주세요."
    if code == 429 or "rate limit" in m:
        return "이 API 계정의 사용 한도에 걸렸어요. 잠시 뒤 다시 하거나 'AI 계정'에서 다른 계정으로 바꿔 주세요."
    if code in (529, 503) or "overloaded" in m:
        return "Claude 서버가 붐벼요. 잠시 뒤 다시 시도해 주세요."
    if code == 404 or ("model" in m and "not" in m):
        return "고른 모델을 이 API 계정에서 쓸 수 없어요. 모델을 바꿔 다시 시도해 주세요."
    if code == 0:
        return "Claude 서버에 연결하지 못했어요. 인터넷 연결을 확인하고 다시 시도해 주세요. (" + (msg or "")[:120] + ")"
    return f"Claude API 오류 (HTTP {code}): {(msg or '')[:200]}"


def claude_error_text(msg):
    """Claude Code 오류를 사용자가 알아들을 말로. 모르는 오류면 빈 문자열."""
    m = (msg or "").lower()
    if "not logged in" in m or "/login" in m or "invalid api key" in m or "oauth token" in m and "expired" in m:
        return ("이 PC의 Claude Code에 로그인이 안 돼 있어요. 오른쪽 위 'Claude Code 열기'를 누르고, 열린 창에서 /login 을 입력해 "
                "Claude 계정(Pro·Max·Team·Enterprise)으로 로그인한 뒤 다시 시도해 주세요.")
    if "usage limit" in m or "rate limit" in m or "limit reached" in m or "credit balance" in m:
        return "Claude 사용 한도에 걸렸어요. 한도가 풀린 뒤 다시 하거나, 모델을 Sonnet·Haiku로 바꿔 보세요."
    if "unknown option" in m and "effort" in m:
        return "이 PC의 Claude Code가 예전 버전이라 '노력' 설정을 몰라요. 노력을 '기본'으로 두거나, 명령 창에서 claude update 를 실행해 주세요."
    if "model" in m and ("not found" in m or "invalid" in m or "not available" in m):
        return "고른 모델을 이 계정에서 쓸 수 없어요. 모델을 '기본'으로 바꿔 다시 시도해 주세요."
    if "enotfound" in m or "network" in m or "econn" in m or "timed out" in m:
        return "Claude 서버에 연결하지 못했어요. 인터넷 연결을 확인하고 다시 시도해 주세요."
    return ""


def ai_copy_job(name, brief, target=None):
    if not claude_available():
        raise ApiError(claude_missing_text())
    is_deck = load_json(video_path(name) / "video.json").get("template") == "deck"
    prompt = deck_prompt(name, brief, target) if is_deck else ai_prompt(name, brief, target)

    def run(job):
        job.add("Claude에게 발표 구성과 문구를 부탁하는 중입니다. 보통 1~3분 걸려요." if is_deck else "Claude에게 문구를 부탁하는 중입니다. 보통 30초~2분 걸려요.")
        job.progress = .1
        data = claude_json(job, prompt, "표준 입력으로 받은 지시에 따라 " + ("발표 자료" if is_deck else "광고 문구") + " JSON을 써 주세요.", want=("content",))
        content = data.get("content") if isinstance(data, dict) and "content" in data else data
        if not isinstance(content, dict):
            raise RuntimeError("Claude가 돌려준 내용 형식이 올바르지 않습니다.")
        job.add("문구 초안이 왔습니다. 확인하고 적용해 주세요.")
        return {"content": content, "notes": (data.get("notes") if isinstance(data, dict) else "") or "", "target": target}
    return start_job("ai", "Claude 문구 쓰기", run)


# ------------------------------------------------------------------ 올리기 (업로드)
def publish_info(name):
    vd = video_path(name)
    import upload as up
    v = load_json(vd / "video.json")
    b = load_json(ROOT / "brands" / v["brand"] / "brand.json")
    texts, meta = up.final_texts(name)
    kit = ROOT / "out" / name / "upload" / "upload.html"
    try:
        yt = up.yt_status(v["brand"])
    except Exception as e:  # noqa: BLE001
        yt = {"client": False, "connected": False, "error": str(e)}
    return {"texts": texts, "meta": {k: meta[k] for k in ("title", "description", "caption", "hashtags", "coverAt", "privacy", "paid")},
            "social": b.get("social") or {}, "platforms": [{k: p[k] for k in ("id", "name", "site", "fmt", "page", "tips")} for p in up.platforms_for(v)],
            "youtube": yt, "done": (v.get("upload") or {}).get("done") or {},
            "kit": rel_url(kit) + f"?m={int(kit.stat().st_mtime)}" if kit.exists() else None,
            "kitPath": f"out/{name}/upload" if kit.exists() else None, "limits": up.LIMITS}


def publish_save(name, upd, social=None):
    vd = video_path(name)
    v = load_json(vd / "video.json")
    cur = v.get("upload") or {}
    for k in ("title", "description", "caption", "coverAt", "privacy", "paid"):
        if k in upd:
            cur[k] = upd[k]
    if "hashtags" in upd:
        import upload as up
        cur["hashtags"] = up.norm_tags(upd["hashtags"] if isinstance(upd["hashtags"], list) else re.split(r"[\s,]+", str(upd["hashtags"])))
    if cur.get("privacy") not in (None, "private", "unlisted", "public"):
        raise ApiError("공개 범위가 올바르지 않습니다")
    v["upload"] = cur
    write_json(vd / "video.json", v)
    if social is not None:
        bp = ROOT / "brands" / v["brand"] / "brand.json"
        b = load_json(bp)
        soc = b.get("social") or {}
        for k in ("instagram", "youtube", "footer"):
            if k in social:
                soc[k] = str(social[k] or "").strip()
        if "hashtags" in social:
            import upload as up
            soc["hashtags"] = up.norm_tags(social["hashtags"] if isinstance(social["hashtags"], list) else re.split(r"[\s,]+", str(social["hashtags"])))
        b["social"] = {k: x for k, x in soc.items() if x}
        write_json(bp, b)
    return publish_info(name)


def publish_kit_job(name):
    video_path(name)

    def run(job):
        import upload as up
        job.add("플랫폼별 커버를 찍고 문구를 정리하는 중이에요.")
        r = up.make_kit(name, log=job.add)
        return {"page": rel_url(r["page"]), "dir": f"out/{name}/upload", "items": r["items"]}
    return start_job("publish", "업로드 안내 만들기", run)


def publish_ai_job(name, brief=""):
    if not claude_available():
        raise ApiError(claude_missing_text())
    vd = video_path(name)
    v = load_json(vd / "video.json")
    b = load_json(ROOT / "brands" / v["brand"] / "brand.json")
    import upload as up
    plats = [p["name"] for p in up.platforms_for(v)]
    brand_info = {k: b.get(k) for k in ("name", "description", "voice", "about", "notes", "social")}
    direction = (vd / "direction.md").read_text(encoding="utf-8-sig")[:3000] if (vd / "direction.md").exists() else ""
    prompt = f"""당신은 소상공인·브랜드의 SNS 운영자입니다. 아래 광고 영상을 {', '.join(plats)} 에 올릴 때 쓸 글을 써 주세요.

[브랜드]
{json.dumps(brand_info, ensure_ascii=False, indent=1)}

[영상 제목(내부용)]
{v.get('title', '')}

[영상에 나오는 문구 (content)]
{json.dumps(v.get('content', {}), ensure_ascii=False)[:6000]}

[추가 요청]
{brief.strip() or '(없음)'}

{('[연출 메모]' + chr(10) + direction) if direction else ''}

지켜 주세요:
- 사람이 실제로 말하듯 자연스러운 한국어. 브랜드 말투(voice)를 따름. "~가 아닙니다, ~입니다" 같은 대조 구문은 쓰지 않음.
- 브랜드 notes 규칙은 반드시 지킴. 영상과 브랜드 정보에 있는 사실만 씀. 가격·기간·수치·후기·평점을 지어내지 않음.
- "최고·1위·유일·100%·무조건" 같은 표현은 근거가 있을 때만.
- title: 유튜브 제목. 40자 안쪽, 검색될 핵심어를 앞에. 이모지는 0~1개. < > 는 쓰지 않음.
- description: 유튜브 설명 본문 2~5줄. 첫 줄에 핵심. 사진 출처·해시태그는 넣지 않음(자동으로 붙음).
- caption: 인스타 캡션 본문 2~5줄. 첫 줄이 '더 보기' 전에 보이니 거기서 관심을 끌 것. 해시태그는 넣지 않음.
- hashtags: 5개. 브랜드·지역·상황에 맞는 것만, 너무 넓은 태그(#일상 #좋아요)는 빼고. '#' 를 붙여서.
- 파일을 읽거나 고치지 말고 답만 하세요.

출력: 맨 끝에 ```json 코드 블록 하나로 {{"title": "...", "description": "...", "caption": "...", "hashtags": ["#..."], "notes": "확인할 점(짧게)"}}"""

    def run(job):
        job.add("Claude에게 업로드 글을 부탁하는 중이에요. 보통 30초~1분 걸려요.")
        job.progress = .1
        data = claude_json(job, prompt, "표준 입력으로 받은 지시에 따라 업로드 글 JSON을 써 주세요.", want=("title", "caption"), model="sonnet")
        out = {k: data.get(k) for k in ("title", "description", "caption", "hashtags", "notes") if data.get(k)}
        if not out.get("title") and not out.get("caption"):
            raise RuntimeError("Claude가 돌려준 내용 형식이 올바르지 않습니다.")
        return out
    return start_job("ai", "Claude 업로드 글 쓰기", run)


def youtube_connect_job(brand):
    brand_dir(brand)

    def run(job):
        import upload as up
        job.progress = .1
        return up.yt_connect(brand, log=job.add)
    return start_job("publish", "유튜브 채널 연결", run)


def youtube_upload_job(name, fmt, privacy):
    video_path(name)

    def run(job):
        import upload as up

        def prog(k):
            job.progress = .02 + .96 * k
        return up.yt_upload(name, fmt, privacy, log=job.add, progress=prog)
    return start_job("publish", "유튜브에 올리기", run)


# ------------------------------------------------------------------ 사진 자동 찾기
def scene_text(v):
    return f"{(v.get('title') or '').replace(chr(10), ' ')} {v.get('sub') or ''}".strip()


PHOTO_FIELDS = {"photo", "photos", "tiles", "works", "art", "next", "banner", "avatar", "wide", "image", "images", "stops", "videos", "items"}
# 사진 검색어 힌트로 쓰지 않을 설정 칸 (장면 종류·배치 같은 값)
NEAR_SKIP = {"type", "layout", "scheme", "transition", "pan", "size", "icon", "symbol", "viz", "credit"}


def photo_slots(v, asset_keys=()):
    """사진을 넣을 칸 목록. 사진형은 사진 장면, 그 밖의 템플릿은 photo1 같은 빈 칸(같은 키는 한 칸).
    [{"i", "key", "paths": ["visuals.0.image", ...], "title", "sub"}]"""
    c = v.get("content") or {}
    if v.get("template") == "promo":
        return [{"i": i, "key": x.get("image") or "", "paths": [f"visuals.{i}.image"], "title": x.get("title") or "", "sub": x.get("sub") or ""}
                for i, x in enumerate(c.get("visuals") or [])]
    keys = set(asset_keys)
    found = {}

    def near(parent, me):
        if isinstance(parent, list):
            return [x for x in parent if isinstance(x, str) and x is not me and not re.fullmatch(r"photo\d+", x) and x not in keys]
        if isinstance(parent, dict):
            return [x for k, x in parent.items() if isinstance(x, str) and x is not me and k not in PHOTO_FIELDS and k not in NEAR_SKIP and len(x) < 60 and not re.fullmatch(r"photo\d+", x)]
        return []

    def walk(o, path, pkey, parent, gp=None):
        if isinstance(o, dict):
            for k, x in o.items():
                walk(x, path + [k], k, o, parent)
        elif isinstance(o, list):
            for i, x in enumerate(o):
                walk(x, path + [str(i)], pkey, o, parent)
        elif isinstance(o, str) and (re.fullmatch(r"photo\d+", o) or (o in keys and pkey in PHOTO_FIELDS)):
            sl = found.setdefault(o, {"key": o, "paths": [], "near": []})
            sl["paths"].append(".".join(path))
            nb = near(parent, o)
            if not nb and isinstance(parent, list) and isinstance(gp, dict):   # 사진 목록(images 등)이면 그 장면의 글로
                nb = near(gp, o)
            sl["near"] += nb
    walk(c, [], "", None)
    top = " ".join(str(c.get(k)).replace("\n", " ") for k in ("name", "title", "headline", "label", "desc", "photoCaption") if isinstance(c.get(k), str))
    out = []
    for i, sl in enumerate(found.values()):
        words = [w.replace("\n", " ") for w in dict.fromkeys(sl["near"])][:3]
        out.append({"i": i, "key": sl["key"], "paths": sl["paths"], "title": " · ".join(words) or top, "sub": top if words else ""})
    return out


def photo_query_prompt(video, brand, scenes):
    c = video.get("content") or {}
    lines = [f"- 장면 {i + 1} (i={i}): 제목 \"{(s.get('title') or '').replace(chr(10), ' ')}\", 설명 \"{s.get('sub') or ''}\""
             for i, s in scenes]
    info = {k: brand.get(k) for k in ("name", "description", "about")}
    return f"""광고 영상의 사진 장면마다 위키미디어 공용(Wikimedia Commons)에서 사진을 찾을 영어 검색어를 정해 주세요.

[브랜드]
{json.dumps(info, ensure_ascii=False)}

[광고 요청 메모]
{video.get('brief') or '(없음)'}

[첫 장면 문장]
{((c.get('hook') or {}).get('headline') or '').replace(chr(10), ' ')}

[사진 장면]
{chr(10).join(lines)}

규칙:
- 장면마다 영어 검색어 2개. 사진에 실제로 찍혀 있을 만한 구체적인 사물·음식·장소·동작으로 (예: "latte art", "roasted coffee beans", "pilates reformer").
- 2~4단어로 짧게, 명사 위주로.
- 장면에 실제 가게·장소 이름이 있으면 첫 검색어는 그 이름을 영어로(예: "Jay Fai Bangkok"), 두 번째는 일반 검색어.
- 사람 얼굴이 크게 나올 만한 검색어는 피함.
- 파일을 읽거나 고치지 말고 답만 하세요.
출력: ```json 코드 블록 하나로 {{"scenes": [{{"i": 0, "queries": ["...", "..."]}}]}}
"""


def photo_context(video, brand):
    """사진이 어울리는지 판단할 때 쓰는 '지금 상황' 요약"""
    c = video.get("content") or {}
    bits = {"브랜드": {k: brand.get(k) for k in ("name", "description", "about") if brand.get(k)},
            "광고 요청 메모": video.get("brief") or "", "영상 제목": video.get("title") or "", "상황 프리셋": video.get("preset") or "",
            "첫 문장": ((c.get("hook") or {}).get("headline") or c.get("title") or "").replace("\n", " "),
            "꼬리표": c.get("kicker") or ""}
    try:
        sid = video.get("style")
        if sid and (ROOT / "styles" / sid / "style.json").exists():
            sj = load_json(ROOT / "styles" / sid / "style.json")
            bits["스타일"] = f"{sj.get('name')} — {sj.get('summary')}"
    except Exception:  # noqa: BLE001
        pass
    return json.dumps({k: v for k, v in bits.items() if v}, ensure_ascii=False, indent=1)


def photo_review_sheets(job, scenes, folder):
    """장면마다 후보 썸네일에 번호를 붙여 한 장으로 (Claude 가 한눈에 비교)"""
    import io
    from PIL import Image, ImageDraw, ImageFont
    from photo import UA
    folder.mkdir(parents=True, exist_ok=True)
    font = None
    for f in ("arialbd.ttf", "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            font = ImageFont.truetype(f, 34)
            break
        except Exception:  # noqa: BLE001
            continue
    if font is None:
        try:
            font = ImageFont.load_default(size=34)
        except TypeError:
            font = ImageFont.load_default()
    out = {}
    for sc in scenes:
        cands = sc["candidates"]
        if not cands:
            continue
        tiles = []
        for c in cands:
            im = None
            try:
                req = urllib.request.Request(c["thumb"], headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=25) as r:
                    im = Image.open(io.BytesIO(r.read())).convert("RGB")
            except Exception:  # noqa: BLE001
                pass
            tiles.append(im)
            time.sleep(.15)
        cols, size = 4, 300
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * size, rows * size), (40, 40, 40))
        d = ImageDraw.Draw(sheet)
        for n, im in enumerate(tiles):
            x, y = (n % cols) * size, (n // cols) * size
            if im:
                im.thumbnail((size - 8, size - 8))
                sheet.paste(im, (x + (size - im.width) // 2, y + (size - im.height) // 2))
            else:
                d.text((x + 20, y + size // 2), "?", fill=(200, 200, 200), font=font)
            d.rectangle((x + 6, y + 6, x + 56, y + 50), fill=(0, 0, 0))
            d.text((x + 14, y + 6), str(n + 1), fill=(255, 220, 0), font=font)
        p = folder / f"scene-{sc['i'] + 1}.jpg"
        sheet.save(p, quality=82)
        out[sc["i"]] = p
    return out


def photo_review_prompt(video, brand, scenes):
    parts = []
    for sc in scenes:
        if not sc["candidates"]:
            continue
        lines = "\n".join(f"  {n + 1}. {c['title'].replace('File:', '')} (검색어 \"{c.get('query', '')}\", {c['width']}×{c['height']})"
                          for n, c in enumerate(sc["candidates"]))
        parts.append(f"- 사진 칸 i={sc['i']} (이미지 scene-{sc['i'] + 1}.jpg): 칸 옆 문구 \"{(sc.get('label') or '').replace(chr(10), ' ')}\"\n{lines}")
    return f"""광고 영상에 넣을 사진 후보를 검토해 주세요. 사진 칸마다 후보 썸네일을 번호를 붙여 한 장으로 모아 두었어요.
검색어에 걸렸다고 다 맞는 사진은 아니에요. 아래 '지금 상황'에 정말 어울리는지 사진을 직접 보고 판단해 주세요.

[지금 상황]
{photo_context(video, brand)}

[사진 칸과 후보]
{chr(10).join(parts)}

판단 기준:
- 이 광고의 주제·업종·상품과 맞는지 (예: 카페 원두 광고에 커피 농장 풍경은 애매, 실험실 비커는 안 맞음)
- 나라·지역·계절·시대 분위기가 맞는지 (예: 한국 동네 가게 광고에 외국 거리 간판이 크게 보이면 안 맞음, 오래된 흑백 기록 사진은 대개 안 맞음)
- 칸 옆 문구가 말하는 바로 그것이 보이는지
- 광고로 쓰기 어려운 것: 다른 회사 로고·상표·간판 글씨가 크게 보임, 워터마크·글자가 많음, 사람 얼굴이 알아볼 만큼 크게 나옴, 지도·도표·스캔 문서, 흐리거나 어두움
- 브랜드 말투·스타일과 결이 맞는지 (밝고 깔끔한지, 따뜻한지 등)
점수는 0~10, 6 이상이면 써도 됨(ok). why 는 한국어 20자 안쪽.
한 칸에 ok 인 후보가 하나도 없으면 better_queries 에 더 잘 맞을 영어 검색어 2개를 적어 주세요(위키미디어 공용에서 찾음, 2~4단어).
파일을 고치지 말고 답만 하세요.
출력: ```json 코드 블록 하나로 {{"scenes": [{{"i": 0, "verdicts": [{{"n": 1, "score": 8, "ok": true, "why": "따뜻한 라떼 클로즈업"}}], "better_queries": []}}]}}
"""


def photo_review(job, video, brand, scenes, folder, weight):
    """후보를 Claude 가 직접 보고 점수 매김 → 점수 순으로 정렬하고 review 를 붙임. 다시 찾을 검색어를 돌려줌."""
    sheets = photo_review_sheets(job, scenes, folder)
    if not sheets:
        return {}
    data = claude_json(job, photo_review_prompt(video, brand, scenes), "같이 받은 사진 후보 이미지를 보고 지시에 따라 검토 JSON을 써 주세요.",
                       want=("scenes",), weight=weight, model="sonnet", images=[sheets[i] for i in sorted(sheets)])
    retry = {}
    by_i = {int(x.get("i", -1)): x for x in (data.get("scenes") or []) if isinstance(x, dict)}
    for sc in scenes:
        r = by_i.get(sc["i"])
        if not r:
            continue
        verdict = {int(v.get("n", 0)): v for v in (r.get("verdicts") or []) if isinstance(v, dict)}
        for n, c in enumerate(sc["candidates"]):
            v = verdict.get(n + 1)
            if v:
                sc_ = max(0, min(10, int(safe_float(v.get("score"), 0))))
                c["review"] = {"score": sc_, "ok": bool(v.get("ok")) and sc_ >= 6, "why": str(v.get("why") or "")[:40]}
        sc["candidates"].sort(key=lambda c: -(c.get("review") or {}).get("score", 5))
        sc["reviewed"] = True
        if not any((c.get("review") or {}).get("ok") for c in sc["candidates"]):
            qs = [str(x) for x in (r.get("better_queries") or []) if str(x).strip()][:3]
            if qs:
                retry[sc["i"]] = qs
    return retry


def autophoto_job(name, scenes=None, queries=None):
    vdir = video_path(name)
    v = load_json(vdir / "video.json")
    va = v.get("assets") or {}
    akeys = set(va) if not any(k in FORMATS or k == "common" for k in va) else {k for g in va.values() if isinstance(g, dict) for k in g}
    vis = photo_slots(v, akeys)
    if not vis:
        raise ApiError("이 영상에는 사진을 넣을 칸이 없어요" if v.get("template") != "promo" else "사진 장면이 없어요. 문구 탭에서 사진 장면을 먼저 추가해 주세요")
    if scenes is None and v.get("template") != "promo":
        miss = [s["i"] for s in vis if s["key"] not in akeys]
        scenes = miss or [s["i"] for s in vis]
    idx = [i for i in (scenes if scenes is not None else range(len(vis))) if 0 <= int(i) < len(vis)]
    idx = [int(i) for i in idx]
    given = {int(k): ([q] if isinstance(q, str) else list(q)) for k, q in (queries or {}).items()}
    b = load_json(ROOT / "brands" / v["brand"] / "brand.json")

    def run(job):
        from photo import find_candidates, load_credits
        q = {i: given[i] for i in idx if i in given}
        need = [i for i in idx if i not in q]
        notes = ""
        if need and claude_available():
            job.add("Claude가 장면에 맞는 검색어를 고르는 중이에요.")
            job.progress = .05
            try:
                data = claude_json(job, photo_query_prompt(v, b, [(i, vis[i]) for i in need]),
                                   "표준 입력으로 받은 지시에 따라 사진 검색어 JSON을 써 주세요.", want=("scenes",), weight=(.05, .35), model="sonnet")
                for sc in (data.get("scenes") or []):
                    i = int(sc.get("i", -1))
                    qs = [str(x) for x in (sc.get("queries") or []) if str(x).strip()]
                    if i in need and qs:
                        q[i] = qs[:3]
            except Exception as e:  # noqa: BLE001
                job.add(f"검색어를 만들지 못했어요: {e}")
        for i in idx:
            if i not in q:
                q[i] = [scene_text(vis[i]) or b.get("name", "")]
                notes = "Claude 없이 장면 문구로 찾아서 결과가 적을 수 있어요. 검색어를 영어로 바꿔 다시 찾아 보세요."
        used = {c.get("title") for c in load_credits(vdir)}
        res = []
        for n, i in enumerate(idx):
            job.add(f"{i + 1}번 칸 사진 찾는 중: {', '.join(q[i])}")
            cands = find_candidates(q[i], 8, used)
            res.append({"i": i, "queries": q[i], "candidates": cands, "paths": vis[i]["paths"], "label": vis[i]["title"]})
            job.progress = .35 + .3 * (n + 1) / len(idx)
        if claude_available() and any(r["candidates"] for r in res):
            folder = APPDATA / "photo-review" / job.id
            try:
                job.add("Claude가 후보 사진을 하나씩 보며 이 광고에 어울리는지 검토하는 중이에요.")
                retry = photo_review(job, v, b, res, folder, (.65, .85))
                if retry:
                    job.add(f"어울리는 사진이 없던 {len(retry)}칸은 검색어를 바꿔 다시 찾아요.")
                    again = []
                    for r in res:
                        if r["i"] in retry:
                            new = find_candidates(retry[r["i"]], 8, used | {c["title"] for c in r["candidates"]})
                            if new:
                                again.append({"i": r["i"], "queries": retry[r["i"]], "candidates": new, "label": r["label"], "paths": r["paths"]})
                    if again:
                        photo_review(job, v, b, again, folder / "2", (.85, .97))
                        for a in again:
                            r = next(x for x in res if x["i"] == a["i"])
                            if any((c.get("review") or {}).get("ok") for c in a["candidates"]):
                                r.update(queries=a["queries"], candidates=a["candidates"] + [dict(c) for c in r["candidates"]][:4], reviewed=True)
                bad = [r["i"] + 1 for r in res if r.get("reviewed") and not any((c.get("review") or {}).get("ok") for c in r["candidates"])]
                if bad:
                    notes = (notes + " " if notes else "") + f"{', '.join(map(str, bad))}번 칸은 이 광고에 어울리는 사진을 못 찾아서 비워 뒀어요. 검색어를 바꾸거나 직접 찍은 사진을 넣어 주세요."
            except Exception as e:  # noqa: BLE001
                job.add(f"사진 검토를 하지 못했어요: {e}")
                notes = (notes + " " if notes else "") + "Claude 검토 없이 검색 결과 그대로예요."
            finally:
                shutil.rmtree(folder, ignore_errors=True)
        return {"scenes": res, "notes": notes}
    return start_job("autophoto", "사진 자동 찾기", run)


def autophoto_apply_job(name, picks):
    vdir = video_path(name)
    picks = [p for p in picks if p.get("title")]
    if not picks:
        raise ApiError("넣을 사진을 골라 주세요")

    def run(job):
        from photo import get_photo
        placed = []
        for n, p in enumerate(picks):
            key = next_photo_key(vdir)
            job.add(f"{int(p['i']) + 1}번 칸 사진 받는 중")
            r = get_photo(name, p["title"], key)
            placed.append({"i": int(p["i"]), "key": key, "credit_line": r["credit_line"], "license": r["license"]})
            job.progress = (n + 1) / len(picks)
        return {"placed": placed}
    return start_job("photo", f"사진 {len(picks)}장 넣기", run)


# ------------------------------------------------------------------ 음악
def music_setup_job(target=None):
    def run(job):
        args = tool("music.py") + ["setup"] + (["--dir", str(target)] if target else [])
        run_cmd(job, args, weight=(0, 1))
        import music
        return music.status()
    return start_job("music", "무료 음악 엔진 설치", run)


def music_job(name, d):
    video_path(name)
    engine = "ace" if d.get("engine") == "ace" else "gemini"
    args = tool("music.py") + ["gen", name, "--engine", engine]
    if d.get("mood"):
        args += ["--mood", str(d["mood"])[:40]]
    if str(d.get("prompt") or "").strip():
        args += ["--prompt", str(d["prompt"]).strip()[:600]]
    try:
        if d.get("bpm"):
            args += ["--bpm", str(max(50.0, min(200.0, safe_float(d["bpm"], 120))))]
        if d.get("seconds"):
            args += ["--seconds", str(max(3.0, min(600.0, safe_float(d["seconds"], 30))))]
        if d.get("seed") not in (None, ""):
            args += ["--seed", str(int(d["seed"]))]
    except (TypeError, ValueError):
        raise ApiError("BPM이나 시드 값이 숫자가 아니에요")
    if engine == "gemini" and d.get("yes"):
        args.append("--yes")

    def run(job):
        out = run_cmd(job, args, weight=(0, 1))
        res = {}
        for line in out.splitlines():
            if line.startswith("RESULT "):
                try:
                    res = json.loads(line[7:])
                except ValueError:
                    pass
        res["detail"] = video_detail(name)
        return res
    title = "Gemini로 음악 만들기" if engine == "gemini" else "음악 만들기"
    return start_job("music", f"{title} · {name}", run)


# ------------------------------------------------------------------ 렌더 작업
def render_job(name, formats, music=None, reuse=False):
    d = video_path(name)
    v = load_json(d / "video.json")
    formats = [f for f in formats if f in (v.get("formats") or FORMATS)] or (v.get("formats") or list(FORMATS))
    if not shutil.which("ffmpeg"):
        raise ApiError("ffmpeg를 찾을 수 없습니다. 설치 프로그램을 다시 실행해 주세요.")
    m = v.get("music") or {}

    def run(job):
        n = len(formats)
        outs = []
        for i, f in enumerate(formats):
            base = i / n
            job.title = f"MP4 만들기 · {name} · {f} ({i + 1}/{n})"
            master = OUT / name / f / "master.mp4"
            if reuse and master.exists():
                job.add(f"{f}: 만들어 둔 화면(master.mp4)을 그대로 쓰고 음악만 다시 합쳐요")
            else:
                # 렌더하는 동안 미리보기가 같은 HTML 을 다시 써도 섞이지 않게, 빌드 직후 따로 떠 둔 사본으로 렌더
                with BUILD_LOCK:
                    from build import build_video
                    [html] = build_video(name, [f])
                    snap = Path(html).with_name(Path(html).stem + ".render.html")
                    shutil.copyfile(html, snap)
                run_cmd(job, tool("render.py") + [name, f, "video"], weight=(base + .02 / n, base + .9 / n),
                        env={"MS_RENDER_HTML": str(snap)})
            args = tool("finalize.py") + [name, f]
            if m.get("file") and (d / m["file"]).exists():
                args += ["--music", str(d / m["file"]), "--volume", str(m.get("volume", 1.0)),
                         "--fade-in", str(m.get("fadeIn", .5)), "--fade-out", str(m.get("fadeOut", 2.5)),
                         "--start", str(m.get("start", 0))]
            run_cmd(job, args, weight=(base + .9 / n, (i + 1) / n))
            mp4 = OUT / name / f / f"{name}_{f}.mp4"
            outs.append({"format": f, "url": rel_url(mp4) + f"?m={int(mp4.stat().st_mtime)}", "path": str(mp4)})
        return {"files": outs, "folder": str(OUT / name)}
    return start_job("render", f"MP4 만들기 · {name}", run)


def deck_pdf_job(name):
    video_path(name)

    def run(job):
        with BUILD_LOCK:
            from build import build_video
            build_video(name, ["wide"])
        run_cmd(job, tool("deck.py") + ["pdf", name], weight=(.05, .98))
        p = OUT / name / "wide" / f"{name}.pdf"
        return {"url": rel_url(p) + f"?m={int(p.stat().st_mtime)}", "path": str(p), "folder": str(p.parent)}
    return start_job("render", f"PDF 만들기 · {name}", run)


def deck_pptx_job(name):
    video_path(name)

    def run(job):
        job.add("장마다 글·도형·사진을 PowerPoint 개체로 옮기는 중이에요. 글꼴을 파일에 넣느라 1~2분 걸려요.")
        with BUILD_LOCK:
            from build import build_video
            build_video(name, ["wide"])
        run_cmd(job, tool("deck_pptx.py") + [name], weight=(.05, .98))
        p = OUT / name / "wide" / f"{name}.pptx"
        return {"url": rel_url(p) + f"?m={int(p.stat().st_mtime)}", "path": str(p), "folder": str(p.parent)}
    return start_job("render", f"PPT 만들기 · {name}", run)


def sheet_job(name, formats, safe=False):
    d = video_path(name)
    v = load_json(d / "video.json")
    if v.get("template") == "deck":
        def run_deck(job):
            with BUILD_LOCK:
                from build import build_video
                build_video(name, ["wide"])
            run_cmd(job, tool("deck.py") + ["sheet", name], weight=(.05, .98))
            p = OUT / name / "wide" / "slides.png"
            return {"sheets": [{"format": "wide", "url": rel_url(p) + f"?m={int(p.stat().st_mtime)}"}], "deck": True}
        return start_job("sheet", f"장 모음 · {name}", run_deck)
    formats = [f for f in formats if f in (v.get("formats") or FORMATS)] or (v.get("formats") or list(FORMATS))

    def run(job):
        res = []
        for i, f in enumerate(formats):
            with BUILD_LOCK:
                from build import build_video
                build_video(name, [f])
            run_cmd(job, tool("render.py") + [name, f, "sheet"] + (["--safe"] if safe else []),
                    weight=(i / len(formats), (i + 1) / len(formats)))
            p = OUT / name / f / ("sheet-safe.png" if safe else "sheet.png")
            res.append({"format": f, "url": rel_url(p) + f"?m={int(p.stat().st_mtime)}"})
        return {"sheets": res}
    return start_job("sheet", f"장면 모음 · {name}", run)


def photo_get_job(name, title, key):
    video_path(name)

    def run(job):
        from photo import get_photo
        job.add(f"받는 중: {title}")
        job.progress = .2
        r = get_photo(name, title, key)
        job.add(f"저장했습니다: {r['file']} · {r['license']}")
        return r
    return start_job("photo", "무료 사진 받기", run)


def cutout_job(src_path, dst_path):
    def run(job):
        note = ""
        try:
            run_cmd(job, tool("cutout.py") + [str(src_path), str(dst_path)], weight=(.05, .9))
        except RuntimeError as e:
            if job.cancelled:
                raise
            # AI 배경 지우기(rembg·onnxruntime)가 이 PC에서 죽거나 실패하면 단순 방식으로 다시
            crashed = "3221225477" in str(e) or "-1073741819" in str(e) or "코드 32212" in str(e)
            job.add("AI 배경 지우기가 " + ("이 PC에서 멈춰서" if crashed else "실패해서") + " 단순 방식(배경색 지우기)으로 다시 해요.")
            run_cmd(job, tool("cutout.py") + [str(src_path), str(dst_path), "--simple"], weight=(.9, 1))
            note = ("AI 배경 지우기 도구가 이 PC에서 실행되지 않아 단순 방식으로 지웠어요. 단색 배경이 아니면 결과가 거칠 수 있어요. "
                    "Microsoft Visual C++ 재배포 패키지(x64)를 설치하면 AI 방식이 될 수 있어요.") if crashed else \
                   "AI 배경 지우기가 실패해서 단순 방식으로 지웠어요."
        return {"url": rel_url(dst_path) + f"?m={int(time.time())}", "note": note}
    return start_job("cutout", "배경 지우기", run)


# ------------------------------------------------------------------ HTTP
LAST_PING = [0.0]
BYE_AT = [0.0]   # 창이 닫힌다고 알려 온 시각 (pagehide)
SERVER = [None]
STATIC_ROOTS = ("app", "out", "brands", "videos", "fonts", "styles")


class Handler(BaseHTTPRequestHandler):
    server_version = "MotionStudio/" + VERSION

    def log_message(self, fmt, *args):  # 조용히
        pass

    # --- 응답 도우미
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def host_ok(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def body(self, limit=50 * 1024 * 1024):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError("요청 형식이 올바르지 않습니다")
        if n > limit:
            raise ApiError("파일이 너무 큽니다 (50MB까지)")
        return self.rfile.read(n) if n else b""

    def jbody(self):
        raw = self.body(5 * 1024 * 1024)
        try:
            d = json.loads(raw.decode("utf-8")) if raw else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ApiError("요청 형식이 올바르지 않습니다")
        if not isinstance(d, dict):
            raise ApiError("요청 형식이 올바르지 않습니다")
        return d

    # --- GET
    def do_GET(self):
        if not self.host_ok():
            return self.send_error(403)
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            if u.path.startswith("/api/"):
                return self.send_json(self.api_get(u.path, q))
            return self.static(u.path)
        except ApiError as e:
            return self.send_json({"error": str(e)}, e.status)
        except SystemExit as e:
            return self.send_json({"error": str(e.code)}, 400)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return None   # 브라우저가 요청을 취소함 (탭 이동 등) — 기록할 필요 없음
        except Exception as e:  # noqa: BLE001
            fe = friendly_error(e)
            user_err = type(e).__name__ in ("UnidentifiedImageError", "JSONDecodeError", "PermissionError")
            if not user_err:
                log(traceback.format_exc())
            try:
                return self.send_json({"error": fe if fe != str(e) else f"처리 중 오류: {e}"}, 400 if user_err else 500)
            except OSError:
                return None

    def static(self, path):
        path = urllib.parse.unquote(path)
        if path in ("/", ""):
            path = "/app/index.html"
        parts = [p for p in path.split("/") if p]
        if not parts or parts[0] not in STATIC_ROOTS:
            return self.send_error(404)
        f = (ROOT / Path(*parts)).resolve()
        base = (ROOT / parts[0]).resolve()
        if base not in f.parents and f != base or not f.is_file():
            return self.send_error(404)
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        size = f.stat().st_size
        rng = self.headers.get("Range")
        if rng and ctype.startswith(("video/", "audio/")):
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m and not m.group(1) and m.group(2):   # bytes=-500 → 마지막 500바이트
                start = max(0, size - int(m.group(2)))
                m = None
            else:
                start = int(m.group(1)) if m and m.group(1) else 0
            # 끝을 안 정한 요청은 4MB 씩만 보냄: 재생기 여러 개가 연결을 오래 쥐고 있으면 다른 요청(작업 확인 등)이 밀림
            end = int(m.group(2)) if m and m.group(2) else min(size - 1, start + (4 << 20) - 1)
            end = min(end, size - 1)
            if start >= size or end < start:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Content-Type", ctype)
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            with open(f, "rb") as fh:
                fh.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = fh.read(min(1 << 20, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") else ""))
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-cache")
        if ctype.startswith(("video/", "audio/")):
            self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        with open(f, "rb") as fh:
            shutil.copyfileobj(fh, self.wfile)

    def api_get(self, path, q):
        if path == "/api/ping":
            LAST_PING[0] = time.time()
            BYE_AT[0] = 0.0
            return {"ok": True, "app": "motion-studio", "version": VERSION, "build": BUILD}
        if path == "/api/state":
            return state()
        if path == "/api/update/notice":
            import update
            return {"notice": update.take_notice(), "version": update.current()[:7]}
        if path == "/api/brand":
            d = brand_dir(q.get("slug"))
            b = load_json(d / "brand.json")
            return {"brand": b, "summary": brand_summary(d.name)}
        if path == "/api/video":
            return video_detail(q.get("name"))
        if path == "/api/job":
            j = JOBS.get(q.get("id", ""))
            if not j:
                raise ApiError("작업을 찾을 수 없습니다", 404)
            return j.as_dict()
        if path == "/api/jobs":
            return {"jobs": [j.as_dict(False) for j in sorted(JOBS.values(), key=lambda j: -j.started)]}
        if path == "/api/photo/search":
            from photo import search_photos
            qq = (q.get("q") or "").strip()
            if not qq:
                raise ApiError("검색어를 넣어 주세요")
            return {"results": search_photos(qq, int(q.get("limit", 18)))}
        if path == "/api/music/status":
            import music
            return music.status()
        if path == "/api/music/prompt":
            import music
            name = video_path(q.get("name")).name
            sec = q.get("seconds")
            return {"prompt": music.prompt_for(name, q.get("mood") or None, q.get("prompt") or None,
                                               q.get("bpm") or None, safe_float(sec))}
        if path == "/api/style":
            from styles import get_style
            try:
                return get_style(q.get("id", ""))
            except KeyError:
                raise ApiError("스타일을 찾을 수 없어요", 404)
        if path == "/api/publish":
            return publish_info(video_path(q.get("name")).name)
        if path == "/api/check":
            from check import check_video
            errors, notes, _, _ = check_video(video_path(q.get("name")).name)
            return {"errors": errors, "notes": notes}
        raise ApiError("없는 기능입니다", 404)

    # --- POST
    def do_POST(self):
        if self.host_ok() and urllib.parse.urlparse(self.path).path == "/api/bye":
            # 창을 닫을 때 sendBeacon 으로 오는 알림 (머리글을 못 붙임). 하는 일은 "곧 꺼도 됨" 표시뿐
            BYE_AT[0] = time.time()
            self.body(4096)
            return self.send_json({"ok": True})
        if not self.host_ok() or self.headers.get("X-Studio") != "1":
            return self.send_error(403)
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            if u.path == "/api/upload":
                return self.send_json(self.upload(q))
            return self.send_json(self.api_post(u.path, self.jbody()))
        except ApiError as e:
            return self.send_json({"error": str(e)}, e.status)
        except SystemExit as e:
            return self.send_json({"error": str(e.code)}, 400)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return None   # 브라우저가 요청을 취소함 (탭 이동 등) — 기록할 필요 없음
        except Exception as e:  # noqa: BLE001
            fe = friendly_error(e)
            user_err = type(e).__name__ in ("UnidentifiedImageError", "JSONDecodeError", "PermissionError")
            if not user_err:
                log(traceback.format_exc())
            try:
                return self.send_json({"error": fe if fe != str(e) else f"처리 중 오류: {e}"}, 400 if user_err else 500)
            except OSError:
                return None

    def upload(self, q):
        name = Path(q.get("name") or "file").name
        name = re.sub(r"[^\w.\-가-힣 ()]", "_", name)[-80:] or "file"
        UPLOADS.mkdir(parents=True, exist_ok=True)
        uid = uuid.uuid4().hex[:12] + "_" + name
        (UPLOADS / uid).write_bytes(self.body())
        return {"id": uid, "name": name}

    def api_post(self, path, d):
        tools_dir = str(ROOT / "tools")
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)

        if path == "/api/quit":
            threading.Thread(target=lambda: (time.sleep(.3), SERVER[0].shutdown()), daemon=True).start()
            return {"ok": True}

        if path == "/api/brand/create":
            from new_brand import BrandError, create_brand
            try:
                r = create_brand(d.get("slug"), d.get("name"), d.get("accent") or None, d.get("bg") or None,
                                 bool(d.get("light")), str(upload_path(d["palette"])) if d.get("palette") else None,
                                 str(upload_path(d["logo"])) if d.get("logo") else None,
                                 str(upload_path(d["mascot"])) if d.get("mascot") else None, bool(d.get("serif")))
            except BrandError as e:
                raise ApiError(str(e))
            return r

        if path == "/api/brand/save":
            bdir = brand_dir(d.get("slug"))
            b = d.get("brand")
            if not isinstance(b, dict) or not isinstance(b.get("colors"), dict):
                raise ApiError("브랜드 형식이 올바르지 않습니다")
            b["slug"] = bdir.name
            write_json(bdir / "brand.json", b)
            return {"ok": True, "summary": brand_summary(bdir.name)}

        if path == "/api/brand/asset":
            bdir = brand_dir(d.get("slug"))
            key = d.get("key")
            if key not in ("logo", "mascot"):
                raise ApiError("로고나 마스코트만 바꿀 수 있습니다")
            b = load_json(bdir / "brand.json")
            assets = b.setdefault("assets", {})
            if d.get("remove"):
                assets.pop(key, None)
                b[key] = None
                if key == "logo" and not b.get("logoText"):
                    b["logoText"] = b.get("name", "")
                write_json(bdir / "brand.json", b)
                return {"ok": True}
            src = upload_path(d.get("upload"))
            from PIL import Image
            (bdir / "assets").mkdir(exist_ok=True)
            dst = bdir / "assets" / f"{key}.png"
            im = Image.open(src)
            im.convert("RGBA").save(dst)
            assets[key] = f"assets/{dst.name}"
            b[key] = key
            write_json(bdir / "brand.json", b)
            alpha = im.mode in ("RGBA", "LA") or "transparency" in im.info
            res = {"ok": True, "url": rel_url(dst) + f"?m={int(time.time())}", "hasAlpha": alpha}
            if d.get("cutout"):
                res["job"] = cutout_job(dst, dst).as_dict(False)
            return res

        if path == "/api/video/create":
            from new_video import VideoError, create_video
            try:
                create_video(d.get("name"), d.get("brand"), d.get("template") or "promo", d.get("formats") or None,
                             d.get("title") or None, d.get("preset") or None, (d.get("brief") or "") if d.get("scratch") else None)
            except VideoError as e:
                raise ApiError(str(e))
            out = video_detail(d["name"])
            if d.get("scratch") and d.get("openClaude") and claude_engine() != "api" and find_claude():
                try:   # 영상은 이미 만들어졌으니 Claude Code 를 못 열어도 실패로 돌려주지 않음 (다시 누르면 '이미 있는 영상'이 되므로)
                    open_claude_code(claude_first_message(d["name"]))
                    out["claudeOpened"] = True
                except Exception as e:  # noqa: BLE001
                    log(f"Claude Code 를 열지 못함: {e}")
                    out["claudeOpened"] = False
            return out

        if path == "/api/video/duplicate":
            src = video_path(d.get("name"))
            new = d.get("newName", "")
            if not SLUG.fullmatch(new):
                raise ApiError("새 영문 이름은 영문 소문자, 숫자, 하이픈만 쓸 수 있습니다")
            dst = ROOT / "videos" / new
            if dst.exists():
                raise ApiError("같은 이름의 영상이 이미 있습니다")
            if d.get("brand"):
                brand_dir(d["brand"])   # 복사하기 전에 확인 (잘못된 계정이면 빈 폴더가 남지 않게)
            shutil.copytree(src, dst)
            v = load_json(dst / "video.json")
            v["title"] = d.get("title") or (v.get("title", src.name) + " 복사본")
            if d.get("brand"):
                brand_dir(d["brand"])
                v["brand"] = d["brand"]
            write_json(dst / "video.json", v)
            return video_detail(new)

        if path == "/api/video/save":
            vdir = video_path(d.get("name"))
            v = d.get("video")
            validate_video(v)
            # 사진(assets)과 음악은 별도 기능이 관리하므로, 화면에 아직 반영 안 된 값이 있으면 지우지 않고 합침
            disk = load_json(vdir / "video.json")
            # 음악은 음악 칸(/api/music)과 음악 만들기 작업만 고칩니다. 화면이 들고 있던 옛 값으로 덮지 않게
            # 디스크 값을 그대로 씀 (고급 탭의 원본 편집은 raw=true 로 예외)
            if not d.get("raw"):
                if "music" in disk:
                    v["music"] = disk["music"]
                else:
                    v.pop("music", None)
            v["assets"] = merge_missing(disk.get("assets") or {}, v.get("assets") or {})
            write_json(vdir / "video.json", v)
            return {"ok": True, "status": video_status(vdir.name, v)}

        if path == "/api/preview":
            name, fmt = d.get("name"), d.get("format")
            vdir = video_path(name)
            v = load_json(vdir / "video.json")
            if fmt not in (v.get("formats") or FORMATS):
                fmt = (v.get("formats") or ["tall"])[0]
            with BUILD_LOCK:
                from build import build_video
                t0 = time.time()
                [out] = build_video(name, [fmt])
            return {"url": rel_url(out) + f"?m={int(time.time() * 1000)}", "format": fmt, "ms": int((time.time() - t0) * 1000)}

        if path == "/api/photo/add":
            vdir = video_path(d.get("name"))
            from photo import PhotoError, add_photo
            key = d.get("key") or next_photo_key(vdir)
            try:
                up = upload_path(d.get("upload"))
                r = add_photo(vdir.name, up, key, d.get("credit", ""), d.get("license") or "자체 촬영/보유",
                              title=up.name.split("_", 1)[-1])
            except PhotoError as e:
                raise ApiError(str(e))
            return {"ok": True, "photo": r, "detail": video_detail(vdir.name)}

        if path == "/api/photo/get":
            vdir = video_path(d.get("name"))
            key = d.get("key") or next_photo_key(vdir)
            return photo_get_job(vdir.name, d.get("title", ""), key).as_dict()

        if path == "/api/photo/remove":
            vdir = video_path(d.get("name"))
            v = load_json(vdir / "video.json")
            va = v.get("assets") or {}
            for g in ([va.get("common", {})] + [va.get(f, {}) for f in FORMATS]) if any(k in FORMATS or k == "common" for k in va) else [va]:
                g.pop(d.get("key"), None)
            write_json(vdir / "video.json", v)
            return video_detail(vdir.name)

        if path == "/api/music":
            vdir = video_path(d.get("name"))
            v = load_json(vdir / "video.json")
            if d.get("remove"):
                v.pop("music", None)
            else:
                m = dict(v.get("music") or {})
                if d.get("upload"):
                    src = upload_path(d["upload"])
                    ext = src.suffix.lower() if src.suffix.lower() in (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".mp4", ".mov") else ".mp3"
                    # 새 이름으로 넣음: 음악 탭의 재생기가 예전 파일을 쥐고 있어도(윈도 파일 잠금) 실패하지 않게
                    newname = f"music-{int(time.time() * 1000)}{ext}"
                    shutil.copy(src, vdir / newname)
                    for old in list(vdir.glob("music.*")) + list(vdir.glob("music-*.*")):
                        if old.name != newname:
                            try:
                                old.unlink()
                            except OSError:
                                pass
                    m["file"] = newname
                    m["name"] = src.name.split("_", 1)[-1]
                    for k in ("engine", "model", "usd", "seed", "prompt"):
                        m.pop(k, None)
                    # 박자를 재서 곡의 첫 박을 영상 0초에 맞춤 (Gemini 앱·Vids 에서 받은 곡도)
                    try:
                        import music
                        a = music.analyze(vdir / m["file"], safe_float(d.get("bpm")))
                        m.update({"bpm": a["bpm"], "beat": a["beat"], "start": a["downbeat"]})
                    except (Exception, SystemExit) as e:  # noqa: BLE001
                        log(f"박자 분석 실패: {e}")
                        for k in ("bpm", "beat"):
                            m.pop(k, None)
                        m["start"] = 0
                for k in ("volume", "fadeIn", "fadeOut", "start"):
                    if k in d:
                        m[k] = safe_float(d[k], 0)
                v["music"] = m
            write_json(vdir / "video.json", v)
            return video_detail(vdir.name)

        if path == "/api/open-web":
            # 앱 창(별도 프로필)이 아니라 평소 쓰는 브라우저로 엶. 구글 로그인이 거기 있어서
            url = str(d.get("url") or "")
            host = urllib.parse.urlparse(url).hostname or ""
            if not url.startswith("https://") or host not in ("gemini.google.com", "aistudio.google.com", "vids.google.com",
                                                                     "console.cloud.google.com", "studio.youtube.com", "www.instagram.com", "console.anthropic.com"):
                raise ApiError("열 수 없는 주소예요")
            webbrowser.open(url)
            return {"ok": True}
        if path == "/api/music/key":
            import music
            key = str(d.get("key") or "").strip()
            if key and not re.fullmatch(r"[A-Za-z0-9_\-]{20,80}", key):
                raise ApiError("키 모양이 맞지 않아요. Google AI Studio에서 복사한 키를 그대로 붙여 넣어 주세요")
            import accounts
            if key:
                try:
                    accounts.add("gemini", str(d.get("name") or ""), key)
                except ValueError as e:
                    raise ApiError(str(e))
            else:   # '바꾸기': 지금 쓰는 키를 지우지 않고 '쓰는 키 없음' 대신 계정 창에서 고르게 함 → 여기서는 그대로
                pass
            return music.status()
        if path == "/api/agent/run":
            if claude_engine() != "api":
                raise ApiError("지금은 Claude Code 로그인 방식이에요. 'AI 계정'에서 API 키로 바꾸거나 'Claude Code 열기'를 써 주세요")
            return agent_job(d.get("name") or None, str(d.get("text") or ""), d.get("session") or None)
        if path == "/api/agent/session":
            return agent_session(d.get("name") or None, d.get("session") or None)
        if path == "/api/accounts":
            import accounts
            op, prov = str(d.get("op") or "list"), str(d.get("provider") or "claude")
            try:
                if op == "add":
                    accounts.add(prov, str(d.get("name") or ""), str(d.get("key") or ""), activate=True)
                elif op == "use":
                    accounts.use(prov, str(d.get("id") or ""))
                elif op == "remove":
                    accounts.remove(prov, str(d.get("id") or ""))
                elif op == "rename":
                    accounts.rename(prov, str(d.get("id") or ""), str(d.get("name") or ""))
                elif op == "budget":
                    import music
                    music.save_settings({"agent_budget": max(.5, min(50.0, float(d.get("budget") or 3)))})
                elif op == "engine":
                    accounts.set_engine("api" if d.get("engine") == "api" else "code")
                elif op == "test":
                    ok, msg = accounts.test(prov, str(d.get("id") or "") or None)
                    out = accounts.public()
                    out["test"] = {"ok": ok, "msg": msg}
                    out["status"] = claude_status_bits()
                    out["budget"] = agent_budget()
                    return out
                elif op != "list":
                    raise ApiError("모르는 요청이에요")
            except ValueError as e:
                raise ApiError(str(e))
            out = accounts.public()
            out["status"] = claude_status_bits()
            out["budget"] = agent_budget()
            return out
        if path == "/api/music/stop":
            import music
            music.ace_stop()
            return music.status()
        if path == "/api/job/music-setup":
            target = str(d.get("dir") or "").strip() or None
            return music_setup_job(target).as_dict()
        if path == "/api/job/music":
            return music_job(d.get("name"), d).as_dict()
        if path == "/api/music/pick":
            # 전에 만든 곡으로 바꾸기 (videos/<영상>/music/ 안의 파일)
            vdir = video_path(d.get("name"))
            f = str(d.get("file") or "")
            src = (vdir / f).resolve()
            if not f.startswith("music/") or vdir.resolve() not in src.parents or not src.exists():
                raise ApiError("곡 파일을 찾을 수 없어요")
            import music
            v = load_json(vdir / "video.json")
            m = dict(v.get("music") or {})
            a = music.analyze(src, m.get("bpm"))
            m.update({"file": f, "name": src.name, "bpm": a["bpm"], "beat": a["beat"], "start": a["downbeat"]})
            v["music"] = m
            write_json(vdir / "video.json", v)
            return video_detail(vdir.name)

        if path == "/api/job/render":
            return render_job(d.get("name"), d.get("formats") or [], reuse=bool(d.get("reuse"))).as_dict()
        if path == "/api/job/deck-pptx":
            return deck_pptx_job(d.get("name")).as_dict()
        if path == "/api/deck/open-file":
            f = (OUT / video_path(d.get("name")).name / "wide" / f"{video_path(d.get('name')).name}.{'pptx' if d.get('kind') == 'pptx' else 'pdf'}")
            if not f.exists():
                raise ApiError("아직 만든 파일이 없어요")
            try:
                if os.name == "nt":
                    os.startfile(str(f))  # noqa: S606  PowerPoint·PDF 보기로 열기
                else:
                    webbrowser.open(f.as_uri())
            except Exception as e:  # noqa: BLE001
                raise ApiError(f"파일을 열지 못했어요: {e}")
            return {"ok": True}
        if path == "/api/job/deck-pdf":
            return deck_pdf_job(d.get("name")).as_dict()
        if path == "/api/deck/source":
            vdir = video_path(d.get("name"))
            if d.get("remove"):
                for f in (vdir / "source.md",):
                    if f.exists():
                        f.unlink()
                v = load_json(vdir / "video.json")
                v.pop("source", None)
                write_json(vdir / "video.json", v)
                return video_detail(vdir.name)
            src = upload_path(d.get("upload"))
            from deck import add_source
            try:
                r = add_source(vdir.name, src, display=re.sub(r"^[0-9a-f]{12}_", "", src.name))
            except RuntimeError as e:
                raise ApiError(str(e))
            out = video_detail(vdir.name)
            out["added"] = r
            return out
        if path == "/api/deck/present":
            name = video_path(d.get("name")).name
            with BUILD_LOCK:
                from build import build_video
                [html] = build_video(name, ["wide"])
            try:
                if os.name == "nt":
                    os.startfile(str(html))  # noqa: S606  기본 브라우저로 발표 파일 열기
                else:
                    webbrowser.open(Path(html).as_uri())
            except Exception as e:  # noqa: BLE001
                raise ApiError(f"브라우저로 열지 못했어요: {e}")
            return {"ok": True, "path": str(html)}
        if path == "/api/job/sheet":
            return sheet_job(d.get("name"), d.get("formats") or [], bool(d.get("safe"))).as_dict()
        if path == "/api/job/ai":
            brief = (d.get("brief") or "").strip()
            if len(brief) < 5:
                raise ApiError("무엇을 알리는 광고인지 한두 문장 적어 주세요")
            target = d.get("target")
            target = int(target) if str(target or "").isdigit() and 3 <= int(target) <= 180 else None
            return ai_copy_job(d.get("name"), brief, target).as_dict()
        if path == "/api/job/autophoto":
            return autophoto_job(d.get("name"), d.get("scenes"), d.get("queries")).as_dict()
        if path == "/api/job/autophoto-apply":
            return autophoto_apply_job(d.get("name"), d.get("picks") or []).as_dict()
        if path == "/api/job/cancel":
            j = JOBS.get(d.get("id", ""))
            if j and j.status == "running":
                j.cancelled = True
                if j.proc:
                    j.proc.terminate()
            return {"ok": True}

        if path == "/api/credits":
            from photo import credits_markdown
            return {"text": credits_markdown(video_path(d.get("name")).name)}

        if path == "/api/open":
            target = (ROOT / (d.get("path") or "")).resolve()
            if ROOT.resolve() not in target.parents and target != ROOT.resolve():
                raise ApiError("열 수 없는 위치입니다")
            if target.is_file():
                target = target.parent
            target.mkdir(parents=True, exist_ok=True)
            open_folder(target)
            return {"ok": True}

        if path == "/api/claude-code":
            if claude_engine() == "api":
                raise ApiError("API 모드에서는 Claude Code 창 대신 앱 안 'Claude에게 부탁하기'를 써요")
            if not find_claude():
                raise ApiError("Claude Code를 찾을 수 없습니다. 이 PC에 Claude Code가 있어야 창을 열 수 있어요 (앱 안 문구 맡기기는 'AI 계정'의 API 키로도 돼요)")
            open_claude_code(claude_first_message(d["name"]) if d.get("name") else None)
            return {"ok": True}

        if path == "/api/claude-model":
            import music
            patch = {}
            if "model" in d:
                m = str(d.get("model") or "")
                if m not in {k for k, _ in CLAUDE_MODELS}:
                    raise ApiError("고를 수 없는 모델이에요")
                patch["claude_model"] = m or None
            if "effort" in d:
                e = str(d.get("effort") or "")
                if e not in {k for k, _ in CLAUDE_EFFORTS}:
                    raise ApiError("고를 수 없는 노력 정도예요")
                patch["claude_effort"] = e or None
            music.save_settings(patch)
            return {"ok": True, "claudeModel": claude_model(), "claudeEffort": claude_effort()}

        if path == "/api/publish/save":
            return publish_save(d.get("name"), d.get("upload") or {}, d.get("social"))

        if path == "/api/publish/open":
            nm = video_path(d.get("name")).name
            url = str(d.get("url") or "")
            if url:
                host = urllib.parse.urlparse(url).hostname or ""
                if not url.startswith("https://") or host not in ("youtube.com", "www.youtube.com", "youtu.be", "studio.youtube.com"):
                    raise ApiError("열 수 없는 주소예요")
                webbrowser.open(url)
                return {"ok": True}
            page = ROOT / "out" / nm / "upload" / "upload.html"
            if not page.exists():
                raise ApiError("업로드 안내를 먼저 만들어 주세요")
            webbrowser.open(page.resolve().as_uri())
            return {"ok": True}

        if path == "/api/job/publish-kit":
            return publish_kit_job(d.get("name")).as_dict()

        if path == "/api/job/publish-ai":
            return publish_ai_job(d.get("name"), str(d.get("brief") or "")).as_dict()

        if path == "/api/youtube/client":
            import upload as up
            src = upload_path(d.get("upload"))
            try:
                cid = up.set_client(src)
            except (up.UploadError, ValueError) as e:
                raise ApiError(str(e) if isinstance(e, up.UploadError) else "JSON 파일을 읽지 못했어요")
            finally:
                src.unlink(missing_ok=True)
            return {"ok": True, "client": cid[:12] + "…"}

        if path == "/api/job/youtube-connect":
            return youtube_connect_job(d.get("brand")).as_dict()

        if path == "/api/youtube/disconnect":
            import upload as up
            brand_dir(d.get("brand"))
            up.yt_disconnect(d.get("brand"))
            return {"ok": True}

        if path == "/api/job/youtube-upload":
            return youtube_upload_job(d.get("name"), d.get("fmt") or None, d.get("privacy") or None).as_dict()

        if path == "/api/video/look":
            # 결 템플릿끼리 바꾸기: 같은 content 를 읽으니 문구는 그대로, 템플릿·(기본이던) 스타일·연출 프롬프트만 바꿈
            from presets import get_preset
            vdir = video_path(d.get("name"))
            v = load_json(vdir / "video.json")
            try:
                newp = get_preset(str(d.get("template") or ""))
            except KeyError:
                raise ApiError("그 결 템플릿을 찾을 수 없어요")
            if newp.get("group") != "look":
                raise ApiError("결 템플릿끼리만 바꿀 수 있어요")
            try:
                oldp = get_preset(v.get("template") or "")
            except KeyError:
                oldp = {}
            if oldp.get("group") != "look":
                raise ApiError("이 영상은 결 템플릿이 아니라서 바꿀 수 없어요")
            if not v.get("style") or v.get("style") == oldp.get("style"):
                if newp.get("style"):
                    v["style"] = newp["style"]
            v["template"] = newp["template"]
            if v.get("preset") == oldp.get("id"):
                v["preset"] = newp["id"]
            dp = vdir / "direction.md"
            old_dir = (oldp.get("direction") or "").strip()
            if newp.get("direction") and (not dp.exists() or dp.read_text(encoding="utf-8-sig").strip() == old_dir):
                dp.write_text(newp["direction"], encoding="utf-8")   # 손대지 않은 연출 프롬프트만 새 결 것으로
            write_json(vdir / "video.json", v)
            return video_detail(vdir.name)

        if path == "/api/direction":
            vd = video_path(d.get("name"))
            text = str(d.get("text") or "")
            if len(text) > 60000:
                raise ApiError("연출 프롬프트가 너무 길어요")
            (vd / "direction.md").write_text(text, encoding="utf-8")
            return {"ok": True}

        raise ApiError("없는 기능입니다", 404)


def claude_first_message(name):
    """앱에서 Claude Code 를 열 때 건네는 첫 말. 영상에 스타일을 골랐으면 스타일 카드를 따르라는 말을 붙임."""
    msg = _first_message(name)
    try:
        sid = load_json(video_path(name) / "video.json").get("style")
    except Exception:  # noqa: BLE001
        sid = None
    if sid and (ROOT / "styles" / sid / "style.json").exists():
        msg += (f" 화면의 결은 styles/{sid}/style.md 스타일 카드대로 맞춰 줘(signature 움직임은 꼭 넣고 avoid 는 피하기, "
                f"질감·글꼴·색 적용 방식은 docs/STYLES.md).")
    return msg


def _first_message(name):
    """처음부터 짜는 영상 / 연출 프롬프트가 있는 영상 / 그 밖."""
    nm = video_path(name).name
    vdir = ROOT / "videos" / nm
    try:
        v = load_json(vdir / "video.json")
    except Exception:  # noqa: BLE001
        v = {}
    if v.get("scratch"):
        det = video_detail(nm)
        if det.get("starter"):
            return (f"videos/{nm}/direction.md 에 적은 영상을 docs/SCRATCH.md 의 순서와 규칙대로 처음부터 짜 줘. "
                    f"brand.json 의 말투와 규칙을 지키고, 설명에 없는 사실(가격·날짜·수치·이름)은 지어내지 말고 먼저 물어봐 줘. "
                    f"짜기 전에 장면 계획(장면마다 몇 초, 무엇이 보이는지)을 짧게 보여 줘.")
        return (f"videos/{nm} 는 처음부터 짠 영상이야(docs/SCRATCH.md, scene.html). direction.md 와 video.json 을 읽고 "
                f"지금 상태를 짧게 알려 준 다음, 무엇을 바꿀지 물어봐 줘.")
    if (vdir / "direction.md").exists():
        return (f"videos/{nm}/direction.md 의 연출 프롬프트를 읽고, 그 연출대로 videos/{nm} 영상을 다듬어 줘. "
                f"brand.json 의 말투와 규칙을 지켜 줘. video.json 의 문구가 아직 프리셋 예시 그대로(가게 이름, 예시 가격·날짜 같은 자리 글)면 "
                f"먼저 나에게 실제 정보(무엇을 알리는지, 가격·기간·장소 등)를 물어보고, 바꿀 점을 짧게 정리해서 보여 준 다음 진행해 줘.")
    return f"videos/{nm} 영상을 같이 고치려고 해. video.json 을 읽고 지금 상태를 짧게 알려 줘."


def open_folder(p):
    if IS_WIN:
        os.startfile(str(p))  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(p)])
    else:
        subprocess.Popen(["xdg-open", str(p)])


def open_claude_code(first=None):
    """Claude Code 를 스튜디오 폴더에서 엶. first 를 주면 그 말로 대화를 시작함. 앱에서 고른 모델·노력 정도를 붙임."""
    flags = claude_flags()
    if IS_WIN:
        q = (" '" + first.replace(chr(39), chr(39) * 2) + "'") if first else ""
        fl = "".join(f" {x}" for x in flags)
        found = find_claude()
        exe = "claude"
        if found and len(found) == 1 and not found[0].lower().endswith(".py"):
            exe = "& '" + found[0].replace(chr(39), chr(39) * 2) + "'"   # PATH 에 없어도 찾은 위치로 실행
        cmd = f"$env:PYTHONUTF8='1'; Set-Location -LiteralPath '{str(ROOT).replace(chr(39), chr(39) * 2)}'; {exe}{fl}{q}"
        subprocess.Popen(["powershell.exe", "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                         creationflags=subprocess.CREATE_NEW_CONSOLE, env=claude_code_env())
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-a", "Terminal", str(ROOT)], env=claude_code_env())
    else:
        subprocess.Popen(["x-terminal-emulator", "-e", "claude"] + flags + ([first] if first else []), cwd=str(ROOT), env=claude_code_env())


def find_app_browser():
    if not IS_WIN:
        for name in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
            p = shutil.which(name)
            if p:
                return p
        return None
    env = os.environ
    cands = [Path(env.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
             Path(env.get("ProgramFiles", r"C:\Program Files")) / "Microsoft/Edge/Application/msedge.exe",
             Path(env.get("ProgramFiles", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
             Path(env.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
             Path(env.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe"]
    for c in cands:
        if c.exists():
            return str(c)
    return None


def open_window(url):
    exe = find_app_browser()
    if exe:
        profile = APPDATA / "window"
        profile.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.Popen([exe, f"--app={url}", "--window-size=1600,980", f"--user-data-dir={profile}",
                              "--no-first-run", "--no-default-browser-check"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except Exception:
            log(traceback.format_exc())
    webbrowser.open(url)


def ping(port, info=False):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=1.5) as r:
            d = json.loads(r.read().decode("utf-8"))
            ok = d.get("app") == "motion-studio"
            return (d if ok else None) if info else ok
    except Exception:
        return None if info else False


def replace_old_server(port):
    """같은 포트에 예전 버전 앱 서버가 떠 있으면(새로 설치한 뒤 앱을 안 껐을 때) 끄고 True. 작업 중이면 그대로 둠."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/jobs", timeout=2) as r:
            jobs = json.loads(r.read().decode("utf-8")).get("jobs") or []
        if any(j.get("status") == "running" for j in jobs):
            log("예전 버전 앱이 작업 중이라 그대로 엽니다. 작업이 끝나면 앱을 껐다 켜 주세요.")
            return False
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/quit", data=b"{}", method="POST",
                                     headers={"X-Studio": "1", "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=2).read()
    except Exception:  # noqa: BLE001
        return False
    for _ in range(20):
        time.sleep(.25)
        if not ping(port):
            log(f"예전 버전 앱(포트 {port})을 끄고 새 버전으로 켭니다.")
            time.sleep(.3)
            return True
    return False


def watchdog():
    """창이 닫히고(핑이 끊기고) 하는 작업이 없으면 서버를 끔.
    창을 내리거나 다른 창에 가려지면 브라우저가 타이머를 1분에 한 번 정도로 줄이니, 핑이 10분 넘게 없을 때만 끔.
    창을 닫을 때 보내는 bye 를 받으면 30초 안에 다시 핑이 없을 때 끔."""
    while True:
        time.sleep(5)
        now = time.time()
        closed = BYE_AT[0] and now - BYE_AT[0] > 30 and LAST_PING[0] < BYE_AT[0]
        if LAST_PING[0] and (closed or now - LAST_PING[0] > 600) and not running_jobs():
            log("창이 닫혀 앱을 끕니다.")
            SERVER[0].shutdown()
            return


class StudioServer(ThreadingHTTPServer):
    # 윈도에서는 SO_REUSEADDR 가 같은 포트를 두 프로그램이 함께 잡게 해 버리므로 끔 (앱을 두 번 눌렀을 때 서버가 둘 생기지 않게)
    allow_reuse_address = not IS_WIN
    daemon_threads = True


def self_update():
    """GitHub 에 새 버전이 있으면 받아서 바꾸고 True (tools/update.py). 인터넷·git 이 없으면 조용히 넘어감."""
    if "--no-update" in sys.argv or os.environ.get("MS_NO_UPDATE"):
        return False
    try:
        import update
        res = update.run(log)
    except Exception:  # noqa: BLE001
        log("업데이트 확인 중 오류:\n" + traceback.format_exc())
        return False
    return bool(res and res.get("updated"))


def main():
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8765
    no_window = "--no-window" in sys.argv
    if self_update():
        # 새 코드로 다시 켬 (이 프로세스는 옛 코드를 이미 불러 와서)
        log("새 버전으로 다시 켭니다")
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), *sys.argv[1:], "--no-update"], cwd=str(ROOT))
        return
    for p in range(port, port + 20):
        old = ping(p, info=True)
        if old and old.get("build") != BUILD and replace_old_server(p):
            old = None
        if old:
            url = f"http://127.0.0.1:{p}/"
            log(f"이미 켜져 있는 앱을 엽니다: {url}")
            if not no_window:
                open_window(url)
            return
        try:
            srv = StudioServer(("127.0.0.1", p), Handler)
            break
        except OSError:
            continue
    else:
        sys.exit("쓸 수 있는 포트를 찾지 못했습니다.")
    srv.daemon_threads = True
    SERVER[0] = srv
    # 하루 넘은 업로드 임시 파일 정리
    if UPLOADS.exists():
        for f in UPLOADS.iterdir():
            try:
                if time.time() - f.stat().st_mtime > 86400:
                    f.unlink()
            except OSError:
                pass
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    log(f"모션 스튜디오 앱: {url}")
    if not no_window:
        threading.Thread(target=watchdog, daemon=True).start()
        threading.Timer(.4, open_window, args=(url,)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    for j in running_jobs():
        if j.proc:
            j.proc.terminate()
    # 앱이 켠 무료 음악 엔진은 그래픽 메모리를 잡고 있으니 같이 끔
    try:
        import music
        if (APPDATA / "acestep.pid").exists():
            music.ace_stop()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException:  # noqa: BLE001  pythonw 로 켜면 오류가 화면에 안 보이니 기록하고 알림 창을 띄움
        log("앱을 켜지 못함:\n" + traceback.format_exc())
        if IS_WIN:
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(None, "모션 스튜디오를 켜지 못했어요.\n\n자세한 내용: 문서\\motion-studio\\out\\_app\\app.log\n"
                                                 "StudioApp_debug.cmd 를 실행하면 오류를 볼 수 있어요.", "모션 스튜디오", 0x10)
            except Exception:  # noqa: BLE001
                pass
        raise
