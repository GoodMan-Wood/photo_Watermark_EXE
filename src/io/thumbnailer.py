from PIL import Image
try:
    # Pillow 9+: use Resampling enum
    from PIL import Image as _PIL_Image
    Resampling = _PIL_Image.Resampling
    _RESAMPLE = Resampling.LANCZOS
except Exception:
    # fallback for very old Pillow
    _RESAMPLE = Image.ANTIALIAS
import os


def make_thumbnail(src_path: str, dst_path: str, size=(256, 256)):
    try:
        img = Image.open(src_path)
        img = img.convert('RGBA')
        img.thumbnail(size, _RESAMPLE)
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        # always save as PNG for consistent decoding
        if not dst_path.lower().endswith('.png'):
            dst_path = os.path.splitext(dst_path)[0] + '.png'
        img.save(dst_path, format='PNG')
        return dst_path
    except Exception as e:
        # return None to signal failure to the caller
        try:
            # ensure directory exists for potential debug traces
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        except Exception:
            pass
        return None
