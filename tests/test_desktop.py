from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication

from app.ui.desktop import StickerMotionWindow
from app.ui.i18n import LANGUAGES, TRANSLATIONS
from sticker_motion.line_validation import ExportValidationResult


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    yield instance


@pytest.fixture
def settings(tmp_path):
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


def test_window_defaults_match_processing_defaults(app, settings) -> None:
    window = StickerMotionWindow(settings)
    assert window.platform == "wechat"
    assert [window.platform_combo.itemData(index) for index in range(2)] == ["wechat", "line"]
    assert [window.platform_combo.itemText(index) for index in range(2)] == ["WeChat (GIF)", "LINE (APNG)"]
    assert window.frame_list.count() == 0
    assert window.duration_spin.value() == 220
    assert window.play_count_combo.currentData() == 1
    assert not window.play_count_combo.isEnabled()
    assert window.font_combo.currentData() == "Iansui"
    assert not hasattr(window, "background_check")
    assert window.language == "zh-TW"
    assert window.export_button.text() == "全部匯出"
    window.close()


def test_platform_switch_updates_existing_output_suffix(app, settings) -> None:
    window = StickerMotionWindow(settings)
    window.output_filename_edit.setText("sticker.png")
    window.platform_combo.setCurrentIndex(1)
    assert window.platform == "line"
    assert window.play_count_combo.isEnabled()
    assert window.current_job().resolved_filename().endswith(".png")
    window.close()


def test_platform_switch_immediately_applies_and_clears_line_validation(app, settings, tmp_path) -> None:
    from PIL import Image

    window = StickerMotionWindow(settings)
    paths = []
    for index in range(11):
        path = tmp_path / f"frame{index:02d}.png"; Image.new("RGBA", (20, 20)).save(path); paths.append(str(path))
    window.add_frame_paths(paths)
    window.platform_combo.setCurrentIndex(window.platform_combo.findData("line"))
    window.play_count_combo.setCurrentIndex(window.play_count_combo.findData(2))
    assert "line_duration:2420:2:4840" in window.current_job().validation_errors()
    assert not window.export_button.isEnabled()
    window.platform_combo.setCurrentIndex(window.platform_combo.findData("wechat"))
    assert not window.play_count_combo.isEnabled()
    assert window.current_job().validation_errors() == []
    assert window.export_button.isEnabled()
    window.platform_combo.setCurrentIndex(window.platform_combo.findData("line"))
    assert window.play_count_combo.isEnabled()
    assert "line_duration:2420:2:4840" in window.current_job().validation_errors()
    assert not window.export_button.isEnabled()
    window.close()


def test_group_list_shows_post_export_status_reason_and_invalidates_on_change(app, settings, tmp_path) -> None:
    from PIL import Image

    window = StickerMotionWindow(settings)
    paths = []
    for index in range(4):
        path = tmp_path / f"frame{index}.png"; Image.new("RGBA", (20, 20)).save(path); paths.append(str(path))
    window.add_frame_paths(paths)
    job = window.current_job()
    job.post_export_validation = ExportValidationResult("warning", ("line_size_warning:982341",), 982_341, 1)
    window._refresh_jobs(0)
    item = window.job_list.item(0)
    assert item.text().startswith("⚠")
    assert "982,341 bytes" in item.toolTip()
    window.duration_spin.setValue(221)
    assert job.post_export_validation is None
    assert window.job_list.item(0).text().startswith("○")
    for change in (
        lambda: window.text_edit.setText("changed"),
        lambda: window.platform_combo.setCurrentIndex(window.platform_combo.findData("line")),
        lambda: window.play_count_combo.setCurrentIndex(window.play_count_combo.findData(2)),
    ):
        job.post_export_validation = ExportValidationResult("ok", ("line_export_ok:900000:1",), 900_000, 1)
        change()
        assert job.post_export_validation is None
    job.post_export_validation = ExportValidationResult("ok", ("line_export_ok:900000:2",), 900_000, 2)
    window.frame_list.setCurrentRow(1); window._move_up()
    assert job.post_export_validation is None
    background = tmp_path / "background.png"; Image.new("RGB", (20, 20)).save(background)
    job.post_export_validation = ExportValidationResult("ok", ("line_export_ok:900000:2",), 900_000, 2)
    window.add_background_path(str(background))
    assert job.post_export_validation is None
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


def test_frame_changes_immediately_refresh_validation_preview_and_export(app, settings, tmp_path) -> None:
    from PIL import Image

    window = StickerMotionWindow(settings)
    paths = []
    for index in range(7):
        path = tmp_path / f"frame{index}.png"
        Image.new("RGBA", (20, 20), (index * 20, 0, 0, 255)).save(path)
        paths.append(str(path))
    window.add_frame_paths(paths)
    assert window.current_job().validation_errors() == []
    assert len(window._preview_frames) == 7
    assert window.preview_timer.interval() == 220
    assert window.export_button.isEnabled()
    window.frame_list.setCurrentRow(6)
    window._remove_selected()
    assert window.current_job().frame_count == 6
    assert window.current_job().validation_errors() == []
    assert len(window._preview_frames) == 6
    assert window.export_button.isEnabled()
    window.close()


def test_frame_limit_immediately_refreshes_invalid_and_valid_states(app, settings, tmp_path) -> None:
    from PIL import Image

    window = StickerMotionWindow(settings)
    paths = []
    for index in range(16):
        path = tmp_path / f"frame{index:02d}.png"
        Image.new("RGBA", (20, 20), (index * 10, 0, 0, 255)).save(path)
        paths.append(str(path))
    window.add_frame_paths(paths[:15])
    assert window.current_job().frame_count == 15
    assert window.current_job().validation_errors() == []
    assert len(window._preview_frames) == 15
    assert window.export_button.isEnabled()
    window.add_frame_paths(paths[15:])
    assert window.current_job().validation_errors() == ["frame_count:16"]
    assert len(window._preview_frames) == 16
    assert not window.export_button.isEnabled()
    window.frame_list.setCurrentRow(15)
    window._remove_selected()
    assert window.current_job().frame_count == 15
    assert window.current_job().validation_errors() == []
    assert len(window._preview_frames) == 15
    assert window.export_button.isEnabled()
    window.close()


@pytest.mark.parametrize("count", [2, 5, 7])
def test_preview_accepts_arbitrary_frame_counts_with_compositing(app, settings, tmp_path, count: int) -> None:
    from PIL import Image

    window = StickerMotionWindow(settings)
    paths = []
    for index in range(count):
        path = tmp_path / f"frame{index}.png"
        Image.new("RGBA", (30, 30), (index * 20, 0, 0, 128)).save(path)
        paths.append(str(path))
    background = tmp_path / "background.png"; Image.new("RGB", (30, 30), "blue").save(background)
    window.add_frame_paths(paths)
    window.duration_spin.setValue(317)
    window.text_check.setChecked(True); window.text_edit.setText("測試")
    window.add_background_path(str(background))
    assert len(window._preview_frames) == count
    assert window.preview_timer.interval() == 317
    before = window._preview_index; window._advance_preview()
    assert window._preview_index == (before + 1) % count
    assert window.current_job().backgrounds[0].end_frame == count
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
    assert window.platform == "line"
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


def test_every_job_editor_control_has_a_translated_visible_label(app, settings) -> None:
    window = StickerMotionWindow(settings)
    expected = {
        "zh-TW": ("介面語言", "影格間隔", "文字方向", "旋轉角度", "預覽"),
        "zh-CN": ("界面语言", "帧间隔", "文字方向", "旋转角度", "预览"),
        "en": ("Interface Language", "Frame Duration", "Text Direction", "Rotation Angle", "Preview"),
    }
    for language, labels in expected.items():
        window.language_combo.setCurrentIndex(window.language_combo.findData(language))
        fields = (
            window.language_combo, window.job_name_edit, window.platform_combo,
            window.duration_spin, window.output_filename_edit, window.text_check,
            window.text_edit, window.font_combo, window.font_size_spin,
            window.text_color_button, window.stroke_color_button,
            window.stroke_width_spin, window.text_direction_combo,
            window.rotation_spin, window.vertical_combo, window.horizontal_combo,
            window.x_offset_spin, window.y_offset_spin, window.preview_label,
        )
        visible = {
            (window.form.labelForField(field) or window.text_form.labelForField(field)).text()
            for field in fields
        }
        assert set(labels) <= visible
        assert "" not in visible
    window.close()


def test_language_switch_preserves_new_text_controls(app, settings) -> None:
    window = StickerMotionWindow(settings)
    window.text_check.setChecked(True)
    window.text_edit.setText("你好 Test")
    window.text_direction_combo.setCurrentIndex(window.text_direction_combo.findData("vertical"))
    window.rotation_spin.setValue(-37)
    window.x_offset_spin.setValue(12)
    window.y_offset_spin.setValue(-9)
    selected = window.job_list.currentRow()
    window.language_combo.setCurrentIndex(window.language_combo.findData("en"))
    job = window.current_job()
    assert window.job_list.currentRow() == selected
    assert job.text_overlay.text_direction == "vertical"
    assert job.text_overlay.rotation_angle == -37
    assert (job.text_overlay.x_offset, job.text_overlay.y_offset) == (12, -9)
    assert window.text_direction_combo.currentText() == "Vertical"
    window.close()


def test_bundled_fonts_are_fixed_first_and_local_action_is_last(app, settings) -> None:
    from sticker_motion.fonts import LOCAL_FONT_ACTION, SYSTEM_SEPARATOR

    window = StickerMotionWindow(settings)
    assert [window.font_combo.itemText(index) for index in range(3)] == ["芫荽", "粉圓體", "辰宇落雁體"]
    assert [window.font_combo.itemData(index) for index in range(3)] == ["Iansui", "jf-openhuninn-2.1", "ChenYuluoyan 2.0"]
    separator_index = next(index for index in range(window.font_combo.count()) if window.font_combo.itemText(index) == SYSTEM_SEPARATOR)
    assert not window.font_combo.model().item(separator_index).isEnabled()
    assert window.font_combo.itemData(window.font_combo.count() - 1) == LOCAL_FONT_ACTION
    assert window.font_combo.count() >= 5
    window.close()


def test_empty_system_fonts_keeps_bundled_fonts_and_local_action_last(app, settings, monkeypatch) -> None:
    from PySide6.QtGui import QFontDatabase
    from sticker_motion.fonts import LOCAL_FONT_ACTION, SYSTEM_SEPARATOR

    monkeypatch.setattr(QFontDatabase, "families", staticmethod(lambda: []))
    window = StickerMotionWindow(settings)
    assert [window.font_combo.itemText(index) for index in range(3)] == ["芫荽", "粉圓體", "辰宇落雁體"]
    assert window.font_combo.itemText(3) == SYSTEM_SEPARATOR
    assert window.font_combo.itemData(window.font_combo.count() - 1) == LOCAL_FONT_ACTION
    assert window.font_combo.count() == 5
    window.close()


def test_valid_saved_font_restores_and_missing_font_falls_back(app, settings) -> None:
    window = StickerMotionWindow(settings)
    job = window.current_job()
    job.text_overlay.font_family = "jf-openhuninn-2.1"
    window._load_job(0)
    assert window.font_combo.currentData() == "jf-openhuninn-2.1"
    job.text_overlay.font_family = "Missing Font"
    window._load_job(0)
    assert window.font_combo.currentData() == "Iansui"
    assert job.text_overlay.font_family == "Iansui"
    window.close()


def test_frame_list_wraps_without_changing_order(app, settings, tmp_path) -> None:
    window = StickerMotionWindow(settings)
    paths = [str(tmp_path / name) for name in ("08.png", "02.png", "01.png", "06.png")]
    window.add_frame_paths(paths)
    assert window.frame_list.viewMode() == window.frame_list.ViewMode.IconMode
    assert window.frame_list.isWrapping()
    assert [Path(path).name for path in window.frame_paths()] == ["01.png", "02.png", "06.png", "08.png"]
    window.close()


def test_background_ui_is_group_based_and_duplicate_copies_it(app, settings, tmp_path) -> None:
    from PIL import Image

    window = StickerMotionWindow(settings)
    frames = []
    for index in range(4):
        path = tmp_path / f"frame{index}.png"; Image.new("RGBA", (40, 40)).save(path); frames.append(str(path))
    background = tmp_path / "背景.png"; Image.new("RGB", (80, 40), "blue").save(background)
    window.add_frame_paths(frames); window.add_background_path(str(background))
    assert window.background_table.rowCount() == 1
    assert window.current_job().backgrounds[0].start_frame == 1
    assert window.current_job().backgrounds[0].end_frame == 4
    window.background_table.cellWidget(0, 1).setValue(2)
    window.background_table.cellWidget(0, 2).setValue(3)
    window._duplicate_job()
    duplicate = window.current_job()
    assert duplicate.backgrounds[0].image_path == background
    assert (duplicate.backgrounds[0].start_frame, duplicate.backgrounds[0].end_frame) == (2, 3)
    assert duplicate.backgrounds is not window.queue.jobs[0].backgrounds
    window.close()


def test_preview_uses_group_duration_and_all_composited_frames(app, settings, tmp_path) -> None:
    from PIL import Image

    window = StickerMotionWindow(settings)
    paths = []
    for index in range(4):
        path = tmp_path / f"p{index}.png"; Image.new("RGBA", (40, 40), (index * 40, 0, 0, 255)).save(path); paths.append(str(path))
    window.add_frame_paths(paths); window.duration_spin.setValue(333)
    assert len(window._preview_frames) == 4
    assert window.preview_timer.interval() == 333
    before = window._preview_index; window._advance_preview()
    assert window._preview_index == (before + 1) % 4
    window.close()
