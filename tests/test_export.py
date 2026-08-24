from __future__ import annotations

from PIL import Image

from sticker_motion.animation import build_animation
from sticker_motion.animation import Animation
from sticker_motion.export import export_animation, export_line_apng


def animation(count: int = 4, duration: int = 200):
    frames = [Image.new("RGBA", (16, 16), (index * 40, 20, 200, 255)) for index in range(count)]
    return build_animation(frames, duration)


def test_line_export_is_animated_png(tmp_path) -> None:
    path = export_animation(animation(6, 150), "line", tmp_path / "line-output")
    assert path.suffix == ".png"
    with Image.open(path) as exported:
        assert exported.format == "PNG"
        assert exported.is_animated
        assert exported.n_frames == 6
        assert exported.info["duration"] == 150.0


def test_generic_apng_preserves_infinite_loop_behavior(tmp_path) -> None:
    source = animation(4)
    path = export_line_apng(Animation(source.frames, source.duration_ms, loop=0), tmp_path / "generic.png")
    with Image.open(path) as exported:
        assert exported.info["loop"] == 0


def test_wechat_export_is_animated_gif(tmp_path) -> None:
    path = export_animation(animation(8), "wechat", tmp_path / "wechat-output.png")
    assert path.suffix == ".gif"
    with Image.open(path) as exported:
        assert exported.format == "GIF"
        assert exported.is_animated
        assert exported.n_frames == 8
        assert exported.info["duration"] == 200


def test_generic_gif_and_apng_preserve_per_frame_durations(tmp_path) -> None:
    frames = tuple(Image.new("RGBA", (16, 16), (index * 40, 20, 200, 255)) for index in range(4))
    durations = (180, 220, 500, 300)
    for platform, name in (("wechat", "timing.gif"), ("line", "timing.png")):
        path = export_animation(Animation(frames, durations), platform, tmp_path / name)
        with Image.open(path) as exported:
            actual = []
            for index in range(exported.n_frames):
                exported.seek(index); actual.append(int(exported.info["duration"]))
        assert actual == list(durations)


def test_export_preserves_transparency(tmp_path) -> None:
    frames = []
    for index in range(4):
        frame = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        frame.putpixel((index, index), (255, 0, 0, 255))
        frames.append(frame)
    path = export_animation(build_animation(frames), "wechat", tmp_path / "transparent.gif")
    with Image.open(path) as exported:
        assert exported.convert("RGBA").getpixel((7, 7))[3] == 0
