@echo off
rem Stops RAOfflineProxy: the proxy (putting your emulators' settings back),
rem its tray icon and the menu. To remove it completely, turn off "Start with
rem Windows" in its Settings first, run this, then delete the folder.
"%~dp0python\python.exe" -m raofflineproxy.windows.launch --stop
