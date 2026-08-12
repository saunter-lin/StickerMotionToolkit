"""Core processing API for Sticker Motion Toolkit."""

from .animation import Animation, build_animation
from .export import Platform, export_animation
from .splitter import SUPPORTED_FRAME_COUNTS, split_sheet

__all__ = [
    "Animation",
    "Platform",
    "SUPPORTED_FRAME_COUNTS",
    "build_animation",
    "export_animation",
    "split_sheet",
]
