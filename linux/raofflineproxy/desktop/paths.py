from __future__ import annotations

import json
from pathlib import Path

from ..config import desktop_bundle_root

TEST_CHANNEL_FILE = "testing.json"


def bundle_root() -> Path:
    root = desktop_bundle_root()
    if root is None:
        raise RuntimeError("not running from the desktop RAOfflineProxy bundle")
    return root


def app_dir() -> Path:
    return bundle_root() / "app"


def test_channel() -> dict:
    """Redirects for test builds only, as on Windows: a testing.json that
    build_bundle.sh adds when RAOFFLINEPROXY_TEST_CHANNEL names one. Keys:
    "update_releases_url" (a releases list in GitHub's format) and
    "logs_folder" (Send Logs saves the zip there, a local folder or an smb://
    share, instead of uploading it). Empty in release builds."""
    root = desktop_bundle_root()
    if root is None:
        return {}
    try:
        data = json.loads((root / TEST_CHANNEL_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
