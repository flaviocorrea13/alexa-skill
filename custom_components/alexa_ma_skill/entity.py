"""Base entity for the Alexa MA Skill integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SKILL_HOSTNAME, DOMAIN
from .coordinator import AlexaMaSkillCoordinator
from .util import entry_config


def get_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> AlexaMaSkillCoordinator:
    """Return the coordinator for a config entry."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    return runtime.coordinator


class AlexaMaSkillEntity(CoordinatorEntity[AlexaMaSkillCoordinator]):
    """Base entity for the Alexa MA Skill integration."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AlexaMaSkillCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._entry = entry

    @property
    def available(self) -> bool:
        """Keep entities available so connection errors show as off/error."""
        return True

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device information for this entry."""
        config = entry_config(self._entry)
        data = self.coordinator.data
        skill_hostname = str(config.get(CONF_SKILL_HOSTNAME) or "")
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="Alexa MA Skill",
            model="Music Assistant Alexa Skill",
            sw_version=data.addon_version if data is not None else None,
            configuration_url=(
                f"https://{skill_hostname}/setup" if skill_hostname else None
            ),
        )
