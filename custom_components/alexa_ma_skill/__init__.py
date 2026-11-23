"""The Alexa MA Skill integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import AlexaMaSkillApi
from .const import (
    CONF_BASE_URL,
    CONF_IGNORE_HTTPS,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_BASE_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    PLATFORMS,
)
from .coordinator import AlexaMaSkillCoordinator
from .supervisor import AlexaMaSkillSupervisor


@dataclass(slots=True)
class AlexaMaSkillRuntimeData:
    """Runtime data stored for a config entry."""

    api: AlexaMaSkillApi
    coordinator: AlexaMaSkillCoordinator
    supervisor: AlexaMaSkillSupervisor


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Alexa MA Skill from a config entry."""
    base_url = entry.data.get(CONF_BASE_URL) or DEFAULT_BASE_URL
    username = str(entry.data.get(CONF_USERNAME) or "")
    password = str(entry.data.get(CONF_PASSWORD) or "")
    if not username or not password:
        raise ConfigEntryNotReady(
            "Missing add-on credentials; reconfigure the Alexa MA Skill integration"
        )

    try:
        scan_interval = int(entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
    except (TypeError, ValueError):
        scan_interval = DEFAULT_SCAN_INTERVAL
    scan_interval = max(MIN_SCAN_INTERVAL, min(MAX_SCAN_INTERVAL, scan_interval))

    api = AlexaMaSkillApi(
        hass,
        base_url,
        username,
        password,
        ignore_https=bool(entry.data.get(CONF_IGNORE_HTTPS, False)),
    )
    supervisor = AlexaMaSkillSupervisor(hass)
    coordinator = AlexaMaSkillCoordinator(hass, api, scan_interval=scan_interval)
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
