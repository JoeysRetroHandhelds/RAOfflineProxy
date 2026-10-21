from __future__ import annotations

"""What the desktop bundle's scripts and sign-in service run:

  python3 -m raofflineproxy.desktop.launch start      update if asked, then start the proxy
  python3 -m raofflineproxy.desktop.launch stop       stop it and restore the emulator configs
  python3 -m raofflineproxy.desktop.launch send-logs  Send Logs (to the test share in test builds)
  python3 -m raofflineproxy.desktop.launch autostart  turn "Start automatically" on or off
  python3 -m raofflineproxy.desktop.launch sign-in    the sign-in service (no dialogs)
  python3 -m raofflineproxy.desktop.launch sign-out   the sign-in service stopping (no dialogs)
"""

import os
import subprocess
import sys

from ..config import APP_VERSION
from . import autostart, dialogs, emulators, logs, update
from .paths import app_dir, bundle_root

START_SCRIPT = "Start RAOfflineProxy.sh"
ASK_AUTOSTART = (
    "Start RAOfflineProxy automatically when you sign in, in Desktop and Game Mode?\n\n"
    "Either way, after a crash or reboot your emulators are never left pointing at a "
    "proxy that isn't running. You can change this with \"Start Automatically.sh\"."
)


def run_main(command: str) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "-m", "raofflineproxy.main", command],
        cwd=app_dir(), capture_output=True, text=True, check=False,
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def emulators_closed(action: str) -> bool:
    """Waits for the user to close any open emulator, which would otherwise
    write its old settings back over ours when it exits. False: cancelled."""
    while True:
        open_now = emulators.running()
        if not open_now:
            return True
        names = " and ".join(open_now)
        if not dialogs.continue_or_cancel(
            f"{names} {'is' if len(open_now) == 1 else 'are'} open. Close {'it' if len(open_now) == 1 else 'them'} "
            f"first, then press Continue to {action}.\n\n"
            "(An open emulator saves its settings when it closes, which would undo this.)"
        ):
            return False


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
    if not emulators_closed("start the proxy"):
        return 1
    if offer_update():
        # The new version's own Start script, so its code runs from here on.
        os.execv("/bin/bash", ["bash", str(bundle_root() / START_SCRIPT)])
    if not autostart.setting_chosen():
        autostart.set_start_automatically(dialogs.ask(ASK_AUTOSTART))
    service_installed = autostart.install()
    ok, output = run_main("start-proxy")
    if ok:
        autostart.mark_wanted(True)
    message = ("Proxy started." if ok else "Starting the proxy failed.") + f"\n\n{output}"
    if not service_installed:
        message += "\n\nThe sign-in service couldn't be set up (no systemd user session)."
    dialogs.show(message)
    return 0 if ok else 1


def stop() -> int:
    if not emulators_closed("stop the proxy"):
        return 1
    ok, output = run_main("stop-proxy")
    if ok:
        autostart.mark_wanted(False)
    dialogs.show(("Proxy stopped." if ok else "Stopping the proxy failed.") + f"\n\n{output}")
    return 0 if ok else 1


def toggle_autostart() -> int:
    enabled = autostart.start_automatically()
    question = (
        "RAOfflineProxy starts automatically when you sign in. Turn that off?"
        if enabled
        else "Start RAOfflineProxy automatically when you sign in, in Desktop and Game Mode?"
    )
    if dialogs.ask(question):
        autostart.set_start_automatically(not enabled)
        autostart.install()
        dialogs.show("Start automatically is " + ("off." if enabled else "on."))
    return 0


def sign_in() -> int:
    """No dialogs: nothing may be on screen yet. Output goes to the journal."""
    ok, output = run_main("start-proxy" if autostart.should_start_at_sign_in() else "stop-proxy")
    print(output)
    return 0 if ok else 1


def sign_out() -> int:
    # Leaves the "wanted" mark alone, so the next sign-in starts it again.
    ok, output = run_main("stop-proxy")
    print(output)
    return 0 if ok else 1


def send_logs() -> int:
    try:
        dialogs.show(logs.send_logs())
        return 0
    except Exception as exc:
        dialogs.show(f"Send Logs failed: {exc}")
        return 1


def main(argv: list[str]) -> int:
    commands = {
        "start": start,
        "stop": stop,
        "send-logs": send_logs,
        "autostart": toggle_autostart,
        "sign-in": sign_in,
        "sign-out": sign_out,
    }
    if len(argv) != 2 or argv[1] not in commands:
        print(__doc__)
        return 2
    return commands[argv[1]]()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
