#!/usr/bin/env bash
set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required. Install it from https://cli.github.com/ and authenticate with 'gh auth login'." >&2
  exit 1
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <version tag> [--notes-file file | --notes \"text\"]" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAG="$1"
shift || true

"$ROOT_DIR/scripts/build_dmg.sh"

pushd "$ROOT_DIR" >/dev/null

REMOTE="${GIT_REMOTE:-origin}"

if ! git rev-parse "$TAG" >/dev/null 2>&1; then
  git tag "$TAG"
  if git remote get-url "$REMOTE" >/dev/null 2>&1; then
    git push "$REMOTE" "$TAG"
  else
    echo "Remote '$REMOTE' not found; skipping git push. Push the tag manually if needed." >&2
  fi
else
  echo "Tag $TAG already exists; skipping git tag creation."
fi

DMG_PATH="dist/Ramener.dmg"
APP_PATH="dist/Ramener.app"

if [[ ! -f "$DMG_PATH" ]]; then
  echo "Expected DMG at $DMG_PATH; build may have failed." >&2
  exit 1
fi

if gh release view "$TAG" >/dev/null 2>&1; then
  echo "GitHub release $TAG already exists; uploading assets."
  gh release upload "$TAG" "$DMG_PATH" "${APP_PATH}" --clobber
else
  gh release create "$TAG" "$DMG_PATH" "$APP_PATH" "$@" --title "$TAG"
fi

popd >/dev/null
