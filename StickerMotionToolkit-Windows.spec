# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

pillow_hiddenimports = collect_submodules("PIL")

analysis = Analysis(
    ["app/gui_main.py"],
    pathex=["."],
    binaries=[],
    datas=[("assets/icon/sticker-motion-toolkit-256.png", "assets/icon")],
    hiddenimports=pillow_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Sticker Motion Toolkit",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/icon/sticker-motion-toolkit.ico",
)

collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="Sticker Motion Toolkit",
)
