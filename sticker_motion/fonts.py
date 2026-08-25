"""Bundled and user-selected font registration shared by preview and export."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtWidgets import QApplication

DEFAULT_FONT = "Iansui"
SYSTEM_SEPARATOR = "── 系統字型 ──"
LOCAL_FONT_ACTION = "__choose_local_font__"


@dataclass(frozen=True)
class BundledFont:
    label: str
    family: str
    relative_path: str
    family_aliases: tuple[str, ...] = ()


BUNDLED_FONTS = (
    BundledFont("芫荽", "Iansui", "Iansui/Iansui-Regular.ttf"),
    BundledFont("粉圓體", "jf-openhuninn-2.1", "Huninn/jf-openhuninn-2.1.ttf"),
    BundledFont(
        "辰宇落雁體",
        "ChenYuluoyan 2.0",
        "ChenYuluoyan/ChenYuluoyan-2.0-Thin.ttf",
        ("ChenYuluoyan 2.0 Thin",),
    ),
)

_registered = False
_registered_bundled_families: tuple[str, ...] = ()
_local_font_paths: dict[str, Path] = {}
_owned_application: QGuiApplication | None = None


def _ensure_qt_application() -> QGuiApplication:
    """Keep one Qt application alive for safe font database access."""
    global _owned_application
    application = QGuiApplication.instance()
    if application is None:
        _owned_application = QApplication([])
        application = _owned_application
    return application


def resource_root() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / "assets" / "fonts"


def bundled_font_paths() -> tuple[Path, ...]:
    return tuple(resource_root() / font.relative_path for font in BUNDLED_FONTS)


def bundled_font_family_matches(descriptor: BundledFont, family: str) -> bool:
    """Accept only the canonical family or an explicit metadata-backed alias."""
    candidate = " ".join(family.split()).casefold()
    accepted = (descriptor.family, *descriptor.family_aliases)
    return candidate in {" ".join(name.split()).casefold() for name in accepted}


def register_bundled_fonts() -> tuple[str, ...]:
    global _registered, _registered_bundled_families
    if _registered:
        return _registered_bundled_families
    _ensure_qt_application()
    registered: list[str] = []
    for descriptor, path in zip(BUNDLED_FONTS, bundled_font_paths(), strict=True):
        font_id = QFontDatabase.addApplicationFont(str(path))
        families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
        if not families:
            raise RuntimeError(f"Unable to load bundled font: {path}")
        if not bundled_font_family_matches(descriptor, families[0]):
            raise RuntimeError(f"Unexpected bundled font family: {families[0]}")
        registered.append(families[0])
    _registered_bundled_families = tuple(registered)
    _registered = True
    return _registered_bundled_families


def register_local_font(path: str | Path) -> str | None:
    candidate = Path(path)
    if not candidate.is_file():
        return None
    _ensure_qt_application()
    font_id = QFontDatabase.addApplicationFont(str(candidate))
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    if not families:
        return None
    family = families[0]
    _local_font_paths[family] = candidate
    return family


def available_font_families() -> list[str]:
    bundled = list(register_bundled_fonts())
    unique_system: dict[str, str] = {}
    for family in QFontDatabase.families():
        key = family.casefold()
        if not any(bundled_font_family_matches(descriptor, family) for descriptor in BUNDLED_FONTS):
            unique_system.setdefault(key, family)
    system = sorted(unique_system.values(), key=str.casefold)
    return bundled + system


def resolved_font_family_name(family: str) -> str | None:
    bundled = register_bundled_fonts()
    requested = family.casefold() if family else ""
    for descriptor, registered in zip(BUNDLED_FONTS, bundled, strict=True):
        if bundled_font_family_matches(descriptor, family) or requested == registered.casefold():
            return registered
    for available in (*_local_font_paths, *QFontDatabase.families()):
        if requested == available.casefold():
            return available
    return None


def valid_font_family(family: str) -> bool:
    return resolved_font_family_name(family) is not None


def resolved_font_families(family: str) -> tuple[list[str], bool]:
    """Return requested family plus safe CJK/system fallbacks and availability."""
    bundled = register_bundled_fonts()
    resolved = resolved_font_family_name(family)
    available = resolved is not None
    primary = resolved or bundled[0]
    system = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()
    fallbacks = [primary]
    for candidate in (bundled[0], bundled[1], system):
        if candidate not in fallbacks:
            fallbacks.append(candidate)
    return fallbacks, available
