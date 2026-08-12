"""Bundled and user-selected font registration shared by preview and export."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QFontDatabase

DEFAULT_FONT = "Iansui"
SYSTEM_SEPARATOR = "── 系統字型 ──"
LOCAL_FONT_ACTION = "__choose_local_font__"


@dataclass(frozen=True)
class BundledFont:
    label: str
    family: str
    relative_path: str


BUNDLED_FONTS = (
    BundledFont("芫荽", "Iansui", "Iansui/Iansui-Regular.ttf"),
    BundledFont("粉圓體", "jf-openhuninn-2.1", "Huninn/jf-openhuninn-2.1.ttf"),
    BundledFont("辰宇落雁體", "ChenYuluoyan 2.0", "ChenYuluoyan/ChenYuluoyan-2.0-Thin.ttf"),
)

_registered = False
_local_font_paths: dict[str, Path] = {}


def resource_root() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / "assets" / "fonts"


def bundled_font_paths() -> tuple[Path, ...]:
    return tuple(resource_root() / font.relative_path for font in BUNDLED_FONTS)


def register_bundled_fonts() -> None:
    global _registered
    if _registered:
        return
    for descriptor, path in zip(BUNDLED_FONTS, bundled_font_paths(), strict=True):
        font_id = QFontDatabase.addApplicationFont(str(path))
        families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
        if descriptor.family not in families:
            raise RuntimeError(f"Unable to load bundled font: {path}")
    _registered = True


def register_local_font(path: str | Path) -> str | None:
    candidate = Path(path)
    if not candidate.is_file():
        return None
    font_id = QFontDatabase.addApplicationFont(str(candidate))
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    if not families:
        return None
    family = families[0]
    _local_font_paths[family] = candidate
    return family


def available_font_families() -> list[str]:
    register_bundled_fonts()
    bundled = {font.family for font in BUNDLED_FONTS}
    return sorted((family for family in QFontDatabase.families() if family not in bundled), key=str.casefold)


def valid_font_family(family: str) -> bool:
    register_bundled_fonts()
    return bool(family and family in QFontDatabase.families())


def resolved_font_families(family: str) -> tuple[list[str], bool]:
    """Return requested family plus safe CJK/system fallbacks and availability."""
    register_bundled_fonts()
    available = valid_font_family(family)
    primary = family if available else DEFAULT_FONT
    system = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()
    fallbacks = [primary]
    for candidate in (DEFAULT_FONT, BUNDLED_FONTS[1].family, system):
        if candidate not in fallbacks:
            fallbacks.append(candidate)
    return fallbacks, available
