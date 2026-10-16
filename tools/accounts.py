"""AI API 계정(키) 여러 개를 저장해 두고 골라 쓰기.

    python tools/accounts.py                      # 저장된 계정 목록 (키는 끝 4자리만)
    python tools/accounts.py add claude "회사 키" --stdin   # 키를 표준 입력으로 받아 추가하고 바로 사용
    python tools/accounts.py use claude <id>      # 사용할 계정 바꾸기
    python tools/accounts.py remove claude <id>
    python tools/accounts.py test claude [<id>]   # 키가 살아 있는지 확인 (요금이 들지 않는 목록 조회)
    python tools/accounts.py engine api|code      # Claude 를 API 키로 쓸지, Claude Code 로그인(구독)으로 쓸지

키는 이 PC 사용자 폴더 .motion-studio/accounts.json 에만 저장해요(프로젝트 폴더에는 넣지 않음).
Windows 에서는 키를 이 PC·이 사용자만 풀 수 있게 암호화(DPAPI)해 둬요.
"""
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

IS_WIN = os.name == "nt"
HOME_DIR = Path.home() / ".motion-studio"
FILE = HOME_DIR / "accounts.json"
SETTINGS = HOME_DIR / "settings.json"

PROVIDERS = {
    "claude": {"label": "Claude API", "pattern": r"sk-ant-[A-Za-z0-9_\-]{20,200}", "hint": "sk-ant- 로 시작하는 키"},
    "gemini": {"label": "Gemini API", "pattern": r"[A-Za-z0-9_\-]{20,80}", "hint": "AIza 로 시작하는 키"},
}


# ------------------------------------------------------------------ 키 보관 (Windows: DPAPI)
def _dpapi(data, protect):
    import ctypes
    from ctypes import wintypes

    class BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    src, out = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), BLOB()
    fn = ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
    if protect:
        ok = fn(ctypes.byref(src), "motion-studio", None, None, None, 0x1, ctypes.byref(out))
    else:
        ok = fn(ctypes.byref(src), None, None, None, None, 0x1, ctypes.byref(out))
    if not ok:
        raise OSError("키를 풀지 못했어요 (다른 PC나 다른 사용자 계정에서 저장한 키일 수 있어요)")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def _seal(key):
    if IS_WIN:
        try:
            return "dpapi:" + base64.b64encode(_dpapi(key.encode("utf-8"), True)).decode("ascii")
        except Exception:  # noqa: BLE001  암호화가 안 되는 환경이면 그대로 (사용자 폴더에만 있음)
            pass
    return "plain:" + key


def _open(sealed):
    if not sealed:
        return ""
    if sealed.startswith("dpapi:"):
        try:
            return _dpapi(base64.b64decode(sealed[6:]), False).decode("utf-8")
        except Exception:  # noqa: BLE001
            return ""
    return sealed[6:] if sealed.startswith("plain:") else sealed


# ------------------------------------------------------------------ 저장 파일
def _settings():
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return {}


def _load():
    try:
        data = json.loads(FILE.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        data = {}
    changed = False
    for p in PROVIDERS:
        if not isinstance(data.get(p), dict):
            data[p] = {"active": None, "items": []}
            changed = True
    # 예전 방식(settings.json 의 gemini_api_key 한 개)을 계정 하나로 옮겨 옴
    old = _settings().get("gemini_api_key")
    if old and not data["gemini"]["items"]:
        it = {"id": uuid.uuid4().hex[:8], "name": "기본 키", "key": _seal(old), "tail": old[-4:], "added": time.strftime("%Y-%m-%d")}
        data["gemini"]["items"].append(it)
        data["gemini"]["active"] = it["id"]
        changed = True
    if changed:
        _save(data)
    return data


def _save(data):
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, FILE)
    try:
        os.chmod(FILE, 0o600)
    except OSError:
        pass


def _provider(p):
    if p not in PROVIDERS:
        raise ValueError("모르는 종류예요: " + str(p))
    return p


# ------------------------------------------------------------------ 바깥에서 쓰는 함수
def public():
    """앱 화면용 목록. 키 자체는 빼고 끝 4자리만."""
    data = _load()
    out = {"engine": engine()}
    for p, info in PROVIDERS.items():
        d = data[p]
        out[p] = {"label": info["label"], "hint": info["hint"], "active": d.get("active"),
                  "items": [{"id": it["id"], "name": it.get("name") or "이름 없음", "tail": it.get("tail", ""), "added": it.get("added", ""),
                             "checked": it.get("checked", ""), "ok": it.get("ok")} for it in d["items"]]}
    out["envClaude"] = bool(os.environ.get("ANTHROPIC_API_KEY"))
    return out


def add(p, name, key, activate=True):
    _provider(p)
    key = (key or "").strip()
    if not re.fullmatch(PROVIDERS[p]["pattern"], key):
        raise ValueError(f"키 모양이 맞지 않아요. {PROVIDERS[p]['hint']}를 그대로 붙여 넣어 주세요")
    data = _load()
    for it in data[p]["items"]:
        if _open(it["key"]) == key:
            raise ValueError(f"이미 '{it.get('name')}' 이름으로 저장된 키예요")
    name = (name or "").strip()[:30] or f"{PROVIDERS[p]['label']} {len(data[p]['items']) + 1}"
    it = {"id": uuid.uuid4().hex[:8], "name": name, "key": _seal(key), "tail": key[-4:], "added": time.strftime("%Y-%m-%d")}
    data[p]["items"].append(it)
    if activate or not data[p]["active"]:
        data[p]["active"] = it["id"]
    _save(data)
    return it["id"]


def remove(p, aid):
    _provider(p)
    data = _load()
    items = [it for it in data[p]["items"] if it["id"] != aid]
    if len(items) == len(data[p]["items"]):
        raise ValueError("그 계정을 찾지 못했어요")
    data[p]["items"] = items
    if data[p]["active"] == aid:
        data[p]["active"] = items[0]["id"] if items else None
    _save(data)
    if p == "gemini" and not items:   # 예전 방식 키가 남아 있으면 다시 살아나지 않게 같이 지움
        _drop_old_gemini()


def _drop_old_gemini():
    s = _settings()
    if "gemini_api_key" in s:
        s.pop("gemini_api_key")
        SETTINGS.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


def rename(p, aid, name):
    _provider(p)
    data = _load()
    for it in data[p]["items"]:
        if it["id"] == aid:
            it["name"] = (name or "").strip()[:30] or it["name"]
            _save(data)
            return
    raise ValueError("그 계정을 찾지 못했어요")


def use(p, aid):
    _provider(p)
    data = _load()
    if not any(it["id"] == aid for it in data[p]["items"]):
        raise ValueError("그 계정을 찾지 못했어요")
    data[p]["active"] = aid
    _save(data)


def active(p):
    """(이름, 키) — 없으면 (None, '')"""
    data = _load()
    d = data[_provider(p)]
    for it in d["items"]:
        if it["id"] == d.get("active"):
            return it.get("name"), _open(it["key"])
    return None, ""


def key_for(p, aid=None):
    if not aid:
        return active(p)[1]
    for it in _load()[_provider(p)]["items"]:
        if it["id"] == aid:
            return _open(it["key"])
    return ""


def engine():
    """Claude 를 무엇으로 부를지: 'api' (API 키) 또는 'code' (이 PC의 Claude Code 로그인)."""
    return "api" if _settings().get("claude_engine") == "api" else "code"


def set_engine(e):
    s = _settings()
    if e == "api":
        s["claude_engine"] = "api"
    else:
        s.pop("claude_engine", None)
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


def test(p, aid=None):
    """요금이 들지 않는 모델 목록 조회로 키가 살아 있는지 확인. (ok, 설명)"""
    key = key_for(p, aid)
    if not key:
        return False, "저장된 키가 없어요"
    if p == "claude":
        req = urllib.request.Request("https://api.anthropic.com/v1/models?limit=5",
                                     headers={"x-api-key": key, "anthropic-version": "2023-06-01"})
    else:
        req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models?pageSize=5",
                                     headers={"x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            json.loads(r.read().decode("utf-8"))
        ok, msg = True, "키가 살아 있어요"
    except urllib.error.HTTPError as e:
        ok = False
        msg = {401: "키가 맞지 않거나 지워진 키예요", 403: "이 키로는 쓸 수 없어요 (권한·결제를 확인해 주세요)",
               400: "키가 맞지 않아요"}.get(e.code, f"서버가 거절했어요 (HTTP {e.code})")
    except Exception as e:  # noqa: BLE001
        ok, msg = False, f"서버에 연결하지 못했어요 ({type(e).__name__})"
    data = _load()
    target = aid or data[p].get("active")
    for it in data[p]["items"]:
        if it["id"] == target:
            it["checked"], it["ok"] = time.strftime("%Y-%m-%d %H:%M"), ok
    _save(data)
    return ok, msg


def main():
    a = [x for x in sys.argv[1:]]
    if not a:
        print(json.dumps(public(), ensure_ascii=False, indent=2))
        return
    cmd = a[0]
    try:
        if cmd == "add" and len(a) >= 3:
            key = sys.stdin.readline().strip() if "--stdin" in a else (a[3] if len(a) > 3 else "")
            print("추가했어요:", add(a[1], a[2], key))
        elif cmd == "use" and len(a) == 3:
            use(a[1], a[2]); print("바꿨어요")
        elif cmd == "remove" and len(a) == 3:
            remove(a[1], a[2]); print("지웠어요")
        elif cmd == "test" and len(a) >= 2:
            ok, msg = test(a[1], a[2] if len(a) > 2 else None); print(("✓ " if ok else "✗ ") + msg)
        elif cmd == "engine" and len(a) == 2 and a[1] in ("api", "code"):
            set_engine(a[1]); print("Claude 연결:", engine())
        else:
            sys.exit(__doc__)
    except ValueError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
