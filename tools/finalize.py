"""마스터 영상을 업로드용 MP4로 만듭니다. 음악 파일이 있으면 페이드와 함께 합칩니다.

사용법:
    python tools/finalize.py <영상> <형식|all> [옵션]

옵션:
    --music 파일.mp3     배경음악 (mp3, wav, m4a 등). 영상 길이에 맞춰 자르고 페이드 처리
    --volume 0.9         음악 크기 (기본 1.0)
    --fade-in 0.5        시작 페이드 초 (기본 0.5)
    --fade-out 2.5       끝 페이드 초 (기본 2.5)
    --start 0            음악을 몇 초 지점부터 쓸지 (기본 0). music.py 가 찾은 첫 다운비트를 넣으면 박이 0초에 맞음
    --lufs -14           음악 크기를 이 라우드니스로 맞춤 (기본 -14, 유튜브·인스타 기준). off 면 맞추지 않음.
                         --volume 은 맞춘 뒤에 곱합니다 (1.0 = -14 LUFS)
    --split 32.2         Google Vids 업로드용으로 이 초에서 두 조각으로 나눔(각 10MB 안팎)

음악이 없으면 무음 오디오 트랙을 넣습니다. 오디오 트랙이 없는 MP4는 일부 서비스(Google Vids 등)가 거절합니다.
결과: out/<영상>/<형식>/<영상>_<형식>.mp4
"""
import os
import shutil
import subprocess
import sys

from common import ROOT, formats_of, load_video, out_dir


def opt(name, default=None, cast=str):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return cast(sys.argv[i + 1])
    return default


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def measure_loudness(src, chain, target=-14):
    """loudnorm 1차 측정값(JSON)을 돌려줌."""
    import json as _j
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-filter_complex",
                        chain + f",loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    txt = r.stderr
    a, b = txt.rfind("{"), txt.rfind("}")
    if a < 0 or b < a:
        return None
    try:
        return _j.loads(txt[a:b + 1])
    except ValueError:
        return None


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,width,height",
                        "-of", "compact", str(path)], capture_output=True, text=True)
    return r.stdout.strip().replace("\n", " | ")


VIDEO = ["-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p"]


def main():
    args = [a for a in sys.argv[1:]]
    if len(args) < 2 or args[0].startswith("--"):
        sys.exit(__doc__)
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg를 찾을 수 없습니다.")
    name = args[0]
    video, _, vdir = load_video(name)
    music = opt("--music")
    if music:
        mp = (vdir / music) if (vdir / music).exists() else (ROOT / music if (ROOT / music).exists() else None)
        if mp is None and os.path.exists(music):
            from pathlib import Path
            mp = Path(music)
        if mp is None:
            sys.exit(f"음악 파일을 찾을 수 없습니다: {music}")
    vol, fi, fo, mstart = opt("--volume", 1.0, float), opt("--fade-in", .5, float), opt("--fade-out", 2.5, float), opt("--start", 0.0, float)
    split = opt("--split", None, float)
    lufs_arg = opt("--lufs", "-14")
    lufs = None if str(lufs_arg).lower() in ("off", "none", "0") else float(lufs_arg)

    for fmt in formats_of(video, args[1]):
        od = out_dir(name, fmt)
        master = od / "master.mp4"
        if not master.exists():
            sys.exit(f"{master.relative_to(ROOT)} 이 없습니다. 먼저 python tools/render.py {name} {fmt} video")
        d = duration(master)
        target = od / f"{name}_{fmt}.mp4"
        if music:
            base = (f"atrim=start={mstart}:duration={d},asetpts=PTS-STARTPTS,"
                    + (f"afade=t=in:st=0:d={fi}," if fi > 0 else "")
                    + f"afade=t=out:st={max(0, d - fo):.3f}:d={fo}")
            norm = ""
            if lufs is not None:
                m = measure_loudness(mp, "[0:a]" + base, lufs)
                if m and m.get("input_i") not in (None, "-inf"):
                    # 목표까지 한 번에 올리고(내리고), 튀는 봉우리는 리미터가 -1dB 아래로 눌러 줍니다
                    lim = ",alimiter=limit=0.89:attack=2:release=60:level=false"
                    gain = max(-30.0, min(24.0, lufs - float(m["input_i"])))
                    for _ in range(2):   # 리미터가 깎은 만큼 다시 재서 보충 (두 번이면 ±0.5 안쪽)
                        m2 = measure_loudness(mp, "[0:a]" + base + f",volume={gain:.2f}dB" + lim, lufs)
                        if not m2 or m2.get("input_i") in (None, "-inf"):
                            break
                        miss = lufs - float(m2["input_i"])
                        if abs(miss) < .4:
                            break
                        gain = max(-30.0, min(30.0, gain + miss))
                    norm = f",volume={gain:.2f}dB"
                    print(f"  음악 크기: {float(m['input_i']):.1f} → {lufs} LUFS ({gain:+.1f}dB)")
            af = f"[1:a]{base}{norm},volume={vol},alimiter=limit=0.89:attack=2:release=60:level=false,aformat=sample_rates=48000:channel_layouts=stereo[a]"
            ff("-i", str(master), "-i", str(mp), "-filter_complex", af, "-map", "0:v", "-map", "[a]",
               *VIDEO, "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-t", f"{d}", "-movflags", "+faststart", str(target))
        else:
            ff("-i", str(master), "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-map", "0:v", "-map", "1:a",
               "-shortest", *VIDEO, "-crf", "20", "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", str(target))
        print(f"  {fmt}: {target.relative_to(ROOT)} → {probe(target)}")

        if split:
            for idx, (ss, tt) in enumerate([(0, split), (split, d - split)], 1):
                part = od / f"{name}_{fmt}_part{idx}.mp4"
                log = str(od / "ffmpeg2pass")
                br = f"{int(9.2 * 8 * 1024 / max(tt, 1) - 80)}k"  # 조각당 약 9MB 목표
                ff("-ss", str(ss), "-i", str(target), "-t", str(tt), *VIDEO, "-b:v", br, "-pass", "1", "-passlogfile", log, "-an", "-f", "mp4", os.devnull)
                ff("-ss", str(ss), "-i", str(target), "-t", str(tt), *VIDEO, "-b:v", br, "-pass", "2", "-passlogfile", log,
                   "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", str(part))
                print(f"    조각 {idx}: {part.relative_to(ROOT)} → {probe(part)}")
            for f in od.glob("ffmpeg2pass*"):
                f.unlink()


if __name__ == "__main__":
    main()
