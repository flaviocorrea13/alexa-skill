#!/usr/bin/env bash
set -euo pipefail
umask 077

cd /app

# Persist the ASK CLI credentials in /data/ask and expose them at the path the
# upstream image expects (~/.ask). Do not export ASK_CREDENTIALS_DIR: the
# upstream app resolves /root/.ask directly, and setting that variable would
# make it look for /data/.ask instead of the symlink target.
unset ASK_CREDENTIALS_DIR
mkdir -p /data/ask
chmod 700 /data/ask

if [ -L /root/.ask ]; then
    current_target="$(readlink -f /root/.ask || true)"
    if [ "$current_target" != "/data/ask" ]; then
        # A symlink to another legacy directory may still hold the only copy
        # of the credentials. Migrate it before replacing the symlink.
        if [ -n "$current_target" ] && [ -d "$current_target" ]; then
            if ! cp -an "$current_target"/. /data/ask/; then
                echo "ERROR: could not migrate legacy ASK credentials from $current_target; leaving /root/.ask untouched." >&2
                exit 1
            fi
        fi
        rm -f /root/.ask
        ln -s /data/ask /root/.ask
    fi
elif [ -d /root/.ask ]; then
    # Preserve credentials created before the symlink existed without
    # overwriting the persistent copy in /data/ask. If the migration fails,
    # stop and leave the legacy directory untouched instead of deleting the
    # only copy.
    if cp -an /root/.ask/. /data/ask/; then
        rm -rf /root/.ask
        ln -s /data/ask /root/.ask
    else
        echo "ERROR: could not migrate legacy /root/.ask to /data/ask; leaving the legacy directory in place." >&2
        exit 1
    fi
elif [ -e /root/.ask ]; then
    rm -f /root/.ask
    ln -s /data/ask /root/.ask
else
    ln -s /data/ask /root/.ask
fi

PYTHON_BIN=/app/venv/bin/python
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN=python3
fi

ENV_FILE="$(mktemp "${TMPDIR:-/tmp}/alexa-ma-skill-env.XXXXXX")"
cleanup() {
    rm -f "$ENV_FILE"
}
trap cleanup EXIT

"$PYTHON_BIN" /app/addon_options.py /data/options.json "$ENV_FILE"

while IFS= read -r -d '' assignment; do
    export "$assignment"
done < "$ENV_FILE"

# The file contains credentials. Remove it before replacing this shell with the
# application so it does not linger for the lifetime of the container.
rm -f "$ENV_FILE"
trap - EXIT

# Fixed runtime settings. These are intentionally not user options.
export HOST="${HOST:-0.0.0.0}"
export QUIET_HTTP="${QUIET_HTTP:-1}"
export FLASK_DEBUG="${FLASK_DEBUG:-0}"
export FLASK_RELOADER="${FLASK_RELOADER:-0}"
export PYTHONUNBUFFERED=1
export DEBUG_PORT="${DEBUG_PORT:-0}"

echo "Starting Alexa MA Skill (host=${SKILL_HOSTNAME:-<unset>}, locale=${LOCALE:-pt-BR}, port=${PORT:-5000})"

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

exec "$PYTHON_BIN" /app/src/app.py
