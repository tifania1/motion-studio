"""모션 스튜디오 자동 업데이트.

앱이 켜질 때 GitHub 저장소(update.json 의 repo)에서 새 버전이 있는지 보고, 있으면 받아서 바꿉니다.

  1. 저장소를 사용자 폴더(~/.motion-studio/update/repo.git)로 받아 옴 (git, PC에 저장된 GitHub 로그인 사용)
  2. 새 버전을 임시 폴더에 풀어서 파이썬 파일이 깨지지 않았는지 먼저 봄
  3. 바뀔 파일을 백업(~/.motion-studio/update/backup) 한 뒤 덮어씀
  4. 앱을 불러 보고, 안 되면 백업으로 되돌리고 그 버전은 다시 받지 않음

프로그램 파일(app, engine, templates, tools …)만 바꿉니다. 내 영상(videos), 브랜드(brands), 결과(out),
API 키(~/.motion-studio)는 건드리지 않아요.

  python tools/update.py           새 버전 확인하고 있으면 적용
  python tools/update.py --check   확인만
  python tools/update.py --rollback  바로 전 버전으로 되돌리기

끄려면 ~/.motion-studio/update/off 파일을 만들거나 앱을 --no-update 로 켜요.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import py_compile
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONF = ROOT / "update.json"
VERSION_FILE = ROOT / ".version"
HOME = Path.home() / ".motion-studio" / "update"
REPO = HOME / "repo.git"
STAGE = HOME / "stage"
BACKUP = HOME / "backup"
MANIFEST = HOME / "manifest.json"
BAD = HOME / "bad.json"
LAST = HOME / "last.json"
LOG = HOME / "update.log"

# 업데이트가 손댈 수 있는 곳 (설치 파일과 같은 범위). 그 밖의 경로는 저장소에 있어도 무시.
DIRS = (".claude", "app", "docs", "engine", "fonts", "installer", "presets", "styles", "templates", "tools", "vendor")
FILES = ("CLAUDE.md", "AGENTS.md", "README.md", "StudioApp.cmd", "StudioApp_debug.cmd", "requirements.txt",
         "requirements-tools.txt", ".gitignore", "update.json")
NEVER = ("settings.local.json",)


def _log(msg, out=None):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    try:
        HOME.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    if out:
        out(msg)


def allowed(rel: str) -> bool:
    p = rel.replace("\\", "/")
    if not p or p.startswith("/") or ".." in p.split("/"):
        return False
    if p.split("/")[-1] in NEVER or "__pycache__" in p.split("/"):
        return False
    top = p.split("/")[0]
    if "/" not in p:
        return p in FILES
    if top == "styles" and p.split("/")[1].startswith(("zz-", "_")):
        return False
    return top in DIRS


def _git(*args, timeout=60, binary=False):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    r = subprocess.run(["git", "--git-dir", str(REPO), *args], capture_output=True, timeout=timeout, env=env,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode != 0:
        raise RuntimeError(f"git {args[0]}: " + r.stderr.decode("utf-8", "replace").strip()[-400:])
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def config():
    try:
        c = json.loads(CONF.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return c if c.get("repo") else None


def current():
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _jload(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _jsave(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def fetch(conf):
    """원격의 최신 커밋 해시."""
    if shutil.which("git") is None:
        raise RuntimeError("git 이 없어요")
    if not (REPO / "HEAD").exists():
        REPO.mkdir(parents=True, exist_ok=True)
        _git("init", "--bare", "-q")
    br = conf.get("branch", "main")
    _git("fetch", "-q", "--depth", "30", conf["repo"], f"+refs/heads/{br}:refs/heads/{br}", timeout=90)
    return _git("rev-parse", br).strip()


def blob_hash(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def tree(rev):
    """{경로: blob 해시} (업데이트 범위 안 파일만)."""
    out = {}
    for line in _git("ls-tree", "-r", "-z", rev).split("\0"):
        if not line:
            continue
        meta, path = line.split("\t", 1)
        mode, kind, sha = meta.split()
        if kind == "blob" and allowed(path):
            out[path] = sha
    return out


def notes(old, new):
    if not old:
        return []
    try:
        _git("cat-file", "-e", old + "^{commit}")
        txt = _git("log", "--format=%s", f"{old}..{new}", "-n", "15")
    except RuntimeError:
        return []
    return [s for s in txt.splitlines() if s.strip()]


def stage(rev, files):
    if STAGE.exists():
        shutil.rmtree(STAGE, ignore_errors=True)
    STAGE.mkdir(parents=True)
    data = _git("archive", "--format=tar", rev, timeout=120, binary=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as t:
        for m in t.getmembers():
            if m.isfile() and m.name in files:
                dst = STAGE / m.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(t.extractfile(m).read())
    missing = [f for f in files if not (STAGE / f).exists()]
    if missing:
        raise RuntimeError(f"받은 파일이 빠졌어요: {missing[:3]}")


def precheck():
    """받은 파이썬 파일이 문법상 멀쩡한지, 핵심 파일이 있는지."""
    for need in ("tools/app.py", "app/app.js", "engine/studio.js", "requirements.txt"):
        if not (STAGE / need).exists():
            raise RuntimeError(f"{need} 이 없는 버전이에요")
    for p in STAGE.rglob("*.py"):
        try:
            py_compile.compile(str(p), cfile=str(HOME / "pyc.tmp"), doraise=True)
        except py_compile.PyCompileError as e:
            raise RuntimeError(f"{p.relative_to(STAGE)} 문법 오류: {e.msg[-200:]}")
    for p in list((STAGE / "templates").rglob("*.json")) + [STAGE / "update.json"]:
        if p.exists():
            try:
                json.loads(p.read_text(encoding="utf-8-sig"))
            except ValueError as e:
                raise RuntimeError(f"{p.relative_to(STAGE)} JSON 오류: {e}")


def app_ok(timeout=90):
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    code = "import sys; sys.path.insert(0, 'tools'); import app; print('app ok')"
    try:
        r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, timeout=timeout, env=env,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return False, "앱 불러오기가 너무 오래 걸림"
    out = (r.stdout + r.stderr).decode("utf-8", "replace")
    return ("app ok" in out and r.returncode == 0), out.strip()[-600:]


def _copy(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".upd-tmp")
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)


def backup(paths, old, new):
    if BACKUP.exists():
        shutil.rmtree(BACKUP, ignore_errors=True)
    (BACKUP / "files").mkdir(parents=True)
    had, local_edits = [], []
    old_tree = _jload(MANIFEST, {}).get("files", {})
    for rel in sorted(paths):
        p = ROOT / rel
        if p.is_file():
            _copy(p, BACKUP / "files" / rel)
            had.append(rel)
            if rel in old_tree and blob_hash(p.read_bytes()) != old_tree[rel]:
                local_edits.append(rel)
    _jsave(BACKUP / "info.json", {"from": old, "to": new, "had": had, "touched": sorted(paths),
                                  "at": time.strftime("%Y-%m-%d %H:%M:%S")})
    return local_edits


def restore(out=None):
    info = _jload(BACKUP / "info.json", None)
    if not info:
        raise RuntimeError("되돌릴 백업이 없어요")
    had = set(info["had"])
    for rel in info["touched"]:
        p = ROOT / rel
        if rel in had:
            _copy(BACKUP / "files" / rel, p)
        elif p.exists():
            p.unlink()
    if info.get("from"):
        VERSION_FILE.write_text(info["from"], encoding="utf-8")
    elif VERSION_FILE.exists():
        VERSION_FILE.unlink()
    m = _jload(MANIFEST, {})
    if m.get("prev"):
        _jsave(MANIFEST, m["prev"])
    _log(f"되돌림: {info['to'][:8]} → {(info.get('from') or '처음 설치본')[:8]}", out)
    return info


def apply(new, out=None):
    old = current()
    files = tree(new)
    stage(new, files)
    precheck()
    prev = _jload(MANIFEST, {})
    old_files = prev.get("files", {})

    def local(f):
        p = ROOT / f
        return blob_hash(p.read_bytes()) if p.is_file() else None

    # PC에서 고친 파일: 이번 버전에서 그 파일이 안 바뀌었으면 PC 쪽을 그대로 둠.
    # 같은 파일이 양쪽에서 바뀌었으면 새 버전으로 바꾸고 PC 쪽은 백업에 남김(알림에 표시).
    changed, kept = [], []
    for f, sha in files.items():
        cur = local(f)
        if cur == sha:
            continue
        if old_files and f in old_files and old_files[f] == sha and cur is not None:
            kept.append(f)
            continue
        changed.append(f)
    gone = [f for f in old_files if f not in files and allowed(f) and local(f) in (old_files[f], None)]
    req_before = (ROOT / "requirements.txt").read_bytes() if (ROOT / "requirements.txt").exists() else b""
    local_edits = backup(set(changed) | set(gone), old, new)
    for f in changed:
        _copy(STAGE / f, ROOT / f)
    for f in gone:
        try:
            (ROOT / f).unlink()
        except OSError:
            pass
    VERSION_FILE.write_text(new, encoding="utf-8")
    _jsave(MANIFEST, {"version": new, "files": files, "prev": {k: v for k, v in prev.items() if k != "prev"}})
    ok, why = app_ok()
    if not ok:
        restore()
        bad = _jload(BAD, [])
        _jsave(BAD, (bad + [new])[-20:])
        raise RuntimeError("새 버전에서 앱이 안 켜져서 되돌렸어요: " + why[-300:])
    shutil.rmtree(STAGE, ignore_errors=True)
    req_after = (ROOT / "requirements.txt").read_bytes()
    pip_note = ""
    if req_after != req_before:
        try:
            r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")],
                               capture_output=True, timeout=600,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            pip_note = "필요한 부품도 설치했어요" if r.returncode == 0 else "필요한 부품 설치가 실패했어요 (requirements.txt)"
        except (OSError, subprocess.TimeoutExpired):
            pip_note = "필요한 부품 설치가 실패했어요 (requirements.txt)"
    info = {"from": old, "to": new, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "notes": notes(old, new),
            "changed": len(changed), "removed": len(gone), "local_edits": local_edits, "kept": kept, "pip": pip_note,
            "seen": False}
    _jsave(LAST, info)
    _log(f"업데이트: {(old or '처음')[:8]} → {new[:8]} (바뀐 파일 {len(changed)}개, 지운 파일 {len(gone)}개)", out)
    return info


def run(out=None, check_only=False):
    """새 버전이 있으면 적용. 결과 dict 또는 None(할 일 없음/꺼짐/연결 안 됨)."""
    conf = config()
    if not conf or (HOME / "off").exists():
        return None
    try:
        new = fetch(conf)
    except Exception as e:  # noqa: BLE001  인터넷이 없거나 로그인이 없으면 조용히 넘어감
        _log(f"새 버전 확인 못 함: {e}", out)
        return None
    if new == current():
        return {"updated": False, "version": new}
    if new in _jload(BAD, []):
        _log(f"{new[:8]} 은 전에 실패한 버전이라 건너뜀", out)
        return {"updated": False, "version": current(), "skipped": new}
    if check_only:
        return {"updated": False, "available": new, "version": current()}
    try:
        info = apply(new, out)
    except Exception as e:  # noqa: BLE001
        _log(f"업데이트 실패: {e}", out)
        _jsave(BAD, (_jload(BAD, []) + [new])[-20:])   # 같은 버전을 켤 때마다 다시 시도하지 않게
        _jsave(LAST, {"error": str(e)[-400:], "to": new, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "seen": False})
        return {"updated": False, "error": str(e)}
    return dict(info, updated=True)


def take_notice():
    """앱 화면에 한 번 보여 줄 업데이트 알림."""
    info = _jload(LAST, None)
    if not info or info.get("seen"):
        return None
    info["seen"] = True
    _jsave(LAST, info)
    return info


if __name__ == "__main__":
    if "--rollback" in sys.argv:
        restore(print)
    else:
        res = run(print, check_only="--check" in sys.argv)
        print(json.dumps(res, ensure_ascii=False, indent=1) if res else "업데이트 꺼짐 또는 확인 못 함")
