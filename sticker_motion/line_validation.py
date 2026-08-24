"""LINE-specific APNG post-export validation."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import struct
from typing import Literal

from PIL import Image

LINE_APNG_MAX_BYTES = 1_000_000
LINE_APNG_WARNING_BYTES = 950_000
LINE_MAX_TOTAL_DURATION_MS = 4_000
LINE_PLAYBACK_SECONDS = (1, 2, 3, 4)

ValidationLevel = Literal["ok", "warning", "error"]


@dataclass(frozen=True)
class ExportValidationResult:
    level: ValidationLevel
    reasons: tuple[str, ...]
    file_bytes: int
    actual_play_count: int | None = None
    actual_playback_ms: int | None = None


@dataclass(frozen=True)
class ApngTiming:
    frame_count: int
    play_count: int
    frame_delays: tuple[Fraction, ...]

    @property
    def one_cycle_seconds(self) -> Fraction:
        return sum(self.frame_delays, start=Fraction())

    @property
    def total_playback_seconds(self) -> Fraction:
        return self.one_cycle_seconds * self.play_count


def line_frame_durations_ms(
    frame_count: int,
    playback_seconds: int,
    weights: tuple[int, ...] | None = None,
) -> tuple[int, ...]:
    """Distribute exact cycle timing, optionally preserving per-frame rhythm weights."""
    if frame_count <= 0 or playback_seconds not in LINE_PLAYBACK_SECONDS:
        raise ValueError("invalid LINE playback timing")
    if weights is not None:
        if len(weights) != frame_count or any(weight <= 0 for weight in weights):
            raise ValueError("invalid LINE frame duration weights")
        target_ms = playback_seconds * 1_000
        if target_ms < frame_count:
            raise ValueError("too many frames for LINE playback timing")
        remaining_ms = target_ms - frame_count
        total_weight = sum(weights)
        shares = [Fraction(weight * remaining_ms, total_weight) for weight in weights]
        durations = [1 + share.numerator // share.denominator for share in shares]
        remainder = target_ms - sum(durations)
        order = sorted(
            range(frame_count),
            key=lambda index: (shares[index] - int(shares[index]), -index),
            reverse=True,
        )
        for index in order[:remainder]:
            durations[index] += 1
        return tuple(durations)
    base, remainder = divmod(playback_seconds * 1_000, frame_count)
    if base <= 0:
        raise ValueError("too many frames for LINE playback timing")
    return (base + 1,) * remainder + (base,) * (frame_count - remainder)


def line_play_count(playback_seconds: int) -> int:
    """Use the maximum legal whole-number loop count without exceeding four seconds."""
    if playback_seconds not in LINE_PLAYBACK_SECONDS:
        raise ValueError("invalid LINE playback time")
    return LINE_MAX_TOTAL_DURATION_MS // (playback_seconds * 1_000)


def read_apng_timing(path: str | Path) -> ApngTiming:
    """Read acTL/fcTL timing directly so validation uses encoded rational delays."""
    data = Path(path).read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not a PNG")
    offset = 8
    frame_count = play_count = None
    delays: list[Fraction] = []
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        chunk = data[offset + 8:offset + 8 + length]
        if len(chunk) != length:
            raise ValueError("truncated PNG chunk")
        if chunk_type == b"acTL" and length == 8:
            frame_count, play_count = struct.unpack(">II", chunk)
        elif chunk_type == b"fcTL" and length == 26:
            fields = struct.unpack(">IIIIIHHBB", chunk)
            delay_num, delay_den = fields[5], fields[6] or 100
            delays.append(Fraction(delay_num, delay_den))
        offset += length + 12
        if chunk_type == b"IEND":
            break
    if frame_count is None or play_count is None or len(delays) != frame_count:
        raise ValueError("invalid APNG timing metadata")
    return ApngTiming(frame_count, play_count, tuple(delays))


def classify_line_apng_size(file_bytes: int) -> ValidationLevel:
    if file_bytes > LINE_APNG_MAX_BYTES:
        return "error"
    if file_bytes > LINE_APNG_WARNING_BYTES:
        return "warning"
    return "ok"


def validate_line_apng(
    path: str | Path,
    requested_playback_seconds: int,
    expected_frame_count: int | None = None,
) -> ExportValidationResult:
    """Read back encoded metadata and validate actual bytes without deleting output."""
    output = Path(path)
    file_bytes = output.stat().st_size
    reasons: list[str] = []
    try:
        timing = read_apng_timing(output)
        with Image.open(output) as image:
            actual_play_count = timing.play_count
            if image.format != "PNG" or not image.is_animated:
                reasons.append("line_metadata_invalid")
            if expected_frame_count is not None and image.n_frames != expected_frame_count:
                reasons.append(f"line_frame_count_mismatch:{expected_frame_count}:{image.n_frames}")
        actual_playback_ms = int(timing.one_cycle_seconds * 1_000)
    except Exception:
        actual_play_count = None
        actual_playback_ms = None
        timing = None
        reasons.append("line_metadata_invalid")

    expected_play_count = line_play_count(requested_playback_seconds)
    if actual_play_count == 0:
        reasons.append("line_infinite_loop")
    elif actual_play_count != expected_play_count:
        reasons.append(f"line_play_count_mismatch:{expected_play_count}:{actual_play_count}")
    if timing is not None:
        expected_cycle = Fraction(requested_playback_seconds, 1)
        if timing.one_cycle_seconds != expected_cycle:
            reasons.append(
                f"line_playback_mismatch:{requested_playback_seconds * 1000}:{actual_playback_ms}"
            )
        if timing.total_playback_seconds > Fraction(4, 1):
            reasons.append(f"line_total_playback:{float(timing.total_playback_seconds):g}")

    size_level = classify_line_apng_size(file_bytes)
    if size_level == "warning":
        reasons.append(f"line_size_warning:{file_bytes}")
    elif size_level == "error":
        reasons.append(f"line_size_error:{file_bytes}")

    level: ValidationLevel
    if any(reason.startswith(("line_metadata", "line_infinite", "line_play_count_mismatch", "line_playback_mismatch", "line_total_playback", "line_frame_count_mismatch", "line_size_error")) for reason in reasons):
        level = "error"
    elif reasons:
        level = "warning"
    else:
        level = "ok"
        reasons.append(f"line_export_ok:{file_bytes}:{actual_play_count}:{actual_playback_ms}")
    return ExportValidationResult(level, tuple(reasons), file_bytes, actual_play_count, actual_playback_ms)
