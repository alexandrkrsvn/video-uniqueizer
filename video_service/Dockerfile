FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg tzdata && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install -r requirements.txt && \
    pip install gunicorn

COPY . /app

EXPOSE 8000

CMD ["python", "-m", "gunicorn", "-w", "3", "-b", "0.0.0.0:8000", "videosvc.wsgi:application"]


