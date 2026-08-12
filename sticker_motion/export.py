"""Platform-specific encoding at the final pipeline stage."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from PIL import Image

from .animation import Animation


class Platform(str, Enum):
    LINE = "line"
    WECHAT = "wechat"


def _flatten_for_gif(frame: Image.Image) -> Image.Image:
    """Convert RGBA to a palette image while preserving binary transparency."""
    rgba = frame.convert("RGBA")
    alpha = rgba.getchannel("A")
    palette = rgba.convert("RGB").quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    mask = alpha.point(lambda value: 255 if value <= 127 else 0)
    palette.paste(255, mask=mask)
    palette.info["transparency"] = 255
    return palette


def export_line_apng(animation: Animation, destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = [frame.copy() for frame in animation.frames]
    frames[0].save(
        path,
        format="PNG",
        save_all=True,
        append_images=frames[1:],
        duration=animation.duration_ms,
        loop=animation.loop,
        disposal=1,
        blend=0,
    )
    return path


def export_wechat_gif(animation: Animation, destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = [_flatten_for_gif(frame) for frame in animation.frames]
    frames[0].save(
        path,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=animation.duration_ms,
        loop=animation.loop,
        disposal=2,
        transparency=255,
        optimize=False,
    )
    return path


def export_animation(animation: Animation, platform: Platform | str, destination: str | Path) -> Path:
    selected = Platform(platform)
    path = Path(destination)
    expected_suffix = ".png" if selected is Platform.LINE else ".gif"
    if path.suffix.lower() != expected_suffix:
        path = path.with_suffix(expected_suffix)
    if selected is Platform.LINE:
        return export_line_apng(animation, path)
    return export_wechat_gif(animation, path)
