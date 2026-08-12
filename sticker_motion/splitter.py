"""Split a sprite sheet into equally sized animation frames."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from PIL import Image

SUPPORTED_FRAME_COUNTS = (4, 6, 8)
Layout = Literal["auto", "horizontal", "vertical", "grid"]


def _grid_shape(frame_count: int) -> tuple[int, int]:
    return {4: (2, 2), 6: (3, 2), 8: (4, 2)}[frame_count]


def detect_layout(size: tuple[int, int], frame_count: int) -> Literal["horizontal", "vertical", "grid"]:
    """Infer the most plausible equal-cell layout from sheet dimensions."""
    width, height = size
    cols, rows = _grid_shape(frame_count)
    candidates: list[tuple[float, Literal["horizontal", "vertical", "grid"]]] = [
        (abs((width / frame_count) / height - 1), "horizontal"),
        (abs(width / (height / frame_count) - 1), "vertical"),
        (abs((width / cols) / (height / rows) - 1), "grid"),
    ]
    return min(candidates, key=lambda item: item[0])[1]


def split_sheet(
    source: str | Path | Image.Image,
    frame_count: int,
    layout: Layout = "auto",
) -> list[Image.Image]:
    """Return frames in reading order (left-to-right, then top-to-bottom)."""
    if frame_count not in SUPPORTED_FRAME_COUNTS:
        raise ValueError(f"frame_count must be one of {SUPPORTED_FRAME_COUNTS}")
    if layout not in {"auto", "horizontal", "vertical", "grid"}:
        raise ValueError("layout must be auto, horizontal, vertical, or grid")

    opened = not isinstance(source, Image.Image)
    image = Image.open(source) if opened else source
    try:
        sheet = image.convert("RGBA")
        actual_layout = detect_layout(sheet.size, frame_count) if layout == "auto" else layout
        if actual_layout == "horizontal":
            cols, rows = frame_count, 1
        elif actual_layout == "vertical":
            cols, rows = 1, frame_count
        else:
            cols, rows = _grid_shape(frame_count)

        if sheet.width % cols or sheet.height % rows:
            raise ValueError(
                f"sheet size {sheet.size} is not evenly divisible by {cols}x{rows} cells"
            )
        cell_width, cell_height = sheet.width // cols, sheet.height // rows
        return [
            sheet.crop((col * cell_width, row * cell_height, (col + 1) * cell_width, (row + 1) * cell_height))
            for row in range(rows)
            for col in range(cols)
        ][:frame_count]
    finally:
        if opened:
            image.close()
