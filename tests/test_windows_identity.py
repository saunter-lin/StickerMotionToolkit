from __future__ import annotations

import sys

from app.windows_identity import WINDOWS_APP_USER_MODEL_ID, configure_windows_app_identity


def test_windows_app_user_model_id_is_stable() -> None:
    assert WINDOWS_APP_USER_MODEL_ID == "Saunter.StickerMotionToolkit"


def test_windows_identity_is_not_invoked_on_macos() -> None:
    if sys.platform == "win32":
        return
    assert configure_windows_app_identity() is False
