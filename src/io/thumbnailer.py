from PIL import Image, ImageFile, ImageOps
try:
    # Pillow 9+: use Resampling enum
    from PIL import Image as _PIL_Image
    Resampling = _PIL_Image.Resampling
    _RESAMPLE = Resampling.LANCZOS
except Exception:
    # fallback for very old Pillow
    _RESAMPLE = Image.ANTIALIAS
import os
from src.utils.logger import get_logger

# 允许加载被截断的图像，避免部分 JPG/PNG 因损坏或流式下载未完成而报错
ImageFile.LOAD_TRUNCATED_IMAGES = True
_log = get_logger('thumbnailer')


def make_thumbnail(src_path: str, dst_path: str, size=(256, 256)):
    try:
        img = Image.open(src_path)
        # 统一方向（有些图片含 EXIF 旋转信息）
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
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
def _save_thumbnail(img: Image.Image, dst_path: str, size=(256, 256)) -> str:
    img = img.convert('RGBA')
    img.thumbnail(size, _RESAMPLE)
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    if not dst_path.lower().endswith('.png'):
        dst_path = os.path.splitext(dst_path)[0] + '.png'
    img.save(dst_path, format='PNG')
    return dst_path


def make_thumbnail(src_path: str, dst_path: str, size=(256, 256)):
    # 尝试多种策略：原图->EXIF 纠正->降级采样->最小尺寸
    try:
        img = Image.open(src_path)
    except Exception as e:
        _log.warning(f"open failed: {src_path} -> {e}")
        return None

    # 尝试 EXIF 旋转纠正
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    # 第一轮：原方案
    try:
        return _save_thumbnail(img, dst_path, size)
    except Exception as e:
        _log.info(f"save thumbnail 1st failed: {src_path} -> {e}")

    # 第二轮：降级采样（使用较小目标 size）
    try:
        small = (min(size[0], 160), min(size[1], 160))
        return _save_thumbnail(img, dst_path, small)
    except Exception as e:
        _log.info(f"save thumbnail 2nd failed: {src_path} -> {e}")

    # 第三轮：更小尺寸
    try:
        tiny = (96, 96)
        return _save_thumbnail(img, dst_path, tiny)
    except Exception as e:
        _log.warning(f"save thumbnail 3rd failed: {src_path} -> {e}")
        return None
