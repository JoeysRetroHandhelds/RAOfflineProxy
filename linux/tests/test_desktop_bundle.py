import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from linux.raofflineproxy import release_assets
from linux.raofflineproxy.desktop import logs, update

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "linux" / "raofflineproxy"

# Run inside a bundle layout: sys.platform first, so a Windows host acts as Linux.
PROBE = """
import json, sys
sys.platform = "linux"
from raofflineproxy import config
print(json.dumps({"desktop": config.running_on_desktop(), "config_dir": str(config.CONFIG_DIR), "port": config.proxy_port({})}))
"""


def make_bundle(root: Path, marker: bool) -> Path:
    shutil.copytree(PACKAGE, root / "app" / "raofflineproxy", ignore=shutil.ignore_patterns("__pycache__", "windows"))
    if marker:
        (root / "desktop.txt").write_text("marker\n")
    return root


def probe(root: Path) -> dict:
    env = {key: value for key, value in os.environ.items() if key not in ("RAOFFLINEPROXY_CONFIG_DIR", "XDG_CONFIG_HOME")}
    result = subprocess.run(
        [sys.executable, "-c", PROBE], cwd=root / "app", env=env, capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


class BundleDetectionTests(unittest.TestCase):
    def test_a_desktop_bundle_keeps_its_data_in_the_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = make_bundle(Path(temp) / "RAOfflineProxy", marker=True)
            result = probe(root)
        self.assertTrue(result["desktop"])
        self.assertEqual(Path(result["config_dir"]), (root / "data").resolve())
        # Not 8080: Steam's Game Mode debugger (and Decky Loader) need that one.
        self.assertEqual(result["port"], 18080)

    def test_without_the_marker_nothing_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = make_bundle(Path(temp) / "RAOfflineProxy", marker=False)
            result = probe(root)
        self.assertFalse(result["desktop"])
        self.assertNotIn(str(root), result["config_dir"])
        self.assertEqual(result["port"], 8080)


def release(tag: str, *names: str) -> dict:
    return {
        "tag_name": tag,
        "draft": False,
        "assets": [{"name": name, "browser_download_url": f"https://github.com/o/r/releases/download/{tag}/{name}"} for name in names],
    }


class UpdateCheckTests(unittest.TestCase):
    def check(self, current: str, releases: list) -> update.DesktopUpdate | None:
        with mock.patch.object(update, "APP_VERSION", current), \
                mock.patch.object(update, "fetch_github_json", return_value=releases), \
                mock.patch.object(update, "releases_url", return_value="https://api.github.com/repos/o/r/releases"):
            return update.check()

    def test_offers_the_newest_desktop_release(self) -> None:
        found = self.check("2.2.0-alpha1-nightly.13", [
            release("v2.2.0-alpha1-nightly.14", "RAOfflineProxy-Desktop-v2.2.0-alpha1-nightly.14.tar.gz",
                    "RAOfflineProxy-Desktop-v2.2.0-alpha1-nightly.14.tar.gz.sha256"),
            release("v2.2.0-alpha1-nightly.15", "RAOfflineProxy-Windows-v2.2.0-alpha1-nightly.15.zip"),
        ])
        self.assertEqual(found.version, "2.2.0-alpha1-nightly.14")
        self.assertTrue(found.checksum_url.endswith(".tar.gz.sha256"))

    def test_nothing_newer(self) -> None:
        self.assertIsNone(self.check("2.2.0-alpha1-nightly.14", [
            release("v2.2.0-alpha1-nightly.14", "RAOfflineProxy-Desktop-v2.2.0-alpha1-nightly.14.tar.gz"),
        ]))

    def test_offline(self) -> None:
        self.assertIsNone(self.check("2.2.0-alpha1-nightly.13", None))

    def test_an_official_release_without_a_checksum_is_refused(self) -> None:
        offer = update.DesktopUpdate("2.3.0", "https://github.com/misantronic/RAOfflineProxy/releases/download/v2.3.0/x.tar.gz", None)
        with mock.patch.object(update, "releases_url", return_value=release_assets.GITHUB_RELEASES_URL), \
                mock.patch.object(release_assets, "download") as download:
            with self.assertRaisesRegex(RuntimeError, "no checksum file"):
                update.download(offer)
        download.assert_not_called()


def bundle_archive(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, content in files.items():
            data = content.encode()
            info = tarfile.TarInfo(f"RAOfflineProxy/{name}")
            info.size = len(data)
            info.mode = 0o755 if name.endswith(".sh") else 0o644
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class InstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()) / "RAOfflineProxy"
        (self.root / "app" / "raofflineproxy").mkdir(parents=True)
        (self.root / "app" / "raofflineproxy" / "config.py").write_text("old")
        (self.root / "data").mkdir()
        (self.root / "data" / "config.json").write_text('{"kept": true}')
        (self.root / "testing.json").write_text("{}")
        (self.root / "Start RAOfflineProxy.sh").write_text("old start")
        self.addCleanup(shutil.rmtree, self.root.parent, True)

    def test_swaps_the_program_and_keeps_the_data(self) -> None:
        update.install(bundle_archive({
            "app/raofflineproxy/config.py": "new",
            "Start RAOfflineProxy.sh": "new start",
            "desktop.txt": "marker",
        }), self.root)
        self.assertEqual((self.root / "app" / "raofflineproxy" / "config.py").read_text(), "new")
        self.assertEqual((self.root / "Start RAOfflineProxy.sh").read_text(), "new start")
        self.assertEqual((self.root / "data" / "config.json").read_text(), '{"kept": true}')
        # A release build has no testing.json, so the test channel goes with the update.
        self.assertFalse((self.root / "testing.json").exists())
        self.assertFalse((self.root / "app.old").exists())
        self.assertFalse((self.root / ".update").exists())

    def test_a_test_build_keeps_the_test_channel(self) -> None:
        update.install(bundle_archive({"app/raofflineproxy/config.py": "new", "testing.json": '{"new": 1}'}), self.root)
        self.assertEqual((self.root / "testing.json").read_text(), '{"new": 1}')

    def test_a_broken_archive_leaves_the_old_version(self) -> None:
        with self.assertRaises(RuntimeError):
            update.install(bundle_archive({"README.txt": "no app folder"}), self.root)
        self.assertEqual((self.root / "app" / "raofflineproxy" / "config.py").read_text(), "old")
        self.assertTrue((self.root / "testing.json").exists())


class SendLogsTests(unittest.TestCase):
    def test_copies_to_a_local_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "logs.zip"
            source.write_bytes(b"zip")
            where = logs.copy_to(source, str(Path(temp) / "share" / "logs"))
            self.assertEqual(Path(where).read_bytes(), b"zip")

    def test_copies_to_a_share_with_kioclient(self) -> None:
        calls = []

        def run(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, "", "")

        with mock.patch.object(logs.shutil, "which", side_effect=lambda name: name if name == "kioclient" else None), \
                mock.patch.object(logs.subprocess, "run", side_effect=run):
            where = logs.copy_to(Path("/tmp/x.zip"), "smb://host/z/logs/")
        self.assertEqual(where, "smb://host/z/logs/x.zip")
        self.assertEqual(calls, [["kioclient", "copy", str(Path("/tmp/x.zip")), "smb://host/z/logs/x.zip"]])

    def test_a_missing_share_folder_is_created(self) -> None:
        calls = []

        def run(command, **kwargs):
            calls.append(command)
            # The file copy fails (no folder); copying a folder of that name works.
            return subprocess.CompletedProcess(command, 0 if len(calls) == 2 else 1, "", "Could not write")

        with mock.patch.object(logs.shutil, "which", side_effect=lambda name: name if name == "kioclient" else None), \
                mock.patch.object(logs.subprocess, "run", side_effect=run):
            where = logs.copy_to(Path(__file__), "smb://host/z/logs")
        self.assertEqual(where, f"smb://host/z/logs/{Path(__file__).name}")
        self.assertEqual(Path(calls[1][2]).name, "logs")
        self.assertEqual(calls[1][3], "smb://host/z/")

    def test_a_share_without_a_copy_tool_says_so(self) -> None:
        with mock.patch.object(logs.shutil, "which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "no kioclient or gio"):
                logs.copy_to(Path("/tmp/x.zip"), "smb://host/z/logs")


class DeviceInfoTests(unittest.TestCase):
    def test_desktop_reports_the_distro_not_a_handheld_firmware(self) -> None:
        from linux.raofflineproxy import config, log_uploader

        with tempfile.TemporaryDirectory() as temp:
            os_release = Path(temp) / "os-release"
            os_release.write_text('NAME="Anatase"\nPRETTY_NAME="Anatase 20261019"\n')
            with mock.patch.object(config, "running_on_desktop", return_value=True), \
                    mock.patch.object(config, "OS_RELEASE_PATH", os_release):
                self.assertEqual(log_uploader._platform_label(), "Anatase")


if __name__ == "__main__":
    unittest.main()
