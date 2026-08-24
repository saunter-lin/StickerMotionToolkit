"""Animation job and queue models shared by GUI and batch processing."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

from .line_validation import (
    ExportValidationResult, LINE_PLAYBACK_SECONDS,
)
from .splitter import MAX_FRAME_COUNT, MIN_FRAME_COUNT

DEFAULT_GROUP_DURATION_MS = 220
MIN_FRAME_DURATION_MS = 10
MAX_FRAME_DURATION_MS = 10_000


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
    play_count: int = 1
    remove_background: bool = False
    background_tolerance: int = 0
    output_filename: str = ""
    text_overlay: TextOverlaySettings = field(default_factory=TextOverlaySettings)
    backgrounds: list[BackgroundEntry] = field(default_factory=list)
    status: str = "ready"
    status_message: str = ""
    post_export_validation: ExportValidationResult | None = None
    frame_duration_overrides_ms: list[int | None] = field(default_factory=list)

    @property
    def frame_count(self) -> int:
        return len(self.frame_paths)

    @property
    def extension(self) -> str:
        return ".png" if self.platform == "line" else ".gif"

    def resolved_filename(self) -> str:
        raw = self.output_filename.strip() or self.name.strip() or "animation"
        return str(Path(raw).with_suffix(self.extension).name)

    def _normalize_frame_duration_overrides(self) -> None:
        """Keep optional timing metadata aligned with the existing path model."""
        del self.frame_duration_overrides_ms[self.frame_count:]
        self.frame_duration_overrides_ms.extend(
            [None] * (self.frame_count - len(self.frame_duration_overrides_ms))
        )

    def effective_frame_durations_ms(self) -> tuple[int, ...]:
        """Resolve inherited timing without expanding defaults into stored overrides."""
        return tuple(
            self.duration_ms if index >= len(self.frame_duration_overrides_ms) or override is None else override
            for index, override in enumerate(self.frame_duration_overrides_ms[:self.frame_count])
        ) + (self.duration_ms,) * max(0, self.frame_count - len(self.frame_duration_overrides_ms))

    def set_frame_duration_override(self, index: int, duration_ms: int | None) -> None:
        if not 0 <= index < self.frame_count:
            raise IndexError("frame index out of range")
        if duration_ms is not None and not MIN_FRAME_DURATION_MS <= duration_ms <= MAX_FRAME_DURATION_MS:
            raise ValueError(
                f"frame duration must be between {MIN_FRAME_DURATION_MS} and {MAX_FRAME_DURATION_MS} ms"
            )
        self._normalize_frame_duration_overrides()
        self.frame_duration_overrides_ms[index] = duration_ms
        self.invalidate_post_export_validation()

    def add_frame_paths(self, paths: list[Path]) -> None:
        self._normalize_frame_duration_overrides()
        self.frame_paths.extend(paths)
        self.frame_duration_overrides_ms.extend([None] * len(paths))
        self.invalidate_post_export_validation()

    def move_frame(self, index: int, offset: int) -> int:
        target = index + offset
        if not (0 <= index < self.frame_count and 0 <= target < self.frame_count):
            return index
        self._normalize_frame_duration_overrides()
        self.frame_paths[index], self.frame_paths[target] = self.frame_paths[target], self.frame_paths[index]
        self.frame_duration_overrides_ms[index], self.frame_duration_overrides_ms[target] = (
            self.frame_duration_overrides_ms[target], self.frame_duration_overrides_ms[index],
        )
        self.invalidate_post_export_validation()
        return target

    def remove_frame(self, index: int) -> Path:
        self._normalize_frame_duration_overrides()
        self.frame_duration_overrides_ms.pop(index)
        path = self.frame_paths.pop(index)
        self.invalidate_post_export_validation()
        return path

    def clear_frames(self) -> None:
        self.frame_paths.clear()
        self.frame_duration_overrides_ms.clear()
        self.invalidate_post_export_validation()

    def validation_errors(self) -> list[str]:
        errors = []
        if not MIN_FRAME_COUNT <= self.frame_count <= MAX_FRAME_COUNT:
            errors.append(f"frame_count:{self.frame_count}")
        if self.duration_ms <= 0:
            errors.append("duration")
        for index, override in enumerate(self.frame_duration_overrides_ms[:self.frame_count], 1):
            if override is not None and not MIN_FRAME_DURATION_MS <= override <= MAX_FRAME_DURATION_MS:
                errors.append(f"frame_duration:{index}")
        if not self.name.strip():
            errors.append("name")
        if self.platform not in {"line", "wechat"}:
            errors.append(f"platform:{self.platform}")
        if self.platform == "line":
            if self.play_count not in LINE_PLAYBACK_SECONDS:
                errors.append(f"line_play_count:{self.play_count}")
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

    def invalidate_post_export_validation(self) -> None:
        self.post_export_validation = None
        self.status = "ready"
        self.status_message = ""

    def duplicate(self, name: str | None = None) -> "AnimationJob":
        result = deepcopy(self)
        result.name = name or f"{self.name} copy"
        result.status = "ready"
        result.status_message = ""
        result.post_export_validation = None
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
