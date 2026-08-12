"""Generate application icon resources from the approved master artwork."""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "assets" / "icon" / "berry-motion-master.png"
ICON_DIR = MASTER.parent


def main() -> None:
    source = Image.open(MASTER).convert("RGBA")
    source.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    canvas.alpha_composite(source, ((1024 - source.width) // 2, (1024 - source.height) // 2))
    iconset = ICON_DIR / "StickerMotionToolkit.iconset"
    iconset.mkdir(exist_ok=True)
    for points, scale in ((16, 1), (16, 2), (32, 1), (32, 2), (128, 1), (128, 2), (256, 1), (256, 2), (512, 1), (512, 2)):
        pixels = points * scale
        name = f"icon_{points}x{points}{'@2x' if scale == 2 else ''}.png"
        canvas.resize((pixels, pixels), Image.Resampling.LANCZOS).save(iconset / name)
    canvas.resize((256, 256), Image.Resampling.LANCZOS).save(ICON_DIR / "sticker-motion-toolkit-256.png")
    canvas.save(ICON_DIR / "sticker-motion-toolkit.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(ICON_DIR / "sticker-motion-toolkit.icns")], check=True)


if __name__ == "__main__":
    main()
