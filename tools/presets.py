"""상황 프리셋: 신메뉴 출시·세일·매장 오픈 같은 상황마다 템플릿, 예시 문구, 길이, 음악, 연출 프롬프트를 묶어 둔 것.

presets/<이름>/preset.json   상황 이름, 템플릿, 형식, 길이, 필요한 사진, 물어볼 정보, 문구 요청 예시, 음악
presets/<이름>/direction.md  연출 프롬프트 (장면·박자·전환·글·음악·확인할 것). 새 영상 폴더에 복사돼요.

사용법:
    python tools/presets.py                 # 상황 목록
    python tools/presets.py show <이름>      # 연출 프롬프트 보기
    python tools/new_video.py <영상> --brand <브랜드> --preset <이름>
"""
import json
import sys

from common import ROOT

PDIR = ROOT / "presets"


def list_presets(with_direction=False):
    out = []
    if not PDIR.is_dir():
        return out
    for d in sorted(PDIR.iterdir()):
        pj = d / "preset.json"
        if not pj.exists():
            continue
        try:
            p = json.loads(pj.read_text(encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        p["id"] = d.name
        tdir = ROOT / "templates" / p.get("template", "")
        if not (tdir / "index.html").exists():
            continue
        if with_direction and (d / "direction.md").exists():
            p["direction"] = (d / "direction.md").read_text(encoding="utf-8-sig")
        out.append(p)
    out.sort(key=lambda p: (p.get("order", 99), p["id"]))
    return out


def get_preset(pid):
    for p in list_presets(with_direction=True):
        if p["id"] == pid:
            return p
    raise KeyError(pid)


def preset_content(p):
    """프리셋 예시 문구. preset.json 의 content 가 없으면 템플릿 example.json."""
    if p.get("content"):
        return json.loads(json.dumps(p["content"]))
    ex = ROOT / "templates" / p["template"] / "example.json"
    return json.loads(ex.read_text(encoding="utf-8-sig")) if ex.exists() else {}


def main():
    args = sys.argv[1:]
    if args[:1] == ["show"] and len(args) > 1:
        try:
            p = get_preset(args[1])
        except KeyError:
            sys.exit(f"상황 '{args[1]}' 이 없어요. python tools/presets.py 로 목록을 보세요.")
        print(p.get("direction") or "(연출 프롬프트 없음)")
        return
    ps = list_presets()
    if not ps:
        sys.exit("presets 폴더에 상황이 없어요.")
    w = max(len(p["id"]) for p in ps)
    for p in ps:
        print(f"{p['id']:<{w}}  {p.get('name', ''):<10} {p.get('template', ''):<9} {p.get('seconds', '')}초  {p.get('look', '')}")


if __name__ == "__main__":
    main()
