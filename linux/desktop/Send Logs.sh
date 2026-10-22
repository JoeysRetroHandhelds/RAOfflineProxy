#!/usr/bin/env bash
# Sends RAOfflineProxy's logs to the developer (test builds: to the test share).
cd "$(dirname "${BASH_SOURCE[0]}")/app" || exit 1
# The bundled Python; the system's only to finish an update from a build without one.
PYTHON=../python/bin/python3
[ -x "${PYTHON}" ] || PYTHON=python3
exec "${PYTHON}" -m raofflineproxy.desktop.launch send-logs
