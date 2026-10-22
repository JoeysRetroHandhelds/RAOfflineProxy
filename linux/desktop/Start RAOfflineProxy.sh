#!/usr/bin/env bash
# Starts RAOfflineProxy from this folder (checking for an update first) and
# points the detected emulators at it. Double-click it in the file manager.
cd "$(dirname "${BASH_SOURCE[0]}")/app" || exit 1
exec ../python/bin/python3 -m raofflineproxy.desktop.launch start
