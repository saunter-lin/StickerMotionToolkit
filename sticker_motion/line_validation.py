"""LINE-specific APNG post-export validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PIL import Image

LINE_APNG_MAX_BYTES = 1_000_000
LINE_APNG_WARNING_BYTES = 950_000
LINE_MAX_TOTAL_DURATION_MS = 4_000
LINE_PLAY_COUNTS = (1, 2, 3, 4)

ValidationLevel = Literal["ok", "warning", "error"]


@dataclass(frozen=True)
class ExportValidationResult:
    level: ValidationLevel
    reasons: tuple[str, ...]
    file_bytes: int
    actual_play_count: int | None = None


def classify_line_apng_size(file_bytes: int) -> ValidationLevel:
    if file_bytes > LINE_APNG_MAX_BYTES:
        return "error"
    if file_bytes > LINE_APNG_WARNING_BYTES:
        return "warning"
    return "ok"


def validate_line_apng(path: str | Path, requested_play_count: int) -> ExportValidationResult:
    """Read back encoded metadata and validate actual bytes without deleting output."""
    output = Path(path)
    file_bytes = output.stat().st_size
    reasons: list[str] = []
    try:
        with Image.open(output) as image:
            actual_play_count = image.info.get("loop")
            if image.format != "PNG" or not image.is_animated:
                reasons.append("line_metadata_invalid")
    except Exception:
        actual_play_count = None
        reasons.append("line_metadata_invalid")

    if actual_play_count == 0:
        reasons.append("line_infinite_loop")
    elif actual_play_count != requested_play_count:
        reasons.append(f"line_play_count_mismatch:{requested_play_count}:{actual_play_count}")

    size_level = classify_line_apng_size(file_bytes)
    if size_level == "warning":
        reasons.append(f"line_size_warning:{file_bytes}")
    elif size_level == "error":
        reasons.append(f"line_size_error:{file_bytes}")

    level: ValidationLevel
    if any(reason.startswith(("line_metadata", "line_infinite", "line_play_count_mismatch", "line_size_error")) for reason in reasons):
        level = "error"
    elif reasons:
        level = "warning"
    else:
        level = "ok"
        reasons.append(f"line_export_ok:{file_bytes}:{actual_play_count}")
    return ExportValidationResult(level, tuple(reasons), file_bytes, actual_play_count)
