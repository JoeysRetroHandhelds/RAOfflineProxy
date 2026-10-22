#!/usr/bin/env bash
# Starts RAOfflineProxy from this folder (checking for an update first) and
# points the detected emulators at it. Double-click it in the file manager.
cd "$(dirname "${BASH_SOURCE[0]}")/app" || exit 1
# The bundled Python; the system's only to finish an update from a build without one.
PYTHON=../python/bin/python3
[ -x "${PYTHON}" ] || PYTHON=python3
exec "${PYTHON}" -m raofflineproxy.desktop.launch start
