#!/usr/bin/env bash
# Sends RAOfflineProxy's logs to the developer (test builds: to the test share).
cd "$(dirname "${BASH_SOURCE[0]}")/app" || exit 1
exec python3 -m raofflineproxy.desktop.launch send-logs
