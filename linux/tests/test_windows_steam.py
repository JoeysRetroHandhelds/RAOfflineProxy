import sys
from pathlib import Path

import pytest

from linux.raofflineproxy import windows_steam as steam

# A shortcuts.vdf as Steam writes it, with one other non-Steam game.
EXISTING = (
    b"\x00shortcuts\x00\x000\x00\x02appid\x00\xef\xed\xf4\xd7\x01appname\x00VPX-Launcher\x00"
    b'\x01Exe\x00"C:\\Visual Pinball\\VPX-Launcher.exe"\x00\x01StartDir\x00C:\\Visual Pinball\\\x00'
    b"\x01icon\x00\x00\x01LaunchOptions\x00\x00\x02IsHidden\x00\x00\x00\x00\x00"
    b"\x02LastPlayTime\x00P\xe7\xefi\x00tags\x00\x08\x08\x08\x08"
)


def test_round_trip_keeps_file_byte_for_byte():
    assert steam.write_vdf(steam.parse_vdf(EXISTING)) == EXISTING


def test_damaged_file_raises_value_error():
    with pytest.raises(ValueError):
        steam.parse_vdf(EXISTING[:40])


def test_adds_entry_and_keeps_others():
    data = steam.parse_vdf(EXISTING)
    root = Path(r"E:\Games\RAOfflineProxy")
    app_id = steam.upsert_shortcut(data, root, None)
    table = data["shortcuts"]
    assert table["0"]["appname"] == "VPX-Launcher"
    ours = table["1"]
    assert ours["appname"] == "RAOfflineProxy"
    assert ours["Exe"] == r'"E:\Games\RAOfflineProxy\python\pythonw.exe"'
    assert ours["StartDir"] == r'"E:\Games\RAOfflineProxy"'
    assert ours["LaunchOptions"] == steam.LAUNCH_OPTIONS
    assert ours["appid"] & 0xFFFFFFFF == app_id
    assert app_id & 0x80000000
    # Written and read back, it's still the same data.
    assert steam.parse_vdf(steam.write_vdf(data)) == data


def test_moved_folder_updates_the_same_entry():
    data = steam.parse_vdf(EXISTING)
    steam.upsert_shortcut(data, Path(r"E:\Games\RAOfflineProxy"), None)
    steam.upsert_shortcut(data, Path(r"F:\Games\RAOfflineProxy"), None)
    table = data["shortcuts"]
    assert len(table) == 2
    assert table["1"]["Exe"].startswith('"F:')


@pytest.mark.skipif(sys.platform != "win32", reason="Steam accounts are read from the Windows registry layout")
def test_add_to_steam_writes_backup_and_artwork(tmp_path):
    pygame = pytest.importorskip("pygame")
    userdata = tmp_path / "userdata" / "123"
    (userdata / "config").mkdir(parents=True)
    (userdata / "config" / "shortcuts.vdf").write_bytes(EXISTING)
    logo = tmp_path / "logo.png"
    pygame.image.save(pygame.Surface((320, 120)), str(logo))

    account = steam.SteamAccount("123", "Tester", userdata)
    steam.add_to_steam(account, Path(r"E:\Games\RAOfflineProxy"), None, logo)

    config = userdata / "config"
    assert (config / "shortcuts.vdf.raofflineproxy-backup").read_bytes() == EXISTING
    data = steam.parse_vdf((config / "shortcuts.vdf").read_bytes())
    app_id = data["shortcuts"]["1"]["appid"] & 0xFFFFFFFF
    for name in (f"{app_id}p.png", f"{app_id}.png", f"{app_id}_hero.png", f"{app_id}_logo.png"):
        assert (config / "grid" / name).exists()


def test_accounts_reads_names_and_skips_placeholder(tmp_path):
    (tmp_path / "userdata" / "12345").mkdir(parents=True)
    (tmp_path / "userdata" / "0").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "loginusers.vdf").write_text(
        '"users"\n{\n\t"76561197960278073"\n\t{\n\t\t"PersonaName"\t\t"Player"\n\t}\n}\n', encoding="utf-8"
    )
    found = steam.accounts(tmp_path)
    assert [(a.account_id, a.name) for a in found] == [("12345", "Player")]
