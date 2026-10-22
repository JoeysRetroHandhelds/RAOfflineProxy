#!/usr/bin/env bash
# Downloads what the desktop bundle runs on, so the machine's own Python (any
# version, or none) doesn't matter: a standalone CPython for x86_64 Linux, from
# python-build-standalone, checked against its published SHA256SUMS, and the
# pygame wheel for the SDL menu.
#
# The CPython archive is kept as it is: build_bundle.sh copies its entries into
# the bundle, so its symlinks survive even when building on Windows.
#
# Usage:
#   linux/desktop/fetch_vendor.sh

set -euo pipefail

PYTHON="$(command -v python3 || command -v python)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR_DIR="${SCRIPT_DIR}/vendor"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

PBS_RELEASE="20261003"
PYTHON_VERSION="3.13.16"
PYGAME_VERSION="2.6.1"
ARCHIVE="cpython-${PYTHON_VERSION}+${PBS_RELEASE}-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"
BASE_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_RELEASE}"

mkdir -p "${VENDOR_DIR}"
echo "Fetching standalone CPython ${PYTHON_VERSION} (${PBS_RELEASE}, x86_64 Linux)..."
curl -fsSL -o "${TMP_DIR}/${ARCHIVE}" "${BASE_URL}/${ARCHIVE}"
curl -fsSL -o "${TMP_DIR}/SHA256SUMS" "${BASE_URL}/SHA256SUMS"
expected="$(grep " ${ARCHIVE}\$" "${TMP_DIR}/SHA256SUMS" | cut -d' ' -f1)"
actual="$("${PYTHON}" -c 'import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "${TMP_DIR}/${ARCHIVE}")"
if [ -z "${expected}" ] || [ "${expected}" != "${actual}" ]; then
  echo "Checksum mismatch for ${ARCHIVE}" >&2
  exit 1
fi
mv "${TMP_DIR}/${ARCHIVE}" "${VENDOR_DIR}/python.tar.gz"

echo "Fetching pygame ${PYGAME_VERSION} (cp313, manylinux x86_64)..."
"${PYTHON}" -m pip download "pygame==${PYGAME_VERSION}" \
    --platform manylinux2014_x86_64 \
    --python-version 313 \
    --only-binary :all: \
    --no-deps \
    -d "${TMP_DIR}" \
    -q

# A wheel is a zip; its pygame/ package and pygame.libs/ carry SDL2 and friends.
rm -rf "${VENDOR_DIR}/site"
mkdir -p "${VENDOR_DIR}/site"
"${PYTHON}" -m zipfile -e "${TMP_DIR}"/pygame-*.whl "${VENDOR_DIR}/site"
rm -rf "${VENDOR_DIR}/site"/*.dist-info "${VENDOR_DIR}/site"/*.data

echo "Created ${VENDOR_DIR}/python.tar.gz and ${VENDOR_DIR}/site"
