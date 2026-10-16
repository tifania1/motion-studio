"""빌드된 HTML을 헤드리스 크로미움으로 한 프레임씩 찍습니다.

사용법:
    python tools/render.py <영상> <형식|all> sheet [--safe]     # 검수용 장면 모음 이미지 (sheet.png)
    python tools/render.py <영상> <형식|all> shots 1.5 4 8.2    # 지정 초의 장면 PNG
    python tools/render.py <영상> <형식|all> video              # 마스터 영상 master.mp4 (무음)
    python tools/render.py <영상> <형식|all> beats [묶음] [밀기]  # 박마다 한 장씩 찍은 검수 이미지 beats.png (묶음=2 면 2박마다, 밀기=0.5 면 반 박 뒤)

--safe 를 붙이면 플랫폼 UI가 덮는 영역(세이프존)을 빨간색으로 겹쳐 그립니다.
먼저 python tools/build.py <영상> 을 실행해야 합니다.

video.json 의 render 항목으로 품질을 정합니다 (없으면 30fps, 블러 없음):
    "render": {"fps": 60, "blur": 4, "shutter": 0.5, "scale": 1.3333, "loop": true}
    fps      초당 프레임
    blur     모션 블러용 서브프레임 수. 한 프레임을 이 수만큼 시간을 나눠 찍어 평균냅니다(4면 4배 오래 걸림)
    shutter  셔터 각(0.5 = 180°). 프레임 간격 중 얼마 동안의 움직임을 번지게 할지
    scale    해상도 배율. 1:1(1080)에 1.3333 이면 1440×1440
    loop     마지막 프레임이 첫 프레임으로 이어지는 영상이면 true (블러가 처음·끝에서 이어짐)
"""
import asyncio
import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

from common import FORMATS, ROOT, formats_of, load_video, out_dir


def render_cfg(video):
    import json
    tj = ROOT / "templates" / (video.get("template") or "_none") / "template.json"
    r = dict((json.loads(tj.read_text(encoding="utf-8-sig")).get("render") or {}) if tj.exists() else {})
    r.update(video.get("render") or {})
    r.setdefault("fps", video.get("fps", 30))
    r["blur"] = max(1, int(r.get("blur", 1)))
    r["shutter"] = float(r.get("shutter", .5))
    r["scale"] = float(r.get("scale", 1))
    r["loop"] = bool(r.get("loop", False))
    return r


async def open_page(p, html, fmt, safe, scale=1.0):
    w, h = FORMATS[fmt]
    browser = await p.chromium.launch(args=[f"--force-device-scale-factor={scale}"])
    page = await browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=scale)
    errors = []
    page.on("pageerror", lambda e: errors.append(f"페이지 오류: {e}"))
    page.on("console", lambda m: errors.append(f"콘솔 오류: {m.text}") if m.type == "error" else None)
    await page.add_init_script("window.__RENDER=true;" + ("window.__SAFE=true;" if safe else ""))
    await page.goto(html.as_uri())
    try:
        await page.wait_for_function("window.__ready===true", timeout=60000)
    except Exception:  # noqa: BLE001
        msg = "; ".join(errors[:3])
        await browser.close()
        sys.exit("미리보기 화면이 준비되지 않았어요 (60초). " + (f"페이지 오류: {msg}" if msg else "문구·사진 값을 확인하고 다시 해 주세요."))
    dur = await page.evaluate("window.__DURATION || 0")
    return browser, page, dur, errors


async def run(name, fmt, mode, times, safe, video):
    od = out_dir(name, fmt)
    html = od / f"{name}-{fmt}.html"
    snap = os.environ.get("MS_RENDER_HTML")   # 앱이 렌더용으로 떠 둔 사본 (미리보기가 같은 파일을 다시 써도 안전)
    if mode == "video" and snap and Path(snap).exists() and Path(snap).parent == od:
        html = Path(snap)
    if not html.exists():
        sys.exit(f"{html.relative_to(ROOT)} 이 없습니다. 먼저 python tools/build.py {name} 를 실행하세요.")
    cfg = render_cfg(video)
    fps = cfg["fps"]
    async with async_playwright() as p:
        browser, page, dur, errors = await open_page(p, html, fmt, safe, cfg["scale"] if mode == "video" else 1.0)
        if mode == "shots":
            sd = od / "shots"
            sd.mkdir(exist_ok=True)
            for t in times:
                await page.evaluate(f"window.__seek({t})")
                await page.screenshot(path=str(sd / f"t{t:06.2f}.png"))
            print(f"  {fmt}: {len(times)}장 → {sd.relative_to(ROOT)}")
        elif mode == "sheet":
            n = 12
            ts = [round(dur * (i + .5) / n, 2) for i in range(n)]
            thumbs = []
            for k, t in enumerate(ts, 1):
                await page.evaluate(f"window.__seek({t})")
                im = Image.open(io.BytesIO(await page.screenshot(type="png"))).convert("RGB")
                thumbs.append((t, im))
                print(f"  {fmt}: 장면 {k}/{n}", flush=True)
            w, h = FORMATS[fmt]
            tw = 360 if w <= h else 480
            th = round(tw * h / w)
            cols = 6 if w <= h else 4
            rows = (n + cols - 1) // cols
            sheet = Image.new("RGB", (cols * (tw + 8) + 8, rows * (th + 34) + 8), (24, 22, 30))
            d = ImageDraw.Draw(sheet)
            try:
                font = ImageFont.truetype("arial.ttf", 18)
            except Exception:
                font = ImageFont.load_default()
            for i, (t, im) in enumerate(thumbs):
                x, y = 8 + (i % cols) * (tw + 8), 8 + (i // cols) * (th + 34)
                sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y + 26))
                d.text((x, y + 4), f"{t:5.2f}s", fill=(255, 220, 120), font=font)
            path = od / ("sheet-safe.png" if safe else "sheet.png")
            sheet.save(path)
            print(f"  {fmt}: 길이 {dur:.2f}초, 장면 모음 → {path.relative_to(ROOT)}")
        elif mode == "beats":
            bpm = float((video.get("content") or {}).get("bpm") or (video.get("music") or {}).get("bpm") or 120)
            per = int(times[0]) if times else 1
            shift = float(times[1]) if len(times) > 1 else 0.0   # 박 사이를 보고 싶으면 0.5 (반 박 뒤)
            step = 60 / bpm * per
            ts = [round(k * step + shift * 60 / bpm, 4)
                  for k in range(int(dur / step + 1e-6) + 1) if k * step + shift * 60 / bpm < dur - 1e-3]
            w, h = FORMATS[fmt]
            tw = 240 if w <= h else 320
            th = round(tw * h / w)
            cols = 8 if w <= h else 6
            rows = (len(ts) + cols - 1) // cols
            sheet = Image.new("RGB", (cols * (tw + 6) + 6, rows * (th + 26) + 6), (24, 22, 30))
            d = ImageDraw.Draw(sheet)
            try:
                font = ImageFont.truetype("arial.ttf", 15)
            except Exception:
                font = ImageFont.load_default()
            for i, t in enumerate(ts):
                await page.evaluate(f"window.__seek({t})")
                im = Image.open(io.BytesIO(await page.screenshot(type="jpeg", quality=88))).convert("RGB")
                x, y = 6 + (i % cols) * (tw + 6), 6 + (i // cols) * (th + 26)
                sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y + 20))
                d.text((x, y + 3), f"#{i * per}  {t:5.2f}s", fill=(255, 220, 120), font=font)
                print(f"  {fmt}: 장면 {i + 1}/{len(ts)}", flush=True)
            path = od / "beats.png"
            sheet.save(path)
            print(f"  {fmt}: {bpm:g} BPM, {per}박마다 {len(ts)}장 → {path.relative_to(ROOT)}")
        else:
            if not shutil.which("ffmpeg"):
                sys.exit("ffmpeg를 찾을 수 없습니다.")
            import numpy as np
            target = od / "master.mp4"
            part = od / "master.part.mp4"   # 다 찍은 뒤에만 master.mp4 로 바꿔 둠 (중간에 끊기면 짧은 파일이 남지 않게)
            W, H = FORMATS[fmt]
            W, H = round(W * cfg["scale"]) // 2 * 2, round(H * cfg["scale"]) // 2 * 2
            nb, shutter, loop = cfg["blur"], cfg["shutter"], cfg["loop"]
            ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                   "-s", f"{W}x{H}", "-framerate", str(fps), "-i", "-",
                                   "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p",
                                   "-movflags", "+faststart", "-r", str(fps), str(part)], stdin=subprocess.PIPE)
            total = round(dur * fps)
            # 서브프레임 시각: 프레임 시각을 가운데에 두고 셔터 각만큼 펼침. 루프 영상은 처음·끝을 감아서 이음
            offs = [((k + .5) / nb - .5) * shutter / fps for k in range(nb)] if nb > 1 else [0.0]

            async def grab(t):
                if loop:
                    t = t % dur
                else:
                    t = min(max(t, 0.0), dur - 1e-4)
                await page.evaluate(f"window.__seek({t:.6f})")
                im = Image.open(io.BytesIO(await page.screenshot(type="jpeg", quality=96))).convert("RGB")
                if im.size != (W, H):
                    im = im.resize((W, H), Image.LANCZOS)
                return np.asarray(im, dtype=np.float32 if nb > 1 else np.uint8)

            t0 = __import__("time").time()
            for i in range(total):
                t = i / fps
                if nb > 1:
                    acc = None
                    for o in offs:
                        a = await grab(t + o)
                        acc = a if acc is None else acc + a
                    frame = np.clip(acc / nb + .5, 0, 255).astype(np.uint8)
                else:
                    frame = await grab(t)
                ff.stdin.write(frame.tobytes())
                if i % (fps * 2) == 0:
                    el = __import__("time").time() - t0
                    eta = el / max(i, 1) * (total - i)
                    print(f"  {fmt}: 프레임 {i}/{total}" + (f" (남은 시간 약 {eta / 60:.0f}분)" if i else ""), flush=True)
            ff.stdin.close()
            if ff.wait() != 0 or not part.exists():
                sys.exit(f"{fmt}: 영상 파일을 만들지 못했어요 (ffmpeg 오류). 디스크 공간을 확인하고 다시 해 주세요.")
            for k in range(10):
                try:
                    os.replace(part, target)
                    break
                except PermissionError:
                    if k == 9:
                        sys.exit(f"{target.name} 을 다른 프로그램(동영상 플레이어 등)이 쓰고 있어서 바꾸지 못했어요. 그 창을 닫고 다시 해 주세요.")
                    __import__("time").sleep(.5)
            print(f"  {fmt}: 완료 → {target.relative_to(ROOT)} ({dur:.2f}초, {W}×{H}, {fps}fps" + (f", 블러 {nb}" if nb > 1 else "") + ")")
        for e in errors:
            print("  " + e)
        await browser.close()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    safe = "--safe" in sys.argv
    if len(args) < 3 or args[2] not in ("shots", "sheet", "video", "beats"):
        sys.exit(__doc__)
    name, fmt_arg, mode = args[:3]
    video, _, _ = load_video(name)
    times = [float(x) for x in args[3:]]
    for fmt in formats_of(video, fmt_arg):
        asyncio.run(run(name, fmt, mode, times, safe, video))


if __name__ == "__main__":
    main()
