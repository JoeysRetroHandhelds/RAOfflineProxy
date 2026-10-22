#!/usr/bin/env bash
# Opens RAOfflineProxy's menu (controller, keyboard or mouse), full screen.
cd "$(dirname "${BASH_SOURCE[0]}")/app" || exit 1
exec ../python/bin/python3 -m raofflineproxy.main menu
