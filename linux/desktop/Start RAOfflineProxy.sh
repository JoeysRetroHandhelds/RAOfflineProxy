#!/usr/bin/env bash
# Starts RAOfflineProxy from this folder (checking for an update first) and
# points the detected emulators at it. Double-click it in the file manager.
cd "$(dirname "${BASH_SOURCE[0]}")/app" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  message="python3 was not found. Install Python 3 and try again."
  kdialog --title RAOfflineProxy --error "${message}" 2>/dev/null || notify-send RAOfflineProxy "${message}" 2>/dev/null || echo "${message}"
  exit 1
fi
exec python3 -m raofflineproxy.desktop.launch start
