import json
from pathlib import Path
from typing import Dict, Optional


class TemplateManager:
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_template(self, name: str, config: Dict) -> Path:
        path = self.storage_dir / f"{name}.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return path

    def load_template(self, name: str) -> Optional[Dict]:
        path = self.storage_dir / f"{name}.json"
        if not path.exists():
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
