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
    target_url = folder.rstrip("/") + "/" + source.name
    errors = []
    for command in COPY_COMMANDS:
        if shutil.which(command[0]) is None:
            continue
        result = subprocess.run([*command, str(source), target_url], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return target_url
        errors.append(f"{command[0]}: {(result.stderr or result.stdout).strip() or result.returncode}")
    raise RuntimeError("couldn't copy to " + folder + (": " + "; ".join(errors) if errors else ": no kioclient or gio found"))


def send_logs() -> str:
    """A one-line result for the dialog."""
    folder = test_channel().get("logs_folder")
    if not folder:
        return f"Logs sent. Log ID: {upload_logs()}"
    with tempfile.TemporaryDirectory() as temp:
        name = f"{socket.gethostname()}-{time.strftime('%Y%m%d-%H%M%S')}.zip"
        source = Path(temp) / name
        source.write_bytes(build_zip())
        return f"Logs saved to {copy_to(source, folder)}"
