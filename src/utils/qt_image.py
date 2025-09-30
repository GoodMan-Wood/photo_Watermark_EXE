from PySide6.QtGui import QImage, QPixmap

def qimage_from_pil(img):
    """Convert a Pillow Image to QImage (deep-copied to own memory)."""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    w, h = img.size
    data = img.tobytes('raw', 'RGBA')
    qimg = QImage(data, w, h, 4 * w, QImage.Format_RGBA8888)
    # deep copy to detach from Python bytes buffer
    return qimg.copy()


def qpixmap_from_path_with_pil(path: str):
    """Try load QPixmap directly; if fails, use Pillow to decode then convert to QPixmap."""
    pm = QPixmap(path)
    if not pm.isNull():
        return pm
    # fallback via PIL
    try:
        import importlib
        PILImage = importlib.import_module('PIL.Image')
        img = PILImage.open(path)
        from PIL import ImageOps as _IO
        try:
            img = _IO.exif_transpose(img)
        except Exception:
            pass
        qimg = qimage_from_pil(img)
        return QPixmap.fromImage(qimg)
    except Exception:
        return QPixmap()
