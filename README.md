# Видео Уникализатор — веб

Веб-сервис для массовой обработки видео с добавлением уникальных эффектов, текста и бейджей. Использует FFmpeg для быстрого и прозрачного пакетного рендеринга с поддержкой NVENC.

## Возможности

- **Массовая обработка**: Рекурсивный поиск видео в папке (MP4, MOV, MKV, WEBM)
- **Множественные копии**: Создание до 50 уникальных копий каждого видео
- **Форматы вывода**: 1:1 (720x720), 9:16 (720x1280), 16:9 (1280x720)
- **Эффекты уникализации**: Микросрезы, контраст, оттенки, шум, яркость, обрезка
- **Анимация**: Движущийся текст, геометрические искажения, временная модуляция
- **Текст и бейджи**: Настраиваемые шрифты, позиции, размеры
- **Аппаратное ускорение**: Автоопределение и использование NVENC
- **Метаданные**: Рандомизация всех метаданных видео
- **Прогресс**: Отслеживание общего и текущего прогресса
- **REST API**: Мониторинг задач через API, подсчет видео
- **Интеграция с Яндекс Диском**: Загрузка видео с Яндекс Диска, обработка на сервере и выгрузка результатов обратно

## Требования

- Python 3.8+
- FFmpeg (обязательно в PATH)
- Django 5.0+
- djangorestframework
- yadisk (для работы с Яндекс Диском)

## Установка

1. Установите FFmpeg и добавьте в PATH
2. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Запуск

### Веб-сервер (Django)


Сервис доступен по адресу 

## API

Сервис предоставляет REST API для мониторинга задач и подсчета видео.

### Базовый URL
```

```

### Endpoints

#### 1. Получить список задач
**GET** `/api/jobs/`

Возвращает список последних 50 задач с сортировкой по дате создания (новые сверху).

**Ответ:**
```json
[
  {
    "id": "my_job_1",
    "name": "Задача #1",
    "status": "running",
    "progress_overall": 45,
    "total_tasks": 10,
    "done_tasks": 4,
    "src_files_total": 5,
    "input_folder": "C:/videos/input",
    "output_folder": "C:/videos/output",
    "created_at": "2025-01-15T12:00:00Z",
    "log_path": "jobs/my_job_1/job.log",
    "message": ""
  }
]
```

**Статусы:**
- `queued` — задача в очереди
- `running` — выполняется
- `done` — завершена
- `error` — ошибка

#### 2. Получить детали задачи
**GET** `/api/jobs/<job_id>/`

Возвращает полную информацию о задаче по её ID.

**Параметры:**
- `job_id` (string) — идентификатор задачи

**Пример:**
```
GET /api/jobs/my_job_1/
```

**Ответ:**
```json
{
  "id": "my_job_1",
  "name": "Задача #1",
  "status": "running",
  "progress_overall": 45,
  "total_tasks": 10,
  "done_tasks": 4,
  "src_files_total": 5,
  "input_folder": "C:/videos/input",
  "output_folder": "C:/videos/output",
  "params": {
    "fmt": "9:16",
    "copies": 2,
    "text_enabled": true,
    ...
  },
  "created_at": "2025-01-15T12:00:00Z",
  "log_path": "jobs/my_job_1/job.log",
  "message": ""
}
```

#### 3. Подсчет видео в папке
**GET** `/api/count_videos?input=<path>`

Подсчитывает количество видеофайлов (MP4, MOV, MKV, WEBM) в указанной папке рекурсивно.

**Параметры:**
- `input` (string, query) — путь к папке

**Пример:**
```
GET /api/count_videos?input=C:/videos/input
```

**Ответ:**
```json
{
  "count": 15
}
```

### Создание задач

**Примечание:** В текущей версии создание задач доступно только через веб-интерфейс (`POST /`). Для создания задачи используйте форму на главной странице.

**Веб-интерфейс:**
- `GET /` — форма создания задачи и список задач
- `POST /` — создание новой задачи (form-data)
- `GET /jobs/<job_id>/` — детали задачи с прогрессом в реальном времени



## Архитектура

### Основные классы

#### `ProcessorWorker(QObject)`
Фоновый обработчик задач. Выполняет FFmpeg команды в отдельном потоке.

**Основные методы:**
- `__init__(tasks)` — инициализация с списком задач
- `run()` — основной цикл обработки
- `request_stop()` — остановка текущей задачи
- `_nvenc_to_x264(cmd)` — fallback с NVENC на x264

**Сигналы:**
- `log_message(str)` — сообщения в лог
- `status_changed(str)` — изменение статуса
- `overall_progress(int)` — общий прогресс
- `current_progress(int)` — прогресс текущего файла
- `task_changed(str)` — смена задачи
- `finished()` — завершение обработки

#### `VideoProcessor(QWidget)`
Главное окно приложения с UI и логикой обработки.

**Основные методы:**
- `__init__()` — создание UI и инициализация
- `start_processing()` — запуск обработки
- `stop_processing()` — остановка обработки
- `build_ffmpeg_command()` — построение FFmpeg команды
- `calc_position()` — расчет позиции текста/бейджа
- `random_metadata()` — генерация случайных метаданных

## Логика работы по шагам

### 1. Инициализация
- Создание UI элементов
- Определение поддержки NVENC
- Валидация NVENC через тестовое кодирование
- Настройка папок по умолчанию (`./input`, `./output`)

### 2. Подготовка задач
- Рекурсивный поиск видеофайлов
- Определение длительности каждого видео через `ffprobe`
- Создание списка задач для каждой копии
- Расчет общего количества задач

### 3. Обработка видео
- Запуск `ProcessorWorker` в отдельном потоке
- Для каждой задачи:
  - Построение FFmpeg команды
  - Запуск FFmpeg с мониторингом прогресса
  - Обработка ошибок и fallback на x264
  - Обновление прогресса

### 4. Построение FFmpeg команды

#### Базовые параметры
- Входной файл: `-i input.mp4`
- Потоки: `-threads N` (количество ядер CPU)
- Выходной файл: `output_v1.mp4`

#### Видео фильтры (в порядке применения)
1. **Обрезка**: `trim=start=X,setpts=PTS-STARTPTS`
2. **Контраст**: `eq=contrast=X`
3. **Оттенок**: `hue=h=X`
4. **Шум**: `noise=alls=X:allf=t`
5. **Яркость/насыщенность**: `eq=brightness=X:saturation=Y`
6. **Обрезка краев**: `crop=iw*X:ih*Y:offset_x:offset_y`
7. **Геометрия**: `rotate=X*sin(2*PI*t)` + `scale=iw*(1+Y*sin(2*PI*t*0.3)):ih*(1+Y*sin(2*PI*t*0.3))`
8. **Оверлеи**: `gblur=sigma=X` + `vignette=PI/6:Y`
9. **Временная модуляция**: `setpts=(1.0+X)*PTS`
10. **Масштабирование**: `scale=W:H:force_original_aspect_ratio=decrease,pad=W:H:(ow-iw)/2:(oh-ih)/2:black,setsar=1`
11. **Текст**: `drawtext=text='TEXT':fontfile='FONT':fontsize=SIZE:fontcolor=COLOR:x=X:y=Y:bordercolor=black:borderw=3:shadowcolor=black@0.5:shadowx=2:shadowy=2`
12. **Скрытая сетка**: `drawgrid=width=64:height=64:thickness=1:color=white@0.03`

#### Аудио фильтры
- Временная модуляция: `atempo=X` (синхронизировано с видео)

#### Бейдж (если включен)
- Масштабирование: `[1:v]fps=30,scale=W:-1:flags=bilinear`
- Colorkey для PNG/GIF: `colorkey=0xFFFFFF:0.1:0.1`
- Формат: `format=rgba[logo]`
- Наложение: `[bg][logo]overlay=X:Y:shortest=1:eof_action=pass`

#### Кодек
- **NVENC** (если доступен): `-c:v h264_nvenc -preset p3 -cq 23 -g 48 -pix_fmt yuv420p`
- **x264** (fallback): `-c:v libx264 -crf 22 -g 48 -preset veryfast -pix_fmt yuv420p`

#### Аудио кодек
- `-c:a aac -b:a 128k`

#### Метаданные
- Случайные: title, encoder, artist, comment, make, model, creation_time, genre, description, year, software, copyright
- Дополнительные: publisher, album, track, duration

### 5. Мониторинг прогресса
- Парсинг вывода FFmpeg с `-progress -`
- Извлечение `out_time_ms`, `out_time_us`, `out_time`, `progress`
- Расчет процента выполнения на основе длительности
- Обновление UI в реальном времени

### 6. Обработка ошибок
- Автоматический fallback NVENC → x264
- Логирование всех ошибок
- Возможность остановки процесса
- Валидация входных файлов

## Настройки эффектов

### Профили уникализации
- **Мягкая**: Базовые амплитуды эффектов
- **Сильная**: Увеличенные амплитуды (×1.4-1.6)

### Безопасный режим
- Отключает агрессивные эффекты (обрезка, оттенки, шум, геометрия, оверлеи, временная модуляция)
- Обеспечивает стабильность обработки

### Позиционирование
- **Текст**: 9 позиций + анимация движения
- **Бейдж**: 9 позиций + случайный масштаб
- **Автоматический расчет** размеров под выбранный формат

## Структура проекта

```
video_service/
├── manage.py          # Django management script
├── api/               # API приложение
│   ├── forms.py       # Формы для веб-интерфейса
│   ├── views.py       # Views и API endpoints
│   ├── serializers.py # DRF serializers
│   ├── tasks.py       # Логика обработки задач
│   ├── store.py       # Хранилище задач (файловое)
│   └── urls.py        # URL routing
├── video_core/        # Ядро обработки видео
│   ├── ffmpeg_builder.py  # Построение FFmpeg команд
│   ├── ffmpeg_runner.py   # Запуск FFmpeg с прогрессом
│   ├── params.py           # Параметры задач
│   ├── positions.py       # Расчет позиций
│   ├── probe.py           # Получение информации о видео
│   └── metadata.py        # Генерация метаданных
├── videosvc/          # Настройки Django
│   ├── settings.py
│   └── urls.py
├── templates/         # HTML шаблоны
├── media/             # Хранилище задач и логов
├── requirements.txt   # Зависимости
└── README.md          # Документация
```

## Используемые библиотеки

### Стандартная библиотека Python
- `sys` — запуск приложения
- `os` — получение количества ядер CPU
- `subprocess` — вызов FFmpeg/ffprobe
- `random` — генерация случайных значений
- `datetime` — работа с датами в метаданных
- `pathlib` — работа с файловыми путями
- `threading` — асинхронная обработка задач
- `json` — работа с конфигурацией задач

### Django и Django REST Framework
- `Django` — веб-фреймворк
- `djangorestframework` — REST API
- `Django Forms` — формы для веб-интерфейса

### Внешние утилиты
- **FFmpeg** — обработка видео/аудио
- **ffprobe** — получение информации о медиафайлах

## Примеры использования

### Базовое использование
1. Выберите папку с исходными видео
2. Выберите папку для сохранения
3. Настройте параметры (текст, бейдж, эффекты)
4. Нажмите "Старт обработки"

### Продвинутые настройки
- **Текст**: Выберите шрифт, размер, позицию, включите анимацию
- **Бейдж**: Загрузите PNG/GIF/MP4, настройте масштаб и позицию
- **Эффекты**: Включите нужные фильтры, выберите профиль
- **Копии**: Установите количество уникальных копий на файл

## Устранение неполадок

### FFmpeg не найден
- Убедитесь, что FFmpeg установлен и добавлен в PATH
- Проверьте: `ffmpeg -version` в командной строке

### NVENC
- Убедитесь, что FFmpeg собран с поддержкой NVENC
- Приложение автоматически переключится на x264

### Ошибки обработки
- Включите "Безопасный режим" для стабильности
- Проверьте формат входных файлов
- Убедитесь в наличии свободного места

## Производительность

- **NVENC**: ~3-5x быстрее CPU кодирования
- **x264 veryfast**: Оптимизирован для скорости
- **Многопоточность**: Использует все ядра CPU
- **Память**: Минимальное потребление благодаря потоковой обработке

## ОС и запуск

Проект поддерживает **Windows** и **Linux** (Ubuntu, Debian и др.)

### Для Ubuntu

1. Установите Python 3.8+ (`sudo apt install python3 python3-venv python3-pip`)
2. Установите FFmpeg c поддержкой NVENC:
   - NVIDIA: установите драйверы (`sudo apt install nvidia-driver-535 nvidia-utils`)
   - FFmpeg: `sudo apt install ffmpeg`
   - Проверьте поддержку nvenc: `ffmpeg -encoders | grep nvenc` (должны быть строки h264_nvenc, hevc_nvenc)
3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
4. Убедитесь, что выбранный шрифт для drawtext реально существует в вашей системе — например, `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf` или скачайте требуемый ttf/otf.
5. Запуск:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

- Исходные и результатирующие видео, а также логи, будут храниться в папке `media/jobs/`.
- Режимы кодирования выбираются автоматически. Если NVENC не доступен — будет использоваться CPU (x264).
- Интерфейс API и web одинаковы вне зависимости от ОС.

### Для Windows

1. Установите Python 3.8+ с [python.org](https://www.python.org/downloads/)
2. Установите FFmpeg:
   - Скачайте с [ffmpeg.org](https://ffmpeg.org/download.html)
   - Добавьте в PATH
   - Проверьте: `ffmpeg -version` в командной строке
3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
4. Запуск:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

Сервис будет доступен по адресу 

## Ограничения

- Требует FFmpeg (обязательно в PATH)
- Работает на Windows и Linux (Ubuntu/Debian). Для ускорения видеообработки NVENC поддерживается только при наличии совместимой видеокарты и драйверов NVIDIA
- Максимум 50 копий на файл (ограничение UI)

## Развертывание на сервере (Docker, Ubuntu)

- Образ в Docker Hub: `yourname/videosvc:latest` (замените на ваш)
- Фиксированные папки (на сервере → внутри контейнера):
  - `/opt/video_service_data/input` → `/data/input` (исходники)
  - `/opt/video_service_data/output` → `/data/output` (результат)
  - `/opt/video_service/media` → `/app/media` (логи/задачи)

Шаги на сервере:

```bash
# 1) Подготовка директорий
sudo mkdir -p /opt/video_service
sudo mkdir -p /opt/video_service_data/{input,output}
sudo mkdir -p /opt/video_service/media

# 2) .env (секреты и настройки)
sudo tee /opt/video_service/.env >/dev/null <<'EOF'
DJANGO_SECRET_KEY=<<СЕКРЕТ_БЕЗ_СКОБОК>>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=77.239.108.88,localhost,127.0.0.1
TZ=Europe/Moscow
EOF

# 3) docker-compose.prod.yml (замените yourname на ваш репозиторий)
sudo tee /opt/video_service/docker-compose.prod.yml >/dev/null <<'YAML'
services:
  videosvc:
    image: yourname/videosvc:latest
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file: .env
    command: ["python","-m","gunicorn","-w","3","-b","0.0.0.0:8000","videosvc.wsgi:application"]
    volumes:
      - /opt/video_service_data/input:/data/input:ro
      - /opt/video_service_data/output:/data/output
      - /opt/video_service/media:/app/media
YAML

# 4) Запуск
cd /opt/video_service
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

Доступ: `http://77.239.108.88:8000`

- В форме указывайте:
  - `input_folder`: `/data/input`
  - `output_folder`: `/data/output`
  - `badge_path` (опционально): `/data/pag/logo.png`

### Работа с Яндекс Диском

Сервис поддерживает работу с Яндекс Диском для загрузки видео, обработки на сервере и выгрузки результатов.

#### Настройка Яндекс Диска

1. **Получите OAuth токен Яндекс Диска:**
   - Перейдите на https://oauth.yandex.ru/
   - Создайте новое приложение
   - Получите OAuth токен с правами доступа к Яндекс Диску

2. **Настройте токен в переменных окружения:**
   
   ```bash
   # В .env файле добавьте:
   YANDEX_DISK_TOKEN=ваш_oauth_токен
   ```
   
   Или экспортируйте переменную окружения:
   ```bash
   export YANDEX_DISK_TOKEN=ваш_oauth_токен
   ```

3. **Использование:**
   - В веб-интерфейсе отметьте чекбокс "Использовать Яндекс Диск"
   - Выберите папку на Яндекс Диске с исходными видео (кнопка "Выбрать папку")
   - Выберите папку на Яндекс Диске для сохранения результатов
   - Запустите обработку

4. **Как это работает:**
   - Сервис автоматически скачивает все видеофайлы из выбранной папки на Яндекс Диске во временную папку на сервере
   - Обрабатывает видео локально на сервере
   - Загружает обработанные файлы обратно на Яндекс Диск в указанную папку
   - Автоматически удаляет временные файлы после завершения

#### API для Яндекс Диска

- **GET** `/api/yadisk/check` — проверка подключения к Яндекс Диску
- **GET** `/api/yadisk/list?path=<путь>` — получение списка файлов и папок на Яндекс Диске
- **GET** `/api/yadisk/count_videos?path=<путь>` — подсчет видеофайлов в папке на Яндекс Диске

### Загрузка и выгрузка видео (сервер - локальная файловая система)

- Куда класть исходники: `/opt/video_service_data/input`
- Откуда забирать результат: `/opt/video_service_data/output`

Из Windows (PowerShell, OpenSSH):
```powershell
# один файл
scp "C:\\Path\\to\\video.mp4" root@77.239.108.88:/opt/video_service_data/input/
# папка
scp -r "C:\\Path\\to\\videos\\*" root@77.239.108.88:/opt/video_service_data/input/
```

Из Linux/macOS:
```bash
scp /path/video.mp4 root@77.239.108.88:/opt/video_service_data/input/
scp -r /path/videos/* root@77.239.108.88:/opt/video_service_data/input/
```

Забрать результаты (Windows):
```powershell
scp -r root@77.239.108.88:/opt/video_service_data/output/* "C:\\Users\\Aorus\\Downloads\\rendered\\"
```

Забрать результаты (Linux/macOS):
```bash
scp -r root@77.239.108.88:/opt/video_service_data/output/* ~/Downloads/rendered/
```

Проверка на сервере:
```bash
ls -la /opt/video_service_data/input | head
ls -la /opt/video_service_data/output | head
# внутри контейнера
docker compose -f /opt/video_service/docker-compose.prod.yml exec videosvc ls -la /data/input | head
```

### Логи задач

- Файлы логов: `/opt/video_service/media/jobs/<job_id>/job.log`

```bash
# последние 50 строк
tail -n 50 /opt/video_service/media/jobs/<job_id>/job.log
```

### Обновление сервиса (образ из Docker Hub)

```bash
cd /opt/video_service
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

### Автозапуск и фаервол

```bash
sudo systemctl enable --now docker
sudo ufw allow 8000/tcp
```
