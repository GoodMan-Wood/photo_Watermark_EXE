from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QListWidget, QLabel, QTextEdit, QPushButton, QSizePolicy,
                               QFileDialog, QListWidgetItem, QFontComboBox, QSpinBox, QSlider, QColorDialog, QGridLayout, QCheckBox, QGroupBox, QScrollArea, QProgressDialog, QComboBox, QAbstractItemView, QLineEdit, QMessageBox)
from PySide6.QtCore import Qt, QThreadPool, QSize, Signal, QRect
from PySide6.QtGui import QPixmap, QIcon, QFont, QColor, QPainter, QShortcut, QKeySequence, QImage
from pathlib import Path
import hashlib
import os
from typing import Optional

from src.io.thumbnailer import make_thumbnail
from src.io.file_manager import SUPPORTED_EXT, list_images_in_folder
from src.utils.workers import Worker
from src.core.image_processor import compose_preview_qpixmap
from src.io.exporter import export_image
import importlib
try:
    PILImage = importlib.import_module('PIL.Image')
except Exception:
    PILImage = None


class PreviewLabel(QLabel):
    """Custom label that draws a QPixmap scaled and centered in paintEvent.
    Exposes positionChanged(relative_x, relative_y) based on the drawn pixmap area.
    """
    positionChanged = Signal(float, float)  # relative x,y 0..1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)
        self._dragging = False
        self._preview_pixmap = None

    def set_preview_pixmap(self, pix: Optional[QPixmap]):
        self._preview_pixmap = pix
        # trigger repaint; do not call QLabel.setPixmap to avoid changing sizeHint
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._emit_pos(event)

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._emit_pos(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self._emit_pos(event)

    def _emit_pos(self, event):
        # compute position relative to the *drawn* pixmap area (scaled to fit)
        pix = self._preview_pixmap
        if pix is None or pix.isNull():
            return
        lbl_w = self.width()
        lbl_h = self.height()
        pix_w = pix.width()
        pix_h = pix.height()
        if pix_w == 0 or pix_h == 0:
            return
        scale = min(lbl_w / pix_w, lbl_h / pix_h)
        draw_w = pix_w * scale
        draw_h = pix_h * scale
        x0 = (lbl_w - draw_w) / 2
        y0 = (lbl_h - draw_h) / 2
        # event.position() returns QPointF in Qt6
        ex = event.position().x()
        ey = event.position().y()
        x = ex - x0
        y = ey - y0
        # clamp to drawn area
        x = max(0, min(x, draw_w))
        y = max(0, min(y, draw_h))
        rx = x / draw_w if draw_w > 0 else 0.5
        ry = y / draw_h if draw_h > 0 else 0.5
        self.positionChanged.emit(rx, ry)

    def paintEvent(self, event):
        painter = QPainter(self)
        # draw background / label defaults
        painter.fillRect(self.rect(), self.palette().window())
        if self._preview_pixmap and not self._preview_pixmap.isNull():
            pw = self._preview_pixmap.width()
            ph = self._preview_pixmap.height()
            lw = self.width()
            lh = self.height()
            scale = min(lw / pw, lh / ph)
            draw_w = int(pw * scale)
            draw_h = int(ph * scale)
            x0 = (lw - draw_w) // 2
            y0 = (lh - draw_h) // 2
            target = QRect(x0, y0, draw_w, draw_h)
            painter.drawPixmap(target, self._preview_pixmap)
        else:
            # fallback to default QLabel paint (shows text)
            super().paintEvent(event)
        painter.end()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Photo Watermark - Demo')
        self.resize(1000, 700)
        self.setAcceptDrops(True)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)

        # Left: thumbnail list + import buttons
        left_layout = QVBoxLayout()
        self.thumb_list = QListWidget()
        self.thumb_list.setMaximumWidth(260)
        self.thumb_list.setIconSize(QSize(72, 72))
        self.thumb_list.setObjectName('thumb_list')
        # allow multi-selection for batch export
        try:
            self.thumb_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        except Exception:
            pass
        # spacing is optional depending on Qt version
        try:
            self.thumb_list.setSpacing(6)
        except Exception:
            pass

        # list first
        left_layout.addWidget(self.thumb_list)

        # bottom import bar
        btn_layout = QHBoxLayout()
        self.import_files_btn = QPushButton('Import Files')
        self.import_folder_btn = QPushButton('Import Folder')
        btn_layout.addWidget(self.import_files_btn)
        btn_layout.addWidget(self.import_folder_btn)
        left_layout.addLayout(btn_layout)

        main_layout.addLayout(left_layout)

        # Center: preview
        preview_layout = QVBoxLayout()
        self.preview_label = PreviewLabel('Preview area')
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet('background: #222; color: #ddd;')
        self.preview_label.setObjectName('preview_label')
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # ensure the label does not change its size to the pixmap we set
        try:
            self.preview_label.setScaledContents(False)
        except Exception:
            pass
        preview_layout.addWidget(self.preview_label)
        main_layout.addLayout(preview_layout)

        # Right: controls (put into a scrollable panel)
        controls_layout = QVBoxLayout()
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText('Watermark text...')
        controls_layout.addWidget(self.text_input)

        # font selector
        self.font_combo = QFontComboBox()
        controls_layout.addWidget(self.font_combo)
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 200)
        self.font_size.setValue(36)
        controls_layout.addWidget(self.font_size)

        # opacity
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(70)
        controls_layout.addWidget(self.opacity_slider)

        # rotation
        self.rotation_slider = QSlider(Qt.Horizontal)
        self.rotation_slider.setRange(-180, 180)
        self.rotation_slider.setValue(0)
        controls_layout.addWidget(self.rotation_slider)

        # color button
        self.color_btn = QPushButton('Choose Color')
        controls_layout.addWidget(self.color_btn)

        # font style: bold / italic
        style_layout = QHBoxLayout()
        self.bold_cb = QCheckBox('B')
        self.bold_cb.setToolTip('Bold')
        self.italic_cb = QCheckBox('I')
        self.italic_cb.setToolTip('Italic')
        style_layout.addWidget(self.bold_cb)
        style_layout.addWidget(self.italic_cb)
        controls_layout.addLayout(style_layout)

        # show handle checkbox
        self.show_handle_cb = QCheckBox('Show handle')
        self.show_handle_cb.setChecked(True)
        controls_layout.addWidget(self.show_handle_cb)

        # outline (stroke)
        outline_layout = QHBoxLayout()
        self.outline_cb = QCheckBox('Outline')
        self.outline_size = QSpinBox()
        self.outline_size.setRange(1, 40)
        self.outline_size.setValue(2)
        outline_layout.addWidget(self.outline_cb)
        outline_layout.addWidget(self.outline_size)
        controls_layout.addLayout(outline_layout)

        # shadow controls
        shadow_layout = QHBoxLayout()
        self.shadow_cb = QCheckBox('Shadow')
        self.shadow_alpha = QSlider(Qt.Horizontal)
        self.shadow_alpha.setRange(0, 100)
        self.shadow_alpha.setValue(50)
        shadow_layout.addWidget(self.shadow_cb)
        shadow_layout.addWidget(self.shadow_alpha)
        controls_layout.addLayout(shadow_layout)

        # shadow color
        self.shadow_color_btn = QPushButton('Shadow Color')
        controls_layout.addWidget(self.shadow_color_btn)

        # position label
        self.pos_label = QLabel('Pos: 50% , 50%')
        controls_layout.addWidget(self.pos_label)

    # removed Apply (demo) button
        # export controls group
        export_group = QGroupBox('Export')
        export_v = QVBoxLayout()
        # output folder
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel('Output Folder'))
        self.export_out_dir = QLineEdit()
        self.export_out_dir.setPlaceholderText('Choose a folder…')
        self.export_out_browse = QPushButton('Browse…')
        out_row.addWidget(self.export_out_dir, 1)
        out_row.addWidget(self.export_out_browse)
        export_v.addLayout(out_row)
        # format
        format_row = QHBoxLayout()
        format_row.addWidget(QLabel('Format'))
        self.export_format = QComboBox()
        self.export_format.addItems(['JPEG', 'PNG'])
        self.export_format.setCurrentText('JPEG')
        format_row.addWidget(self.export_format)
        export_v.addLayout(format_row)
        # quality
        quality_row = QHBoxLayout()
        quality_row.addWidget(QLabel('JPEG Quality'))
        self.export_quality = QSpinBox()
        self.export_quality.setRange(1, 100)
        self.export_quality.setValue(90)
        quality_row.addWidget(self.export_quality)
        export_v.addLayout(quality_row)
        # naming rules
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel('Naming'))
        self.naming_rule = QComboBox()
        self.naming_rule.addItems(['Original', 'Prefix', 'Suffix'])
        self.name_prefix = QLineEdit(); self.name_prefix.setPlaceholderText('prefix_')
        self.name_suffix = QLineEdit(); self.name_suffix.setPlaceholderText('_suffix')
        name_row.addWidget(self.naming_rule)
        name_row.addWidget(self.name_prefix)
        name_row.addWidget(self.name_suffix)
        export_v.addLayout(name_row)
        # resize options
        resize_row = QHBoxLayout()
        resize_row.addWidget(QLabel('Resize'))
        self.resize_mode = QComboBox(); self.resize_mode.addItems(['None', 'Width', 'Height', 'Percent'])
        self.resize_width = QSpinBox(); self.resize_width.setRange(16, 10000); self.resize_width.setValue(1920)
        self.resize_height = QSpinBox(); self.resize_height.setRange(16, 10000); self.resize_height.setValue(1080)
        self.resize_percent = QSpinBox(); self.resize_percent.setRange(5, 500); self.resize_percent.setValue(100)
        resize_row.addWidget(self.resize_mode)
        resize_row.addWidget(QLabel('W'))
        resize_row.addWidget(self.resize_width)
        resize_row.addWidget(QLabel('H'))
        resize_row.addWidget(self.resize_height)
        resize_row.addWidget(QLabel('%'))
        resize_row.addWidget(self.resize_percent)
        export_v.addLayout(resize_row)
        # buttons
        self.export_btn = QPushButton('Export Current…')
        self.export_all_btn = QPushButton('Export All…')
        export_v.addWidget(self.export_btn)
        export_v.addWidget(self.export_all_btn)
        export_group.setLayout(export_v)
        controls_layout.addWidget(export_group)
        controls_layout.addStretch()

        # Anchor grid inside a GroupBox (compact, icon-like buttons)
        self.anchor_grid = QGridLayout()
        anchors = [
            ('top-left', '↖'), ('top-center', '↑'), ('top-right', '↗'),
            ('center-left', '←'), ('center', '·'), ('center-right', '→'),
            ('bottom-left', '↙'), ('bottom-center', '↓'), ('bottom-right', '↘'),
        ]
        self.anchor_buttons = {}
        for idx, (name, symbol) in enumerate(anchors):
            btn = QPushButton(symbol)
            btn.setFixedSize(36, 36)
            btn.setFlat(True)
            btn.setObjectName(f'anchor_{name.replace("-", "_")}')
            btn.setToolTip(name)
            btn.clicked.connect(lambda checked, n=name: self.set_anchor(n))
            r = idx // 3
            c = idx % 3
            self.anchor_grid.addWidget(btn, r, c)
            self.anchor_buttons[name] = btn

        anchor_group = QGroupBox('Quick anchors')
        anchor_group.setLayout(self.anchor_grid)
        controls_layout.addWidget(anchor_group)

        # wrap controls in widget + scroll area to keep right panel tidy
        controls_widget = QWidget()
        controls_widget.setLayout(controls_layout)
        controls_widget.setObjectName('controls_widget')
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(controls_widget)
        scroll.setMaximumWidth(360)
        main_layout.addWidget(scroll)


        # Thread pool
        self.pool = QThreadPool.globalInstance()

        # debug toggles
        self._debug_thumbs = True
        # track running tasks to keep references
        self._running_tasks = []
        self._export_progress = None
        self._cancel_export = False

        # keyboard shortcuts for selection
        try:
            QShortcut(QKeySequence('Ctrl+A'), self, activated=self.thumb_list.selectAll)
            QShortcut(QKeySequence('Esc'), self, activated=self.thumb_list.clearSelection)
        except Exception:
            pass

        # cache dir
        self.cache_dir = Path(os.getcwd()) / 'cache' / 'thumbnails'
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # wiring
        self.import_files_btn.clicked.connect(self.on_import_files)
        self.import_folder_btn.clicked.connect(self.on_import_folder)
        self.thumb_list.itemClicked.connect(self.on_thumb_clicked)
        self.export_btn.clicked.connect(self.on_export_current)
        self.export_all_btn.clicked.connect(self.on_export_all)
        self.export_out_browse.clicked.connect(self._browse_out_dir)
        self.naming_rule.currentIndexChanged.connect(self._toggle_name_fields)
        self.resize_mode.currentIndexChanged.connect(self._toggle_resize_fields)
        self.text_input.textChanged.connect(self.update_preview)
        self.font_combo.currentFontChanged.connect(lambda f: self.update_preview())
        self.font_size.valueChanged.connect(lambda v: self.update_preview())
        self.opacity_slider.valueChanged.connect(lambda v: self.update_preview())
        self.rotation_slider.valueChanged.connect(lambda v: self.update_preview())
        self.color_btn.clicked.connect(self.choose_color)
        # style wiring
        self.bold_cb.stateChanged.connect(lambda _: self.update_preview())
        self.italic_cb.stateChanged.connect(lambda _: self.update_preview())
        self.outline_cb.stateChanged.connect(lambda _: self.update_preview())
        self.outline_size.valueChanged.connect(lambda _: self.update_preview())
        self.shadow_cb.stateChanged.connect(lambda _: self.update_preview())
        self.shadow_alpha.valueChanged.connect(lambda _: self.update_preview())
        self.shadow_color_btn.clicked.connect(self.choose_shadow_color)

        # connect preview drag
        self.preview_label.positionChanged.connect(lambda rx, ry: self.on_preview_pos_changed(rx, ry))

        # basic stylesheet for controls
        self.setStyleSheet('''
        QWidget#controls_widget { font-size: 11px; padding: 8px; }
        QGroupBox { font-weight: bold; margin-top: 8px; }
        QPushButton { padding: 6px; }
        QPushButton:hover { background: #e6f0ff; }
        /* anchor small circular buttons (flat) */
        QPushButton[flat="true"] { border: 1px solid transparent; border-radius: 6px; }
        QPushButton[flat="true"]:hover { background: rgba(68,119,255,0.12); }
        /* Left thumbnail list: dark background and light text for better contrast */
        QListWidget {
            background: #2b2b2b;
            color: #e6e6e6;
            border: none;
        }
        QListWidget::item {
            padding: 6px;
            margin: 2px 4px;
        }
        QListWidget::item:selected {
            background: #3d6eff;
            color: white;
        }
        QListWidget::item:hover {
            background: rgba(68,119,255,0.08);
        }
        QLabel#preview_label { border: 1px solid #444; }
        ''')

        # watermark state
        self.current_image_path = None
        self.current_preview_pixmap = None
        self.watermark_color = QColor('#FFFFFF')
        # watermark config for preview/export
        self.watermark_config = {
            'text': '',
            'font_family': self.font_combo.currentFont().family(),
            'font_size': self.font_size.value(),
            'opacity': self.opacity_slider.value() / 100.0,
            'color': self.watermark_color.name(),
            'rotation': 0.0,
            'position': {'x': 0.5, 'y': 0.5},
            'anchor': 'center'
        }

        # init export UI states
        self._toggle_name_fields()
        self._toggle_resize_fields()

    def _browse_out_dir(self):
        d = QFileDialog.getExistingDirectory(self, 'Select output folder', str(Path.home()))
        if d:
            self.export_out_dir.setText(d)

    def _toggle_name_fields(self):
        mode = self.naming_rule.currentText()
        self.name_prefix.setEnabled(mode == 'Prefix')
        self.name_suffix.setEnabled(mode == 'Suffix')
        if mode != 'Prefix':
            self.name_prefix.clear()
        if mode != 'Suffix':
            self.name_suffix.clear()

    def _toggle_resize_fields(self):
        mode = self.resize_mode.currentText()
        self.resize_width.setEnabled(mode == 'Width')
        self.resize_height.setEnabled(mode == 'Height')
        self.resize_percent.setEnabled(mode == 'Percent')

    def on_apply(self):
        txt = self.text_input.toPlainText().strip()
        if txt:
            self.preview_label.setText(txt)
        else:
            self.preview_label.setText('Preview area')

    def on_export_current(self):
        if not self.current_image_path:
            return
        # determine output dir and prevent source folder overwrite
        out_dir = self.export_out_dir.text().strip()
        if not out_dir:
            QMessageBox.warning(self, 'Export', 'Please choose an output folder.'); return
        src_dir = str(Path(self.current_image_path).parent)
        if os.path.normcase(os.path.normpath(out_dir)) == os.path.normcase(os.path.normpath(src_dir)):
            QMessageBox.warning(self, 'Export', 'Exporting to the source folder is disabled by default. Please choose another folder.'); return
        fmt = self.export_format.currentText().upper()
        quality = int(self.export_quality.value()) if fmt == 'JPEG' else None
        # build export config that matches preview scale, and never draw handle
        cfg = dict(self.watermark_config)
        cfg['show_handle'] = False
        try:
            # original image size (from current preview pixmap which holds the original)
            bw, bh = self.current_preview_pixmap.width(), self.current_preview_pixmap.height()
            lw, lh = self.preview_label.width(), self.preview_label.height()
            scale = min(lw / max(1, bw), lh / max(1, bh))
            if scale > 0:
                # scale text and related metrics back to original size
                cfg['font_size'] = int(max(1, round(self.font_size.value() / scale)))
                cfg['outline_size'] = int(max(1, round(self.outline_size.value() / scale)))
                # preview offset was roughly font_size//8; scale it
                prev_off = max(2, int(self.font_size.value() // 8))
                cfg['shadow_offset'] = int(max(2, round(prev_off / scale)))
        except Exception:
            pass
        # naming
        stem = Path(self.current_image_path).stem
        rule = self.naming_rule.currentText()
        if rule == 'Prefix':
            stem = f"{self.name_prefix.text()}{stem}"
        elif rule == 'Suffix':
            stem = f"{stem}{self.name_suffix.text()}"
        ext = '.jpg' if fmt == 'JPEG' else '.png'
        out_path = str(Path(out_dir) / f"{stem}{ext}")
        # resize
        target_size = self._calc_target_size(self.current_image_path)
        try:
            export_image(self.current_image_path, cfg, out_path, fmt=fmt, quality=quality, target_size=target_size)
            QMessageBox.information(self, 'Export', f'导出成功\n{out_path}')
        except Exception as e:
            print('Export failed:', e)

    def on_export_selected(self):
        items = self.thumb_list.selectedItems()
        if not items:
            # fallback to current item
            cur = self.thumb_list.currentItem()
            if cur:
                items = [cur]
            else:
                return
        paths = [it.data(Qt.UserRole) for it in items if it.data(Qt.UserRole)]
        self._export_batch(paths)

    def on_export_all(self):
        paths = []
        for i in range(self.thumb_list.count()):
            it = self.thumb_list.item(i)
            p = it.data(Qt.UserRole)
            if p:
                paths.append(p)
        if not paths:
            return
        self._export_batch(paths)

    def _export_batch(self, paths):
        out_dir = self.export_out_dir.text().strip()
        if not out_dir:
            QMessageBox.warning(self, 'Export', 'Please choose an output folder.'); return
        out_dir_p = Path(out_dir)
        fmt = self.export_format.currentText().upper()
        quality = int(self.export_quality.value()) if fmt == 'JPEG' else None
        # disallow exporting into any source folder
        for p in paths:
            if os.path.normcase(os.path.normpath(str(Path(p).parent))) == os.path.normcase(os.path.normpath(out_dir)):
                QMessageBox.warning(self, 'Export', f'Output folder matches source folder of {Path(p).name}. Please choose another folder.');
                return

        progress = QProgressDialog('Exporting images…', 'Cancel', 0, len(paths), self)
        progress.setWindowModality(Qt.ApplicationModal)
        progress.setAutoClose(True)
        progress.setAutoReset(True)
        progress.show()
        self._export_progress = progress

        self._export_total = len(paths)
        self._export_done = 0
        self._export_errors = []
        self._cancel_export = False
        progress.canceled.connect(lambda: setattr(self, '_cancel_export', True))

        def on_one_finished(worker=None):
            self._export_done += 1
            try:
                progress.setValue(self._export_done)
            except Exception:
                pass
            if progress.wasCanceled():
                # do not cancel running tasks here; we just stop updating further scheduling
                pass
            if self._export_done >= self._export_total:
                try:
                    progress.setValue(progress.maximum())
                    progress.close()
                    progress.deleteLater()
                except Exception:
                    pass
                self._export_progress = None
                if self._export_errors:
                    print('Batch export completed with errors:', len(self._export_errors))
                    QMessageBox.warning(self, 'Export', f'部分导出失败，共 {len(self._export_errors)} 项。')
                else:
                    print('Batch export completed.')
                    QMessageBox.information(self, 'Export', '全部导出成功')
            # remove finished worker ref
            try:
                if worker in self._running_tasks:
                    self._running_tasks.remove(worker)
            except Exception:
                pass

        for p in paths:
            if self._cancel_export:
                break
            stem = Path(p).stem
            ext = '.jpg' if fmt == 'JPEG' else '.png'
            # naming
            rule = self.naming_rule.currentText()
            if rule == 'Prefix':
                stem = f"{self.name_prefix.text()}{stem}"
            elif rule == 'Suffix':
                stem = f"{stem}{self.name_suffix.text()}"
            out_path = str(out_dir_p / f"{stem}{ext}")
            # snapshot current config
            cfg = dict(self.watermark_config)
            cfg['show_handle'] = False
            # scale sizes for this specific image relative to preview label
            try:
                img = QImage(p)
                if not img.isNull():
                    lw, lh = self.preview_label.width(), self.preview_label.height()
                    scale = min(lw / max(1, img.width()), lh / max(1, img.height()))
                    if scale > 0:
                        cfg['font_size'] = int(max(1, round(self.font_size.value() / scale)))
                        cfg['outline_size'] = int(max(1, round(self.outline_size.value() / scale)))
                        prev_off = max(2, int(self.font_size.value() // 8))
                        cfg['shadow_offset'] = int(max(2, round(prev_off / scale)))
            except Exception:
                pass
            target_size = self._calc_target_size(p)
            worker = Worker(export_image, p, cfg, out_path, fmt, quality, target_size)
            worker.signals.result.connect(lambda res: None)
            worker.signals.error.connect(lambda err, src=p: self._export_errors.append((src, err)))
            worker.signals.finished.connect(lambda w=worker: on_one_finished(w))
            self._running_tasks.append(worker)
            self.pool.start(worker)

    def _calc_target_size(self, src_path: str):
        mode = self.resize_mode.currentText()
        if mode == 'None':
            return None
        img = QImage(src_path)
        if img.isNull():
            return None
        if mode == 'Width':
            w = int(self.resize_width.value());
            if w <= 0: return None
            # keep AR
            h = max(1, int(round(img.height() * (w / img.width()))))
            return (w, h)
        if mode == 'Height':
            h = int(self.resize_height.value());
            if h <= 0: return None
            w = max(1, int(round(img.width() * (h / img.height()))))
            return (w, h)
        if mode == 'Percent':
            p = int(self.resize_percent.value());
            w = max(1, int(round(img.width() * (p / 100.0))))
            h = max(1, int(round(img.height() * (p / 100.0))))
            return (w, h)
        return None

    def choose_shadow_color(self):
        col = QColorDialog.getColor(QColor('#000000'), self, 'Select shadow color')
        if col.isValid():
            # store shadow color in watermark_config and update
            self.watermark_color = getattr(self, 'watermark_color', QColor('#FFFFFF'))
            self._shadow_color = col
            self.update_preview()

    def on_import_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Select images', str(Path.home()),
                                                'Images (*.jpg *.jpeg *.png *.bmp *.tif *.tiff)')
        for f in files:
            self.add_image_item(f)

    def on_import_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select folder', str(Path.home()))
        if not folder:
            return
        # list images non-recursive for now
        imgs = list_images_in_folder(folder)
        for p in imgs:
            self.add_image_item(p)

    def add_image_item(self, path: str):
        # avoid duplicates
        for i in range(self.thumb_list.count()):
            item = self.thumb_list.item(i)
            if item.data(Qt.UserRole) == path:
                return

        filename = Path(path).name
        item = QListWidgetItem(filename)
        item.setData(Qt.UserRole, path)
        # placeholder icon
        item.setIcon(QIcon())
        # reserve item height so icons have space when they are set later
        try:
            item.setSizeHint(QSize(200, 80))
        except Exception:
            pass
        self.thumb_list.addItem(item)

        # auto-select newly added item so user sees preview immediately
        self.thumb_list.setCurrentItem(item)
        # call preview loader for immediate feedback
        self.on_thumb_clicked(item)

        # schedule thumbnail creation
        key = hashlib.sha1(path.encode('utf-8')).hexdigest()
        dst = str(self.cache_dir / f"{key}.png")
        if getattr(self, '_debug_thumbs', False):
            print(f'Add item: {path} -> thumbnail dst: {dst}')

        # if cached thumbnail already exists, set it immediately
        try:
            if os.path.exists(dst):
                pix = QPixmap(dst)
                if not pix.isNull():
                    item.setIcon(QIcon(pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
        except Exception:
            pass

        worker = Worker(make_thumbnail, path, dst, (256, 256))
        worker.signals.result.connect(lambda res, it=item: self.on_thumbnail_ready(res, it))
        # attach per-item error handler so failed thumbnails still get a placeholder
        worker.signals.error.connect(lambda err, it=item: self.on_thumbnail_error(err, it))
        self.pool.start(worker)

    def on_thumbnail_ready(self, dst_path: str, item: QListWidgetItem):
        if getattr(self, '_debug_thumbs', False):
            print('on_thumbnail_ready called for item:', item.text(), 'dst_path=', dst_path)
        # If thumbnail file exists, try to use it. Otherwise try to load original image as fallback.
        tried_paths = []
        if dst_path and os.path.exists(dst_path):
            tried_paths.append(dst_path)
            pix = QPixmap(dst_path)
            if not pix.isNull():
                icon = QIcon(pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                item.setIcon(icon)
                if getattr(self, '_debug_thumbs', False):
                    print('  set icon from thumbnail file')
                return

        # fallback: try to load the original image directly from the item's stored path
        orig = item.data(Qt.UserRole)
        if orig:
            tried_paths.append(orig)
            try:
                pix2 = QPixmap(orig)
                if not pix2.isNull():
                    icon = QIcon(pix2.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    item.setIcon(icon)
                    if getattr(self, '_debug_thumbs', False):
                        print('  set icon from original image')
                    return
            except Exception:
                pass

        # final fallback: set a simple error placeholder icon so user sees the failure
        try:
            pix = QPixmap(64, 64)
            pix.fill(QColor('#f8d7da'))
            painter = QPainter(pix)
            painter.setPen(QColor('#721c24'))
            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(pix.rect(), Qt.AlignCenter, 'X')
            painter.end()
            item.setIcon(QIcon(pix))
            if getattr(self, '_debug_thumbs', False):
                print('  set placeholder icon')
        except Exception:
            # fallback: leave empty icon
            pass

    def on_worker_error(self, err_tuple):
        exctype, value, tb = err_tuple
        print('Worker error:', exctype, value)
        print(tb)

    def on_thumbnail_error(self, err_tuple, item: QListWidgetItem):
        # when thumbnail generation fails for this item, set a visual placeholder
        if getattr(self, '_debug_thumbs', False):
            print('on_thumbnail_error for', item.text(), 'err=', err_tuple[1])
        try:
            pix = QPixmap(64, 64)
            pix.fill(QColor('#f8d7da'))
            painter = QPainter(pix)
            painter.setPen(QColor('#721c24'))
            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(pix.rect(), Qt.AlignCenter, 'X')
            painter.end()
            item.setIcon(QIcon(pix))
        except Exception:
            # fallback: no icon
            pass

    def on_thumb_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if not path:
            return
        # normalize path to avoid mixed slashes
        norm_path = os.path.normpath(path)
        self.current_image_path = norm_path
        # reset anchor to center on new image for predictable behavior
        self.watermark_config['anchor'] = 'center'
        # clear anchor button highlight
        for btn in getattr(self, 'anchor_buttons', {}).values():
            btn.setStyleSheet('')

        pix = QPixmap(norm_path)
        if pix.isNull():
            # try PIL fallback: open and write a temporary PNG then load
            if PILImage is not None:
                try:
                    key = hashlib.sha1(norm_path.encode('utf-8')).hexdigest()
                    tmp_path = str(self.cache_dir / f"tmp_preview_{key}.png")
                    img = PILImage.open(norm_path)
                    img = img.convert('RGBA')
                    img.save(tmp_path)
                    pix = QPixmap(tmp_path)
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                except Exception as e:
                    print('Preview load fallback failed for', norm_path, '->', e)
            else:
                print('Pillow not available: cannot fallback to open', norm_path)
                # give clearer UI feedback
                self.preview_label.setText('Unable to load image (Pillow not installed)')

        if pix.isNull():
            self.preview_label.setText('Unable to load image')
            return

        self.current_preview_pixmap = pix
        self.update_preview()

    def update_preview(self):
        # if there is a current preview pixmap, draw watermark overlay using core compositor
        if not self.current_preview_pixmap:
            return
        base = self.current_preview_pixmap
        w = self.preview_label.width()
        h = self.preview_label.height()
        scaled = base.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # update watermark_config from controls
        self.watermark_config.update({
            'text': self.text_input.toPlainText().strip(),
            'font_family': self.font_combo.currentFont().family(),
            'font_size': self.font_size.value(),
            'opacity': self.opacity_slider.value() / 100.0,
            'color': self.watermark_color.name(),
            'rotation': float(self.rotation_slider.value()),
            # show handle during interactive preview based on checkbox
            'show_handle': bool(self.show_handle_cb.isChecked()),
            # font styles
            'bold': bool(self.bold_cb.isChecked()),
            'italic': bool(self.italic_cb.isChecked()),
            # outline (stroke)
            'outline': bool(self.outline_cb.isChecked()),
            'outline_size': int(self.outline_size.value()),
            'outline_color': '#000000',
            # shadow
            'shadow': bool(self.shadow_cb.isChecked()),
            'shadow_alpha': float(self.shadow_alpha.value()) / 100.0,
            'shadow_color': getattr(self, '_shadow_color', QColor('#000000')).name(),
            'shadow_offset': max(2, int(self.font_size.value() // 8)),
        })

        composed = compose_preview_qpixmap(scaled, self.watermark_config)
        # prevent feedback loop where setting a larger pixmap makes the label expand
        try:
            final = composed.scaled(self.preview_label.width(), self.preview_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception:
            final = composed

        self.preview_label.set_preview_pixmap(final)

    def choose_color(self):
        col = QColorDialog.getColor(self.watermark_color, self, 'Select watermark color')
        if col.isValid():
            self.watermark_color = col
            self.update_preview()

    def set_anchor(self, name: str):
        # map anchor name to relative position
        mapping = {
            'top-left': {'x': 0.1, 'y': 0.1},
            'top-center': {'x': 0.5, 'y': 0.1},
            'top-right': {'x': 0.9, 'y': 0.1},
            'center-left': {'x': 0.1, 'y': 0.5},
            'center': {'x': 0.5, 'y': 0.5},
            'center-right': {'x': 0.9, 'y': 0.5},
            'bottom-left': {'x': 0.1, 'y': 0.9},
            'bottom-center': {'x': 0.5, 'y': 0.9},
            'bottom-right': {'x': 0.9, 'y': 0.9}
        }
        if name in mapping:
            self.watermark_config['position'] = mapping[name]
            self.watermark_config['anchor'] = name
            # update visual highlight for anchor buttons
            for aname, btn in getattr(self, 'anchor_buttons', {}).items():
                if aname == name:
                    # simple highlight
                    btn.setStyleSheet('background: #4477ff; color: white;')
                else:
                    btn.setStyleSheet('')
            # update position label to reflect anchor
            pos = mapping[name]
            self.pos_label.setText(f"Pos: {int(pos['x']*100)}% , {int(pos['y']*100)}%")
            # ensure handle visibility per checkbox
            self.watermark_config['show_handle'] = bool(self.show_handle_cb.isChecked())
            self.update_preview()

    # drag and drop support
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        for u in urls:
            path = u.toLocalFile()
            if not path:
                continue
            _, ext = os.path.splitext(path.lower())
            if ext in SUPPORTED_EXT:
                self.add_image_item(path)

    def on_preview_pos_changed(self, rx: float, ry: float):
        # update watermark position (relative)
        self.watermark_config['position'] = {'x': rx, 'y': ry}
        # when user manually drags, use center anchor to align visually with drag point
        self.watermark_config['anchor'] = 'center'
        # update position label
        self.pos_label.setText(f'Pos: {int(rx*100)}% , {int(ry*100)}%')
        # if user is dragging, consider anchors deselected (clear any highlight)
        for btn in getattr(self, 'anchor_buttons', {}).values():
            btn.setStyleSheet('')
        # update preview with or without handle based on checkbox
        self.watermark_config['show_handle'] = bool(self.show_handle_cb.isChecked())
        self.update_preview()
