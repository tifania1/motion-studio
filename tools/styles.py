"""스타일 라이브러리: 잘 만든 모션에서 배운 보는 방식·움직이는 방식 (docs/STYLES.md).

styles/<이름>/style.json   색, 글꼴, 질감(look), 모양, 움직임, 장면 쌓기 모양
styles/<이름>/style.md     스타일 카드 (사람과 Claude 가 읽음)
styles/<이름>/thumb.jpg    앱의 스타일 고르기 썸네일

사용법:
    python tools/styles.py                    # 스타일 목록 (묶음별)
    python tools/styles.py show <이름>         # 스타일 카드 보기
    python tools/styles.py check [이름...]     # 값 점검 (빠진 항목, 글꼴 파일, 글자·바탕 대비, 전환 이름)
    python tools/styles.py thumbs [이름...]    # 썸네일 다시 만들기 (이름 없으면 썸네일이 없거나 오래된 것만, --all 이면 전부)
    python tools/new_video.py ... 뒤 video.json 에 "style": "<이름>" 또는 앱 연출 탭 → 스타일
"""
import json
import re
import sys

from common import ROOT

SDIR = ROOT / "styles"
GROUPS = ["타이포", "제품 UI", "그라디언트·빛", "3D·사물", "그래픽·도형", "레트로·픽셀", "손그림",
          "콜라주·사진", "다이어그램·데이터", "시네마틱"]
COLOR_KEYS = ["bg", "onBg", "onBgMuted", "paper", "ink", "accent", "accentInk", "pattern", "glow"]
LOOK_KEYS = {"paper", "paperTone", "fiber", "grain", "grainFps", "halftone", "halftoneSize", "dither", "ditherSize",
             "scanlines", "vignette", "tint", "tintMode", "tintAmount", "frame", "boil", "rgbSplit"}
TRANSITIONS = {"cut", "fade", "wipe", "iris", "push", "blades", "flood", "zoom", "blur", "whip", "blocks"}
SCENE_VALUES = {"bg": {"solid", "grid", "dots", "lines", "mesh", "aurora", "none"}, "align": {"center", "left"},
                "card": {"flat", "glass", "outline", "paper", "shadow"}, "marker": {"highlight", "underline", "circle", "color"},
                "case": {"none", "upper"},
                "title": {"rise", "type", "slot", "scramble", "blur", "pop", "mask", "write", "stamp", "fade"},
                "frame": {"none", "window", "browser", "phone", "panel", "terminal", "card", "poster"},
                "number": {"count", "odometer", "scramble"}}
DECO = {"cursor", "handles", "orb", "rings", "dots", "marks", "doodles", "stickers", "bubbles", "speedlines", "scribble", "shapes", "streaks", "ticker"}
# 썸네일·점검용 예시 (가상 브랜드 lumenta-demo 로 장면 쌓기 템플릿에 입혀 찍음)
SAMPLE = {"scenes": [
    {"type": "title", "kicker": "스타일 미리보기", "text": "보는 결이\n이렇게 달라요", "highlight": "달라요", "sub": "모션 스튜디오", "dur": 3},
    {"type": "compare", "text": "전과 후", "leftLabel": "그동안", "left": "같은 화면\n같은 움직임", "rightLabel": "이제는", "right": "브랜드마다\n다른 결", "dur": 3},
], "cta": "지금 골라 보세요", "ctaDur": 2}
THUMB_AT = (2.7, 5.7)
# 결 템플릿 10개: 스타일의 template 이 이 중 하나면 그 템플릿에 공통 예시(STORY)를 넣어 찍음. 두 장면을 찍을 시각(전체 길이 비율)
LOOK_TEMPLATES = {"typeslam": (.25, .74), "uidemo": (.25, .58), "sketchbook": (.12, .42), "dataflow": (.25, .74), "terminal": (.25, .58),
                  "collage": (.12, .58), "stage": (.12, .74), "glow": (.12, .42), "brandmark": (.12, .58), "cinema": (.12, .74)}
STORY = {"kicker": "새 기능", "title": "회의록은 이제\n알아서 정리돼요", "highlight": "알아서",
         "points": ["말하면 바로 받아 적고", "할 일만 골라 정리하고", "팀 채널로 바로 보내요"],
         "number": {"prefix": "하루", "value": 40, "suffix": "분", "label": "정리하는 시간을 아껴요", "source": "예시 수치"},
         "photos": [], "cta": {"headline": "다음 회의부터\n바로 써 보세요", "button": "무료로 시작", "sub": "example.com"}}


def _read(sid):
    p = SDIR / sid / "style.json"
    return json.loads(p.read_text(encoding="utf-8-sig"))


def list_styles(with_card=False):
    """스타일 목록. 이름이 _ 나 zz- 로 시작하는 폴더(시험용)는 빼요."""
    out = []
    if not SDIR.is_dir():
        return out
    for d in sorted(SDIR.iterdir()):
        if d.name.startswith(("_", ".", "zz-")) or not (d / "style.json").exists():
            continue
        try:
            s = _read(d.name)
        except Exception:  # noqa: BLE001
            continue
        s["id"] = d.name
        s["thumb"] = (d / "thumb.jpg").exists()
        if with_card and (d / "style.md").exists():
            s["card"] = (d / "style.md").read_text(encoding="utf-8-sig")
        out.append(s)
    gi = {g: i for i, g in enumerate(GROUPS)}
    out.sort(key=lambda s: (gi.get(s.get("group"), 99), s.get("name", s["id"])))
    return out


def get_style(sid, with_card=True):
    if not sid or not (SDIR / sid / "style.json").exists():
        raise KeyError(sid)
    s = _read(sid)
    s["id"] = sid
    s["thumb"] = (SDIR / sid / "thumb.jpg").exists()
    if with_card and (SDIR / sid / "style.md").exists():
        s["card"] = (SDIR / sid / "style.md").read_text(encoding="utf-8-sig")
    return s


def summary(s):
    """앱 목록용으로 줄인 값."""
    keys = ("id", "name", "group", "template", "summary", "tags", "hand", "palette", "thumb", "fits", "avoid", "signature")
    out = {k: s.get(k) for k in keys if s.get(k) is not None}
    out["colors"] = {k: (s.get("colors") or {}).get(k) for k in ("bg", "onBg", "accent")}
    out["look"] = sorted((s.get("look") or {}).keys())
    out["fonts"] = [f.get("family") for f in s.get("fonts") or []]
    return out


# ---------- 점검 ----------
def _rgb(c):
    """#hex · rgb() · rgba() → (r, g, b, a). 못 읽으면 None."""
    c = (c or "").strip()
    m = re.fullmatch(r"#([0-9a-fA-F]{3,8})", c)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(x * 2 for x in h)
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1
        return r, g, b, a
    m = re.fullmatch(r"rgba?\(([^)]*)\)", c)
    if m:
        parts = [x.strip() for x in m.group(1).replace("/", ",").split(",") if x.strip()]
        try:
            r, g, b = (float(x) for x in parts[:3])
            a = float(parts[3].rstrip("%")) / (100 if parts[3].endswith("%") else 1) if len(parts) > 3 else 1
            return r, g, b, a
        except ValueError:
            return None
    return None


def _over(fg, bg):
    a = fg[3]
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3)) + (1,)


def _lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4
    return .2126 * ch(c[0]) + .7152 * ch(c[1]) + .0722 * ch(c[2])


def contrast(fg, bg):
    f, b = _rgb(fg), _rgb(bg)
    if not f or not b:
        return None
    f = _over(f, b)
    hi, lo = sorted((_lum(f), _lum(b)), reverse=True)
    return (hi + .05) / (lo + .05)


def check_style(sid):
    """문제 목록 [(수준, 말)] — 수준은 '오류' 또는 '주의'."""
    probs = []
    err = lambda m: probs.append(("오류", m))
    warn = lambda m: probs.append(("주의", m))
    d = SDIR / sid
    try:
        s = _read(sid)
    except FileNotFoundError:
        return [("오류", "style.json 이 없어요")]
    except json.JSONDecodeError as e:
        return [("오류", f"style.json 을 읽지 못했어요: {e}")]
    if s.get("id") and s["id"] != sid:
        err(f"id '{s['id']}' 가 폴더 이름과 달라요")
    for k in ("name", "group", "summary", "colors", "motion", "scenes", "signature"):
        if not s.get(k):
            err(f"{k} 가 비었어요")
    if s.get("group") and s["group"] not in GROUPS:
        err(f"묶음 '{s['group']}' 은 없는 묶음이에요 ({' · '.join(GROUPS)})")
    if not (d / "style.md").exists():
        err("style.md(스타일 카드)가 없어요")
    if s.get("template") and not (ROOT / "templates" / s["template"] / "index.html").exists():
        err(f"template '{s['template']}' 템플릿이 없어요")
    col = s.get("colors") or {}
    for k in COLOR_KEYS:
        if k not in col:
            err(f"colors.{k} 가 없어요")
        elif not _rgb(col[k]):
            err(f"colors.{k} '{col[k]}' 를 색으로 읽지 못했어요 (#hex 나 rgba())")
    for fg, bg, need in (("onBg", "bg", 4.5), ("ink", "paper", 4.5), ("accentInk", "accent", 3), ("onBgMuted", "bg", 3)):
        if fg in col and bg in col:
            r = contrast(col[fg], col[bg])
            if r is not None and r < need:
                (err if r < need * .7 else warn)(f"{fg} 와 {bg} 대비가 {r:.1f} 이에요 ({need} 이상 권장)")
    for p in s.get("palette") or []:
        if not _rgb(p):
            err(f"palette 의 '{p}' 를 색으로 읽지 못했어요")
    fams = set()
    for f in s.get("fonts") or []:
        fams.add(f.get("family"))
        if not f.get("file") or not (ROOT / f["file"]).exists():
            err(f"글꼴 파일 {f.get('file')} 이 없어요")
    for role, v in (s.get("type") or {}).items():
        names = v if isinstance(v, list) else [v]
        for n in names:
            if n not in fams:
                err(f"type.{role} 의 '{n}' 이 fonts 에 없어요")
        hangul = any(re.search(r"KR|Nanum|Gaegu|Pretendard|Gothic|Myeongjo|Batang|Galmuri|Serif KR|Sans KR", n) for n in names)
        if not hangul:
            warn(f"type.{role} 에 한글 글꼴이 없어요 (한글은 브랜드 글꼴로 보여요)")
    for k, v in (s.get("look") or {}).items():
        if k not in LOOK_KEYS:
            err(f"look.{k} 는 엔진이 모르는 값이에요")
    lk = s.get("look") or {}
    if isinstance(lk.get("grain"), (int, float)) and lk["grain"] > .3:
        warn(f"grain {lk['grain']} 은 꽤 강해요 (0~0.3)")
    mo = s.get("motion") or {}
    for t in mo.get("transitions") or []:
        if t not in TRANSITIONS:
            err(f"motion.transitions 의 '{t}' 는 엔진에 없는 전환이에요 ({', '.join(sorted(TRANSITIONS))})")
    if mo.get("ease") and not re.fullmatch(r"(none|linear|(power[0-4]|sine|expo|circ|back|elastic|bounce|quad|cubic|quart|quint|strong)(\.(in|out|inOut)(\([\d.,\s]*\))?)?)", mo["ease"]):
        err(f"motion.ease '{mo['ease']}' 는 GSAP 이징 이름이 아니에요")
    if mo.get("stepped") and not (4 <= float(mo["stepped"]) <= 24):
        err("motion.stepped 는 4~24 (초당 장 수)")
    sc = s.get("scenes") or {}
    for k, allowed in SCENE_VALUES.items():
        if k in sc and sc[k] not in allowed:
            err(f"scenes.{k} '{sc[k]}' 는 없는 값이에요 ({' · '.join(sorted(allowed))})")
    deco = sc.get("deco") or []
    if not isinstance(deco, list) or any(x not in DECO for x in deco):
        err(f"scenes.deco 는 {' · '.join(sorted(DECO))} 중에서 고른 목록이에요")
    elif len(deco) > 3:
        warn("scenes.deco 는 3개까지만 쓰여요")
    if "scale" in sc and not (isinstance(sc["scale"], (int, float)) and .7 <= sc["scale"] <= 1.6):
        err("scenes.scale 은 0.8~1.4 숫자")
    if "schemes" in sc and (not isinstance(sc["schemes"], list) or any(x not in ("dark", "accent", "paper") for x in sc["schemes"])):
        err("scenes.schemes 는 dark·accent·paper 로 된 목록이에요")
    if s.get("hand") and not (lk.get("boil") or sc.get("rough") or mo.get("stepped")):
        warn("손그림 스타일인데 boil·rough·stepped 가 하나도 없어요")
    if not (d / "thumb.jpg").exists():
        warn("thumb.jpg 가 없어요 (python tools/styles.py thumbs)")
    return probs


# ---------- 썸네일 ----------
def make_thumbs(ids, log=print):
    """스타일마다 장면 쌓기 예시를 두 장면 찍어 styles/<이름>/thumb.jpg (720×360)."""
    import asyncio
    import io
    import shutil

    from PIL import Image
    from playwright.async_api import async_playwright

    import build as B
    from common import load_json

    brand = load_json(ROOT / "brands" / "lumenta-demo" / "brand.json")
    import os
    tmp = ROOT / "out" / f"_styles-{os.getpid()}"   # 여러 개를 동시에 돌려도 안 겹치게
    vdir = tmp / "video"
    vdir.mkdir(parents=True, exist_ok=True)
    pages = []
    for sid in ids:
        tpl = (_read(sid).get("template") or "scenes")
        look = tpl in LOOK_TEMPLATES and (ROOT / "templates" / tpl / "index.html").exists()
        video = {"title": f"스타일 {sid}", "brand": "lumenta-demo", "template": tpl if look else "scenes", "formats": ["square"],
                 "style": sid, "styleColors": True, "content": json.loads(json.dumps(STORY if look else SAMPLE))}
        html = B.build(tmp.name, "square", video, brand, vdir)
        keep = tmp / f"{sid}.html"
        shutil.copyfile(html, keep)
        pages.append((sid, keep, LOOK_TEMPLATES.get(tpl) if look else None))

    async def run():
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1080, "height": 1080})
            await page.add_init_script("window.__RENDER=true;")
            for sid, html, fr in pages:
                await page.goto(html.as_uri())
                await page.wait_for_function("window.__ready===true", timeout=60000)
                dur = await page.evaluate("window.__DURATION || 0")
                ims = []
                for t in ([dur * f for f in fr] if fr else THUMB_AT):
                    await page.evaluate(f"window.__seek({t})")
                    ims.append(Image.open(io.BytesIO(await page.screenshot(type="png"))).convert("RGB").resize((360, 360), Image.LANCZOS))
                sheet = Image.new("RGB", (720, 360))
                for i, im in enumerate(ims):
                    sheet.paste(im, (i * 360, 0))
                out = SDIR / sid / "thumb.jpg"
                sheet.save(out, quality=84, optimize=True, progressive=True)
                log(f"  {sid}: 썸네일 → {out.relative_to(ROOT)}")
            await browser.close()

    asyncio.run(run())
    shutil.rmtree(tmp, ignore_errors=True)


def _stale(sid):
    d = SDIR / sid
    th = d / "thumb.jpg"
    return not th.exists() or th.stat().st_mtime < (d / "style.json").stat().st_mtime


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args[:1] == ["show"] and len(args) > 1:
        try:
            s = get_style(args[1])
        except KeyError:
            sys.exit(f"스타일 '{args[1]}' 이 없어요. python tools/styles.py 로 목록을 보세요.")
        print(s.get("card") or json.dumps(s, ensure_ascii=False, indent=2))
        return
    if args[:1] == ["check"]:
        ids = args[1:] or [s["id"] for s in list_styles()]
        bad = 0
        for sid in ids:
            probs = check_style(sid)
            errs = [m for lv, m in probs if lv == "오류"]
            bad += bool(errs)
            mark = "✗" if errs else ("!" if probs else "✓")
            print(f"{mark} {sid}")
            for lv, m in probs:
                print(f"    {lv}: {m}")
        print(f"\n{len(ids)}개 중 {len(ids) - bad}개 통과")
        sys.exit(1 if bad else 0)
    if args[:1] == ["thumbs"]:
        ids = args[1:] or [s["id"] for s in list_styles() if "--all" in sys.argv or _stale(s["id"])]
        if not ids:
            print("썸네일이 모두 최신이에요 (--all 로 전부 다시 만들 수 있어요)")
            return
        print(f"썸네일 {len(ids)}개 만들기")
        make_thumbs(ids)
        return
    ss = list_styles()
    if not ss:
        sys.exit("styles 폴더에 스타일이 없어요.")
    w = max(len(s["id"]) for s in ss)
    group = None
    for s in ss:
        if s.get("group") != group:
            group = s.get("group")
            print(f"\n[{group}]")
        print(f"  {s['id']:<{w}}  {s.get('name', '')}{' (손그림)' if s.get('hand') else ''}")
    print(f"\n모두 {len(ss)}개 · 손그림 {sum(1 for s in ss if s.get('hand'))}개")


if __name__ == "__main__":
    main()
