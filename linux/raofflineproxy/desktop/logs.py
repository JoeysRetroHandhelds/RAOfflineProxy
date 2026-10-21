from __future__ import annotations

"""Send Logs for the desktop bundle: the same redacted zip the menu uploads.
Test builds save it to the test channel's logs_folder instead, which may be an
smb:// share (copied with KDE's kioclient or GNOME's gio, as Python can't
write to one directly)."""

import json
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path

from ..log_uploader import _read_redacted_log_files, _zip_logs, device_metadata, upload_logs
from .paths import test_channel

# kioclient is KDE 6's name; older Plasma ships kioclient5.
COPY_COMMANDS = (("kioclient", "copy"), ("kioclient5", "copy"), ("gio", "copy"))


def patched_emulators() -> list[str]:
    """From what the proxy actually patched: the shared check only knows the
    default RetroArch location, and has no Dolphin."""
    from ..state import load_patch_state

    state = load_patch_state() or {}
    found = []
    if state.get("cfg_path"):
        found.append("RetroArch")
    if state.get("dolphin_ini_path"):
        found.append("Dolphin")
    if state.get("ppsspp_ini_path"):
        found.append("PPSSPP")
    return found


def device_name() -> str:
    """For the log file name: the name set in the system settings (hostnamectl's
    pretty hostname), else the machine's model, rather than a network name
    such as one an ISP assigned."""
    try:
        pretty = subprocess.run(
            ["hostnamectl", "--pretty"], capture_output=True, text=True, timeout=5, check=False
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pretty = ""
    name = pretty or device_metadata().get("device") or socket.gethostname()
    return "".join(char if char.isalnum() or char in "-_" else "-" for char in str(name)).strip("-") or "linux"


def build_zip() -> bytes:
    files = _read_redacted_log_files()
    files["device.json"] = json.dumps(device_metadata(), indent=2)
    return _zip_logs(files)


def copy_to(source: Path, folder: str) -> str:
    """Copies source into folder (a path, or a URL such as smb://host/share/dir);
    returns where it went."""
    if "://" not in folder:
        target = Path(folder).expanduser() / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return str(target)
    folder = folder.rstrip("/")
    target_url = folder + "/" + source.name
    parent_url, folder_name = folder.rsplit("/", 1)
    errors = []
    for command in COPY_COMMANDS:
        if shutil.which(command[0]) is None:
            continue
        if _copy(command, source, target_url, errors):
            return target_url
        # The folder may be missing, and these can't create one on a share: copying a
        # local folder of that name, holding the file, makes it.
        with tempfile.TemporaryDirectory() as temp:
            holder = Path(temp) / folder_name
            holder.mkdir()
            shutil.copyfile(source, holder / source.name)
            if _copy(command, holder, parent_url + "/", errors):
                return target_url
    raise RuntimeError("couldn't copy to " + folder + (": " + "; ".join(errors) if errors else ": no kioclient or gio found"))


def _copy(command: tuple[str, str], source: Path, target: str, errors: list[str]) -> bool:
    result = subprocess.run([*command, str(source), target], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        errors.append(f"{command[0]}: {(result.stderr or result.stdout).strip() or result.returncode}")
    return result.returncode == 0


def send_logs() -> str:
    """A one-line result for the dialog."""
    folder = test_channel().get("logs_folder")
    if not folder:
        return f"Logs sent. Log ID: {upload_logs()}"
    with tempfile.TemporaryDirectory() as temp:
        name = f"{device_name()}-{time.strftime('%Y%m%d-%H%M%S')}.zip"
        source = Path(temp) / name
        source.write_bytes(build_zip())
        return f"Logs saved to {copy_to(source, folder)}"
