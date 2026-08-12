"""Optional background cleanup shared by all output platforms."""

from __future__ import annotations

from PIL import Image


def remove_background(
    image: Image.Image,
    tolerance: int = 0,
    color: tuple[int, int, int] | None = None,
) -> Image.Image:
    """Make pixels near a chosen color transparent.

    When color is omitted the top-left pixel is used, which works well for
    uniformly backed sprite sheets and keeps this first version deterministic.
    """
    if not 0 <= tolerance <= 255:
        raise ValueError("tolerance must be between 0 and 255")
    result = image.convert("RGBA")
    target = color or result.getpixel((0, 0))[:3]
    pixels = result.load()
    for y in range(result.height):
        for x in range(result.width):
            red, green, blue, alpha = pixels[x, y]
            distance = max(abs(red - target[0]), abs(green - target[1]), abs(blue - target[2]))
            pixels[x, y] = (red, green, blue, 0 if distance <= tolerance else alpha)
    return result
