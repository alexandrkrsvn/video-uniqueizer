import os
import random
from pathlib import Path
from typing import List, Optional
from .params import JobParams
from .positions import calc_position
from .probe import probe_badge
from .metadata import random_metadata

def detect_nvenc() -> bool:
    import subprocess
    try:
        out = subprocess.run(["ffmpeg","-hide_banner","-encoders"], capture_output=True, text=True)
        return out.returncode==0 and ("h264_nvenc" in out.stdout or "hevc_nvenc" in out.stdout)
    except Exception:
        return False

def validate_nvenc_runtime() -> bool:
    import subprocess
    try:
        test = ["ffmpeg","-v","error","-f","lavfi","-i","color=size=64x64:rate=1:duration=1","-c:v","h264_nvenc","-f","null","-"]
        r = subprocess.run(test, capture_output=True, text=True)
        return r.returncode==0
    except Exception:
        return False

def build_ffmpeg_command(p: JobParams, duration_sec: float, nvenc_ok: Optional[bool]=None) -> List[str]:
    fmt = p.fmt
    video_w, video_h = (720,720) if fmt=="1:1" else (720,1280) if fmt=="9:16" else (1280,720)

    filters = []
    E = p.effects
    strong = E.profile_strong
    safe = E.safe_mode

    audio_filter: Optional[str] = None
    
    if E.cut and not safe:
        trim_value = random.uniform(0.05, 0.12)
        filters.append(f"trim=start={trim_value:.2f},setpts=PTS-STARTPTS")
    if E.contrast:
        filters.append(f"eq=contrast={random.uniform(1.0,1.04):.2f}")
    if E.color_shift and not safe:
        filters.append(f"hue=h={random.uniform(-4,4):.2f}")
    if E.noise and not safe:
        filters.append(f"noise=alls={random.randint(1,3)}:allf=t")
    if E.brightness_sat:
        filters.append(f"eq=brightness={random.uniform(0.003,0.03):.2f}:saturation={random.uniform(0.96,1.04):.2f}")
    
    if E.crop_edges and not safe:
        crop_w = random.uniform(0.985, 0.995)
        crop_h = random.uniform(0.985, 0.995)
        crop_x = random.uniform(0, video_w * 0.01)
        crop_y = random.uniform(0, video_h * 0.01)
        filters.append(f"crop=iw*{crop_w:.3f}:ih*{crop_h:.3f}:{crop_x:.2f}:{crop_y:.2f}")
    
    if E.geom and not safe:
        rot_amp = random.uniform(0.001, 0.002) * (1.6 if strong else 1.0)
        scl_amp = random.uniform(0.002, 0.004) * (1.6 if strong else 1.0)
        filters.append(f"rotate={rot_amp:.4f}*sin(2*PI*t):fillcolor=black")
        filters.append(f"scale=iw*(1+{scl_amp:.4f}*sin(2*PI*t*0.3)):ih*(1+{scl_amp:.4f}*sin(2*PI*t*0.3)):eval=frame")
    
    if E.overlays and not safe:
        sigma = 0.25 * (1.4 if strong else 1.0)
        vig = 0.12 * (1.3 if strong else 1.0)
        filters.append(f"gblur=sigma={sigma:.2f}")
        filters.append(f"vignette=PI/6:{vig:.2f}")
    
    # Временная модуляция (видео + синхронизация звука через -af atempo)
    if E.time_mod and not safe:
        delta = random.uniform(-0.0080, 0.0080) * (1.6 if strong else 1.0)
        filters.append(f"setpts=(1.0+{delta:.4f})*PTS")
        atempo = 1.0 / (1.0 + delta)
        atempo = min(2.0, max(0.5, atempo))
        audio_filter = f"atempo={atempo:.4f}"
    
    if E.color_mod and not safe:
        hue_v = random.uniform(-4, 4) * (1.6 if strong else 1.0)
        b_v = random.uniform(0.003, 0.03) * (1.4 if strong else 1.0)
        s_v = 1.0 + (random.uniform(-0.04, 0.04) * (1.4 if strong else 1.0))
        filters.append(f"hue=h={hue_v:.2f}")
        filters.append(f"eq=brightness={b_v:.3f}:saturation={s_v:.2f}")
    
    text_filters = []
    if p.text.enabled and p.text.content.strip():
        fontfile = p.text.fontfile
        if fontfile and fontfile.exists():
            if p.text.auto_font:
                k = 0.05 if p.text.level=="Заголовок" else 0.035
                fontsize = max(12, int(video_h*k))
            else:
                fontsize = p.text.fontsize
            x,y,_ = calc_position(True, video_w, video_h, 0,0, p.text.position)
            safe_text = (p.text.content
                         .replace('\\','\\\\').replace(':','\\:').replace(',','\\,').replace('=','\\=')
                         .replace('`','\\`').replace('"','\\"').replace("'", "'\\''"))
            color = random.choice(["#FFFFFF","#FFFF00","#FF0000","#00FF00","#0000FF"])
            fontfile_escaped = str(fontfile).replace('\\','/')
            fontfile_escaped = fontfile_escaped.replace(':', '\\:')
            text_filters.append(
                f"drawtext=text='{safe_text}':fontfile='{fontfile_escaped}':fontsize={fontsize}:fontcolor={color}:x={x}:y={y}:"
                f"bordercolor=black:borderw=3:shadowcolor=black@0.5:shadowx=2:shadowy=2:line_spacing=6"
            )
    
    if E.hidden_pattern:
        filters.append("drawgrid=width=64:height=64:thickness=1:color=white@0.03")
    
    filters.extend(text_filters)

    # Фиксировать длительность: определяем нужен ли loop для продления
    input_loop_needed = False
    input_loop_count = -1
    if p.fixed_duration_sec and p.fixed_duration_sec > 0 and duration_sec < p.fixed_duration_sec:
        # Нужно продлить видео - используем loop 
        loops_needed = int((p.fixed_duration_sec / duration_sec) + 1)
        input_loop_needed = True
        input_loop_count = loops_needed

    use_badge = (
        p.badge.enabled
        and p.badge.path
        and isinstance(p.badge.path, Path)
        and p.badge.path.exists()
        and p.badge.path.is_file()
    )
    if use_badge:
        badge_w, badge_h, has_alpha, badge_dur = probe_badge(p.badge.path)
        badge_scale_percent = getattr(p.badge, 'scale_percent', 30) or 30
        if getattr(p.badge, 'random_scale', False):
            scale_percent = max(10, min(80, int(badge_scale_percent)))
            badge_scale_percent = random.randint(max(10, scale_percent - 10), min(80, scale_percent + 20))
        badge_scale_rel = badge_scale_percent / 100.0
        badge_target_w = max(64, int(video_w * badge_scale_rel))
        est_badge_h = int((badge_h or 225) * (badge_target_w / float(badge_w or 399)))
        badge_file = str(p.badge.path).replace('\\','/')
        ext_lower = badge_file.lower()

        # Поведение длительности бейджа и параметры loop
        loop_flag = []
        force_shortest = False
        is_static_image = (badge_dur is None or badge_dur == 0) and (ext_lower.endswith('.png') or ext_lower.endswith('.jpg') or ext_lower.endswith('.jpeg'))
        badge_behavior = getattr(p.badge, 'behavior', 'Исчезновение') or 'Исчезновение'
        if badge_behavior == 'Луп до конца':
            if ext_lower.endswith('.png') or ext_lower.endswith('.jpg') or ext_lower.endswith('.jpeg'):
                loop_flag = ['-loop', '1']
            else:
                loop_flag = ['-stream_loop', '-1']
        elif badge_behavior == 'Обрезать по короткому':
            loop_flag = []
            force_shortest = True
        else:
            loop_flag = []
            force_shortest = False

        input_loop_cmd = []
        if input_loop_needed:
            input_loop_cmd = ['-stream_loop', str(input_loop_count)]
        cmd = [
            'ffmpeg', '-y', '-threads', str(os.cpu_count() or 4),
        ] + input_loop_cmd + ['-i', str(p.input_path).replace('\\','/')] + loop_flag + ['-i', badge_file]

        bx, by, _ = calc_position(False, video_w, video_h, badge_target_w, est_badge_h, p.badge.position)

        base_parts = []
        start = '[0:v]'
        if filters:
            start += filters[0]
        base_parts.append(start)
        if filters and len(filters) > 1:
            base_parts.extend(filters[1:])
        base_parts.append(f'scale={video_w}:{video_h}:force_original_aspect_ratio=decrease')
        base_parts.append(f'pad={video_w}:{video_h}:(ow-iw)/2:(oh-ih)/2:black')
        base_parts.append('setsar=1')
        base_chain_str = ','.join(base_parts) + '[bg]'

        badge_parts = ['[1:v]fps=30', f'scale={badge_target_w}:-1:flags=bilinear']
        if not has_alpha and (ext_lower.endswith('.gif') or ext_lower.endswith('.png')):
            badge_parts.append('colorkey=0xFFFFFF:0.1:0.1')
        badge_parts.append('format=rgba')
        badge_chain_str = ','.join(badge_parts) + '[logo]'

        # Overlay: для "Обрезать по короткому"
        overlay_opts = f'overlay={bx}:{by}:eof_action=pass'
        if force_shortest:
            overlay_opts += ':shortest=1'

        filter_complex = ';'.join([base_chain_str, badge_chain_str, f'[bg][logo]{overlay_opts}[outv]'])
        cmd += ['-filter_complex_threads', '2', '-filter_complex', filter_complex, '-map', '[outv]', '-map', '0:a?']
    else:
        if p.badge.enabled and p.badge.path:
            print(f"[ffmpeg_builder] WARNING: badge_path is not a real file: {p.badge.path}")
        input_loop_cmd = []
        if input_loop_needed:
            input_loop_cmd = ['-stream_loop', str(input_loop_count)]
        cmd = ['ffmpeg', '-y', '-threads', str(os.cpu_count() or 4)] + input_loop_cmd + ['-i', str(p.input_path).replace('\\','/')]
        vf_parts = []
        if filters:
            vf_parts.append(','.join(filters))
        vf_parts.append(f'scale={video_w}:{video_h}:force_original_aspect_ratio=decrease')
        vf_parts.append(f'pad={video_w}:{video_h}:(ow-iw)/2:(oh-ih)/2:black')
        vf_parts.append('setsar=1')
        vf_chain = ','.join(vf_parts)
        cmd += ['-filter_threads', '2', '-vf', vf_chain]
    cmd += random_metadata()

    # Аудио фильтр 
    if audio_filter:
        cmd += ['-af', audio_filter]

    # Кодек: NVENC при наличии, иначе x264 
    use_nvenc = bool(nvenc_ok)
    if nvenc_ok is None:
        try:
            use_nvenc = detect_nvenc() and validate_nvenc_runtime()
        except Exception:
            use_nvenc = False
    
    if use_nvenc:
        vcodec_args = ['-c:v','h264_nvenc','-preset','p3','-cq','23','-g','48','-pix_fmt','yuv420p']
    else:
        if E.codec_random and not safe:
            crf = random.randint(20, 24)
            preset = random.choice(["veryfast", "superfast"])
            vcodec_args = ['-c:v','libx264','-crf',str(crf),'-g','48','-preset',preset,'-pix_fmt','yuv420p']
        else:
            vcodec_args = ['-c:v','libx264','-crf','22','-g','48','-preset','veryfast','-pix_fmt','yuv420p']
    
    acodec_args = ['-c:a','aac','-b:a','128k','-movflags','+faststart']
    cmd += vcodec_args + acodec_args

    # Глобальный -shortest для "Обрезать по короткому" 
    if use_badge:
        badge_behavior = getattr(p.badge, 'behavior', 'Исчезновение') or 'Исчезновение'
        if badge_behavior == 'Обрезать по короткому':
            cmd += ['-shortest']

    # Фиксировать длительность: обрезать видео до заданной длительности 
    if p.fixed_duration_sec and p.fixed_duration_sec > 0:
        target_dur = p.fixed_duration_sec
        insert_pos = len(cmd) - 1
        for i, arg in enumerate(cmd):
            if arg in ['-c:v', '-c:a']:
                insert_pos = i
                break
        cmd.insert(insert_pos, str(target_dur))
        cmd.insert(insert_pos, '-t')

    cmd.append(str(p.output_path))
    return cmd


