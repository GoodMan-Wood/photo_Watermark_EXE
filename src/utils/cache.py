import os
import shutil
import time
from pathlib import Path
from typing import Tuple


def get_dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = Path(root) / f
            try:
                total += fp.stat().st_size
            except Exception:
                pass
    return total


def clear_cache_dir(path: Path) -> Tuple[int, int]:
    """Delete all files under path and recreate dir. Returns (files_deleted, bytes_freed)."""
    files_deleted = 0
    bytes_freed = 0
    if path.exists():
        for root, _, files in os.walk(path):
            for f in files:
                fp = Path(root) / f
                try:
                    sz = fp.stat().st_size
                except Exception:
                    sz = 0
                try:
                    fp.unlink(missing_ok=True)
                    files_deleted += 1
                    bytes_freed += sz
                except Exception:
                    pass
    path.mkdir(parents=True, exist_ok=True)
    return files_deleted, bytes_freed


def enforce_cache_quota(path: Path, *, max_bytes: int = 200 * 1024 * 1024, max_files: int = 10000, max_age_days: int = 60) -> Tuple[int, int]:
    """Ensure cache directory stays within limits by deleting old files.
    Returns (files_deleted, bytes_freed).
    """
    now = time.time()
    max_age_sec = max(0, max_age_days) * 24 * 3600
    entries = []  # (path, size, mtime)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return 0, 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = Path(root) / f
            try:
                st = fp.stat()
                entries.append((fp, st.st_size, st.st_mtime))
            except Exception:
                pass

    files_deleted = 0
    bytes_freed = 0

    # 先删过期文件
    if max_age_sec > 0:
        for fp, sz, mt in list(entries):
            if now - mt > max_age_sec:
                try:
                    fp.unlink(missing_ok=True)
                    files_deleted += 1
                    bytes_freed += sz
                    entries.remove((fp, sz, mt))
                except Exception:
                    pass

    # 检查总量与数量
    total_bytes = sum(sz for _, sz, _ in entries)
    total_files = len(entries)

    if total_files <= max_files and total_bytes <= max_bytes:
        return files_deleted, bytes_freed

    # 按 mtime 从旧到新排序，优先删除旧文件
    entries.sort(key=lambda t: t[2])
    i = 0
    while (total_files > max_files or total_bytes > max_bytes) and i < len(entries):
        fp, sz, _ = entries[i]
        try:
            fp.unlink(missing_ok=True)
            files_deleted += 1
            bytes_freed += sz
            total_files -= 1
            total_bytes -= sz
            i += 1
        except Exception:
            i += 1
            pass

    return files_deleted, bytes_freed
