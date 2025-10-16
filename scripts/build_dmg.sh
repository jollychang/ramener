#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC_FILE="$ROOT_DIR/packaging/ramener.spec"
DIST_DIR="$ROOT_DIR/dist"
BUILD_DIR="$ROOT_DIR/build"
PYINSTALLER_CMD="${PYINSTALLER:-pyinstaller}"
export RAMENER_PROJECT_ROOT="$ROOT_DIR"

ICON_PNG="$ROOT_DIR/packaging/ramener.png"
ICON_ICNS="$ROOT_DIR/packaging/ramener.icns"
PYTHON_CMD="${PYTHON_CMD:-python3}"

if ! command -v "$PYINSTALLER_CMD" >/dev/null 2>&1; then
  echo "PyInstaller is required. Install it with: pip install pyinstaller" >&2
  exit 1
fi

if [[ ! -f "$ICON_ICNS" ]]; then
  if [[ -f "$ICON_PNG" ]]; then
    if command -v "$PYTHON_CMD" >/dev/null 2>&1; then
      "$PYTHON_CMD" "$ROOT_DIR/scripts/make_icns.py"
    else
      echo "Cannot find python executable for icon conversion. Set PYTHON_CMD." >&2
      exit 1
    fi
  else
    echo "Missing icon artwork at $ICON_PNG" >&2
    exit 1
  fi
fi

rm -rf "$DIST_DIR" "$BUILD_DIR"

"$PYINSTALLER_CMD" \
  --clean \
  --distpath "$DIST_DIR" \
  --workpath "$BUILD_DIR" \
  "$SPEC_FILE"

APP_PATH="$DIST_DIR/Ramener.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "Expected app bundle not found at $APP_PATH" >&2
  exit 1
fi

STAGING_DIR="$DIST_DIR/dmg-staging"
DMG_PATH="$DIST_DIR/Ramener.dmg"
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"
cp -R "$APP_PATH" "$STAGING_DIR/"
ln -sf /Applications "$STAGING_DIR/Applications"

if command -v hdiutil >/dev/null 2>&1; then
  hdiutil create \
    -volname "Ramener" \
    -srcfolder "$STAGING_DIR" \
    -ov \
    -format UDZO \
    "$DMG_PATH"
  echo "DMG created at $DMG_PATH"
else
  echo "hdiutil not available. Skipping DMG creation; app bundle at $APP_PATH" >&2
fi
