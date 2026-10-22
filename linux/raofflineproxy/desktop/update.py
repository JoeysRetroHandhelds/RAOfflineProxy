from __future__ import annotations

"""In-place updates for the desktop Linux bundle: find a newer release with a
RAOfflineProxy-Desktop-v<version>.tar.gz, check it against its .sha256, and
swap the bundle's app/ and scripts for the new ones, keeping data/.

Linux lets files that are in use be replaced, so unlike Windows this runs in
the same process; the caller stops the proxy first and restarts afterwards."""

import io
import shutil
import tarfile
from dataclasses import dataclass
from pathlib import Path

from .. import release_assets
from ..config import APP_VERSION, load_config
from ..update import GITHUB_RELEASES_URL, fetch_github_json, parse_version
from .paths import TEST_CHANNEL_FILE, bundle_root, test_channel

# For testing the update flow only, as on Windows.
RELEASES_URL_OVERRIDE_KEY = "update_releases_url"
BUNDLE_DIR = "RAOfflineProxy"
PROGRAM_FOLDERS = ("app", "python")


@dataclass
class DesktopUpdate:
    version: str
    asset_url: str
    checksum_url: str | None


def releases_url() -> str:
    return test_channel().get("update_releases_url") or load_config().get(RELEASES_URL_OVERRIDE_KEY) or GITHUB_RELEASES_URL


def find_desktop_asset(assets: list[dict]) -> str | None:
    return release_assets.find_asset(assets, "desktop", ".tar.gz")


def check() -> DesktopUpdate | None:
    """The newest release newer than this one, or None (also when offline).
    A bundle without its python/ folder (updated by a build whose updater
    only swapped app/) is offered this same version again, to complete it."""
    current = parse_version(APP_VERSION)
    incomplete = not (bundle_root() / "python").is_dir()
    releases = fetch_github_json(releases_url())
    if current is None or not isinstance(releases, list):
        return None
    best = None
    for release in releases:
        if not isinstance(release, dict) or release.get("draft"):
            continue
        name = str(release.get("tag_name") or "")
        version = parse_version(name)
        assets = release.get("assets") or []
        asset_url = find_desktop_asset(assets)
        if version is None or asset_url is None:
            continue
        if not (version > current or (incomplete and version == current)):
            continue
        # A nightly is only offered to someone already on nightlies, as elsewhere.
        if version.is_nightly and not current.is_nightly:
            continue
        if best is None or version > best[0]:
            best = (version, DesktopUpdate(name.removeprefix("v"), asset_url, release_assets.find_checksum_asset(assets, asset_url)))
    return best[1] if best else None


def download(update: DesktopUpdate) -> bytes:
    source = releases_url()
    for url in (update.asset_url, update.checksum_url):
        if url and not release_assets.allowed_download(url, source):
            raise RuntimeError(f"refusing to download an update from {url}")
    if update.checksum_url is None and release_assets.checksum_required(source):
        raise RuntimeError("this release has no checksum file (.sha256), so it can't be checked and isn't installed")
    data = release_assets.download(update.asset_url)
    if update.checksum_url and not release_assets.matches_checksum(data, release_assets.download(update.checksum_url)):
        raise RuntimeError("the downloaded update doesn't match its published checksum")
    return data


def install(archive: bytes, root: Path | None = None) -> None:
    """Swaps in the new bundle. data/ is never touched; on any failure the old
    program folders are put back. testing.json goes when the new build has none, so a test
    install that updates to a release build leaves the test channel."""
    root = root or bundle_root()
    staging = root / ".update"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            bundle.extractall(staging, filter="data")
        new = staging / BUNDLE_DIR
        if not (new / "app").is_dir():
            raise RuntimeError("the downloaded update has no app folder")
        # app/, and python/ (the bundled runtime, which older builds didn't have).
        folders = [name for name in PROGRAM_FOLDERS if (new / name).is_dir()]
        swapped = []
        try:
            for name in folders:
                old = root / f"{name}.old"
                shutil.rmtree(old, ignore_errors=True)
                if (root / name).exists():
                    (root / name).rename(old)
                (new / name).rename(root / name)
                swapped.append(name)
        except OSError:
            for name in reversed(folders):
                if name in swapped:
                    shutil.rmtree(root / name, ignore_errors=True)
                if (root / f"{name}.old").exists():
                    (root / f"{name}.old").rename(root / name)
            raise
        for item in new.iterdir():
            if item.is_file():
                shutil.copy2(item, root / item.name)
        if not (new / TEST_CHANNEL_FILE).exists():
            (root / TEST_CHANNEL_FILE).unlink(missing_ok=True)
        for name in folders:
            shutil.rmtree(root / f"{name}.old", ignore_errors=True)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
