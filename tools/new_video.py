"""새 광고 영상 폴더를 만듭니다. 템플릿의 예시 내용(example.json)으로 채워 두니 문구만 바꾸면 됩니다.

사용법:
    python tools/new_video.py <영상이름> --brand <브랜드슬러그> [--template promo] [--formats tall,square] [--title "제목"]
    python tools/new_video.py <영상이름> --brand <브랜드슬러그> --preset <상황>     # 상황 프리셋으로 (python tools/presets.py 로 목록)
    python tools/new_video.py <영상이름> --brand <브랜드슬러그> --scratch "원하는 영상 설명"   # 템플릿 없이 처음부터 (Claude Code 가 짬, docs/SCRATCH.md)

템플릿:
    promo    사진 장면 + 장점 + 숫자 + CTA (기본)
    kinetic  사진 없이 글자만으로 (세일·이벤트·공지)
    scenes   장면 쌓기: 표지·문장·사진·숫자·목록·단계·비교·인용·그래프·사진 여러 장·로고 장면을 원하는 순서로
    그 밖의 템플릿은 templates/ 폴더와 docs/TEMPLATES.md 를 보세요.

상황 프리셋(--preset)을 쓰면 템플릿·예시 문구·형식·목표 길이·음악 힌트가 한 번에 채워지고,
연출 프롬프트가 videos/<영상>/direction.md 로 복사됩니다.

예)
    python tools/new_video.py mint-oct-trial --brand mint-pilates --template kinetic --formats tall,portrait
결과: videos/<영상이름>/video.json, videos/<영상이름>/photos/ (사진과 credits.json 자리)
"""
import json
import re
import sys

from common import FORMATS, ROOT


def opt(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


class VideoError(Exception):
    pass


def list_templates():
    return sorted(p.name for p in (ROOT / "templates").iterdir() if (p / "index.html").exists())


SCRATCH_DIRECTION = """# 처음부터 새로 짜는 영상 — 연출 프롬프트

이 영상은 템플릿 없이 이 영상만을 위해 처음부터 짭니다. 짜는 순서와 규칙은 docs/SCRATCH.md 를 따릅니다.

## 원하는 영상 (사용자가 적은 설명)
{brief}

## 형식
- 비율: {formats}
- 길이: 설명에 없으면 내용에 맞게 15~30초
- 파일: videos/{name}/scene.html 을 새로 짜고, 화면에 나오는 글·숫자·사진 키는 video.json 의 content 에 둡니다

## 확인할 것
- 설명에 없는 사실(가격·날짜·수치·이름)은 지어내지 말고 먼저 물어봅니다
- 네 비율 장면 모음(sheet)을 직접 열어 보고 글자 넘침·세이프존을 확인합니다
"""
FMT_KO = {"tall": "9:16", "portrait": "4:5", "square": "1:1", "wide": "16:9"}


def create_scratch(name, brand, brief, formats=None, title=None):
    """템플릿 없이 처음부터 짜는 영상 폴더. 시작 파일(engine/starter.html)과 연출 프롬프트(direction.md)를 둠."""
    brief = (brief or "").strip()
    if len(brief) < 5:
        raise VideoError("어떤 영상을 원하는지 한두 문장 적어 주세요. 예) 신제품 센서가 공장 설비에 붙어 데이터를 보내는 과정을 그림으로 보여 주는 20초 영상")
    formats = [f for f in (formats or list(FORMATS)) if f in FORMATS] or list(FORMATS)
    vdir = ROOT / "videos" / name
    (vdir / "photos").mkdir(parents=True, exist_ok=True)
    (vdir / "scene.html").write_text((ROOT / "engine" / "starter.html").read_text(encoding="utf-8-sig"), encoding="utf-8")
    first = brief.splitlines()[0].strip()
    if len(first) > 28:
        first = (first[:28].rsplit(" ", 1)[0] or first[:28]) + "…"
    video = {"title": title or name, "brand": brand, "fps": 30, "formats": formats, "safe": {"tall": "reels"},
             "src": "scene.html", "scratch": True, "brief": brief, "assets": {},
             "fonts": [{"family": "Archivo", "weight": "100 900", "stretch": "62% 125%", "file": "fonts/Archivo-Variable.woff2"}],
             "content": {"tag": "NEW VIDEO", "title": title or first, "sub": "Claude Code가 이 영상을 처음부터 짜면 이 화면이 바뀌어요"}}
    (vdir / "direction.md").write_text(SCRATCH_DIRECTION.format(brief=brief, formats=" · ".join(FMT_KO[f] for f in formats), name=name), encoding="utf-8")
    (vdir / "video.json").write_text(json.dumps(video, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cred = vdir / "photos" / "credits.json"
    if not cred.exists():
        cred.write_text("[]\n", encoding="utf-8")
    return video


def create_video(name, brand, template="promo", formats=None, title=None, preset=None, scratch=None):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name or ""):
        raise VideoError("영상 영문 이름은 영문 소문자, 숫자, 하이픈만 쓸 수 있습니다. 예) mint-oct-trial")
    brands = sorted(p.name for p in (ROOT / "brands").iterdir() if (p / "brand.json").exists() and not p.name.startswith("_"))
    if brand not in brands:
        raise VideoError(f"브랜드를 찾을 수 없습니다: {brand}")
    if (ROOT / "videos" / name / "video.json").exists():
        raise VideoError(f"이미 있는 영상입니다: {name}")
    if scratch is not None:
        return create_scratch(name, brand, scratch, formats, title)
    pr = None
    if preset:
        from presets import get_preset
        try:
            pr = get_preset(preset)
        except KeyError:
            raise VideoError(f"상황 프리셋 '{preset}' 이 없습니다.")
        template = pr["template"]
        if not formats:
            formats = pr.get("formats")
    tdir = ROOT / "templates" / template
    if not (tdir / "index.html").exists():
        raise VideoError(f"템플릿 '{template}' 이 없습니다. 있는 템플릿: {', '.join(list_templates())}")
    tmeta = json.loads((tdir / "template.json").read_text(encoding="utf-8-sig")) if (tdir / "template.json").exists() else {}
    allowed = tmeta.get("formats") or list(FORMATS)
    formats = [f for f in (formats or allowed) if f in allowed] or allowed
    for f in formats:
        if f not in FORMATS:
            raise VideoError(f"알 수 없는 형식: {f}")
    vdir = ROOT / "videos" / name
    if (vdir / "video.json").exists():
        raise VideoError(f"이미 있는 영상입니다: {name}")
    (vdir / "photos").mkdir(parents=True, exist_ok=True)
    example = json.loads((tdir / "example.json").read_text(encoding="utf-8-sig")) if (tdir / "example.json").exists() else {}
    video = {"title": title or name, "brand": brand, "template": template, "fps": 30, "formats": formats,
             "safe": {"tall": "reels"}, "assets": {}, "content": example}
    if pr:
        from presets import preset_content
        video["content"] = preset_content(pr)
        video["preset"] = pr["id"]
        if pr.get("seconds"):
            video["target"] = pr["seconds"]
        if pr.get("music"):
            video["musicHint"] = pr["music"]
        if pr.get("direction"):
            (vdir / "direction.md").write_text(pr["direction"], encoding="utf-8")
        if pr.get("style") and (ROOT / "styles" / pr["style"] / "style.json").exists():
            video["style"] = pr["style"]   # 결 템플릿 프리셋은 어울리는 스타일을 기본으로 (앱 연출 탭에서 바꿀 수 있음)
    (vdir / "video.json").write_text(json.dumps(video, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cred = vdir / "photos" / "credits.json"
    if not cred.exists():
        cred.write_text("[]\n", encoding="utf-8")
    return video


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        sys.exit(__doc__)
    name = sys.argv[1]
    if "--scratch" in sys.argv and not opt("--scratch"):
        sys.exit('--scratch 뒤에 원하는 영상 설명을 적어 주세요. 예) --scratch "센서가 데이터를 보내는 과정을 그림처럼 보여 주는 20초 영상"')
    template = opt("--template", "promo")
    formats = [f.strip() for f in opt("--formats", ",".join(FORMATS)).split(",")]
    try:
        video = create_video(name, opt("--brand"), template, formats if "--formats" in sys.argv else None, opt("--title"), opt("--preset"),
                             opt("--scratch") if "--scratch" in sys.argv else None)
        template = video.get("template")
    except VideoError as e:
        sys.exit(str(e))
    if not template:
        print(f"영상 만듦: videos/{name}/ (브랜드 {opt('--brand')}, 처음부터 짜기, 형식 {', '.join(video['formats'])})")
        print("다음: Claude Code 에서 \"videos/%s/direction.md 를 읽고 docs/SCRATCH.md 대로 이 영상을 처음부터 짜 줘\" 라고 부탁하세요." % name)
        return
    print(f"영상 만듦: videos/{name}/video.json (브랜드 {opt('--brand')}, 템플릿 {template}, 형식 {', '.join(video['formats'])})")
    steps = ["content 의 예시 문구를 실제 문구로 바꾸기"]
    if video.get("preset"):
        steps.insert(0, f"videos/{name}/direction.md 의 연출 프롬프트 읽기 (상황: {video['preset']})")
    if template == "promo":
        steps.append(f"사진 넣기: python tools/photo.py add {name} 파일.jpg --as photo1   (또는 photo.py search / get)")
    steps.append(f"python tools/check.py {name}  →  python tools/build.py {name}  →  python tools/render.py {name} all sheet")
    print("다음:")
    for i, s in enumerate(steps, 1):
        print(f"  {i}) {s}")


if __name__ == "__main__":
    main()
