from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets
from rest_framework.response import Response
from .serializers import JobSerializer
from .forms import JobForm
from .tasks import start_job_thread
from .store import create_job, list_jobs, read_job
from django.http import JsonResponse
from pathlib import Path

@require_http_methods(["GET", "POST"])
def index(request):
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            action = request.POST.get('action', 'batch')
            params = {k: v for k, v in data.items() if k not in ['job_name', 'input_folder', 'output_folder']}
            params['is_test'] = (action == 'test')
            job_payload = {
                'job_name': data.get('job_name', ''),
                'input_folder': data['input_folder'],
                'output_folder': data['output_folder'],
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