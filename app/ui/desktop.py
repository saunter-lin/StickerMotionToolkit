"""Simple PySide6 desktop front end for the shared processing pipeline."""

from __future__ import annotations

import sys
import re
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.workers.pipeline import process_frame_files
from app.ui.i18n import DEFAULT_LANGUAGE, LANGUAGES, localized_error, translate


class StickerMotionWindow(QMainWindow):
    """Main window kept intentionally small while the workflow stabilizes."""

    def __init__(self, settings: QSettings | None = None) -> None:
        super().__init__()
        self.settings = settings or QSettings("StickerMotionToolkit", "StickerMotionToolkit")
        saved_language = str(self.settings.value("language", DEFAULT_LANGUAGE))
        self.language = saved_language if saved_language in LANGUAGES else DEFAULT_LANGUAGE
        self.setMinimumSize(560, 420)
        self.resize(760, 640)

        self.output_edit = QLineEdit()

        self.language_combo = QComboBox()
        for code, label in LANGUAGES.items():
            self.language_combo.addItem(label, code)
        self.language_combo.setCurrentIndex(self.language_combo.findData(self.language))

        self.platform_combo = QComboBox()
        self.platform_combo.addItem("LINE (APNG)", "line")
        self.platform_combo.addItem("WeChat (GIF)", "wechat")

        self.frame_list = QListWidget()
        self.frame_list.setMinimumHeight(150)
        self.frame_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.frame_count_label = QLabel()
        self.add_frames_button = QPushButton()
        self.move_up_button = QPushButton()
        self.move_down_button = QPushButton()
        self.remove_frame_button = QPushButton()
        self.clear_frames_button = QPushButton()

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(10, 10_000)
        self.duration_spin.setSingleStep(10)
        self.duration_spin.setSuffix(" ms")
        self.duration_spin.setValue(200)

        self.background_check = QCheckBox()
        self.export_button = QPushButton()
        self.export_button.setDefault(True)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)

        self.output_browse = QPushButton()
        self.output_browse.clicked.connect(self._choose_output)
        form = QFormLayout()
        self.form = form
        form.addRow("", self.language_combo)
        form.addRow("", self.platform_combo)
        form.addRow("", self.duration_spin)
        form.addRow("", self.background_check)
        form.addRow("", self._path_row(self.output_edit, self.output_browse))

        frame_buttons = QGridLayout()
        for index, button in enumerate((
            self.add_frames_button,
            self.move_up_button,
            self.move_down_button,
            self.remove_frame_button,
            self.clear_frames_button,
        )):
            row, column = divmod(index, 3)
            frame_buttons.addWidget(button, row, column)
        for column in range(3):
            frame_buttons.setColumnStretch(column, 1)
        frame_header = QHBoxLayout()
        self.frame_list_label = QLabel()
        frame_header.addWidget(self.frame_list_label)
        frame_header.addStretch()
        frame_header.addWidget(self.frame_count_label)

        self.content_widget = QWidget()
        self.content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addLayout(form)
        layout.addLayout(frame_header)
        layout.addWidget(self.frame_list, stretch=1)
        layout.addLayout(frame_buttons)
        layout.addWidget(self.export_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.status_label)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setWidget(self.content_widget)
        self.setCentralWidget(self.scroll_area)

        self.platform_combo.currentIndexChanged.connect(self._platform_changed)
        self.language_combo.currentIndexChanged.connect(self._language_changed)
        self.export_button.clicked.connect(self._export)
        self.add_frames_button.clicked.connect(self._choose_frames)
        self.move_up_button.clicked.connect(self._move_up)
        self.move_down_button.clicked.connect(self._move_down)
        self.remove_frame_button.clicked.connect(self._remove_selected)
        self.clear_frames_button.clicked.connect(self._clear_frames)
        self.frame_list.currentRowChanged.connect(self._update_frame_controls)
        self._build_menus()
        self._retranslate_ui()
        self._update_frame_count()

    def _path_row(self, line_edit: QLineEdit, button: QPushButton) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(line_edit, stretch=1)
        layout.addWidget(button)
        return container

    def t(self, key: str, **values: object) -> str:
        return translate(self.language, key, **values)

    def _build_menus(self) -> None:
        self.file_menu = self.menuBar().addMenu("")
        self.export_action = self.file_menu.addAction("")
        self.export_action.triggered.connect(self._export)
        self.file_menu.addSeparator()
        self.quit_action = self.file_menu.addAction("")
        self.quit_action.triggered.connect(self.close)
        self.help_menu = self.menuBar().addMenu("")
        self.about_action = self.help_menu.addAction("")
        self.about_action.triggered.connect(self._show_about)

    def _language_changed(self) -> None:
        selected = self.language_combo.currentData()
        if not selected:
            return
        self.language = str(selected)
        self.settings.setValue("language", self.language)
        self.settings.sync()
        self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(self.t("window_title"))
        self.output_edit.setPlaceholderText(self.t("output_placeholder"))
        self.background_check.setText(self.t("remove_background"))
        self.output_browse.setText(self.t("browse"))
        self.add_frames_button.setText(self.t("add_frames"))
        self.move_up_button.setText(self.t("move_up"))
        self.move_down_button.setText(self.t("move_down"))
        self.remove_frame_button.setText(self.t("remove_frame"))
        self.clear_frames_button.setText(self.t("clear_frames"))
        self.frame_list_label.setText(self.t("frame_list"))
        self._update_frame_count()
        self.export_button.setText(self.t("export"))
        for row, key in enumerate(("language", "platform", "duration", "", "output")):
            label = self.form.labelForField(self.form.itemAt(row, QFormLayout.ItemRole.FieldRole).widget())
            if label is not None:
                label.setText(self.t(key) if key else "")
        self.file_menu.setTitle(self.t("menu_file"))
        self.export_action.setText(self.t("menu_export"))
        self.quit_action.setText(self.t("menu_quit"))
        self.help_menu.setTitle(self.t("menu_help"))
        self.about_action.setText(self.t("menu_about"))
        if not self.status_label.text() or self.status_label.property("state") == "ready":
            self._set_status(self.t("ready"), state="ready")

    def _show_about(self) -> None:
        QMessageBox.about(self, self.t("about_title"), self.t("about_text"))

    @property
    def platform(self) -> str:
        return str(self.platform_combo.currentData())

    def _platform_changed(self) -> None:
        current = Path(self.output_edit.text())
        if not current.name:
            return
        suffix = ".png" if self.platform == "line" else ".gif"
        self.output_edit.setText(str(current.with_suffix(suffix)))

    @staticmethod
    def _natural_key(path: str) -> list[object]:
        return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", Path(path).name)]

    def _choose_frames(self) -> None:
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            self.t("choose_frames"),
            "",
            self.t("png_filter"),
        )
        if filenames:
            self.add_frame_paths(filenames)

    def add_frame_paths(self, paths: list[str]) -> None:
        existing = self.frame_paths()
        known = set(existing)
        added = sorted(
            (str(Path(path)) for path in paths if str(Path(path)) not in known),
            key=self._natural_key,
        )
        for path in added:
            self.frame_list.addItem(Path(path).name)
            self.frame_list.item(self.frame_list.count() - 1).setData(Qt.ItemDataRole.UserRole, path)
            self.frame_list.item(self.frame_list.count() - 1).setToolTip(path)
        self._update_frame_count()
        self._set_status(self.t("frames_added", count=len(added)))

    def frame_paths(self) -> list[str]:
        return [str(self.frame_list.item(index).data(Qt.ItemDataRole.UserRole)) for index in range(self.frame_list.count())]

    def _move_up(self) -> None:
        row = self.frame_list.currentRow()
        if row > 0:
            item = self.frame_list.takeItem(row)
            self.frame_list.insertItem(row - 1, item)
            self.frame_list.setCurrentRow(row - 1)

    def _move_down(self) -> None:
        row = self.frame_list.currentRow()
        if 0 <= row < self.frame_list.count() - 1:
            item = self.frame_list.takeItem(row)
            self.frame_list.insertItem(row + 1, item)
            self.frame_list.setCurrentRow(row + 1)

    def _remove_selected(self) -> None:
        row = self.frame_list.currentRow()
        if row >= 0:
            self.frame_list.takeItem(row)
            self._update_frame_count()

    def _clear_frames(self) -> None:
        self.frame_list.clear()
        self._update_frame_count()
        self._set_status(self.t("frames_cleared"))

    def _update_frame_count(self) -> None:
        self.frame_count_label.setText(self.t("frame_count", count=self.frame_list.count()))
        self._update_frame_controls()

    def _update_frame_controls(self) -> None:
        row = self.frame_list.currentRow()
        count = self.frame_list.count()
        self.move_up_button.setEnabled(row > 0)
        self.move_down_button.setEnabled(0 <= row < count - 1)
        self.remove_frame_button.setEnabled(row >= 0)
        self.clear_frames_button.setEnabled(count > 0)

    def _choose_output(self) -> None:
        if self.platform == "line":
            file_filter, default_name = self.t("animated_png_filter"), "animation.png"
        else:
            file_filter, default_name = self.t("animated_gif_filter"), "animation.gif"
        initial = self.output_edit.text() or default_name
        filename, _ = QFileDialog.getSaveFileName(self, self.t("choose_output"), initial, file_filter)
        if filename:
            self.output_edit.setText(filename)

    def _set_status(self, message: str, *, error: bool = False, state: str = "message") -> None:
        color = "#b42318" if error else "#19703e"
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color};")
        self.status_label.setProperty("state", state)

    def _export(self) -> None:
        destination = self.output_edit.text().strip()
        paths = self.frame_paths()
        if len(paths) not in (4, 6, 8):
            self._set_status(self.t("validation_frame_total", count=len(paths)), error=True)
            return
        if not destination:
            self._set_status(self.t("validation_output"), error=True)
            return

        self.export_button.setEnabled(False)
        self._set_status(self.t("exporting"))
        QApplication.processEvents()
        try:
            output = process_frame_files(
                paths,
                destination,
                self.platform,
                duration_ms=self.duration_spin.value(),
                transparent_background=self.background_check.isChecked(),
            )
        except Exception as error:  # UI boundary: present actionable failures.
            message = localized_error(self.language, error)
            self._set_status(self.t("export_failed_status", error=message), error=True)
            QMessageBox.critical(self, self.t("export_failed"), message)
        else:
            self.output_edit.setText(str(output))
            self._set_status(self.t("export_complete_status", path=output))
            QMessageBox.information(self, self.t("export_complete"), self.t("saved_file", name=Path(output).name))
        finally:
            self.export_button.setEnabled(True)


def launch() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setOrganizationName("StickerMotionToolkit")
    app.setApplicationName("Sticker Motion Toolkit")
    window = StickerMotionWindow()
    window.show()
    return app.exec()
