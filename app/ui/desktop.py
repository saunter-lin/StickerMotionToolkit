"""Resizable multilingual PySide6 queue editor for Sticker Motion Toolkit."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL.ImageQt import ImageQt
from PySide6.QtCore import QObject, QSettings, Qt, QThread, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QFileDialog, QFormLayout,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSpinBox,
    QSplitter, QVBoxLayout, QWidget,
)

from app.ui.i18n import DEFAULT_LANGUAGE, LANGUAGES, localized_error, translate
from app.windows_identity import configure_windows_app_identity
from sticker_motion.batch import export_jobs, prepare_job_frames
from sticker_motion.jobs import AnimationJob, AnimationQueue
from sticker_motion.text_overlay import available_font_families


class ExportWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, jobs: list[AnimationJob], folder: str) -> None:
        super().__init__()
        self.jobs, self.folder = jobs, folder

    def run(self) -> None:
        try:
            outputs = export_jobs(self.jobs, self.folder, lambda i, total, job: self.progress.emit(i + 1, total, job.name))
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.finished.emit([str(path) for path in outputs])


class StickerMotionWindow(QMainWindow):
    def __init__(self, settings: QSettings | None = None) -> None:
        super().__init__()
        self.settings = settings or QSettings("StickerMotionToolkit", "StickerMotionToolkit")
        saved = str(self.settings.value("language", DEFAULT_LANGUAGE))
        self.language = saved if saved in LANGUAGES else DEFAULT_LANGUAGE
        self.queue = AnimationQueue()
        self._loading = False
        self._thread: QThread | None = None
        icon = Path(__file__).resolve().parents[2] / "assets" / "icon" / "sticker-motion-toolkit-256.png"
        if icon.exists(): self.setWindowIcon(QIcon(str(icon)))
        self.setMinimumSize(700, 420)
        self.resize(1000, 760)
        self._build_ui()
        self._build_menus()
        self._connect()
        self._retranslate_ui()
        self._add_job()

    def _build_ui(self) -> None:
        self.language_combo = QComboBox()
        for code, label in LANGUAGES.items(): self.language_combo.addItem(label, code)
        self.language_combo.setCurrentIndex(self.language_combo.findData(self.language))
        self.job_list = QListWidget()
        self.job_list.setMinimumWidth(190)
        self.add_job_button, self.remove_job_button, self.duplicate_job_button = QPushButton(), QPushButton(), QPushButton()
        self.move_job_up_button, self.move_job_down_button, self.clear_jobs_button = QPushButton(), QPushButton(), QPushButton()
        queue_buttons = QGridLayout()
        for index, button in enumerate((self.add_job_button, self.duplicate_job_button, self.remove_job_button, self.move_job_up_button, self.move_job_down_button, self.clear_jobs_button)):
            queue_buttons.addWidget(button, index // 2, index % 2)
        queue_panel = QWidget(); queue_layout = QVBoxLayout(queue_panel)
        self.queue_label = QLabel(); queue_layout.addWidget(self.queue_label); queue_layout.addWidget(self.job_list, 1); queue_layout.addLayout(queue_buttons)

        self.job_name_edit, self.output_filename_edit = QLineEdit(), QLineEdit()
        self.platform_combo = QComboBox(); self.platform_combo.addItem("LINE (APNG)", "line"); self.platform_combo.addItem("WeChat (GIF)", "wechat")
        self.frame_count_combo = QComboBox(); [self.frame_count_combo.addItem(str(count), count) for count in (4, 6, 8)]; self.frame_count_combo.setCurrentIndex(2); self.frame_count_combo.setVisible(False)
        self.duration_spin = QSpinBox(); self.duration_spin.setRange(10, 10000); self.duration_spin.setValue(200); self.duration_spin.setSuffix(" ms")
        self.frame_list = QListWidget(); self.frame_list.setMinimumHeight(150); self.frame_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.frame_count_label = QLabel()
        self.add_frames_button, self.move_up_button, self.move_down_button = QPushButton(), QPushButton(), QPushButton()
        self.remove_frame_button, self.clear_frames_button = QPushButton(), QPushButton()
        frame_buttons = QGridLayout()
        for index, button in enumerate((self.add_frames_button, self.move_up_button, self.move_down_button, self.remove_frame_button, self.clear_frames_button)):
            frame_buttons.addWidget(button, index // 3, index % 3)

        self.text_check, self.text_edit = QCheckBox(), QLineEdit()
        self.font_combo = QComboBox(); self.font_combo.addItems(available_font_families())
        self.font_size_spin = QSpinBox(); self.font_size_spin.setRange(6, 300); self.font_size_spin.setValue(36)
        self.text_color_button, self.stroke_color_button = QPushButton(), QPushButton()
        self.stroke_width_spin = QSpinBox(); self.stroke_width_spin.setRange(0, 20); self.stroke_width_spin.setValue(2)
        self.text_direction_combo = QComboBox(); [self.text_direction_combo.addItem("", value) for value in ("horizontal", "vertical")]
        self.rotation_spin = QSpinBox(); self.rotation_spin.setRange(-180, 180); self.rotation_spin.setSuffix("°")
        self.vertical_combo = QComboBox(); [self.vertical_combo.addItem("", value) for value in ("top", "center", "bottom")]; self.vertical_combo.setCurrentIndex(2)
        self.horizontal_combo = QComboBox(); [self.horizontal_combo.addItem("", value) for value in ("left", "center", "right")]; self.horizontal_combo.setCurrentIndex(1)
        self.x_offset_spin, self.y_offset_spin = QSpinBox(), QSpinBox()
        for spin in (self.x_offset_spin, self.y_offset_spin): spin.setRange(-1000, 1000)
        self.preview_label = QLabel(); self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.preview_label.setMinimumSize(260, 180); self.preview_label.setStyleSheet("background:#222; color:#aaa;")

        self.form = QFormLayout()
        self.form_labels: list[QLabel] = []
        for widget in (self.language_combo, self.job_name_edit, self.platform_combo, self.duration_spin, self.output_filename_edit, self.text_check, self.text_edit, self.font_combo, self.font_size_spin, self.text_color_button, self.stroke_color_button, self.stroke_width_spin, self.text_direction_combo, self.rotation_spin, self.vertical_combo, self.horizontal_combo, self.x_offset_spin, self.y_offset_spin, self.preview_label):
            label = QLabel(); label.setBuddy(widget); self.form_labels.append(label); self.form.addRow(label, widget)
        header = QHBoxLayout(); self.frame_list_label = QLabel(); header.addWidget(self.frame_list_label); header.addStretch(); header.addWidget(self.frame_count_label)
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        editor = QWidget(); editor_layout = QVBoxLayout(editor); editor_layout.addLayout(self.form); editor_layout.addLayout(header); editor_layout.addWidget(self.frame_list, 1); editor_layout.addLayout(frame_buttons)
        splitter = QSplitter(); splitter.addWidget(queue_panel); splitter.addWidget(editor); splitter.setStretchFactor(1, 1)
        self.content_widget = QWidget(); content_layout = QVBoxLayout(self.content_widget); content_layout.addWidget(splitter, 1)
        bottom = QHBoxLayout(); self.output_folder_edit = QLineEdit(); self.output_browse = QPushButton(); self.export_button = QPushButton(); self.export_button.setDefault(True)
        bottom.addWidget(self.output_folder_edit, 1); bottom.addWidget(self.output_browse); bottom.addWidget(self.export_button); content_layout.addLayout(bottom)
        self.progress_bar = QProgressBar(); self.progress_bar.setVisible(False); content_layout.addWidget(self.progress_bar)
        self.status_label = QLabel(); self.status_label.setWordWrap(True); content_layout.addWidget(self.status_label)
        self.scroll_area = QScrollArea(); self.scroll_area.setWidgetResizable(True); self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.scroll_area.setWidget(self.content_widget); self.setCentralWidget(self.scroll_area)
        self.output_edit = self.output_folder_edit

    def _connect(self) -> None:
        self.language_combo.currentIndexChanged.connect(self._language_changed); self.job_list.currentRowChanged.connect(self._load_job)
        self.add_job_button.clicked.connect(self._add_job); self.remove_job_button.clicked.connect(self._remove_job); self.duplicate_job_button.clicked.connect(self._duplicate_job)
        self.clear_jobs_button.clicked.connect(self._clear_jobs); self.move_job_up_button.clicked.connect(lambda: self._move_job(-1)); self.move_job_down_button.clicked.connect(lambda: self._move_job(1))
        self.add_frames_button.clicked.connect(self._choose_frames); self.move_up_button.clicked.connect(self._move_up); self.move_down_button.clicked.connect(self._move_down); self.remove_frame_button.clicked.connect(self._remove_selected); self.clear_frames_button.clicked.connect(self._clear_frames)
        self.output_browse.clicked.connect(self._choose_output_folder); self.export_button.clicked.connect(self._export)
        self.text_color_button.clicked.connect(lambda: self._choose_color("color")); self.stroke_color_button.clicked.connect(lambda: self._choose_color("stroke_color"))
        for widget in (self.job_name_edit, self.output_filename_edit, self.text_edit): widget.textChanged.connect(self._save_job)
        for widget in (self.platform_combo, self.duration_spin, self.text_check, self.font_combo, self.font_size_spin, self.stroke_width_spin, self.text_direction_combo, self.rotation_spin, self.vertical_combo, self.horizontal_combo, self.x_offset_spin, self.y_offset_spin):
            if isinstance(widget, QCheckBox): widget.toggled.connect(self._save_job)
            elif isinstance(widget, QComboBox): widget.currentIndexChanged.connect(self._save_job)
            else: widget.valueChanged.connect(self._save_job)
        self.frame_list.currentRowChanged.connect(self._update_controls)

    def _build_menus(self) -> None:
        self.file_menu = self.menuBar().addMenu(""); self.export_action = self.file_menu.addAction(""); self.export_action.triggered.connect(self._export); self.file_menu.addSeparator(); self.quit_action = self.file_menu.addAction(""); self.quit_action.triggered.connect(self.close)
        self.help_menu = self.menuBar().addMenu(""); self.about_action = self.help_menu.addAction(""); self.about_action.triggered.connect(lambda: QMessageBox.about(self, self.t("about_title"), self.t("about_text")))

    def t(self, key: str, **values: object) -> str: return translate(self.language, key, **values)
    @property
    def platform(self) -> str: return str(self.platform_combo.currentData())
    @staticmethod
    def _natural_key(path: str) -> list[object]: return [int(p) if p.isdigit() else p.casefold() for p in re.split(r"(\d+)", Path(path).name)]
    def current_job(self) -> AnimationJob | None:
        row = self.job_list.currentRow(); return self.queue.jobs[row] if 0 <= row < len(self.queue.jobs) else None

    def _language_changed(self) -> None:
        selected = self.language_combo.currentData()
        if selected: self.language = str(selected); self.settings.setValue("language", self.language); self.settings.sync(); self._retranslate_ui(); self._refresh_jobs()

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(self.t("window_title")); self.queue_label.setText(self.t("animation_queue")); self.add_job_button.setText(self.t("add_job")); self.remove_job_button.setText(self.t("remove_job")); self.duplicate_job_button.setText(self.t("duplicate_job")); self.clear_jobs_button.setText(self.t("clear_jobs")); self.move_job_up_button.setText(self.t("move_job_up")); self.move_job_down_button.setText(self.t("move_job_down")); self.export_button.setText(self.t("export_all")); self.output_browse.setText(self.t("browse"))
        self.text_check.setText(self.t("enabled")); self.add_frames_button.setText(self.t("add_frames")); self.move_up_button.setText(self.t("move_up")); self.move_down_button.setText(self.t("move_down")); self.remove_frame_button.setText(self.t("remove_frame")); self.clear_frames_button.setText(self.t("clear_frames")); self.frame_list_label.setText(self.t("frame_list")); self.preview_label.setToolTip(self.t("preview")); self.text_color_button.setText(self.t("choose_text_color")); self.stroke_color_button.setText(self.t("choose_outline_color"))
        for label, key in zip(self.form_labels, ("language", "job_name", "platform", "duration", "output_filename", "text_overlay", "text_content", "font", "font_size", "text_color", "outline_color", "outline_width", "text_direction", "rotation_angle", "vertical_position", "horizontal_alignment", "x_offset", "y_offset", "preview"), strict=True):
            label.setText(self.t(key))
        for combo, prefix, values in ((self.text_direction_combo, "direction_", ("horizontal", "vertical")), (self.vertical_combo, "position_", ("top", "center", "bottom")), (self.horizontal_combo, "align_", ("left", "center", "right"))):
            for index, value in enumerate(values): combo.setItemText(index, self.t(prefix + value))
        self.output_folder_edit.setPlaceholderText(self.t("output_folder")); self.file_menu.setTitle(self.t("menu_file")); self.export_action.setText(self.t("export_all")); self.quit_action.setText(self.t("menu_quit")); self.help_menu.setTitle(self.t("menu_help")); self.about_action.setText(self.t("menu_about"))
        if not self.status_label.text(): self._set_status(self.t("ready"))

    def _add_job(self) -> None:
        index = self.queue.add(AnimationJob(self.t("job_default", number=len(self.queue.jobs) + 1))); self._refresh_jobs(index)
    def _remove_job(self) -> None:
        row = self.job_list.currentRow()
        if row >= 0: self.queue.remove(row); self._refresh_jobs(min(row, len(self.queue.jobs) - 1))
    def _duplicate_job(self) -> None:
        row = self.job_list.currentRow()
        if row >= 0: self._refresh_jobs(self.queue.duplicate(row))
    def _clear_jobs(self) -> None: self.queue.clear(); self._refresh_jobs(-1)
    def _move_job(self, offset: int) -> None:
        row = self.job_list.currentRow()
        if row >= 0: self._refresh_jobs(self.queue.move(row, offset))
    def _refresh_jobs(self, selected: int | None = None) -> None:
        selected = self.job_list.currentRow() if selected is None else selected; self.job_list.blockSignals(True); self.job_list.clear()
        for job in self.queue.jobs:
            mark = "✓" if not job.validation_errors() else "⚠"; self.job_list.addItem(f"{mark} {job.name} ({job.frame_count})")
        self.job_list.blockSignals(False); self.job_list.setCurrentRow(selected if self.queue.jobs else -1); self._load_job(self.job_list.currentRow())

    def _load_job(self, row: int) -> None:
        job = self.current_job(); self._loading = True
        enabled = job is not None
        for widget in (self.job_name_edit, self.platform_combo, self.duration_spin, self.output_filename_edit, self.text_check, self.text_edit, self.font_combo, self.font_size_spin, self.text_color_button, self.stroke_color_button, self.stroke_width_spin, self.text_direction_combo, self.rotation_spin, self.vertical_combo, self.horizontal_combo, self.x_offset_spin, self.y_offset_spin, self.frame_list): widget.setEnabled(enabled)
        if job:
            self.job_name_edit.setText(job.name); self.platform_combo.setCurrentIndex(self.platform_combo.findData(job.platform)); self.duration_spin.setValue(job.duration_ms); self.output_filename_edit.setText(job.output_filename); s = job.text_overlay; self.text_check.setChecked(s.enabled); self.text_edit.setText(s.text); self.font_combo.setCurrentText(s.font_family); self.font_size_spin.setValue(s.font_size); self.stroke_width_spin.setValue(s.stroke_width); self.text_direction_combo.setCurrentIndex(self.text_direction_combo.findData(getattr(s, "text_direction", "horizontal"))); self.rotation_spin.setValue(getattr(s, "rotation_angle", 0)); self.vertical_combo.setCurrentIndex(self.vertical_combo.findData(s.vertical_position)); self.horizontal_combo.setCurrentIndex(self.horizontal_combo.findData(s.horizontal_alignment)); self.x_offset_spin.setValue(s.x_offset); self.y_offset_spin.setValue(s.y_offset); self._populate_frames()
        else: self.frame_list.clear(); self.preview_label.clear()
        self._loading = False; self._update_frame_count(); self._update_controls(); self._update_preview()

    def _save_job(self) -> None:
        if self._loading or not (job := self.current_job()): return
        job.name = self.job_name_edit.text(); job.platform = self.platform; job.duration_ms = self.duration_spin.value(); job.output_filename = self.output_filename_edit.text(); s = job.text_overlay; s.enabled = self.text_check.isChecked(); s.text = self.text_edit.text(); s.font_family = self.font_combo.currentText(); s.font_size = self.font_size_spin.value(); s.stroke_width = self.stroke_width_spin.value(); s.text_direction = str(self.text_direction_combo.currentData()); s.rotation_angle = self.rotation_spin.value(); s.vertical_position = str(self.vertical_combo.currentData()); s.horizontal_alignment = str(self.horizontal_combo.currentData()); s.x_offset = self.x_offset_spin.value(); s.y_offset = self.y_offset_spin.value(); self._refresh_jobs(self.job_list.currentRow()); self._update_preview()

    def _choose_color(self, field: str) -> None:
        job = self.current_job()
        if not job: return
        color = QColorDialog.getColor(QColor(getattr(job.text_overlay, field)), self, self.t("choose_color"))
        if color.isValid(): setattr(job.text_overlay, field, color.name()); self._update_preview()
    def _choose_frames(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, self.t("choose_frames"), "", self.t("png_filter"))
        if paths: self.add_frame_paths(paths)
    def add_frame_paths(self, paths: list[str]) -> None:
        job = self.current_job()
        if not job: return
        selected_frame = self.frame_list.currentRow(); known = {str(path) for path in job.frame_paths}; job.frame_paths.extend(Path(path) for path in sorted((path for path in paths if path not in known), key=self._natural_key)); self._populate_frames(); self._refresh_jobs(self.job_list.currentRow()); self.frame_list.setCurrentRow(selected_frame); self._update_preview()
    def _populate_frames(self) -> None:
        self.frame_list.clear()
        if job := self.current_job():
            for path in job.frame_paths: self.frame_list.addItem(path.name); self.frame_list.item(self.frame_list.count() - 1).setData(Qt.ItemDataRole.UserRole, str(path))
    def frame_paths(self) -> list[str]: return [str(self.frame_list.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(self.frame_list.count())]
    def _move_up(self) -> None: self._move_frame(-1)
    def _move_down(self) -> None: self._move_frame(1)
    def _move_frame(self, offset: int) -> None:
        row = self.frame_list.currentRow(); job = self.current_job(); target = row + offset
        if job and 0 <= target < len(job.frame_paths): job.frame_paths[row], job.frame_paths[target] = job.frame_paths[target], job.frame_paths[row]; self._populate_frames(); self.frame_list.setCurrentRow(target); self._update_preview()
    def _remove_selected(self) -> None:
        row = self.frame_list.currentRow(); job = self.current_job()
        if job and row >= 0: job.frame_paths.pop(row); self._populate_frames(); self._refresh_jobs(self.job_list.currentRow()); self._update_preview()
    def _clear_frames(self) -> None:
        if job := self.current_job(): job.frame_paths.clear(); self._populate_frames(); self._refresh_jobs(self.job_list.currentRow()); self._update_preview()
    def _update_frame_count(self) -> None: self.frame_count_label.setText(self.t("frame_count", count=self.frame_list.count()))
    def _update_controls(self) -> None:
        jr = self.job_list.currentRow(); fr = self.frame_list.currentRow(); self.remove_job_button.setEnabled(jr >= 0); self.duplicate_job_button.setEnabled(jr >= 0); self.move_job_up_button.setEnabled(jr > 0); self.move_job_down_button.setEnabled(0 <= jr < len(self.queue.jobs) - 1); self.clear_jobs_button.setEnabled(bool(self.queue.jobs)); self.move_up_button.setEnabled(fr > 0); self.move_down_button.setEnabled(0 <= fr < self.frame_list.count() - 1); self.remove_frame_button.setEnabled(fr >= 0); self.clear_frames_button.setEnabled(self.frame_list.count() > 0); self._update_frame_count()

    def _update_preview(self) -> None:
        job = self.current_job()
        if not job or not job.frame_paths or not job.frame_paths[0].is_file(): self.preview_label.setPixmap(QPixmap()); self.preview_label.setText(self.t("preview")); return
        try: frame, _ = prepare_job_frames(AnimationJob(job.name, [job.frame_paths[0]], text_overlay=job.text_overlay))
        except Exception: return
        pixmap = QPixmap.fromImage(ImageQt(frame[0])); self.preview_label.setPixmap(pixmap.scaled(420, 260, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
    def _choose_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self.t("choose_output_folder"), self.output_folder_edit.text())
        if folder: self.output_folder_edit.setText(folder)
    def _set_status(self, text: str, error: bool = False) -> None: self.status_label.setText(text); self.status_label.setStyleSheet(f"color:{'#b42318' if error else '#19703e'}")
    def _export(self) -> None:
        if not self.queue.jobs: self._set_status(self.t("validation_no_jobs"), True); return
        invalid = self.queue.validation_errors()
        if invalid: self._set_status(self.t("validation_jobs", jobs=", ".join(str(i + 1) for i in invalid)), True); return
        folder = self.output_folder_edit.text().strip()
        if not folder: self._set_status(self.t("validation_output"), True); return
        self.export_button.setEnabled(False); self.progress_bar.setRange(0, len(self.queue.jobs)); self.progress_bar.setValue(0); self.progress_bar.setVisible(True)
        self._thread = QThread(self); worker = ExportWorker(self.queue.jobs, folder); worker.moveToThread(self._thread); self._thread.started.connect(worker.run); worker.progress.connect(self._export_progress); worker.finished.connect(self._export_finished); worker.failed.connect(self._export_failed); worker.finished.connect(self._thread.quit); worker.failed.connect(self._thread.quit); self._thread.finished.connect(worker.deleteLater); self._thread.start(); self._worker = worker
    def _export_progress(self, current: int, total: int, name: str) -> None: self.progress_bar.setValue(current - 1); self._set_status(self.t("batch_progress", current=current, total=total, name=name))
    def _export_finished(self, outputs: list[str]) -> None: self.progress_bar.setValue(len(outputs)); self.export_button.setEnabled(True); self._set_status(self.t("batch_complete", count=len(outputs))); QMessageBox.information(self, self.t("export_complete"), self.t("batch_complete", count=len(outputs)))
    def _export_failed(self, error: str) -> None: self.export_button.setEnabled(True); message = localized_error(self.language, ValueError(error)); self._set_status(self.t("batch_failed", error=message), True); QMessageBox.critical(self, self.t("export_failed"), message)
    def _platform_changed(self) -> None: self._save_job()
    def _choose_output(self) -> None: self._choose_output_folder()


def launch() -> int:
    configure_windows_app_identity()
    app = QApplication.instance() or QApplication(sys.argv); app.setOrganizationName("Saunter"); app.setOrganizationDomain("saunter.app"); app.setApplicationName("Sticker Motion Toolkit"); app.setApplicationDisplayName("Sticker Motion Toolkit")
    icon = Path(__file__).resolve().parents[2] / "assets" / "icon" / "sticker-motion-toolkit-256.png"
    if icon.exists(): app.setWindowIcon(QIcon(str(icon)))
    window = StickerMotionWindow(); window.show(); return app.exec()
