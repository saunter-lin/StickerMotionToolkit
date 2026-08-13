"""Group-based still background composition for animation frames."""

from __future__ import annotations

from PIL import Image, ImageOps

from .jobs import BackgroundEntry


def scale_to_cover(image: Image.Image, canvas_size: tuple[int, int]) -> Image.Image:
    """Preserve aspect ratio while resizing and center-cropping to the canvas."""
    return ImageOps.fit(
        image.convert("RGBA"),
        canvas_size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def apply_backgrounds(
    frame: Image.Image,
    backgrounds: list[BackgroundEntry],
    frame_number: int,
) -> Image.Image:
    """Composite applicable backgrounds in list order beneath one frame."""
    character = frame.convert("RGBA")
    canvas = Image.new("RGBA", character.size)
    for entry in backgrounds:
        if not entry.applies_to(frame_number):
            continue
        with Image.open(entry.image_path) as source:
            background = scale_to_cover(source, character.size)
        canvas = Image.alpha_composite(canvas, background)
    return Image.alpha_composite(canvas, character)
