import subprocess
from typing import Dict, Iterator, List

def _calc_pct(out_time_ms: float, duration_sec: float) -> int:
    if duration_sec>0:
        return int(min(100, max(0, (out_time_ms / (duration_sec*1000.0))*100 )))
    return 0

def run_ffmpeg_with_progress(cmd: List[str], duration_sec: float) -> Iterator[Dict]:
    try:
        if len(cmd)>=2 and cmd[0]=="ffmpeg":
            insert_pos = 2
            inject = ["-progress","-","-nostats","-loglevel","error"]
            cmd = cmd[:insert_pos] + inject + cmd[insert_pos:]
    except Exception:
        pass

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )
    out_time_ms = 0.0
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            if line.startswith("out_time_ms="):
                try:
                    out_time_ms = float(line.split("=",1)[1])
                except Exception:
                    pass
                yield {"event":"progress","pct": _calc_pct(out_time_ms, duration_sec)}
            elif line.startswith("out_time_us="):
                try:
                    val = line.split("=",1)[1]
                    if val != "N/A":
                        out_time_ms = float(val)/1000.0
                except Exception:
                    pass
                yield {"event":"progress","pct": _calc_pct(out_time_ms, duration_sec)}
            elif line.startswith("progress="):
                yield {"event":"progress","pct": _calc_pct(out_time_ms, duration_sec)}
            else:
                yield {"event":"log","line": line}
        code = proc.wait()
        if code==0:
            yield {"event":"done","code":0}
        else:
            yield {"event":"error","code":code}
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


