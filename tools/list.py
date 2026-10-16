"""브랜드(광고 계정)와 영상 목록, 각 영상의 작업 상태를 보여 줍니다.

사용법:
    python tools/list.py            # 전체
    python tools/list.py <브랜드>    # 그 브랜드의 영상만
"""
import json
import sys

from common import ROOT


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    brands = {}
    for p in sorted((ROOT / "brands").iterdir()):
        if (p / "brand.json").exists() and not p.name.startswith("_"):
            try:
                brands[p.name] = json.loads((p / "brand.json").read_text(encoding="utf-8-sig"))
            except Exception as e:  # noqa: BLE001  하나가 깨져도 목록은 보여 줌
                brands[p.name] = {"name": f"(brand.json 오류: {e})"}
    videos = []
    for p in sorted((ROOT / "videos").iterdir()):
        if (p / "video.json").exists():
            try:
                v = json.loads((p / "video.json").read_text(encoding="utf-8-sig"))
            except Exception as e:  # noqa: BLE001
                v = {"title": f"(video.json 오류: {e})"}
            videos.append((p.name, v))

    print("브랜드")
    for slug, b in brands.items():
        if only and slug != only:
            continue
        n = sum(1 for _, v in videos if v.get("brand") == slug)
        print(f"  {slug:22s} {b.get('name', '')}  · 영상 {n}개  {('— ' + b['description']) if b.get('description') else ''}")
    print("\n영상")
    for name, v in videos:
        if only and v.get("brand") != only:
            continue
        states = []
        for f in v.get("formats") or []:
            od = ROOT / "out" / name / f
            s = "완성" if (od / f"{name}_{f}.mp4").exists() else "마스터" if (od / "master.mp4").exists() else \
                "빌드" if (od / f"{name}-{f}.html").exists() else "-"
            states.append(f"{f}:{s}")
        print(f"  {name:26s} [{v.get('brand')}] {v.get('template') or '직접'} · {' '.join(states)}  {v.get('title', '')}")


if __name__ == "__main__":
    main()
