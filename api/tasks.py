import threading
from pathlib import Path
from typing import List, Union
from video_core.probe import probe_duration
from video_core.ffmpeg_builder import build_ffmpeg_command
from video_core.ffmpeg_runner import run_ffmpeg_with_progress
from video_core.params import JobParams, TextParams, BadgeParams, EffectsParams
from .store import read_job, write_job, job_log_path

def start_job_thread(job_id: Union[int, str]):
    # Запуск обработки как независимого потока — чтобы веб не вис и можно было отслеживать статус в реальном времени
    t = threading.Thread(target=_run_job, args=(job_id,), daemon=True)
    t.start()

def _clean_path_str(val: str) -> str:
    if val is None:
        return ""
    return val.strip().strip('"').strip("'")

def _build_params(job: dict, input_path: Path, output_path: Path, ui: dict) -> JobParams:
    font_path_str = _clean_path_str(ui.get('text_fontfile') or '')
    badge_path_str = _clean_path_str(ui.get('badge_path') or '')
    text = TextParams(
        enabled=bool(ui.get('text_enabled')),
        content=ui.get('text_content',''),
        fontfile=(Path(font_path_str) if font_path_str else None),
        auto_font=bool(ui.get('text_auto')),
        level=ui.get('text_level','Подпись'),
        fontsize=int(ui.get('text_fontsize') or 24),
        position=ui.get('text_position','Случайная'),
    )
    badge = BadgeParams(
        enabled=bool(ui.get('badge_enabled')),
        path=(Path(badge_path_str) if badge_path_str else None),
        random_scale=bool(ui.get('badge_random_scale')),
        scale_percent=int(ui.get('badge_scale_percent') or 30),
        position=ui.get('badge_position','Случайная'),
        behavior=ui.get('badge_behavior','Исчезновение'),
    )
    effects = EffectsParams(
        cut=bool(ui.get('cut')),
        contrast=bool(ui.get('contrast', True)),
        color_shift=bool(ui.get('color_shift')),
        noise=bool(ui.get('noise')),
        brightness_sat=bool(ui.get('brightness_sat', True)),
        crop_edges=bool(ui.get('crop_edges')),
        geom=bool(ui.get('geom', True)),
        time_mod=bool(ui.get('time_mod', True)),
        overlays=bool(ui.get('overlays', True)),
        codec_random=bool(ui.get('codec_random', True)),
        profile_strong=bool(ui.get('profile_strong')),
        safe_mode=bool(ui.get('safe_mode', True)),
        color_mod=bool(ui.get('color_mod')),
        hidden_pattern=bool(ui.get('hidden_pattern')),
    )
    jp = JobParams(
        input_path=input_path,
        output_path=output_path,
        copies=int(ui.get('copies') or 1),
        fmt=ui.get('fmt','9:16'),
        text=text,
        badge=badge,
        effects=effects,
        fixed_duration_sec=int(ui.get('fixed_duration') or 0) if ui.get('fixed_duration_enabled') else None,
    )
    return jp

def _nvenc_to_x264(cmd: List[str]) -> List[str]:
    # Fallback: если ffmpeg падает на NVENC, пересобираем команду под x264
    new_cmd = []
    skip_next = False
    i = 0
    while i < len(cmd):
        if skip_next:
            skip_next = False
            i += 1
            i += 1
            continue
        if cmd[i] == "-c:v" and i + 1 < len(cmd) and cmd[i + 1] == "h264_nvenc":
            new_cmd.extend(["-c:v", "libx264", "-crf", "22", "-g", "48", "-preset", "veryfast", "-pix_fmt", "yuv420p"])
            i += 2
            continue
        if cmd[i] == "-cq":
            skip_next = True
            i += 1
            i += 1
            continue
        if cmd[i] == "-preset" and i + 1 < len(cmd):
            i += 2
            continue
        new_cmd.append(cmd[i])
        i += 1
    return new_cmd

def _run_job(job_id: Union[int, str]):
    job = read_job(job_id)
    params = job.get('params') or {}
    is_test = params.get('is_test', False)
    input_folder = Path(job['input_folder'])
    output_folder = Path(job['output_folder'])
    if is_test:
        # Для теста — отдельная подпапка, чтобы не смешивать с пачкой
        output_folder = output_folder / 'tests'
    output_folder.mkdir(parents=True, exist_ok=True)
    exts = ["*.mp4","*.MP4","*.mov","*.MOV","*.mkv","*.MKV","*.webm","*.WEBM"]
    video_files_set = set()
    for pattern in exts:
        video_files_set.update(input_folder.rglob(pattern))
    video_files: List[Path] = list(video_files_set)
    if is_test:
        if not video_files:
            job['status'] = 'error'
            job['message'] = 'Не найдено видео для теста в папке.'
            write_job(job)
            return
        video_files = video_files[:1]
    copies_total = 1 if is_test else int(params.get('copies') or 1)

    # src_files_total = количество исходных видео в папке
    # total_tasks = количество выходных файлов (исходных * копии)
    job['src_files_total'] = len(video_files)
    job['src_files_done'] = 0
    write_job(job)

    tasks = []
    for f in video_files:
        for i in range(copies_total):
            out_name = f"test_{f.stem}.mp4" if is_test else f"{f.stem}_v{i+1}.mp4"
            out = output_folder / out_name
            tasks.append((f, out))
    total = len(tasks)
    job['total_tasks'] = total
    job['done_tasks'] = 0
    job['status'] = 'running'
    write_job(job)
    log_path = job_log_path(job_id)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, 'a', encoding='utf-8') as logf:
        for (inp, outp) in tasks:
            if not inp.exists():
                logf.write(f"INPUT NOT FOUND: {inp}\n")
                job['message'] = f"Нет файла: {inp}"
                job['done_tasks'] += 1
                job['progress_overall'] = int(job['done_tasks'] * 100 / max(1, job['total_tasks']))
                write_job(job)
                continue

            dur = probe_duration(inp)
            jp = _build_params(job, inp, outp, params)
            cmd = build_ffmpeg_command(jp, dur)
            # Логирование наличия шрифта (для диагностики путей)
            if jp.text.enabled:
                if jp.text.fontfile:
                    if jp.text.fontfile.exists():
                        logf.write(f"USING FONT: {jp.text.fontfile}\n")
                    else:
                        logf.write(f"FONT MISSING OR NOT FOUND: {jp.text.fontfile}\n")
                else:
                    logf.write("FONT NOT SPECIFIED (using auto or default)\n")
            if jp.badge.enabled:
                if not (jp.badge.path and jp.badge.path.exists()):
                    logf.write(f"BADGE MISSING OR NOT FOUND: {jp.badge.path}\n")
                else:
                    logf.write(f"USING BADGE: {jp.badge.path}\n")

            tried_nvenc_fallback = False
            while True:
                file_pct = 0
                finished_ok = False
                finished_err = False
                for ev in run_ffmpeg_with_progress(cmd, dur):
                    if ev.get('event') == 'progress':
                        file_pct = ev.get('pct', 0)
                    elif ev.get('event') == 'log':
                        logf.write(ev.get('line','') + "\n")
                    elif ev.get('event') == 'done':
                        finished_ok = True
                    elif ev.get('event') == 'error':
                        finished_err = True
                # Если была ошибка NVENC — автоматический fallback
                if finished_err and any(tok == 'h264_nvenc' for tok in cmd) and not tried_nvenc_fallback:
                    logf.write("NVENC error -> fallback to libx264\n")
                    cmd = _nvenc_to_x264(cmd)
                    tried_nvenc_fallback = True
                    continue
                if not finished_ok and finished_err:
                    logf.write("FFmpeg finished with error\n")
                break

            job['done_tasks'] += 1
            job['progress_overall'] = int(job['done_tasks'] * 100 / max(1, job['total_tasks']))
            write_job(job)

    job['status'] = 'done'
    job['message'] = ''
    write_job(job)


