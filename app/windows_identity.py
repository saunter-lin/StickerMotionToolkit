"""Stable Windows shell identity for taskbar grouping and pinned shortcuts."""

from __future__ import annotations

import sys

WINDOWS_APP_USER_MODEL_ID = "Saunter.StickerMotionToolkit"


def configure_windows_app_identity() -> bool:
    """Set the process AppUserModelID on Windows; remain inert elsewhere."""
    if sys.platform != "win32":
        return False
    import ctypes

    result = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        WINDOWS_APP_USER_MODEL_ID
    )
    if result != 0:
        raise OSError(result, "Unable to set Windows AppUserModelID")
    return True
