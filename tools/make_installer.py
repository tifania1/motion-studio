"""완전한 설치 파일(MotionStudioSetup.zip) 만들기.

압축 안에는 설치 스크립트(installer 폴더)와 스튜디오 전체(엔진·템플릿·도구·앱·상황 프리셋·스킬·글꼴)가 들어가요.
브랜드와 영상은 installer/examples.json 에 적힌 예시만 넣어서, 내 광고 계정 자료는 설치 파일에 섞이지 않아요.
다 만든 뒤에는 압축을 새 폴더에 풀어서 상황 12개 영상 만들기·점검·빌드와 앱 불러오기까지 해 봅니다.

사용법:
    python tools/make_installer.py                 # dist/MotionStudioSetup.zip 만들고 풀어서 점검
    python tools/make_installer.py --no-check      # 점검 건너뛰기
    python tools/make_installer.py --with-renders  # 예시 필름의 화면 렌더(master.mp4)도 넣기 → '음악만 다시 합치기'가 바로 됨 (약 50MB 늘어남)
    python tools/make_installer.py --all           # 모든 브랜드·영상 넣기 (다른 사람에게 줄 설치 파일에는 쓰지 마세요)
    python tools/make_installer.py --out <zip 경로>

새 버전을 낼 때는 installer/README.txt 의 "이번 버전에서 새로 생긴 것"부터 고치세요.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

from common import ROOT

SETUP = "MotionStudioSetup"
PROJECT = "motion-studio"
PARTS = [".claude", "app", "docs", "engine", "fonts", "installer", "presets", "styles", "templates", "tools", "vendor"]
ROOT_FILES = ["CLAUDE.md", "README.md", "StudioApp.cmd", "StudioApp_debug.cmd", "requirements.txt", "requirements-tools.txt", ".gitignore", "update.json"]
INSTALLER_FILES = ["install.ps1", "Install_MotionStudio.cmd", "README.txt"]
SKIP_DIRS = {"__pycache__", ".git", "node_modules"}
SKIP_FILES = {".DS_Store", "Thumbs.db", "desktop.ini", "settings.local.json"}
CHAT_LIMIT_MB = 30


def files_under(base: Path):
    for dp, dns, fns in os.walk(base):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
        for f in sorted(fns):
            if f in SKIP_FILES or f.endswith(".pyc"):
                continue
            yield Path(dp) / f


def collect(with_renders=False, everything=False):
    """(압축 안 경로, 실제 파일) 목록과 알림."""
    ex = json.loads((ROOT / "installer" / "examples.json").read_text(encoding="utf-8-sig"))
    notes, items = [], []
    for f in INSTALLER_FILES:
        p = ROOT / "installer" / f
        if not p.exists():
            sys.exit(f"installer/{f} 이 없어요. 설치 스크립트가 있어야 설치 파일을 만들 수 있어요.")
        items.append((f"{SETUP}/{f}", p))
    pre = f"{SETUP}/{PROJECT}/"
    for part in PARTS:
        base = ROOT / part
        if not base.exists():
            notes.append(f"{part} 폴더가 없어서 건너뜀")
            continue
        files = files_under(base)
        if part == "styles":   # 시험용 스타일(zz-·_ 로 시작)은 빼고
            files = [p for p in files if not p.relative_to(base).parts[0].startswith(("zz-", "_"))]
        items += [(pre + p.relative_to(ROOT).as_posix(), p) for p in files]
    for f in ROOT_FILES:
        if (ROOT / f).exists():
            items.append((pre + f, ROOT / f))
    for kind in ("brands", "videos"):
        names = sorted(p.name for p in (ROOT / kind).iterdir() if p.is_dir()) if everything else ex.get(kind, [])
        for n in names:
            d = ROOT / kind / n
            if not d.is_dir():
                notes.append(f"예시 {kind}/{n} 이 없어서 빠짐")
                continue
            items += [(pre + p.relative_to(ROOT).as_posix(), p) for p in files_under(d)]
    if with_renders:
        for v in ex.get("renders", []):
            found = sorted((ROOT / "out" / v).glob("*/master.mp4"))
            if not found:
                notes.append(f"{v} 의 화면 렌더(master.mp4)가 없어서 빠짐")
            items += [(pre + p.relative_to(ROOT).as_posix(), p) for p in found]
    return items, notes


def write_zip(items, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".tmp")
    dirs = set()
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for arc, src in items:
            parts = arc.split("/")[:-1]
            for i in range(1, len(parts) + 1):
                d = "/".join(parts[:i]) + "/"
                if d not in dirs:
                    dirs.add(d)
                    z.writestr(d, "")
            z.write(src, arc)
    tmp.replace(dst)


def run(args, cwd):
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable] + args, cwd=cwd, capture_output=True, env=env)
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")


def old_python_issues(root: Path):
    """파이썬 3.10·3.11 에서 안 되는 f-string 문법(중괄호 안 역슬래시, 같은 따옴표 겹치기)을 찾음.
    설치하는 PC의 파이썬이 3.10~3.11 일 수 있어서 (3.12 이상에서만 되는 문법을 쓰면 그 PC에서만 오류)."""
    import tokenize
    if not hasattr(tokenize, "FSTRING_START"):
        return []
    bad = []
    for f in sorted((root / "tools").glob("*.py")):
        stack = []
        try:
            toks = list(tokenize.generate_tokens(f.open(encoding="utf-8").readline))
        except (tokenize.TokenError, SyntaxError) as e:
            bad.append(f"{f.name}: 읽지 못함 ({e})")
            continue
        for t in toks:
            if t.type == tokenize.FSTRING_START:
                stack.append(t.string.lstrip("rRbBfFuU")[:1])
            elif t.type == tokenize.FSTRING_END:
                stack.pop()
            elif stack and t.type != tokenize.FSTRING_MIDDLE:
                if "\\" in t.string:
                    bad.append(f"{f.name} {t.start[0]}줄: f-string 중괄호 안에 역슬래시")
                if t.type == tokenize.STRING and t.string.lstrip("rRbBuU")[:1] == stack[-1]:
                    bad.append(f"{f.name} {t.start[0]}줄: f-string 안에 같은 따옴표")
                if t.type == tokenize.FSTRING_START and t.string.lstrip("rRbBfFuU")[:1] in stack[:-1]:
                    bad.append(f"{f.name} {t.start[0]}줄: f-string 안에 같은 따옴표")
    return bad


def check(zip_path: Path):
    """새 폴더에 풀어서 실제로 쓰는 것처럼 해 봄. 실패 목록 반환."""
    bad = []
    tmp = Path(tempfile.mkdtemp(prefix="ms-check-"))
    try:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp)
        proj = tmp / SETUP / PROJECT
        old = old_python_issues(proj)
        print(f"  파이썬 3.10 호환 문법: {'통과' if not old else '걸림'}")
        bad += [f"파이썬 3.10에서 안 되는 문법: {x}" for x in old]
        for f in INSTALLER_FILES:
            if not (tmp / SETUP / f).exists():
                bad.append(f"압축에 {f} 이 없어요")
        ps = shutil.which("powershell") or shutil.which("pwsh")
        if ps:
            script = str(tmp / SETUP / "install.ps1").replace("'", "''")
            r = subprocess.run([ps, "-NoProfile", "-Command",
                                f"$e=$null; $null=[System.Management.Automation.Language.Parser]::ParseFile('{script}',[ref]$null,[ref]$e); $e.Count"],
                               capture_output=True)
            n = r.stdout.decode("utf-8", "replace").strip()
            print(f"  install.ps1 문법 오류: {n or '?'}개")
            if n != "0":
                bad.append(f"install.ps1 문법 오류 {n}개")
        code, out = run(["-c", "import sys; sys.path.insert(0, 'tools'); "
                               "from presets import list_presets; print(' '.join(p['id'] for p in list_presets()))"], proj)
        ids = out.split() if code == 0 else []
        if not ids:
            bad.append("상황 프리셋을 읽지 못했어요")
        brand = "haru-cafe" if (proj / "brands" / "haru-cafe").is_dir() else None
        for pid in ids if brand else []:
            v = f"zz-check-{pid}"
            for step, args in (("만들기", ["tools/new_video.py", v, "--brand", brand, "--preset", pid]),
                               ("점검", ["tools/check.py", v]),
                               ("빌드", ["tools/build.py", v])):
                code, out = run(args, proj)
                if code != 0:
                    bad.append(f"{pid} {step} 실패: {out.strip().splitlines()[-1] if out.strip() else code}")
                    break
            else:
                print(f"  {pid:<16} 만들기·점검·빌드 통과")
        if brand:
            v = "zz-check-scratch"
            for step, args in (("만들기", ["tools/new_video.py", v, "--brand", brand, "--scratch", "점검용 영상: 로고가 나타나고 한 문장이 나오는 10초 영상"]),
                               ("점검", ["tools/check.py", v]), ("빌드", ["tools/build.py", v])):
                code, out = run(args, proj)
                if code != 0:
                    bad.append(f"처음부터 짜기 {step} 실패: {out.strip().splitlines()[-1] if out.strip() else code}")
                    break
            else:
                print(f"  {'처음부터 짜기':<14} 만들기·점검·빌드 통과")
        if (proj / "videos" / "lumenta-deck" / "video.json").exists():   # 발표 자료: 점검·빌드·장마다 찍어 PDF
            for step, args in (("점검", ["tools/check.py", "lumenta-deck"]), ("빌드", ["tools/build.py", "lumenta-deck"]),
                               ("PDF", ["tools/deck.py", "pdf", "lumenta-deck"]),
                               ("PPT", ["tools/deck_pptx.py", "lumenta-deck", "--no-embed"])):
                code, out = run(args, proj)
                if code != 0:
                    bad.append(f"발표 자료 {step} 실패: {out.strip().splitlines()[-1] if out.strip() else code}")
                    break
            else:
                print(f"  {'발표 자료':<14} 점검·빌드·PDF·PPT 통과")
        code, out = run(["tools/styles.py", "check"], proj)
        last = out.strip().splitlines()[-1] if out.strip() else ""
        print(f"  스타일 점검: {last or code}")
        if code != 0:
            bad.append("스타일 점검 실패: " + " / ".join(l.strip() for l in out.splitlines() if "오류" in l)[:400])
        if ids and brand:
            code, out = run(["-c", "import sys, json; sys.path.insert(0, 'tools'); from styles import list_styles; "
                                   "print(' '.join(s['id'] for s in list_styles()))"], proj)
            sids = out.split() if code == 0 else []
            if not sids:
                bad.append("스타일 목록을 읽지 못했어요")
            vj = proj / "videos" / f"zz-check-{ids[0]}" / "video.json"
            for sid in sids[:: max(1, len(sids) // 6)] if vj.exists() else []:   # 묶음이 섞이게 여섯 개쯤 골라 빌드
                v = json.loads(vj.read_text(encoding="utf-8-sig"))
                v.update(style=sid, styleColors=True)
                vj.write_text(json.dumps(v, ensure_ascii=False), encoding="utf-8")
                code, out = run(["tools/build.py", f"zz-check-{ids[0]}", "tall"], proj)
                if code != 0:
                    bad.append(f"스타일 {sid} 빌드 실패: {out.strip()[-200:]}")
            if sids:
                print(f"  스타일 입혀 빌드: {'통과' if not any(b.startswith('스타일 ') for b in bad) else '실패'}")
        if ids and brand:
            code, out = run(["tools/upload.py", "text", f"zz-check-{ids[0]}"], proj)
            print(f"  올릴 글 만들기: {'통과' if code == 0 else '실패'}")
            if code != 0:
                bad.append("올릴 글을 만들지 못했어요: " + out.strip()[-300:])
        code, out = run(["-c", "import sys; sys.path.insert(0, 'tools'); import app; print('app ok')"], proj)
        print(f"  앱 불러오기: {'통과' if 'app ok' in out else '실패'}")
        if "app ok" not in out:
            bad.append("앱을 불러오지 못했어요: " + out.strip()[-300:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return bad


def main():
    args = sys.argv[1:]
    out = Path(args[args.index("--out") + 1]) if "--out" in args else ROOT / "dist" / f"{SETUP}.zip"
    t0 = time.time()
    items, notes = collect("--with-renders" in args, "--all" in args)
    print(f"설치 파일 만드는 중: 파일 {len(items)}개")
    for n in notes:
        print(f"  알림: {n}")
    write_zip(items, out)
    mb = out.stat().st_size / 1e6
    print(f"  → {out} ({mb:.1f}MB)")
    if mb > CHAT_LIMIT_MB:
        print(f"  알림: {CHAT_LIMIT_MB}MB가 넘어서 채팅으로는 못 보낼 수 있어요. 드라이브나 USB로 옮기세요.")
    if "--no-check" in args:
        print("점검은 건너뛰었어요.")
        return
    print("압축을 새 폴더에 풀어서 점검하는 중…")
    bad = check(out)
    if bad:
        print("점검에서 걸린 것:")
        for b in bad:
            print(f"  - {b}")
        sys.exit(1)
    print(f"점검 통과. 설치 파일 완성 ({time.time() - t0:.0f}초)")


if __name__ == "__main__":
    main()
