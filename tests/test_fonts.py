from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtGui import QFontDatabase

from sticker_motion.fonts import (
    BUNDLED_FONTS, DEFAULT_FONT, available_font_families, bundled_font_paths,
    register_bundled_fonts, register_local_font, resolved_font_families,
)
from sticker_motion.jobs import TextOverlaySettings
from sticker_motion.text_overlay import apply_text_overlay, render_text_layer


def test_bundled_font_resources_exist_and_register() -> None:
    assert [font.label for font in BUNDLED_FONTS] == ["芫荽", "粉圓體", "辰宇落雁體"]
    assert DEFAULT_FONT == "Iansui"
    paths = bundled_font_paths()
    assert all(path.is_file() and path.stat().st_size > 1_000_000 for path in paths)
    register_bundled_fonts()
    families = set(QFontDatabase.families())
    assert {font.family for font in BUNDLED_FONTS} <= families
    assert available_font_families()


def test_local_font_registration_remains_available(tmp_path: Path) -> None:
    source = bundled_font_paths()[0]
    local = tmp_path / "本機 字型.ttf"
    local.write_bytes(source.read_bytes())
    assert register_local_font(local) == "Iansui"
    assert register_local_font(tmp_path / "missing.ttf") is None


def test_missing_font_resolves_to_iansui_with_fallbacks() -> None:
    families, available = resolved_font_families("Missing Font")
    assert not available
    assert families[0] == DEFAULT_FONT
    assert len(families) >= 2


def test_mixed_traditional_simplified_english_numbers_render() -> None:
    settings = TextOverlaySettings(enabled=True, text="繁體中文 简体中文 English 123，。！？", font_family="Iansui", font_size=28)
    layer, available = render_text_layer(settings)
    assert available and layer.getbbox() is not None
    frame, frame_available = apply_text_overlay(Image.new("RGBA", (640, 160)), settings)
    assert frame_available and frame.getbbox() is not None


def test_preview_and_export_share_font_resolution_path() -> None:
    settings = TextOverlaySettings(enabled=True, text="共同字型", font_family="Iansui")
    layer, layer_available = render_text_layer(settings)
    frame, frame_available = apply_text_overlay(Image.new("RGBA", (300, 160)), settings)
    assert layer_available == frame_available
    assert layer.getbbox() is not None and frame.getbbox() is not None


def test_pyinstaller_specs_bundle_fonts_and_licenses() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in ("StickerMotionToolkit.spec", "StickerMotionToolkit-Windows.spec"):
        content = (root / name).read_text(encoding="utf-8")
        assert '("assets/fonts", "assets/fonts")' in content
        assert '("THIRD_PARTY_LICENSES.md", ".")' in content
