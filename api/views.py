from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .serializers import JobSerializer
from .forms import JobForm
from .tasks import start_job_thread
from .store import create_job, list_jobs, read_job, job_log_relpath
from django.http import JsonResponse, FileResponse, Http404
from pathlib import Path
from django.conf import settings
from .yadisk_client import get_yadisk_client
import json
import os

@require_http_methods(["GET", "POST"])
def index(request):
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            action = request.POST.get('action', 'batch')
            use_yadisk = data.get('use_yadisk', False)
            
            if use_yadisk:
                input_folder = data.get('input_yadisk_path', '').strip()
                output_folder = data.get('output_yadisk_path', '').strip()
                if not input_folder or not output_folder:
                    form.add_error(None, 'При использовании Яндекс Диска необходимо указать пути к папкам на Яндекс Диске')
                    jobs = list_jobs(20)
                    return render(request, 'job_form.html', { 'form': form, 'jobs': jobs })
            else:
                input_folder = data.get('input_folder', '').strip()
                output_folder = data.get('output_folder', '').strip()
                if not input_folder or not output_folder:
                    form.add_error(None, 'Необходимо указать пути к локальным папкам')
                    jobs = list_jobs(20)
                    return render(request, 'job_form.html', { 'form': form, 'jobs': jobs })
            
            params = {k: v for k, v in data.items() if k not in [
                'job_name', 'input_folder', 'output_folder', 'use_yadisk', 
                'input_yadisk_path', 'output_yadisk_path',
                'text_font_from_yadisk', 'text_fontfile_yadisk',
                'badge_from_yadisk', 'badge_path_yadisk'
            ]}
            
            if data.get('text_font_from_yadisk', False):
                params['text_fontfile'] = data.get('text_fontfile_yadisk', '')
                params['text_font_from_yadisk'] = True
            else:
                params['text_fontfile'] = data.get('text_fontfile', '')
                params['text_font_from_yadisk'] = False
                
            if data.get('badge_from_yadisk', False):
                params['badge_path'] = data.get('badge_path_yadisk', '')
                params['badge_from_yadisk'] = True
            else:
                params['badge_path'] = data.get('badge_path', '')
                params['badge_from_yadisk'] = False
            
            params['is_test'] = (action == 'test')
            params['use_yadisk'] = use_yadisk
            
            job_payload = {
                'job_name': data.get('job_name', ''),
                'input_folder': input_folder,
                'output_folder': output_folder,
                'params': params,
            }
            if params['is_test']:
                job_name = data.get('job_name', '') or 'run'
                job_payload['job_name'] = f"test_{job_name}"
            new_job = create_job(job_payload)
            start_job_thread(new_job['id'])
            return redirect('job_detail', pk=new_job['id'])
    else:
        form = JobForm()

    jobs = list_jobs(20)
    return render(request, 'job_form.html', { 'form': form, 'jobs': jobs })

def job_detail(request, pk):
    job = read_job(pk)
    return render(request, 'job_detail.html', { 'job': job })

def count_videos(request):
    base = request.GET.get('input') or ''
    try:
        p = Path(base)
        if not p.exists() or not p.is_dir():
            return JsonResponse({"count": 0})
        exts = ["*.mp4","*.MP4","*.mov","*.MOV","*.mkv","*.MKV","*.webm","*.WEBM"]
        files = set()
        for pattern in exts:
            files.update(p.rglob(pattern))
        return JsonResponse({"count": len(files)})
    except Exception:
        return JsonResponse({"count": 0})

class JobViewSet(viewsets.ViewSet):
    def list(self, request):
        jobs = list_jobs(50)
        return Response(jobs)

    def retrieve(self, request, pk=None):
        job = read_job(pk)
        return Response(job)

@api_view(['GET'])
def yadisk_check(request):
    """Проверка подключения к Яндекс Диску"""
    try:
        client = get_yadisk_client()
        if not client:
            return JsonResponse({
                "connected": False, 
                "error": "Токен Яндекс Диска не настроен. Установите переменную окружения YANDEX_DISK_TOKEN или создайте файл .env"
            })
        
        try:
            connected, message = client.check_connection()
            if connected:
                return JsonResponse({"connected": True, "message": message})
            else:
                return JsonResponse({"connected": False, "error": message})
        except Exception as e:
            return JsonResponse({"connected": False, "error": f"Неожиданная ошибка: {str(e)}"})
    except Exception as e:
        return JsonResponse({"connected": False, "error": f"Ошибка инициализации клиента: {str(e)}"})

@api_view(['GET'])
def yadisk_list(request):
    """Получить список файлов и папок на Яндекс Диске"""
    client = get_yadisk_client()
    if not client:
        return JsonResponse({"error": "Токен Яндекс Диска не настроен"}, status=400)
    
    path = request.GET.get('path', '/')
    file_type = request.GET.get('type', 'all')  # 'all', 'files', 'dirs'
    
    try:
        items = client.list_files(path)
        
        # Фильтруем по типу, если указан
        if file_type == 'files':
            items = [item for item in items if item.get('type') == 'file']
        elif file_type == 'dirs':
            items = [item for item in items if item.get('type') == 'dir']
            
        return JsonResponse({"items": items})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@api_view(['GET'])
def yadisk_count_videos(request):
    """Подсчитать количество видеофайлов в папке на Яндекс Диске"""
    client = get_yadisk_client()
    if not client:
        return JsonResponse({"count": 0, "error": "Токен Яндекс Диска не настроен"})
    
    path = request.GET.get('path', '/')
    try:
        count = client.count_videos(path)
        return JsonResponse({"count": count})
    except Exception as e:
        return JsonResponse({"count": 0, "error": str(e)})

def download_log(request, pk):
    try:
        job = read_job(pk)
        log_path_str = job.get('log_path')
        if not log_path_str:
            raise Http404("Лог не найден")
        
        log_path = Path(log_path_str)
        
        if log_path.is_absolute():
            full_path = log_path
        else:
            media_root = Path(settings.MEDIA_ROOT)
            full_path = media_root / log_path
            
            if not full_path.exists() and job.get('output_folder'):
                output_folder = Path(job['output_folder'])
                if output_folder.is_absolute():
                    alt_path = output_folder / str(pk) / 'logs' / 'job.log'
                    if alt_path.exists():
                        full_path = alt_path
        
        if not full_path.exists():
            raise Http404("Файл лога не найден")
        
        return FileResponse(
            open(full_path, 'rb'),
            as_attachment=True,
            filename=f'job_{pk}_log.txt'
        )
    except FileNotFoundError:
        raise Http404("Лог не найден")
    except Exception as e:
        raise Http404(f"Ошибка: {str(e)}")