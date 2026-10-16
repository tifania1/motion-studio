"""이미지 배경을 지워 투명 PNG로 만듭니다 (로고, 마스코트, 제품 사진).

사용법:
    python tools/cutout.py <입력 이미지> <출력.png> [--model isnet-general-use] [--all]
    python tools/cutout.py <입력 이미지> <출력.png> --simple    # AI 없이: 가장자리와 이어진 배경색만 지움 (흰 배경 로고 등)

    --model   rembg 모델. 사람·캐릭터·제품 모두 isnet-general-use(기본)가 무난합니다.
              애니·일러스트 캐릭터는 isnet-anime 이 나을 때가 있습니다.
    --all     작은 조각도 남김 (기본은 가장 큰 덩어리와 그 3% 이상 크기 조각만 남김)

처음 실행할 때 모델(수십~170MB)을 내려받습니다. 필요한 패키지:
    pip install -r requirements-tools.txt
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def simple_cutout(src, dst, tol=38):
    """AI 없이 배경 지우기: 가장자리 색(배경)과 비슷하고 가장자리와 이어진 부분만 투명하게. 단색 배경 로고·캐릭터용."""
    im = Image.open(src).convert("RGBA")
    a = np.asarray(im).astype(np.int16)
    rgb, alpha0 = a[:, :, :3], a[:, :, 3]
    h, w = alpha0.shape
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    bg = np.median(border, axis=0)
    dist = np.sqrt(((rgb - bg) ** 2).sum(axis=2))
    near = ((dist < tol) | (alpha0 < 10)).astype(np.uint8) * 255
    m = Image.fromarray(near, "L").copy()  # 배열과 메모리를 나누지 않게 (floodfill 이 안 먹는 경우가 있음)
    step = max(1, min(w, h) // 60)
    seeds = [(x, 0) for x in range(0, w, step)] + [(x, h - 1) for x in range(0, w, step)] + \
            [(0, y) for y in range(0, h, step)] + [(w - 1, y) for y in range(0, h, step)]
    for xy in seeds:
        if m.getpixel(xy) == 255:
            ImageDraw.floodfill(m, xy, 128)
    bgmask = np.asarray(m) == 128
    soft = np.asarray(Image.fromarray((~bgmask).astype(np.uint8) * 255, "L").filter(ImageFilter.GaussianBlur(1.0)))
    out = np.asarray(im).copy()
    out[:, :, 3] = np.minimum(alpha0, soft).astype(np.uint8)
    ys, xs = np.where(out[:, :, 3] > 10)
    if not len(xs):
        sys.exit("배경과 그림을 구분하지 못했어요. 배경이 단색이 아닌 사진은 직접 지운 PNG를 넣어 주세요.")
    out = out[max(ys.min() - 4, 0):ys.max() + 5, max(xs.min() - 4, 0):xs.max() + 5]
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out).save(dst)
    print(f"저장(단순 방식): {dst} ({out.shape[1]}x{out.shape[0]}, 투명 배경)")


def main():
    args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] != "--model"]
    if len(args) < 2:
        sys.exit(__doc__)
    src, dst = Path(args[0]), Path(args[1])
    if "--simple" in sys.argv:
        return simple_cutout(src, dst)
    try:
        from rembg import new_session, remove
    except ImportError:
        sys.exit("rembg 가 없습니다. 먼저 실행: pip install -r requirements-tools.txt (또는 --simple)")
    model = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "isnet-general-use"
    im = Image.open(src).convert("RGB")
    scale = 2 if max(im.size) < 1200 else 1
    if scale > 1:
        im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
    out = np.array(remove(im, session=new_session(model), post_process_mask=True))
    alpha = out[:, :, 3]
    if "--all" not in sys.argv:
        try:
            import cv2
            mask = (alpha > 20).astype(np.uint8)
            n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
            if n > 1:
                areas = stats[1:, cv2.CC_STAT_AREA]
                keep = np.isin(lab, [i + 1 for i, a in enumerate(areas) if a >= .03 * areas.max()])
                out[:, :, 3] = (alpha * keep).astype(np.uint8)
        except ImportError:
            pass
    ys, xs = np.where(out[:, :, 3] > 10)
    if not len(xs):
        sys.exit("남은 부분이 없습니다. 다른 --model 로 해 보세요.")
    out = out[max(ys.min() - 4, 0):ys.max() + 5, max(xs.min() - 4, 0):xs.max() + 5]
    dst.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out).save(dst)
    print(f"저장: {dst} ({out.shape[1]}x{out.shape[0]}, 투명 배경)")


if __name__ == "__main__":
    main()
