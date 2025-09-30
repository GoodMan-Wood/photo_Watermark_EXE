from pathlib import Path
from typing import Optional

from PySide6.QtGui import QImage
from PySide6.QtCore import Qt

from src.core.image_processor import compose_export_qimage


def export_image(image_path: str, watermark_config: dict, out_path: str, fmt: Optional[str] = None, quality: Optional[int] = None, target_size: Optional[tuple] = None) -> str:
    """
    Export the given image with watermark applied to out_path.
    - image_path: source image path
    - watermark_config: same fields as compose_preview_qpixmap/compose_export_qimage
    - out_path: target file path (extension decides format unless fmt specified)
    - fmt: optional format override, e.g., 'PNG' or 'JPEG'
    - quality: optional quality (0-100) for lossy formats

    Returns the output path on success; raises on failure.
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    qimg: Optional[QImage] = compose_export_qimage(image_path, watermark_config)
    if qimg is None or qimg.isNull():
        raise ValueError(f"Failed to load or compose image: {image_path}")

    # optional resize prior to save
    if target_size and len(target_size) == 2:
        w, h = int(target_size[0]), int(target_size[1])
        if w > 0 and h > 0:
            qimg = qimg.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

    # Determine format from extension if not provided
    if fmt is None:
        ext = out.suffix.lower().strip('.')
        if ext == 'jpg':
            fmt = 'JPEG'
        elif ext == 'jpeg':
            fmt = 'JPEG'
        elif ext == 'png':
            fmt = 'PNG'
        else:
            # default to PNG
            fmt = 'PNG'

    # Save with optional quality
    if quality is not None and fmt.upper() in ('JPG', 'JPEG', 'WEBP', 'AVIF'):
        # Qt expects quality as int 0-100 when saving
        q = max(0, min(100, int(quality)))
        qimg.save(str(out), fmt.upper(), q)
    else:
        qimg.save(str(out), fmt.upper())

    return str(out)
