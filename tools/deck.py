"""발표 자료(deck 템플릿) 도구.

    python tools/deck.py pdf <발표>            # 장마다 등장이 끝난 화면을 모아 PDF (out/<발표>/wide/<발표>.pdf)
    python tools/deck.py sheet <발표>          # 검수용: 모든 장의 마지막 화면을 한 장에 (out/<발표>/wide/slides.png)
    python tools/deck.py extract <파일> [--out 폴더]   # PPTX·PDF·DOCX·HWPX·TXT·MD 에서 글(과 PPTX·DOCX 사진)을 뽑음
    python tools/deck.py source <발표> <파일>  # 위 extract 결과를 videos/<발표>/source.md 와 사진으로 넣음 (Claude 가 구성할 때 읽음)

먼저 python tools/build.py <발표> 를 실행해야 PDF·sheet 를 만들 수 있어요.
발표 화면 자체는 out/<발표>/wide/<발표>-wide.html 한 파일이에요. 브라우저로 열고 F5(전체 화면) → 클리커로 넘기면 돼요.
"""
import asyncio
import io
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from common import ROOT, load_json, out_dir

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
MAX_TEXT = 60000


# ------------------------------------------------------------------ 화면 찍기
async def _shots(name, scale=1.0):
    from playwright.async_api import async_playwright
    from PIL import Image
    html = out_dir(name, "wide") / f"{name}-wide.html"
    if not html.exists():
        sys.exit(f"{html.relative_to(ROOT)} 이 없어요. 먼저 python tools/build.py {name} 을 실행하세요.")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=scale)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        await page.add_init_script("window.__RENDER=true;")
        await page.goto(html.as_uri())
        try:
            await page.wait_for_function("window.__ready===true", timeout=60000)
        except Exception:  # noqa: BLE001
            await browser.close()
            sys.exit("발표 화면이 준비되지 않았어요. " + ("; ".join(errors[:2]) or "문구 값을 확인해 주세요."))
        stops = await page.evaluate("window.__STOPS || []")
        if not stops:
            await browser.close()
            sys.exit("발표 자료(deck 템플릿)가 아니에요.")
        ims = []
        for t in stops:
            await page.evaluate(f"window.__seek({t})")
            await page.wait_for_timeout(30)
            ims.append(Image.open(io.BytesIO(await page.screenshot(type="png"))).convert("RGB"))
        await browser.close()
        if errors:
            print("  페이지 오류: " + "; ".join(errors[:3]))
        return ims


def make_pdf(name):
    ims = asyncio.run(_shots(name, 2.0))   # 3840×2160 로 찍어 확대해도 또렷하게
    out = out_dir(name, "wide") / f"{name}.pdf"
    ims[0].save(out, "PDF", save_all=True, append_images=ims[1:], resolution=288)
    print(f"PDF {len(ims)}장 → {out.relative_to(ROOT)}")
    return out, len(ims)


def make_sheet(name):
    from PIL import Image, ImageDraw
    ims = asyncio.run(_shots(name, .5))
    cols = 3 if len(ims) > 4 else 2
    w, h = 640, 360
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w + (cols + 1) * 12, rows * (h + 34) + 12), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    for i, im in enumerate(ims):
        x, y = 12 + (i % cols) * (w + 12), 12 + (i // cols) * (h + 34)
        sheet.paste(im.resize((w, h), Image.LANCZOS), (x, y))
        d.text((x + 4, y + h + 8), f"{i + 1}", fill=(230, 230, 230))
    out = out_dir(name, "wide") / "slides.png"
    sheet.save(out)
    print(f"장 모음 {len(ims)}장 → {out.relative_to(ROOT)}")
    return out, len(ims)


# ------------------------------------------------------------------ 글 뽑기
def _xml_text(data, para_tags, text_tags):
    """XML 에서 문단마다 글을 모음 (태그 이름은 네임스페이스를 뺀 끝부분으로 비교)."""
    out = []
    try:
        rootx = ET.fromstring(data)
    except ET.ParseError:
        return out
    for el in rootx.iter():
        if el.tag.rsplit("}", 1)[-1] in para_tags:
            s = "".join((t.text or "") for t in el.iter() if t.tag.rsplit("}", 1)[-1] in text_tags).strip()
            if s:
                out.append(s)
    return out


def _num(name):
    m = re.search(r"(\d+)", Path(name).stem)
    return int(m.group(1)) if m else 0


def _rels(z, names, part):
    """part(예: ppt/slides/slide3.xml)의 관계 파일을 {id: (종류, 경로)} 로."""
    d, f = part.rsplit("/", 1)
    rp = f"{d}/_rels/{f}.rels"
    out = {}
    if rp not in names:
        return out
    for el in ET.fromstring(z.read(rp)):
        tgt = el.get("Target", "")
        full = tgt.lstrip("/") if tgt.startswith("/") else str(Path(d, tgt).as_posix())
        parts = []
        for seg in full.split("/"):   # ../ 정리
            if seg == "..":
                parts and parts.pop()
            elif seg and seg != ".":
                parts.append(seg)
        out[el.get("Id")] = (el.get("Type", "").rsplit("/", 1)[-1], "/".join(parts))
    return out


def _rel_target(z, names, part, kind):
    for k, p in _rels(z, names, part).values():
        if k == kind and p in names:
            return p
    return None


def _pptx_order(z, names):
    """발표 순서대로 장 파일 목록 (presentation.xml 의 sldIdLst). 못 읽으면 파일 번호 순."""
    try:
        rels = _rels(z, names, "ppt/presentation.xml")
        order = []
        for el in ET.fromstring(z.read("ppt/presentation.xml")).iter():
            if el.tag.rsplit("}", 1)[-1] == "sldId":
                rid = next((v for k, v in el.attrib.items() if k.endswith("}id")), None)
                if rid in rels and rels[rid][1] in names:
                    order.append(rels[rid][1])
        if order:
            return order
    except Exception:  # noqa: BLE001
        pass
    return sorted([n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)], key=_num)


def extract_pptx(path, img_dir=None):
    parts, imgs = [], []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        slides = _pptx_order(z, names)
        for i, n in enumerate(slides, 1):
            lines = _xml_text(z.read(n), {"p"}, {"t"})
            notes_n = _rel_target(z, names, n, "notesSlide")
            notes = _xml_text(z.read(notes_n), {"p"}, {"t"}) if notes_n else []
            notes = [x for x in notes if not re.fullmatch(r"\d+", x)]
            parts.append(f"## {i}장\n" + "\n".join(lines) + (("\n(발표 메모) " + " / ".join(notes)) if notes else ""))
        if img_dir:
            imgs = _save_images(z, [n for n in names if n.startswith("ppt/media/")], img_dir)
    return "\n\n".join(parts), imgs


def extract_docx(path, img_dir=None):
    with zipfile.ZipFile(path) as z:
        lines = _xml_text(z.read("word/document.xml"), {"p"}, {"t"})
        imgs = _save_images(z, [n for n in z.namelist() if n.startswith("word/media/")], img_dir) if img_dir else []
    return "\n".join(lines), imgs


def extract_hwpx(path, img_dir=None):
    with zipfile.ZipFile(path) as z:
        secs = sorted([n for n in z.namelist() if re.fullmatch(r"Contents/section\d+\.xml", n)], key=_num)
        lines = []
        for n in secs:
            lines += _xml_text(z.read(n), {"p"}, {"t"})
        imgs = _save_images(z, [n for n in z.namelist() if n.startswith("BinData/")], img_dir) if img_dir else []
    return "\n".join(lines), imgs


def extract_pdf(path, img_dir=None):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("PDF 글을 읽으려면 pypdf 가 필요해요 (pip install pypdf). PPTX·DOCX·TXT 는 바로 돼요.")
    r = PdfReader(str(path))
    parts = []
    for i, pg in enumerate(r.pages, 1):
        t = (pg.extract_text() or "").strip()
        if t:
            parts.append(f"## {i}쪽\n{t}")
    return "\n\n".join(parts), []


def _save_images(z, members, img_dir, limit=12):
    """문서 안 사진 중 쓸 만한 것(짧은 변 360px 이상)만 크기순으로 limit 장 저장."""
    from PIL import Image
    got = []
    for n in members:
        if Path(n).suffix.lower() not in IMG_EXT:
            continue
        try:
            data = z.read(n)
            im = Image.open(io.BytesIO(data))
            im.load()
        except Exception:  # noqa: BLE001  (깨진 그림·지원 안 하는 형식은 건너뜀)
            continue
        if min(im.size) < 360:
            continue
        got.append((im.size[0] * im.size[1], n, im))
    got.sort(key=lambda x: -x[0])
    out = []
    img_dir = Path(img_dir)
    img_dir.mkdir(parents=True, exist_ok=True)
    for k, (_, n, im) in enumerate(got[:limit], 1):
        p = img_dir / f"source{k}.jpg"
        im.convert("RGB").save(p, quality=90)
        out.append(p)
    return out


def extract(path, img_dir=None):
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".pptx":
        text, imgs = extract_pptx(path, img_dir)
    elif ext == ".docx":
        text, imgs = extract_docx(path, img_dir)
    elif ext == ".hwpx":
        text, imgs = extract_hwpx(path, img_dir)
    elif ext == ".pdf":
        text, imgs = extract_pdf(path, img_dir)
    elif ext in (".txt", ".md", ".csv"):
        raw = path.read_bytes()
        for enc in ("utf-8-sig", "cp949", "utf-16"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = raw.decode("utf-8", "replace")
        imgs = []
    elif ext in (".ppt", ".doc", ".hwp"):
        raise RuntimeError("예전 형식(.ppt·.doc·.hwp)은 읽지 못해요. PowerPoint·Word·한글에서 다른 이름으로 저장(.pptx·.docx·.hwpx 또는 PDF)한 뒤 넣어 주세요.")
    else:
        raise RuntimeError(f"이 형식은 읽지 못해요: {ext} (PPTX·PDF·DOCX·HWPX·TXT·MD)")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text and not imgs:
        raise RuntimeError("파일에서 글을 찾지 못했어요. 스캔한 PDF 처럼 글이 그림으로만 들어 있으면 읽을 수 없어요.")
    return text[:MAX_TEXT], imgs


def add_source(name, file, display=None):
    """자료 파일을 발표 폴더에 넣음: source.md(뽑은 글), photos/source*.jpg + video.json assets 등록."""
    vdir = ROOT / "videos" / name
    vj = vdir / "video.json"
    if not vj.exists():
        raise RuntimeError(f"발표 '{name}' 이 없어요")
    file = Path(file)
    display = display or file.name
    tmp = vdir / "_src_imgs"
    shutil.rmtree(tmp, ignore_errors=True)
    text, imgs = extract(file, tmp)
    v = load_json(vj)
    assets = v.setdefault("assets", {})
    pdir = vdir / "photos"
    pdir.mkdir(exist_ok=True)
    keys = []
    k = 1
    for p in imgs:
        while f"source{k}" in assets:
            k += 1
        dst = pdir / f"source{k}.jpg"
        shutil.move(str(p), dst)
        assets[f"source{k}"] = f"photos/source{k}.jpg"
        keys.append(f"source{k}")
        k += 1
    shutil.rmtree(tmp, ignore_errors=True)
    if keys:
        cj = pdir / "credits.json"
        cr = load_json(cj) if cj.exists() else []
        cr = [x for x in cr if x.get("key") not in keys]
        for key in keys:
            cr.append({"file": f"{key}.jpg", "key": key, "title": f"{display} 안의 그림", "author": "", "license": "사용자 제공",
                       "license_url": "", "source_page": "", "credit_line": ""})
        cj.write_text(json.dumps(cr, ensure_ascii=False, indent=2), encoding="utf-8")
    head = f"# 자료: {display}\n\n"
    (vdir / "source.md").write_text(head + text, encoding="utf-8")
    v["source"] = display
    vj.write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"chars": len(text), "images": keys, "file": display}


def main():
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "pdf":
        make_pdf(a[1])
    elif len(a) >= 2 and a[0] == "sheet":
        make_sheet(a[1])
    elif len(a) >= 2 and a[0] == "extract":
        out = a[a.index("--out") + 1] if "--out" in a else None
        try:
            text, imgs = extract(a[1], out)
        except RuntimeError as e:
            sys.exit(str(e))
        print(text)
        if imgs:
            print(f"\n(사진 {len(imgs)}장 → {Path(out)})")
    elif len(a) >= 3 and a[0] == "source":
        try:
            r = add_source(a[1], a[2])
        except RuntimeError as e:
            sys.exit(str(e))
        print(f"자료를 넣었어요: 글 {r['chars']}자, 사진 {len(r['images'])}장 → videos/{a[1]}/source.md")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
