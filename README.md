# Sticker Motion Toolkit

Sticker Motion Toolkit is a standalone animated-sticker creation tool and a companion to Sticker Toolkit. It shares no code or runtime dependency with Sticker Toolkit.

The primary V1 workflow is:

```text
prepared individual PNG frames
→ Sticker Motion Toolkit
→ animated sticker
```

The processing pipeline supports 4, 6, or 8 frames and branches only at export:

- LINE: animated PNG (APNG)
- WeChat: animated GIF

## Version overview

### v1.0

- Single-animation workflow using one ordered frame list
- Official macOS Apple Silicon arm64 and Windows 10/11 x64 builds

### v1.1

- Animation Job Queue for preparing multiple independent animations
- Per-job frames, platform, duration, filename, status, and text settings
- Add, remove, duplicate, clear, and reorder jobs
- Sequential Export All with progress; mixed LINE APNG and WeChat GIF queues are supported
- Existing files are never overwritten: `name-2`, `name-3`, and later numeric suffixes are used
- Optional static text overlay composited onto every frame
- Host font selection, size, fill/stroke colors, stroke width, top/center/bottom, left/center/right, and X/Y offsets
- Representative first-frame text preview
- Dedicated Berry Motion application icon

## Shared features

- Individual PNG frame input in the GUI
- 4, 6, or 8-frame animations
- Natural filename sorting and manual playback-order management
- Move Up, Move Down, Remove selected, and Clear all controls
- Default 200 ms duration per frame, configurable in the GUI and CLI
- Optional solid-background removal remains available through the source CLI and processing API for compatibility; it is not shown in the v1.1 GUI
- LINE APNG and WeChat GIF export
- Traditional Chinese, Simplified Chinese, and English GUI
- Persisted language preference and live language switching
- Resizable, vertically scrollable desktop interface
- Standalone macOS Apple Silicon arm64 and Windows 10/11 x64 builds

## Setup

Python 3.10 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## GUI usage

```bash
python -m app.main --gui
```

Select 4, 6, or 8 individual PNG frames. Files initially use natural filename order (for example, `frame2.png` precedes `frame10.png`) and can then be moved, removed, or cleared. The visible list is the exact APNG/GIF playback order.

The desktop window is freely resizable. Its content expands horizontally and scrolls vertically when height is limited, keeping every control accessible across all three languages. The selected language is remembered through Qt platform settings.

## CLI

The source CLI remains supported for evenly divided horizontal, vertical, or grid sprite sheets. Auto layout compares sheet proportions with expected cell arrangements: 2×2 for four frames, 3×2 for six, and 4×2 for eight.

Horizontal, vertical, and grid sprite sheets are supported. Auto layout compares the sheet proportions with the expected cell arrangements. Grid arrangements are 2x2 for four frames, 3x2 for six, and 4x2 for eight, read left-to-right and top-to-bottom.

```bash
# LINE APNG, eight frames, automatic layout, 200 ms/frame
python -m app.main sheet.png output/line.png --platform line --frames 8

# WeChat GIF with six frames and a custom duration
python -m app.main sheet.png output/wechat.gif \
  --platform wechat --frames 6 --layout grid --duration 120

# Remove a uniform background sampled from each frame's top-left corner
python -m app.main sheet.png output/line.png \
  --platform line --frames 4 --remove-background --background-tolerance 10

```

Run tests with:

```bash
python -m pytest
```

## macOS Apple Silicon build

The v1.1 source can be built as a self-contained unsigned arm64 application and DMG on an Apple Silicon Mac:

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
./build_macos.sh
```

Outputs are written to `dist/Sticker Motion Toolkit.app` and `dist/Sticker-Motion-Toolkit-v1.1.0-macOS-arm64.dmg`. The packaged application opens directly into the GUI; users do not need Python or any Python packages.

The development build is not code-signed or notarized. macOS Gatekeeper may therefore block the first launch. A user who trusts the file can Control-click the app, choose **Open**, and confirm **Open**. Signing and notarization should be added before public distribution.

For release verification, the frozen executable supports an internal export diagnostic:

```bash
"dist/Sticker Motion Toolkit.app/Contents/MacOS/Sticker Motion Toolkit" --self-test /tmp/sticker-motion-smoke
```

## Windows 10/11 x64

Download `StickerMotionToolkit-v1.1.0-Windows-x64.zip` from the official [saunter-lin/StickerMotionToolkit v1.1.0 release](https://github.com/saunter-lin/StickerMotionToolkit/releases/tag/v1.1.0).

1. Fully extract the ZIP before launching. Do not run the executable from inside the ZIP.
2. Keep the complete extracted folder together; this is an onedir distribution and the `_internal` folder is required.
3. Launch `Sticker Motion Toolkit.exe`.

Python and Python packages are not required. This v1.1 Windows build is unsigned, so Windows SmartScreen may display a warning. Verify that the ZIP came from the official GitHub release before opening it.

The native Windows build uses `StickerMotionToolkit-Windows.spec`. Build it on Windows x64 with:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\pyinstaller.exe --clean --noconfirm StickerMotionToolkit-Windows.spec
```

## Architecture

`app/main.py` provides the source CLI, `app/gui_main.py` is the packaged GUI-first entry point, and `app/workers/pipeline.py` is the application orchestration boundary shared by both interfaces.

The `sticker_motion` package is deliberately modular:

- `splitter.py`: validates frame counts, detects layouts, and slices sheets.
- `background.py`: optional deterministic color-to-alpha cleanup.
- `animation.py`: platform-neutral frame normalization and timing model.
- `preview.py`: reusable static contact sheet; an interactive animation preview can build on the same `Animation` model.
- `export.py`: the only platform branch, encoding LINE APNG or WeChat GIF.

Image objects are copied into this project-owned model. There is no import from or runtime dependency on Sticker Toolkit.

## Current limitations

- The CLI accepts one evenly divided sprite sheet; the GUI accepts 4, 6, or 8 individual PNG frames. Irregular atlases are not supported.
- Background removal is color-threshold based, not semantic segmentation.
- The preview is a representative static frame, not an animated preview.
- Text is static per job and composited consistently onto all frames; animated text effects are not implemented.
- Background composition, frame-range grouping, and platform-specific validation/compression remain future extension points.
- GIF uses palette transparency and therefore cannot preserve partial alpha. APNG preserves full RGBA.
- Output files are correctly encoded, but submission acceptance still depends on current platform upload rules; the toolkit does not yet enforce those rules.
- Official V1 packaged builds target macOS Apple Silicon arm64 and Windows 10/11 x64. Other platforms have not been built or verified.
