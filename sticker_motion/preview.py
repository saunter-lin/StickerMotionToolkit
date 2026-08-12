"""Static contact-sheet preview generation."""

from __future__ import annotations

import math

from PIL import Image, ImageDraw

from .animation import Animation


def make_contact_sheet(animation: Animation, thumbnail_size: tuple[int, int] = (160, 160)) -> Image.Image:
    columns = min(4, len(animation.frames))
    rows = math.ceil(len(animation.frames) / columns)
    gap, label_height = 12, 22
    width = gap + columns * (thumbnail_size[0] + gap)
    height = gap + rows * (thumbnail_size[1] + label_height + gap)
    preview = Image.new("RGBA", (width, height), (225, 229, 235, 255))
    draw = ImageDraw.Draw(preview)
    for index, frame in enumerate(animation.frames):
        row, column = divmod(index, columns)
        x = gap + column * (thumbnail_size[0] + gap)
        y = gap + row * (thumbnail_size[1] + label_height + gap)
        tile = Image.new("RGBA", thumbnail_size, "white")
        small = frame.copy()
        small.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
        tile.alpha_composite(small, ((thumbnail_size[0] - small.width) // 2, (thumbnail_size[1] - small.height) // 2))
        preview.alpha_composite(tile, (x, y))
        draw.text((x, y + thumbnail_size[1] + 4), f"Frame {index + 1}", fill=(30, 30, 30, 255))
    return preview
