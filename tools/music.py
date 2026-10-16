"""배경음악 만들기와 박자 분석.

사용법:
    python tools/music.py gen <영상> [옵션]               # 구글 Gemini(Lyria)로 영상 길이에 맞는 연주곡을 받아 video.json 에 연결
    python tools/music.py prompt <영상> [--mood cafe]     # Gemini 앱(gemini.google.com)에 붙여 넣을 프롬프트 (무료로 손수 만들 때)
    python tools/music.py beats <곡 파일> [--bpm 120]      # BPM과 첫 다운비트 찾기 (받은 곡을 넣을 때 앱이 자동으로 함)
    python tools/music.py key <Gemini API 키>              # 키 저장 (PC마다 한 번). 지우려면 key -
    python tools/music.py status                          # 키·엔진 상태

gen 옵션:
    --mood cafe                   분위기 (minimal keynote cafe lofi citypop travel cinematic funk)
    --prompt "영어 분위기 설명"   직접 적기. 예) "warm acoustic cafe groove, soft guitar, light percussion"
    --bpm 120                     박자. 모션을 박자에 맞춘 영상이면 같은 값을 줍니다
    --seconds 30                  길이. 비우면 영상 길이를 재서 씁니다
    --yes                         비용에 동의 (없으면 비용만 알려 주고 멈춤)

구글 Gemini API 의 Lyria 는 무료 등급이 없어요. 영상이 28초 이하면 30초 곡 lyria-3-clip-preview(약 0.04달러),
더 길면 lyria-3.5(약 0.08달러)를 씁니다. 키는 Google AI Studio 에서 만들고 결제를 연결해야 합니다.
무료로 하려면 Gemini 앱에서 'prompt' 로 받은 문장을 붙여 넣어 연주곡을 만들고, 받은 MP3 를 앱에 넣으세요.

(고급) 그래픽카드가 있는 PC에서는 오픈소스 ACE-Step 1.5 를 설치해 무료로 돌릴 수도 있어요:
    python tools/music.py setup [--dir 경로]  →  python tools/music.py gen <영상> --engine ace

만든 곡은 videos/<영상>/music/ 에 쌓이고, 마지막 곡이 video.json 의 music 으로 연결됩니다.
곡의 첫 다운비트(마디 첫 박)를 찾아 영상 0초에 맞춥니다(music.start).
"""
import base64
import json
import math
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, load_json  # noqa: E402

IS_WIN = os.name == "nt"
NO_WINDOW = 0x08000000 if IS_WIN else 0
DETACHED = 0x00000008 if IS_WIN else 0
NEW_GROUP = 0x00000200 if IS_WIN else 0
SETTINGS = Path.home() / ".motion-studio" / "settings.json"
APPDATA = ROOT / "out" / "_app"
ACE_REPO = "https://github.com/ace-step/ACE-Step-1.5.git"
ACE_ZIP = "https://codeload.github.com/ace-step/ACE-Step-1.5/zip/refs/heads/main"
ACE_PORT = int(os.environ.get("ACESTEP_API_PORT", "8001"))
ACE_URL = f"http://127.0.0.1:{ACE_PORT}"
LYRIA_URL = os.environ.get("MOTION_STUDIO_GEMINI_URL") or "https://generativelanguage.googleapis.com/v1beta/interactions"
LYRIA = {  # 2026-09 기준 Gemini API 가격 (무료 등급 없음)
    "clip": {"model": "lyria-3-clip-preview", "usd": 0.04, "max": 30},
    "song": {"model": "lyria-3.5", "usd": 0.08, "max": 180},
}

# 앱의 분위기 고르기와 같은 목록 (영어 설명이 음악 모델에 더 잘 먹힙니다)
MOODS = {
    "minimal": "minimal modern electronic, clean punchy drums, warm sub bass, crisp hi-hats, sleek and confident, product launch",
    "keynote": "uplifting modern keynote music, bright plucked synths, steady four-on-the-floor kick, airy pads",
    "cafe": "warm acoustic cafe groove, soft nylon guitar, brushed drums, upright bass, cozy morning mood",
    "lofi": "chill lo-fi hip hop, dusty drums, mellow electric piano, vinyl warmth, relaxed",
    "citypop": "bright city pop, funky bass, clean electric guitar, glossy synths, summer drive",
    "travel": "upbeat travel vlog music, tropical house, marimba, claps, sunny and energetic",
    "cinematic": "cinematic hybrid trailer, pulsing synths, big drums, rising tension, epic hits",
    "funk": "funky disco house, slap bass, clavinet, groovy drums, playful",
}


def say(msg):
    print(msg, flush=True)


def step(i, n, msg):
    say(f"단계 {i}/{n} {msg}")


# ------------------------------------------------------------------ 설정
def settings():
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def save_settings(patch):
    s = settings()
    for k, v in patch.items():
        if v is None:
            s.pop(k, None)
        else:
            s[k] = v
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    return s


def gemini_key():
    """환경 변수 → 앱에서 고른 Gemini 계정(accounts.py) → 예전 방식 settings.json 키 순서."""
    k = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if k:
        return k
    try:
        import accounts
        k = accounts.active("gemini")[1]
    except Exception:  # noqa: BLE001
        k = ""
    return k or settings().get("gemini_api_key") or ""


# ------------------------------------------------------------------ ACE-Step (무료, 내 PC)
def default_ace_dir():
    """C 드라이브가 좁으면 여유 있는 다른 드라이브에 둡니다."""
    if IS_WIN:
        best = None
        for letter in "DEFGH":
            root = Path(f"{letter}:\\")
            try:
                if root.exists():
                    free = shutil.disk_usage(root).free
                    if free > 40e9 and (best is None or free > best[1]):
                        best = (root, free)
            except Exception:
                pass
        if best:
            return best[0] / "MotionStudio-engines" / "ACE-Step-1.5"
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "MotionStudio" / "ACE-Step-1.5"
    return Path.home() / ".motion-studio" / "ACE-Step-1.5"


def ace_dir():
    d = os.environ.get("ACESTEP_DIR") or settings().get("acestep_dir")
    return Path(d) if d else None


def ace_installed(d=None):
    d = d or ace_dir()
    return bool(d and (d / "pyproject.toml").exists() and (d / ".venv").exists())


def ace_models_ready(d=None):
    d = d or ace_dir()
    ck = d / "checkpoints" if d else None
    return bool(ck and (ck / "acestep-v15-turbo").exists() and (ck / "vae").exists())


def http_json(url, data=None, timeout=10, headers=None):
    body = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST" if data is not None else "GET",
                                 headers=dict({"Content-Type": "application/json"}, **(headers or {})))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def ace_running():
    try:
        r = http_json(ACE_URL + "/health", timeout=2)
        return (r.get("data") or {}).get("status") == "ok" or r.get("code") == 200
    except Exception:
        return False


def find_uv():
    for c in (shutil.which("uv"), Path.home() / ".local" / "bin" / ("uv.exe" if IS_WIN else "uv"),
              Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links" / "uv.exe"):
        if c and Path(c).exists():
            return [str(c)]
    try:
        subprocess.run([sys.executable, "-m", "uv", "--version"], check=True, capture_output=True)
        return [sys.executable, "-m", "uv"]
    except Exception:
        return None


def gpu_name():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=10, creationflags=NO_WINDOW)
        return r.stdout.strip().splitlines()[0] if r.returncode == 0 and r.stdout.strip() else ""
    except Exception:
        return ""


def stream(args, cwd=None, env=None):
    """명령을 실행하며 출력을 그대로 흘려보냄 (앱 작업 기록에 보이도록)."""
    p = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                         creationflags=NO_WINDOW)
    last = ""
    for raw in p.stdout:
        line = raw.decode("utf-8", "replace").rstrip()
        # 진행 막대처럼 같은 줄을 계속 덮어쓰는 출력은 줄여서 보여 줍니다
        line = line.split("\r")[-1].strip()
        if line and line != last:
            say("  " + line[:220])
            last = line
    p.wait()
    if p.returncode != 0:
        raise SystemExit(f"명령이 실패했습니다 (코드 {p.returncode}): {' '.join(map(str, args[:3]))}")


def ace_setup(target=None):
    n = 4
    d = Path(target) if target else (ace_dir() or default_ace_dir())
    gpu = gpu_name()
    say(f"설치 위치: {d}")
    say(f"그래픽카드: {gpu or '(NVIDIA 그래픽카드를 찾지 못했어요. 느리거나 안 될 수 있어요)'}")
    d.parent.mkdir(parents=True, exist_ok=True)

    step(1, n, "ACE-Step 1.5 내려받기")
    if (d / "pyproject.toml").exists():
        say("  이미 있어요. 건너뜁니다.")
    elif shutil.which("git"):
        stream(["git", "clone", "--depth", "1", ACE_REPO, str(d)])
    else:
        import io
        import zipfile
        say("  git이 없어서 압축 파일로 받습니다.")
        req = urllib.request.Request(ACE_ZIP, headers={"User-Agent": "MotionStudio"})
        data = urllib.request.urlopen(req, timeout=300).read()
        tmp = d.parent / "_ace_zip"
        shutil.rmtree(tmp, ignore_errors=True)
        zipfile.ZipFile(io.BytesIO(data)).extractall(tmp)
        inner = next(tmp.iterdir())
        shutil.move(str(inner), str(d))
        shutil.rmtree(tmp, ignore_errors=True)

    step(2, n, "uv(파이썬 패키지 도구) 확인")
    uv = find_uv()
    if not uv:
        say("  uv가 없어서 설치합니다.")
        stream([sys.executable, "-m", "pip", "install", "--user", "--upgrade", "uv"])
        uv = find_uv()
        if not uv:
            raise SystemExit("uv를 설치하지 못했어요. PowerShell에서 'winget install astral-sh.uv' 후 다시 시도해 주세요.")
    say("  " + " ".join(uv))

    step(3, n, "필요한 패키지 설치 (PyTorch 포함, 몇 GB라 시간이 걸려요)")
    stream(uv + ["sync"], cwd=str(d))

    step(4, n, "음악 모델 내려받기 (약 10GB, 처음 한 번)")
    stream(uv + ["run", "acestep-download"], cwd=str(d))
    save_settings({"acestep_dir": str(d)})
    say("설치를 마쳤어요. 이제 'python tools/music.py gen <영상>' 이나 앱의 음악 만들기를 쓰면 돼요.")
    return d


def ace_start(wait=900):
    if ace_running():
        return
    d = ace_dir()
    if not ace_installed(d):
        raise SystemExit("무료 음악 엔진이 아직 없어요. 먼저 'python tools/music.py setup' 으로 설치해 주세요 (처음 한 번).")
    uv = find_uv()
    if not uv:
        raise SystemExit("uv를 찾을 수 없어요. 'python tools/music.py setup' 을 다시 실행해 주세요.")
    APPDATA.mkdir(parents=True, exist_ok=True)
    logf = open(APPDATA / "acestep.log", "ab")
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", ACESTEP_API_HOST="127.0.0.1",
               ACESTEP_API_PORT=str(ACE_PORT))
    p = subprocess.Popen(uv + ["run", "acestep-api", "--host", "127.0.0.1", "--port", str(ACE_PORT)], cwd=str(d),
                         stdout=logf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env,
                         creationflags=NO_WINDOW | NEW_GROUP | DETACHED, close_fds=True)
    (APPDATA / "acestep.pid").write_text(str(p.pid))
    say("음악 엔진을 켜는 중이에요. 처음엔 모델을 읽느라 1~2분 걸려요.")
    t0 = time.time()
    while time.time() - t0 < wait:
        if p.poll() is not None:
            tail = (APPDATA / "acestep.log").read_bytes()[-1500:].decode("utf-8", "replace")
            raise SystemExit("음악 엔진이 켜지다 멈췄어요.\n" + tail)
        if ace_running():
            say(f"음악 엔진 준비 완료 ({time.time() - t0:.0f}초)")
            return
        time.sleep(2)
    raise SystemExit("음악 엔진이 제시간에 켜지지 않았어요. out/_app/acestep.log 를 확인해 주세요.")


def ace_stop():
    pidf = APPDATA / "acestep.pid"
    if not pidf.exists():
        say("켜 둔 음악 엔진이 없어요.")
        return
    pid = pidf.read_text().strip()
    if IS_WIN:
        subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True, creationflags=NO_WINDOW)
    else:
        try:
            os.killpg(int(pid), 15)
        except Exception:
            try:
                os.kill(int(pid), 15)
            except Exception:
                pass
    pidf.unlink(missing_ok=True)
    say("음악 엔진을 껐어요.")


def ace_generate(prompt, bpm, seconds, seed=None, out=None):
    ace_start()
    req = {
        "prompt": prompt, "lyrics": "[Instrumental]", "instrumental": True,
        "bpm": int(round(bpm)), "time_signature": "4", "audio_duration": float(seconds),
        "batch_size": 1, "inference_steps": 8, "thinking": False,
        "use_cot_caption": False, "use_cot_language": False,
        "use_random_seed": seed is None, "seed": int(seed) if seed is not None else -1,
        "audio_format": "mp3",
    }
    r = http_json(ACE_URL + "/release_task", req, timeout=30)
    if r.get("code") not in (200, None) or not (r.get("data") or {}).get("task_id"):
        raise SystemExit(f"음악 엔진이 요청을 받지 않았어요: {r.get('error') or r}")
    tid = r["data"]["task_id"]
    t0, est, shown = time.time(), max(20.0, seconds * 1.2), -10.0
    while True:
        time.sleep(1.5)
        q = http_json(ACE_URL + "/query_result", {"task_id_list": [tid]}, timeout=30)
        item = (q.get("data") or [{}])[0]
        st = item.get("status")
        el = time.time() - t0
        if el - shown >= 6:
            shown = el
            say(f"단계 {min(95, 5 + int(el / est * 90))}/100 곡 만드는 중 ({el:.0f}초)")
        if st == 1:
            res = item.get("result")
            res = json.loads(res) if isinstance(res, str) else res
            first = res[0] if isinstance(res, list) else res
            url = first.get("file") or ""
            if url.startswith("/"):
                url = ACE_URL + url
            data = urllib.request.urlopen(url, timeout=120).read()
            Path(out).write_bytes(data)
            seeds = str(first.get("seed_value") or "")
            return {"seed": seeds.split(",")[0] if seeds else (seed if seed is not None else ""),
                    "metas": first.get("metas") or {}}
        if st == 2:
            raise SystemExit(f"곡을 만들지 못했어요: {item.get('result') or item}")
        if el > 1200:
            raise SystemExit("곡 만들기가 너무 오래 걸려요. out/_app/acestep.log 를 확인해 주세요.")


# ------------------------------------------------------------------ 구글 Lyria (유료)
def lyria_plan(seconds):
    return LYRIA["clip"] if seconds <= LYRIA["clip"]["max"] else LYRIA["song"]


def _find_audio(obj):
    """응답 JSON 어디에 있든 base64 오디오를 찾아냄."""
    best = None
    stack = [obj]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            mime = str(o.get("mime_type") or o.get("mimeType") or "")
            data = o.get("data")
            if isinstance(data, str) and len(data) > 2000 and ("audio" in mime or not mime):
                if best is None or len(data) > len(best[0]):
                    best = (data, mime)
            stack.extend(o.values())
        elif isinstance(o, list):
            stack.extend(o)
    return best


def _ts(x):
    x = int(round(x))
    return f"{x // 60}:{x % 60:02d}"


def track_seconds(dur, bpm):
    """만들 곡 길이. 첫 다운비트를 찾아 앞을 잘라 쓰므로 한 마디+2초 여유를 두되,
    영상이 28초 이하면 30초로 맞춤(Lyria Clip·Gemini 앱이 30초 곡을 만들고, 0.04달러짜리로 충분)."""
    want = max(10.0, math.ceil(dur + 4 * 60 / bpm + 2))
    if want > LYRIA["clip"]["max"] and dur <= LYRIA["clip"]["max"] - 2:
        want = float(LYRIA["clip"]["max"])
    return want


def hint_sections(v, seconds):
    """상황 프리셋이 정해 둔 음악 구간 (video.json musicHint.sections)."""
    sec = (v.get("musicHint") or {}).get("sections")
    if not sec:
        return None
    out = [(float(a), float(b), str(d)) for a, b, d in sec]
    a, b, d = out[-1]
    out[-1] = (a, max(b, seconds), d)
    return out


def song_sections(v, bpm=120):
    """필름 템플릿은 음악 구조를 장면에 맞춤: 확대가 드롭에 착지하고, 마지막 장면은 조용한 브레이크다운.
    [(시작초, 끝초, 설명)] 또는 None"""
    c = v.get("content") or {}
    beat = 60 / bpm
    if v.get("template") == "keynote":
        n = 40 if c.get("film") == "channel" else 54
        drop, brk0, brk1 = 12 * beat, (33 if n == 40 else 46) * beat, (38.5 if n == 40 else 52) * beat
        end = n * beat
        return [(0, drop, "light intro groove building up with risers"),
                (drop, brk0, "the drop: full beat and bass hit exactly at the start, energetic"),
                (brk0, brk1, "quiet breakdown, drums out, soft pads only"),
                (brk1, end + 3, "full beat returns on the downbeat and ends on a clean final hit")]
    return None


def gemini_prompt(prompt, bpm, seconds, app=False, sections=None):
    """Lyria 에 줄 영어 프롬프트. 박자를 숫자로 못 박는 모델이라 문장으로 분명히 적고, 시간 표시로 길이·구조를 잡습니다."""
    secs = int(math.ceil(seconds))
    end = _ts(secs)
    if sections:
        plan = " ".join(f"[{_ts(a)}-{_ts(min(b, secs))}] {d}." for a, b, d in sections if a < secs)
    else:
        plan = f"[0:00-{end}] keep the energy up the whole way, end on a clean final hit at {end}."
    body = (f"Instrumental background music for a short video ad. {prompt.strip().rstrip('.')}. "
            f"Tempo exactly {int(round(bpm))} BPM in 4/4 with a clear, steady pulse on every beat. "
            f"Start immediately on beat one, no slow fade-in. {plan} "
            f"Instrumental only, no vocals, no lyrics.")
    if app:
        body = f"Create an instrumental track, about {secs} seconds long. " + body
    return body


def lyria_generate(prompt, bpm, seconds, out, sections=None):
    key = gemini_key()
    if not key:
        raise SystemExit("Gemini API 키가 없어요. 'python tools/music.py key <키>' 로 저장하거나 앱 음악 칸에 넣어 주세요.")
    plan = lyria_plan(seconds)
    text = gemini_prompt(prompt, bpm, seconds, sections=sections)
    req = urllib.request.Request(LYRIA_URL, data=json.dumps({"model": plan["model"], "input": text}).encode("utf-8"),
                                 method="POST", headers={"Content-Type": "application/json", "x-goog-api-key": key})
    say(f"단계 10/100 구글 Gemini(Lyria)에 요청 ({plan['model']}, 약 {plan['usd']}달러). 30초~1분 걸려요")
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")[:600]
        if e.code in (401, 403):
            raise SystemExit("키가 거절됐어요. 결제가 연결된 Gemini API 키인지 확인해 주세요 (Lyria는 무료 등급이 없어요).\n" + msg)
        raise SystemExit(f"구글 Gemini 요청 실패 ({e.code}): {msg}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise SystemExit(f"구글 Gemini 에 연결하지 못했어요. 인터넷·회사 프록시·방화벽을 확인하고 다시 시도해 주세요. ({e})")
    found = _find_audio(resp)
    if not found:
        raise SystemExit("응답에서 오디오를 찾지 못했어요: " + json.dumps(resp, ensure_ascii=False)[:400])
    data = base64.b64decode(found[0])
    ext = ".wav" if (found[1] and "wav" in found[1]) or data[:4] == b"RIFF" else ".mp3"
    out = Path(out).with_suffix(ext)
    out.write_bytes(data)
    return {"model": plan["model"], "usd": plan["usd"], "file": out}


# ------------------------------------------------------------------ 박자 분석
def decode(path, sr=22050):
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True, creationflags=NO_WINDOW)
    if r.returncode != 0:
        raise SystemExit("음원을 읽지 못했어요: " + r.stderr.decode("utf-8", "replace")[:300])
    return np.frombuffer(r.stdout, dtype=np.float32).copy(), sr


def analyze(path, bpm_hint=None, sr=22050, hop=128):
    """BPM, 박 위치, 첫 다운비트(마디 첫 박)를 찾습니다. numpy 만 씁니다.

    1) 스펙트럼 변화량(onset)으로 소리가 '터지는' 순간을 구하고
    2) 자기상관으로 박 간격을, 빗살 맞추기로 박의 위상을 찾고
    3) 저음(킥·베이스) 힘과 화성 변화가 가장 큰 박을 마디 첫 박으로 봅니다.
    """
    import numpy as np
    y, sr = decode(path, sr)
    if len(y) < sr * 2:
        raise SystemExit("곡이 너무 짧아요 (2초 미만).")
    n_fft = 1024
    win = np.hanning(n_fft).astype(np.float32)
    nfr = 1 + (len(y) - n_fft) // hop
    spec = np.empty((nfr, n_fft // 2 + 1), dtype=np.float32)
    for s0 in range(0, nfr, 4096):          # 메모리를 아끼려고 나눠서 계산
        s1 = min(nfr, s0 + 4096)
        idx = np.arange(n_fft)[None, :] + hop * np.arange(s0, s1)[:, None]
        spec[s0:s1] = np.abs(np.fft.rfft(y[idx] * win, axis=1))
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    fps = sr / hop
    logs = np.log1p(100 * spec)
    flux = np.maximum(0, np.diff(logs, axis=0))
    onset = flux.sum(axis=1)

    def clean(x):
        k = int(fps * .4) | 1
        x = x - np.convolve(x, np.ones(k) / k, mode="same")
        x = np.maximum(0, x)
        return x / (x.max() + 1e-9)
    onset = clean(onset)

    # 음악이 실제로 시작하는 곳 (가장 큰 소리보다 30dB 작은 소리를 넘는 첫 프레임)
    rms = np.sqrt((spec[1:] ** 2).mean(axis=1))
    start_fr = int(np.argmax(rms > rms.max() * 10 ** (-30 / 20)))

    # 템포: FFT 자기상관 + 힌트(없으면 120) 근처를 선호
    n = len(onset)
    F = np.fft.rfft(onset, 2 * n)
    ac = np.fft.irfft(F * np.conj(F))[:n]
    lags = np.arange(n)
    bpms = 60 * fps / np.maximum(lags, 1)
    ok = (lags > 0) & (bpms >= 60) & (bpms <= 200)
    center = bpm_hint or 120
    prior = np.exp(-0.5 * (np.log2(bpms / center) / (0.25 if bpm_hint else 0.9)) ** 2)
    score = np.where(ok, ac * prior, 0)
    lag = int(np.argmax(score))
    a_, b_, c_ = score[lag - 1], score[lag], score[min(lag + 1, n - 1)]
    den = a_ - 2 * b_ + c_
    lagf = lag + (0.5 * (a_ - c_) / den if den else 0)
    bpm = 60 * fps / lagf
    if bpm_hint and abs(bpm - bpm_hint) / bpm_hint < 0.04:
        bpm = float(bpm_hint)   # 힌트와 거의 같으면 그 값으로 고정 (생성 곡은 박자가 일정)
    period = 60 * fps / bpm

    # 위상: 박 격자 위의 onset 합이 가장 큰 곳 (0.25프레임 단위)
    nb = max(1, int((n - start_fr) / period) - 1)
    k = np.arange(nb)
    best, phase = -1.0, 0.0
    for ph in np.arange(0, period, 0.25):
        pos = np.round(start_fr + ph + period * k).astype(int)
        pos = pos[pos < n - 1]
        s = onset[pos].sum() + 0.5 * (onset[pos - 1].sum() + onset[pos + 1].sum())
        if s > best:
            best, phase = s, ph
    first = start_fr + phase
    while first - period >= start_fr - 0.12 * fps:   # 맨 앞 박이 시작점 바로 앞에 걸친 경우
        first -= period
    first = max(first, -1 - n_fft * 0.85 / hop)   # 0초보다 앞서지 않게
    beats_fr = first + period * np.arange(int((n - first) / period))
    bpos = np.clip(np.round(beats_fr).astype(int), 0, n - 1)

    # 마디 첫 박 찾기
    #  - 저음 힘: 박 직후 0.1초 동안 30~160Hz 에너지(선형)
    #  - 화성 변화: 박 앞뒤 2박 동안의 음계(크로마) 분포 차이
    lowband = (freqs >= 30) & (freqs <= 160)
    lowE = (spec[:, lowband] ** 2).sum(axis=1)
    w = max(1, int(.1 * fps))
    lowb = np.array([lowE[p:p + w].mean() for p in bpos])
    band = (freqs >= 80) & (freqs <= 4000)
    pc = np.round(12 * np.log2(freqs[band] / 440.0)).astype(int) % 12
    chroma = np.zeros((spec.shape[0], 12), dtype=np.float32)
    for c in range(12):
        chroma[:, c] = spec[:, band][:, pc == c].sum(axis=1)
    half = int(period * 2)
    nov = []
    for p in bpos:
        a0, a1 = chroma[max(0, p - half):p].mean(axis=0) if p > 0 else None, chroma[p:p + half].mean(axis=0)
        if a0 is None or not np.isfinite(a0).all():
            nov.append(0.0)
            continue
        cs = float(a0 @ a1 / (np.linalg.norm(a0) * np.linalg.norm(a1) + 1e-9))
        nov.append(1 - cs)
    nov = np.array(nov)
    onb = onset[bpos]
    z = lambda x: (x - x.mean()) / (x.std() + 1e-9)
    comb = z(lowb) + z(nov) + 0.5 * z(onb)
    dscore = [comb[m::4].mean() if len(comb[m::4]) else -9 for m in range(4)]
    m = int(np.argmax(dscore))
    off = np.clip(np.round(beats_fr[:-1] + period / 2).astype(int), 0, n - 1)
    conf = float(onb.mean() / (onset[off].mean() + 1e-6)) if len(off) else 0.0
    # 프레임 번호 → 초. diff 로 한 프레임 밀린 것과, 소리가 창 끝에 걸리자마자 변화량이 튀는 만큼(재어 본 값 0.85창)을 보정
    to_t = lambda fr: float(((fr + 1) * hop + n_fft * 0.85) / sr)
    beats = [round(to_t(f), 4) for f in beats_fr]
    return {
        "bpm": round(float(bpm), 2), "beat": round(60 / bpm, 4),
        "firstBeat": beats[0] if beats else 0.0,
        "downbeat": beats[m] if len(beats) > m else 0.0,
        "musicStart": round(to_t(start_fr), 3),
        "confidence": round(conf, 2), "beats": beats,
        "duration": round(len(y) / sr, 3),
    }


# ------------------------------------------------------------------ 영상과 연결
def video_seconds(name):
    """영상 길이(초). 만들어 둔 master.mp4 가 있으면 그 길이, 없으면 빌드해서 잽니다."""
    vdir = ROOT / "videos" / name
    v = load_json(vdir / "video.json")
    for f in (v.get("formats") or []):
        m = ROOT / "out" / name / f / "master.mp4"
        if m.exists():
            r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(m)],
                               capture_output=True, text=True, creationflags=NO_WINDOW)
            try:
                return float(r.stdout.strip())
            except ValueError:
                pass
    import asyncio
    from build import build_video
    from playwright.async_api import async_playwright
    fmt = (v.get("formats") or ["square"])[0]
    build_video(name, [fmt])
    html = ROOT / "out" / name / fmt / f"{name}-{fmt}.html"

    async def go():
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pg = await b.new_page(viewport={"width": 640, "height": 640})
            await pg.add_init_script("window.__RENDER=true;")
            await pg.goto(html.as_uri())
            await pg.wait_for_function("window.__ready===true", timeout=60000)
            d = await pg.evaluate("window.__DURATION || 0")
            await b.close()
            return d
    return float(asyncio.run(go()))


def default_prompt(v, brand):
    m = v.get("music") or {}
    if m.get("prompt"):
        return m["prompt"]
    mood = m.get("mood") or (brand.get("music") or {}).get("mood")
    if mood in MOODS:
        return MOODS[mood]
    tpl = v.get("template") or ""
    if tpl in ("keynote", "uimorph", "showreel"):
        return MOODS["keynote"]
    return MOODS["minimal"]


def gen_for_video(name, engine="gemini", prompt=None, bpm=None, seconds=None, seed=None, yes=False, mood=None):
    vdir = ROOT / "videos" / name
    if not (vdir / "video.json").exists():
        raise SystemExit(f"영상 '{name}' 을 찾을 수 없어요.")
    v = load_json(vdir / "video.json")
    brand = load_json(ROOT / "brands" / v["brand"] / "brand.json")
    c = v.get("content") or {}
    hint = v.get("musicHint") or {}
    if mood and mood in MOODS and not prompt:
        prompt = MOODS[mood]
    if not prompt and not mood and hint:
        prompt = hint.get("prompt") or MOODS.get(hint.get("mood"))
    prompt = prompt or default_prompt(v, brand)
    bpm = float(bpm or c.get("bpm") or hint.get("bpm") or (v.get("music") or {}).get("bpm") or 120)
    step(1, 100, "영상 길이 재는 중")
    dur = float(seconds) if seconds else video_seconds(name)
    # 첫 다운비트를 찾아 앞을 잘라 쓰므로 앞뒤 여유를 둡니다
    want = track_seconds(dur, bpm)
    say(f"영상 {dur:.1f}초 → 곡 {want:.0f}초, {bpm:g} BPM")
    say(f"분위기: {prompt}")
    md = vdir / "music"
    stamp = time.strftime("%Y%m%d-%H%M%S")
    if engine in ("gemini", "lyria"):
        plan = lyria_plan(want)
        if not yes:
            say(f"COST {json.dumps({'usd': plan['usd'], 'model': plan['model']})}")
            raise SystemExit(f"구글 Gemini(Lyria)는 곡당 약 {plan['usd']}달러가 들어요. 괜찮으면 --yes 를 붙여 다시 실행해 주세요.")
    md.mkdir(exist_ok=True)
    if engine in ("gemini", "lyria"):
        r = lyria_generate(prompt, bpm, want, md / f"gemini-{stamp}.mp3", song_sections(v, bpm) or hint_sections(v, want))
        path, extra = r["file"], {"engine": "gemini", "model": r["model"], "usd": r["usd"]}
    else:
        path = md / f"ace-{stamp}.mp3"
        r = ace_generate(prompt, bpm, want, seed, path)
        extra = {"engine": "ace-step-1.5", "seed": r.get("seed")}
    say("단계 96/100 박자 분석")
    a = analyze(path, bpm)
    start = a["downbeat"]
    if start + dur > a["duration"] - 0.5:   # 곡이 모자라면 처음 박부터
        start = a["firstBeat"]
    v = load_json(vdir / "video.json")      # 그 사이 앱이 고쳤을 수 있으니 다시 읽음
    m = dict(v.get("music") or {})
    m.update({"file": str(path.relative_to(vdir)).replace("\\", "/"), "name": path.name, "prompt": prompt,
              "bpm": a["bpm"], "start": round(start, 3), "beat": a["beat"]}, **extra)
    m.setdefault("volume", 0.9)
    m.setdefault("fadeIn", 0.0)
    m.setdefault("fadeOut", 2.0)
    v["music"] = m
    (vdir / "video.json").write_text(json.dumps(v, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    res = {"file": m["file"], "bpm": a["bpm"], "start": m["start"], "confidence": a["confidence"], **extra}
    say(f"단계 100/100 완료: {m['file']} · {a['bpm']} BPM · 첫 다운비트 {start:.2f}초 (확신도 {a['confidence']})")
    say("RESULT " + json.dumps(res, ensure_ascii=False))
    return res


# ------------------------------------------------------------------ 명령
def opt(args, name, default=None):
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            return args[i + 1]
    return default


def status():
    d = ace_dir()
    k = gemini_key()
    return {
        "gemini": {"key": bool(k), "keyTail": k[-4:] if k else "", "prices": {kk: v["usd"] for kk, v in LYRIA.items()},
                   "clipMax": LYRIA["clip"]["max"]},
        "ace": {"installed": ace_installed(d), "running": ace_running() if d else False},
        "moods": MOODS,
    }


def prompt_for(name, mood=None, prompt=None, bpm=None, seconds=None):
    vdir = ROOT / "videos" / name
    v = load_json(vdir / "video.json")
    brand = load_json(ROOT / "brands" / v["brand"] / "brand.json")
    hint = v.get("musicHint") or {}
    if mood and mood in MOODS and not prompt:
        prompt = MOODS[mood]
    if not prompt and not mood and hint:
        prompt = hint.get("prompt") or MOODS.get(hint.get("mood"))
    prompt = prompt or default_prompt(v, brand)
    bpm = float(bpm or (v.get("content") or {}).get("bpm") or hint.get("bpm") or (v.get("music") or {}).get("bpm") or 120)
    dur = float(seconds) if seconds else video_seconds(name)
    want = track_seconds(dur, bpm)
    return gemini_prompt(prompt, bpm, want, app=True, sections=song_sections(v, bpm) or hint_sections(v, want))


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    cmd = args[0]
    if cmd == "status":
        print(json.dumps(status(), ensure_ascii=False, indent=2))
    elif cmd == "setup":
        ace_setup(opt(args, "--dir"))
    elif cmd == "stop":
        ace_stop()
    elif cmd == "key":
        if len(args) < 2:
            sys.exit("사용법: python tools/music.py key <Gemini API 키>  (지우려면 key -, 표준 입력으로 받으려면 key --stdin)")
        k = sys.stdin.readline().strip() if args[1] == "--stdin" else args[1].strip()
        if not k:
            sys.exit("키가 비어 있어요.")
        import accounts
        if k == "-":
            nm, _ = accounts.active("gemini")
            for it in accounts.public()["gemini"]["items"]:
                if it["name"] == nm:
                    accounts.remove("gemini", it["id"])
            say("지웠어요.")
        else:
            try:
                accounts.add("gemini", opt(args, "--name") or "", k)
            except ValueError as e:
                sys.exit(str(e))
            say("저장하고 이 키를 쓰도록 바꿨어요. (python tools/accounts.py 로 여러 키를 골라 쓸 수 있어요)")
    elif cmd == "beats":
        if len(args) < 2:
            sys.exit(__doc__)
        b = opt(args, "--bpm")
        a = analyze(args[1], float(b) if b else None)
        beats = a.pop("beats")
        a["beatsPreview"] = beats[:8]
        print(json.dumps(a, ensure_ascii=False, indent=2))
    elif cmd == "prompt":
        if len(args) < 2:
            sys.exit(__doc__)
        print(prompt_for(args[1], opt(args, "--mood"), opt(args, "--prompt"), opt(args, "--bpm"), opt(args, "--seconds")))
    elif cmd == "gen":
        if len(args) < 2:
            sys.exit(__doc__)
        seed = opt(args, "--seed")
        gen_for_video(args[1], engine=opt(args, "--engine", "gemini"), prompt=opt(args, "--prompt"),
                      bpm=opt(args, "--bpm"), seconds=opt(args, "--seconds"),
                      seed=int(seed) if seed not in (None, "") else None, yes="--yes" in args,
                      mood=opt(args, "--mood"))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
