import subprocess
from pathlib import Path
from typing import Optional, Tuple

def probe_duration(path: Path) -> float:
    cmd = [
        "ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1", str(path).replace('\\','/')
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(r.stdout.strip() or "12.63")
    except Exception:
        return 12.63

def probe_badge(path: Path) -> Tuple[int,int,bool,Optional[float]]:
    cmd = [
        "ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=width,height,pix_fmt,duration",
        "-of","default=noprint_wrappers=1:nokey=1", str(path).replace('\\','/')
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = r.stdout.strip().splitlines()
        w = int(lines[0]) if lines and lines[0].strip() else 399
        h = int(lines[1]) if len(lines)>1 and lines[1].strip() else 225
        pix_fmt = (lines[2].strip() if len(lines)>2 else "").lower()
        has_alpha = "a" in pix_fmt
        dur = float(lines[3]) if len(lines)>3 and lines[3].strip() else None
        return w,h,has_alpha,dur
    except Exception:
        return 399,225,False,None


