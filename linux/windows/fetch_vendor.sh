#!/usr/bin/env bash
# Downloads the Windows embeddable Python the bundle runs on, so the target
# machine needs no Python install, and the pygame wheel for the SDL menu.
#
# Usage:
#   linux/windows/fetch_vendor.sh

set -euo pipefail

# "python" first: on Windows, "python3" can be the Microsoft Store stub.
PYTHON="$(command -v python || command -v python3)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR_DIR="${SCRIPT_DIR}/vendor"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

PYTHON_VERSION="3.13.9"
PYGAME_VERSION="2.6.1"
ZIP_NAME="python-${PYTHON_VERSION}-embed-amd64.zip"

echo "Fetching embeddable Python ${PYTHON_VERSION} (amd64)..."
curl -fsSL -o "${TMP_DIR}/${ZIP_NAME}" "https://www.python.org/ftp/python/${PYTHON_VERSION}/${ZIP_NAME}"

rm -rf "${VENDOR_DIR}/python"
mkdir -p "${VENDOR_DIR}/python"
unzip -q "${TMP_DIR}/${ZIP_NAME}" -d "${VENDOR_DIR}/python"

echo "Fetching pygame ${PYGAME_VERSION} (cp313, win_amd64)..."
"${PYTHON}" -m pip download "pygame==${PYGAME_VERSION}" \
    --platform win_amd64 \
    --python-version 313 \
    --only-binary :all: \
    --no-deps \
    -d "${TMP_DIR}" \
    -q

# A wheel is a zip; its pygame/ package carries SDL2 and friends as DLLs.
rm -rf "${VENDOR_DIR}/site"
mkdir -p "${VENDOR_DIR}/site"
unzip -q "${TMP_DIR}"/pygame-*.whl -d "${VENDOR_DIR}/site"
rm -rf "${VENDOR_DIR}/site"/*.dist-info "${VENDOR_DIR}/site"/*.data

echo "Created ${VENDOR_DIR}/python and ${VENDOR_DIR}/site"
