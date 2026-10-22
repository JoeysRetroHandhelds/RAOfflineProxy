from __future__ import annotations

"""The Windows-only parts of the SDL menu's window: one menu at a time, and
where the window goes. Gamepad input is shared with desktop Linux, in
sdl_input; it's re-exported here for the names the menu already uses."""

from pathlib import Path

from ..sdl_input import close_input_devices, open_input_devices, read_keys  # noqa: F401


MENU_MUTEX_NAME = "Local\\RAOfflineProxyMenu"
_menu_mutex = None


def show_existing_menu() -> bool:
    """One menu at a time: with a menu already open, brings it to the front
    and returns True, and this process should exit. Two menus would both act
    on the same controller press (e.g. installing an update twice)."""
    import ctypes

    global _menu_mutex
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    _menu_mutex = kernel32.CreateMutexW(None, False, MENU_MUTEX_NAME)
    if ctypes.get_last_error() != 183:  # ERROR_ALREADY_EXISTS
        return False
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.FindWindowW.restype = ctypes.c_void_p
    # SDL's window class; the title is set in open_menu_window.
    hwnd = user32.FindWindowW("SDL_app", "RAOfflineProxy")
    if hwnd:
        user32.ShowWindow(ctypes.c_void_p(hwnd), 9)  # SW_RESTORE
        user32.SetForegroundWindow(ctypes.c_void_p(hwnd))
    return True


def open_menu_window(pygame, config_data: dict):
    """Borderless window covering the primary monitor by default: no display mode
    switch, instant Alt-Tab, and always on the primary screen with several
    monitors. menu_fullscreen = "exclusive" in config.json restores the
    exclusive full screen the Linux devices use."""
    import ctypes
    import os

    try:
        # Per-monitor DPI aware, so the window covers the real pixels instead of
        # being stretched by Windows display scaling (common on handhelds).
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        pass
    pygame.display.set_caption("RAOfflineProxy")
    # Our own taskbar identity, so the window isn't grouped under Python, and
    # the logo as its icon instead of pygame's.
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RAOfflineProxy.Menu")
    except (AttributeError, OSError):
        pass
    logo = Path(__file__).resolve().parent.parent / "logo-320.png"
    if logo.exists():
        try:
            pygame.display.set_icon(pygame.transform.smoothscale(pygame.image.load(str(logo)), (64, 64)))
        except pygame.error:
            pass

    if config_data.get("menu_fullscreen") == "exclusive":
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

    # The primary monitor's work area: the screen minus the taskbar, which
    # otherwise stays on top of a borderless window and hides its bottom edge
    # (where the menu's messages are).
    from ctypes import wintypes

    area = wintypes.RECT()
    user32 = ctypes.windll.user32
    if user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(area), 0):  # SPI_GETWORKAREA
        left, top, size = area.left, area.top, (area.right - area.left, area.bottom - area.top)
    else:
        left, top, size = 0, 0, (user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))
    os.environ["SDL_VIDEO_WINDOW_POS"] = f"{left},{top}"
    return pygame.display.set_mode(size, pygame.NOFRAME)
