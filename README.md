# Sticker Motion Toolkit

Sticker Motion Toolkit is a standalone animated-sticker creation tool and a companion to Sticker Toolkit. It shares no code or runtime dependency with Sticker Toolkit.

The primary V1 workflow is:

```text
prepared individual PNG frames
→ Sticker Motion Toolkit
→ animated sticker
```

The processing pipeline supports animations with 2–15 frames and branches only at export:

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
- Bundled Iansui, jf open Huninn, and ChenYuluoyan fonts, with local-font selection still available

### v1.2 development

- Every per-job setting has a visible translated label in a compact two-column form
- Text Overlay supports horizontal text and simple top-to-bottom character stacking
- Arbitrary text rotation from -180° to +180° is applied after layout and outline rendering
- Preview and final APNG/GIF export share the same text-rendering implementation
- Windows application identity uses the stable AppUserModelID `Saunter.StickerMotionToolkit`

### v1.3 development

- Group-based Background Layer entries with independent start/end frame ranges
- Multiple still backgrounds can overlap; list order defines bottom-to-top precedence
- Backgrounds use aspect-preserving Scale to Cover with center crop
- Final layer order is Background → Animation Frame → Text Overlay
- Animation frames use a wrapping multi-column display without changing playback order
- Preview animates the fully composited group at its configured frame duration
- New groups default to 220 ms per frame; existing explicit durations such as 200 ms remain unchanged

## Shared features

- Individual PNG frame input in the GUI
- Animations with 2–15 frames
- Natural filename sorting and manual playback-order management
- Move Up, Move Down, Remove selected, and Clear all controls
- New GUI groups default to 220 ms per frame; duration remains configurable and the CLI default remains 200 ms
- WeChat GIF is the default for new jobs; LINE APNG remains available from the same output-format menu
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

Select 2–15 individual PNG frames. Files initially use natural filename order (for example, `frame2.png` precedes `frame10.png`) and can then be moved, removed, or cleared. The visible list is the exact APNG/GIF playback order.

The desktop window is freely resizable. Its content expands horizontally and scrolls vertically when height is limited, keeping every control accessible across all three languages. The selected language is remembered through Qt platform settings.

The job editor clearly labels interface language, job name, output format, frame duration, output filename, all text settings, positioning, and offsets. Text may be horizontal or stacked vertically, then rotated by any whole-number angle from -180° to +180°. Positive X moves right, negative X moves left, positive Y moves down, and negative Y moves up. The animated preview uses the same frame-composition path as final export.

Backgrounds belong to one animation group. Add already prepared still images below the Animation Frames section, then set each entry's inclusive start and end frame. Frames outside every background range retain their original transparency. Background count cannot exceed the group's animation-frame count. The toolkit deliberately does not include a background grid cutter; prepare or split background sheets in Sticker Toolkit first.

Plan the complete composition before generating character frames. If a background or text will be added, leave suitable visible space around the character—roughly 75% character occupancy is a useful starting point rather than a hard rule. Sky, fireworks, ground effects, scene objects, and text each need intentional room.

The font menu always starts with 芫荽, 粉圓體, and 辰宇落雁體, followed by detected system fonts and **Choose Local Font…**. 芫荽 is the default. Bundled fonts are application resources and are not installed into macOS or Windows. Missing glyphs use the bundled/system fallback chain shared by preview and export. See `THIRD_PARTY_LICENSES.md` for official sources and licenses.

Vertical text uses simple character-by-character stacking. Advanced East Asian vertical typography, including punctuation rotation and repositioning, is not implemented.

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

The v1.3 source can be built as a self-contained unsigned arm64 application and DMG on an Apple Silicon Mac:

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
./build_macos.sh
```

Outputs are written to `dist/Sticker Motion Toolkit.app` and `dist/Sticker-Motion-Toolkit-v1.3.3-macOS-arm64.dmg`. The packaged application opens directly into the GUI; users do not need Python or any Python packages.

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

Windows pinned-taskbar icon handling has been updated through a stable process AppUserModelID plus consistent application, window, PNG, and executable icons. Native Windows verification is still required before the v1.2 release.

## Architecture

`app/main.py` provides the source CLI, `app/gui_main.py` is the packaged GUI-first entry point, and `app/workers/pipeline.py` is the application orchestration boundary shared by both interfaces.

The `sticker_motion` package is deliberately modular:

- `splitter.py`: validates frame counts, detects layouts, and slices sheets.
- `background.py`: optional deterministic color-to-alpha cleanup.
- `background_layer.py`: group-based frame-range selection, cover/crop, and background compositing.
- `animation.py`: platform-neutral frame normalization and timing model.
- `preview.py`: reusable static contact sheet; the GUI preview animates fully prepared frames using the group duration.
- `export.py`: the only platform branch, encoding LINE APNG or WeChat GIF.

Image objects are copied into this project-owned model. There is no import from or runtime dependency on Sticker Toolkit.

## Current limitations

- The CLI accepts one evenly divided sprite sheet; the GUI accepts 2–15 individual PNG frames. Irregular atlases are not supported.
- Background removal is color-threshold based, not semantic segmentation.
- Text is static per job and composited consistently onto all frames; animated text effects are not implemented.
- Vertical text uses simple character stacking; advanced East Asian vertical punctuation and layout are not implemented.
- Video backgrounds, background animation editing, and platform-specific validation/compression remain future extension points.
- GIF uses palette transparency and therefore cannot preserve partial alpha. APNG preserves full RGBA.
- Output files are correctly encoded, but submission acceptance still depends on current platform upload rules; the toolkit does not yet enforce those rules.
- Official V1 packaged builds target macOS Apple Silicon arm64 and Windows 10/11 x64. Other platforms have not been built or verified.
