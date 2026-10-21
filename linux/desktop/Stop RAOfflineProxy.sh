#!/usr/bin/env bash
# Stops RAOfflineProxy and puts the emulator configs back the way they were.
set -u

LINUX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

show() {
  if command -v kdialog >/dev/null 2>&1; then
    kdialog --title "RAOfflineProxy" --msgbox "$1"
  elif command -v notify-send >/dev/null 2>&1; then
    notify-send "RAOfflineProxy" "$1"
  else
    printf '%s\n' "$1"
  fi
}

if output="$(cd "${LINUX_DIR}" && python3 -m raofflineproxy.main stop-proxy 2>&1)"; then
  show "Proxy stopped.

${output}"
else
  show "Stopping the proxy failed.

${output}"
  exit 1
fi
