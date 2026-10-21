import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from linux.raofflineproxy import config

OVERRIDES = (
    "RAOFFLINEPROXY_RETROARCH_CFG",
    "RAOFFLINEPROXY_DOLPHIN_CONFIG_DIR",
    "RAOFFLINEPROXY_PPSSPP_INI",
)


class FlatpakPathTests(unittest.TestCase):
    """Desktop Linux with Flatpak emulators (SteamOS/EmuDeck, Discover)."""

    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        environ = {key: value for key, value in os.environ.items() if key not in OVERRIDES}
        for patcher in (
            mock.patch.object(Path, "home", return_value=self.home),
            mock.patch.dict(os.environ, environ, clear=True),
            # Desktop Linux, even when the tests run on Windows.
            mock.patch.object(config, "running_on_windows", return_value=False),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _touch(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return path

    def _flatpak_config(self, app_id: str) -> Path:
        return self.home / ".var" / "app" / app_id / "config"

    # RetroArch

    def test_retroarch_flatpak_cfg_is_used_when_present(self) -> None:
        cfg = self._touch(self._flatpak_config("org.libretro.RetroArch") / "retroarch" / "retroarch.cfg")
        self.assertEqual(config.detect_retroarch_cfg(), str(cfg))

    def test_retroarch_regular_install_wins_over_the_flatpak(self) -> None:
        self._touch(self._flatpak_config("org.libretro.RetroArch") / "retroarch" / "retroarch.cfg")
        native = self._touch(self.home / ".config" / "retroarch" / "retroarch.cfg")
        self.assertEqual(config.detect_retroarch_cfg(), str(native))

    def test_retroarch_without_a_flatpak_keeps_the_regular_path(self) -> None:
        self.assertEqual(
            config.detect_retroarch_cfg(), str(self.home / ".config" / "retroarch" / "retroarch.cfg")
        )

    def test_retroarch_env_override_still_wins(self) -> None:
        self._touch(self._flatpak_config("org.libretro.RetroArch") / "retroarch" / "retroarch.cfg")
        with mock.patch.dict(os.environ, {"RAOFFLINEPROXY_RETROARCH_CFG": "/custom/retroarch.cfg"}):
            self.assertEqual(config.detect_retroarch_cfg(), "/custom/retroarch.cfg")

    # Dolphin

    def test_dolphin_flatpak_config_dir_is_used_when_present(self) -> None:
        folder = self._flatpak_config("org.DolphinEmu.dolphin-emu") / "dolphin-emu"
        folder.mkdir(parents=True)
        self.assertEqual(config.detect_dolphin_config_dir({}), str(folder))

    def test_dolphin_without_a_flatpak_is_not_found(self) -> None:
        self.assertIsNone(config.detect_dolphin_config_dir({}))

    def test_dolphin_env_override_still_wins(self) -> None:
        (self._flatpak_config("org.DolphinEmu.dolphin-emu") / "dolphin-emu").mkdir(parents=True)
        with mock.patch.dict(os.environ, {"RAOFFLINEPROXY_DOLPHIN_CONFIG_DIR": "/custom/dolphin"}):
            self.assertEqual(config.detect_dolphin_config_dir({}), "/custom/dolphin")

    # PPSSPP

    def test_ppsspp_flatpak_ini_is_used_when_present(self) -> None:
        ini = self._touch(self._flatpak_config("org.ppsspp.PPSSPP") / "ppsspp" / "PSP" / "SYSTEM" / "ppsspp.ini")
        self.assertEqual(config.detect_ppsspp_ini({}), str(ini))

    def test_ppsspp_without_a_flatpak_is_not_found(self) -> None:
        self.assertIsNone(config.detect_ppsspp_ini({}))

    def test_ppsspp_env_override_still_wins(self) -> None:
        self._touch(self._flatpak_config("org.ppsspp.PPSSPP") / "ppsspp" / "PSP" / "SYSTEM" / "ppsspp.ini")
        with mock.patch.dict(os.environ, {"RAOFFLINEPROXY_PPSSPP_INI": "/custom/ppsspp.ini"}):
            self.assertEqual(config.detect_ppsspp_ini({}), "/custom/ppsspp.ini")

    def test_nothing_is_looked_up_at_import(self) -> None:
        """The paths are built per call, so a broken home can't break imports."""
        self.assertFalse(any(isinstance(value, Path) and ".var" in value.parts for value in vars(config).values()))


if __name__ == "__main__":
    unittest.main()
