from pathlib import Path
import tempfile


def get_temp_base_dir() -> Path:
    # 使用系统临时目录，便于 Windows Storage Sense/磁盘清理自动清理
    return Path(tempfile.gettempdir()) / 'PhotoWatermark'


def get_cache_dir() -> Path:
    return get_temp_base_dir() / 'cache' / 'thumbnails'


def get_logs_dir() -> Path:
    return get_temp_base_dir() / 'logs'


def get_templates_dir() -> Path:
    return get_temp_base_dir() / 'templates'
