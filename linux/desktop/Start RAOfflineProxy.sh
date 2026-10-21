#!/usr/bin/env bash
# Starts RAOfflineProxy from this checkout with the system's python3 and points
# the detected emulators (Flatpak or regular installs) at it. For testing on
# desktop Linux; double-click it in the file manager.
set -u

LINUX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="${HOME}/.config/raofflineproxy/service.log"

show() {
  if command -v kdialog >/dev/null 2>&1; then
    kdialog --title "RAOfflineProxy" --msgbox "$1"
  elif command -v notify-send >/dev/null 2>&1; then
    notify-send "RAOfflineProxy" "$1"
  else
    printf '%s\n' "$1"
  fi
}

if ! command -v python3 >/dev/null 2>&1; then
  show "python3 was not found. Install Python 3 and try again."
  exit 1
fi

if output="$(cd "${LINUX_DIR}" && python3 -m raofflineproxy.main start-proxy 2>&1)"; then
  show "Proxy started.

${output}

Log: ${LOG}"
else
  show "Starting the proxy failed.

${output}

Log: ${LOG}"
  exit 1
fi
