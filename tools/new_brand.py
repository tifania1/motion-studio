"""새 광고 계정(브랜드) 폴더를 만듭니다.

사용법:
    python tools/new_brand.py <슬러그> --name "브랜드 이름" [옵션]

옵션:
    --palette 이미지     로고·대표 사진에서 색을 뽑아 배경/강조색을 자동으로 정함
    --accent #RRGGBB     강조색 직접 지정 (버튼, 마커, 숫자)
    --bg #RRGGBB         배경색 직접 지정
    --light              밝은 배경으로 (기본은 어두운 배경)
    --logo 파일          로고 이미지 (투명 PNG 권장) → assets/logo.*
    --mascot 파일        마스코트·캐릭터 이미지 (투명 PNG) → assets/mascot.png
    --serif              제목 글꼴을 명조(Noto Serif KR)로

예)
    python tools/new_brand.py mint-pilates --name "민트 필라테스" --accent "#2BB673" --light
    python tools/new_brand.py ddong-bakery --name "똥빵 베이커리" --palette 로고.png --logo 로고.png

슬러그는 영문 소문자·숫자·하이픈만 씁니다. 결과: brands/<슬러그>/brand.json
"""
import colorsys
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from common import ROOT

ARGS_WITH_VALUE = ("--name", "--palette", "--accent", "--bg", "--logo", "--mascot")


def opt(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def hex2rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        sys.exit(f"색 형식이 이상합니다: {h} (#RRGGBB)")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb2hex(c):
    return "#{:02X}{:02X}{:02X}".format(*[max(0, min(255, round(v))) for v in c])


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in c)
    return .2126 * r + .7152 * g + .0722 * b


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + .05) / (lb + .05)


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def hls(c):
    return colorsys.rgb_to_hls(*(v / 255 for v in c))


def from_hls(h, l, s):
    return tuple(v * 255 for v in colorsys.hls_to_rgb(h, l, s))


def palette(path, n=8):
    im = Image.open(path).convert("RGBA")
    im.thumbnail((300, 300))
    arr = np.asarray(im).reshape(-1, 4)
    px = [tuple(int(v) for v in p[:3]) for p in arr[arr[:, 3] > 200]]
    if not px:
        sys.exit("팔레트를 뽑을 픽셀이 없습니다 (이미지가 거의 투명함).")
    flat = Image.new("RGB", (len(px), 1))
    flat.putdata(px)
    q = flat.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:n * 3]
    counts = sorted(q.getcolors(), reverse=True)
    return [(cnt / len(px), tuple(pal[i * 3:i * 3 + 3])) for cnt, i in counts]


def pick_accent(cols):
    best, score = None, -1
    for share, c in cols:
        h, l, s = hls(c)
        if l < .18 or l > .9:
            continue
        sc = s * (1 - abs(l - .55)) * (share ** .3)
        if sc > score:
            best, score = c, sc
    return best or (242, 140, 40)


def derive(accent, bg=None, light=False, msgs=None):
    h, l, s = hls(accent)
    if bg is None:
        bg = from_hls(h, .96, min(s, .35)) if light else from_hls(h, .1, min(s, .45))
    dark_bg = lum(bg) < .25
    white, black = (255, 255, 255), (17, 17, 17)
    on_bg = mix(white, from_hls(h, .95, .3), .5) if dark_bg else from_hls(h, .1, min(s, .4))
    paper = from_hls(h, .97, min(s, .4)) if dark_bg else from_hls(h, .12, min(s, .4))
    ink = from_hls(h, .1, min(s, .4)) if dark_bg else from_hls(h, .97, min(s, .4))
    accent_ink = black if contrast(accent, black) >= contrast(accent, white) else white
    original = accent
    step = .03 if dark_bg else -.03
    while contrast(accent, bg) < 3 and .05 < l < .95:  # 강조색이 배경에 묻히면 밝기를 조금씩 벌림
        l += step
        accent = from_hls(h, l, s)
    if accent != original:
        m = f"강조색을 배경과 구분되게 {rgb2hex(original)} → {rgb2hex(accent)} 로 조정했습니다. 원래 색을 꼭 써야 하면 브랜드 색에서 되돌리세요."
        (msgs.append(m) if msgs is not None else print("  " + m))
    accent_ink = black if contrast(accent, black) >= contrast(accent, white) else white
    ob = on_bg
    return {
        "bg": rgb2hex(bg),
        "onBg": rgb2hex(on_bg),
        "onBgMuted": "rgba({},{},{},.75)".format(*[round(v) for v in ob]),
        "paper": rgb2hex(paper),
        "ink": rgb2hex(ink),
        "accent": rgb2hex(accent),
        "accentInk": rgb2hex(accent_ink),
        "pattern": "rgba({},{},{},.08)".format(*[round(v) for v in ob]),
        "glow": "rgba({},{},{},.35)".format(*[round(v) for v in accent]),
    }


class BrandError(Exception):
    pass


def contrast_report(colors):
    c = {k: hex2rgb(v) for k, v in colors.items() if isinstance(v, str) and v.startswith("#")}
    out = []
    for a, b in (("onBg", "bg"), ("accentInk", "accent"), ("ink", "paper"), ("accent", "bg")):
        if a in c and b in c:
            out.append({"pair": f"{a}/{b}", "ratio": round(contrast(c[a], c[b]), 1)})
    return out


def create_brand(slug, name=None, accent=None, bg=None, light=False, palette_path=None, logo=None, mascot=None, serif=False):
    """brands/<slug>/brand.json 을 만들고 {brand, messages, palette, contrast} 를 돌려줌."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug or ""):
        raise BrandError("영문 이름(슬러그)은 영문 소문자, 숫자, 하이픈만 쓸 수 있습니다. 예) mint-pilates")
    bdir = ROOT / "brands" / slug
    if (bdir / "brand.json").exists():
        raise BrandError(f"이미 있는 브랜드입니다: {slug}")
    msgs = []
    brand = json.loads((ROOT / "brands" / "_template" / "brand.json").read_text(encoding="utf-8-sig"))
    name = name or slug
    brand["name"], brand["slug"] = name, slug
    brand["description"] = ""
    brand["voice"] = {"tone": ""}
    brand["about"] = []
    brand["notes"] = []
    brand["logoText"] = name
    brand["assets"] = {}

    cols = palette(palette_path) if palette_path else []
    acc = hex2rgb(accent) if accent else (pick_accent(cols) if cols else hex2rgb(brand["colors"]["accent"]))
    bgc = hex2rgb(bg) if bg else None
    brand["colors"] = derive(acc, bgc, light=light, msgs=msgs)
    if serif:
        brand["fonts"].append({"family": "BrandSerif", "weight": 900, "file": "fonts/NotoSerifKR-Black.woff2"})
        brand["type"]["heading"] = "BrandSerif"
        brand["type"]["display"] = "BrandSerif"

    for key, src in (("logo", logo), ("mascot", mascot)):   # 폴더를 만들기 전에 그림 파일부터 확인
        if src and Path(src).exists():
            try:
                Image.open(src).verify()
            except Exception:  # noqa: BLE001
                raise BrandError(f"{Path(src).name} 은 열 수 없는 그림이에요. JPG나 PNG로 바꿔서 넣어 주세요 (아이폰 HEIC, SVG 는 안 돼요).")
    (bdir / "assets").mkdir(parents=True, exist_ok=True)
    for key, src in (("logo", logo), ("mascot", mascot)):
        if not src:
            continue
        sp = Path(src)
        if not sp.exists():
            raise BrandError(f"파일이 없습니다: {src}")
        im = Image.open(sp)
        has_alpha = im.mode in ("RGBA", "LA") or "transparency" in im.info
        dst = bdir / "assets" / (key + (sp.suffix.lower() if key == "logo" else ".png"))
        if key == "mascot" and sp.suffix.lower() != ".png":
            im.convert("RGBA").save(dst)
        elif sp.resolve() != dst.resolve():
            shutil.copy(sp, dst)
        brand["assets"][key] = f"assets/{dst.name}"
        brand[key] = key
        if key == "logo":
            brand["logoText"] = ""
        if not has_alpha:
            msgs.append(f"{'로고' if key == 'logo' else '마스코트'} 이미지에 투명 배경이 없습니다. 배경 지우기를 쓰면 더 깔끔해요.")

    (bdir / "brand.json").write_text(json.dumps(brand, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"brand": brand, "messages": msgs, "palette": [{"hex": rgb2hex(c), "share": round(sh, 3)} for sh, c in cols],
            "contrast": contrast_report(brand["colors"])}


def main():
    pos = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] not in ARGS_WITH_VALUE]
    if not pos:
        sys.exit(__doc__)
    try:
        r = create_brand(pos[0], opt("--name"), opt("--accent"), opt("--bg"), "--light" in sys.argv, opt("--palette"),
                         opt("--logo"), opt("--mascot"), "--serif" in sys.argv)
    except BrandError as e:
        sys.exit(str(e))
    if r["palette"]:
        print("이미지에서 뽑은 색 (비율 순):")
        for c in r["palette"]:
            print(f"  {c['hex']}  {c['share'] * 100:4.1f}%")
    for m in r["messages"]:
        print("  " + m)
    b = r["brand"]
    print(f"\n브랜드 만듦: brands/{b['slug']}/brand.json")
    for k in ("bg", "onBg", "accent", "accentInk", "paper", "ink"):
        print(f"  {k:10s} {b['colors'][k]}")
    print("대비(4.5 이상 권장, 큰 제목은 3 이상):")
    for c in r["contrast"]:
        print(f"  {c['pair']}: {c['ratio']}{'' if c['ratio'] >= 3 else '  ← 낮음, 색을 조정하세요'}")
    print("\n다음: brand.json 의 description, voice(말투), notes(금지 표현·필수 문구)를 채우세요.")


if __name__ == "__main__":
    main()
