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
    current_target="$(readlink /root/.ask || true)"
    if [ "$current_target" != "/data/ask" ]; then
        rm -f /root/.ask
        ln -s /data/ask /root/.ask
    fi
elif [ -d /root/.ask ]; then
    # Preserve credentials created before the symlink existed without
    # overwriting the persistent copy in /data/ask.
    cp -an /root/.ask/. /data/ask/ 2>/dev/null || true
    rm -rf /root/.ask
    ln -s /data/ask /root/.ask
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
