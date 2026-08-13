"""Core processing API for Sticker Motion Toolkit."""

from .animation import Animation, build_animation
from .export import Platform, export_animation
from .splitter import MAX_FRAME_COUNT, MIN_FRAME_COUNT, split_sheet
from .jobs import AnimationJob, AnimationQueue, TextOverlaySettings

__all__ = [
    "Animation",
    "Platform",
    "MIN_FRAME_COUNT",
    "MAX_FRAME_COUNT",
    "build_animation",
    "export_animation",
    "split_sheet",
    "AnimationJob",
    "AnimationQueue",
    "TextOverlaySettings",
]
