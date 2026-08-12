# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

pillow_hiddenimports = collect_submodules("PIL")

analysis = Analysis(
    ["app/gui_main.py"],
    pathex=["."],
    binaries=[],
    datas=[],
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
    argv_emulation=False,
    target_arch="arm64",
)

collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="Sticker Motion Toolkit",
)

app = BUNDLE(
    collection,
    name="Sticker Motion Toolkit.app",
    icon=None,
    bundle_identifier="com.saunter.stickermotiontoolkit",
    version="1.0.0",
    info_plist={
        "CFBundleDisplayName": "Sticker Motion Toolkit",
        "CFBundleName": "Sticker Motion Toolkit",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1",
        "LSMinimumSystemVersion": "13.0",
        "NSHighResolutionCapable": True,
    },
)
