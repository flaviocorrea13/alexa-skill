"""Base entity for the Alexa MA Skill integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AlexaMaSkillCoordinator
from .util import mask_skill_ids_in_text


def get_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> AlexaMaSkillCoordinator:
    """Return the coordinator for a config entry."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    return runtime.coordinator


def safe_entry_title(title: str | None) -> str:
    """Return an entry title that never exposes a full skill ID.

    The config entry title is derived from the hostname typed by the user, so a
    skill ID pasted into the wrong field must not reach the device name.
    """
    return mask_skill_ids_in_text(str(title or ""))


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
        data = self.coordinator.data
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=safe_entry_title(self._entry.title),
            manufacturer="Alexa MA Skill",
            model="Music Assistant Alexa Skill",
            sw_version=data.addon_version if data is not None else None,
        )
