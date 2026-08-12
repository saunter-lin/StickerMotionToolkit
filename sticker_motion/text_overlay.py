"""Cross-platform text-layer layout, rotation, placement, and compositing."""

from __future__ import annotations

from PIL import Image
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPainterPath, QPen

from .fonts import available_font_families, resolved_font_families
from .jobs import TextOverlaySettings


def _font(settings: TextOverlaySettings) -> tuple[QFont, bool]:
    families, available = resolved_font_families(settings.font_family)
    font = QFont(families[0])
    font.setFamilies(families)
    font.setPixelSize(max(1, settings.font_size))
    return font, available


def _text_path(settings: TextOverlaySettings, font: QFont) -> QPainterPath:
    path = QPainterPath()
    if settings.text_direction == "vertical":
        cursor = 0.0
        for character in settings.text:
            character_path = QPainterPath()
            character_path.addText(QPointF(0, 0), font, character)
            bounds = character_path.boundingRect()
            character_path.translate(-bounds.left(), cursor - bounds.top())
            path.addPath(character_path)
            cursor += max(bounds.height(), float(settings.font_size))
    else:
        path.addText(QPointF(0, 0), font, settings.text)
    return path


def render_text_layer(settings: TextOverlaySettings) -> tuple[Image.Image, bool]:
    """Render text and outline into a tightly bounded transparent RGBA layer."""
    font, font_available = _font(settings)
    path = _text_path(settings, font)
    bounds = path.boundingRect()
    margin = settings.stroke_width + 3
    width = max(1, int(bounds.width() + margin * 2 + 1))
    height = max(1, int(bounds.height() + margin * 2 + 1))
    layer = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    layer.fill(Qt.GlobalColor.transparent)
    path.translate(margin - bounds.left(), margin - bounds.top())
    painter = QPainter(layer)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    if settings.stroke_width:
        painter.strokePath(path, QPen(QColor(settings.stroke_color), settings.stroke_width * 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.fillPath(path, QColor(settings.color))
    painter.end()
    converted = layer.convertToFormat(QImage.Format.Format_RGBA8888)
    rgba = Image.frombytes("RGBA", (width, height), bytes(converted.bits()))
    if settings.rotation_angle:
        rgba = rgba.rotate(-settings.rotation_angle, resample=Image.Resampling.BICUBIC, expand=True)
    return rgba, font_available


def overlay_position(frame_size: tuple[int, int], layer_size: tuple[int, int], settings: TextOverlaySettings) -> tuple[int, int]:
    """Place the completed layer, then apply signed X/Y offsets."""
    width, height = frame_size
    layer_width, layer_height = layer_size
    margin = settings.stroke_width + 2
    if settings.horizontal_alignment == "left":
        x = margin
    elif settings.horizontal_alignment == "right":
        x = width - layer_width - margin
    else:
        x = (width - layer_width) / 2
    if settings.vertical_position == "top":
        y = margin
    elif settings.vertical_position == "center":
        y = (height - layer_height) / 2
    else:
        y = height - layer_height - margin
    return round(x + settings.x_offset), round(y + settings.y_offset)


def apply_text_overlay(image: Image.Image, settings: TextOverlaySettings) -> tuple[Image.Image, bool]:
    """Composite static text into one RGBA frame and report font availability."""
    base = image.convert("RGBA")
    if not settings.enabled or not settings.text:
        return base, True
    layer, font_available = render_text_layer(settings)
    overlay = Image.new("RGBA", base.size)
    overlay.paste(layer, overlay_position(base.size, layer.size, settings), layer)
    return Image.alpha_composite(base, overlay), font_available
