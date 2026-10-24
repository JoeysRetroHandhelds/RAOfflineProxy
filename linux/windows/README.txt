RAOfflineProxy for Windows (portable)

Earn RetroAchievements offline with RetroArch, Dolphin and PPSSPP: unlocks
earned without a connection are saved and synced once you're back online.

Start:   double-click "Start RAOfflineProxy.cmd". The first start finds your
         emulators. The proxy runs in the background with an icon by the clock;
         the menu works with a controller or keyboard.
Stop:    "Stop RAOfflineProxy.cmd", or right-click the tray icon.

Settings, cached games and pending awards are kept in the data folder here,
so you can move this folder, put it on a USB stick or copy it to another PC
(it finds that PC's emulators on the first start).

The only thing added to Windows is a sign-in check (a startup entry, or a
sign-in task once Start with Windows is on). After a crash or power cut it
starts the proxy again if it was running, and otherwise puts your emulator
settings back, so they never point at a proxy that isn't running.

Start with Windows (in Settings) still finds the folder if a USB stick comes
back with a different drive letter.

Updates install from the menu when a new version is out.

To remove: run Stop, choose Settings > "Remove from Windows sign-in", then
delete this folder.

Windows may warn the first time you run a .cmd from a downloaded zip
("Windows protected your PC"): choose More info, then Run anyway.

https://raofflineproxy.com
