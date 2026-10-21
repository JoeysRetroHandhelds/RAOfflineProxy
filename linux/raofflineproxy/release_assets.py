from __future__ import annotations

"""Release download rules shared by the portable bundles (Windows and desktop
Linux): which URLs an in-place update may download, and the published SHA-256
next to each bundle."""

import hashlib
import urllib.request
from urllib.parse import urlsplit

from .network import configured_ssl_context
from .update import GITHUB_RELEASES_URL


def find_asset(assets: list[dict], word: str, suffix: str) -> str | None:
    for asset in assets:
        name = str(asset.get("name") or "").lower()
        if word in name and name.endswith(suffix):
            return str(asset.get("browser_download_url") or "") or None
    return None


def find_checksum_asset(assets: list[dict], bundle_url: str) -> str | None:
    wanted = bundle_url.rsplit("/", 1)[-1].lower() + ".sha256"
    for asset in assets:
        if str(asset.get("name") or "").lower() == wanted:
            return str(asset.get("browser_download_url") or "") or None
    return None


def _repo_of(api_url: str) -> str | None:
    parts = urlsplit(api_url)
    if parts.netloc == "api.github.com" and parts.path.startswith("/repos/"):
        return "/".join(parts.path.split("/")[2:4]).lower()
    return None


def allowed_download(url: str, releases_url: str, nightly_urls: tuple[str, ...] = ()) -> bool:
    """Only this project's GitHub release downloads are installed (its releases
    and its nightly builds). A test releases list (test channel or
    update_releases_url) may also point at its own repository's releases, or at
    its own host (a local test server)."""
    target = urlsplit(url)
    source = urlsplit(releases_url)
    repos = {_repo_of(GITHUB_RELEASES_URL), _repo_of(releases_url), *map(_repo_of, nightly_urls)} - {None}
    if target.scheme == "https" and target.netloc == "github.com":
        repo = "/".join(target.path.split("/")[1:3]).lower()
        return repo in repos and target.path.split("/")[3:5] == ["releases", "download"]
    official = urlsplit(GITHUB_RELEASES_URL).netloc
    return source.netloc not in ("", official, "api.github.com") and target.netloc == source.netloc


def checksum_required(releases_url: str) -> bool:
    """Official releases must publish a .sha256 for the bundle. A test releases
    list (test channel or update_releases_url) may leave it out."""
    return releases_url == GITHUB_RELEASES_URL


def download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120, context=configured_ssl_context()) as response:
        return response.read()


def matches_checksum(data: bytes, checksum_file: bytes) -> bool:
    fields = checksum_file.decode("ascii", errors="replace").split()
    return bool(fields) and hashlib.sha256(data).hexdigest() == fields[0].lower()
