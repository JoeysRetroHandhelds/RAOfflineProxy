from __future__ import annotations

"""Gamepad input for the SDL menu through SDL itself, for Windows (which has
no /dev/input) and desktop Linux (where reading /dev/input takes permissions
an ordinary user doesn't have).

Same interface as menu_input's open/read/close, and the same evdev codes out,
so the menu's key handling is unchanged. Gamepads are read through SDL's
GameController API, which maps XInput pads (built-in handheld controllers,
Xbox pads) and most others to one standard layout. The keyboard needs nothing
here: the menu already handles it through pygame KEYDOWN events. State is
polled rather than taken from the event queue, because the menu's own event
loop drains that queue first."""

import time

from .menu_input import (
    BTN_DPAD_DOWN,
    BTN_DPAD_LEFT,
    BTN_DPAD_RIGHT,
    BTN_DPAD_UP,
    BTN_EAST,
    BTN_SELECT,
    BTN_SOUTH,
    BTN_START,
    BTN_TL,
    BTN_TR,
)

# Past this the left stick counts as a d-pad press (axis range is +-32767).
STICK_THRESHOLD = 20000
RESCAN_SECONDS = 2.0


class _Pads:
    """The handle list the menu holds. Rescans now and then, so a pad that is
    connected after the menu opens (or reconnects) still works."""

    def __init__(self) -> None:
        self.controllers: dict[int, object] = {}
        self.held: set[tuple[int, int]] = set()
        self.next_scan = 0.0

    def __bool__(self) -> bool:
        # Truthy even with no pad yet, so the menu keeps polling read_keys.
        return True

    def rescan(self) -> None:
        from pygame._sdl2 import controller

        if not controller.get_init():
            controller.init()
        for index in range(controller.get_count()):
            if index in self.controllers or not controller.is_controller(index):
                continue
            try:
                self.controllers[index] = controller.Controller(index)
            except Exception:
                continue
        for index, pad in list(self.controllers.items()):
            if not pad.attached():
                del self.controllers[index]
                self.held = {held for held in self.held if held[0] != index}
        self.next_scan = time.monotonic() + RESCAN_SECONDS


def open_input_devices() -> list[object]:
    pads = _Pads()
    try:
        pads.rescan()
    except Exception:
        pass
    return [pads]


def close_input_devices(handles: list[object]) -> None:
    for pads in handles:
        if isinstance(pads, _Pads):
            for pad in pads.controllers.values():
                try:
                    pad.quit()
                except Exception:
                    pass
            pads.controllers.clear()


def _pressed(pad, pygame) -> set[int]:
    pressed = {
        code
        for button, code in (
            (pygame.CONTROLLER_BUTTON_A, BTN_SOUTH),
            (pygame.CONTROLLER_BUTTON_B, BTN_EAST),
            (pygame.CONTROLLER_BUTTON_BACK, BTN_SELECT),
            (pygame.CONTROLLER_BUTTON_START, BTN_START),
            (pygame.CONTROLLER_BUTTON_LEFTSHOULDER, BTN_TL),
            (pygame.CONTROLLER_BUTTON_RIGHTSHOULDER, BTN_TR),
            (pygame.CONTROLLER_BUTTON_DPAD_UP, BTN_DPAD_UP),
            (pygame.CONTROLLER_BUTTON_DPAD_DOWN, BTN_DPAD_DOWN),
            (pygame.CONTROLLER_BUTTON_DPAD_LEFT, BTN_DPAD_LEFT),
            (pygame.CONTROLLER_BUTTON_DPAD_RIGHT, BTN_DPAD_RIGHT),
        )
        if pad.get_button(button)
    }
    x = pad.get_axis(pygame.CONTROLLER_AXIS_LEFTX)
    y = pad.get_axis(pygame.CONTROLLER_AXIS_LEFTY)
    if y < -STICK_THRESHOLD:
        pressed.add(BTN_DPAD_UP)
    elif y > STICK_THRESHOLD:
        pressed.add(BTN_DPAD_DOWN)
    if x < -STICK_THRESHOLD:
        pressed.add(BTN_DPAD_LEFT)
    elif x > STICK_THRESHOLD:
        pressed.add(BTN_DPAD_RIGHT)
    return pressed


def read_keys(handles: list[object], last_press: dict[int, float] | None = None) -> list[int]:
    """Codes that went down since the last call: one per press, like the evdev
    reader. last_press is accepted for the shared signature; polling sees each
    press once, so there is no chatter to debounce."""
    import pygame

    keys: list[int] = []
    # SDL keeps reporting pad state while the window is in the background, so
    # without this, playing a game with the menu open behind it would also
    # drive the menu (and could confirm a dialog). Keyboard input is focus-bound
    # already.
    focused = pygame.display.get_init() and pygame.key.get_focused()
    for pads in handles:
        if not isinstance(pads, _Pads):
            continue
        try:
            if time.monotonic() >= pads.next_scan:
                pads.rescan()
            now_held: set[tuple[int, int]] = set()
            for index, pad in pads.controllers.items():
                for code in _pressed(pad, pygame):
                    now_held.add((index, code))
                    if focused and (index, code) not in pads.held:
                        keys.append(code)
            # Tracked while unfocused too, so a button still held when the menu
            # regains focus isn't read as a fresh press.
            pads.held = now_held
        except pygame.error:
            continue
    return keys
