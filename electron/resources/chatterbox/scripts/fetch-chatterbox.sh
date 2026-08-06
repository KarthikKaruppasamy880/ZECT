#!/usr/bin/env bash
# Download a private Chatterbox sidecar zip into bin/.
#   export CHATTERBOX_BUNDLE_URL=https://your-artifacts/chatterbox-linux-x64.zip
#   bash electron/resources/chatterbox/scripts/fetch-chatterbox.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/bin"
URL="${CHATTERBOX_BUNDLE_URL:-}"
if [[ -z "$URL" ]]; then
  echo "CHATTERBOX_BUNDLE_URL is not set."
  echo "Manually copy the engine binary into: $BIN"
  exit 1
fi
mkdir -p "$BIN"
TMP="$(mktemp -d)"
curl -L "$URL" -o "$TMP/bundle.zip"
unzip -o "$TMP/bundle.zip" -d "$BIN"
rm -rf "$TMP"
echo "Done. Bin contents:"
ls -la "$BIN"
