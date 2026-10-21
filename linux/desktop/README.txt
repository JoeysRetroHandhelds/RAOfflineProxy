RAOfflineProxy for desktop Linux (experimental)
================================================

For SteamOS, Anatase and other Linux distros, with RetroArch, Dolphin or
PPSSPP installed as Flatpaks (Discover, EmuDeck) or regular packages.

Needs Python 3 (most distros include it).

Start RAOfflineProxy.sh   Checks for an update, starts the proxy and points
                          your emulators at it. Close the emulators first.
Stop RAOfflineProxy.sh    Stops the proxy and restores the emulator configs.
Send Logs.sh              Sends the logs to the developer, for bug reports.
Start Automatically.sh    Turns starting at sign-in (Desktop and Game Mode) on or off.

The first Start asks whether to start automatically. Either way, a small
sign-in service (a systemd user service, no admin rights) checks the emulators
at every sign-in, so a crash or reboot never leaves them pointing at a proxy
that isn't running: it starts the proxy again if it should be on, and
otherwise puts the emulator settings back.

Double-click a script in the file manager to run it. If it opens in a text
editor instead: right-click it, Properties, Permissions, tick "Is executable".

Settings, cached games and pending awards are kept in the data folder here,
and updates keep it.
