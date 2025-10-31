import json
import re
from pathlib import Path
from typing import Dict, List, Union
from django.conf import settings
from datetime import datetime

JOBS_ROOT = Path(settings.MEDIA_ROOT) / 'jobs'  # Все задачи здесь 

def _slugify(name: str) -> str:
    name = re.sub(r'[^\w\s-]', '', name).strip().lower()
    name = re.sub(r'[-\s]+', '-', name)
    return name

def _ensure_root():
    JOBS_ROOT.mkdir(parents=True, exist_ok=True)

def _get_unique_job_name(base_name: str) -> str:
    _ensure_root()
    if not base_name:
        p_counter = JOBS_ROOT / 'last_id.txt'
        n = int(p_counter.read_text().strip()) + 1 if p_counter.exists() else 1
        p_counter.write_text(str(n))
        return str(n)

    slug_name = _slugify(base_name)
    if not (JOBS_ROOT / slug_name).exists():
        return slug_name
    counter = 1
    while True:
        unique_name = f"{slug_name}_{counter}"
        if not (JOBS_ROOT / unique_name).exists():
            return unique_name
        counter += 1

def _job_dir(job_id: Union[int, str]) -> Path:
    return JOBS_ROOT / str(job_id)

def job_json_path(job_id: Union[int, str]) -> Path:
    return _job_dir(job_id) / 'job.json'

def job_log_path(job_id: Union[int, str]) -> Path:
    return _job_dir(job_id) / 'job.log'

def create_job(payload: Dict) -> Dict:
    job_name_raw = payload.get('job_name', '')
    job_name = _get_unique_job_name(job_name_raw)
    d = _job_dir(job_name)
    d.mkdir(parents=True, exist_ok=True)
    job = {
        'id': job_name,
        'name': job_name_raw or f"Задача #{job_name}",
        'status': 'queued',
        'progress_overall': 0,
        'total_tasks': 0,
        'done_tasks': 0,
        'input_folder': payload['input_folder'],
        'output_folder': payload['output_folder'],
        'params': payload.get('params', {}),
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'log_path': str(job_log_relpath(job_name)),
        'message': '',
    }
    write_job(job)
    job_log_path(job_name).touch()
    return job

def write_job(job: Dict) -> None:
    p = job_json_path(job['id'])
    p.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(job, ensure_ascii=False, indent=2)
    tmp = p.with_suffix('.json.tmp')
    tmp.write_text(data, encoding='utf-8')
    tmp.replace(p)

def read_job(job_id: Union[int, str]) -> Dict:
    p = job_json_path(job_id)
    return json.loads(p.read_text(encoding='utf-8'))

def job_log_relpath(job_id: Union[int, str]) -> Path:
    return Path('jobs') / str(job_id) / 'job.log'
def list_jobs(limit: int = 20) -> List[Dict]:
    # Возвращаем список job с сортировкой по дате создания
    _ensure_root()
    jobs = []
    all_job_paths = [p for p in JOBS_ROOT.iterdir() if p.is_dir()]
    job_data = []
    for path in all_job_paths:
        json_p = path / 'job.json'
        if json_p.exists():
            try:
                job_data.append(json.loads(json_p.read_text(encoding='utf-8')))
            except Exception:
                continue
    job_data.sort(key=lambda j: j.get('created_at', ''), reverse=True)
    return job_data[:limit]