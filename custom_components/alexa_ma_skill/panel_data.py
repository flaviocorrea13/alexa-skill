"""Sanitized data for the Alexa MA admin panel."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import (
    CONF_ADDON_SLUG,
    CONF_MA_API_URL,
    CONF_MANAGED,
    CONF_SKILL_HOSTNAME,
    CONF_SKILL_ID,
    DOMAIN,
    StatusLevel,
)
from .coordinator import AlexaMaSkillData
from .setup import build_setup_checklist
from .util import (
    entry_config,
    html_to_text,
    mask_skill_identifier,
    mask_skill_ids_in_text,
    redact_stream_urls,
    skill_linked,
)

_LOGGER = logging.getLogger(__name__)

STALE_AFTER = timedelta(minutes=10)
_MAX_TEXT = 240
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


class PanelError(Exception):
    """Base error for panel data requests."""

    code = "internal_error"


class PanelNotLoaded(PanelError):
    """No loaded Alexa MA config entry is available."""

    code = "not_loaded"


class PanelEntryRequired(PanelError):
    """More than one entry is loaded and no entry_id was selected."""

    code = "entry_required"


class PanelEntryNotFound(PanelError):
    """The requested entry is not loaded."""

    code = "entry_not_found"


def _safe_text(value: Any) -> str | None:
    """Return short text without stream URLs, HTML, or full skill IDs."""
    if value is None:
        return None
    text = mask_skill_ids_in_text(redact_stream_urls(html_to_text(str(value))))
    text = _URL_RE.sub("[url]", text)
    text = " ".join(text.split())
    return text[:_MAX_TEXT] or None


def _safe_title(value: str) -> str:
    """Mask skill IDs that a config entry title may accidentally contain."""
    return mask_skill_ids_in_text(value or "")


def _runtime_entries(hass: HomeAssistant) -> dict[str, tuple[ConfigEntry, Any]]:
    """Return loaded config entries and their runtime data."""
    runtime_data = hass.data.get(DOMAIN, {})
    entries: dict[str, tuple[ConfigEntry, Any]] = {}
    for entry in hass.config_entries.async_entries(DOMAIN):
        runtime = runtime_data.get(entry.entry_id)
        if runtime is None or not hasattr(runtime, "coordinator"):
            continue
        entries[entry.entry_id] = (entry, runtime)
    return entries


def build_entries(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Return the safe list of loaded entries."""
    entries = []
    for entry, _runtime in _runtime_entries(hass).values():
        config = entry_config(entry)
        managed = bool(config.get(CONF_MANAGED, False))
        entries.append(
            {
                "entry_id": entry.entry_id,
                "title": _safe_title(entry.title),
                "managed": managed,
                "addon_slug": (
                    str(config.get(CONF_ADDON_SLUG) or "") or None if managed else None
                ),
            }
        )
    return sorted(entries, key=lambda item: (item["title"], item["entry_id"]))


def resolve_entry(hass: HomeAssistant, entry_id: str | None) -> tuple[ConfigEntry, Any]:
    """Resolve an explicit or implicit loaded entry."""
    entries = _runtime_entries(hass)
    if entry_id:
        resolved = entries.get(entry_id)
        if resolved is None:
            raise PanelEntryNotFound
        return resolved
    if not entries:
        raise PanelNotLoaded
    if len(entries) > 1:
        raise PanelEntryRequired
    return next(iter(entries.values()))


async def async_integration_version(hass: HomeAssistant) -> str | None:
    """Return the loaded integration version, when available."""
    try:
        integration = await async_get_integration(hass, DOMAIN)
    except Exception:  # noqa: BLE001 - version is informative only
        return None
    version = getattr(integration, "version", None)
    return str(version) if version else None


def build_addon_summary(runtime: Any, data: AlexaMaSkillData | None) -> dict[str, Any]:
    """Return a safe add-on summary without options or secrets.

    The values come from the coordinator snapshot, which already queried the
    Supervisor during the last poll. This keeps ``overview`` and ``refresh``
    free of extra Supervisor traffic.
    """
    supervisor = getattr(runtime, "supervisor", None)
    available = bool(
        supervisor is not None
        and getattr(supervisor, "available", False)
        and getattr(supervisor, "manager_ready", False)
    )
    installed = data.addon_installed if data is not None else None
    running = data.container_online if data is not None else None

    state: str | None = None
    if installed is False:
        state = "not_installed"
    elif installed is True:
        state = "running" if running else "not_running"

    return {
        "available": available,
        "installed": installed,
        "running": running,
        "state": state,
        "version": data.addon_version if data is not None else None,
        "hostname": data.addon_hostname if data is not None else None,
        "error": None if available else "supervisor_unavailable",
    }


def _overview_state(
    config: dict[str, Any],
    data: AlexaMaSkillData | None,
    runtime: Any,
    addon: dict[str, Any],
) -> tuple[str, str]:
    """Return the primary panel state and a non-secret reason code."""
    if data is None:
        return "error", "no_data"
    if addon.get("installed") is False:
        return "addon_not_found", "addon_not_installed"
    if addon.get("installed") is True and addon.get("running") is False:
        return "addon_stopped", "addon_not_running"
    if not data.reachable:
        return "error", "addon_unreachable"
    if data.detailed is not None and data.detailed.ma_api_level is StatusLevel.RED:
        return "ma_unavailable", "ma_api_unavailable"
    if not str(config.get(CONF_SKILL_HOSTNAME) or "").strip():
        return "config_incomplete", "skill_hostname_missing"
    if (
        bool(config.get(CONF_MANAGED, False))
        and not str(config.get(CONF_SKILL_ID) or "").strip()
    ):
        return "config_incomplete", "skill_id_missing"
    coordinator = runtime.coordinator
    if data.detailed_error or not coordinator.last_update_success:
        return "error", "status_error"
    if data.https_skill_ok is False:
        return "error", "https_skill_unreachable"
    return "connected", "ok"


def build_overview_payload(
    hass: HomeAssistant,
    entry: ConfigEntry,
    runtime: Any,
    addon: dict[str, Any],
    version: str | None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build the allowlisted overview payload."""
    data: AlexaMaSkillData | None = runtime.coordinator.data
    config = entry_config(entry)
    current = now or datetime.now(UTC)
    state, reason = _overview_state(config, data, runtime, addon)

    last_check = data.last_check if data is not None else None
    stale = bool(last_check is not None and current - last_check > STALE_AFTER)

    music_assistant = {
        "configured": bool(str(config.get(CONF_MA_API_URL) or "").strip()),
        "level": (
            data.detailed.ma_api_level.value
            if data is not None and data.detailed is not None
            else "unknown"
        ),
        "stream_present": bool(data.stream_url_present) if data else False,
        "stream_https_ok": bool(data.https_stream_ok) if data else False,
    }

    configured_skill_id = str(config.get(CONF_SKILL_ID) or "").strip()
    detected_skill_id = data.detected_skill_id if data is not None else None
    # The coordinator only sets ``suggested_skill_id`` to the detected ID when
    # the configured one is missing or different, so the masked detected ID
    # already carries that value. A boolean keeps the hint without duplicating
    # the identifier in the payload.
    skill_id_suggested = None if data is None else data.suggested_skill_id is not None

    alexa: dict[str, Any] = {
        "configured": bool(configured_skill_id),
        "configured_skill_id_masked": mask_skill_identifier(configured_skill_id),
        "detected_skill_id_masked": mask_skill_identifier(detected_skill_id),
        "skill_id_suggested": skill_id_suggested,
        "skill_id_matches": data.skill_id_matches if data is not None else None,
        "skill_linked": None,
        "skill_found": None,
        "endpoint_matches": None,
        "testing_enabled": None,
    }

    checklist: dict[str, Any] | None = None
    warnings: list[str] = []
    if data is not None:
        _checklist_state, attributes = build_setup_checklist(
            config,
            data,
            getattr(hass.config, "language", "en"),
            getattr(getattr(runtime, "checklist", None), "confirmations", {}),
        )
        progress = attributes.get("progress") or {}
        checklist = {
            "done": progress.get("done", 0),
            "pending": progress.get("pending", 0),
            "blocked": progress.get("blocked", 0),
            "attention": progress.get("attention", 0),
            "applicable": progress.get("applicable", 0),
            "total": progress.get("total", 0),
            "percent": progress.get("percent", 0),
            "complete": bool(progress.get("complete", False)),
            "next_step": progress.get("next_step"),
            "next_step_title": _safe_text(progress.get("next_step_title")),
        }
        alexa["skill_linked"] = skill_linked(
            data.detailed.skill_ask_html if data.detailed else "",
            data.detailed.skill_ask_level if data.detailed else StatusLevel.UNKNOWN,
        )
        alexa["skill_found"] = attributes.get("skill_found")
        alexa["endpoint_matches"] = attributes.get("endpoint_matches")
        alexa["testing_enabled"] = attributes.get("testing_enabled")
        warnings = [
            value
            for value in (_safe_text(item) for item in attributes.get("warnings", []))
            if value
        ]

    error = _safe_text(data.detailed_error if data is not None else None)
    if error:
        warnings.insert(0, error)

    return {
        "entry": {
            "entry_id": entry.entry_id,
            "title": _safe_title(entry.title),
            "managed": bool(config.get(CONF_MANAGED, False)),
        },
        "generated_at": current.isoformat(),
        "state": state,
        "reason": reason,
        "stale": stale,
        "integration": {
            "version": version,
            "loaded": True,
            "reachable": bool(data.reachable) if data is not None else False,
            "last_check": last_check.isoformat() if last_check else None,
            "last_update_success": bool(runtime.coordinator.last_update_success),
            "error": error,
        },
        "addon": addon,
        "music_assistant": music_assistant,
        "alexa": alexa,
        "checklist": checklist,
        "warnings": warnings[:5],
    }


async def async_build_overview(
    hass: HomeAssistant, entry_id: str | None
) -> dict[str, Any]:
    """Resolve one entry and return its sanitized overview."""
    entry, runtime = resolve_entry(hass, entry_id)
    data: AlexaMaSkillData | None = runtime.coordinator.data
    addon = build_addon_summary(runtime, data)
    version = await async_integration_version(hass)
    return build_overview_payload(hass, entry, runtime, addon, version)
