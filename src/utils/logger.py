import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from src.utils.paths import get_logs_dir


_LOGGER_CACHE = {}


def get_log_file() -> Path:
    log_dir = get_logs_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / 'app.log'


def get_logger(name: str = 'app') -> logging.Logger:
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    # 防止重复添加 handler（多次导入）
    if not logger.handlers:
        log_file = get_log_file()
        handler = RotatingFileHandler(str(log_file), maxBytes=1_000_000, backupCount=3, encoding='utf-8')
        fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    _LOGGER_CACHE[name] = logger
    return logger
