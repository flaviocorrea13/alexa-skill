"""Constants for the Alexa MA Skill integration."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum

from homeassistant.const import Platform

DOMAIN = "alexa_ma_skill"
NAME = "Alexa MA Skill"

ADDON_NAME = "Alexa MA Skill"
ADDON_SLUG = "alexa_ma_skill"

CONF_MANAGED = "managed"
CONF_BASE_URL = "base_url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SKILL_HOSTNAME = "skill_hostname"
CONF_MA_HOSTNAME = "ma_hostname"
CONF_LOCALE = "locale"
CONF_ENABLE_APL = "enable_apl"
CONF_SKIP_URL_VALIDATION = "skip_url_validation"
CONF_SKILL_ID = "skill_id"
CONF_MA_API_URL = "ma_api_url"
CONF_MA_API_TOKEN = "ma_api_token"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_IGNORE_HTTPS = "ignore_https"

DEFAULT_HOST = "alexa-ma-skill"
DEFAULT_PORT = 5000
DEFAULT_BASE_URL = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}"
DEFAULT_LOCALE = "pt-BR"
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 300

DETAILED_SCAN_INTERVAL = timedelta(minutes=5)
REQUEST_TIMEOUT = 10
DETAILED_REQUEST_TIMEOUT = 30

ADDON_START_TIMEOUT = 90
ADDON_START_POLL_INTERVAL = 2

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

ALLOWED_LOCALES = (
    "pt-BR",
    "en-US",
    "en-GB",
    "en-AU",
    "en-CA",
    "en-IN",
    "de-DE",
    "es-ES",
    "es-MX",
    "fr-FR",
    "fr-CA",
    "it-IT",
    "nl-NL",
)


class StatusLevel(StrEnum):
    """Status LED levels reported by the add-on status page."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    UNKNOWN = "unknown"
