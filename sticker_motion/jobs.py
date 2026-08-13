"""Animation job and queue models shared by GUI and batch processing."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

SUPPORTED_FRAME_COUNTS = (4, 6, 8)
DEFAULT_GROUP_DURATION_MS = 250


@dataclass
class BackgroundEntry:
    image_path: Path
    start_frame: int = 1
    end_frame: int = 1

    def applies_to(self, frame_number: int) -> bool:
        return self.start_frame <= frame_number <= self.end_frame


@dataclass
class TextOverlaySettings:
    enabled: bool = False
    text: str = ""
    font_family: str = "Iansui"
    font_size: int = 36
    color: str = "#ffffff"
    stroke_color: str = "#000000"
    stroke_width: int = 2
    text_direction: str = "horizontal"
    rotation_angle: int = 0
    vertical_position: str = "bottom"
    horizontal_alignment: str = "center"
    x_offset: int = 0
    y_offset: int = 0


@dataclass
class AnimationJob:
    name: str
    frame_paths: list[Path] = field(default_factory=list)
    duration_ms: int = DEFAULT_GROUP_DURATION_MS
    platform: str = "wechat"
    remove_background: bool = False
    background_tolerance: int = 0
    output_filename: str = ""
    text_overlay: TextOverlaySettings = field(default_factory=TextOverlaySettings)
    backgrounds: list[BackgroundEntry] = field(default_factory=list)
    status: str = "ready"
    status_message: str = ""

    @property
    def frame_count(self) -> int:
        return len(self.frame_paths)

    @property
    def extension(self) -> str:
        return ".png" if self.platform == "line" else ".gif"

    def resolved_filename(self) -> str:
        raw = self.output_filename.strip() or self.name.strip() or "animation"
        return str(Path(raw).with_suffix(self.extension).name)

    def validation_errors(self) -> list[str]:
        errors = []
        if self.frame_count not in SUPPORTED_FRAME_COUNTS:
            errors.append(f"frame_count:{self.frame_count}")
        if self.duration_ms <= 0:
            errors.append("duration")
        if not self.name.strip():
            errors.append("name")
        missing = [path for path in self.frame_paths if not Path(path).is_file()]
        if missing:
            errors.append(f"missing_frames:{len(missing)}")
        if len(self.backgrounds) > self.frame_count:
            errors.append(f"background_count:{len(self.backgrounds)}")
        for index, background in enumerate(self.backgrounds, 1):
            if not Path(background.image_path).is_file():
                errors.append(f"missing_background:{index}")
            if not (1 <= background.start_frame <= background.end_frame <= self.frame_count):
                errors.append(f"background_range:{index}")
        return errors

    def duplicate(self, name: str | None = None) -> "AnimationJob":
        result = deepcopy(self)
        result.name = name or f"{self.name} copy"
        result.status = "ready"
        result.status_message = ""
        return result


class AnimationQueue:
    def __init__(self, jobs: list[AnimationJob] | None = None) -> None:
        self.jobs = jobs or []

    def add(self, job: AnimationJob) -> int:
        self.jobs.append(job)
        return len(self.jobs) - 1

    def remove(self, index: int) -> AnimationJob:
        return self.jobs.pop(index)

    def duplicate(self, index: int) -> int:
        self.jobs.insert(index + 1, self.jobs[index].duplicate())
        return index + 1

    def clear(self) -> None:
        self.jobs.clear()

    def move(self, index: int, offset: int) -> int:
        target = index + offset
        if not (0 <= index < len(self.jobs) and 0 <= target < len(self.jobs)):
            return index
        self.jobs[index], self.jobs[target] = self.jobs[target], self.jobs[index]
        return target

    def validation_errors(self) -> dict[int, list[str]]:
        return {index: errors for index, job in enumerate(self.jobs) if (errors := job.validation_errors())}
