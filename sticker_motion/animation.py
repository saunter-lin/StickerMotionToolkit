"""Platform-independent animation preparation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from PIL import Image

from .background import remove_background
from .splitter import MAX_FRAME_COUNT, MIN_FRAME_COUNT

DEFAULT_FRAME_DURATION_MS = 200


@dataclass(frozen=True)
class Animation:
    frames: tuple[Image.Image, ...]
    duration_ms: int | tuple[int, ...] = DEFAULT_FRAME_DURATION_MS
    loop: int = 0

    def __post_init__(self) -> None:
        if not MIN_FRAME_COUNT <= len(self.frames) <= MAX_FRAME_COUNT:
            raise ValueError(f"animations require {MIN_FRAME_COUNT} to {MAX_FRAME_COUNT} frames")
        durations = (self.duration_ms,) if isinstance(self.duration_ms, int) else self.duration_ms
        if len(durations) not in (1, len(self.frames)) or any(duration <= 0 for duration in durations):
            raise ValueError("duration_ms must contain positive timing for every frame")
        if self.loop < 0:
            raise ValueError("loop must be zero or positive")
        sizes = {frame.size for frame in self.frames}
        if len(sizes) != 1:
            raise ValueError("all frames must have the same dimensions")


def build_animation(
    frames: Iterable[Image.Image],
    duration_ms: int | tuple[int, ...] = DEFAULT_FRAME_DURATION_MS,
    *,
    transparent_background: bool = False,
    background_tolerance: int = 0,
) -> Animation:
    """Normalize copied frames to RGBA and apply shared processing."""
    processed = tuple(frame.convert("RGBA") for frame in frames)
    if transparent_background:
        processed = tuple(remove_background(frame, background_tolerance) for frame in processed)
    return Animation(processed, duration_ms)
