# RAOfflineProxy for Windows

Experimental. Runs the shared `linux/raofflineproxy` package on Windows PCs and handhelds as a **portable folder**: an embeddable Python is bundled, nothing is installed, and settings and cache live in the folder.

Windows-only code is kept in its own modules, which the shared code only calls into when `sys.platform == "win32"`. Each is named `raofflineproxy/windows_*.py`:

- `windows_paths.py`: the portable folder and its `data/`, plus RetroArch, Dolphin and PPSSPP locations
- `windows_process.py`: process checks, detached start, graceful stop (Windows has no SIGTERM), exclusive port probe and `LockFileEx` file locks
- `windows_launch.py`: what the Start and Stop scripts run
- `windows_autostart.py`: Start with Windows, surviving a changed drive letter
- `windows_emulators.py` and `windows_emulators_menu.py`: emulator detection and the on/off screen
- `windows_menu.py` and its mixins (`windows_settings`, `windows_games`, `windows_account`, `windows_support`, `windows_status`, `windows_keyboard`, `windows_input`): the Android app's features on top of the shared SDL menu
- `windows_tray.py`: tray icon and notifications
- `windows_background.py`: Smart Cache as its own process
- `windows_history.py`: Awards History
- `windows_update.py`: in-app updates

## Using it

Unzip anywhere (a folder, or a USB stick), then:

- **Start RAOfflineProxy.cmd** starts the proxy, its tray icon and the menu. The first start finds the emulators. A folder copied from another PC finds this PC's emulators on its first start here, keeping its cache and settings.
- **Stop RAOfflineProxy.cmd** stops the proxy (putting the emulator configs back), the tray and the menu.

Settings, cached games, pending awards and history are kept in the folder's `data\`. To remove it: turn off Start with Windows, run Stop, then delete the folder.

**Start with Windows** (in Settings) adds a per-user sign-in entry (no admin). That entry runs a small launcher kept in `%LOCALAPPDATA%\RAOfflineProxy-autostart`, which finds the folder by the id in its `portable.txt`:

- it looks first where the folder last was, then at the same path on every other drive letter;
- a USB stick that comes back as a different drive still starts, and with the stick unplugged it does nothing;
- every start records the folder's location, so after moving the folder one manual start is enough.

Turning the setting off removes the entry and the launcher.

**Updates** install from the menu (or the tray's notice): the new zip's `app\`, `python\` and scripts replace the old ones in place, and `data\` and `portable.txt` are kept.

## Menu

The same SDL menu as the Linux handhelds, plus the Android app's screens: Emulators, Watched folders, Awards history, Settings, Help & about, and a status panel on the main screen.

- Use a gamepad (A to confirm, B to go back) or the keyboard (arrows, Enter and Esc).
- B on the main menu asks whether to minimize to the tray or exit completely; Settings can make either the default.
- It opens as a borderless window covering the primary monitor down to the taskbar, so Alt-Tab is instant and there's no display mode switch. For exclusive full screen, set `"menu_fullscreen": "exclusive"` in `data\config.json`.
- Controller calibration is skipped, because SDL already maps the A and B buttons the same way on every pad.

## Supported emulators

Tested with RetroArch and Dolphin. PPSSPP detection is in place but untested.

`windows_emulators.py` finds them the way the Android app lists installed ones, as far as Windows allows. It looks in:

- the installed-programs registry
- Start-menu and desktop shortcuts
- a shallow scan of Program Files, `%LOCALAPPDATA%\Programs`, Scoop, Desktop, Downloads, Documents and the top of each local drive, so portable copies such as `C:\Emulators\RetroArch-Win64` are found too

It then works out each emulator's config from where its exe is (portable or installed). The menu's Emulators screen turns each one on or off, re-runs detection, or browses to an exe it missed.

## Build

From Git Bash, with [zig](https://ziglang.org) on `PATH` (or `ZIG_BIN` set):

```bash
linux/windows/fetch_vendor.sh
linux/windows/build_bundle.sh
```

This produces `linux/windows/dist/RAOfflineProxy-Windows-v<version>.zip`, about 22 MB with Python and pygame included. On a Windows host, `build_rchash.sh` compiles each source separately, because zig's single compile-and-link run crashes there.

## Releases

The in-app updater offers a release when it has a `RAOfflineProxy-Windows-v<version>.zip` asset, so stable releases need that zip attached alongside the device bundles. Nightly builds include it already: `nightly.yml` cross-builds the bundle on Linux and publishes it with the Linux bundles, and nightly installs follow that release.
