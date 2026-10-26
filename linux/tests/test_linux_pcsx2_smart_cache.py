import struct
import tempfile
import unittest
from pathlib import Path

from linux.raofflineproxy import smart_cache

# As PCSX2 pads it: serial, total seconds, last played (unix time).
PLAYTIME = """SCUS-97198                       19056                1772832948
SLUS-20219                       1199                 1774993783
SLUS-99999                       0                    0
SLUS-20927                       153                  1774994360
"""


def cache_entry(path: str, serial: str) -> bytes:
    def text(value: str) -> bytes:
        data = value.encode("utf-8")
        return struct.pack("<I", len(data)) + data

    return (
        text(path) + text(serial) + text("Title") + text("title") + text("Title (EN)")
        + struct.pack("<BBQQIB", 0, 1, 123, 456, 0xDEADBEEF, 5)
    )


def gamelist_cache(*entries: tuple[str, str], version: int = smart_cache.PCSX2_CACHE_VERSION) -> bytes:
    return struct.pack("<II", smart_cache.PCSX2_CACHE_SIGNATURE, version) + b"".join(
        cache_entry(path, serial) for path, serial in entries
    )


class Pcsx2RecentGamesTests(unittest.TestCase):
    def test_playtime_is_read_most_recent_first_skipping_never_played(self) -> None:
        self.assertEqual(
            smart_cache.parse_pcsx2_playtime(PLAYTIME), ["SLUS-20927", "SLUS-20219", "SCUS-97198"]
        )

    def test_the_cache_maps_serials_to_files(self) -> None:
        data = gamelist_cache(("C:/ps2/a.chd", "SLUS-20219"), ("C:/ps2/b.iso", "SCUS-97198"))
        self.assertEqual(
            smart_cache.parse_pcsx2_gamelist_cache(data),
            {"SLUS-20219": Path("C:/ps2/a.chd"), "SCUS-97198": Path("C:/ps2/b.iso")},
        )

    def test_an_unknown_cache_version_is_not_guessed_at(self) -> None:
        data = gamelist_cache(("C:/ps2/a.chd", "SLUS-20219"), version=99)
        self.assertEqual(smart_cache.parse_pcsx2_gamelist_cache(data), {})

    def test_a_truncated_cache_keeps_the_entries_before_the_damage(self) -> None:
        data = gamelist_cache(("C:/ps2/a.chd", "SLUS-20219"), ("C:/ps2/b.iso", "SCUS-97198"))
        self.assertEqual(list(smart_cache.parse_pcsx2_gamelist_cache(data[:-10])), ["SLUS-20219"])

    def test_recent_games_are_the_played_files_that_exist(self) -> None:
        root = Path(tempfile.mkdtemp())
        (root / "inis").mkdir()
        (root / "cache").mkdir()
        games = root / "games"
        games.mkdir()
        (games / "recent.chd").write_bytes(b"disc")
        (root / "inis" / "PCSX2.ini").write_text("[Achievements]\n", encoding="utf-8")
        (root / "inis" / "playtime.dat").write_text(PLAYTIME, encoding="utf-8")
        (root / "cache" / "gamelist.cache").write_bytes(gamelist_cache(
            (str(games / "recent.chd"), "SLUS-20927"),
            (str(games / "deleted.chd"), "SLUS-20219"),
        ))
        paths = smart_cache._load_pcsx2_recent_paths({"pcsx2_ini": str(root / "inis" / "PCSX2.ini")})
        self.assertEqual(paths, [games / "recent.chd"])

    def test_no_pcsx2_means_no_recent_games(self) -> None:
        self.assertEqual(smart_cache._load_pcsx2_recent_paths({"pcsx2_ini": "/nowhere/PCSX2.ini"}), [])


if __name__ == "__main__":
    unittest.main()
