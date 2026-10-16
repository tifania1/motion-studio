"""영상 올리기: 플랫폼별 업로드 안내 묶음(영상·커버·제목·설명·캡션·해시태그·체크리스트)과 유튜브 자동 업로드.

인스타그램 릴스는 업로드 안내 묶음을 만들어 앱에서 직접 올립니다(자동 업로드는 Meta 개발자 앱·페이스북 페이지 연결이 필요해서 아직 넣지 않음).
유튜브는 구글 OAuth 클라이언트를 한 번 등록하면 계정(브랜드)마다 채널을 연결해 바로 올릴 수 있어요.
자세한 준비 순서는 docs/UPLOAD.md.

사용법:
    python tools/upload.py kit <영상>                         # out/<영상>/upload/ 에 안내 묶음 (upload.html 을 열면 됨)
    python tools/upload.py text <영상>                        # 플랫폼별 최종 문구와 점검 결과 보기
    python tools/upload.py youtube-client <client_secret.json> # 구글 OAuth 클라이언트(데스크톱 앱) 등록 (PC마다 한 번)
    python tools/upload.py youtube-connect <브랜드>            # 브라우저로 그 계정의 유튜브 채널 연결
    python tools/upload.py youtube-status <브랜드>
    python tools/upload.py youtube-upload <영상> [형식] [--privacy private|unlisted|public]

video.json 의 "upload" 항목:
    {"title": "유튜브 제목", "description": "유튜브 설명 본문", "caption": "인스타 캡션 본문",
     "hashtags": ["#태그"], "coverAt": 2.4, "privacy": "private", "paid": false}
brand.json 의 "social" 항목 (계정 공통):
    {"instagram": "@계정", "youtube": "@채널", "hashtags": ["#태그"], "footer": "설명 끝에 늘 붙일 말"}
사진 출처(CC BY)와 유료 광고 표시는 설명·캡션 끝에 자동으로 붙어요.
"""
import base64
import hashlib
import html
import http.server
import json
import os
import re
import secrets
import shutil
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

from common import FORMATS, ROOT, load_video, out_dir

HOME = Path(os.environ.get("MOTION_STUDIO_HOME") or (Path.home() / ".motion-studio"))
YT_CLIENT = HOME / "youtube_client.json"
YT_TOKENS = HOME / "youtube"
YT_SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"
OAUTH_AUTH = os.environ.get("MS_OAUTH_AUTH", "https://accounts.google.com/o/oauth2/v2/auth")
OAUTH_TOKEN = os.environ.get("MS_OAUTH_TOKEN", "https://oauth2.googleapis.com/token")
YT_API = os.environ.get("MS_YT_API", "https://www.googleapis.com/youtube/v3")
YT_UPLOAD = os.environ.get("MS_YT_UPLOAD", "https://www.googleapis.com/upload/youtube/v3")

PLATFORMS = [
    {"id": "shorts", "name": "유튜브 쇼츠", "site": "youtube", "formats": ["tall"], "page": "https://studio.youtube.com/",
     "tips": ["세로 영상이고 3분 이하면 쇼츠로 올라가요. 제목에 #shorts 는 없어도 돼요.",
              "쇼츠 커버는 업로드 화면의 '썸네일'에서 영상 속 장면을 고르는 방식이에요. 커버 이미지 아래에 적힌 시각의 장면을 고르면 돼요.",
              "음악을 넣었다면 직접 만든 곡이나 사용 허락을 받은 곡인지 확인하세요."]},
    {"id": "youtube", "name": "유튜브 (가로 영상)", "site": "youtube", "formats": ["wide"], "page": "https://studio.youtube.com/",
     "tips": ["썸네일(1280×720)을 맞춤 썸네일로 올리세요. 채널 전화번호 인증이 돼 있어야 올릴 수 있어요.",
              "아동용 아님, 유료 광고가 있으면 '유료 프로모션 포함'을 체크하세요."]},
    {"id": "reels", "name": "인스타 릴스", "site": "instagram", "formats": ["tall"], "page": "https://www.instagram.com/",
     "tips": ["휴대폰으로 옮겨 올리거나, PC 인스타그램에서 '만들기 → 게시물'로 올리면 9:16 영상은 릴스로 올라가요.",
              "커버는 '커버 편집 → 카메라 롤에서 추가'로 cover.jpg 를 넣으세요. 프로필 격자에서는 가운데 3:4 부분만 보여요.",
              "해시태그는 한 게시물에 5개까지만 쓸 수 있어요.",
              "협찬·제휴 광고면 '유료 파트너십 레이블'을 켜세요."]},
    {"id": "feed", "name": "인스타 피드", "site": "instagram", "formats": ["portrait", "square"], "page": "https://www.instagram.com/",
     "tips": ["4:5 영상이 피드에서 화면을 가장 크게 차지해요.", "해시태그는 5개까지만 쓸 수 있어요."]},
]
PRIVACY_KO = {"private": "비공개", "unlisted": "일부 공개", "public": "공개"}
LIMITS = {"ytTitle": 100, "ytDesc": 5000, "igCaption": 2200, "igTags": 5, "ytTags": 15}


class UploadError(Exception):
    pass


# ------------------------------------------------------------------ 문구
def brand_of(v):
    p = ROOT / "brands" / v.get("brand", "") / "brand.json"
    return json.loads(p.read_text(encoding="utf-8-sig")) if p.exists() else {}


def platforms_for(v):
    fm = v.get("formats") or list(FORMATS)
    out = []
    for p in PLATFORMS:
        f = next((f for f in p["formats"] if f in fm), None)
        if f:
            out.append(dict(p, fmt=f))
    return out


def credit_lines(vdir, v):
    lines = []
    cp = vdir / "photos" / "credits.json"
    if cp.exists():
        for c in json.loads(cp.read_text(encoding="utf-8-sig")):
            if c.get("credit_line") and c["credit_line"] not in lines:
                lines.append(c["credit_line"])
    for c in re.findall(r'"credit"\s*:\s*"([^"]+)"', json.dumps(v.get("content") or {}, ensure_ascii=False)):
        if c.startswith("Photo") and c not in lines:
            lines.append(c)
    return lines


def norm_tags(tags):
    out = []
    for t in tags or []:
        t = re.sub(r"\s+", "", str(t)).strip()
        if not t:
            continue
        t = "#" + t.lstrip("#")
        if t != "#" and t not in out:
            out.append(t)
    return out


SKIP_KEYS = {"credit", "image", "photo", "focus", "bg", "font", "color", "accent", "kind", "type", "motif", "viz", "film", "layout"}


def content_lines(content, limit=4):
    """문구(content)에서 화면에 나오는 한국어 문장을 순서대로 몇 줄 뽑음 (설명 초안용)."""
    out = []

    def walk(x, key=""):
        if len(out) >= limit:
            return
        if isinstance(x, dict):
            for k, val in x.items():
                if k not in SKIP_KEYS and not re.fullmatch(r"photo\d*", k):
                    walk(val, k)
        elif isinstance(x, list):
            for val in x:
                walk(val, key)
        elif isinstance(x, str):
            s = re.sub(r"\s+", " ", x.replace("\n", " ")).strip()
            if len(s) >= 6 and re.search(r"[가-힣]", s) and "가상 브랜드" not in s and s not in out:
                out.append(s)
    walk(content or {})
    return out


def default_meta(v, b):
    soc = b.get("social") or {}
    name = b.get("name") or v.get("brand", "")
    title = (v.get("title") or "").strip()
    tags = norm_tags(soc.get("hashtags")) or norm_tags([re.sub(r"[^\w가-힣]", "", name)])
    desc = "\n".join(content_lines(v.get("content"))) or b.get("description") or ""
    return {"title": f"{title} | {name}" if title and name and name not in title else title or name,
            "description": desc, "caption": desc, "hashtags": tags, "coverAt": None, "privacy": "private", "paid": False}


def meta_of(v, b):
    m = default_meta(v, b)
    for k, val in (v.get("upload") or {}).items():
        if k in m and val not in (None, ""):
            m[k] = val
    m["hashtags"] = norm_tags(m.get("hashtags"))
    return m


def final_texts(name):
    """플랫폼별 최종 제목·설명·캡션과 점검 결과."""
    v, b, vdir = load_video(name)
    m = meta_of(v, b)
    soc = b.get("social") or {}
    credits = credit_lines(vdir, v)
    paid = "#광고 · 유료 광고 포함" if m.get("paid") else ""
    footer = (soc.get("footer") or "").strip()
    yt_tags, ig_tags = m["hashtags"][:LIMITS["ytTags"]], m["hashtags"][:LIMITS["igTags"]]
    yt_desc = "\n\n".join(x for x in [paid, m["description"].strip(), footer, "\n".join(credits), " ".join(yt_tags)] if x)
    ig_cap = "\n\n".join(x for x in [paid, m["caption"].strip(), footer, "\n".join(credits), " ".join(ig_tags)] if x)
    out = {}
    for p in platforms_for(v):
        notes = []
        if p["site"] == "youtube":
            t = {"title": m["title"].strip(), "text": yt_desc, "tags": [x.lstrip("#") for x in yt_tags]}
            if not t["title"]:
                notes.append("제목이 비어 있어요")
            if len(t["title"]) > LIMITS["ytTitle"]:
                notes.append(f"제목이 {len(t['title'])}자예요. 100자 안으로 줄여 주세요")
            if re.search(r"[<>]", t["title"] + yt_desc):
                notes.append("유튜브는 제목·설명에 < > 를 쓸 수 없어요")
            if len(yt_desc) > LIMITS["ytDesc"]:
                notes.append("설명이 5000자를 넘어요")
            if len(m["hashtags"]) > LIMITS["ytTags"]:
                notes.append(f"해시태그가 많아서 앞의 {LIMITS['ytTags']}개만 넣었어요")
        else:
            t = {"title": "", "text": ig_cap, "tags": ig_tags}
            if len(ig_cap) > LIMITS["igCaption"]:
                notes.append(f"캡션이 {len(ig_cap)}자예요. 2200자 안으로 줄여 주세요")
            if len(m["hashtags"]) > LIMITS["igTags"]:
                notes.append("인스타그램은 해시태그를 5개까지만 써서 앞의 5개만 넣었어요")
        if not (m["description"] if p["site"] == "youtube" else m["caption"]).strip():
            notes.append("본문이 비어 있어요. 영상에서 하는 말을 한두 문장으로 적어 주세요")
        out[p["id"]] = dict(t, platform=p["id"], name=p["name"], fmt=p["fmt"], notes=notes)
    return out, m


# ------------------------------------------------------------------ 커버
def capture_cover(name, fmt, at=None):
    """fmt 영상의 at 초 장면을 PNG로. at 이 없으면 길이의 30% 지점. (경로, 실제 시각) 반환."""
    import asyncio
    from playwright.async_api import async_playwright
    from render import open_page
    od = out_dir(name, fmt)
    html_p = od / f"{name}-{fmt}.html"
    if not html_p.exists():
        import subprocess
        subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools" / "build.py"), name, fmt], check=True, capture_output=True)
    dst = od / "cover.png"

    async def go():
        async with async_playwright() as p:
            browser, page, dur, _ = await open_page(p, html_p, fmt, False, 1.0)
            t = float(at) if at not in (None, "") else round(dur * .3, 2)
            t = max(0.0, min(t, max(0.0, dur - .05)))
            await page.evaluate(f"window.__seek({t})")
            await page.screenshot(path=str(dst))
            await browser.close()
            return t
    t = asyncio.run(go())
    return dst, t


def save_jpg(src, dst, size=None, max_bytes=None):
    from PIL import Image
    im = Image.open(src).convert("RGB")
    if size:
        im = im.resize(size, Image.LANCZOS)
    q = 92
    while True:
        im.save(dst, "JPEG", quality=q, optimize=True)
        if not max_bytes or dst.stat().st_size <= max_bytes or q <= 60:
            return dst
        q -= 8


# ------------------------------------------------------------------ 안내 묶음
def safe_name(s):
    s = re.sub(r'[\\/:*?"<>|\n\r\t]+', " ", s).strip()
    return re.sub(r"\s+", " ", s)[:60] or "video"


def make_kit(name, log=print):
    v, b, vdir = load_video(name)
    texts, m = final_texts(name)
    kd = ROOT / "out" / name / "upload"
    kd.mkdir(parents=True, exist_ok=True)
    plats = platforms_for(v)
    covers, cover_t = {}, None
    for fmt in sorted({p["fmt"] for p in plats}):
        log(f"  {fmt}: 커버 장면 찍는 중")
        png, cover_t = capture_cover(name, fmt, m.get("coverAt"))
        covers[fmt] = png
    base = safe_name(f"{b.get('name', '')} {v.get('title') or name}")
    items = []
    for p in plats:
        t = texts[p["id"]]
        pd = kd / p["id"]
        pd.mkdir(parents=True, exist_ok=True)
        for f in pd.iterdir():   # 폴더째 지우지 않음: 탐색기로 열려 있거나 영상을 재생 중이어도 되게
            try:
                f.unlink()
            except OSError:
                pass
        mp4 = ROOT / "out" / name / p["fmt"] / f"{name}_{p['fmt']}.mp4"
        vid = None
        if mp4.exists():
            vid = pd / f"{base} - {p['name']}.mp4"
            try:
                if vid.exists():
                    vid.unlink()
                os.link(mp4, vid)
            except OSError:
                try:
                    shutil.copy2(mp4, vid)
                except OSError:
                    log(f"  {p['name']}: 영상 파일을 다른 프로그램이 쓰고 있어서 바꾸지 못했어요 (예전 파일이 남아 있어요).")
        cover = None
        if p["fmt"] in covers:
            if p["id"] == "youtube":
                cover = save_jpg(covers[p["fmt"]], pd / "thumbnail.jpg", (1280, 720), 2_000_000)
            else:
                cover = save_jpg(covers[p["fmt"]], pd / "cover.jpg")
        body = (f"제목\n{t['title']}\n\n설명\n{t['text']}\n" if p["site"] == "youtube" else f"캡션\n{t['text']}\n")
        (pd / "문구.txt").write_text(body, encoding="utf-8-sig")
        items.append({"p": p, "t": t, "video": vid, "cover": cover, "mp4": mp4.exists()})
    page = kd / "upload.html"
    page.write_text(kit_html(v, b, m, items, cover_t, kd), encoding="utf-8")
    log(f"  안내 묶음 → {page.relative_to(ROOT)}")
    return {"dir": kd, "page": page, "items": [{"platform": i["p"]["id"], "mp4": i["mp4"], "notes": i["t"]["notes"]} for i in items]}


def kit_html(v, b, m, items, cover_t, kd):
    e = html.escape
    rel = lambda p: urllib.parse.quote(p.relative_to(kd).as_posix()) if p else ""
    cards = []
    for i, it in enumerate(items):
        p, t = it["p"], it["t"]
        fields = []
        if p["site"] == "youtube":
            fields.append(("제목", t["title"]))
            fields.append(("설명", t["text"]))
            if t["tags"]:
                fields.append(("태그 (세부정보 → 태그 칸)", ", ".join(t["tags"])))
        else:
            fields.append(("캡션", t["text"]))
        fhtml = "".join(f'<div class="f"><div class="fh"><b>{e(k)}</b><button data-c="c{i}_{j}">복사</button></div>'
                        f'<pre id="c{i}_{j}">{e(val)}</pre></div>' for j, (k, val) in enumerate(fields))
        media = (f'<video src="{rel(it["video"])}" controls playsinline preload="metadata"></video>' if it["video"] else
                 '<div class="miss">MP4가 아직 없어요. 앱에서 이 형식의 MP4를 만든 뒤 묶음을 다시 만드세요.</div>')
        cover = (f'<figure><img src="{rel(it["cover"])}" alt="커버"><figcaption>{"썸네일 1280×720" if p["id"] == "youtube" else "커버"}'
                 f'{f" · {cover_t:.1f}초 장면" if cover_t is not None else ""}</figcaption></figure>') if it["cover"] else ""
        notes = "".join(f"<li class=warn>{e(n)}</li>" for n in t["notes"])
        tips = "".join(f"<li>{e(x)}</li>" for x in p["tips"])
        cards.append(f"""<section class="card"><header><h2>{e(p['name'])}</h2><span class="fmt">{e(p['fmt'])}</span>
<a class="go" href="{e(p['page'])}" target="_blank" rel="noopener">올리러 가기 ↗</a></header>
<div class="grid"><div class="media">{media}{cover}</div><div class="text">{fhtml}<ul class="tips">{notes}{tips}</ul></div></div></section>""")
    when = time.strftime("%Y-%m-%d %H:%M")
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(v.get('title') or '')} 올리기</title><style>
:root{{--bg:#f5f4f0;--card:#fff;--ink:#1b1b1d;--ink2:#5f5f66;--line:#e2e0da;--acc:#e8590c;--warn:#b42318}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151517;--card:#1f1f22;--ink:#f2f1ee;--ink2:#a5a5ad;--line:#33333a;--acc:#ff8a3d;--warn:#ff8a80}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 "Pretendard","Noto Sans KR","Malgun Gothic",system-ui,sans-serif}}
main{{max-width:1080px;margin:0 auto;padding:28px 16px 60px}}h1{{font-size:24px;margin:0 0 4px}}.sub{{color:var(--ink2);margin:0 0 22px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin:0 0 18px}}
header{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px}}h2{{font-size:18px;margin:0}}
.fmt{{font-size:12px;color:var(--ink2);border:1px solid var(--line);border-radius:99px;padding:1px 8px}}
.go{{margin-left:auto;color:var(--acc);font-weight:700;text-decoration:none}}
.grid{{display:grid;grid-template-columns:minmax(0,360px) minmax(0,1fr);gap:18px}}@media (max-width:720px){{.grid{{grid-template-columns:1fr}}}}
.media{{display:grid;grid-template-columns:1fr 1fr;gap:10px;align-items:start}}.media .miss{{grid-column:1/-1}}.media video,.media img{{width:100%;border-radius:10px;background:#000;display:block}}figure{{margin:0}}figcaption{{font-size:12px;color:var(--ink2);margin-top:4px}}
.miss{{border:1px dashed var(--line);border-radius:10px;padding:18px;color:var(--ink2)}}
.f{{margin-bottom:12px}}.fh{{display:flex;align-items:center;justify-content:space-between}}
.fh button{{font:inherit;font-size:13px;border:1px solid var(--line);background:none;color:var(--ink);border-radius:8px;padding:2px 10px;cursor:pointer}}
pre{{white-space:pre-wrap;word-break:break-word;font:inherit;background:var(--bg);border-radius:8px;padding:10px 12px;margin:6px 0 0}}
.tips{{margin:6px 0 0;padding-left:18px;color:var(--ink2);font-size:14px}}.tips .warn{{color:var(--warn);font-weight:700}}
</style></head><body><main><h1>{e(v.get('title') or '')} 올리기</h1>
<p class="sub">{e(b.get('name', ''))} · {when} 에 만든 안내예요. 문구를 고치면 앱에서 묶음을 다시 만드세요.</p>
{''.join(cards)}</main><script>
document.addEventListener('click',async e=>{{const b=e.target.closest('[data-c]');if(!b)return;const t=document.getElementById(b.dataset.c).textContent;
try{{await navigator.clipboard.writeText(t)}}catch(_){{const a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();document.execCommand('copy');a.remove()}}
const o=b.textContent;b.textContent='복사했어요';setTimeout(()=>b.textContent=o,1400)}});
</script></body></html>"""


# ------------------------------------------------------------------ 유튜브
def _http(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except (urllib.error.URLError, OSError) as e:   # 인터넷 끊김·프록시·시간 초과: 0 으로 돌려주고 부르는 쪽이 판단
        return 0, {}, NET_FAIL + str(e).encode("utf-8", "replace")


NET_FAIL = b"__NET__"


def _api_error(body):
    if isinstance(body, bytes) and body.startswith(NET_FAIL):
        return "인터넷에 연결하지 못했어요. 인터넷·회사 프록시·방화벽을 확인하고 다시 시도해 주세요."
    try:
        j = json.loads(body)
        err = j.get("error")
        if isinstance(err, dict):
            reason = ((err.get("errors") or [{}])[0]).get("reason", "")
            msg = err.get("message", "")
            if reason == "quotaExceeded":
                return "오늘 유튜브 API 사용량을 다 썼어요. 내일 다시 해 보세요."
            if reason in ("uploadLimitExceeded",):
                return "이 채널의 하루 업로드 한도를 넘었어요."
            return f"{msg} ({reason})" if reason else msg
        return j.get("error_description") or str(err)
    except Exception:  # noqa: BLE001
        return body[:300].decode("utf-8", "replace") if isinstance(body, bytes) else str(body)[:300]


def yt_client():
    if not YT_CLIENT.exists():
        raise UploadError("유튜브 연결 준비가 안 돼 있어요. 구글 OAuth 클라이언트(데스크톱 앱) JSON을 먼저 등록해 주세요 (docs/UPLOAD.md).")
    j = json.loads(YT_CLIENT.read_text(encoding="utf-8-sig"))
    c = j.get("installed") or j.get("web") or j
    if not c.get("client_id") or not c.get("client_secret"):
        raise UploadError("OAuth 클라이언트 파일에 client_id·client_secret 이 없어요.")
    return c


def set_client(path):
    j = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    c = j.get("installed") or j.get("web") or {}
    if not c.get("client_id"):
        raise UploadError("구글 클라우드에서 받은 OAuth 클라이언트 JSON이 맞는지 확인해 주세요 (유형: 데스크톱 앱).")
    if "installed" not in j:
        raise UploadError("OAuth 클라이언트 유형을 '데스크톱 앱'으로 만들어 주세요.")
    HOME.mkdir(parents=True, exist_ok=True)
    YT_CLIENT.write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")
    return c["client_id"]


def token_path(brand):
    if not re.fullmatch(r"[a-z0-9][a-z0-9\-_]*", brand or ""):
        raise UploadError("브랜드 이름이 올바르지 않아요")
    return YT_TOKENS / f"{brand}.json"


def yt_status(brand):
    tp = token_path(brand)
    st = {"client": YT_CLIENT.exists(), "connected": tp.exists()}
    if tp.exists():
        t = json.loads(tp.read_text(encoding="utf-8-sig"))
        st.update(channel=t.get("channel", ""), channelId=t.get("channelId", ""), connectedAt=t.get("connectedAt", ""))
    return st


def yt_connect(brand, log=print, timeout=300, open_browser=True):
    c = yt_client()
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_urlsafe(16)
    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" in q or "error" in q:
                got.update({k: v[0] for k, v in q.items()})
                ok = "code" in q and q.get("state", [""])[0] == state
                msg = "유튜브 채널을 연결했어요. 이 창을 닫고 모션 스튜디오로 돌아가세요." if ok else "연결하지 못했어요. 모션 스튜디오에서 다시 시도해 주세요."
                body = f"<!doctype html><meta charset=utf-8><title>모션 스튜디오</title><body style='font:16px sans-serif;padding:40px'>{msg}</body>".encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    redirect = f"http://127.0.0.1:{srv.server_port}"
    url = OAUTH_AUTH + "?" + urllib.parse.urlencode({
        "client_id": c["client_id"], "redirect_uri": redirect, "response_type": "code", "scope": YT_SCOPES,
        "code_challenge": challenge, "code_challenge_method": "S256", "access_type": "offline", "prompt": "consent select_account",
        "state": state})
    th = threading.Thread(target=lambda: [srv.handle_request() for _ in range(20) if not got], daemon=True)
    th.start()
    log("브라우저에서 이 계정에 쓸 유튜브 채널을 고르고 허용을 눌러 주세요.")
    if open_browser:
        webbrowser.open(url)
    else:
        log(url)
    t0 = time.time()
    while not got and time.time() - t0 < timeout:
        time.sleep(.3)
    srv.server_close()
    if not got:
        raise UploadError("5분 안에 연결이 끝나지 않았어요. 다시 시도해 주세요.")
    if got.get("error"):
        raise UploadError("구글에서 연결을 거절했어요: " + got["error"])
    if got.get("state") != state:
        raise UploadError("연결 확인 값이 맞지 않아요. 다시 시도해 주세요.")
    st, _, body = _http(OAUTH_TOKEN, urllib.parse.urlencode({
        "code": got["code"], "client_id": c["client_id"], "client_secret": c["client_secret"], "redirect_uri": redirect,
        "grant_type": "authorization_code", "code_verifier": verifier}).encode(), {"Content-Type": "application/x-www-form-urlencoded"})
    if st != 200:
        raise UploadError("토큰을 받지 못했어요: " + _api_error(body))
    tok = json.loads(body)
    if not tok.get("refresh_token"):
        raise UploadError("새로고침 토큰이 오지 않았어요. 구글 계정의 '타사 앱 액세스'에서 이 앱을 지우고 다시 연결해 주세요.")
    access = tok["access_token"]
    st, _, body = _http(YT_API + "/channels?part=snippet&mine=true", headers={"Authorization": f"Bearer {access}"})
    chan, cid = "", ""
    if st == 200:
        items = json.loads(body).get("items") or []
        if items:
            chan, cid = items[0]["snippet"].get("title", ""), items[0].get("id", "")
    if st == 200 and not cid:
        raise UploadError("이 구글 계정에는 유튜브 채널이 없어요. 유튜브에서 채널을 먼저 만들어 주세요.")
    YT_TOKENS.mkdir(parents=True, exist_ok=True)
    data = {"refresh_token": tok["refresh_token"], "access_token": access, "expires": time.time() + int(tok.get("expires_in", 3600)) - 60,
            "channel": chan, "channelId": cid, "connectedAt": time.strftime("%Y-%m-%d %H:%M")}
    tp = token_path(brand)
    tp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        os.chmod(tp, 0o600)
    except OSError:
        pass
    log(f"연결했어요: {chan or '(채널 이름을 읽지 못함)'}")
    return yt_status(brand)


def yt_disconnect(brand):
    tp = token_path(brand)
    if tp.exists():
        tp.unlink()


def yt_access(brand):
    tp = token_path(brand)
    if not tp.exists():
        raise UploadError("이 계정에 연결된 유튜브 채널이 없어요. 먼저 채널을 연결해 주세요.")
    t = json.loads(tp.read_text(encoding="utf-8-sig"))
    if t.get("access_token") and t.get("expires", 0) > time.time():
        return t["access_token"]
    c = yt_client()
    st, _, body = _http(OAUTH_TOKEN, urllib.parse.urlencode({
        "client_id": c["client_id"], "client_secret": c["client_secret"], "refresh_token": t["refresh_token"],
        "grant_type": "refresh_token"}).encode(), {"Content-Type": "application/x-www-form-urlencoded"})
    if st != 200:
        msg = _api_error(body)
        if "invalid_grant" in str(body):
            msg = "연결이 만료됐어요. 채널을 다시 연결해 주세요. (구글 클라우드의 OAuth 동의 화면이 '테스트' 상태면 7일마다 만료돼요)"
        raise UploadError(msg)
    tok = json.loads(body)
    t.update(access_token=tok["access_token"], expires=time.time() + int(tok.get("expires_in", 3600)) - 60)
    tp.write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
    return t["access_token"]


def yt_upload(name, fmt=None, privacy=None, log=print, progress=None, chunk=8 * 1024 * 1024):
    v, b, vdir = load_video(name)
    texts, m = final_texts(name)
    yts = [p for p in platforms_for(v) if p["site"] == "youtube" and (fmt is None or p["fmt"] == fmt)]
    if not yts:
        raise UploadError("유튜브에 올릴 형식(9:16 또는 16:9)이 이 영상에 없어요.")
    p = yts[0]
    t = texts[p["id"]]
    if not t["title"]:
        raise UploadError("유튜브 제목을 먼저 적어 주세요.")
    hard = [n for n in t["notes"] if "줄여" in n or "< >" in n or "비어" in n and "제목" in n]
    if hard:
        raise UploadError(" / ".join(hard))
    mp4 = ROOT / "out" / name / p["fmt"] / f"{name}_{p['fmt']}.mp4"
    if not mp4.exists():
        raise UploadError(f"{p['fmt']} MP4가 아직 없어요. MP4를 먼저 만들어 주세요.")
    privacy = privacy or m.get("privacy") or "private"
    if privacy not in ("private", "unlisted", "public"):
        raise UploadError("공개 범위는 private, unlisted, public 중 하나예요.")
    access = yt_access(v["brand"])
    size = mp4.stat().st_size
    meta = {"snippet": {"title": t["title"], "description": t["text"], "tags": t["tags"], "categoryId": "22",
                        "defaultLanguage": "ko", "defaultAudioLanguage": "ko"},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False, "embeddable": True}}
    log(f"{p['name']} 올리는 중: {mp4.name} ({size / 1e6:.1f}MB, {PRIVACY_KO[privacy]})")
    st, hd, body = _http(YT_UPLOAD + "/videos?uploadType=resumable&part=snippet,status", json.dumps(meta).encode(),
                         {"Authorization": f"Bearer {access}", "Content-Type": "application/json; charset=UTF-8",
                          "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4"}, "POST")
    loc = {k.lower(): val for k, val in hd.items()}.get("location")
    if st not in (200, 201) or not loc:
        raise UploadError("업로드를 시작하지 못했어요: " + _api_error(body))
    sent, result, tries = 0, None, 0
    with open(mp4, "rb") as fh:
        while sent < size:
            fh.seek(sent)
            part = fh.read(chunk)
            end = sent + len(part) - 1
            st, hd, body = _http(loc, part, {"Authorization": f"Bearer {access}", "Content-Length": str(len(part)),
                                             "Content-Range": f"bytes {sent}-{end}/{size}"}, "PUT")
            if st in (200, 201):
                result = json.loads(body)
                sent = size
            elif st == 308:
                rng = {k.lower(): val for k, val in hd.items()}.get("range")
                sent = int(rng.split("-")[1]) + 1 if rng else 0
                tries = 0
            elif (st >= 500 or st == 0) and tries < 6:
                tries += 1
                time.sleep(2 ** tries)
                st2, hd2, _ = _http(loc, b"", {"Authorization": f"Bearer {access}", "Content-Range": f"bytes */{size}"}, "PUT")
                rng = {k.lower(): val for k, val in hd2.items()}.get("range")
                sent = int(rng.split("-")[1]) + 1 if st2 == 308 and rng else 0 if st2 == 308 else sent
                continue
            else:
                raise UploadError("업로드 중에 멈췄어요: " + _api_error(body))
            if progress:
                progress(sent / size)
    vid = result.get("id")
    status = (result.get("status") or {})
    got_privacy = status.get("privacyStatus", privacy)
    url = f"https://youtube.com/shorts/{vid}" if p["id"] == "shorts" else f"https://youtu.be/{vid}"
    note = ""
    if got_privacy != privacy:
        note = (f"{PRIVACY_KO.get(privacy, privacy)}(으)로 올렸는데 유튜브가 {PRIVACY_KO.get(got_privacy, got_privacy)}(으)로 바꿨어요. "
                "검수받지 않은 구글 클라우드 프로젝트로 올린 영상은 비공개로만 올라가요. 유튜브 스튜디오에서 공개 범위를 바꿔 주세요.")
    if p["id"] == "youtube":
        thumb = ROOT / "out" / name / "upload" / "youtube" / "thumbnail.jpg"
        if not thumb.exists():
            try:
                png, _ = capture_cover(name, p["fmt"], m.get("coverAt"))
                thumb.parent.mkdir(parents=True, exist_ok=True)
                save_jpg(png, thumb, (1280, 720), 2_000_000)
            except Exception:  # noqa: BLE001
                thumb = None
        if thumb and thumb.exists():
            st, _, body = _http(YT_UPLOAD + f"/thumbnails/set?videoId={vid}", thumb.read_bytes(),
                                {"Authorization": f"Bearer {access}", "Content-Type": "image/jpeg"}, "POST")
            if st != 200:
                note = (note + " " if note else "") + "썸네일은 올리지 못했어요(채널 전화번호 인증이 필요할 수 있어요): " + _api_error(body)
    rec = {"id": vid, "url": url, "privacy": got_privacy, "at": time.strftime("%Y-%m-%d %H:%M"), "fmt": p["fmt"]}
    vp = vdir / "video.json"
    vj = json.loads(vp.read_text(encoding="utf-8-sig"))
    vj.setdefault("upload", {}).setdefault("done", {})[p["id"]] = rec
    tmp = vp.with_suffix(".tmp")
    tmp.write_text(json.dumps(vj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, vp)
    log(f"올렸어요: {url}")
    if note:
        log(note)
    return dict(rec, note=note)


# ------------------------------------------------------------------ 명령줄
def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    try:
        if a[0] == "kit" and len(a) > 1:
            r = make_kit(a[1])
            for i in r["items"]:
                print(f"  {i['platform']}: {'MP4 있음' if i['mp4'] else 'MP4 없음'}{' · ' + ' / '.join(i['notes']) if i['notes'] else ''}")
        elif a[0] == "text" and len(a) > 1:
            texts, _ = final_texts(a[1])
            for t in texts.values():
                print(f"=== {t['name']} ({t['fmt']})")
                if t["title"]:
                    print("제목:", t["title"])
                print(t["text"])
                for n in t["notes"]:
                    print("  확인:", n)
        elif a[0] == "youtube-client" and len(a) > 1:
            print("등록했어요:", set_client(a[1]))
        elif a[0] == "youtube-connect" and len(a) > 1:
            print(json.dumps(yt_connect(a[1]), ensure_ascii=False))
        elif a[0] == "youtube-status" and len(a) > 1:
            st = yt_status(a[1])
            if not st["client"]:
                print("유튜브 연결 준비가 안 돼 있어요. 구글 OAuth 클라이언트(데스크톱 앱) JSON 을 먼저 등록하세요: "
                      "python tools/upload.py youtube-client <파일.json> (순서는 docs/UPLOAD.md)")
            elif not st["connected"]:
                print(f"'{a[1]}' 계정에 연결된 유튜브 채널이 없어요: python tools/upload.py youtube-connect {a[1]}")
            else:
                print(f"연결됨: {st.get('channel') or '(채널 이름 없음)'} · {st.get('connectedAt', '')}")
        elif a[0] == "youtube-upload" and len(a) > 1:
            fmt = a[2] if len(a) > 2 and not a[2].startswith("--") else None
            priv = a[a.index("--privacy") + 1] if "--privacy" in a else None
            r = yt_upload(a[1], fmt, priv, progress=lambda k: print(f"  {k * 100:.0f}%"))
            print(json.dumps(r, ensure_ascii=False))
        else:
            sys.exit(__doc__)
    except UploadError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
