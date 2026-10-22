#!/usr/bin/env bash
# Opens RAOfflineProxy's menu (controller, keyboard or mouse), full screen.
cd "$(dirname "${BASH_SOURCE[0]}")/app" || exit 1
# The bundled Python; the system's only to finish an update from a build without one.
PYTHON=../python/bin/python3
[ -x "${PYTHON}" ] || PYTHON=python3
exec "${PYTHON}" -m raofflineproxy.main menu
