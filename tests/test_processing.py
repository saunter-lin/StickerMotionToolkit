from __future__ import annotations

import pytest
from PIL import Image

from app.version import __version__
from sticker_motion.animation import DEFAULT_FRAME_DURATION_MS, build_animation
from sticker_motion.background import remove_background
from sticker_motion.splitter import detect_layout, split_sheet
from app.workers import pipeline


COLORS = [
    (255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255), (255, 255, 0, 255),
    (255, 0, 255, 255), (0, 255, 255, 255), (128, 0, 0, 255), (0, 128, 0, 255),
    (0, 0, 128, 255), (128, 128, 0, 255), (128, 0, 128, 255), (0, 128, 128, 255),
    (192, 64, 0, 255), (64, 192, 0, 255), (0, 64, 192, 255),
]


def test_development_version() -> None:
    assert __version__ == "1.4.0-dev"


def horizontal_sheet(count: int) -> Image.Image:
    sheet = Image.new("RGBA", (count * 10, 10))
    for index in range(count):
        sheet.paste(COLORS[index], (index * 10, 0, (index + 1) * 10, 10))
    return sheet


@pytest.mark.parametrize("count", [2, 4, 5, 6, 7, 8, 15])
def test_splits_supported_horizontal_frame_counts(count: int) -> None:
    frames = split_sheet(horizontal_sheet(count), count, "horizontal")
    assert len(frames) == count
    assert all(frame.size == (10, 10) for frame in frames)
    assert [frame.getpixel((5, 5)) for frame in frames] == COLORS[:count]


def test_grid_split_uses_reading_order() -> None:
    sheet = Image.new("RGBA", (30, 20))
    for index, color in enumerate(COLORS[:6]):
        x, y = (index % 3) * 10, (index // 3) * 10
        sheet.paste(color, (x, y, x + 10, y + 10))
    frames = split_sheet(sheet, 6, "grid")
    assert [frame.getpixel((5, 5)) for frame in frames] == COLORS[:6]
    assert detect_layout(sheet.size, 6) == "grid"


def test_invalid_count_and_indivisible_sheet_are_rejected() -> None:
    with pytest.raises(ValueError, match="frame_count"):
        split_sheet(horizontal_sheet(4), 1)
    with pytest.raises(ValueError, match="not evenly divisible"):
        split_sheet(Image.new("RGBA", (41, 10)), 4, "horizontal")


def test_animation_defaults_and_background_removal() -> None:
    image = Image.new("RGBA", (3, 3), "white")
    image.putpixel((1, 1), (10, 20, 30, 255))
    cleaned = remove_background(image)
    assert cleaned.getpixel((0, 0))[3] == 0
    assert cleaned.getpixel((1, 1))[3] == 255
    animation = build_animation([cleaned] * 4)
    assert animation.duration_ms == DEFAULT_FRAME_DURATION_MS == 200
    assert animation.frames[0].mode == "RGBA"


def test_ordered_frame_files_reach_exporter_in_exact_order(tmp_path, monkeypatch) -> None:
    paths = []
    for number, red in enumerate((40, 10, 30, 20), 1):
        path = tmp_path / f"frame{number}.png"
        Image.new("RGBA", (4, 4), (red, 0, 0, 255)).save(path)
        paths.append(path)
    captured = {}

    def fake_export(animation, platform, destination):
        captured["reds"] = [frame.getpixel((0, 0))[0] for frame in animation.frames]
        captured["platform"] = platform
        return destination

    monkeypatch.setattr(pipeline, "export_animation", fake_export)
    pipeline.process_frame_files(paths, tmp_path / "ordered.png", "line")
    assert captured == {"reds": [40, 10, 30, 20], "platform": "line"}


@pytest.mark.parametrize("count", [2, 4, 5, 6, 7, 8, 15])
def test_ordered_frame_pipeline_accepts_arbitrary_counts(tmp_path, monkeypatch, count: int) -> None:
    paths = []
    for index in range(count):
        path = tmp_path / f"frame{index}.png"
        Image.new("RGBA", (4, 4), (index, 0, 0, 255)).save(path)
        paths.append(path)
    captured = []
    monkeypatch.setattr(pipeline, "export_animation", lambda animation, platform, destination: captured.extend(animation.frames) or destination)
    pipeline.process_frame_files(paths, tmp_path / "ordered.gif", "wechat")
    assert len(captured) == count


def test_ordered_frame_pipeline_rejects_more_than_fifteen(tmp_path) -> None:
    paths = []
    for index in range(16):
        path = tmp_path / f"frame{index}.png"
        Image.new("RGBA", (4, 4)).save(path)
        paths.append(path)
    with pytest.raises(ValueError, match="between 2 and 15"):
        pipeline.process_frame_files(paths, tmp_path / "too-many.gif", "wechat")
