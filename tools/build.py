"""영상 하나를 형식(비율)별 HTML 한 파일로 묶습니다. 브랜드 글꼴·색·이미지와 엔진, GSAP이 모두 들어갑니다.

사용법:
    python tools/build.py <영상이름> [형식]
    예) python tools/build.py cafe-spring-promo            # video.json 의 모든 형식
        python tools/build.py cafe-spring-promo tall,square

결과: out/<영상이름>/<형식>/<영상이름>-<형식>.html  (브라우저로 바로 열어 볼 수 있음, 인터넷 없이도 동작)
"""
import base64
import io
import json
import re
import sys

from fontTools import subset
from fontTools.ttLib import TTFont
from PIL import Image

from common import FORMATS, ROOT, formats_of, load_video, out_dir, resolve

GSAP_TAG = re.compile(r'<script src="https://cdnjs\.cloudflare\.com/ajax/libs/gsap/[^"]+/gsap\.min\.js"></script>')
MAX_SIDE = 2160  # 이미지 긴 변 최대 픽셀


def data_uri(path, cache={}):
    st = path.stat()
    ck = (str(path), st.st_mtime_ns, st.st_size)
    if ck in cache:
        return cache[ck]
    im = Image.open(path)
    alpha = im.mode in ("RGBA", "LA", "P") and (im.mode != "P" or "transparency" in im.info)
    im = im.convert("RGBA" if alpha else "RGB")
    if max(im.size) > MAX_SIDE:
        r = MAX_SIDE / max(im.size)
        im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    buf = io.BytesIO()
    if alpha:
        im.save(buf, "WEBP", quality=88, method=6, exact=True)
    else:
        im.save(buf, "WEBP", quality=84, method=6)
    cache[ck] = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
    return cache[ck]


def subset_font(path, text):
    font = TTFont(path)
    cmap = font.getBestCmap()
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(c for c in text if ord(c) in cmap))
    sub.subset(font)
    out = io.BytesIO()
    font.flavor = "woff2"
    font.save(out)
    return out.getvalue(), cmap


def brand_css(brand):
    c = brand.get("colors", {})
    t = brand.get("type", {})
    fb = {"display": "serif", "heading": "sans-serif", "body": "sans-serif"}
    names = {"bg": "--bg", "onBg": "--on-bg", "onBgMuted": "--on-bg-muted", "paper": "--paper", "ink": "--ink",
             "accent": "--accent", "accentInk": "--accent-ink", "pattern": "--pattern", "glow": "--glow"}
    lines = [f"{v}:{c[k]};" for k, v in names.items() if k in c]
    # 강조색 바탕 위 형광펜 색: 강조색 위 글자(accentInk)가 어두우면 밝은 펜, 밝으면 어두운 펜
    ink = c.get("accentInk", "#111111").lstrip("#")
    if len(ink) == 6:
        r, g, b = (int(ink[i:i + 2], 16) for i in (0, 2, 4))
        dark_ink = (0.299 * r + 0.587 * g + 0.114 * b) < 140
        lines.append(f"--mark-on-accent:{'rgba(255,255,255,.62)' if dark_ink else 'rgba(0,0,0,.3)'};")
    for role in ("display", "heading", "body"):
        fam = t.get(role) or t.get("body") or "sans-serif"
        lines.append(f'--font-{role}:"{fam}",{fb[role]};')
        lines.append(f'--font-{role}-brand:"{fam}",{fb[role]};')   # 스타일 글꼴에 없는 글자는 브랜드 글꼴로
    return ":root{" + "".join(lines) + "}"


def asset_map(video, brand, vdir, bdir, fmt):
    paths = {}
    for k, p in (brand.get("assets") or {}).items():
        paths[k] = resolve(p, bdir)
    va = video.get("assets") or {}
    if any(k in FORMATS or k == "common" for k in va):
        merged = dict(va.get("common", {}))
        merged.update(va.get(fmt, {}))
    else:
        merged = va
    for k, p in merged.items():
        paths[k] = resolve(p, vdir)
    return {k: data_uri(p) for k, p in paths.items()}


def load_style(video):
    """video.json 의 style(스타일 이름)로 styles/<이름>/style.json 을 읽음. 없으면 {}."""
    sid = video.get("style")
    if not sid:
        return {}
    p = ROOT / "styles" / sid / "style.json"
    if not p.exists():
        print(f"  경고: 스타일 '{sid}' 이 없어서 스타일 없이 만듭니다 (styles/{sid}/style.json)")
        return {}
    return json.loads(p.read_text(encoding="utf-8-sig"))


def style_css(style, video):
    """스타일 글꼴·색·모양을 CSS 변수로. 글꼴은 styleFonts=false, 색은 styleColors=true 일 때만 바꿈."""
    out = []
    t = style.get("type") or {}
    if t and video.get("styleFonts", True):
        fb = {"display": "serif", "heading": "sans-serif", "body": "sans-serif"}
        fam = lambda v: ",".join(f'"{x}"' for x in (v if isinstance(v, list) else [v]))   # ["Caveat", "Nanum Pen"] 처럼 여러 개면 차례로
        out += [f'--font-{r}:{fam(t[r])},var(--font-{r}-brand,{fb[r]});' for r in ("display", "heading", "body") if t.get(r)]
    if video.get("styleColors") and style.get("colors"):
        names = {"bg": "--bg", "onBg": "--on-bg", "onBgMuted": "--on-bg-muted", "paper": "--paper", "ink": "--ink",
                 "accent": "--accent", "accentInk": "--accent-ink", "pattern": "--pattern", "glow": "--glow"}
        out += [f"{v}:{style['colors'][k]};" for k, v in names.items() if k in style["colors"]]
        # 팔레트의 나머지 색(바탕·글자·강조 말고)은 그라디언트 덩어리 같은 곳에 --pal1~3 으로
        used = {str(style["colors"].get(k, "")).lower() for k in ("bg", "onBg", "paper", "ink", "accent")}
        extra = [c for c in style.get("palette") or [] if str(c).lower() not in used][:3]
        out += [f"--pal{i}:{c};" for i, c in enumerate(extra, 1)]
        ink = str(style["colors"].get("accentInk", "")).lstrip("#")
        if len(ink) == 6:
            r, g, b = (int(ink[i:i + 2], 16) for i in (0, 2, 4))
            out.append(f"--mark-on-accent:{'rgba(255,255,255,.62)' if (0.299 * r + 0.587 * g + 0.114 * b) < 140 else 'rgba(0,0,0,.3)'};")
    sh = style.get("shape") or {}
    if sh.get("radius") is not None:
        out.append(f"--radius:{sh['radius']};")
    return (":root{" + "".join(out) + "}") if out else ""


def build(name, fmt, video, brand, vdir):
    bdir = ROOT / "brands" / video["brand"]
    style = load_style(video)
    if video.get("template"):
        src_path = ROOT / "templates" / video["template"] / "index.html"
    else:
        src = video.get("src", "index.html")
        src_path = vdir / (src[fmt] if isinstance(src, dict) else src)
    src = src_path.read_text(encoding="utf-8-sig")

    w, h = FORMATS[fmt]
    content = video.get("content", {})
    brand_public = {k: v for k, v in brand.items() if k not in ("fonts", "assets", "voice", "notes", "about")}
    assets = asset_map(video, brand, vdir, bdir, fmt)

    # 글꼴: 실제로 쓰인 글자만 잘라서 넣음
    text_pool = src + json.dumps(content, ensure_ascii=False) + json.dumps(brand_public, ensure_ascii=False)
    used = {c for c in text_pool if ord(c) > 126} | {chr(c) for c in range(32, 127)} | set("·–—“”‘’…→✓")
    text = "".join(sorted(used))
    faces, covered = [], set()
    # 템플릿이 따로 쓰는 글꼴(templates/<이름>/template.json 의 fonts, 예: Geist·Archivo 가변 글꼴)도 함께 넣음
    tdir = ROOT / "templates" / (video.get("template") or "_none")
    tmeta = json.loads((tdir / "template.json").read_text(encoding="utf-8-sig")) if (tdir / "template.json").exists() else {}
    # 직접 짠 영상은 video.json 의 fonts 로 추가 글꼴을 고름 (파일은 영상 폴더나 스튜디오 폴더 기준, 예: fonts/Archivo-Variable.woff2)
    font_list = [(f, bdir) for f in brand.get("fonts", [])] + [(f, tdir) for f in tmeta.get("fonts", [])] + [(f, vdir) for f in video.get("fonts", []) or []]
    if style and video.get("styleFonts", True):
        font_list += [(f, ROOT) for f in style.get("fonts", []) or []]
    for f, base in font_list:
        data, cmap = subset_font(resolve(f["file"], base), text)
        covered |= set(cmap)
        stretch = f';font-stretch:{f["stretch"]}' if f.get("stretch") else ""
        faces.append(f'@font-face{{font-family:"{f["family"]}";font-weight:{f.get("weight", 400)};font-style:{f.get("style", "normal")}{stretch};'
                     f'font-display:block;src:url(data:font/woff2;base64,{base64.b64encode(data).decode()}) format("woff2")}}')
    content_chars = {c for c in json.dumps(content, ensure_ascii=False) if ord(c) > 126}
    missing = sorted(c for c in content_chars if ord(c) not in covered and c not in "·–—“”‘’…→✓")
    if missing:
        print(f"  경고: 브랜드 글꼴에 없는 글자 {''.join(missing)} → 다른 글꼴로 보일 수 있음")

    data = (f"window.__FORMAT={json.dumps({'key': fmt, 'w': w, 'h': h})};"
            f"window.__FPS={video.get('fps', 30)};"
            f"window.__BRAND={json.dumps(brand_public, ensure_ascii=False)};"
            f"window.__CONTENT={json.dumps(content, ensure_ascii=False)};"
            f"window.__SAFE_ZONE={json.dumps(video.get('safe', {}))};"
            f"window.__ASSETS={json.dumps(assets)};")
    look = dict(style.get("look") or {}) if video.get("styleLook", True) else {}   # styleLook=false 면 스타일 질감 끄기
    look.update(video.get("look") or {})
    look = {k: v for k, v in look.items() if v not in (None, False, 0, "")}
    if look:
        data += f"window.__LOOK={json.dumps(look, ensure_ascii=False)};"
    if style:
        pub = {k: style.get(k) for k in ("id", "name", "motion", "shape", "scenes") if style.get(k) is not None}
        data += f"window.__STYLE={json.dumps(pub, ensure_ascii=False)};"
    gsap = (ROOT / "vendor" / "gsap.min.js").read_text(encoding="utf-8-sig")
    rep = {
        "/*@TITLE@*/": video.get("title", name),
        "/*@FONTFACES@*/": "\n".join(faces),
        "/*@BRAND_CSS@*/": brand_css(brand) + style_css(style, video),
        "/*@ENGINE_CSS@*/": (ROOT / "engine" / "studio.css").read_text(encoding="utf-8-sig"),
        "/*@GSAP@*/": gsap,
        "/*@DATA@*/": data,
        "/*@ENGINE_JS@*/": (ROOT / "engine" / "studio.js").read_text(encoding="utf-8-sig") + "\n"
                           + (ROOT / "engine" / "motion.js").read_text(encoding="utf-8-sig"),
        "/*@ASSETS@*/": json.dumps(assets),  # 예전 방식(Bax 방콕 영상) 호환
    }
    out = src
    for k, v in rep.items():
        out = out.replace(k, v)
    out = GSAP_TAG.sub(lambda m: "<script>" + gsap + "</script>", out)
    if "/*@" in out:
        left = re.findall(r"/[*]@\w+@[*]/", out)
        sys.exit(f"채우지 못한 자리표시자가 있습니다: {left}")
    if not out.lstrip().lower().startswith("<!doctype"):
        out = ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
               '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>'
               + out + "</body></html>")
    target = out_dir(name, fmt) / f"{name}-{fmt}.html"
    target.write_text(out, encoding="utf-8")
    print(f"  {fmt:8s} → {target.relative_to(ROOT)} ({len(out.encode()) // 1024} KB)")
    return target


def build_video(name, formats=None):
    """형식별 HTML을 만들고 경로 목록을 돌려줌. formats: None(전부) | 'tall,square' | ['tall']"""
    video, brand, vdir = load_video(name)
    arg = ",".join(formats) if isinstance(formats, (list, tuple)) else formats
    return [build(name, fmt, video, brand, vdir) for fmt in formats_of(video, arg)]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    name = sys.argv[1]
    video, brand, vdir = load_video(name)
    print(f"빌드: {name} (브랜드 {brand.get('name', video['brand'])})")
    build_video(name, sys.argv[2] if len(sys.argv) > 2 else None)


if __name__ == "__main__":
    main()
