"""Command-line and desktop entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.workers.pipeline import ProcessingOptions, process_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sticker-motion", description="Build LINE APNG or WeChat GIF animations from a sprite sheet.")
    parser.add_argument("source", nargs="?", type=Path, help="input sprite sheet")
    parser.add_argument("output", nargs="?", type=Path, help="output .png (LINE) or .gif (WeChat)")
    parser.add_argument("--platform", choices=("line", "wechat"), default="line")
    parser.add_argument("--frames", type=int, choices=(4, 6, 8), default=8)
    parser.add_argument("--layout", choices=("auto", "horizontal", "vertical", "grid"), default="auto")
    parser.add_argument("--duration", type=int, default=200, help="milliseconds per frame")
    parser.add_argument("--remove-background", action="store_true")
    parser.add_argument("--background-tolerance", type=int, default=0)
    parser.add_argument("--gui", action="store_true", help="launch desktop interface")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.gui:
        from app.ui.desktop import launch

        return launch()
    if args.source is None or args.output is None:
        build_parser().error("source and output are required unless --gui is used")
    options = ProcessingOptions(
        frame_count=args.frames,
        layout=args.layout,
        duration_ms=args.duration,
        transparent_background=args.remove_background,
        background_tolerance=args.background_tolerance,
    )
    output = process_file(args.source, args.output, args.platform, options)
    print(f"Exported {args.frames} frames to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
