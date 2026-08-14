"""Resizable multilingual PySide6 queue editor for Sticker Motion Toolkit."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL.ImageQt import ImageQt
from PySide6.QtCore import QObject, QSize, QSettings, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QFileDialog, QFormLayout,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSpinBox,
    QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.ui.i18n import DEFAULT_LANGUAGE, LANGUAGES, localized_error, translate
from app.windows_identity import configure_windows_app_identity
from sticker_motion.batch import export_jobs, prepare_job_frames
from sticker_motion.jobs import AnimationJob, AnimationQueue, BackgroundEntry
from sticker_motion.fonts import (
    BUNDLED_FONTS, DEFAULT_FONT, LOCAL_FONT_ACTION, SYSTEM_SEPARATOR,
    available_font_families, register_local_font, valid_font_family,
)


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
        self._preview_frames: list[QPixmap] = []
        self._preview_index = 0
        self.preview_timer = QTimer(self); self.preview_timer.timeout.connect(self._advance_preview)
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
        self.platform_combo = QComboBox(); self.platform_combo.addItem("WeChat (GIF)", "wechat"); self.platform_combo.addItem("LINE (APNG)", "line")
        self.play_count_combo = QComboBox(); [self.play_count_combo.addItem(str(count), count) for count in (1, 2, 3, 4)]
        self.frame_count_combo = QComboBox(); self.frame_count_combo.setVisible(False)
        self.duration_spin = QSpinBox(); self.duration_spin.setRange(10, 10000); self.duration_spin.setValue(220); self.duration_spin.setSuffix(" ms")
        self.frame_list = QListWidget(); self.frame_list.setMinimumHeight(110); self.frame_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding); self.frame_list.setViewMode(QListWidget.ViewMode.IconMode); self.frame_list.setFlow(QListWidget.Flow.LeftToRight); self.frame_list.setWrapping(True); self.frame_list.setResizeMode(QListWidget.ResizeMode.Adjust); self.frame_list.setMovement(QListWidget.Movement.Static); self.frame_list.setGridSize(QSize(150, 30)); self.frame_list.setUniformItemSizes(True)
        self.frame_count_label = QLabel()
        self.add_frames_button, self.move_up_button, self.move_down_button = QPushButton(), QPushButton(), QPushButton()
        self.remove_frame_button, self.clear_frames_button = QPushButton(), QPushButton()
        frame_buttons = QGridLayout()
        for index, button in enumerate((self.add_frames_button, self.move_up_button, self.move_down_button, self.remove_frame_button, self.clear_frames_button)):
            frame_buttons.addWidget(button, index // 3, index % 3)

        self.background_label = QLabel(); self.add_background_button = QPushButton()
        self.background_table = QTableWidget(0, 4); self.background_table.setMinimumHeight(110); self.background_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.background_table.verticalHeader().setVisible(False); self.background_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); self.background_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection); self.background_table.horizontalHeader().setStretchLastSection(False); self.background_table.horizontalHeader().setSectionResizeMode(0, self.background_table.horizontalHeader().ResizeMode.Stretch); self.background_table.horizontalHeader().setSectionResizeMode(1, self.background_table.horizontalHeader().ResizeMode.ResizeToContents); self.background_table.horizontalHeader().setSectionResizeMode(2, self.background_table.horizontalHeader().ResizeMode.ResizeToContents); self.background_table.horizontalHeader().setSectionResizeMode(3, self.background_table.horizontalHeader().ResizeMode.ResizeToContents)
        background_header = QHBoxLayout(); background_header.addWidget(self.background_label); background_header.addStretch(); background_header.addWidget(self.add_background_button)

        self.text_check, self.text_edit = QCheckBox(), QLineEdit()
        self.font_combo = QComboBox(); self._populate_font_combo()
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
        self.text_form = QFormLayout()
        self.form_labels: list[QLabel] = []
        editor_fields = (self.language_combo, self.job_name_edit, self.platform_combo, self.play_count_combo, self.duration_spin, self.output_filename_edit, self.text_check, self.text_edit, self.font_combo, self.font_size_spin, self.text_color_button, self.stroke_color_button, self.stroke_width_spin, self.text_direction_combo, self.rotation_spin, self.vertical_combo, self.horizontal_combo, self.x_offset_spin, self.y_offset_spin, self.preview_label)
        for index, widget in enumerate(editor_fields):
            label = QLabel(); label.setBuddy(widget); self.form_labels.append(label); (self.form if index < 6 else self.text_form).addRow(label, widget)
        header = QHBoxLayout(); self.frame_list_label = QLabel(); header.addWidget(self.frame_list_label); header.addStretch(); header.addWidget(self.frame_count_label)
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        self.text_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow); self.text_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        editor = QWidget(); editor_layout = QVBoxLayout(editor); editor_layout.addLayout(self.form); editor_layout.addLayout(header); editor_layout.addWidget(self.frame_list); editor_layout.addLayout(frame_buttons); editor_layout.addLayout(background_header); editor_layout.addWidget(self.background_table); editor_layout.addLayout(self.text_form)
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
        self.add_background_button.clicked.connect(self._choose_background)
        self.output_browse.clicked.connect(self._choose_output_folder); self.export_button.clicked.connect(self._export)
        self.text_color_button.clicked.connect(lambda: self._choose_color("color")); self.stroke_color_button.clicked.connect(lambda: self._choose_color("stroke_color"))
        self.font_combo.activated.connect(self._font_activated)
        for widget in (self.job_name_edit, self.output_filename_edit, self.text_edit): widget.textChanged.connect(self._save_job)
        for widget in (self.platform_combo, self.play_count_combo, self.duration_spin, self.text_check, self.font_combo, self.font_size_spin, self.stroke_width_spin, self.text_direction_combo, self.rotation_spin, self.vertical_combo, self.horizontal_combo, self.x_offset_spin, self.y_offset_spin):
            if isinstance(widget, QCheckBox): widget.toggled.connect(self._save_job)
            elif isinstance(widget, QComboBox): widget.currentIndexChanged.connect(self._save_job)
            else: widget.valueChanged.connect(self._save_job)
        self.frame_list.currentRowChanged.connect(self._update_controls)

    def _build_menus(self) -> None:
        self.file_menu = self.menuBar().addMenu(""); self.export_action = self.file_menu.addAction(""); self.export_action.triggered.connect(self._export); self.file_menu.addSeparator(); self.quit_action = self.file_menu.addAction(""); self.quit_action.triggered.connect(self.close)
        self.help_menu = self.menuBar().addMenu(""); self.about_action = self.help_menu.addAction(""); self.about_action.triggered.connect(lambda: QMessageBox.about(self, self.t("about_title"), self.t("about_text")))

    def _populate_font_combo(self, selected: str = DEFAULT_FONT) -> None:
        self.font_combo.clear()
        for font in BUNDLED_FONTS:
            self.font_combo.addItem(font.label, font.family)
        self.font_combo.addItem(SYSTEM_SEPARATOR)
        separator_index = self.font_combo.count() - 1
        self.font_combo.model().item(separator_index).setEnabled(False)
        for family in available_font_families():
            self.font_combo.addItem(family, family)
        self.font_combo.addItem(self.t("choose_local_font"), LOCAL_FONT_ACTION)
        family = selected if valid_font_family(selected) else DEFAULT_FONT
        self.font_combo.setCurrentIndex(self.font_combo.findData(family))

    def _font_activated(self, index: int) -> None:
        if self.font_combo.itemData(index) != LOCAL_FONT_ACTION:
            return
        current = self.current_job().text_overlay.font_family if self.current_job() else DEFAULT_FONT
        path, _ = QFileDialog.getOpenFileName(self, self.t("choose_local_font"), "", self.t("font_filter"))
        family = register_local_font(path) if path else None
        self._populate_font_combo(family or current)
        self._save_job()

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
        self.text_check.setText(self.t("enabled")); self.add_frames_button.setText(self.t("add_frames")); self.move_up_button.setText(self.t("move_up")); self.move_down_button.setText(self.t("move_down")); self.remove_frame_button.setText(self.t("remove_frame")); self.clear_frames_button.setText(self.t("clear_frames")); self.frame_list_label.setText(self.t("frame_list")); self.background_label.setText(self.t("background_layer")); self.add_background_button.setText(self.t("add_background")); self.background_table.setHorizontalHeaderLabels((self.t("background_image"), self.t("start_frame"), self.t("end_frame"), self.t("remove"))); self.preview_label.setToolTip(self.t("preview")); self.text_color_button.setText(self.t("choose_text_color")); self.stroke_color_button.setText(self.t("choose_outline_color"))
        local_index = self.font_combo.findData(LOCAL_FONT_ACTION)
        if local_index >= 0: self.font_combo.setItemText(local_index, self.t("choose_local_font"))
        for label, key in zip(self.form_labels, ("language", "job_name", "platform", "play_count", "duration", "output_filename", "text_overlay", "text_content", "font", "font_size", "text_color", "outline_color", "outline_width", "text_direction", "rotation_angle", "vertical_position", "horizontal_alignment", "x_offset", "y_offset", "preview"), strict=True):
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
            level, reasons = self._job_validation_state(job)
            mark = {"ok": "✓", "warning": "⚠", "error": "✕", "neutral": "○"}[level]
            item = QListWidgetItem(f"{mark} {job.name} ({job.frame_count})")
            item.setForeground(QColor({"ok": "#19703e", "warning": "#9a6700", "error": "#b42318", "neutral": "#667085"}[level]))
            item.setToolTip("\n".join(self._localized_validation_reason(reason) for reason in reasons))
            self.job_list.addItem(item)
        self.job_list.blockSignals(False); self.job_list.setCurrentRow(selected if self.queue.jobs else -1); self._load_job(self.job_list.currentRow())

    def _job_validation_state(self, job: AnimationJob) -> tuple[str, list[str]]:
        if errors := job.validation_errors(): return "error", errors
        if result := job.post_export_validation: return result.level, list(result.reasons)
        return "neutral", ["not_validated"]

    def _localized_validation_reason(self, reason: str) -> str:
        parts = reason.split(":")
        if parts[0] == "line_duration": return self.t("line_duration_error", single=parts[1], plays=parts[2], total=parts[3])
        if parts[0] == "line_play_count": return self.t("line_play_count_error")
        if parts[0] == "line_infinite_loop": return self.t("line_infinite_loop_error")
        if parts[0] == "line_play_count_mismatch": return self.t("line_play_count_mismatch", requested=parts[1], actual=parts[2])
        if parts[0] == "line_metadata_invalid": return self.t("line_metadata_invalid")
        if parts[0] == "exporter_failure": return self.t("exporter_failure", error=":".join(parts[1:]))
        if parts[0] in {"line_size_warning", "line_size_error", "line_export_ok", "export_ok"}:
            size = int(parts[1]); key = {"line_size_warning": "line_size_warning", "line_size_error": "line_size_error", "line_export_ok": "line_export_ok", "export_ok": "export_ok"}[parts[0]]
            values = {"bytes": f"{size:,}", "kb": f"{size / 1000:.2f}"}
            if parts[0] == "line_export_ok": values["plays"] = parts[2]
            return self.t(key, **values)
        if parts[0] == "not_validated": return self.t("not_validated")
        return localized_error(self.language, ValueError(reason))

    def _load_job(self, row: int) -> None:
        job = self.current_job(); self._loading = True
        enabled = job is not None
        for widget in (self.job_name_edit, self.platform_combo, self.play_count_combo, self.duration_spin, self.output_filename_edit, self.text_check, self.text_edit, self.font_combo, self.font_size_spin, self.text_color_button, self.stroke_color_button, self.stroke_width_spin, self.text_direction_combo, self.rotation_spin, self.vertical_combo, self.horizontal_combo, self.x_offset_spin, self.y_offset_spin, self.frame_list, self.background_table, self.add_background_button): widget.setEnabled(enabled)
        if job:
            self.job_name_edit.setText(job.name); self.platform_combo.setCurrentIndex(self.platform_combo.findData(job.platform if job.platform in ("wechat", "line") else "wechat")); self.play_count_combo.setCurrentIndex(self.play_count_combo.findData(job.play_count)); self.duration_spin.setValue(job.duration_ms); self.output_filename_edit.setText(job.output_filename); s = job.text_overlay; self.text_check.setChecked(s.enabled); self.text_edit.setText(s.text); family = s.font_family if valid_font_family(s.font_family) else DEFAULT_FONT; s.font_family = family; self.font_combo.setCurrentIndex(self.font_combo.findData(family)); self.font_size_spin.setValue(s.font_size); self.stroke_width_spin.setValue(s.stroke_width); self.text_direction_combo.setCurrentIndex(self.text_direction_combo.findData(getattr(s, "text_direction", "horizontal"))); self.rotation_spin.setValue(getattr(s, "rotation_angle", 0)); self.vertical_combo.setCurrentIndex(self.vertical_combo.findData(s.vertical_position)); self.horizontal_combo.setCurrentIndex(self.horizontal_combo.findData(s.horizontal_alignment)); self.x_offset_spin.setValue(s.x_offset); self.y_offset_spin.setValue(s.y_offset); self._populate_frames(); self._populate_backgrounds()
        else: self.frame_list.clear(); self.background_table.setRowCount(0); self.preview_label.clear()
        self._loading = False; self._update_platform_controls(); self._update_frame_count(); self._update_controls(); self._update_preview()

    def _save_job(self) -> None:
        if self._loading or not (job := self.current_job()): return
        selected_font = self.font_combo.currentData()
        if selected_font == LOCAL_FONT_ACTION: return
        job.invalidate_post_export_validation(); job.name = self.job_name_edit.text(); job.platform = self.platform; job.play_count = int(self.play_count_combo.currentData()); job.duration_ms = self.duration_spin.value(); job.output_filename = self.output_filename_edit.text(); s = job.text_overlay; s.enabled = self.text_check.isChecked(); s.text = self.text_edit.text(); s.font_family = str(selected_font) if selected_font is not None else DEFAULT_FONT; s.font_size = self.font_size_spin.value(); s.stroke_width = self.stroke_width_spin.value(); s.text_direction = str(self.text_direction_combo.currentData()); s.rotation_angle = self.rotation_spin.value(); s.vertical_position = str(self.vertical_combo.currentData()); s.horizontal_alignment = str(self.horizontal_combo.currentData()); s.x_offset = self.x_offset_spin.value(); s.y_offset = self.y_offset_spin.value(); self._update_platform_controls(); self._refresh_jobs(self.job_list.currentRow()); self._update_preview()

    def _update_platform_controls(self) -> None:
        self.play_count_combo.setEnabled(self.current_job() is not None and self.platform == "line")

    def _choose_color(self, field: str) -> None:
        job = self.current_job()
        if not job: return
        color = QColorDialog.getColor(QColor(getattr(job.text_overlay, field)), self, self.t("choose_color"))
        if color.isValid(): setattr(job.text_overlay, field, color.name()); job.invalidate_post_export_validation(); self._refresh_jobs(self.job_list.currentRow()); self._update_preview()
    def _choose_frames(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, self.t("choose_frames"), "", self.t("png_filter"))
        if paths: self.add_frame_paths(paths)
    def add_frame_paths(self, paths: list[str]) -> None:
        job = self.current_job()
        if not job: return
        selected_frame = self.frame_list.currentRow(); known = {str(path) for path in job.frame_paths}; job.frame_paths.extend(Path(path) for path in sorted((path for path in paths if path not in known), key=self._natural_key)); job.invalidate_post_export_validation(); self._populate_frames(); self._refresh_jobs(self.job_list.currentRow()); self.frame_list.setCurrentRow(selected_frame); self._update_preview()
    def _populate_frames(self) -> None:
        self.frame_list.clear()
        if job := self.current_job():
            for path in job.frame_paths: self.frame_list.addItem(path.name); self.frame_list.item(self.frame_list.count() - 1).setData(Qt.ItemDataRole.UserRole, str(path))
    def frame_paths(self) -> list[str]: return [str(self.frame_list.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(self.frame_list.count())]
    def _move_up(self) -> None: self._move_frame(-1)
    def _move_down(self) -> None: self._move_frame(1)
    def _move_frame(self, offset: int) -> None:
        row = self.frame_list.currentRow(); job = self.current_job(); target = row + offset
        if job and 0 <= target < len(job.frame_paths): job.frame_paths[row], job.frame_paths[target] = job.frame_paths[target], job.frame_paths[row]; job.invalidate_post_export_validation(); self._populate_frames(); self._refresh_jobs(self.job_list.currentRow()); self.frame_list.setCurrentRow(target); self._update_preview()
    def _remove_selected(self) -> None:
        row = self.frame_list.currentRow(); job = self.current_job()
        if job and row >= 0: job.frame_paths.pop(row); job.invalidate_post_export_validation(); self._populate_frames(); self._refresh_jobs(self.job_list.currentRow()); self._update_preview()
    def _clear_frames(self) -> None:
        if job := self.current_job(): job.frame_paths.clear(); job.invalidate_post_export_validation(); self._populate_frames(); self._refresh_jobs(self.job_list.currentRow()); self._update_preview()

    def _choose_background(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.t("choose_background"), "", self.t("images_filter"))
        if path: self.add_background_path(path)

    def add_background_path(self, path: str) -> None:
        job = self.current_job()
        if not job or not Path(path).is_file(): return
        if not job.frame_count: self._set_status(self.t("background_requires_frames"), True); return
        if len(job.backgrounds) >= job.frame_count: self._set_status(self.t("background_limit", count=job.frame_count), True); return
        job.backgrounds.append(BackgroundEntry(Path(path), 1, job.frame_count)); job.invalidate_post_export_validation(); self._populate_backgrounds(); self._refresh_jobs(self.job_list.currentRow()); self._update_preview()

    def _populate_backgrounds(self) -> None:
        self.background_table.blockSignals(True); self.background_table.setRowCount(0)
        if job := self.current_job():
            for row, entry in enumerate(job.backgrounds):
                self.background_table.insertRow(row)
                item = QTableWidgetItem(entry.image_path.name); item.setData(Qt.ItemDataRole.UserRole, str(entry.image_path)); item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable); self.background_table.setItem(row, 0, item)
                for column, value in ((1, entry.start_frame), (2, entry.end_frame)):
                    spin = QSpinBox(); spin.setRange(1, max(1, job.frame_count)); spin.setValue(value); spin.valueChanged.connect(lambda _, r=row: self._background_range_changed(r)); self.background_table.setCellWidget(row, column, spin)
                remove = QPushButton(self.t("remove")); remove.clicked.connect(lambda _, r=row: self._remove_background(r)); self.background_table.setCellWidget(row, 3, remove)
        self.background_table.blockSignals(False)

    def _background_range_changed(self, row: int) -> None:
        job = self.current_job()
        if self._loading or not job or not (0 <= row < len(job.backgrounds)): return
        start = self.background_table.cellWidget(row, 1).value(); end = self.background_table.cellWidget(row, 2).value()
        if start > end:
            sender = self.sender()
            if sender is self.background_table.cellWidget(row, 1): end = start; self.background_table.cellWidget(row, 2).setValue(end)
            else: start = end; self.background_table.cellWidget(row, 1).setValue(start)
        job.backgrounds[row].start_frame, job.backgrounds[row].end_frame = start, end; job.invalidate_post_export_validation(); self._refresh_jobs(self.job_list.currentRow()); self._update_preview()

    def _remove_background(self, row: int) -> None:
        job = self.current_job()
        if job and 0 <= row < len(job.backgrounds): job.backgrounds.pop(row); job.invalidate_post_export_validation(); self._populate_backgrounds(); self._refresh_jobs(self.job_list.currentRow()); self._update_preview()
    def _update_frame_count(self) -> None: self.frame_count_label.setText(self.t("frame_count", count=self.frame_list.count()))
    def _update_controls(self) -> None:
        jr = self.job_list.currentRow(); fr = self.frame_list.currentRow(); self.remove_job_button.setEnabled(jr >= 0); self.duplicate_job_button.setEnabled(jr >= 0); self.move_job_up_button.setEnabled(jr > 0); self.move_job_down_button.setEnabled(0 <= jr < len(self.queue.jobs) - 1); self.clear_jobs_button.setEnabled(bool(self.queue.jobs)); self.move_up_button.setEnabled(fr > 0); self.move_down_button.setEnabled(0 <= fr < self.frame_list.count() - 1); self.remove_frame_button.setEnabled(fr >= 0); self.clear_frames_button.setEnabled(self.frame_list.count() > 0); self.export_button.setEnabled(bool(self.queue.jobs) and not self.queue.validation_errors()); self._update_frame_count()

    def _update_preview(self) -> None:
        self.preview_timer.stop(); self._preview_frames = []; self._preview_index = 0
        job = self.current_job()
        if not job or not job.frame_paths or not job.frame_paths[0].is_file(): self.preview_label.setPixmap(QPixmap()); self.preview_label.setText(self.t("preview")); return
        try: frames, _ = prepare_job_frames(job)
        except Exception: return
        self._preview_frames = [QPixmap.fromImage(ImageQt(frame)).scaled(420, 260, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation) for frame in frames]
        self.preview_label.setText(""); self.preview_label.setPixmap(self._preview_frames[0])
        if len(self._preview_frames) > 1: self.preview_timer.start(job.duration_ms)

    def _advance_preview(self) -> None:
        if not self._preview_frames: return
        self._preview_index = (self._preview_index + 1) % len(self._preview_frames); self.preview_label.setPixmap(self._preview_frames[self._preview_index])
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
    def _export_finished(self, outputs: list[str]) -> None:
        self.progress_bar.setValue(len(outputs)); self._refresh_jobs(self.job_list.currentRow()); details = [f"{job.name}: {self._localized_validation_reason(job.post_export_validation.reasons[0])}" for job in self.queue.jobs if job.post_export_validation]; message = self.t("batch_complete", count=len(outputs)) + ("\n" + "\n".join(details) if details else ""); self._set_status(message); QMessageBox.information(self, self.t("export_complete"), message)
    def _export_failed(self, error: str) -> None:
        self._refresh_jobs(self.job_list.currentRow()); self.export_button.setEnabled(True); message = localized_error(self.language, ValueError(error)); self._set_status(self.t("batch_failed", error=message), True); QMessageBox.critical(self, self.t("export_failed"), message)
    def _platform_changed(self) -> None: self._save_job()
    def _choose_output(self) -> None: self._choose_output_folder()


def launch() -> int:
    configure_windows_app_identity()
    app = QApplication.instance() or QApplication(sys.argv); app.setOrganizationName("Saunter"); app.setOrganizationDomain("saunter.app"); app.setApplicationName("Sticker Motion Toolkit"); app.setApplicationDisplayName("Sticker Motion Toolkit")
    icon = Path(__file__).resolve().parents[2] / "assets" / "icon" / "sticker-motion-toolkit-256.png"
    if icon.exists(): app.setWindowIcon(QIcon(str(icon)))
    window = StickerMotionWindow(); window.show(); return app.exec()
