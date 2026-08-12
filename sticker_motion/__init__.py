"""Core processing API for Sticker Motion Toolkit."""

from .animation import Animation, build_animation
from .export import Platform, export_animation
from .splitter import SUPPORTED_FRAME_COUNTS, split_sheet
from .jobs import AnimationJob, AnimationQueue, TextOverlaySettings

__all__ = [
    "Animation",
    "Platform",
    "SUPPORTED_FRAME_COUNTS",
    "build_animation",
    "export_animation",
    "split_sheet",
    "AnimationJob",
    "AnimationQueue",
    "TextOverlaySettings",
]
