"""빌드 전에 영상 설정을 점검합니다. 빠진 파일, 너무 긴 문구, 출처 누락, 근거가 필요한 광고 표현을 찾아 알려 줍니다.

사용법:
    python tools/check.py <영상>

결과의 '오류'는 빌드가 안 되거나 화면이 깨지는 문제, '확인'은 사람이 판단해야 할 부분입니다.
"""
import json
import re
import sys

from common import FORMATS, ROOT, load_video, resolve

# 표시광고법·플랫폼 광고 정책에서 근거를 요구하거나 자주 반려되는 표현
RISKY = ["최고", "최초", "최상", "1위", "넘버원", "유일", "100%", "무조건", "완벽", "완치", "치료", "보장", "부작용 없",
         "효과 확실", "평생", "공짜", "무료", "최저가", "가장 싼", "국내 유일", "세계 최초", "다이어트 효과", "살 빠지"]
# 문구 길이 권장(글자 수, 줄바꿈 제외). 넘으면 글자가 많이 작아짐
LIMITS = {"hook.headline": 24, "hook.kicker": 14, "visuals.title": 18, "visuals.sub": 22, "benefits.title": 14,
          "benefits.items": 18, "proof.label": 24, "cta.headline": 22, "cta.button": 10, "cta.sub": 30,
          "beats.text": 22, "beats.kicker": 12, "beats.sub": 24, "beats.items": 16}
# 템플릿마다 따로 쓰는 권장 글자 수 (name·label 같은 흔한 키 이름이 다른 템플릿에 걸리지 않게 템플릿별로)
LIMITS_BY_TPL = {
    "scenes": {"scenes.kicker": 14, "scenes.text": 40, "scenes.sub": 30, "scenes.items": 18, "scenes.left": 24, "scenes.right": 24,
               "scenes.leftLabel": 8, "scenes.rightLabel": 8, "scenes.by": 14, "scenes.role": 20, "note": 40},
    "company": {"label": 24, "name": 16, "mission": 40, "highlight": 12, "pillarsTitle": 14, "pillars.title": 12, "pillars.desc": 22,
                "factsTitle": 14, "facts.label": 12, "facts.unit": 3, "source": 40, "partnersTitle": 14, "partners": 10,
                "card.slogan": 20, "card.address": 36, "note": 30},
    "product": {"problem.title": 22, "problem.pains": 12, "product.name": 12, "product.tagline": 26, "features.title": 10,
                "features.desc": 20, "flow.title": 14, "flow.steps": 8, "result.label": 22, "result.source": 40},
    "timeline": {"milestones.title": 12, "milestones.text": 22, "now.title": 22, "now.sub": 26, "badgeUnit": 6},
    "news": {"partner.name": 14, "partner.deal": 24, "amount.round": 10, "award.name": 22, "launch.name": 14, "launch.sub": 30,
             "quote.text": 50, "ticker": 25, "plan": 30, "topic": 8, "facts": 18},
}
# 결 템플릿 10개는 같은 content(이야기)를 읽어요
STORY_LIMITS = {"kicker": 14, "title": 30, "highlight": 12, "points": 18, "number.prefix": 6, "number.suffix": 6, "number.label": 22,
                "number.source": 40, "cta.headline": 24, "cta.button": 10, "cta.sub": 30, "note": 40}
for _t in ("typeslam", "uidemo", "sketchbook", "dataflow", "terminal", "collage", "stage", "glow", "brandmark", "cinema"):
    LIMITS_BY_TPL[_t] = STORY_LIMITS


def limits_for(template):
    return {**LIMITS, **LIMITS_BY_TPL.get(template or "", {})}


def check_video(name):
    """(errors, notes, video, brand) 를 돌려줌."""
    video, brand, vdir = load_video(name)
    bdir = ROOT / "brands" / video["brand"]
    errors, notes = [], []

    if video.get("template"):
        if not (ROOT / "templates" / video["template"] / "index.html").exists():
            errors.append(f"템플릿이 없습니다: templates/{video['template']}/index.html")
    for f in video.get("formats") or []:
        if f not in FORMATS:
            errors.append(f"알 수 없는 형식: {f}")

    # 파일
    def exists(p, *bases):
        return any((b / p).exists() for b in (*bases, ROOT))
    for fnt in brand.get("fonts", []):
        if not exists(fnt["file"], bdir):
            errors.append(f"브랜드 글꼴 파일이 없습니다: {fnt['file']}")
    for fnt in video.get("fonts", []) or []:
        if not isinstance(fnt, dict) or not fnt.get("file") or not fnt.get("family"):
            errors.append("video.json 의 fonts 항목에는 family 와 file 이 있어야 합니다")
        elif not exists(fnt["file"], vdir):
            errors.append(f"영상 글꼴 파일이 없습니다: {fnt['file']}")
    if not video.get("template"):
        src = video.get("src", "index.html")
        for f in (src.values() if isinstance(src, dict) else [src]):
            if not (vdir / f).exists():
                errors.append(f"영상 HTML 이 없습니다: videos/{name}/{f}")
    keys = set()
    for k, p in (brand.get("assets") or {}).items():
        keys.add(k)
        if not exists(p, bdir):
            errors.append(f"브랜드 이미지가 없습니다: {k} → {p}")
    va = video.get("assets") or {}
    groups = [va] if not any(k in FORMATS or k == "common" for k in va) else [va.get("common", {})] + [va.get(f, {}) for f in FORMATS]
    for g in groups:
        for k, p in g.items():
            keys.add(k)
            if not exists(p, vdir):
                errors.append(f"영상 이미지가 없습니다: {k} → {p}")

    c = video.get("content") or {}
    for i, v in enumerate(c.get("visuals", []) or []):
        if v.get("image") and v["image"] not in keys:
            errors.append(f"visuals[{i}].image '{v['image']}' 가 assets 에 없습니다")
    for i, b in enumerate(c.get("beats", []) or []):
        if b.get("image") and b["image"] not in keys:
            errors.append(f"beats[{i}].image '{b['image']}' 가 assets 에 없습니다")
    # 장면 쌓기: photo1 같은 빈 자리는 아래 '아직 사진이 없는 칸'으로 알리고, 그 밖의 없는 키는 오류
    for i, b in enumerate(c.get("scenes", []) or [] if video.get("template") == "scenes" else []):
        if not isinstance(b, dict):
            continue
        for k in [b.get("image")] + list(b.get("images") or []):
            if isinstance(k, str) and k and k not in keys and not re.fullmatch(r"photo\d+", k):
                errors.append(f"scenes[{i}] 의 사진 '{k}' 가 assets 에 없습니다")
        if b.get("type") == "quote" and b.get("text"):
            notes.append(f"scenes[{i}] 인용: 실제로 그 사람이 한 말인지, 이름과 직함을 써도 되는지 확인하세요")
    for k in ("logo", "mascot"):
        if brand.get(k) and brand[k] not in keys:
            errors.append(f"brand.{k} '{brand[k]}' 가 브랜드 assets 에 없습니다")

    # 예시 문구가 남았는지
    raw = json.dumps(c, ensure_ascii=False)
    for marker in ("두 줄까지", "짧은 설명 한 줄", "버튼 문구", "장점 하나", "@계정이름", "첫 2초에", "목록 제목", "꼬리표", "가게 이름", "채널 이름"):
        if marker in raw:
            notes.append(f"템플릿 예시 문구가 남아 있습니다: '{marker}'")

    # 상황 프리셋의 예시 문구가 그대로인지 (문구 칸의 절반 넘게 같으면 알림)
    if video.get("preset"):
        try:
            from presets import get_preset, preset_content
            sample = preset_content(get_preset(video["preset"]))
            def leaves(o, out):
                if isinstance(o, dict):
                    for v in o.values():
                        leaves(v, out)
                elif isinstance(o, list):
                    for v in o:
                        leaves(v, out)
                elif isinstance(o, str) and len(o) > 3 and not re.fullmatch(r"photo\d+|#?[0-9a-fA-F]{3,8}", o):
                    out.append(o)
                return out
            mine, theirs = set(leaves(c, [])), set(leaves(sample, []))
            same = mine & theirs
            if theirs and len(same) >= max(3, len(theirs) * .5):
                notes.append(f"상황 프리셋 예시 문구가 그대로인 곳이 {len(same)}곳 있어요. 실제 내용으로 바꿔 주세요 (예: {sorted(same)[0]!r})")
        except Exception:  # noqa: BLE001
            pass
    # 비어 있는 사진 칸 (photo1 같은 키가 아직 assets 에 없음)
    empty = sorted({x for x in re.findall(r'"(photo\d+)"', json.dumps(c)) if x not in keys})
    if empty:
        notes.append(f"아직 사진이 없는 칸: {', '.join(empty)} (사진 탭에서 넣거나 '사진 자동 찾기')")

    # 문구 길이
    lims = limits_for(video.get("template"))

    def chk(path, text):
        if not isinstance(text, str):
            return
        n = len(text.replace("\n", ""))
        lim = lims.get(re.sub(r"\[\d+\]", "", path))
        if lim and n > lim:
            notes.append(f"{path} 가 {n}자입니다(권장 {lim}자 이하). 글자가 작아질 수 있어요: {text!r}")
        for w in RISKY:
            if w in text:
                if w in ("무료", "공짜"):
                    notes.append(f"{path} 의 '{w}' → 정말 조건 없이 무료인지 확인하고, 조건(기간·대상·횟수)이 있으면 함께 적으세요.")
                else:
                    notes.append(f"{path} 의 '{w}' → 근거(자료·인증)가 있는지 확인하세요. 없으면 표현을 바꾸는 게 안전합니다.")

    def walk(prefix, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("image", "images", "focus", "pan", "transition", "scheme", "type", "credit", "layout", "size", "symbol", "icon"):
                    continue
                walk(f"{prefix}.{k}" if prefix else k, v)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(f"{prefix}[{i}]" if not isinstance(v, str) else prefix, v)
        else:
            chk(prefix, obj)
    walk("", c)

    # 출처: 사진 파일과 같은 폴더(또는 상위 photos 폴더)의 credits.json 에서 파일 이름으로 찾음
    def credit_for(path):
        f = (vdir / path).resolve()
        for d in [f.parent, *f.parents][:4]:
            cj = d / "credits.json"
            if not cj.exists():
                for sub in ("source", "photos"):
                    if (d / sub / "credits.json").exists():
                        cj = d / sub / "credits.json"
                        break
            if cj.exists():
                items = json.loads(cj.read_text(encoding="utf-8-sig"))
                for x in items:
                    stem = x.get("file", "").rsplit(".", 1)[0]
                    if x.get("file") == f.name or (stem and f.stem in (stem, stem + "b")):
                        return x
        return None
    for g in groups:
        for k, p in g.items():
            if "photos/" in p and credit_for(p) is None:
                notes.append(f"사진 {p} 의 출처 기록이 없습니다 (직접 찍은 사진이면 python tools/photo.py add 로 기록)")
    for i, v in enumerate(c.get("visuals", []) or []):
        k = v.get("image")
        p = next((g[k] for g in groups if k in g), "")
        info = credit_for(p) if p else None
        need = info and (info.get("credit_line") or str(info.get("license", "")).upper().startswith("CC BY"))
        if need and not v.get("credit"):
            line = info.get("credit_line") or f"Photo: {info.get('author')} · {info.get('license')}"
            notes.append(f"visuals[{i}] 사진은 {info.get('license')} 라 화면에 출처를 넣어야 합니다: \"{line}\"")

    # 장면 쌓기: CC BY 사진을 쓰는 장면에는 그 장면의 credit 이 있어야 함
    if video.get("template") == "scenes":
        for i, sb in enumerate(c.get("scenes", []) or []):
            if not isinstance(sb, dict) or sb.get("credit"):
                continue
            for k in [sb.get("image")] + list(sb.get("images") or []):
                p = next((g[k] for g in groups if isinstance(k, str) and k in g), "")
                info = credit_for(p) if p else None
                if info and (info.get("credit_line") or str(info.get("license", "")).upper().startswith("CC BY")):
                    line = info.get("credit_line") or f"Photo: {info.get('author')} · {info.get('license')}"
                    notes.append(f"scenes[{i}] 사진은 {info.get('license')} 라 화면에 출처를 넣어야 합니다(그 장면의 credit): \"{line}\"")
                    break

    # 브랜드 규칙
    for n in brand.get("notes", []) or []:
        notes.append(f"브랜드 규칙 확인: {n}")

    return errors, notes, video, brand


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    name = sys.argv[1]
    errors, notes, video, brand = check_video(name)
    print(f"점검: {name} (브랜드 {brand.get('name')}, 템플릿 {video.get('template') or '직접 작성'})")
    for e in errors:
        print("  오류 ·", e)
    for n in notes:
        print("  확인 ·", n)
    if not errors and not notes:
        print("  문제 없음")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
