"""Shared application pipeline used by both CLI and desktop UI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from sticker_motion.animation import DEFAULT_FRAME_DURATION_MS, build_animation
from sticker_motion.export import Platform, export_animation
from sticker_motion.splitter import Layout, split_sheet


@dataclass(frozen=True)
class ProcessingOptions:
    frame_count: int
    layout: Layout = "auto"
    duration_ms: int = DEFAULT_FRAME_DURATION_MS
    transparent_background: bool = False
    background_tolerance: int = 0


def process_file(
    source: str | Path,
    destination: str | Path,
    platform: Platform | str,
    options: ProcessingOptions,
) -> Path:
    frames = split_sheet(source, options.frame_count, options.layout)
    animation = build_animation(
        frames,
        options.duration_ms,
        transparent_background=options.transparent_background,
        background_tolerance=options.background_tolerance,
    )
    return export_animation(animation, platform, destination)


def process_frame_files(
    sources: list[str | Path],
    destination: str | Path,
    platform: Platform | str,
    *,
    duration_ms: int = DEFAULT_FRAME_DURATION_MS,
    transparent_background: bool = False,
    background_tolerance: int = 0,
) -> Path:
    """Build an animation from ordered frame files without changing their order."""
    if len(sources) not in (4, 6, 8):
        raise ValueError("frame_count must be one of (4, 6, 8)")
    frames = []
    for source in sources:
        with Image.open(source) as image:
            frames.append(image.convert("RGBA"))
    animation = build_animation(
        frames,
        duration_ms,
        transparent_background=transparent_background,
        background_tolerance=background_tolerance,
    )
    return export_animation(animation, platform, destination)
