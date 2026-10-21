from __future__ import annotations

"""Which emulators are open. They keep their settings in memory and write them
back when they close, so patching or restoring a config under a running one
is undone the moment it exits."""

import shutil
import subprocess

FLATPAK_IDS = {
    "org.libretro.RetroArch": "RetroArch",
    "org.DolphinEmu.dolphin-emu": "Dolphin",
    "org.ppsspp.PPSSPP": "PPSSPP",
}
# Regular installs. Not "dolphin": that's KDE's file manager.
PROCESS_NAMES = {
    "retroarch": "RetroArch",
    "dolphin-emu": "Dolphin",
    "PPSSPPSDL": "PPSSPP",
    "PPSSPPQt": "PPSSPP",
}


def _output(command: list[str]) -> str:
    if shutil.which(command[0]) is None:
        return ""
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=10, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def running() -> list[str]:
    found = set()
    for line in _output(["flatpak", "ps", "--columns=application"]).split():
        if line in FLATPAK_IDS:
            found.add(FLATPAK_IDS[line])
    for name, emulator in PROCESS_NAMES.items():
        if _output(["pgrep", "-x", name]).strip():
            found.add(emulator)
    return sorted(found)
