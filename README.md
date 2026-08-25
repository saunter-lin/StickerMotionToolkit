# Sticker Motion Toolkit

Sticker Motion Toolkit is a standalone desktop tool for turning ordered PNG frames into animated stickers. It exports LINE animations as APNG and WeChat animations as GIF, and runs independently from [Sticker Toolkit](https://github.com/saunter-lin/StickerToolkit).

Current release: **v1.3.3**

Current source version: **v1.4.0**, adding optional per-frame duration overrides while retaining each group’s default duration.

## Download

Download the latest builds from the [v1.3.3 GitHub Release](https://github.com/saunter-lin/StickerMotionToolkit/releases/tag/v1.3.3).

| Platform | Release file | Requirements |
| --- | --- | --- |
| macOS | `StickerMotionToolkit-v1.3.3-macOS-arm64.dmg` | Apple Silicon (arm64) |
| Windows | `StickerMotionToolkit-v1.3.3-Windows-x64.zip` | Windows 10/11 x64 |

The packaged applications are self-contained. End users do not need Python, PySide6, Pillow, or PyInstaller.

Both builds are currently unsigned. macOS Gatekeeper or Windows SmartScreen may therefore display a warning. Only download release files from this repository and verify the source before opening them.

## What it does

```text
ordered PNG frames
        ↓
background layers → animation frames → text overlay
        ↓
LINE APNG or WeChat GIF
```

- Creates multiple independent animations with an Animation Job Queue.
- Accepts **2–15 PNG frames** per animation group.
- Uses natural filename sorting for the initial playback order.
- Supports adding, removing, duplicating, clearing, and reordering jobs.
- Supports adding, removing, clearing, and moving individual frames up or down.
- Uses the visible frame-list order as the exact preview and export order.
- Exports mixed LINE and WeChat jobs sequentially with **Export All**.
- Never overwrites an existing output; numeric suffixes such as `name-2` are added automatically.
- Provides a resizable, vertically scrollable PySide6 interface.
- Supports live switching between Traditional Chinese, Simplified Chinese, and English, with the selected language remembered locally.

## Export formats and timing

### WeChat GIF

- WeChat GIF is the default format for a newly created group.
- New groups default to **220 ms per frame**.
- Frame duration remains configurable per group.
- In v1.4 development, each frame may optionally override the group default; resetting an override restores live inheritance from the group value.
- GIF export uses palette transparency; partial alpha cannot be preserved.

### LINE APNG

- LINE Playback Time can be set to **1, 2, 3, or 4 seconds**.
- Frame delays are distributed precisely, including when the selected playback time is not evenly divisible by the frame count.
- Per-frame overrides preserve relative rhythm while LINE timing remains normalized to the selected 1–4 second playback time.
- Exported APNG timing and play-count metadata are read back and validated after encoding.
- Finite play metadata keeps total LINE animation playback within four seconds.
- APNG preserves full RGBA transparency.

The LINE timing options do not change the group’s stored per-frame duration or WeChat GIF behavior.

## Background layers

Each animation group can contain still background images with independent inclusive start and end frames.

- Multiple backgrounds may overlap; list order defines bottom-to-top precedence.
- Backgrounds use aspect-preserving **Scale to Cover** with center crop.
- Frames outside all background ranges retain their original transparency.
- Background ranges are validated against the group’s actual frame count.
- The final layer order is **Background → Animation Frame → Text Overlay**.

Sticker Motion Toolkit does not cut background sprite sheets. Prepare or split those images in Sticker Toolkit before adding them here.

## Text overlay and fonts

Text Overlay is rendered through the same composition path for preview and final APNG/GIF export.

Available controls include:

- text content, font, size, fill color, outline color, and outline width;
- top, center, or bottom vertical placement;
- left, center, or right horizontal alignment;
- X/Y offsets;
- horizontal text or simple top-to-bottom character stacking;
- rotation from -180° to +180°.

Three redistributable fonts are bundled and always appear first in the font menu:

1. 芫荽 (Iansui, default)
2. 粉圓體 (jf open Huninn)
3. 辰宇落雁體 (ChenYuluoyan)
4. system fonts
5. **Choose Local Font…**

Bundled fonts are loaded from application resources and are not installed into the operating system. Preview and export share the same font-resolution and fallback logic. Official font sources and licenses are documented in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

## Desktop workflow

1. Create or select an animation group.
2. Choose WeChat GIF or LINE APNG.
3. Add 2–15 individual PNG frames.
4. Review and adjust their playback order.
5. Configure duration or LINE Playback Time.
6. Optionally add background layers and text.
7. Use Preview to inspect the fully composited animation.
8. Choose an output folder and select **Export All**.

Plan the final composition before creating the character frames. If backgrounds or text will be added, leave enough visible space around the character; roughly 75% character occupancy is a useful starting point, not a hard requirement.

## Run from source

Python 3.10 or newer is recommended.

```bash
git clone https://github.com/saunter-lin/StickerMotionToolkit.git
cd StickerMotionToolkit
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m app.main --gui
```

On Windows, activate the environment with `.venv\Scripts\activate` before running the final command.

## CLI

The source CLI creates one animation from an evenly divided horizontal, vertical, or grid sprite sheet. It is preserved alongside the GUI workflow.

```bash
# LINE APNG, eight frames, automatic layout, 200 ms/frame
python -m app.main sheet.png output/line.png --platform line --frames 8

# WeChat GIF, six-frame grid, custom duration
python -m app.main sheet.png output/wechat.gif \
  --platform wechat --frames 6 --layout grid --duration 120

# Remove a uniform background sampled from each frame's top-left corner
python -m app.main sheet.png output/line.png \
  --platform line --frames 4 --remove-background --background-tolerance 10
```

The CLI default remains **200 ms per frame**. Auto layout supports horizontal, vertical, and conventional grid arrangements. Common grids are 2×2 for four frames, 3×2 for six, and 4×2 for eight, read left-to-right and top-to-bottom.

The optional solid-color background removal remains available through the CLI and processing API for compatibility. It is intentionally not exposed in the desktop GUI.

## Tests

Install the development dependencies and run the complete suite:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

The v1.3.3 release source passes **124 automated tests** on both macOS and Windows release environments.

## Build from source

### macOS Apple Silicon

Run on an arm64 Mac:

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
./build_macos.sh
```

The script runs the tests, performs a clean PyInstaller build, and creates:

- `dist/Sticker Motion Toolkit.app`
- `dist/Sticker-Motion-Toolkit-v1.3.3-macOS-arm64.dmg`

The frozen executable also provides an internal release smoke test:

```bash
"dist/Sticker Motion Toolkit.app/Contents/MacOS/Sticker Motion Toolkit" \
  --self-test /tmp/sticker-motion-smoke
```

### Windows 10/11 x64

Build natively on Windows x64:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\pyinstaller.exe --clean --noconfirm StickerMotionToolkit-Windows.spec
```

The Windows release is a PyInstaller onedir application. Fully extract the ZIP, keep the executable and `_internal` directory together, then launch `Sticker Motion Toolkit.exe`.

## Architecture

- `app/main.py`: source CLI and GUI launcher.
- `app/gui_main.py`: GUI-first entry point used by packaged builds and frozen self-tests.
- `app/ui/desktop.py`: PySide6 desktop interface.
- `app/workers/pipeline.py`: orchestration boundary shared by the CLI and GUI.
- `sticker_motion/splitter.py`: frame-count validation, layout detection, and sprite-sheet slicing.
- `sticker_motion/background.py`: deterministic color-to-alpha processing.
- `sticker_motion/background_layer.py`: background ranges, cover/crop, and compositing.
- `sticker_motion/animation.py`: platform-neutral frame normalization and timing model.
- `sticker_motion/jobs.py`: animation group and queue models.
- `sticker_motion/text_overlay.py`: shared preview/export text rendering.
- `sticker_motion/fonts.py`: bundled, system, and local font resolution.
- `sticker_motion/line_validation.py`: LINE timing calculation, APNG metadata read-back, and validation.
- `sticker_motion/export.py`: platform-specific APNG/GIF encoding boundary.

Sticker Motion Toolkit does not import from or depend on the Sticker Toolkit project at runtime.

## Current limitations

- The GUI accepts individual PNG frames; the CLI accepts one evenly divided sprite sheet. Irregular atlases are not supported.
- Background removal is color-threshold based, not semantic segmentation.
- Background Layer currently uses still images; video or animated-background editing is not included.
- Text is static per group and composited onto every frame; animated text effects are not included.
- Vertical text uses simple character stacking rather than full East Asian vertical punctuation and layout rules.
- Output validity does not guarantee acceptance if LINE or WeChat changes its submission rules.
- Official packaged builds target macOS Apple Silicon arm64 and Windows 10/11 x64. Other platforms are not currently verified.

## License notices

See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) for bundled-font licenses and official sources.
