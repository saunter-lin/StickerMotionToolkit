"""Sequential safe batch export for animation jobs."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PIL import Image

from .animation import Animation, build_animation
from .background import remove_background
from .background_layer import apply_backgrounds
from .export import export_animation
from .jobs import AnimationJob
from .line_validation import (
    ExportValidationResult, line_frame_durations_ms, line_play_count, validate_line_apng,
)
from .text_overlay import apply_text_overlay

ProgressCallback = Callable[[int, int, AnimationJob], None]


def unique_output_path(folder: Path, filename: str) -> Path:
    """Never overwrite: append a numeric suffix when a destination exists."""
    candidate = folder / filename
    counter = 2
    while candidate.exists():
        candidate = folder / f"{Path(filename).stem}-{counter}{Path(filename).suffix}"
        counter += 1
    return candidate


def prepare_job_frames(job: AnimationJob) -> tuple[list[Image.Image], bool]:
    frames: list[Image.Image] = []
    font_available = True
    for frame_number, path in enumerate(job.frame_paths, 1):
        with Image.open(path) as source:
            frame = source.convert("RGBA")
        if job.remove_background:
            frame = remove_background(frame, job.background_tolerance)
        frame = apply_backgrounds(frame, job.backgrounds, frame_number)
        frame, available = apply_text_overlay(frame, job.text_overlay)
        font_available = font_available and available
        frames.append(frame)
    return frames, font_available


def export_job(job: AnimationJob, output_folder: str | Path) -> Path:
    errors = job.validation_errors()
    if errors:
        raise ValueError(",".join(errors))
    frames, font_available = prepare_job_frames(job)
    if not font_available:
        job.status_message = "font_fallback"
    effective_durations = job.effective_frame_durations_ms()
    animation = build_animation(frames, effective_durations)
    if job.platform == "line":
        animation = Animation(
            animation.frames,
            line_frame_durations_ms(job.frame_count, job.play_count, effective_durations),
            line_play_count(job.play_count),
        )
    destination = unique_output_path(Path(output_folder), job.resolved_filename())
    output = export_animation(animation, job.platform, destination)
    if job.platform == "line":
        result = validate_line_apng(output, job.play_count, job.frame_count)
    else:
        result = ExportValidationResult("ok", (f"export_ok:{output.stat().st_size}",), output.stat().st_size)
    job.post_export_validation = result
    job.status_message = result.reasons[0]
    if result.level == "error":
        raise ValueError(result.reasons[0])
    job.status = "warning" if result.level == "warning" else "complete"
    return output


def export_jobs(
    jobs: list[AnimationJob],
    output_folder: str | Path,
    progress: ProgressCallback | None = None,
) -> list[Path]:
    invalid = {index: job.validation_errors() for index, job in enumerate(jobs) if job.validation_errors()}
    if invalid:
        raise ValueError(f"invalid_jobs:{','.join(str(index + 1) for index in invalid)}")
    folder = Path(output_folder)
    folder.mkdir(parents=True, exist_ok=True)
    outputs = []
    total = len(jobs)
    for index, job in enumerate(jobs):
        job.post_export_validation = None
        job.status = "exporting"
        if progress:
            progress(index, total, job)
        try:
            outputs.append(export_job(job, folder))
        except Exception as error:
            job.status = "error"
            if job.post_export_validation is None:
                job.post_export_validation = ExportValidationResult("error", (f"exporter_failure:{error}",), 0)
                job.status_message = job.post_export_validation.reasons[0]
            raise
        if job.status == "exporting":
            job.status = "complete"
    return outputs
