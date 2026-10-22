from __future__ import annotations

"""The SDL menu's window on desktop Linux: full screen, as on the handhelds
(Steam's Game Mode shows one app at a time anyway), with the app's name and
logo. menu_fullscreen = "window" in config.json opens a window instead."""

import fcntl
from pathlib import Path

from ..config import CONFIG_DIR

WINDOW_SIZE = (1280, 800)
_menu_lock = None


def show_existing_menu() -> bool:
    """One menu at a time, as on Windows: two would both act on the same
    controller press. True when one is already open; this one should exit."""
    global _menu_lock
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _menu_lock = open(CONFIG_DIR / "menu.lock", "w")
    try:
        fcntl.flock(_menu_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return True
    return False


def open_menu_window(pygame, config_data: dict):
    pygame.display.set_caption("RAOfflineProxy")
    logo = Path(__file__).resolve().parent.parent / "logo-320.png"
    if logo.exists():
        try:
            pygame.display.set_icon(pygame.transform.smoothscale(pygame.image.load(str(logo)), (64, 64)))
        except pygame.error:
            pass
    if config_data.get("menu_fullscreen") == "window":
        return pygame.display.set_mode(WINDOW_SIZE)
    return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
