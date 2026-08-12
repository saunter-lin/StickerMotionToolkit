"""GUI entry point used by the packaged macOS application."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

from app.ui.desktop import launch
from app.workers.pipeline import process_frame_files


def packaged_self_test(output_dir: Path) -> int:
    """Exercise frozen PNG/APNG/GIF support without affecting normal launch."""
    output_dir.mkdir(parents=True, exist_ok=True)
    frame_paths = []
    for index, color in enumerate(("red", "green", "blue", "yellow"), 1):
        path = output_dir / f"frame{index}.png"
        Image.new("RGBA", (32, 32), color).save(path)
        frame_paths.append(path)
    line_path = process_frame_files(frame_paths, output_dir / "line.png", "line")
    wechat_path = process_frame_files(frame_paths, output_dir / "wechat.gif", "wechat")
    for path, expected_format in ((line_path, "PNG"), (wechat_path, "GIF")):
        with Image.open(path) as animation:
            if animation.format != expected_format or animation.n_frames != 4:
                raise RuntimeError(f"invalid packaged export: {path}")
    print(f"PACKAGED_SELF_TEST_OK {line_path} {wechat_path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        raise SystemExit(packaged_self_test(Path(sys.argv[2])))
    raise SystemExit(launch())
