from __future__ import annotations

"""What the desktop bundle's scripts run:

  python3 -m raofflineproxy.desktop.launch start      update if asked, then start the proxy
  python3 -m raofflineproxy.desktop.launch stop       stop it and restore the emulator configs
  python3 -m raofflineproxy.desktop.launch send-logs  Send Logs (to the test share in test builds)
"""

import os
import subprocess
import sys

from ..config import APP_VERSION
from . import dialogs, logs, update
from .paths import app_dir, bundle_root

START_SCRIPT = "Start RAOfflineProxy.sh"


def run_main(command: str) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "-m", "raofflineproxy.main", command],
        cwd=app_dir(), capture_output=True, text=True, check=False,
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def offer_update() -> bool:
    """True when an update was installed (the caller restarts)."""
    available = update.check()
    if available is None:
        return False
    if not dialogs.ask(f"RAOfflineProxy {available.version} is available (you have {APP_VERSION}).\n\nUpdate now?"):
        return False
    try:
        archive = update.download(available)
        run_main("stop-proxy")
        update.install(archive)
    except Exception as exc:  # the old version is still in place; carry on with it
        dialogs.show(f"The update failed: {exc}\n\nStarting the current version.")
        return False
    return True


def start() -> int:
    if offer_update():
        # The new version's own Start script, so its code runs from here on.
        os.execv("/bin/bash", ["bash", str(bundle_root() / START_SCRIPT)])
    ok, output = run_main("start-proxy")
    dialogs.show(("Proxy started." if ok else "Starting the proxy failed.") + f"\n\n{output}")
    return 0 if ok else 1


def stop() -> int:
    ok, output = run_main("stop-proxy")
    dialogs.show(("Proxy stopped." if ok else "Stopping the proxy failed.") + f"\n\n{output}")
    return 0 if ok else 1


def send_logs() -> int:
    try:
        dialogs.show(logs.send_logs())
        return 0
    except Exception as exc:
        dialogs.show(f"Send Logs failed: {exc}")
        return 1


def main(argv: list[str]) -> int:
    commands = {"start": start, "stop": stop, "send-logs": send_logs}
    if len(argv) != 2 or argv[1] not in commands:
        print(__doc__)
        return 2
    return commands[argv[1]]()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
