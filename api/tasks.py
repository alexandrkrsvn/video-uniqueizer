import threading
import tempfile
import shutil
from pathlib import Path
from typing import List, Union, Optional
from video_core.probe import probe_duration
from video_core.ffmpeg_builder import build_ffmpeg_command
from video_core.ffmpeg_runner import run_ffmpeg_with_progress
from video_core.params import JobParams, TextParams, BadgeParams, EffectsParams
from .store import read_job, write_job, job_log_relpath
from .yadisk_client import get_yadisk_client

def start_job_thread(job_id: Union[int, str]):
    t = threading.Thread(target=_run_job, args=(job_id,), daemon=True)
    t.start()

def _clean_path_str(val: str) -> str:
    if val is None:
        return ""
    return val.strip().strip('"').strip("'")

def _build_params(job: dict, input_path: Path, output_path: Path, ui: dict, temp_assets_folder: Optional[Path] = None) -> JobParams:
    font_path_str = _clean_path_str(ui.get('text_fontfile') or '')
    badge_path_str = _clean_path_str(ui.get('badge_path') or '')
    
    font_path = None
    if font_path_str:
        font_path = Path(font_path_str) if font_path_str else None
    
    badge_path = None
    if badge_path_str:
        badge_path = Path(badge_path_str) if badge_path_str else None
    
    text = TextParams(
        enabled=bool(ui.get('text_enabled')),
        content=ui.get('text_content',''),
        fontfile=font_path,
        auto_font=bool(ui.get('text_auto')),
        level=ui.get('text_level','Подпись'),
        fontsize=int(ui.get('text_fontsize') or 24),
        position=ui.get('text_position','Случайная'),
    )
    badge = BadgeParams(
        enabled=bool(ui.get('badge_enabled')),
        path=badge_path,
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
    use_yadisk = params.get('use_yadisk', False)
    
    yadisk_client = None
    temp_input_folder = None
    temp_output_folder = None
    temp_base = None
    temp_assets_folder = None
    
    task_log_path = None
    task_output_root = None
    task_logs_folder = None
    task_videos_folder = None
    task_tests_folder = None
    base_output_folder = None
    
    if use_yadisk:
        yadisk_client = get_yadisk_client()
        if not yadisk_client:
            job['status'] = 'error'
            job['message'] = 'Токен Яндекс Диска не настроен'
            write_job(job)
            return
        
        temp_base = Path(tempfile.gettempdir()) / f'job_{job_id}'
        temp_input_folder = temp_base / 'input'
        temp_output_folder = temp_base / 'output'
        temp_input_folder.mkdir(parents=True, exist_ok=True)
        temp_output_folder.mkdir(parents=True, exist_ok=True)
        
        temp_task_root = temp_output_folder / str(job_id)
        temp_logs_folder = temp_task_root / 'logs'
        temp_videos_folder = temp_task_root / 'videos'
        temp_tests_folder = temp_task_root / 'tests'
        
        temp_logs_folder.mkdir(parents=True, exist_ok=True)
        if is_test:
            temp_tests_folder.mkdir(parents=True, exist_ok=True)
        else:
            temp_videos_folder.mkdir(parents=True, exist_ok=True)
        
        task_log_path = temp_logs_folder / 'job.log'
        task_log_path.parent.mkdir(parents=True, exist_ok=True)
        task_log_path.touch()
        
        yadisk_input_path = job['input_folder']
        yadisk_output_path = job['output_folder']
        
        job['log_path'] = str(job_log_relpath(job_id, job['output_folder']))
        write_job(job)
        
        log_path = task_log_path
        
        with open(log_path, 'a', encoding='utf-8') as logf:
            logf.write(f"Загрузка видео с Яндекс Диска из: {yadisk_input_path}\n")
        
        job['status'] = 'downloading'
        job['message'] = 'Загрузка видео с Яндекс Диска...'
        write_job(job)
        
        downloaded_files = yadisk_client.download_folder_videos(yadisk_input_path, temp_input_folder)
        
        if not downloaded_files:
            job['status'] = 'error'
            job['message'] = 'Не найдено видеофайлов на Яндекс Диске'
            write_job(job)
            return
        
        with open(log_path, 'a', encoding='utf-8') as logf:
            logf.write(f"Скачано {len(downloaded_files)} видеофайлов\n")
        
        input_folder = temp_input_folder
        if is_test:
            output_folder = temp_tests_folder
        else:
            output_folder = temp_videos_folder
        
        video_files = downloaded_files
        
        temp_assets_folder = temp_base / 'assets'
        temp_assets_folder.mkdir(parents=True, exist_ok=True)
        
        with open(log_path, 'a', encoding='utf-8') as logf:
            if params.get('text_font_from_yadisk', False) and params.get('text_fontfile'):
                font_yadisk_path = params['text_fontfile']
                logf.write(f"Скачивание шрифта с Яндекс Диска: {font_yadisk_path}\n")
                font_local = yadisk_client.download_file(font_yadisk_path, temp_assets_folder / Path(font_yadisk_path).name)
                if font_local:
                    params['text_fontfile'] = str(font_local)
                    logf.write(f"Шрифт скачан: {font_local}\n")
                else:
                    logf.write(f"Ошибка скачивания шрифта: {font_yadisk_path}\n")
            
            if params.get('badge_from_yadisk', False) and params.get('badge_path'):
                badge_yadisk_path = params['badge_path']
                logf.write(f"Скачивание бейджа с Яндекс Диска: {badge_yadisk_path}\n")
                badge_local = yadisk_client.download_file(badge_yadisk_path, temp_assets_folder / Path(badge_yadisk_path).name)
                if badge_local:
                    params['badge_path'] = str(badge_local)
                    logf.write(f"Бейдж скачан: {badge_local}\n")
                else:
                    logf.write(f"Ошибка скачивания бейджа: {badge_yadisk_path}\n")
        
    else:
        base_output_folder = Path(job['output_folder'])
        
        task_output_root = base_output_folder / str(job_id)
        task_logs_folder = task_output_root / 'logs'
        task_videos_folder = task_output_root / 'videos'
        task_tests_folder = task_output_root / 'tests'
        
        task_logs_folder.mkdir(parents=True, exist_ok=True)
        if is_test:
            task_tests_folder.mkdir(parents=True, exist_ok=True)
        else:
            task_videos_folder.mkdir(parents=True, exist_ok=True)
        
        task_log_path = task_logs_folder / 'job.log'
        
        job['log_path'] = str(job_log_relpath(job_id, job['output_folder']))
        write_job(job)
        
        input_folder = Path(job['input_folder'])
        if is_test:
            output_folder = task_tests_folder
        else:
            output_folder = task_videos_folder
        
        exts = ["*.mp4","*.MP4","*.mov","*.MOV","*.mkv","*.MKV","*.webm","*.WEBM"]
        video_files_set = set()
        for pattern in exts:
            video_files_set.update(input_folder.rglob(pattern))
        video_files: List[Path] = list(video_files_set)
        
        if params.get('text_font_from_yadisk', False) or params.get('badge_from_yadisk', False):
            yadisk_client = get_yadisk_client()
            if yadisk_client:
                temp_base = Path(tempfile.gettempdir()) / f'job_{job_id}'
                temp_assets_folder = temp_base / 'assets'
                temp_assets_folder.mkdir(parents=True, exist_ok=True)
                
                log_path = task_log_path
                
                with open(log_path, 'a', encoding='utf-8') as logf:
                    if params.get('text_font_from_yadisk', False) and params.get('text_fontfile'):
                        font_yadisk_path = params['text_fontfile']
                        logf.write(f"Скачивание шрифта с Яндекс Диска: {font_yadisk_path}\n")
                        font_local = yadisk_client.download_file(font_yadisk_path, temp_assets_folder / Path(font_yadisk_path).name)
                        if font_local:
                            params['text_fontfile'] = str(font_local)
                            logf.write(f"Шрифт скачан: {font_local}\n")
                        else:
                            logf.write(f"Ошибка скачивания шрифта: {font_yadisk_path}\n")
                    
                    if params.get('badge_from_yadisk', False) and params.get('badge_path'):
                        badge_yadisk_path = params['badge_path']
                        logf.write(f"Скачивание бейджа с Яндекс Диска: {badge_yadisk_path}\n")
                        badge_local = yadisk_client.download_file(badge_yadisk_path, temp_assets_folder / Path(badge_yadisk_path).name)
                        if badge_local:
                            params['badge_path'] = str(badge_local)
                            logf.write(f"Бейдж скачан: {badge_local}\n")
                        else:
                            logf.write(f"Ошибка скачивания бейджа: {badge_yadisk_path}\n")
    
    if is_test:
        if not video_files:
            job['status'] = 'error'
            job['message'] = 'Не найдено видео для теста в папке.'
            write_job(job)
            return
        video_files = video_files[:1]
    copies_total = 1 if is_test else int(params.get('copies') or 1)

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
    
    log_path = task_log_path

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
            jp = _build_params(job, inp, outp, params, temp_assets_folder=temp_assets_folder)
            cmd = build_ffmpeg_command(jp, dur)
            
            cmd_str = ' '.join(cmd)
            logf.write(f"FFMPEG CMD: {cmd_str}\n")
            
            filter_complex_idx = None
            for i, arg in enumerate(cmd):
                if arg == '-filter_complex' and i + 1 < len(cmd):
                    filter_complex_idx = i + 1
                    break
            if filter_complex_idx is not None:
                logf.write(f"FILTER_COMPLEX: {cmd[filter_complex_idx]}\n")
            
            if jp.text.enabled:
                if jp.text.fontfile:
                    if jp.text.fontfile.exists():
                        logf.write(f"USING FONT: {jp.text.fontfile} (exists: {jp.text.fontfile.exists()})\n")
                    else:
                        logf.write(f"FONT MISSING OR NOT FOUND: {jp.text.fontfile}\n")
                else:
                    logf.write("FONT NOT SPECIFIED (using auto or default)\n")
            if jp.badge.enabled:
                if jp.badge.path:
                    exists_check = jp.badge.path.exists()
                    is_file_check = jp.badge.path.is_file() if exists_check else False
                    logf.write(f"BADGE CHECK: path={jp.badge.path}, exists={exists_check}, is_file={is_file_check}\n")
                    if not exists_check:
                        logf.write(f"BADGE MISSING OR NOT FOUND: {jp.badge.path}\n")
                    else:
                        logf.write(f"USING BADGE: {jp.badge.path}\n")
                else:
                    logf.write("BADGE PATH IS NONE\n")

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

    job['status'] = 'done' if not use_yadisk else 'uploading'
    job['message'] = '' if not use_yadisk else 'Загрузка результатов на Яндекс Диск...'
    write_job(job)
    
    if use_yadisk and yadisk_client and temp_output_folder:
        log_path = task_log_path
        yadisk_output_path = job['output_folder']
        
        original_output_path = yadisk_output_path
        yadisk_output_path = yadisk_client._normalize_disk_path(yadisk_output_path)
        
        with open(log_path, 'a', encoding='utf-8') as logf:
            logf.write(f"Исходный путь выходной папки: {original_output_path}\n")
            logf.write(f"Нормализованный путь выходной папки: {yadisk_output_path}\n")
        
        yadisk_task_path = f"{yadisk_output_path.rstrip('/')}/{job_id}"
        if is_test:
            yadisk_videos_path = f"{yadisk_task_path}/tests"
        else:
            yadisk_videos_path = f"{yadisk_task_path}/videos"
        
        temp_task_output = temp_output_folder / str(job_id)
        if is_test:
            temp_videos_src = temp_task_output / 'tests'
        else:
            temp_videos_src = temp_task_output / 'videos'
        
        with open(log_path, 'a', encoding='utf-8') as logf:
            logf.write(f"Базовый путь выходной папки: {yadisk_output_path}\n")
            logf.write(f"Путь к задаче: {yadisk_task_path}\n")
            logf.write(f"Загрузка обработанных файлов на Яндекс Диск: {yadisk_videos_path}\n")
            logf.write(f"Локальная папка источник: {temp_videos_src}\n")
        
        uploaded_count = 0
        if temp_videos_src.exists():
            uploaded_count = yadisk_client.upload_folder(
                temp_videos_src, 
                yadisk_videos_path, 
                overwrite=True,
                base_path=yadisk_output_path
            )
        
        yadisk_logs_path = f"{yadisk_task_path}/logs"
        if log_path.exists():
            yadisk_log_file_path = f"{yadisk_logs_path}/job.log"
            with open(log_path, 'a', encoding='utf-8') as logf:
                logf.write(f"Загрузка логов на Яндекс Диск: {yadisk_log_file_path}\n")
            
            if yadisk_client.upload_file(log_path, yadisk_log_file_path, overwrite=True, base_path=yadisk_output_path):
                uploaded_count += 1
        
        with open(log_path, 'a', encoding='utf-8') as logf:
            logf.write(f"Загружено {uploaded_count} файлов на Яндекс Диск\n")
    
    if not use_yadisk and temp_base and temp_base.exists():
        log_path = task_log_path
        try:
            shutil.rmtree(temp_base)
            with open(log_path, 'a', encoding='utf-8') as logf:
                logf.write("Временные файлы (шрифты/бейджи) удалены\n")
        except Exception as e:
            with open(log_path, 'a', encoding='utf-8') as logf:
                logf.write(f"Ошибка удаления временных файлов: {e}\n")
    
    job['status'] = 'done'
    job['message'] = ''
    write_job(job)


