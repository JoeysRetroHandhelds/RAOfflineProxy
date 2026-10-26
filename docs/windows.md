# Windows Setup

::: warning Experimental
Windows support is experimental. It is new and has had little testing, so expect rough edges.
:::

RAOfflineProxy for Windows is a **portable folder**: nothing is installed, and settings and cached games stay in the folder. It works with RetroArch, Dolphin, PCSX2 and PPSSPP (PPSSPP is untested).

## Setup

1. Download `RAOfflineProxy-Windows-*.zip` from [GitHub Releases](https://github.com/misantronic/RAOfflineProxy/releases)
2. Unzip it anywhere, for example a folder or a USB stick
3. Enter your RetroAchievements account details in your emulator
4. Double-click **Start RAOfflineProxy.cmd**. Windows may warn the first time: choose **More info**, then **Run anyway**
5. Start the proxy while online. The first start finds your emulators
6. Cache games with **Smart Cache** or by launching them once in your emulator

The proxy runs in the background with a tray icon. The menu works with a controller or the keyboard.

## Offline use

Launch a cached game and play. Unlocks are queued and sent when you are back online.

## Stop and remove

- **Stop RAOfflineProxy.cmd** stops the proxy and restores your emulator configs.
- To remove it: run Stop, choose **Settings > Remove from Windows sign-in**, then delete the folder.

Updates install from the menu when a new version is out. Hardcore mode is not supported.
