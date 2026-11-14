#!/bin/sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -n "${CLUBATX_PHOTO_ENV_FILE:-}" ]; then
  exec node --env-file="$CLUBATX_PHOTO_ENV_FILE" "$SCRIPT_DIR/server.mjs"
fi
exec node "$SCRIPT_DIR/server.mjs"
