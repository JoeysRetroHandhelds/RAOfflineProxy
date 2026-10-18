from __future__ import annotations

"""Update checker for Windows, as in the Android app: at most once a day, look
for a newer GitHub release with a Windows zip, and install it by running that
zip into the portable folder in place, keeping its data/.

Uses the shared release fetching and version comparison. The shared checker
only knows the Linux bundles, so the Windows menu turns it off and uses this."""

import json
import logging
import subprocess
import tempfile
import time
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import APP_VERSION, CONFIG_DIR, load_config
from .network import configured_ssl_context
from .update import (
    GITHUB_NIGHTLY_RELEASE_URL,
    GITHUB_RELEASES_URL,
    fetch_github_json,
    nightly_version_name,
    parse_version,
)

LOGGER = logging.getLogger("raofflineproxy")
STATUS_FILE = CONFIG_DIR / "windows_update.json"
CHECK_INTERVAL_SECONDS = 24 * 60 * 60
# For testing the update flow only: a releases list in GitHub's format (e.g. a
# local server with a fake newer release) used instead of GitHub. It also
# stops nightly builds from being considered.
RELEASES_URL_OVERRIDE_KEY = "update_releases_url"
# After a failed check (offline, GitHub rate limit), wait this long before the next.
RETRY_INTERVAL_SECONDS = 60 * 60
TEST_CHANNEL_INTERVAL_SECONDS = 10 * 60


@dataclass
class WindowsUpdate:
    available: bool
    latest_version: str | None
    release_url: str | None
    asset_url: str | None
    checked_at: int
    failed: bool = False


def find_windows_asset(assets: list[dict]) -> str | None:
    for asset in assets:
        name = str(asset.get("name") or "").lower()
        if "windows" in name and name.endswith(".zip"):
            return str(asset.get("browser_download_url") or "") or None
    return None


def check(force: bool = False) -> WindowsUpdate:
    cached = load_status()
    if cached is not None and not force:
        interval = RETRY_INTERVAL_SECONDS if cached.failed else CHECK_INTERVAL_SECONDS
        from .windows_paths import test_channel

        if test_channel().get("update_releases_url"):
            # Test builds are published often, so testers get them quickly.
            interval = min(interval, TEST_CHANNEL_INTERVAL_SECONDS)
        if time.time() - cached.checked_at < interval:
            return still_newer(cached)

    current = parse_version(APP_VERSION)
    best = None
    from .windows_paths import test_channel

    override = test_channel().get("update_releases_url") or load_config().get(RELEASES_URL_OVERRIDE_KEY)
    releases = fetch_github_json(override or GITHUB_RELEASES_URL)
    candidates = [(release, str(release.get("tag_name") or "")) for release in releases or [] if isinstance(release, dict)]
    if current is not None and current.is_nightly and not override:
        # Nightly installs also follow the nightly build, whose Windows zip is
        # published alongside the Linux bundles (as the Linux checker does).
        nightly = fetch_github_json(GITHUB_NIGHTLY_RELEASE_URL)
        if isinstance(nightly, dict):
            candidates.append((nightly, nightly_version_name(nightly)))
    for release, version_name in candidates:
        if release.get("draft"):
            continue
        version = parse_version(version_name)
        asset_url = find_windows_asset(release.get("assets") or [])
        if version is None or asset_url is None or current is None or not version > current:
            continue
        # A nightly is only offered to someone already on nightlies, as on Linux.
        if version.is_nightly and not current.is_nightly:
            continue
        if best is None or version > best[0]:
            best = (version, version_name, str(release.get("html_url") or ""), asset_url)

    result = WindowsUpdate(
        available=best is not None,
        latest_version=best[1] if best else None,
        release_url=best[2] if best else None,
        asset_url=best[3] if best else None,
        checked_at=int(time.time()),
        failed=releases is None,
    )
    # A failure is recorded too, so callers polling check() don't retry it on
    # every call; it's retried after RETRY_INTERVAL_SECONDS.
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(asdict(result)), encoding="utf-8")
    return result


def still_newer(cached: WindowsUpdate) -> WindowsUpdate:
    """A saved result offers its version only while it's newer than what's
    running: right after an update installs, it's the running version."""
    if not cached.available:
        return cached
    offered, current = parse_version(cached.latest_version or ""), parse_version(APP_VERSION)
    if offered is None or current is None or offered > current:
        return cached
    return WindowsUpdate(False, None, None, None, cached.checked_at, cached.failed)


def load_status() -> WindowsUpdate | None:
    try:
        return WindowsUpdate(**json.loads(STATUS_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return None


# Runs from a temp folder once the app has stopped, so the files it replaces
# aren't in use. data\ (settings, cache, awards) and portable.txt (the folder's
# id for Start with Windows) are never touched.
UPDATER_SCRIPT = r"""
param([string]$Root, [string]$New, [string]$Log, [switch]$NoMenu)
$ErrorActionPreference = 'Stop'
Start-Transcript -LiteralPath $Log -Append | Out-Null
try {
    & (Join-Path $Root 'python\python.exe') -m raofflineproxy.windows_launch --stop
    $python = (Join-Path $Root 'python').ToLower()
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline -and (Get-CimInstance Win32_Process |
            Where-Object { $_.ExecutablePath -and $_.ExecutablePath.ToLower().StartsWith($python) })) {
        Start-Sleep -Milliseconds 500
    }
    # Rename the old program aside rather than deleting it: a rename fails as a
    # whole if anything inside is still locked (a process not quite gone, an
    # antivirus scan), so the folder is never left half deleted. Retried while
    # locks clear; on any failure the old version is put back.
    $moved = @()
    try {
        foreach ($name in 'app', 'python') {
            $old = Join-Path $Root "$name.old"
            if (Test-Path -LiteralPath $old) { Remove-Item -LiteralPath $old -Recurse -Force }
            for ($attempt = 1; ; $attempt++) {
                try { Rename-Item -LiteralPath (Join-Path $Root $name) -NewName "$name.old"; break }
                catch { if ($attempt -ge 20) { throw }; Start-Sleep -Milliseconds 500 }
            }
            $moved += $name
        }
        foreach ($name in 'app', 'python') {
            Copy-Item -LiteralPath (Join-Path $New $name) -Destination $Root -Recurse
        }
    } catch {
        foreach ($name in $moved) {
            $current = Join-Path $Root $name
            if (Test-Path -LiteralPath $current) { Remove-Item -LiteralPath $current -Recurse -Force }
            Rename-Item -LiteralPath (Join-Path $Root "$name.old") -NewName $name
        }
        throw
    }
    foreach ($name in 'app', 'python') {
        Remove-Item -LiteralPath (Join-Path $Root "$name.old") -Recurse -Force -ErrorAction SilentlyContinue
    }
    Get-ChildItem -LiteralPath $New -File | Where-Object { $_.Name -ne 'portable.txt' } |
        Copy-Item -Destination $Root -Force
    # testing.json comes and goes with the build: updating a test build to a
    # release build drops it, so the folder stops using the test channel.
    if (-not (Test-Path -LiteralPath (Join-Path $New 'testing.json'))) {
        Remove-Item -LiteralPath (Join-Path $Root 'testing.json') -ErrorAction SilentlyContinue
    }
    Write-Output 'Update installed'
} finally {
    # Start again either way: after a failure the old version is back in place.
    $launch = @('-m', 'raofflineproxy.windows_launch')
    if ($NoMenu) { $launch += '--autostart' }
    Start-Process -FilePath (Join-Path $Root 'python\pythonw.exe') -ArgumentList $launch -WorkingDirectory $Root
    Stop-Transcript | Out-Null
    # This script's own folder (the download): gone once Windows lets go of it.
    Start-Process -WindowStyle Hidden cmd.exe -ArgumentList '/c', "timeout /t 3 /nobreak >nul & rmdir /s /q `"$PSScriptRoot`""
}
"""


def download_and_launch_installer(asset_url: str, open_menu: bool = True) -> None:
    """Downloads and unzips the release, then starts a script that stops this
    folder's proxy, tray and menu, swaps in the new program files and starts it
    again. The caller should exit right after."""
    from .windows_paths import portable_root

    root = portable_root()
    if root is None:
        raise RuntimeError("updates install into the portable RAOfflineProxy folder")
    folder = Path(tempfile.mkdtemp(prefix="RAOfflineProxy-update-"))
    archive = folder / "update.zip"
    with urllib.request.urlopen(asset_url, timeout=120, context=configured_ssl_context()) as response:
        archive.write_bytes(response.read())
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(folder / "new")
    marker = next((folder / "new").rglob("portable.txt"))
    script = folder / "update.ps1"
    script.write_text(UPDATER_SCRIPT.lstrip(), encoding="utf-8")
    subprocess.Popen(
        [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
            "-File", str(script), "-Root", str(root), "-New", str(marker.parent),
            "-Log", str(CONFIG_DIR / "update.log"),
            *([] if open_menu else ["-NoMenu"]),
        ],
        # Not DETACHED_PROCESS: PowerShell exits at once without a console. A
        # hidden one (CREATE_NO_WINDOW) also outlives the menu that starts it.
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
