# Pinned upstream image. The digest is multi-arch, so the same FROM line works
# for amd64 and aarch64. Do not replace it with :latest.
FROM ghcr.io/alams154/music-assistant-skill:0.0.39-beta@sha256:b1ef33ad0b05b7e0a315535e8141177898be4b6a0401decf43dedf424f0d90f1

LABEL org.opencontainers.image.title="Alexa MA Skill"
LABEL org.opencontainers.image.source="https://github.com/flaviocorrea13/alexa-skill"
LABEL org.opencontainers.image.url="https://github.com/flaviocorrea13/alexa-skill"

ENV DEBIAN_FRONTEND=noninteractive

# The upstream image does not include the timezone database. TZ is exposed as
# an add-on option, so install tzdata before the app starts.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY run.sh /run.sh
COPY addon_options.py /app/addon_options.py
RUN chmod +x /run.sh

ENV QUIET_HTTP=1
ENV PYTHONUNBUFFERED=1
ENV DEBUG_PORT=0

ENTRYPOINT ["/run.sh"]

# Setting ENTRYPOINT above clears the CMD inherited from the base image, so the
# original upstream CMD must be redeclared here. The fallback in run.sh is only
# a reserve for direct/manual invocations without arguments.
CMD ["/bin/sh", "-lc", "if [ -n \"${DEBUG_PORT}\" ] && [ \"${DEBUG_PORT}\" != \"0\" ]; then exec /app/venv/bin/python -m debugpy --listen 0.0.0.0:${DEBUG_PORT} src/app.py; else exec /app/venv/bin/python src/app.py; fi"]
