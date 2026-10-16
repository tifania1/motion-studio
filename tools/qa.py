"""완성된 master.mp4 를 프레임 단위로 검사합니다.

사용법:
    python tools/qa.py <영상> [형식|all]

찾는 것
  - 튐: 한 프레임만 갑자기 크게 바뀌는 곳 (앞뒤 프레임 변화량의 3배 넘게 튀는 프레임). 전환이 한 프레임에 확 바뀌거나
    요소가 한 프레임 깜빡이는 실수를 잡습니다.
  - 멈춤: 화면이 1초 넘게 거의 안 움직이는 구간 (키노트 스타일에서는 1초 넘는 정지를 피함)
  - 루프: render.loop 가 true 면 마지막 프레임과 첫 프레임이 같은지
결과는 out/<영상>/<형식>/qa.json 과, 튄 프레임 앞·뒤를 붙인 qa-pops.png 로 저장합니다.
"""
import json
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

from common import ROOT, formats_of, load_video, out_dir

SIDE = 128


def frames(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    num, den = (r.stdout.strip() or "30/1").split("/")
    fps = float(num) / float(den or 1)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"scale={SIDE}:{SIDE},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.uint8).reshape(-1, SIDE, SIDE).astype(np.float32)
    return a, fps


def grab(path, idx, fps):
    t = idx / fps
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", str(path), "-frames:v", "1",
                        "-vf", "scale=320:-2", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    import io
    return Image.open(io.BytesIO(r.stdout)).convert("RGB")


def check(name, fmt, video):
    od = out_dir(name, fmt)
    path = od / "master.mp4"
    if not path.exists():
        print(f"  {fmt}: master.mp4 가 없어요. 먼저 python tools/render.py {name} {fmt} video")
        return None
    a, fps = frames(path)
    d = np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))            # 프레임 i→i+1 변화량 (0~255)
    pops = []
    for i in range(1, len(d) - 1):
        nb = max(d[i - 1], d[i + 1], .35)
        if d[i] > 3 * nb and d[i] > 2.0:
            pops.append({"frame": i + 1, "time": round((i + 1) / fps, 3), "diff": round(float(d[i]), 2),
                         "neighbours": [round(float(d[i - 1]), 2), round(float(d[i + 1]), 2)]})
    # 멈춤: 변화량이 아주 작은 프레임이 1초 넘게 이어짐
    still = d < .08
    holds, run = [], 0
    for i, s in enumerate(list(still) + [False]):
        if s:
            run += 1
        else:
            if run / fps > 1.0:
                holds.append({"from": round((i - run) / fps, 2), "to": round(i / fps, 2)})
            run = 0
    from render import render_cfg
    cfg = render_cfg(video)
    loop = None
    if cfg.get("loop"):
        ld = float(np.abs(a[-1] - a[0]).mean())
        step = float(np.median(d)) if len(d) else 0
        loop = {"lastToFirst": round(ld, 2), "typicalStep": round(step, 2), "ok": ld <= max(2.5, step * 2.5)}
    res = {"frames": int(len(a)), "fps": fps, "pops": pops, "holds": holds, "loop": loop,
           "maxDiff": round(float(d.max()), 2) if len(d) else 0}
    (od / "qa.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {fmt}: {len(a)}프레임 @ {fps:g}fps")
    print(f"    튐 {len(pops)}곳" + (": " + ", ".join(f"{p['time']}s(×{p['diff'] / max(max(p['neighbours']), .35):.1f})" for p in pops[:12]) if pops else ""))
    print(f"    1초 넘는 멈춤 {len(holds)}곳" + (": " + ", ".join(f"{h['from']}~{h['to']}s" for h in holds) if holds else ""))
    if loop:
        print(f"    루프: 끝→처음 변화 {loop['lastToFirst']} (보통 한 프레임 {loop['typicalStep']}) → {'자연스럽게 이어짐' if loop['ok'] else '이음새가 보일 수 있음'}")
    if pops:
        rows = pops[:8]
        sheet = Image.new("RGB", (3 * 326 + 6, len(rows) * (186 + 22) + 6), (24, 22, 30))
        dr = ImageDraw.Draw(sheet)
        for r_, p in enumerate(rows):
            for c, off in enumerate((-1, 0, 1)):
                im = grab(path, p["frame"] + off, fps)
                im.thumbnail((320, 180))
                x, y = 6 + c * 326, 6 + r_ * 208
                sheet.paste(im, (x, y + 22))
                dr.text((x, y + 4), f"{(p['frame'] + off) / fps:.3f}s" + ("  <- POP" if off == 0 else ""), fill=(255, 220, 120))
        sheet.save(od / "qa-pops.png")
        print(f"    튄 곳 이미지 → {(od / 'qa-pops.png').relative_to(ROOT)}")
    return res


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    video, _, _ = load_video(args[0])
    for fmt in formats_of(video, args[1] if len(args) > 1 else None):
        check(args[0], fmt, video)


if __name__ == "__main__":
    main()
