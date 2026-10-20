@echo off
rem Starts RAOfflineProxy from this folder: the proxy, its tray icon and the menu.
rem Nothing is installed; settings and cached games are kept in data\ here.
start "" "%~dp0python\pythonw.exe" -m raofflineproxy.windows.launch
