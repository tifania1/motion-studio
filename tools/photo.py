"""영상에 쓸 사진을 찾고, 받고, 출처를 기록합니다.

사용법:
    python tools/photo.py search "검색어" [--limit 12] [--allow-sa]
        위키미디어 공용에서 출처 표시만 하면 되는 사진(CC0, 퍼블릭 도메인, CC BY)을 찾습니다.
        검색어는 영어가 잘 찾아집니다. 예) "latte art", "Bangkok street food"
    python tools/photo.py get <영상> "File:파일이름.jpg" --as <키> [--width 1920]
        위키미디어 사진을 받아 videos/<영상>/photos/<키>.jpg 로 저장하고 credits.json, video.json assets 에 추가
    python tools/photo.py add <영상> <내 사진 파일> --as <키> [--credit "Photo: 홍길동"] [--license "자체 촬영"]
        직접 찍었거나 구매한 사진을 넣을 때
    python tools/photo.py credits <영상>
        credits.json 으로 CREDITS.md 를 만듦 (게시글 본문에 붙일 출처 문구)

참고: 위키미디어는 요청이 빠르면 429로 막습니다. 이 도구는 표준 크기 썸네일만 받고, 요청 사이에 쉬고, 막히면 기다렸다 다시 시도합니다.
CC BY-SA 사진은 광고에 쓰면 결과물도 같은 조건으로 공개해야 할 수 있어 기본으로 빼 둡니다(--allow-sa 로 볼 수 있음).
"""
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

from PIL import Image

from common import FORMATS, ROOT, video_dir

API = "https://commons.wikimedia.org/w/api.php"
# 위키미디어는 연락처(URL·이메일)가 없는 User-Agent를 429로 막습니다. 막히면 환경변수 WIKIMEDIA_CONTACT 에
# 본인 사이트 주소나 이메일을 넣으세요. 예) set WIKIMEDIA_CONTACT=https://instagram.com/내계정
CONTACT = os.environ.get("WIKIMEDIA_CONTACT") or "https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia"
UA = f"MotionStudio/1.0 ({CONTACT}; local ad-video tool) python-urllib/3"
STANDARD_WIDTHS = (500, 960, 1280, 1920, 3840)


def opt(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def fetch(url, tries=4):
    wait = 5
    for k in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and k < tries - 1:
                ra = e.headers.get("Retry-After", "")
                w = int(ra) if ra.isdigit() else wait
                if w > 90:
                    sys.exit(f"위키미디어가 잠시 요청을 막았어요(429). 약 {max(1, round(w / 60))}분 뒤 다시 해 보세요.")
                print(f"  요청이 많다고 막혔습니다(429). {w}초 기다렸다 다시 시도합니다.")
                time.sleep(w)
                wait *= 3
                continue
            if e.code == 429:
                sys.exit("위키미디어가 계속 막고 있습니다(429). 몇 분 뒤 다시 하거나, 환경변수 WIKIMEDIA_CONTACT 에 본인 주소·이메일을 넣고 다시 해 보세요.")
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if k < tries - 1:
                time.sleep(2)
                continue
            raise PhotoError("위키미디어에 연결하지 못했어요. 인터넷·회사 프록시·방화벽을 확인하고 다시 시도해 주세요.") from e


def api(**params):
    params.update(format="json", formatversion="2")
    data = json.loads(fetch(API + "?" + urllib.parse.urlencode(params)))
    time.sleep(1.5)
    return data


def strip_html(s):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()


def license_kind(short):
    s = (short or "").strip().upper()
    if s in ("CC0", "CC0 1.0") or "PUBLIC DOMAIN" in s or s.startswith("PD"):
        return "ok"
    if s.startswith("CC BY-SA"):
        return "sa"
    if s.startswith("CC BY") and not any(x in s for x in ("-NC", "-ND")):
        return "ok"
    return "no"


def meta(ii):
    em = ii.get("extmetadata", {})
    g = lambda k: (em.get(k) or {}).get("value", "")
    return {"author": strip_html(g("Artist")) or strip_html(g("Credit")) or "Unknown",
            "license": strip_html(g("LicenseShortName")) or "Unknown",
            "license_url": strip_html(g("LicenseUrl"))}


class PhotoError(Exception):
    pass


def search_photos(q, limit=12, allow_sa=False):
    """위키미디어 공용 검색. 광고에 쓸 수 있는 라이선스만 돌려줌."""
    data = api(action="query", generator="search", gsrsearch=f"{q} filetype:bitmap", gsrnamespace=6,
               gsrlimit=min(50, limit * 3), prop="imageinfo", iiprop="url|size|extmetadata", iiurlwidth=330,
               iiextmetadatafilter="Artist|LicenseShortName|LicenseUrl|Credit")
    pages = sorted((data.get("query") or {}).get("pages", []), key=lambda p: p.get("index", 0))
    out = []
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        m = meta(ii)
        kind = license_kind(m["license"])
        if kind == "no" or (kind == "sa" and not allow_sa):
            continue
        out.append({"title": p["title"], "width": ii.get("width", 0), "height": ii.get("height", 0),
                    "license": m["license"], "author": m["author"], "kind": kind,
                    "page": ii.get("descriptionurl", ""), "thumb": (ii.get("thumburl") or "").split("?")[0]})
        if len(out) >= limit:
            break
    return out


def find_candidates(queries, want=8, exclude_titles=()):
    """여러 검색어로 찾아 관련도 순서를 섞어(검색어1의 1등, 검색어2의 1등, …) 후보를 고름. 너무 작은 사진은 뺌."""
    lists, errs = [], []
    for q in queries:
        q = (q or "").strip()
        if not q:
            continue
        try:
            lists.append([dict(r, query=q) for r in search_photos(q, limit=12)])
        except (SystemExit, Exception) as e:  # 429 등으로 한 검색어가 실패해도 나머지는 계속
            errs.append(e)
            continue
    if errs and not lists:   # 모든 검색이 실패했으면(인터넷 끊김, 계속 429) 이유를 알려 줌
        e = errs[-1]
        if isinstance(e, SystemExit):
            raise PhotoError(str(e.code))
        if isinstance(e, (urllib.error.URLError, OSError)):
            raise PhotoError("위키미디어에 연결하지 못했어요. 인터넷·회사 프록시·방화벽을 확인하고 다시 시도해 주세요.")
        raise e
    seen, out = set(exclude_titles), []
    for k in range(12):
        for lst in lists:
            if k < len(lst):
                r = lst[k]
                if r["title"] in seen or max(r["width"], r["height"]) < 1200:
                    continue
                seen.add(r["title"])
                out.append(r)
    return out[:want]


def cmd_search():
    q = sys.argv[2] if len(sys.argv) > 2 else sys.exit(__doc__)
    found = search_photos(q, int(opt("--limit", 12)), "--allow-sa" in sys.argv)
    for r in found:
        flag = "  ※ BY-SA(주의)" if r["kind"] == "sa" else ""
        small = "  ※ 작음" if max(r["width"], r["height"]) < 1600 else ""
        print(f'"{r["title"]}"\n    {r["width"]}x{r["height"]} · {r["license"]} · {r["author"][:60]}{flag}{small}\n    {r["page"]}')
    if not found:
        print("조건에 맞는 사진이 없습니다. 영어 검색어나 다른 표현으로 다시 찾아 보세요.")


def update_video(vdir, key, rel, credit_line):
    vp = vdir / "video.json"
    video = json.loads(vp.read_text(encoding="utf-8-sig"))
    assets = video.setdefault("assets", {})
    if any(k in FORMATS or k == "common" for k in assets):
        assets.setdefault("common", {})[key] = rel
    else:
        assets[key] = rel
    filled = 0
    for v in (video.get("content") or {}).get("visuals", []) or []:
        if v.get("image") == key and not v.get("credit") and credit_line:
            v["credit"] = credit_line
            filled += 1
    for b in (video.get("content") or {}).get("beats", []) or []:
        if b.get("image") == key and not b.get("credit") and credit_line:
            b["credit"] = credit_line
            filled += 1
    vp.write_text(json.dumps(video, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return filled


def load_credits(vdir):
    cp = vdir / "photos" / "credits.json"
    return json.loads(cp.read_text(encoding="utf-8-sig")) if cp.exists() else []


def add_credit(vdir, entry):
    cp = vdir / "photos" / "credits.json"
    items = [i for i in load_credits(vdir) if i.get("file") != entry["file"]] + [entry]
    cp.parent.mkdir(exist_ok=True)
    cp.write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def save_jpg(raw, path):
    try:
        im = Image.open(io.BytesIO(raw))
    except Exception as e:  # noqa: BLE001  HEIC·SVG·깨진 파일
        raise PhotoError("이 그림 파일은 열 수 없어요. JPG나 PNG로 바꿔서 넣어 주세요 (아이폰 HEIC, SVG 는 안 돼요).") from e
    im = im.convert("RGB")
    if max(im.size) > 2600:
        r = 2600 / max(im.size)
        im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    im.save(path, "JPEG", quality=92)
    return im.size


def check_key(key):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", key or ""):
        raise PhotoError("사진 이름(키)은 영문·숫자·_·- 로 40자 안에서 지어 주세요. 예) photo1")


def get_photo(name, title, key, width=1920):
    """위키미디어 사진을 받아 저장하고 출처를 기록. 결과 정보 dict 반환."""
    check_key(key)
    if not title.startswith("File:"):
        title = "File:" + title
    width = min(STANDARD_WIDTHS, key=lambda w: abs(w - width))
    vdir = video_dir(name)
    data = api(action="query", titles=title, prop="imageinfo", iiprop="url|size|extmetadata", iiurlwidth=width,
               iiextmetadatafilter="Artist|LicenseShortName|LicenseUrl|Credit")
    page = data["query"]["pages"][0]
    if page.get("missing"):
        raise PhotoError(f"위키미디어에 없는 파일입니다: {title}")
    ii = page["imageinfo"][0]
    m = meta(ii)
    kind = license_kind(m["license"])
    if kind == "no":
        raise PhotoError(f"이 사진은 라이선스({m['license']})가 광고용으로 맞지 않아 받지 않았습니다.")
    url = (ii.get("thumburl") if ii.get("width", 0) > width else None) or ii["url"]
    url = url.split("?")[0]
    (vdir / "photos").mkdir(exist_ok=True)
    dst = vdir / "photos" / f"{key}.jpg"
    size = save_jpg(fetch(url), dst)
    credit_line = f"Photo: {m['author']} · {m['license']}" if kind != "ok" or not m["license"].upper().startswith(("CC0", "PUBLIC")) else ""
    add_credit(vdir, {"file": dst.name, "key": key, "title": page["title"], "author": m["author"], "license": m["license"],
                      "license_url": m["license_url"], "source_page": ii.get("descriptionurl", ""), "credit_line": credit_line})
    filled = update_video(vdir, key, f"photos/{dst.name}", credit_line)
    return {"key": key, "file": f"photos/{dst.name}", "size": list(size), "license": m["license"], "author": m["author"],
            "credit_line": credit_line, "filled": filled, "share_alike": kind == "sa"}


def add_photo(name, src, key, credit="", license="자체 촬영/보유", author="", source="", title=None):
    """내 사진 파일을 영상에 넣음."""
    check_key(key)
    src = Path(src)
    if not src.exists():
        raise PhotoError(f"파일이 없습니다: {src}")
    vdir = video_dir(name)
    (vdir / "photos").mkdir(exist_ok=True)
    dst = vdir / "photos" / f"{key}.jpg"
    if src.resolve() != dst.resolve():
        try:
            small_jpg = src.suffix.lower() in (".jpg", ".jpeg") and max(Image.open(src).size) <= 2600
        except Exception as e:  # noqa: BLE001
            raise PhotoError("이 그림 파일은 열 수 없어요. JPG나 PNG로 바꿔서 넣어 주세요 (아이폰 HEIC, SVG 는 안 돼요).") from e
        if small_jpg:
            shutil.copy(src, dst)
            size = Image.open(dst).size
        else:
            size = save_jpg(src.read_bytes(), dst)
    else:
        size = Image.open(dst).size
    add_credit(vdir, {"file": dst.name, "key": key, "title": title or src.name, "author": author,
                      "license": license, "license_url": "", "source_page": source, "credit_line": credit})
    update_video(vdir, key, f"photos/{dst.name}", credit)
    return {"key": key, "file": f"photos/{dst.name}", "size": list(size), "credit_line": credit}


def credits_markdown(name):
    vdir = video_dir(name)
    lines = ["# 사진 출처", ""]
    for i in load_credits(vdir):
        src = f" · [원본]({i['source_page']})" if i.get("source_page") else ""
        lic = f"[{i['license']}]({i['license_url']})" if i.get("license_url") else i.get("license", "")
        who = i.get("author") or "-"
        lines.append(f"- {i['file']}: {i.get('title', '')} — {who} · {lic}{src}")
    text = "\n".join(lines) + "\n"
    (vdir / "CREDITS.md").write_text(text, encoding="utf-8")
    return text


def cmd_get():
    if len(sys.argv) < 4 or not opt("--as"):
        sys.exit(__doc__)
    r = get_photo(sys.argv[2], sys.argv[3], opt("--as"), int(opt("--width", 1920)))
    if r["share_alike"]:
        print(f"  주의: {r['license']} 입니다. 광고에 쓰면 결과물도 같은 조건으로 공개해야 할 수 있습니다.")
    print(f"저장: videos/{sys.argv[2]}/{r['file']} ({r['size'][0]}x{r['size'][1]}) · {r['license']} · {r['author']}")
    if r["credit_line"]:
        print(f"  화면 출처 표시: {r['credit_line']}" + (f" (visuals {r['filled']}곳에 자동 기입)" if r["filled"] else " → 이 사진을 쓰는 장면의 credit 에 넣으세요"))
    else:
        print("  CC0·퍼블릭 도메인이라 출처 표시는 필수가 아닙니다. credits.json 에는 기록해 두었습니다.")


def cmd_add():
    if len(sys.argv) < 4 or not opt("--as"):
        sys.exit(__doc__)
    r = add_photo(sys.argv[2], sys.argv[3], opt("--as"), opt("--credit", ""), opt("--license", "자체 촬영/보유"),
                  opt("--author", ""), opt("--source", ""))
    print(f"저장: videos/{sys.argv[2]}/{r['file']} ({r['size'][0]}x{r['size'][1]})")


def cmd_credits():
    name = sys.argv[2] if len(sys.argv) > 2 else sys.exit(__doc__)
    print(credits_markdown(name))
    print(f"→ videos/{name}/CREDITS.md")


def main():
    cmds = {"search": cmd_search, "get": cmd_get, "add": cmd_add, "credits": cmd_credits}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    try:
        cmds[sys.argv[1]]()
    except PhotoError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
