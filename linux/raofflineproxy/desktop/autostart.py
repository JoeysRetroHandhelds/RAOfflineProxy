from __future__ import annotations

"""The sign-in service: a systemd user unit that runs at every sign-in, in
Desktop and Game Mode, without admin rights. It always runs, so a crash or
reboot never leaves the emulators pointed at a proxy that isn't running:

- "Start automatically" on, or the proxy was running when the session ended:
  start it (and point the emulators at it again);
- otherwise: put back any emulator config still pointing at the proxy.

The setting is the shared autostart key in config.json, the one the Linux
handhelds' boot-reconcile reads. The unit holds the bundle's path, so every
Start rewrites it, which keeps it right after the folder moves."""

import os
import shutil
import sys
import subprocess
from pathlib import Path

from ..config import CONFIG_DIR, load_config, save_config
from ..platform import AUTOSTART_CONFIG_KEY
from .paths import app_dir

UNIT_NAME = "raofflineproxy.service"
# Set when the proxy service starts and cleared when it's stopped (service.py),
# from any script or the menu: the sign-in service starts it again after a crash,
# a power loss or a logout, even with "Start automatically" off.
WANTED_FILE = CONFIG_DIR / "desktop_proxy_wanted"

UNIT = """[Unit]
Description=RAOfflineProxy: start it at sign-in, or restore the emulator configs

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory={app}
ExecStart={python} -m raofflineproxy.desktop.launch sign-in

[Install]
WantedBy=default.target
"""


def unit_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "systemd" / "user" / UNIT_NAME


def _systemctl(*args: str) -> bool:
    if shutil.which("systemctl") is None:
        return False
    return subprocess.run(["systemctl", "--user", *args], capture_output=True, check=False).returncode == 0


def install() -> bool:
    """Writes and enables the unit. False when there's no systemd user session."""
    path = unit_path()
    # The bundle's own Python (this one), not whatever the distro ships.
    content = UNIT.format(app=app_dir(), python=sys.executable)
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        _systemctl("daemon-reload")
    return _systemctl("enable", UNIT_NAME)


def setting_chosen() -> bool:
    return AUTOSTART_CONFIG_KEY in load_config()


def start_automatically() -> bool:
    return bool(load_config().get(AUTOSTART_CONFIG_KEY))


def set_start_automatically(enabled: bool) -> None:
    config_data = load_config()
    config_data[AUTOSTART_CONFIG_KEY] = enabled
    save_config(config_data)


def mark_wanted(wanted: bool) -> None:
    if wanted:
        WANTED_FILE.parent.mkdir(parents=True, exist_ok=True)
        WANTED_FILE.touch()
    else:
        WANTED_FILE.unlink(missing_ok=True)


def should_start_at_sign_in() -> bool:
    return start_automatically() or WANTED_FILE.exists()
