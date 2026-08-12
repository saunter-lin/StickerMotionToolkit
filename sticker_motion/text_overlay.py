"""Cross-platform anti-aliased text rendering using host Qt fonts."""

from __future__ import annotations

from PIL import Image
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPainterPath, QPen

from .jobs import TextOverlaySettings


def available_font_families() -> list[str]:
    return sorted(QFontDatabase.families(), key=str.casefold)


def _font(settings: TextOverlaySettings) -> tuple[QFont, bool]:
    families = set(QFontDatabase.families())
    available = bool(settings.font_family and settings.font_family in families)
    family = settings.font_family if available else QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()
    font = QFont(family)
    font.setPixelSize(max(1, settings.font_size))
    return font, available or not settings.font_family


def apply_text_overlay(image: Image.Image, settings: TextOverlaySettings) -> tuple[Image.Image, bool]:
    """Composite static text into one RGBA frame and report font availability."""
    base = image.convert("RGBA")
    if not settings.enabled or not settings.text:
        return base, True

    width, height = base.size
    overlay = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    overlay.fill(Qt.GlobalColor.transparent)
    painter = QPainter(overlay)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    font, font_available = _font(settings)
    path = QPainterPath()
    path.addText(QPointF(0, 0), font, settings.text)
    bounds = path.boundingRect()
    margin = settings.stroke_width + 2
    if settings.horizontal_alignment == "left":
        x = margin
    elif settings.horizontal_alignment == "right":
        x = width - bounds.width() - margin
    else:
        x = (width - bounds.width()) / 2
    if settings.vertical_position == "top":
        baseline = margin - bounds.top()
    elif settings.vertical_position == "center":
        baseline = (height - bounds.height()) / 2 - bounds.top()
    else:
        baseline = height - bounds.bottom() - margin
    path.translate(x + settings.x_offset, baseline + settings.y_offset)
    if settings.stroke_width:
        painter.strokePath(path, QPen(QColor(settings.stroke_color), settings.stroke_width * 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.fillPath(path, QColor(settings.color))
    painter.end()

    converted = overlay.convertToFormat(QImage.Format.Format_RGBA8888)
    rgba = Image.frombytes("RGBA", (width, height), bytes(converted.bits()))
    return Image.alpha_composite(base, rgba), font_available
