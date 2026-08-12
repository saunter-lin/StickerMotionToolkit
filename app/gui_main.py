"""GUI entry point used by the packaged macOS application."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import QApplication

from app.ui.desktop import launch
from app.workers.pipeline import process_frame_files
from sticker_motion.batch import export_jobs
from sticker_motion.jobs import AnimationJob, TextOverlaySettings


def packaged_self_test(output_dir: Path) -> int:
    """Exercise frozen PNG/APNG/GIF support without affecting normal launch."""
    app = QApplication.instance() or QApplication([])
    output_dir.mkdir(parents=True, exist_ok=True)
    frame_paths = []
    for index, color in enumerate(("red", "green", "blue", "yellow"), 1):
        path = output_dir / f"frame{index}.png"
        Image.new("RGBA", (32, 32), color).save(path)
        frame_paths.append(path)
    jobs = [
        AnimationJob("line-text", frame_paths, platform="line", output_filename="line", text_overlay=TextOverlaySettings(enabled=True, text="測試 Test", font_size=16)),
        AnimationJob("wechat-plain", frame_paths, platform="wechat", output_filename="wechat"),
    ]
    line_path, wechat_path = export_jobs(jobs, output_dir)
    for path, expected_format in ((line_path, "PNG"), (wechat_path, "GIF")):
        with Image.open(path) as animation:
            if animation.format != expected_format or animation.n_frames != 4:
                raise RuntimeError(f"invalid packaged export: {path}")
    print(f"PACKAGED_SELF_TEST_OK {line_path} {wechat_path}")
    app.quit()
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        raise SystemExit(packaged_self_test(Path(sys.argv[2])))
    raise SystemExit(launch())
