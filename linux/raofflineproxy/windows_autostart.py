from __future__ import annotations

"""Start with Windows for the portable folder, surviving a changed drive letter.

The sign-in entry (the per-user Run key, no admin rights) doesn't hold the
folder's path. It runs a small launcher kept in %LOCALAPPDATA%, which looks for
the folder: first where it last was, then at the same path on every other
drive letter, matching the id written into the folder's portable.txt. So
E:\\Games\\RAOfflineProxy that comes back as F:\\Games\\RAOfflineProxy is still
found, and with the stick unplugged the launcher quietly does nothing. Only
the drive with the folder's volume serial is searched, so network drives
aren't probed and a backup copy on another drive is never started instead.

Every start records where the folder is (refresh_location), so after moving it
somewhere else the next manual start is enough. Turning Start with Windows off
removes both the entry and the launcher, leaving nothing behind."""

import json
import os
import subprocess
import uuid
from pathlib import Path

from .windows_paths import PORTABLE_MARKER, portable_root

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "RAOfflineProxy"
ID_PREFIX = "id="
# Windows 10 2004 and later have conhost --headless.
HEADLESS_CONHOST_BUILD = 19041

LAUNCHER_SCRIPT = r"""
# RAOfflineProxy sign-in launcher. Finds the portable folder (which may have
# changed drive letter) and starts it. Written by the app; safe to delete.
$state = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'location.json') | ConvertFrom-Json
function Test-Folder($root) {
    $marker = Join-Path $root 'portable.txt'
    (Test-Path -LiteralPath $marker) -and
        ((Get-Content -LiteralPath $marker) -contains ('id=' + $state.id))
}
$candidates = @($state.root)
# Only the drive with the folder's volume serial (a stick keeps it under any
# letter); network drives (DriveType 4) are never probed, as they can stall.
foreach ($disk in Get-CimInstance Win32_LogicalDisk -Filter 'DriveType = 2 OR DriveType = 3') {
    if (-not $state.volume -or $disk.VolumeSerialNumber -eq $state.volume) {
        $candidates += Join-Path ($disk.DeviceID + '\') $state.relative
    }
}
foreach ($root in $candidates) {
    if (Test-Folder $root) {
        Start-Process -FilePath (Join-Path $root 'python\pythonw.exe') `
            -ArgumentList '-m', 'raofflineproxy.windows_launch', '--autostart' `
            -WorkingDirectory $root
        break
    }
}
"""


def launcher_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    return base / "RAOfflineProxy-autostart"


def folder_id(root: Path) -> str:
    """The id in portable.txt, added the first time it's needed."""
    marker = root / PORTABLE_MARKER
    lines = marker.read_text(encoding="utf-8").splitlines() if marker.exists() else []
    for line in lines:
        if line.startswith(ID_PREFIX):
            return line[len(ID_PREFIX):].strip()
    new_id = uuid.uuid4().hex
    marker.write_text("\n".join([*lines, ID_PREFIX + new_id]) + "\n", encoding="utf-8")
    return new_id


def volume_serial(root: Path) -> str | None:
    """The drive's volume serial as Win32_LogicalDisk shows it (8 hex digits).
    It stays the same when a USB stick comes back under another letter."""
    import ctypes

    drive = os.path.splitdrive(str(root))[0] + os.sep
    serial = ctypes.c_uint32()
    if not ctypes.windll.kernel32.GetVolumeInformationW(drive, None, 0, ctypes.byref(serial), None, None, None, 0):
        return None
    return f"{serial.value:08X}"


def _write_location(root: Path) -> None:
    drive, relative = os.path.splitdrive(str(root))
    folder = launcher_dir()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "location.json").write_text(
        json.dumps(
            {
                "id": folder_id(root),
                "root": str(root),
                "relative": relative.lstrip("\\/"),
                "volume": volume_serial(root),
            }
        ),
        encoding="utf-8",
    )


TASK_NAME = "RAOfflineProxy"
# Tests (and anyone who wants no admin prompt) can keep to the Run entry.
MODE_ENV = "RAOFFLINEPROXY_AUTOSTART_MODE"

# Registers the logon task. Creating a logon-triggered task needs admin rights,
# so this runs elevated, once, through the standard UAC prompt. The task itself
# runs as the signed-in user, unelevated, with no time limit and on battery.
REGISTER_SCRIPT = r"""
param([string]$User, [string]$Execute, [string]$Arguments, [switch]$Remove)
$ErrorActionPreference = 'Stop'
if ($Remove) {
    Unregister-ScheduledTask -TaskName 'RAOfflineProxy' -Confirm:$false
    exit 0
}
$action = New-ScheduledTaskAction -Execute $Execute -Argument $Arguments
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $User
$principal = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'RAOfflineProxy' -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null
"""


def _launcher_command() -> list[str]:
    import sys

    script = launcher_dir() / "start.ps1"
    command = [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", str(script),
    ]
    # conhost --headless keeps PowerShell's console from flashing at sign-in.
    # Early Windows 10 builds lack it; there the console just flashes briefly.
    if sys.getwindowsversion().build >= HEADLESS_CONHOST_BUILD:
        command = ["conhost.exe", "--headless", *command]
    return command


def _run_value() -> str:
    return subprocess.list2cmdline(_launcher_command())


def _run_elevated(*args: str) -> bool:
    """Runs register.ps1 elevated (one UAC prompt) and waits. False when the
    prompt was declined or the script failed."""
    script = launcher_dir() / "register.ps1"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(REGISTER_SCRIPT.lstrip(), encoding="utf-8")
    inner = subprocess.list2cmdline(
        ["-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", str(script), *args]
    )
    outer = (
        "try { $p = Start-Process powershell.exe -Verb RunAs -Wait -PassThru -WindowStyle Hidden "
        f"-ArgumentList '{inner.replace(chr(39), chr(39) * 2)}'; exit $p.ExitCode }} catch {{ exit 1223 }}"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", outer],
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
        timeout=300,
        check=False,
    )
    return result.returncode == 0


# The Settings screen asks every frame; schtasks.exe takes a moment to start.
_task_cache: tuple[float, bool] | None = None
TASK_CACHE_SECONDS = 5


def task_exists() -> bool:
    import time

    global _task_cache
    if _task_cache is not None and time.monotonic() - _task_cache[0] < TASK_CACHE_SECONDS:
        return _task_cache[1]
    result = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", TASK_NAME],
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )
    _task_cache = (time.monotonic(), result.returncode == 0)
    return _task_cache[1]


def _forget_task() -> None:
    global _task_cache
    _task_cache = None


def _run_entry_exists() -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, RUN_VALUE)
            return True
    except OSError:
        return False


def is_enabled() -> bool:
    return _run_entry_exists() or task_exists()


def _set_run_entry(enabled: bool) -> None:
    import winreg

    if enabled:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, _run_value())
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, RUN_VALUE)
    except FileNotFoundError:
        pass


def enable() -> str:
    """Turns Start with Windows on. Prefers a logon task, which Windows' Xbox
    full screen experience still runs (it skips the Run list's startup apps);
    falls back to the Run entry if the admin prompt is declined. Returns
    "task" or "run" for which one it used."""
    root = portable_root()
    if root is None:
        raise OSError("Start with Windows needs the portable RAOfflineProxy folder")
    _write_location(root)
    (launcher_dir() / "start.ps1").write_text(LAUNCHER_SCRIPT.lstrip(), encoding="utf-8")

    _forget_task()
    if os.environ.get(MODE_ENV) != "run":
        command = _launcher_command()
        # Passed in, not read inside: an elevated prompt answered with another
        # admin's password would otherwise register the task for that account.
        domain, name = os.environ.get("USERDOMAIN", ""), os.environ.get("USERNAME", "")
        user = f"{domain}\\{name}" if domain else name
        if _run_elevated("-User", user, "-Execute", command[0], "-Arguments", subprocess.list2cmdline(command[1:])):
            _set_run_entry(False)  # one way to start, not two
            return "task"
    _set_run_entry(True)
    return "run"


def disable() -> bool:
    """False when the logon task couldn't be removed (admin prompt declined);
    the Run entry and launcher are removed either way only on success."""
    import shutil

    _forget_task()
    if task_exists() and not _run_elevated("-Remove"):
        return False
    _forget_task()
    _set_run_entry(False)
    shutil.rmtree(launcher_dir(), ignore_errors=True)
    return True


def refresh_location() -> None:
    """Called on every start, so the launcher's first guess is where the folder is now."""
    root = portable_root()
    if root is not None and is_enabled():
        _write_location(root)
