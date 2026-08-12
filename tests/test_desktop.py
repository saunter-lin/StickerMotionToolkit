from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication

from app.ui.desktop import StickerMotionWindow
from app.ui.i18n import LANGUAGES, TRANSLATIONS


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    yield instance


@pytest.fixture
def settings(tmp_path):
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


def test_window_defaults_match_processing_defaults(app, settings) -> None:
    window = StickerMotionWindow(settings)
    assert window.platform == "line"
    assert window.frame_list.count() == 0
    assert window.duration_spin.value() == 200
    assert not hasattr(window, "background_check")
    assert window.language == "zh-TW"
    assert window.export_button.text() == "全部匯出"
    window.close()


def test_platform_switch_updates_existing_output_suffix(app, settings) -> None:
    window = StickerMotionWindow(settings)
    window.output_filename_edit.setText("sticker.png")
    window.platform_combo.setCurrentIndex(1)
    assert window.platform == "wechat"
    assert window.current_job().resolved_filename().endswith(".gif")
    window.close()


def test_language_switch_is_live_and_persisted(app, settings) -> None:
    window = StickerMotionWindow(settings)
    window.language_combo.setCurrentIndex(window.language_combo.findData("zh-CN"))
    assert window.export_button.text() == "全部导出"
    assert window.file_menu.title() == "文件"
    window.close()

    restored = StickerMotionWindow(settings)
    assert restored.language == "zh-CN"
    assert restored.language_combo.currentText() == "简体中文"
    restored.language_combo.setCurrentIndex(restored.language_combo.findData("en"))
    assert restored.export_button.text() == "Export All"
    assert restored.help_menu.title() == "Help"
    restored.close()


def test_translation_catalogs_have_identical_keys() -> None:
    assert set(TRANSLATIONS) == set(LANGUAGES)
    expected = set(TRANSLATIONS["zh-TW"])
    assert all(set(catalog) == expected for catalog in TRANSLATIONS.values())


def test_window_is_resizable_and_content_scrolls_vertically(app, settings) -> None:
    window = StickerMotionWindow(settings)
    assert window.minimumWidth() <= 700
    assert window.minimumHeight() <= 420
    assert window.scroll_area.widgetResizable()
    assert window.scroll_area.widget() is window.content_widget
    assert window.scroll_area.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert window.scroll_area.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
    window.resize(700, 420)
    window.show()
    app.processEvents()
    assert window.frame_list.height() >= window.frame_list.minimumHeight()
    window.resize(900, 800)
    app.processEvents()
    assert window.width() >= 900
    window.close()


def test_frames_are_naturally_sorted_and_reordered(app, settings, tmp_path) -> None:
    window = StickerMotionWindow(settings)
    paths = [str(tmp_path / name) for name in ("frame10.png", "frame2.png", "frame1.png", "frame3.png")]
    window.add_frame_paths(paths)
    assert [Path(path).name for path in window.frame_paths()] == [
        "frame1.png", "frame2.png", "frame3.png", "frame10.png"
    ]
    assert window.frame_count_label.text() == "影格數：4"
    window.frame_list.setCurrentRow(2)
    window._move_up()
    assert [Path(path).name for path in window.frame_paths()] == [
        "frame1.png", "frame3.png", "frame2.png", "frame10.png"
    ]
    assert window.frame_count_label.text() == "影格數：4"
    window.add_frame_paths([str(tmp_path / "frame12.png"), str(tmp_path / "frame11.png")])
    assert [Path(path).name for path in window.frame_paths()] == [
        "frame1.png", "frame3.png", "frame2.png", "frame10.png", "frame11.png", "frame12.png"
    ]
    window._remove_selected()
    assert window.frame_list.count() == 5
    assert window.frame_count_label.text() == "影格數：5"
    window._clear_frames()
    assert window.frame_list.count() == 0
    window.close()


def test_job_selection_preserves_independent_state(app, settings, tmp_path) -> None:
    window = StickerMotionWindow(settings)
    first_paths = [str(tmp_path / f"a{i}.png") for i in range(4)]
    window.add_frame_paths(first_paths)
    window.job_name_edit.setText("Wave")
    window.duration_spin.setValue(120)
    window.text_check.setChecked(True)
    window.text_edit.setText("哈囉")
    window._add_job()
    second = window.current_job()
    window.job_name_edit.setText("Sleep")
    window.platform_combo.setCurrentIndex(1)
    window.job_list.setCurrentRow(0)
    assert window.current_job().name == "Wave"
    assert window.current_job().frame_count == 4
    assert window.duration_spin.value() == 120
    assert window.text_edit.text() == "哈囉"
    window.job_list.setCurrentRow(1)
    assert window.current_job() is second
    assert window.platform == "wechat"
    window.close()


def test_gui_duplicate_and_reorder_jobs(app, settings) -> None:
    window = StickerMotionWindow(settings)
    window.job_name_edit.setText("One")
    window._add_job()
    window.job_name_edit.setText("Two")
    window.job_list.setCurrentRow(0)
    window._duplicate_job()
    assert [job.name for job in window.queue.jobs] == ["One", "One copy", "Two"]
    window._move_job(1)
    assert [job.name for job in window.queue.jobs] == ["One", "Two", "One copy"]
    window._remove_job()
    assert [job.name for job in window.queue.jobs] == ["One", "Two"]
    window.close()


def test_language_switch_preserves_queue_state(app, settings) -> None:
    window = StickerMotionWindow(settings)
    window.job_name_edit.setText("Keep me")
    window.duration_spin.setValue(345)
    window.language_combo.setCurrentIndex(window.language_combo.findData("en"))
    assert window.current_job().name == "Keep me"
    assert window.current_job().duration_ms == 345
    assert window.queue_label.text() == "Animation Job Queue"
    assert window.export_button.text() == "Export All"
    window.close()
