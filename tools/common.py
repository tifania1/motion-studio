"""공용 경로·설정 읽기."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMATS = {
    "tall": (1080, 1920),      # 9:16 릴스·쇼츠·틱톡·스토리
    "portrait": (1080, 1350),  # 4:5 피드
    "square": (1080, 1080),    # 1:1 피드
    "wide": (1920, 1080),      # 16:9 유튜브
}

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def load_json(path: Path) -> dict:
    # utf-8-sig: 메모장·PowerShell 5.1 로 저장하면 붙는 BOM 도 읽음
    return json.loads(path.read_text(encoding="utf-8-sig"))


def video_dir(name: str) -> Path:
    d = ROOT / "videos" / name
    if not (d / "video.json").exists():
        names = sorted(p.name for p in (ROOT / "videos").iterdir() if (p / "video.json").exists())
        sys.exit(f"영상 '{name}' 을 찾을 수 없습니다. 있는 영상: {', '.join(names) or '(없음)'}")
    return d


def load_video(name: str) -> tuple[dict, dict, Path]:
    vdir = video_dir(name)
    video = load_json(vdir / "video.json")
    bdir = ROOT / "brands" / video["brand"]
    if not (bdir / "brand.json").exists():
        sys.exit(f"브랜드 '{video['brand']}' 를 찾을 수 없습니다 (brands/{video['brand']}/brand.json).")
    brand = load_json(bdir / "brand.json")
    return video, brand, vdir


def formats_of(video: dict, arg: str | None) -> list[str]:
    allowed = video.get("formats") or list(FORMATS)
    if not arg or arg == "all":
        return allowed
    out = [f.strip() for f in arg.split(",")]
    for f in out:
        if f not in FORMATS:
            sys.exit(f"알 수 없는 형식: {f} (tall, portrait, square, wide)")
    return out


def out_dir(name: str, fmt: str) -> Path:
    d = ROOT / "out" / name / fmt
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve(path: str, *bases: Path) -> Path:
    for b in (*bases, ROOT):
        p = (b / path)
        if p.exists():
            return p
    sys.exit(f"파일을 찾을 수 없습니다: {path}")
