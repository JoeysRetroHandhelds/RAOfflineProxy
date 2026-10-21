#!/usr/bin/env bash
# Turns "Start RAOfflineProxy automatically when you sign in" on or off.
cd "$(dirname "${BASH_SOURCE[0]}")/app" || exit 1
exec python3 -m raofflineproxy.desktop.launch autostart
