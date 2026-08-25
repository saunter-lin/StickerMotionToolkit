"""Bundled and user-selected font registration shared by preview and export."""

from __future__ import annotations

import sys
import struct
from dataclasses import dataclass
from functools import lru_cache
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


BUNDLED_FONTS = (
    BundledFont("芫荽", "Iansui", "Iansui/Iansui-Regular.ttf"),
    BundledFont("粉圓體", "jf-openhuninn-2.1", "Huninn/jf-openhuninn-2.1.ttf"),
    BundledFont("辰宇落雁體", "ChenYuluoyan 2.0", "ChenYuluoyan/ChenYuluoyan-2.0-Thin.ttf"),
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


def _normalized_family_name(family: str) -> str:
    return " ".join(family.split()).casefold()


@lru_cache(maxsize=None)
def font_family_aliases(path: Path) -> frozenset[str]:
    """Derive exact Qt family candidates from a bundled SFNT name table."""
    data = path.read_bytes()
    table_count = struct.unpack_from(">H", data, 4)[0]
    name_offset = None
    for index in range(table_count):
        tag, _, offset, _ = struct.unpack_from(">4sIII", data, 12 + index * 16)
        if tag == b"name":
            name_offset = offset
            break
    if name_offset is None:
        raise RuntimeError(f"Bundled font has no name table: {path}")

    _, record_count, strings_offset = struct.unpack_from(">HHH", data, name_offset)
    records: dict[tuple[int, int, int], dict[int, set[str]]] = {}
    for index in range(record_count):
        record_offset = name_offset + 6 + index * 12
        platform, encoding, language, name_id, length, offset = struct.unpack_from(
            ">HHHHHH", data, record_offset
        )
        if name_id not in {1, 2, 16, 17}:
            continue
        raw_offset = name_offset + strings_offset + offset
        raw = data[raw_offset:raw_offset + length]
        try:
            if platform in {0, 3}:
                value = raw.decode("utf-16-be")
            elif platform == 1:
                value = raw.decode("mac_roman")
            else:
                continue
        except UnicodeDecodeError:
            continue
        value = " ".join(value.split())
        if value:
            records.setdefault((platform, encoding, language), {}).setdefault(name_id, set()).add(value)

    aliases: set[str] = set()
    for names in records.values():
        aliases.update(names.get(1, ()))
        aliases.update(names.get(16, ()))
        for family in names.get(16, ()):
            for subfamily in names.get(17, ()):
                aliases.add(f"{family} {subfamily}")
    if not aliases:
        raise RuntimeError(f"Bundled font has no usable family names: {path}")
    return frozenset(_normalized_family_name(alias) for alias in aliases)


def bundled_font_family_aliases(descriptor: BundledFont) -> frozenset[str]:
    return font_family_aliases(resource_root() / descriptor.relative_path)


def bundled_font_family_matches(descriptor: BundledFont, family: str) -> bool:
    """Match exactly against Unicode aliases derived from this font's metadata."""
    return _normalized_family_name(family) in bundled_font_family_aliases(descriptor)


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
