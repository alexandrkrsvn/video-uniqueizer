import os
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from yadisk import YaDisk
import logging

try:
    from yadisk.exceptions import YaDiskException
except ImportError:
    YaDiskException = Exception

logger = logging.getLogger(__name__)


class YandexDiskClient:
    """Клиент для работы с Яндекс Диском"""
    
    def __init__(self, token: str):
        """
        Инициализация клиента Яндекс Диска
        
        Args:
            token: OAuth токен Яндекс Диска
        """
        self.disk = YaDisk(token=token)
        self.temp_dir = Path(tempfile.gettempdir()) / 'yadisk_videos'
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def check_connection(self) -> Tuple[bool, str]:
        """
        Проверка подключения к Яндекс Диску
        
        Returns:
            tuple (успешно: bool, сообщение: str)
        """
        try:
            info = self.disk.get_disk_info()
            if info:
                return True, "Подключение успешно"
            return False, "Не удалось получить информацию о диске"
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Ошибка проверки подключения к Яндекс Диску: {e}")
            
            if "401" in error_msg or "Unauthorized" in error_msg or "unauthorized" in error_msg.lower():
                return False, "Неверный токен. Проверьте правильность OAuth токена"
            elif "403" in error_msg or "Forbidden" in error_msg:
                return False, "Доступ запрещен. Проверьте права токена"
            elif "token" in error_msg.lower() or "токен" in error_msg.lower():
                return False, f"Ошибка токена: {error_msg}"
            else:
                return False, f"Ошибка подключения: {error_msg}"
    
    def list_files(self, path: str = '/', limit: int = 1000) -> List[Dict]:
        """
        Получить список файлов и папок на Яндекс Диске
        
        Args:
            path: Путь на Яндекс Диске (по умолчанию корень)
            limit: Максимальное количество элементов
            
        Returns:
            Список словарей с информацией о файлах/папках
        """
        try:
            items = []
            for item in self.disk.listdir(path, limit=limit):
                items.append({
                    'name': item.name,
                    'path': item.path,
                    'type': 'dir' if item.type == 'dir' else 'file',
                    'size': getattr(item, 'size', 0),
                    'modified': str(item.modified) if hasattr(item, 'modified') else None,
                })
            return items
        except YaDiskException as e:
            logger.error(f"Ошибка получения списка файлов: {e}")
            return []
    
    def get_video_files(self, path: str = '/') -> List[Dict]:
        """
        Получить список только видеофайлов из указанной папки (рекурсивно)
        
        Args:
            path: Путь к папке на Яндекс Диске
            
        Returns:
            Список словарей с информацией о видеофайлах
        """
        video_extensions = {'.mp4', '.MP4', '.mov', '.MOV', '.mkv', '.MKV', '.webm', '.WEBM'}
        video_files = []
        
        try:
            def _scan_folder(folder_path: str):
                try:
                    for item in self.disk.listdir(folder_path):
                        if item.type == 'dir':
                            _scan_folder(item.path)
                        elif item.type == 'file':
                            file_name = item.name
                            file_ext = Path(file_name).suffix
                            if file_ext in video_extensions:
                                video_files.append({
                                    'name': file_name,
                                    'path': item.path,
                                    'size': getattr(item, 'size', 0),
                                    'modified': str(item.modified) if hasattr(item, 'modified') else None,
                                })
                except YaDiskException as e:
                    logger.error(f"Ошибка при сканировании папки {folder_path}: {e}")
            
            _scan_folder(path)
            return video_files
        except Exception as e:
            logger.error(f"Ошибка получения видеофайлов: {e}")
            return []
    
    def count_videos(self, path: str = '/') -> int:
        """
        Подсчитать количество видеофайлов в папке
        
        Args:
            path: Путь к папке на Яндекс Диске
            
        Returns:
            Количество видеофайлов
        """
        return len(self.get_video_files(path))
    
    def download_file(self, disk_path: str, local_path: Optional[Path] = None) -> Optional[Path]:
        """
        Скачать файл с Яндекс Диска
        
        Args:
            disk_path: Путь к файлу на Яндекс Диске
            local_path: Локальный путь для сохранения (если None - используется временная папка)
            
        Returns:
            Path к скачанному файлу или None в случае ошибки
        """
        try:
            if local_path is None:
                file_name = Path(disk_path).name
                local_path = self.temp_dir / file_name
            
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Скачиваем файл
            self.disk.download(disk_path, str(local_path))
            
            return local_path
        except YaDiskException as e:
            logger.error(f"Ошибка скачивания файла {disk_path}: {e}")
            return None
    
    def download_folder_videos(self, disk_folder_path: str, local_folder: Path) -> List[Path]:
        """
        Скачать все видеофайлы из папки на Яндекс Диске
        
        Args:
            disk_folder_path: Путь к папке на Яндекс Диске
            local_folder: Локальная папка для сохранения файлов
            
        Returns:
            Список путей к скачанным файлам
        """
        local_folder.mkdir(parents=True, exist_ok=True)
        video_files = self.get_video_files(disk_folder_path)
        downloaded_files = []
        
        for video_file in video_files:
            disk_path = video_file['path']
            relative_path = disk_path.replace(disk_folder_path, '').lstrip('/')
            local_path = local_folder / relative_path
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            downloaded_path = self.download_file(disk_path, local_path)
            if downloaded_path:
                downloaded_files.append(downloaded_path)
        
        return downloaded_files
    
    def _normalize_disk_path(self, disk_path: str, for_api: bool = False) -> str:
        """
        Нормализует путь на Яндекс Диске.
        
        Args:
            disk_path: Путь на Яндекс Диске (может быть в разных форматах)
            for_api: Если True, возвращает путь для API (без /disk/), иначе с /disk/
            
        Returns:
            Нормализованный путь
        """
        if not disk_path:
            return '/' if for_api else '/disk'
        
        disk_path = disk_path.strip()
        
        if disk_path.startswith('disk:/'):
            disk_path = disk_path[6:]
        elif disk_path.startswith('disk:'):
            disk_path = disk_path[5:]
        
        if disk_path.startswith('/disk/'):
            disk_path = disk_path[6:]
        elif disk_path.startswith('/disk'):
            disk_path = disk_path[5:]
        
        if not disk_path.startswith('/'):
            disk_path = '/' + disk_path
        
        while '//' in disk_path:
            disk_path = disk_path.replace('//', '/')
        
        if not for_api:
            if not disk_path.startswith('/disk/'):
                disk_path = '/disk' + disk_path
        
        return disk_path
    
    def _path_for_api(self, disk_path: str) -> str:
        """
        Преобразует путь в формат для API YaDisk (без префикса /disk/).
        
        Args:
            disk_path: Путь на Яндекс Диске
            
        Returns:
            Путь без префикса /disk/ для передачи в API
        """
        return self._normalize_disk_path(disk_path, for_api=True)
    
    def _ensure_path_exists(self, disk_path: str, base_path: Optional[str] = None):
        """
        Создает промежуточные папки на Яндекс Диске для указанного пути.
        Если указан base_path, создает только новые папки относительно него.
        
        Args:
            disk_path: Полный путь на Яндекс Диске
            base_path: Базовый путь, который уже существует (опционально)
        """
        disk_path = self._normalize_disk_path(disk_path)
        
        if base_path:
            base_path = self._normalize_disk_path(base_path)
            
            if not disk_path.startswith(base_path.rstrip('/')):
                base_path = None
            else:
                relative = disk_path[len(base_path.rstrip('/')):].lstrip('/')
                if not relative:
                    return
                
                parts = relative.split('/')
                current_path = base_path.rstrip('/')
                
                for part in parts:
                    if not part:
                        continue
                    current_path = f"{current_path}/{part}"
                    api_path = self._path_for_api(current_path)
                    try:
                        self.disk.mkdir(api_path)
                    except YaDiskException as e:
                        error_str = str(e).lower()
                        if 'already exists' not in error_str and 'существует' not in error_str:
                            logger.debug(f"Ошибка создания папки {current_path}: {e}")
                        pass
                return
        
        parts = disk_path.strip('/').split('/')
        if not parts or parts[0] == '':
            return
        
        current_path = ''
        for part in parts:
            if not part:
                continue
            if current_path:
                current_path = f"{current_path}/{part}"
            else:
                current_path = f"/{part}"
            
            api_path = self._path_for_api(current_path)
            try:
                self.disk.mkdir(api_path)
            except YaDiskException:
                pass
    
    def upload_file(self, local_path: Path, disk_path: str, overwrite: bool = True, base_path: Optional[str] = None) -> bool:
        """
        Загрузить файл на Яндекс Диск
        
        Args:
            local_path: Путь к локальному файлу
            disk_path: Путь на Яндекс Диске для сохранения
            overwrite: Перезаписывать существующий файл
            base_path: Базовый путь, который уже существует (опционально)
            
        Returns:
            True если успешно, False в случае ошибки
        """
        try:
            disk_path = self._normalize_disk_path(disk_path)
            
            disk_path_clean = disk_path.rstrip('/')
            last_slash = disk_path_clean.rfind('/')
            if last_slash >= 0:
                parent_dir = disk_path_clean[:last_slash]
                if parent_dir:
                    self._ensure_path_exists(parent_dir, base_path=base_path)
            
            api_path = self._path_for_api(disk_path)
            self.disk.upload(str(local_path), api_path, overwrite=overwrite)
            return True
        except YaDiskException as e:
            logger.error(f"Ошибка загрузки файла {local_path} на {disk_path}: {e}")
            return False
    
    def upload_folder(self, local_folder: Path, disk_folder_path: str, overwrite: bool = True, base_path: Optional[str] = None) -> int:
        """
        Загрузить все файлы из локальной папки на Яндекс Диск
        
        Args:
            local_folder: Локальная папка с файлами
            disk_folder_path: Путь к папке на Яндекс Диске
            overwrite: Перезаписывать существующий файл
            base_path: Базовый путь, который уже существует (опционально)
            
        Returns:
            Количество успешно загруженных файлов
        """
        uploaded_count = 0
        
        disk_folder_path = self._normalize_disk_path(disk_folder_path)
        
        self._ensure_path_exists(disk_folder_path, base_path=base_path)
        
        for file_path in local_folder.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(local_folder)
                disk_file_path = f"{disk_folder_path.rstrip('/')}/{str(relative_path).replace(chr(92), '/')}"
                
                if self.upload_file(file_path, disk_file_path, overwrite=overwrite, base_path=base_path):
                    uploaded_count += 1
        
        return uploaded_count
    
    def cleanup_temp(self):
        """Очистить временные файлы"""
        try:
            import shutil
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            logger.error(f"Ошибка очистки временных файлов: {e}")


def get_yadisk_client() -> Optional[YandexDiskClient]:
    """
    Получить клиент Яндекс Диска с токеном из настроек
    
    Returns:
        YandexDiskClient или None если токен не настроен
    """
    from django.conf import settings
    token = getattr(settings, 'YANDEX_DISK_TOKEN', None)
    if not token or not token.strip():
        logger.warning("YANDEX_DISK_TOKEN не настроен или пуст")
        return None
    return YandexDiskClient(token.strip())


