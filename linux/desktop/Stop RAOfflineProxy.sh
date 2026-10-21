#!/usr/bin/env bash
# Stops RAOfflineProxy and puts the emulator configs back the way they were.
cd "$(dirname "${BASH_SOURCE[0]}")/app" || exit 1
exec python3 -m raofflineproxy.desktop.launch stop
