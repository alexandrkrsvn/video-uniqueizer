import os
import random
from pathlib import Path
from typing import List, Optional, Tuple
from .params import JobParams
from .positions import calc_position
from .probe import probe_badge
from .metadata import random_metadata


def detect_nvenc() -> bool:
    """Проверка наличия NVENC кодеков."""
    import subprocess
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True)
        return out.returncode == 0 and ("h264_nvenc" in out.stdout or "hevc_nvenc" in out.stdout)
    except Exception:
        return False


def validate_nvenc_runtime() -> bool:
    """Валидация NVENC в runtime."""
    import subprocess
    try:
        test = ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=size=64x64:rate=1:duration=1",
                "-c:v", "h264_nvenc", "-f", "null", "-"]
        r = subprocess.run(test, capture_output=True, text=True)
        return r.returncode == 0
    except Exception:
        return False


def _escape_text_for_drawtext(text: str) -> str:
    """Экранирование текста для FFmpeg drawtext."""
    return (text
            .replace('\\', '\\\\')
            .replace(':', '\\:')
            .replace(',', '\\,')
            .replace('=', '\\=')
            .replace('`', '\\`')
            .replace('"', '\\"')
            .replace("'", "'\\''"))


def _escape_fontfile_path(path: Path) -> str:
    """
    Экранирование пути к шрифту для FFmpeg drawtext fontfile.
    """
    path_str = str(path).replace('\\', '/')
    escaped = path_str.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def _build_video_effects_filters(effects, video_w: int, video_h: int, safe: bool, strong: bool) -> Tuple[List[str], Optional[str]]:
    """
    Построение фильтров эффектов видео.
    Возвращает (список фильтров, аудио фильтр если есть).
    """
    filters = []
    audio_filter = None
    
    if effects.cut and not safe:
        trim_value = random.uniform(0.05, 0.12)
        filters.append(f"trim=start={trim_value:.2f},setpts=PTS-STARTPTS")
    
    eq_parts = []
    
    if effects.contrast:
        eq_parts.append(f"contrast={random.uniform(1.0, 1.04):.2f}")
    
    if effects.brightness_sat:
        eq_parts.append(f"brightness={random.uniform(0.003, 0.03):.2f}")
        eq_parts.append(f"saturation={random.uniform(0.96, 1.04):.2f}")
    
    if eq_parts:
        filters.append("eq=" + ":".join(eq_parts))
    
    if effects.color_shift and not safe:
        filters.append(f"hue=h={random.uniform(-4, 4):.2f}")
    
    if effects.noise and not safe:
        filters.append(f"noise=alls={random.randint(1, 3)}:allf=t")
    
    if effects.crop_edges and not safe:
        crop_w = random.uniform(0.985, 0.995)
        crop_h = random.uniform(0.985, 0.995)
        crop_x = random.uniform(0, video_w * 0.01)
        crop_y = random.uniform(0, video_h * 0.01)
        filters.append(f"crop=iw*{crop_w:.3f}:ih*{crop_h:.3f}:{crop_x:.2f}:{crop_y:.2f}")
    
    if effects.geom and not safe:
        rot_amp = random.uniform(0.001, 0.002) * (1.6 if strong else 1.0)
        scl_amp = random.uniform(0.002, 0.004) * (1.6 if strong else 1.0)
        filters.append(f"rotate={rot_amp:.4f}*sin(2*PI*t):fillcolor=black")
        filters.append(f"scale=iw*(1+{scl_amp:.4f}*sin(2*PI*t*0.3)):ih*(1+{scl_amp:.4f}*sin(2*PI*t*0.3)):eval=frame")
    
    if effects.overlays and not safe:
        sigma = 0.25 * (1.4 if strong else 1.0)
        vig = 0.12 * (1.3 if strong else 1.0)
        filters.append(f"gblur=sigma={sigma:.2f}")
        filters.append(f"vignette=PI/6:{vig:.2f}")
    
    if effects.time_mod and not safe:
        delta = random.uniform(-0.0080, 0.0080) * (1.6 if strong else 1.0)
        filters.append(f"setpts=(1.0+{delta:.4f})*PTS")
        atempo = 1.0 / (1.0 + delta)
        atempo = min(2.0, max(0.5, atempo))
        audio_filter = f"atempo={atempo:.4f}"
    
    if effects.color_mod and not safe:
        hue_v = random.uniform(-4, 4) * (1.6 if strong else 1.0)
        b_v = random.uniform(0.003, 0.03) * (1.4 if strong else 1.0)
        s_v = 1.0 + (random.uniform(-0.04, 0.04) * (1.4 if strong else 1.0))
        filters.append(f"hue=h={hue_v:.2f}")
        eq_color_parts = [f"brightness={b_v:.3f}", f"saturation={s_v:.2f}"]
        if eq_color_parts:
            filters.append("eq=" + ":".join(eq_color_parts))
    
    if effects.hidden_pattern:
        filters.append("drawgrid=width=64:height=64:thickness=1:color=white@0.03")
    
    return filters, audio_filter


def _build_text_filters(text_params, video_w: int, video_h: int, safe: bool) -> List[str]:
    """Построение фильтров текста."""
    if not text_params.enabled or not text_params.content.strip():
        return []
    
    if text_params.auto_font:
        k = 0.05 if text_params.level == "Заголовок" else 0.035
        fontsize = max(12, int(video_h * k))
    else:
        fontsize = text_params.fontsize
    
    x, y, _ = calc_position(True, video_w, video_h, 0, 0, text_params.position)
    
    def _strip_time_expr(expr: str) -> str:
        if not isinstance(expr, str):
            return str(expr)
        if 't*' not in expr:
            return expr
        head = expr.split('t*', 1)[0].rstrip('+-')
        return head or '0'
    
    if safe:
        x = _strip_time_expr(x)
        y = _strip_time_expr(y)
    
    safe_text = _escape_text_for_drawtext(text_params.content)
    
    color = random.choice(["#FFFFFF", "#FFFF00", "#FF0000", "#00FF00", "#0000FF"])
    
    if text_params.fontfile:
        if not text_params.fontfile.exists():
            print(f"[ffmpeg_builder] WARNING: Font file does not exist: {text_params.fontfile}, but will try to use it anyway")
        
        fontfile_escaped = _escape_fontfile_path(text_params.fontfile)
        fontfile_param = f"fontfile={fontfile_escaped}"
    else:
        fontfile_param = None
    
    drawtext_parts = [
        f"text='{safe_text}'",
        fontfile_param if fontfile_param else None,
        f"fontsize={fontsize}",
        f"fontcolor={color}",
        f"x={x}",
        f"y={y}",
        "bordercolor=black",
        "borderw=3",
        "shadowcolor=black@0.5",
        "shadowx=2",
        "shadowy=2",
        "line_spacing=6"
    ]
    
    drawtext_parts = [p for p in drawtext_parts if p is not None]
    
    drawtext_filter = "drawtext=" + ":".join(drawtext_parts)
    
    return [drawtext_filter]


def _build_filter_chain(
    input_label: str,
    video_effects: List[str],
    video_w: int,
    video_h: int,
    text_filters: List[str],
    output_label: str
) -> str:
    """
    Построение цепочки фильтров для видео потока.
    Структура: [input]effects,scale,pad,setsar,text[output]
    """
    parts = []
    
    chain = input_label
    
    if video_effects:
        chain += video_effects[0]
        if len(video_effects) > 1:
            parts.extend(video_effects[1:])
    
    parts.append(f"scale={video_w}:{video_h}:force_original_aspect_ratio=decrease")
    parts.append(f"pad={video_w}:{video_h}:(ow-iw)/2:(oh-ih)/2:black")
    parts.append("setsar=1")
    
    parts.extend(text_filters)
    
    if parts:
        chain += "," + ",".join(parts)
    
    chain += output_label
    
    return chain


def build_ffmpeg_command(p: JobParams, duration_sec: float, nvenc_ok: Optional[bool] = None) -> List[str]:
    """Построение команды FFmpeg из параметров."""
    
    fmt = p.fmt
    video_w, video_h = (720, 720) if fmt == "1:1" else (720, 1280) if fmt == "9:16" else (1280, 720)
    
    E = p.effects
    safe = E.safe_mode
    strong = E.profile_strong
    
    video_effects, audio_filter = _build_video_effects_filters(E, video_w, video_h, safe, strong)
    
    text_filters = _build_text_filters(p.text, video_w, video_h, safe)
    
    input_loop_needed = False
    input_loop_count = -1
    if p.fixed_duration_sec and p.fixed_duration_sec > 0 and duration_sec < p.fixed_duration_sec:
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
    
    cmd = ['ffmpeg', '-y', '-threads', str(os.cpu_count() or 4)]
    
    if input_loop_needed:
        cmd.extend(['-stream_loop', str(input_loop_count)])
    
    cmd.extend(['-i', str(p.input_path).replace('\\', '/')])
    
    if use_badge:
        try:
            badge_w, badge_h, has_alpha, badge_dur = probe_badge(p.badge.path)
        except Exception as e:
            print(f"[ffmpeg_builder] WARNING: Failed to probe badge {p.badge.path}: {e}")
            badge_w, badge_h, has_alpha, badge_dur = 399, 225, False, None
        
        badge_scale_percent = getattr(p.badge, 'scale_percent', 30) or 30
        if getattr(p.badge, 'random_scale', False):
            scale_percent = max(10, min(80, int(badge_scale_percent)))
            badge_scale_percent = random.randint(max(10, scale_percent - 10), min(80, scale_percent + 20))
        
        badge_scale_rel = badge_scale_percent / 100.0
        badge_target_w = max(64, int(video_w * badge_scale_rel))
        est_badge_h = int((badge_h or 225) * (badge_target_w / float(badge_w or 399)))
        
        badge_file = str(p.badge.path).replace('\\', '/')
        ext_lower = badge_file.lower()
        
        loop_flag = []
        force_shortest = False
        badge_behavior = getattr(p.badge, 'behavior', 'Исчезновение') or 'Исчезновение'
        
        if badge_behavior == 'Луп до конца':
            if ext_lower.endswith(('.png', '.jpg', '.jpeg')):
                loop_flag = ['-loop', '1']
            else:
                loop_flag = ['-stream_loop', '-1']
        elif badge_behavior == 'Обрезать по короткому':
            force_shortest = True
        
        cmd.extend(loop_flag)
        cmd.extend(['-i', badge_file])
        
        bx, by, _ = calc_position(False, video_w, video_h, badge_target_w, est_badge_h, p.badge.position)
        bx = str(bx) if bx is not None else "0"
        by = str(by) if by is not None else "0"
        
        base_chain = _build_filter_chain('[0:v]', video_effects, video_w, video_h, text_filters, '[bg]')
        
        badge_parts = ['[1:v]fps=30', f'scale={badge_target_w}:-1:flags=bilinear']
        
        if not has_alpha and ext_lower.endswith(('.gif', '.png')):
            badge_parts.append('colorkey=0xFFFFFF:0.1:0.1')
        
        badge_parts.append('format=rgba')
        badge_chain = ','.join(badge_parts) + '[logo]'
        
        overlay_opts = f'overlay={bx}:{by}:eof_action=pass'
        if force_shortest:
            overlay_opts += ':shortest=1'
        
        overlay_chain = f'[bg][logo]{overlay_opts}[outv]'
        
        filter_complex = ';'.join([base_chain, badge_chain, overlay_chain])
        
        cmd.extend([
            '-filter_complex_threads', '2',
            '-filter_complex', filter_complex,
            '-map', '[outv]',
            '-map', '0:a?'
        ])
        
        if badge_behavior == 'Обрезать по короткому':
            cmd.append('-shortest')
    
    else:
        if p.badge.enabled and p.badge.path:
            print(f"[ffmpeg_builder] WARNING: badge_path is not a real file: {p.badge.path}")
        
        filter_parts = []
        
        filter_parts.extend(video_effects)
        
        filter_parts.append(f'scale={video_w}:{video_h}:force_original_aspect_ratio=decrease')
        filter_parts.append(f'pad={video_w}:{video_h}:(ow-iw)/2:(oh-ih)/2:black')
        filter_parts.append('setsar=1')
        
        filter_parts.extend(text_filters)
        
        vf_chain = ','.join(filter_parts)
        
        cmd.extend(['-filter_threads', '2', '-vf', vf_chain])
    
    cmd.extend(random_metadata())
    
    if audio_filter:
        cmd.extend(['-af', audio_filter])
    
    use_nvenc = bool(nvenc_ok)
    if nvenc_ok is None:
        try:
            use_nvenc = detect_nvenc() and validate_nvenc_runtime()
        except Exception:
            use_nvenc = False
    
    if use_nvenc:
        cmd.extend(['-c:v', 'h264_nvenc', '-preset', 'p3', '-cq', '23', '-g', '48', '-pix_fmt', 'yuv420p'])
    else:
        if E.codec_random and not safe:
            crf = random.randint(20, 24)
            preset = random.choice(["veryfast", "superfast"])
            cmd.extend(['-c:v', 'libx264', '-crf', str(crf), '-g', '48', '-preset', preset, '-pix_fmt', 'yuv420p'])
        else:
            cmd.extend(['-c:v', 'libx264', '-crf', '22', '-g', '48', '-preset', 'veryfast', '-pix_fmt', 'yuv420p'])
    
    cmd.extend(['-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart'])
    
    if p.fixed_duration_sec and p.fixed_duration_sec > 0:
        target_dur = p.fixed_duration_sec
        insert_pos = len(cmd)
        for i, arg in enumerate(cmd):
            if arg in ['-c:v', '-c:a']:
                insert_pos = i
                break
        cmd.insert(insert_pos, str(target_dur))
        cmd.insert(insert_pos, '-t')
    
    cmd.append(str(p.output_path))
    
    return cmd
