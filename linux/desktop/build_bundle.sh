#!/usr/bin/env bash
# Builds the desktop Linux bundle: the shared raofflineproxy package (without
# the Windows code), libraproxy_rchash.so for x86_64, and the Start/Stop/Send
# Logs scripts, as dist/RAOfflineProxy-Desktop-v<version>.tar.gz. It runs on
# the system's python3. Needs zig (ZIG_BIN, default: zig on PATH).
#
# Usage:
#   linux/desktop/build_bundle.sh

set -euo pipefail

PYTHON="$(command -v python3 || command -v python)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LINUX_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION="${RAOFFLINEPROXY_APP_VERSION:-2.2.0-alpha1}"
DIST_DIR="${SCRIPT_DIR}/dist/RAOfflineProxy"
APP_DIR="${DIST_DIR}/app"
ARCHIVE="${SCRIPT_DIR}/dist/RAOfflineProxy-Desktop-v${VERSION}.tar.gz"

# glibc 2.17, so the library loads on any current distro.
TARGET="x86_64-linux-gnu.2.17" OUT_DIR="${SCRIPT_DIR}/native" ZIG_BIN="${ZIG_BIN:-zig}" \
  "${LINUX_DIR}/build_rchash.sh"

rm -rf "${DIST_DIR}"
mkdir -p "${APP_DIR}/lib"
cp -r "${LINUX_DIR}/raofflineproxy" "${APP_DIR}/raofflineproxy"
rm -rf "${APP_DIR}/raofflineproxy/windows"
find "${APP_DIR}" -name "__pycache__" -type d -prune -exec rm -rf {} +
find "${APP_DIR}/raofflineproxy" -maxdepth 1 -name "*.dll" -delete
if [ -n "${RAOFFLINEPROXY_APP_VERSION:-}" ]; then
  "${PYTHON}" - "${APP_DIR}/raofflineproxy/config.py" "${VERSION}" <<'EOF'
import re
import sys

path, version = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
text, count = re.subn(r'^(APP_VERSION = .* or )"[^"]*"$', rf'\1"{version}"', text, flags=re.M)
assert count == 1, "APP_VERSION line not found"
open(path, "w", encoding="utf-8", newline="\n").write(text)
EOF
fi
cp "${LINUX_DIR}/../docs/public/logo-320.png" "${APP_DIR}/raofflineproxy/logo-320.png"
# rom_hashing.py looks in ../lib next to the package.
cp "${SCRIPT_DIR}/native/libraproxy_rchash.so" "${APP_DIR}/lib/"

for script in "Start RAOfflineProxy.sh" "Stop RAOfflineProxy.sh" "Send Logs.sh" "README.txt"; do
  sed 's/\r$//' "${SCRIPT_DIR}/${script}" > "${DIST_DIR}/${script}"
done
# Marks the folder as the desktop bundle (config.desktop_bundle_root).
printf '%s\n' "This folder is a desktop RAOfflineProxy bundle. Keep this file: it marks the folder." \
  > "${DIST_DIR}/desktop.txt"
# Test builds only: send logs and updates to test destinations (desktop/paths.py, test_channel).
if [ -n "${RAOFFLINEPROXY_TEST_CHANNEL:-}" ]; then
  cp "${RAOFFLINEPROXY_TEST_CHANNEL}" "${DIST_DIR}/testing.json"
fi

# tarfile rather than tar, so the scripts are executable even when this is
# built on Windows (which has no file modes).
"${PYTHON}" - "${SCRIPT_DIR}/dist" "${ARCHIVE}" <<'EOF'
import sys
import tarfile
from pathlib import Path

dist, archive = Path(sys.argv[1]), sys.argv[2]


def modes(info):
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    if info.isdir() or info.name.endswith(".sh"):
        info.mode = 0o755
    else:
        info.mode = 0o644
    return info


with tarfile.open(archive, "w:gz") as bundle:
    bundle.add(dist / "RAOfflineProxy", arcname="RAOfflineProxy", filter=modes)
EOF

echo "Created ${DIST_DIR}"
echo "Created ${ARCHIVE}"
