"""The Alexa MA Skill integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.storage import Store

from .api import AlexaMaSkillApi
from .const import (
    CONF_BASE_URL,
    CONF_IGNORE_HTTPS,
    CONF_MA_HOSTNAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_SKILL_HOSTNAME,
    CONF_SKILL_ID,
    CONF_USERNAME,
    DEFAULT_BASE_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    PLATFORMS,
    STORAGE_VERSION,
)
from .coordinator import AlexaMaSkillCoordinator
from .supervisor import AlexaMaSkillSupervisor
from .util import entry_config


@dataclass(slots=True)
class AlexaMaSkillRuntimeData:
    """Runtime data stored for a config entry."""

    api: AlexaMaSkillApi
    coordinator: AlexaMaSkillCoordinator
    supervisor: AlexaMaSkillSupervisor


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Alexa MA Skill from a config entry."""
    config = entry_config(entry)
    base_url = config.get(CONF_BASE_URL) or DEFAULT_BASE_URL
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

    api = AlexaMaSkillApi(
        hass,
        base_url,
        username,
        password,
        ignore_https=bool(config.get(CONF_IGNORE_HTTPS, False)),
    )
    supervisor = AlexaMaSkillSupervisor(hass)
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
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        domain_data = hass.data.get(DOMAIN, {})
        domain_data.pop(entry.entry_id, None)
        if not domain_data:
            hass.data.pop(DOMAIN, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry after its configuration changes."""
    await hass.config_entries.async_reload(entry.entry_id)
