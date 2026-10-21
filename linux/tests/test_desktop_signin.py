import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from linux.raofflineproxy.desktop import autostart, emulators, launch


class SignInTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = Path(tempfile.mkdtemp())
        self.config: dict = {}
        for patcher in (
            mock.patch.object(autostart, "WANTED_FILE", self.data / "desktop_proxy_wanted"),
            mock.patch.object(autostart, "load_config", side_effect=lambda: dict(self.config)),
            mock.patch.object(autostart, "save_config", side_effect=lambda data: self.config.update(data)),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def sign_in_command(self) -> str:
        with mock.patch.object(launch, "run_main", return_value=(True, "")) as run:
            launch.sign_in()
        return run.call_args.args[0]

    def test_starts_when_set_to_start_automatically(self) -> None:
        autostart.set_start_automatically(True)
        self.assertEqual(self.sign_in_command(), "start-proxy")

    def test_starts_again_after_a_crash_while_it_was_running(self) -> None:
        autostart.set_start_automatically(False)
        autostart.mark_wanted(True)  # Start ran, Stop never did
        self.assertEqual(self.sign_in_command(), "start-proxy")

    def test_otherwise_restores_the_emulator_configs(self) -> None:
        autostart.set_start_automatically(False)
        self.assertEqual(self.sign_in_command(), "stop-proxy")

    def test_stop_clears_the_mark_and_sign_out_keeps_it(self) -> None:
        autostart.mark_wanted(True)
        with mock.patch.object(launch, "run_main", return_value=(True, "")):
            launch.sign_out()
            self.assertTrue(autostart.WANTED_FILE.exists())
            with mock.patch.object(launch, "emulators_closed", return_value=True), \
                    mock.patch.object(launch.dialogs, "show"):
                launch.stop()
        self.assertFalse(autostart.WANTED_FILE.exists())


class UnitTests(unittest.TestCase):
    def test_writes_and_enables_the_unit_with_the_bundle_path(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            calls = []
            with mock.patch.dict("os.environ", {"XDG_CONFIG_HOME": home}), \
                    mock.patch.object(autostart, "app_dir", return_value=Path("/bundle/app")), \
                    mock.patch.object(autostart.shutil, "which", return_value="/usr/bin/systemctl"), \
                    mock.patch.object(autostart.subprocess, "run",
                                      side_effect=lambda command, **kw: calls.append(command) or subprocess.CompletedProcess(command, 0)):
                self.assertTrue(autostart.install())
                unit = (Path(home) / "systemd" / "user" / "raofflineproxy.service").read_text()
                # Unchanged on the next Start: no needless daemon-reload.
                autostart.install()
        self.assertIn(f"WorkingDirectory={Path('/bundle/app')}", unit)
        self.assertIn("launch sign-in", unit)
        self.assertIn("WantedBy=default.target", unit)
        self.assertEqual(
            calls,
            [["systemctl", "--user", "daemon-reload"], ["systemctl", "--user", "enable", "raofflineproxy.service"],
             ["systemctl", "--user", "enable", "raofflineproxy.service"]],
        )


class EmulatorCheckTests(unittest.TestCase):
    def test_finds_flatpak_and_regular_emulators_but_not_the_file_manager(self) -> None:
        def output(command):
            if command[0] == "flatpak":
                return "org.DolphinEmu.dolphin-emu\norg.kde.okular\n"
            return "1234\n" if command[-1] == "retroarch" else ""

        with mock.patch.object(emulators, "_output", side_effect=output):
            self.assertEqual(emulators.running(), ["Dolphin", "RetroArch"])

    def test_start_waits_for_open_emulators_and_can_be_cancelled(self) -> None:
        with mock.patch.object(emulators, "running", side_effect=[["Dolphin"], []]), \
                mock.patch.object(launch.dialogs, "continue_or_cancel", return_value=True) as asked:
            self.assertTrue(launch.emulators_closed("start the proxy"))
        self.assertIn("Dolphin is open", asked.call_args.args[0])
        with mock.patch.object(emulators, "running", return_value=["RetroArch"]), \
                mock.patch.object(launch.dialogs, "continue_or_cancel", return_value=False):
            self.assertFalse(launch.emulators_closed("start the proxy"))


if __name__ == "__main__":
    unittest.main()
