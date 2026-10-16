"""Claude API 로 도는 작업 도우미 (앱의 'API 모드'에서 Claude Code 창 대신 씀).

Claude 가 이 폴더의 파일을 읽고(read_file·list_files), 고치고(write_file·edit_file), 스튜디오 도구를 돌리고(run_tool:
check·build·render sheet 등), 장면 모음 이미지를 직접 보며(view_image) 영상을 짜거나 다듬어요.
대화는 out/_app/agent/<세션>.json 에 남아서 '이어서 부탁하기'로 계속할 수 있어요.

    python tools/agent.py "<부탁할 말>" [--video <영상>] [--session <id>]   # 명령 창에서 바로 (API 키는 AI 계정에서 고른 것)
"""
import base64
import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT  # noqa: E402

SESS_DIR = ROOT / "out" / "_app" / "agent"
API_URL = os.environ.get("MOTION_STUDIO_ANTHROPIC_URL") or "https://api.anthropic.com/v1/messages"
MODELS = {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5"}
PRICES = {"claude-opus-5-5": (4, 20), "claude-sonnet-5-5": (2, 10), "claude-haiku-5-5": (.1, .5)}   # 100만 토큰당 달러 (입력, 출력)
NO_WRITE = ("tools/", "app/", "installer/", "vendor/", "fonts/", "out/", "dist/", ".claude/", ".git/")
RUN_TOOLS = {"check", "build", "render", "qa", "styles", "presets", "photo", "list", "finalize", "music"}
MAX_TURNS = 60


class Stop(Exception):
    pass


# ------------------------------------------------------------------ 도구
TOOLS = [
    {"name": "list_files", "description": "폴더 안 파일·폴더 이름 (모션 스튜디오 폴더 기준 상대 경로). pattern 을 주면 그 glob 으로 찾음(예: 'videos/*/video.json').",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "pattern": {"type": "string"}}}},
    {"name": "read_file", "description": "텍스트 파일 읽기. 긴 파일은 offset(시작 줄, 1부터)·limit(줄 수)로 나눠 읽기. 줄 번호가 붙어 나옴.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "offset": {"type": "integer"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "파일 전체를 새로 씀(없으면 만듦). tools/ app/ installer/ vendor/ fonts/ out/ 은 쓸 수 없음. 고칠 곳이 일부면 edit_file 을 쓰기.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "파일에서 old 문자열(파일 안에 정확히 한 번 있어야 함)을 new 로 바꿈.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}}, "required": ["path", "old", "new"]}},
    {"name": "run_tool", "description": "스튜디오 명령 실행: python tools/<tool>.py <args...>. tool 은 check, build, render, qa, styles, presets, photo, list, finalize, music 중 하나. "
                                       "예: {tool:'build', args:['내영상']}, {tool:'render', args:['내영상','all','sheet']}, {tool:'render', args:['내영상','tall','sheet','--safe']}. "
                                       "music gen 은 유료라 쓰지 않음. 출력 끝부분과 종료 코드를 돌려줌.",
     "input_schema": {"type": "object", "properties": {"tool": {"type": "string"}, "args": {"type": "array", "items": {"type": "string"}}}, "required": ["tool"]}},
    {"name": "view_image", "description": "PNG·JPG 이미지를 직접 봄(예: render 가 만든 out/<영상>/<형식>/sheet.png). 만든 결과는 꼭 열어 보고 확인하기.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
]


def _safe(path, write=False):
    p = (ROOT / str(path or ".").replace("\\", "/").lstrip("/")).resolve()
    if p != ROOT.resolve() and ROOT.resolve() not in p.parents:
        raise ValueError("모션 스튜디오 폴더 밖은 다룰 수 없어요")
    rel = p.relative_to(ROOT.resolve()).as_posix()
    if write and (rel + "/").startswith(NO_WRITE):
        raise ValueError(f"{rel} 은 이 도우미가 고칠 수 없는 곳이에요(앱·도구·설치 파일). 필요하면 사용자에게 알려 주세요")
    return p, rel


def tool_call(name, inp, log, cancelled):
    """(결과 content, 짧은 기록) — 결과는 문자열이나 이미지 블록 목록"""
    if name == "list_files":
        p, rel = _safe(inp.get("path") or ".")
        if inp.get("pattern"):
            hits = sorted(x.relative_to(ROOT).as_posix() for x in ROOT.glob(inp["pattern"]) if "out/" not in x.relative_to(ROOT).as_posix()[:4])[:300]
            return "\n".join(hits) or "(없음)", f"찾기 {inp['pattern']}"
        if not p.is_dir():
            return f"폴더가 아니에요: {rel}", f"목록 {rel}"
        items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))[:400]
        return "\n".join((x.name + ("/" if x.is_dir() else f"  ({x.stat().st_size:,} B)")) for x in items) or "(비어 있음)", f"목록 {rel or '.'}"
    if name == "read_file":
        p, rel = _safe(inp["path"])
        if not p.is_file():
            return f"파일이 없어요: {rel}", f"읽기 {rel} (없음)"
        lines = p.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        off = max(1, int(inp.get("offset") or 1))
        lim = int(inp.get("limit") or 0) or 1500
        chunk = lines[off - 1: off - 1 + lim]
        body = "\n".join(f"{i:>5}\t{s[:2000]}" for i, s in enumerate(chunk, off))
        more = f"\n… ({len(lines)}줄 중 {off}~{off + len(chunk) - 1}줄. 나머지는 offset 으로)" if off - 1 + lim < len(lines) else ""
        return (body or "(빈 파일)") + more, f"읽기 {rel}"
    if name == "write_file":
        p, rel = _safe(inp["path"], write=True)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(inp.get("content") or "", encoding="utf-8")
        return f"썼어요: {rel} ({len(inp.get('content') or ''):,}자)", f"쓰기 {rel}"
    if name == "edit_file":
        p, rel = _safe(inp["path"], write=True)
        if not p.is_file():
            return f"파일이 없어요: {rel}", f"고치기 {rel} (없음)"
        t = p.read_text(encoding="utf-8-sig")
        n = t.count(inp["old"])
        if n != 1:
            return f"old 문자열이 {n}번 나와요. 정확히 한 번 나오게 앞뒤를 더 넣어 주세요.", f"고치기 {rel} (실패)"
        p.write_text(t.replace(inp["old"], inp["new"]), encoding="utf-8")
        return f"고쳤어요: {rel}", f"고치기 {rel}"
    if name == "run_tool":
        tool = str(inp.get("tool") or "").removesuffix(".py")
        args = [str(a) for a in (inp.get("args") or [])]
        if tool not in RUN_TOOLS:
            return f"실행할 수 없는 도구예요: {tool}", f"실행 거절 {tool}"
        if tool == "music" and args[:1] == ["gen"]:
            return "음악 생성은 유료라 이 도우미가 돌리지 않아요. 사용자에게 앱 음악 탭을 안내하세요.", "music gen 거절"
        exe = Path(sys.executable)
        if exe.name.lower() == "pythonw.exe":
            exe = exe.with_name("python.exe")
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        log(f"실행: {tool} {' '.join(args)}")
        kw = {"creationflags": 0x08000000} if os.name == "nt" else {}
        proc = subprocess.Popen([str(exe), str(ROOT / "tools" / f"{tool}.py")] + args, cwd=str(ROOT), env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **kw)
        out, t0 = [], time.time()
        for line in proc.stdout:
            out.append(line.rstrip())
            if cancelled():
                proc.kill()
                raise Stop("취소했어요")
            if time.time() - t0 > 1800:
                proc.kill()
                out.append("(30분이 넘어 멈췄어요)")
                break
        proc.wait()
        text = "\n".join(x for x in out if "NOT subset" not in x)
        return f"종료 코드 {proc.returncode}\n" + text[-6000:], f"{tool} {' '.join(args)} → {proc.returncode}"
    if name == "view_image":
        p, rel = _safe(inp["path"])
        if not p.is_file():
            return f"이미지가 없어요: {rel}", f"보기 {rel} (없음)"
        from PIL import Image
        im = Image.open(p).convert("RGB")
        im.thumbnail((1500, 1500))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=82)
        return [{"type": "text", "text": f"{rel} ({im.width}×{im.height})"},
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}}], f"보기 {rel}"
    return f"모르는 도구예요: {name}", name


# ------------------------------------------------------------------ 세션
def system_prompt(video=None):
    claude_md = (ROOT / "CLAUDE.md").read_text(encoding="utf-8-sig") if (ROOT / "CLAUDE.md").exists() else ""
    cur = f"- 지금 다루는 영상: videos/{video}" if video else ""
    return f"""당신은 사용자의 모션 스튜디오 앱 안에서 Claude API 로 일하는 작업 도우미예요. 평소 Claude Code 가 하던 일(영상 연출 짜기·다듬기, 문구·사진·스타일 적용, 검수)을
도구로 해요. 사용자는 한국어를 쓰는 유니티 개발자이고, 대답은 사람이 말하듯 자연스러운 한국어로 짧게 해요("~가 아닙니다, ~입니다" 같은 대조 구문은 쓰지 않아요).

일하는 방식
- 파일 경로는 모션 스튜디오 폴더 기준 상대 경로예요(예: videos/<영상>/video.json). 먼저 필요한 파일을 읽고 시작해요.
- 고친 뒤에는 꼭 run_tool 로 check·build 하고 render <영상> all sheet (9:16 은 tall sheet --safe 도) 를 만든 다음 view_image 로 sheet.png 를 직접 보고 고쳐요.
  sheet 경로는 out/<영상>/<형식>/sheet.png 예요. MP4(render ... video)는 사용자가 원할 때만(시간이 오래 걸려요).
- 대화 중간에 사용자에게 바로 물어볼 수는 없어요. 사실 정보(가격·날짜·이름 등)가 비었거나 결정이 필요하면, 할 수 있는 데까지 하고
  마지막 답에 물어볼 것을 짧게 적고 멈춰요. 사용자가 '이어서 부탁하기'로 답해 줘요. 지어내지 않아요.
- 앱(app/), 도구(tools/), 설치 파일(installer/)은 고칠 수 없어요. 그런 수정이 필요하면 무엇을 바꿔야 하는지 알려 줘요.
- 비용이 드는 생성(music gen, Artlist, Kling)은 하지 않아요. 요금은 토큰으로 나가니 같은 큰 파일을 여러 번 통째로 읽지 말고, 고칠 땐 edit_file 을 써요.
- 마지막 답에는 무엇을 했고, 무엇을 확인했고, 남은 확인 사항이 무엇인지 짧게 적어요.
{cur}

아래는 이 폴더의 CLAUDE.md (규칙 전체)예요.

{claude_md}"""


def new_session(video=None, title=""):
    SESS_DIR.mkdir(parents=True, exist_ok=True)
    s = {"id": time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4], "video": video, "title": title[:60], "created": time.strftime("%Y-%m-%d %H:%M"),
         "messages": [], "usd": 0.0, "tokens": {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0}, "steps": []}
    save(s)
    return s


def load(sid):
    p = SESS_DIR / f"{Path(str(sid)).name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save(s):
    SESS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SESS_DIR / f"{s['id']}.tmp"
    tmp.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, SESS_DIR / f"{s['id']}.json")


def latest(video=None):
    if not SESS_DIR.exists():
        return None
    best = None
    for f in sorted(SESS_DIR.glob("*.json"), reverse=True):
        try:
            s = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if s.get("video") == video:
            best = s
            break
    return best


def transcript(s):
    """화면용: 사용자 말·Claude 답(글만)·도구 기록"""
    out = []
    for m in s.get("messages", []):
        c = m["content"]
        if isinstance(c, str):
            out.append({"role": m["role"], "text": c})
            continue
        texts = [b.get("text", "") for b in c if b.get("type") == "text" and not b.get("_hidden")]
        if m["role"] == "assistant":
            tools = [b.get("_label") or b.get("name") for b in c if b.get("type") == "tool_use"]
            if any(t.strip() for t in texts):
                out.append({"role": "assistant", "text": "\n".join(t for t in texts if t.strip())})
            if tools:
                out.append({"role": "tool", "text": " · ".join(tools)})
        elif texts:
            out.append({"role": "user", "text": "\n".join(texts)})
    return out


# ------------------------------------------------------------------ API 한 번 (스트리밍)
def _stream(body, key, on_text):
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode("utf-8"), method="POST", headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json", "accept": "text/event-stream"})
    resp = urllib.request.urlopen(req, timeout=900)
    blocks, usage, stop = {}, {}, None
    with resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            try:
                ev = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            t = ev.get("type")
            if t == "message_start":
                usage.update((ev.get("message") or {}).get("usage") or {})
            elif t == "content_block_start":
                b = dict(ev.get("content_block") or {})
                if b.get("type") == "tool_use":
                    b["_json"] = ""
                blocks[ev["index"]] = b
            elif t == "content_block_delta":
                b, d = blocks.get(ev["index"]), ev.get("delta") or {}
                if b is None:
                    continue
                dt = d.get("type")
                if dt == "text_delta":
                    b["text"] = b.get("text", "") + d.get("text", "")
                    on_text(len(b["text"]))
                elif dt == "thinking_delta":
                    b["thinking"] = b.get("thinking", "") + d.get("thinking", "")
                elif dt == "signature_delta":
                    b["signature"] = d.get("signature", "")
                elif dt == "input_json_delta":
                    b["_json"] += d.get("partial_json", "")
            elif t == "message_delta":
                stop = (ev.get("delta") or {}).get("stop_reason") or stop
                usage.update(ev.get("usage") or {})
            elif t == "error":
                err = ev.get("error") or {}
                raise RuntimeError(f"{err.get('type', '')}: {err.get('message', '')}")
    content = []
    for i in sorted(blocks):
        b = blocks[i]
        if b.get("type") == "tool_use":
            raw = b.pop("_json", "")
            try:
                b["input"] = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                b["input"] = {"_bad_json": raw[:200]}
        content.append(b)
    return content, usage, stop


def _with_cache(messages):
    """마지막 메시지 끝에 캐시 표시 하나 (앞부분을 다시 읽을 때 90% 싸게)"""
    msgs = json.loads(json.dumps(messages))
    for m in msgs:   # 화면용 표시는 API 로 보내지 않음
        if isinstance(m["content"], list):
            for b in m["content"]:
                for k in [k for k in b if k.startswith("_")]:
                    b.pop(k)
    last = msgs[-1]
    if isinstance(last["content"], str):
        last["content"] = [{"type": "text", "text": last["content"]}]
    if last["content"]:
        last["content"][-1]["cache_control"] = {"type": "ephemeral"}
    return msgs


def _add_user(s, text):
    """사용자 말을 붙임. 앞이 끊겨 있으면(취소·한도) API 규칙에 맞게 이어 붙임."""
    msgs = s["messages"]
    last = msgs[-1] if msgs else None
    if last and last["role"] == "assistant" and isinstance(last["content"], list):
        pending = [b["id"] for b in last["content"] if b.get("type") == "tool_use"]
        if pending:   # 도구를 부르다 끊긴 경우: 결과 자리를 채워 줌
            msgs.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": i, "content": "(사용자가 중간에 멈췄어요)"} for i in pending]})
            last = msgs[-1]
    if last and last["role"] == "user":
        if isinstance(last["content"], str):
            last["content"] = [{"type": "text", "text": last["content"]}]
        last["content"].append({"type": "text", "text": text})
    else:
        msgs.append({"role": "user", "content": text})


def run(s, text, key, model="opus", effort="", budget=3.0, log=print, cancelled=lambda: False, progress=lambda k: None):
    """사용자 말 하나를 받아 Claude 가 끝낼 때까지(또는 예산·턴 한도까지) 도구를 돌림. 마지막 답 글을 돌려줌."""
    mid = MODELS.get(model or "opus", model or MODELS["opus"])
    pin, pout = PRICES.get(mid, (4, 20))
    _add_user(s, text)
    save(s)
    spent0, reply = s["usd"], ""
    system = [{"type": "text", "text": system_prompt(s.get("video")), "cache_control": {"type": "ephemeral"}}]
    for turn in range(MAX_TURNS):
        if cancelled():
            raise Stop("취소했어요")
        body = {"model": mid, "max_tokens": 32000, "stream": True, "system": system, "tools": TOOLS, "messages": _with_cache(s["messages"])}
        if effort:
            body["output_config"] = {"effort": effort}
        tries = 0
        while True:
            tries += 1
            try:
                content, usage, stop = _stream(body, key, lambda n: progress(min(.9, .05 + turn * .03)))
                break
            except urllib.error.HTTPError as e:
                raw = e.read().decode("utf-8", "replace")
                try:
                    msg = str((json.loads(raw).get("error") or {}).get("message") or "")
                except Exception:  # noqa: BLE001
                    msg = raw[:300]
                if e.code == 400 and "output_config" in body and "effort" in msg.lower():
                    body.pop("output_config")
                    log(f"이 모델은 노력 '{effort}' 를 받지 않아서 기본으로 보내요.")
                    continue
                if e.code in (429, 500, 502, 503, 529) and tries < 4:
                    log(f"Claude 서버가 바빠서 {tries * 15}초 뒤 다시 보내요.")
                    time.sleep(tries * 15)
                    continue
                raise RuntimeError(f"HTTP {e.code}: {msg}")
        cw, cr = int(usage.get("cache_creation_input_tokens") or 0), int(usage.get("cache_read_input_tokens") or 0)
        ti, to = int(usage.get("input_tokens") or 0), int(usage.get("output_tokens") or 0)
        s["usd"] += (ti * pin + cw * pin * 1.25 + cr * pin * .1 + to * pout) / 1e6
        for k, v in (("in", ti), ("out", to), ("cache_read", cr), ("cache_write", cw)):
            s["tokens"][k] = s["tokens"].get(k, 0) + v
        s["messages"].append({"role": "assistant", "content": content})
        texts = [b.get("text", "") for b in content if b.get("type") == "text"]
        if any(t.strip() for t in texts):
            reply = "\n".join(t for t in texts if t.strip())
            log("Claude: " + reply.strip().splitlines()[0][:120])
        uses = [b for b in content if b.get("type") == "tool_use"]
        if not uses or stop != "tool_use":
            save(s)
            log(f"끝났어요. 이번 부탁 약 {s['usd'] - spent0:.2f}달러 · 이 대화 누적 {s['usd']:.2f}달러")
            return reply, stop
        results = []
        for b in uses:
            try:
                res, label = tool_call(b["name"], b.get("input") or {}, log, cancelled)
            except Stop:
                save(s)
                raise
            except Exception as e:  # noqa: BLE001
                res, label = f"오류: {e}", f"{b['name']} 안 됨: {str(e)[:60]}"
            b["_label"] = label
            log("· " + label)
            results.append({"type": "tool_result", "tool_use_id": b["id"], "content": res})
        s["messages"].append({"role": "user", "content": results})
        save(s)
        if s["usd"] - spent0 >= budget:
            note = f"이번 부탁에서 예산 {budget:.1f}달러에 닿아 멈췄어요. 계속하려면 '이어서 부탁하기'에 '계속해 줘'라고 보내 주세요."
            s["messages"].append({"role": "assistant", "content": [{"type": "text", "text": note}]})
            save(s)
            log(note)
            return note, "budget"
    note = f"도구를 {MAX_TURNS}번 써서 일단 멈췄어요. '계속해 줘'라고 보내면 이어서 해요."
    log(note)
    return note, "turns"


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    import accounts
    name, key = accounts.active("claude")
    if not key:
        sys.exit("Claude API 키가 없어요. 앱 'AI 계정' 또는 python tools/accounts.py add 로 넣어 주세요.")
    vid = a[a.index("--video") + 1] if "--video" in a else None
    sid = a[a.index("--session") + 1] if "--session" in a else None
    text = a[0]
    s = load(sid) if sid else new_session(vid, text)
    reply, _ = run(s, text, key)
    print("\n" + reply)
    print(f"\n세션 {s['id']} · 누적 약 {s['usd']:.2f}달러")


if __name__ == "__main__":
    main()
