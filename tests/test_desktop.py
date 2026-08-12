from __future__ import annotations

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
    assert not window.background_check.isChecked()
    assert window.language == "zh-TW"
    assert window.export_button.text() == "匯出動畫"
    window.close()


def test_platform_switch_updates_existing_output_suffix(app, settings) -> None:
    window = StickerMotionWindow(settings)
    window.output_edit.setText("/tmp/sticker.png")
    window.platform_combo.setCurrentIndex(1)
    assert window.platform == "wechat"
    assert window.output_edit.text().endswith(".gif")
    window.close()


def test_language_switch_is_live_and_persisted(app, settings) -> None:
    window = StickerMotionWindow(settings)
    window.language_combo.setCurrentIndex(window.language_combo.findData("zh-CN"))
    assert window.export_button.text() == "导出动画"
    assert window.file_menu.title() == "文件"
    window.close()

    restored = StickerMotionWindow(settings)
    assert restored.language == "zh-CN"
    assert restored.language_combo.currentText() == "简体中文"
    restored.language_combo.setCurrentIndex(restored.language_combo.findData("en"))
    assert restored.export_button.text() == "Export animation"
    assert restored.help_menu.title() == "Help"
    restored.close()


def test_translation_catalogs_have_identical_keys() -> None:
    assert set(TRANSLATIONS) == set(LANGUAGES)
    expected = set(TRANSLATIONS["zh-TW"])
    assert all(set(catalog) == expected for catalog in TRANSLATIONS.values())


def test_window_is_resizable_and_content_scrolls_vertically(app, settings) -> None:
    window = StickerMotionWindow(settings)
    assert window.minimumWidth() <= 560
    assert window.minimumHeight() <= 420
    assert window.scroll_area.widgetResizable()
    assert window.scroll_area.widget() is window.content_widget
    assert window.scroll_area.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert window.scroll_area.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
    window.resize(560, 420)
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
    assert [path.rsplit("/", 1)[-1] for path in window.frame_paths()] == [
        "frame1.png", "frame2.png", "frame3.png", "frame10.png"
    ]
    assert window.frame_count_label.text() == "影格數：4"
    window.frame_list.setCurrentRow(2)
    window._move_up()
    assert [path.rsplit("/", 1)[-1] for path in window.frame_paths()] == [
        "frame1.png", "frame3.png", "frame2.png", "frame10.png"
    ]
    assert window.frame_count_label.text() == "影格數：4"
    window.add_frame_paths([str(tmp_path / "frame12.png"), str(tmp_path / "frame11.png")])
    assert [path.rsplit("/", 1)[-1] for path in window.frame_paths()] == [
        "frame1.png", "frame3.png", "frame2.png", "frame10.png", "frame11.png", "frame12.png"
    ]
    window._remove_selected()
    assert window.frame_list.count() == 5
    assert window.frame_count_label.text() == "影格數：5"
    window._clear_frames()
    assert window.frame_list.count() == 0
    window.close()
