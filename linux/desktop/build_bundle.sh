#!/usr/bin/env bash
# Builds the desktop Linux bundle: a standalone CPython and pygame (from
# fetch_vendor.sh, so the machine's own Python doesn't matter), the shared
# raofflineproxy package (without the Windows code), libraproxy_rchash.so for
# x86_64, and the scripts, as dist/RAOfflineProxy-Desktop-v<version>.tar.gz.
# Run fetch_vendor.sh once first. Needs zig (ZIG_BIN, default: zig on PATH).
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

if [ ! -f "${SCRIPT_DIR}/vendor/python.tar.gz" ] || [ ! -d "${SCRIPT_DIR}/vendor/site/pygame" ]; then
  echo "Missing vendor/: run ${SCRIPT_DIR}/fetch_vendor.sh first" >&2
  exit 1
fi

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
# pygame next to the package: python -m from app/ finds it there.
cp -R "${SCRIPT_DIR}/vendor/site/." "${APP_DIR}/"

for script in "Open Menu.sh" "Start RAOfflineProxy.sh" "Stop RAOfflineProxy.sh" "Send Logs.sh" "Start Automatically.sh" "README.txt"; do
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
"${PYTHON}" - "${SCRIPT_DIR}/dist" "${ARCHIVE}" "${SCRIPT_DIR}/vendor/python.tar.gz" <<'EOF'
import sys
import tarfile
from pathlib import Path

dist, archive, python_archive = Path(sys.argv[1]), sys.argv[2], sys.argv[3]


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
    # CPython straight from its archive (python/bin/python3 and so on), with its
    # own modes and symlinks, which a checkout on Windows couldn't hold.
    with tarfile.open(python_archive, "r:gz") as runtime:
        for member in runtime.getmembers():
            if member.name != "python" and not member.name.startswith("python/"):
                continue
            source = runtime.extractfile(member) if member.isfile() else None
            member.name = "RAOfflineProxy/" + member.name
            if member.islnk():  # hard links name their target by its path in the archive
                member.linkname = "RAOfflineProxy/" + member.linkname
            member.uid = member.gid = 0
            member.uname = member.gname = ""
            bundle.addfile(member, source)
EOF

echo "Created ${DIST_DIR}"
echo "Created ${ARCHIVE}"
