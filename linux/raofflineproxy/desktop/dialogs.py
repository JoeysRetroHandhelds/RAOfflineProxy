from __future__ import annotations

"""Plain desktop dialogs for the Start/Stop/Send Logs scripts, until there is
a menu: KDE's kdialog, else GNOME's zenity, else the terminal."""

import shutil
import subprocess

TITLE = "RAOfflineProxy"


def show(text: str) -> None:
    if shutil.which("kdialog"):
        subprocess.run(["kdialog", "--title", TITLE, "--msgbox", text], check=False)
    elif shutil.which("zenity"):
        subprocess.run(["zenity", "--info", "--title", TITLE, "--no-wrap", "--text", text], check=False)
    elif shutil.which("notify-send"):
        subprocess.run(["notify-send", TITLE, text], check=False)
    else:
        print(text)


def ask(text: str) -> bool:
    """False when no dialog tool is available: nothing is done unasked."""
    if shutil.which("kdialog"):
        return subprocess.run(["kdialog", "--title", TITLE, "--yesno", text], check=False).returncode == 0
    if shutil.which("zenity"):
        return subprocess.run(["zenity", "--question", "--title", TITLE, "--text", text], check=False).returncode == 0
    print(text + " (no dialog tool found, so skipped)")
    return False
