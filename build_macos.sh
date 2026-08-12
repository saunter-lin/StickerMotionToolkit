#!/bin/zsh
set -euo pipefail

project_dir=${0:A:h}
cd "$project_dir"

if [[ "$(uname -m)" != "arm64" ]]; then
  print -u2 "This build script must run on macOS Apple Silicon (arm64)."
  exit 1
fi

python_bin="$project_dir/.venv/bin/python"
pyinstaller_bin="$project_dir/.venv/bin/pyinstaller"
if [[ ! -x "$pyinstaller_bin" ]]; then
  print -u2 "Install build dependencies first: .venv/bin/python -m pip install -r requirements-dev.txt"
  exit 1
fi

QT_QPA_PLATFORM=offscreen "$python_bin" -m pytest -q
rm -rf "$project_dir/build" "$project_dir/dist"
mkdir -p "$project_dir/build/pyinstaller-cache"
PYINSTALLER_CONFIG_DIR="$project_dir/build/pyinstaller-cache" \
  "$pyinstaller_bin" --clean --noconfirm "$project_dir/StickerMotionToolkit.spec"

app_path="$project_dir/dist/Sticker Motion Toolkit.app"
dmg_root="$project_dir/build/dmg-root"
dmg_path="$project_dir/dist/Sticker-Motion-Toolkit-v1.2.0-macOS-arm64.dmg"
mkdir -p "$dmg_root"
ditto "$app_path" "$dmg_root/Sticker Motion Toolkit.app"
ln -s /Applications "$dmg_root/Applications"
hdiutil create -volname "Sticker Motion Toolkit v1.2.0" -srcfolder "$dmg_root" -ov -format UDZO "$dmg_path"

print "Built: $app_path"
print "Built: $dmg_path"
