import pytest

from linux.raofflineproxy.windows.update import (
    GITHUB_RELEASES_URL,
    allowed_download,
    find_checksum_asset,
)

FORK_RELEASES = "https://api.github.com/repos/JoeysRetroHandhelds/RAOfflineProxy/releases"


@pytest.mark.parametrize(
    "url, releases_url, allowed",
    [
        ("https://github.com/misantronic/RAOfflineProxy/releases/download/v2.3/RAOfflineProxy-Windows-v2.3.zip", GITHUB_RELEASES_URL, True),
        ("https://github.com/misantronic/RAOfflineProxy-nightly/releases/download/nightly-linux/x.zip", GITHUB_RELEASES_URL, True),
        ("https://github.com/someone/RAOfflineProxy/releases/download/v1/x.zip", GITHUB_RELEASES_URL, False),
        ("https://github.com/misantronic/RAOfflineProxy/archive/x.zip", GITHUB_RELEASES_URL, False),
        ("http://github.com/misantronic/RAOfflineProxy/releases/download/v1/x.zip", GITHUB_RELEASES_URL, False),
        ("https://example.com/x.zip", GITHUB_RELEASES_URL, False),
        # A test releases list may use its own repository, or its own host.
        ("https://github.com/JoeysRetroHandhelds/RAOfflineProxy/releases/download/v1/x.zip", FORK_RELEASES, True),
        ("http://127.0.0.1:5000/x.zip", "http://127.0.0.1:5000/releases.json", True),
        ("http://127.0.0.1:6000/x.zip", "http://127.0.0.1:5000/releases.json", False),
    ],
)
def test_only_release_downloads_are_allowed(url, releases_url, allowed):
    assert allowed_download(url, releases_url) is allowed


def test_checksum_asset_matches_the_zip_name():
    assets = [
        {"name": "RAOfflineProxy-Windows-v2.3.zip", "browser_download_url": "https://x/a.zip"},
        {"name": "RAOfflineProxy-Windows-v2.3.zip.sha256", "browser_download_url": "https://x/a.zip.sha256"},
        {"name": "RAOfflineProxy-Knulli-v2.3-Install.sh.sha256", "browser_download_url": "https://x/k.sha256"},
    ]
    zip_url = "https://github.com/o/r/releases/download/v2.3/RAOfflineProxy-Windows-v2.3.zip"
    assert find_checksum_asset(assets, zip_url) == "https://x/a.zip.sha256"
    assert find_checksum_asset(assets[:1], zip_url) is None
