"""Diagnostics support for the Alexa MA Skill integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .api import DetailedStatus
from .const import CONF_MA_API_TOKEN, CONF_PASSWORD, DOMAIN
from .coordinator import AlexaMaSkillData
from .supervisor import SupervisorOperationError, SupervisorUnavailableError
from .util import html_to_text, redact_stream_urls

TO_REDACT = {
    CONF_PASSWORD,
    CONF_MA_API_TOKEN,
    "password",
    "APP_PASSWORD",
    "MA_API_TOKEN",
    "token",
    "access_token",
    "refresh_token",
    "streamUrl",
    "stream_url",
    "audioSources",
}


def _clean_text(value: str) -> str:
    """Strip HTML and redact stream URLs from diagnostics text."""
    return redact_stream_urls(html_to_text(value))


def _detailed_data(detailed: DetailedStatus | None) -> dict[str, Any] | None:
    """Return sanitized detailed status data."""
    if detailed is None:
        return None
    return {
        "skill_html": _clean_text(detailed.skill_html),
        "skill_ask_html": _clean_text(detailed.skill_ask_html),
        "ma_api_html": _clean_text(detailed.ma_api_html),
        "alexa_api_html": _clean_text(detailed.alexa_api_html),
        "metadata_html": _clean_text(detailed.metadata_html),
        "invocations_html": _clean_text(detailed.invocations_html),
        "skill_ask_level": detailed.skill_ask_level.value,
        "ma_api_level": detailed.ma_api_level.value,
        "alexa_api_level": detailed.alexa_api_level.value,
        "ma_api_details": detailed.ma_api_details,
        "stream_url": detailed.stream_url,
    }


def _coordinator_data(data: AlexaMaSkillData | None) -> dict[str, Any] | None:
    """Return sanitized coordinator data."""
    if data is None:
        return None
    return {
        "reachable": data.reachable,
        "http_status": data.http_status,
        "last_check": data.last_check.isoformat() if data.last_check else None,
        "detailed_error": data.detailed_error,
        "container_online": data.container_online,
        "addon_version": data.addon_version,
        "https_skill_ok": data.https_skill_ok,
        "https_stream_ok": data.https_stream_ok,
        "stream_url_present": data.stream_url_present,
        "detailed": _detailed_data(data.detailed),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    coordinator = runtime.coordinator if runtime is not None else None
    diagnostics: dict[str, Any] = {
        "entry": {
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "coordinator": _coordinator_data(
            coordinator.data if coordinator is not None else None
        ),
        "addon": None,
    }

    if runtime is not None:
        supervisor = runtime.supervisor
        if supervisor.available:
            try:
                info = await supervisor.async_get_info()
            except (
                SupervisorOperationError,
                SupervisorUnavailableError,
            ) as err:
                diagnostics["addon"] = {
                    "available": True,
                    "error": type(err).__name__,
                }
            else:
                diagnostics["addon"] = {
                    "available": True,
                    "hostname": info.hostname,
                    "version": info.version,
                    "state": getattr(info.state, "value", str(info.state)),
                    "options": dict(info.options),
                }
        else:
            diagnostics["addon"] = {"available": False}

    return async_redact_data(diagnostics, TO_REDACT)
