"""Core image processing functions: preview composition and final export helpers.

This module contains a preview compositor that uses Qt types (QPixmap/QPainter) so it
should be called from the UI thread. Final export functions (Pillow-based) will be
added later and reuse the same watermark parameters.
"""
from typing import Optional, Tuple

from PySide6.QtGui import QPixmap, QPainter, QFont, QColor, QPainterPath, QPen, QBrush, QImage
from PySide6.QtCore import Qt, QRect


def compose_preview_qpixmap(base_pixmap: QPixmap, watermark_config: dict) -> QPixmap:
    """Compose a preview QPixmap by drawing text watermark onto a copy of base_pixmap.

    base_pixmap should already be scaled to the preview size.
    watermark_config fields used:
      - text: str
      - font_family: str
      - font_size: int
      - opacity: float (0.0-1.0)
      - color: QColor or hex string
      - rotation: float degrees
      - position: {'x': float, 'y': float} relative 0..1

    Returns a new QPixmap.
    """
    if base_pixmap.isNull():
        return base_pixmap

    canvas = QPixmap(base_pixmap)
    painter = QPainter(canvas)
    try:
        # prepare font
        font_family = watermark_config.get('font_family', 'Sans')
        font_size = int(watermark_config.get('font_size', 36))
        font = QFont(font_family, font_size)
        # bold/italic
        try:
            font.setBold(bool(watermark_config.get('bold', False)))
            font.setItalic(bool(watermark_config.get('italic', False)))
        except Exception:
            pass
        painter.setFont(font)

        # color
        color = watermark_config.get('color', '#FFFFFF')
        if isinstance(color, QColor):
            pen_color = QColor(color)
        else:
            pen_color = QColor(color)

        opacity = float(watermark_config.get('opacity', 0.7))

        text = watermark_config.get('text', '')
        if not text:
            return canvas

        # calculate position
        pos = watermark_config.get('position', {'x': 0.5, 'y': 0.5})
        px = int(pos.get('x', 0.5) * canvas.width())
        py = int(pos.get('y', 0.5) * canvas.height())

        # rotation
        rotation = float(watermark_config.get('rotation', 0.0))

        # set up painter path for text so we can draw outline and shadow
        fm = painter.fontMetrics()
        text_w = fm.horizontalAdvance(text)
        text_h = fm.height()
        ascent = fm.ascent()

        # build path centered at origin
        path = QPainterPath()
        # baseline y: ascent relative to vertical center
        baseline_y = int(ascent - (text_h / 2))
        path.addText(-text_w / 2, baseline_y, font, text)

        painter.save()
        painter.translate(px, py)
        # apply anchor translation
        anchor_name = str(watermark_config.get('anchor', 'center'))
        anchor_map = {
            'top-left': (0.0, 0.0), 'top-center': (0.5, 0.0), 'top-right': (1.0, 0.0),
            'center-left': (0.0, 0.5), 'center': (0.5, 0.5), 'center-right': (1.0, 0.5),
            'bottom-left': (0.0, 1.0), 'bottom-center': (0.5, 1.0), 'bottom-right': (1.0, 1.0),
        }
        ax, ay = anchor_map.get(anchor_name, (0.5, 0.5))
        dx = (0.5 - ax) * text_w
        dy = (0.5 - ay) * text_h
        painter.translate(dx, dy)
        if rotation != 0.0:
            painter.rotate(rotation)

        # shadow
        shadow_enabled = bool(watermark_config.get('shadow', False))
        shadow_offset = int(watermark_config.get('shadow_offset', max(2, font_size // 8)))
        shadow_color = QColor(watermark_config.get('shadow_color', '#000000'))
        shadow_color.setAlphaF(min(1.0, watermark_config.get('shadow_alpha', 0.5)))
        if shadow_enabled:
            try:
                painter.save()
                painter.translate(shadow_offset, shadow_offset)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(shadow_color))
                painter.drawPath(path)
            finally:
                painter.restore()

        # outline (stroke)
        outline_enabled = bool(watermark_config.get('outline', False))
        outline_size = int(watermark_config.get('outline_size', max(1, font_size // 14)))
        outline_color = QColor(watermark_config.get('outline_color', '#000000'))
        outline_color.setAlphaF(min(1.0, watermark_config.get('outline_alpha', opacity)))
        if outline_enabled and outline_size > 0:
            pen = QPen(outline_color)
            pen.setWidth(outline_size)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)

        # fill text with main color at specified opacity
        pen_color.setAlphaF(opacity)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(pen_color))
        painter.drawPath(path)

        painter.restore()

    finally:
        painter.end()

    # optionally draw a small position handle (in canvas coordinates) to aid dragging
    try:
        show_handle = bool(watermark_config.get('show_handle', False))
    except Exception:
        show_handle = False

    if show_handle:
        hp = QPainter(canvas)
        try:
            pos = watermark_config.get('position', {'x': 0.5, 'y': 0.5})
            px = int(pos.get('x', 0.5) * canvas.width())
            py = int(pos.get('y', 0.5) * canvas.height())
            # handle size relative to image size
            r = max(6, int(min(canvas.width(), canvas.height()) * 0.02))
            outer = QColor('#000000')
            inner = QColor('#FFFFFF')
            outer.setAlphaF(0.8)
            inner.setAlphaF(0.95)
            hp.setPen(outer)
            hp.setBrush(outer)
            hp.drawEllipse(px - r, py - r, r * 2, r * 2)
            hp.setPen(inner)
            hp.setBrush(inner)
            hp.drawEllipse(px - r//2, py - r//2, (r//2) * 2, (r//2) * 2)
        finally:
            hp.end()
    return canvas


def compose_image_pil(image_path: str, watermark_config: dict, output_size: Optional[Tuple[int, int]] = None):
    """Placeholder for Pillow-based export; to be implemented later."""
    return None


def compose_export_qimage(image_path: str, watermark_config: dict) -> Optional[QImage]:
    """Compose and return a QImage with watermark drawn at the original image size.

    This mirrors compose_preview_qpixmap but works on QImage so it can be used in
    non-GUI threads if needed. It loads the source image using QImage, converts to a
    paintable format, and draws text with outline/shadow based on watermark_config.
    """
    base = QImage(image_path)
    if base.isNull():
        return None
    if base.format() != QImage.Format_ARGB32:
        base = base.convertToFormat(QImage.Format_ARGB32)

    canvas = QImage(base)
    painter = QPainter(canvas)
    try:
        # prepare font
        font_family = watermark_config.get('font_family', 'Sans')
        font_size = int(watermark_config.get('font_size', 36))
        font = QFont(font_family, font_size)
        try:
            font.setBold(bool(watermark_config.get('bold', False)))
            font.setItalic(bool(watermark_config.get('italic', False)))
        except Exception:
            pass
        painter.setFont(font)

        # color
        color = watermark_config.get('color', '#FFFFFF')
        pen_color = QColor(color) if not isinstance(color, QColor) else QColor(color)
        opacity = float(watermark_config.get('opacity', 0.7))
        text = watermark_config.get('text', '')
        if not text:
            return canvas

        # position
        pos = watermark_config.get('position', {'x': 0.5, 'y': 0.5})
        px = int(pos.get('x', 0.5) * canvas.width())
        py = int(pos.get('y', 0.5) * canvas.height())

        rotation = float(watermark_config.get('rotation', 0.0))

        fm = painter.fontMetrics()
        text_w = fm.horizontalAdvance(text)
        text_h = fm.height()
        ascent = fm.ascent()

        path = QPainterPath()
        baseline_y = int(ascent - (text_h / 2))
        path.addText(-text_w / 2, baseline_y, font, text)

        painter.save()
        painter.translate(px, py)
        # apply anchor translation
        anchor_name = str(watermark_config.get('anchor', 'center'))
        anchor_map = {
            'top-left': (0.0, 0.0), 'top-center': (0.5, 0.0), 'top-right': (1.0, 0.0),
            'center-left': (0.0, 0.5), 'center': (0.5, 0.5), 'center-right': (1.0, 0.5),
            'bottom-left': (0.0, 1.0), 'bottom-center': (0.5, 1.0), 'bottom-right': (1.0, 1.0),
        }
        ax, ay = anchor_map.get(anchor_name, (0.5, 0.5))
        dx = (0.5 - ax) * text_w
        dy = (0.5 - ay) * text_h
        painter.translate(dx, dy)
        if rotation != 0.0:
            painter.rotate(rotation)

        # shadow
        shadow_enabled = bool(watermark_config.get('shadow', False))
        shadow_offset = int(watermark_config.get('shadow_offset', max(2, font_size // 8)))
        shadow_color = QColor(watermark_config.get('shadow_color', '#000000'))
        try:
            # shadow_alpha may be 0..1
            sa = watermark_config.get('shadow_alpha', 0.5)
            if sa > 1:
                sa = sa / 100.0
        except Exception:
            sa = 0.5
        shadow_color.setAlphaF(min(1.0, float(sa)))
        if shadow_enabled:
            try:
                painter.save()
                painter.translate(shadow_offset, shadow_offset)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(shadow_color))
                painter.drawPath(path)
            finally:
                painter.restore()

        # outline
        outline_enabled = bool(watermark_config.get('outline', False))
        outline_size = int(watermark_config.get('outline_size', max(1, font_size // 14)))
        outline_color = QColor(watermark_config.get('outline_color', '#000000'))
        outline_color.setAlphaF(min(1.0, float(watermark_config.get('outline_alpha', opacity))))
        if outline_enabled and outline_size > 0:
            pen = QPen(outline_color)
            pen.setWidth(outline_size)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)

        # fill text
        pen_color.setAlphaF(opacity)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(pen_color))
        painter.drawPath(path)

        painter.restore()
    finally:
        painter.end()

    # handle marker if needed
    try:
        show_handle = bool(watermark_config.get('show_handle', False))
    except Exception:
        show_handle = False
    if show_handle:
        hp = QPainter(canvas)
        try:
            pos = watermark_config.get('position', {'x': 0.5, 'y': 0.5})
            px = int(pos.get('x', 0.5) * canvas.width())
            py = int(pos.get('y', 0.5) * canvas.height())
            r = max(6, int(min(canvas.width(), canvas.height()) * 0.02))
            outer = QColor('#000000'); inner = QColor('#FFFFFF')
            outer.setAlphaF(0.8); inner.setAlphaF(0.95)
            hp.setPen(outer); hp.setBrush(outer); hp.drawEllipse(px - r, py - r, r*2, r*2)
            hp.setPen(inner); hp.setBrush(inner); hp.drawEllipse(px - r//2, py - r//2, (r//2)*2, (r//2)*2)
        finally:
            hp.end()

    return canvas
