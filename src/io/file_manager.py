import os
from typing import List


SUPPORTED_EXT = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff'}


def list_images_in_folder(folder_path: str) -> List[str]:
    """Return list of image file paths under folder_path (non-recursive)."""
    files = []
    for name in os.listdir(folder_path):
        lower = name.lower()
        _, ext = os.path.splitext(lower)
        if ext in SUPPORTED_EXT:
            files.append(os.path.join(folder_path, name))
    return files
