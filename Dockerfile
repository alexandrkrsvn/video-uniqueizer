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

# Dev-friendly default command (для разработки используйте docker-compose override)
# Для продакшена используйте gunicorn (см. docker-compose.prod.yml)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


