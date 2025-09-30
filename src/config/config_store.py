import json
from pathlib import Path
from src.utils.paths import get_temp_base_dir
from typing import Dict


def get_appdata_dir() -> Path:
    # 为兼容旧版本保留此函数，但内部改为临时目录
    base = get_temp_base_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base


def load_config() -> Dict:
    # 新位置
    base = get_temp_base_dir()
    cfg_dir = base / 'configs'
    cfg_dir.mkdir(parents=True, exist_ok=True)
    p = cfg_dir / 'config.json'
    if p.exists():
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    # 旧位置兼容迁移（AppData/Roaming/PhotoWatermark）
    old = Path.home() / 'AppData' / 'Roaming' / 'PhotoWatermark' / 'config.json'
    if old.exists():
        try:
            data = json.load(open(old, 'r', encoding='utf-8'))
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return data
        except Exception:
            pass
    return {}


def save_config(cfg: Dict):
    base = get_temp_base_dir()
    cfg_dir = base / 'configs'
    cfg_dir.mkdir(parents=True, exist_ok=True)
    p = cfg_dir / 'config.json'
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
