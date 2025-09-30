import json
from pathlib import Path
from typing import Dict


def get_appdata_dir() -> Path:
    base = Path.home() / 'AppData' / 'Roaming' / 'PhotoWatermark'
    base.mkdir(parents=True, exist_ok=True)
    return base


def load_config() -> Dict:
    p = get_appdata_dir() / 'config.json'
    if not p.exists():
        return {}
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(cfg: Dict):
    p = get_appdata_dir() / 'config.json'
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
