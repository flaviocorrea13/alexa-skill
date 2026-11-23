"""The Alexa MA Skill integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.storage import Store

from .api import AlexaMaSkillApi
from .const import (
    CONF_ADDON_SLUG,
    CONF_BASE_URL,
    CONF_IGNORE_HTTPS,
    CONF_MA_HOSTNAME,
    CONF_MANAGED,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_SKILL_HOSTNAME,
    CONF_SKILL_ID,
    CONF_USERNAME,
    DEFAULT_BASE_URL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    PLATFORMS,
    STORAGE_VERSION,
)
from .coordinator import AlexaMaSkillCoordinator
from .setup import ChecklistManager
from .supervisor import (
    AlexaMaSkillSupervisor,
    SupervisorOperationError,
    SupervisorUnavailableError,
    addon_hostname,
)
from .util import entry_config

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class AlexaMaSkillRuntimeData:
    """Runtime data stored for a config entry."""

    api: AlexaMaSkillApi
    coordinator: AlexaMaSkillCoordinator
    supervisor: AlexaMaSkillSupervisor
    checklist: ChecklistManager


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Alexa MA Skill from a config entry."""
    config = entry_config(entry)
    username = str(config.get(CONF_USERNAME) or "")
    password = str(config.get(CONF_PASSWORD) or "")
    if not username or not password:
        raise ConfigEntryNotReady(
            "Missing add-on credentials; reconfigure the Alexa MA Skill integration"
        )

    try:
        scan_interval = int(config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
    except (TypeError, ValueError):
        scan_interval = DEFAULT_SCAN_INTERVAL
    scan_interval = max(MIN_SCAN_INTERVAL, min(MAX_SCAN_INTERVAL, scan_interval))

    addon_slug = (
        str(config.get(CONF_ADDON_SLUG) or "").strip()
        if bool(config.get(CONF_MANAGED, False))
        else ""
    )
    supervisor = AlexaMaSkillSupervisor(hass, addon_slug=addon_slug or None)
    if (
        bool(config.get(CONF_MANAGED, False))
        and supervisor.available
        and not supervisor.manager_ready
    ):
        try:
            candidates = supervisor.discover_addons()
        except (SupervisorOperationError, SupervisorUnavailableError):
            candidates = []
        if len(candidates) == 1:
            try:
                supervisor.select_addon(candidates[0].slug)
            except SupervisorOperationError as err:
                _LOGGER.debug(
                    "Could not select the only matching Alexa MA Skill add-on: %s",
                    err,
                )
            else:
                addon_slug = candidates[0].slug
                data = {**entry.data, CONF_ADDON_SLUG: candidates[0].slug}
                options = (
                    {**entry.options, CONF_ADDON_SLUG: candidates[0].slug}
                    if entry.options
                    else entry.options
                )
                hass.config_entries.async_update_entry(
                    entry,
                    data=data,
                    options=options,
                )
        elif len(candidates) > 1:
            _LOGGER.warning(
                "Multiple Alexa MA Skill add-ons found (%s); select one in the "
                "integration options",
                [candidate.slug for candidate in candidates],
            )

    if addon_slug:
        base_url = f"http://{addon_hostname(addon_slug)}:{DEFAULT_PORT}"
    else:
        base_url = config.get(CONF_BASE_URL) or DEFAULT_BASE_URL

    api = AlexaMaSkillApi(
        hass,
        base_url,
        username,
        password,
        ignore_https=bool(config.get(CONF_IGNORE_HTTPS, False)),
    )
    store: Store[dict[str, str]] = Store(
        hass,
        STORAGE_VERSION,
        f"{DOMAIN}.{entry.entry_id}.skill_id",
    )
    stored = await store.async_load()
    detected_skill_id = None
    if isinstance(stored, dict):
        stored_skill_id = stored.get("detected_skill_id")
        if isinstance(stored_skill_id, str) and stored_skill_id:
            detected_skill_id = stored_skill_id
    checklist_store: Store[dict[str, Any]] = Store(
        hass,
        STORAGE_VERSION,
        f"{DOMAIN}.{entry.entry_id}.checklist",
    )
    checklist = ChecklistManager(checklist_store, await checklist_store.async_load())
    if addon_slug and str(config.get(CONF_ADDON_SLUG) or "") != addon_slug:
        await checklist.async_clear_all()
    coordinator = AlexaMaSkillCoordinator(
        hass,
        api,
        supervisor=supervisor,
        skill_hostname=str(config.get(CONF_SKILL_HOSTNAME) or ""),
        ma_hostname=str(config.get(CONF_MA_HOSTNAME) or ""),
        ignore_https=bool(config.get(CONF_IGNORE_HTTPS, False)),
        scan_interval=scan_interval,
        store=store,
        configured_skill_id=str(config.get(CONF_SKILL_ID) or ""),
        initial_detected_skill_id=detected_skill_id,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = AlexaMaSkillRuntimeData(
        api=api,
        coordinator=coordinator,
        supervisor=supervisor,
        checklist=checklist,
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        if runtime is not None:
            await runtime.coordinator.async_shutdown()
        domain_data = hass.data.get(DOMAIN, {})
        domain_data.pop(entry.entry_id, None)
        if not domain_data:
            hass.data.pop(DOMAIN, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry after its configuration changes."""
    await hass.config_entries.async_reload(entry.entry_id)
