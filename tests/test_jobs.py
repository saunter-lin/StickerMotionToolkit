from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageChops

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from sticker_motion.batch import export_jobs, prepare_job_frames, unique_output_path
from sticker_motion.jobs import AnimationJob, AnimationQueue, BackgroundEntry, TextOverlaySettings
from sticker_motion.background_layer import apply_backgrounds, scale_to_cover
from sticker_motion.text_overlay import overlay_position, render_text_layer


@pytest.fixture(scope="module", autouse=True)
def qt_app():
    yield QApplication.instance() or QApplication([])


def make_frames(tmp_path: Path, count: int, transparent: bool = False) -> list[Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    paths = []
    for index in range(count):
        color = (20 * index, 40, 90, 0 if transparent else 255)
        path = tmp_path / f"frame{index + 1}.png"
        Image.new("RGBA", (160, 100), color).save(path)
        paths.append(path)
    return paths


def test_queue_operations_and_order() -> None:
    queue = AnimationQueue()
    queue.add(AnimationJob("A"))
    queue.add(AnimationJob("B"))
    queue.add(AnimationJob("C"))
    duplicate = queue.duplicate(0)
    assert duplicate == 1
    assert [job.name for job in queue.jobs] == ["A", "A copy", "B", "C"]
    queue.move(3, -1)
    assert [job.name for job in queue.jobs] == ["A", "A copy", "C", "B"]
    queue.remove(1)
    assert [job.name for job in queue.jobs] == ["A", "C", "B"]
    queue.clear()
    assert queue.jobs == []


@pytest.mark.parametrize("count", [2, 4, 5, 6, 7, 8, 15])
def test_supported_job_counts(tmp_path: Path, count: int) -> None:
    job = AnimationJob("valid", make_frames(tmp_path, count))
    assert job.frame_count == count
    assert job.validation_errors() == []


@pytest.mark.parametrize("count", [0, 1, 16])
def test_invalid_frame_count(tmp_path: Path, count: int) -> None:
    job = AnimationJob("invalid", make_frames(tmp_path, count))
    assert job.validation_errors() == [f"frame_count:{count}"]


def test_text_disabled_leaves_frames_unchanged(tmp_path: Path) -> None:
    paths = make_frames(tmp_path, 4)
    job = AnimationJob("plain", paths, text_overlay=TextOverlaySettings(enabled=False, text="Hello"))
    frames, _ = prepare_job_frames(job)
    with Image.open(paths[0]) as original:
        assert ImageChops.difference(original.convert("RGBA"), frames[0]).getbbox() is None


@pytest.mark.parametrize("position", ["top", "center", "bottom"])
def test_text_applied_to_every_frame_with_position_and_stroke(tmp_path: Path, position: str) -> None:
    paths = make_frames(tmp_path / position, 4, transparent=True)
    settings = TextOverlaySettings(
        enabled=True,
        text="測試 Test",
        font_size=26,
        color="#ff0000",
        stroke_color="#ffffff",
        stroke_width=2,
        vertical_position=position,
        horizontal_alignment="right",
        x_offset=-3,
        y_offset=2,
    )
    frames, available = prepare_job_frames(AnimationJob(position, paths, text_overlay=settings))
    assert available
    assert all(frame.getbbox() is not None for frame in frames)
    assert all(frame.getchannel("A").getextrema()[1] == 255 for frame in frames)


def test_font_fallback_and_long_text_do_not_crash(tmp_path: Path) -> None:
    settings = TextOverlaySettings(enabled=True, text="中文 English " * 20, font_family="Definitely Missing", font_size=30)
    frames, available = prepare_job_frames(AnimationJob("fallback", make_frames(tmp_path, 4), text_overlay=settings))
    assert len(frames) == 4
    assert not available


def test_offsets_change_rendered_result(tmp_path: Path) -> None:
    paths = make_frames(tmp_path, 4)
    base = TextOverlaySettings(enabled=True, text="Offset", font_size=24)
    shifted = TextOverlaySettings(enabled=True, text="Offset", font_size=24, x_offset=20, y_offset=-10)
    first, _ = prepare_job_frames(AnimationJob("one", paths, text_overlay=base))
    second, _ = prepare_job_frames(AnimationJob("two", paths, text_overlay=shifted))
    assert ImageChops.difference(first[0].convert("RGB"), second[0].convert("RGB")).getbbox() is not None


def test_unique_output_path_uses_numeric_suffix(tmp_path: Path) -> None:
    (tmp_path / "wave.png").touch()
    (tmp_path / "wave-2.png").touch()
    assert unique_output_path(tmp_path, "wave.png").name == "wave-3.png"


def test_batch_export_order_and_mixed_platforms(tmp_path: Path) -> None:
    frames = make_frames(tmp_path / "frames", 4)
    jobs = [
        AnimationJob("wave", frames, platform="line", output_filename="wave"),
        AnimationJob("hug", frames, platform="wechat", output_filename="hug", text_overlay=TextOverlaySettings(enabled=True, text="Hi")),
    ]
    progress = []
    outputs = export_jobs(jobs, tmp_path / "output", lambda index, total, job: progress.append(job.name))
    assert progress == ["wave", "hug"]
    assert [path.name for path in outputs] == ["wave.png", "hug.gif"]
    with Image.open(outputs[0]) as apng, Image.open(outputs[1]) as gif:
        assert apng.n_frames == gif.n_frames == 4
        assert apng.format == "PNG"
        assert gif.format == "GIF"


def test_batch_validates_all_jobs_before_writing(tmp_path: Path) -> None:
    valid = AnimationJob("valid", make_frames(tmp_path / "valid", 4))
    invalid = AnimationJob("invalid", make_frames(tmp_path / "invalid", 1))
    with pytest.raises(ValueError, match="invalid_jobs:2"):
        export_jobs([valid, invalid], tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_v12_text_defaults_are_backward_compatible() -> None:
    settings = TextOverlaySettings()
    assert settings.font_family == "Iansui"
    assert settings.text_direction == "horizontal"
    assert settings.rotation_angle == 0


def test_default_platform_is_wechat() -> None:
    assert AnimationJob("default").platform == "wechat"
    assert AnimationJob("default").duration_ms == 220


def test_explicit_legacy_duration_remains_unchanged() -> None:
    assert AnimationJob("legacy", duration_ms=200).duration_ms == 200


def test_background_scale_to_cover_center_crops() -> None:
    source = Image.new("RGB", (200, 100), "red")
    result = scale_to_cover(source, (100, 100))
    assert result.size == (100, 100)
    assert result.getpixel((50, 50)) == (255, 0, 0, 255)


def test_background_ranges_overlap_in_list_order_and_leave_unassigned_transparent(tmp_path: Path) -> None:
    red = tmp_path / "red.png"; blue = tmp_path / "blue.png"
    Image.new("RGBA", (20, 20), "red").save(red); Image.new("RGBA", (20, 20), (0, 0, 255, 128)).save(blue)
    transparent = Image.new("RGBA", (20, 20))
    entries = [BackgroundEntry(red, 2, 4), BackgroundEntry(blue, 3, 3)]
    assert apply_backgrounds(transparent, entries, 1).getbbox() is None
    assert apply_backgrounds(transparent, entries, 2).getpixel((10, 10)) == (255, 0, 0, 255)
    overlap = apply_backgrounds(transparent, entries, 3).getpixel((10, 10))
    assert overlap[2] > 0 and overlap[0] > 0 and overlap[3] == 255


def test_background_frame_text_layer_order(tmp_path: Path) -> None:
    background = tmp_path / "background.png"; frame_path = tmp_path / "frame.png"
    Image.new("RGB", (120, 80), "blue").save(background)
    Image.new("RGBA", (120, 80), (255, 0, 0, 128)).save(frame_path)
    settings = TextOverlaySettings(enabled=True, text="TOP", color="#ffffff", stroke_width=0, vertical_position="center")
    job = AnimationJob("layers", [frame_path] * 4, backgrounds=[BackgroundEntry(background, 1, 4)], text_overlay=settings)
    frames, _ = prepare_job_frames(job)
    assert frames[0].getpixel((0, 0))[3] == 255
    background_and_frame = apply_backgrounds(Image.open(frame_path), job.backgrounds, 1)
    assert ImageChops.difference(frames[0].convert("RGB"), background_and_frame.convert("RGB")).getbbox() is not None


def test_background_validation_count_ranges_and_missing(tmp_path: Path) -> None:
    paths = make_frames(tmp_path / "frames", 4)
    valid_bg = tmp_path / "bg.png"; Image.new("RGB", (20, 20)).save(valid_bg)
    too_many = [BackgroundEntry(valid_bg, 1, 4) for _ in range(5)]
    errors = AnimationJob("invalid", paths, backgrounds=too_many + [BackgroundEntry(tmp_path / "missing.png", 0, 5)]).validation_errors()
    assert "background_count:6" in errors
    assert "missing_background:6" in errors
    assert "background_range:6" in errors


def test_five_frame_background_range_uses_actual_group_count(tmp_path: Path) -> None:
    paths = make_frames(tmp_path / "frames", 5)
    background = tmp_path / "background.png"; Image.new("RGB", (20, 20)).save(background)
    assert AnimationJob("valid", paths, backgrounds=[BackgroundEntry(background, 1, 5)]).validation_errors() == []
    assert "background_range:1" in AnimationJob(
        "invalid", paths, backgrounds=[BackgroundEntry(background, 1, 6)]
    ).validation_errors()


@pytest.mark.parametrize("count", [5, 7])
@pytest.mark.parametrize("platform", ["line", "wechat"])
def test_arbitrary_frame_count_exports_exact_source_total(tmp_path: Path, count: int, platform: str) -> None:
    paths = make_frames(tmp_path / f"{platform}-{count}", count)
    output = export_jobs([AnimationJob("custom", paths, platform=platform)], tmp_path / "out")[0]
    with Image.open(output) as animation:
        assert animation.n_frames == count


@pytest.mark.parametrize("platform", ["line", "wechat"])
def test_background_ranges_export_without_changing_frame_order(tmp_path: Path, platform: str) -> None:
    paths = make_frames(tmp_path / platform, 4, transparent=True)
    for index, path in enumerate(paths):
        with Image.open(path) as source:
            frame = source.convert("RGBA")
        frame.putpixel((index, index), (255, index * 40, 0, 255)); frame.save(path)
    background = tmp_path / f"{platform}-bg.png"; Image.new("RGB", (200, 80), "green").save(background)
    job = AnimationJob("range", paths, platform=platform, duration_ms=250, backgrounds=[BackgroundEntry(background, 2, 3)])
    output = export_jobs([job], tmp_path / "out")[0]
    with Image.open(output) as animation:
        assert animation.n_frames == 4
        assert animation.info.get("duration") == 250


@pytest.mark.parametrize("text,direction", [("你好", "horizontal"), ("你好", "vertical"), ("Test", "horizontal"), ("Test", "vertical")])
def test_horizontal_and_vertical_text_render_transparently(text: str, direction: str) -> None:
    settings = TextOverlaySettings(enabled=True, text=text, font_size=32, stroke_width=3, text_direction=direction)
    layer, _ = render_text_layer(settings)
    assert layer.mode == "RGBA"
    assert layer.getchannel("A").getextrema() == (0, 255)
    if direction == "vertical":
        assert layer.height > layer.width


@pytest.mark.parametrize("direction", ["horizontal", "vertical"])
@pytest.mark.parametrize("angle", [0, 15, -15, 30, -30, 37])
def test_rotation_angles_render_without_clipping(direction: str, angle: int) -> None:
    plain, _ = render_text_layer(TextOverlaySettings(enabled=True, text="旋轉 Test", font_size=28, text_direction=direction))
    rotated, _ = render_text_layer(TextOverlaySettings(enabled=True, text="旋轉 Test", font_size=28, text_direction=direction, rotation_angle=angle))
    assert rotated.getbbox() is not None
    if angle:
        assert rotated.size != plain.size


def test_position_presets_and_signed_offsets() -> None:
    frame, layer = (200, 120), (40, 20)
    left_top = overlay_position(frame, layer, TextOverlaySettings(horizontal_alignment="left", vertical_position="top"))
    right_bottom = overlay_position(frame, layer, TextOverlaySettings(horizontal_alignment="right", vertical_position="bottom"))
    center = overlay_position(frame, layer, TextOverlaySettings(horizontal_alignment="center", vertical_position="center"))
    shifted = overlay_position(frame, layer, TextOverlaySettings(horizontal_alignment="center", vertical_position="center", x_offset=10, y_offset=-8))
    assert left_top[0] < center[0] < right_bottom[0]
    assert left_top[1] < center[1] < right_bottom[1]
    assert shifted == (center[0] + 10, center[1] - 8)


@pytest.mark.parametrize("platform,extension", [("line", ".png"), ("wechat", ".gif")])
@pytest.mark.parametrize("direction", ["horizontal", "vertical"])
def test_rotated_text_exports_on_every_frame(tmp_path: Path, platform: str, extension: str, direction: str) -> None:
    paths = make_frames(tmp_path / f"{platform}-{direction}", 4)
    settings = TextOverlaySettings(enabled=True, text="測試 Test", font_size=24, text_direction=direction, rotation_angle=15)
    output = export_jobs([AnimationJob("rotated", paths, platform=platform, text_overlay=settings)], tmp_path / "out")[0]
    assert output.suffix == extension
    with Image.open(output) as animation:
        assert animation.n_frames == 4
        assert all(animation.seek(index) is None and animation.convert("RGBA").getbbox() is not None for index in range(4))
