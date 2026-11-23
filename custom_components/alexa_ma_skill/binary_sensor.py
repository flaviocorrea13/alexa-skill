"""Binary sensors for the Alexa MA Skill integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AlexaMaSkillCoordinator, AlexaMaSkillData
from .entity import AlexaMaSkillEntity, get_coordinator
from .util import skill_linked


def _skill_linked(data: AlexaMaSkillData) -> bool:
    """Return True when the skill exists, matches, and testing is enabled."""
    detailed = data.detailed
    if detailed is None:
        return False
    return skill_linked(detailed.skill_ask_html, detailed.skill_ask_level)


@dataclass(frozen=True, kw_only=True)
class AlexaMaSkillBinarySensorDescription(BinarySensorEntityDescription):
    """Description of an Alexa MA Skill binary sensor."""

    value_fn: Callable[[AlexaMaSkillData], bool]


BINARY_SENSORS: tuple[AlexaMaSkillBinarySensorDescription, ...] = (
    AlexaMaSkillBinarySensorDescription(
        key="container_online",
        translation_key="container_online",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.container_online,
    ),
    AlexaMaSkillBinarySensorDescription(
        key="https_skill",
        translation_key="https_skill",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.https_skill_ok,
    ),
    AlexaMaSkillBinarySensorDescription(
        key="https_stream",
        translation_key="https_stream",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.https_stream_ok,
    ),
    AlexaMaSkillBinarySensorDescription(
        key="skill_linked",
        translation_key="skill_linked",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_skill_linked,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator = get_coordinator(hass, entry)
    async_add_entities(
        AlexaMaSkillBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSORS
    )


class AlexaMaSkillBinarySensor(AlexaMaSkillEntity, BinarySensorEntity):
    """Representation of an Alexa MA Skill binary sensor."""

    entity_description: AlexaMaSkillBinarySensorDescription

    def __init__(
        self,
        coordinator: AlexaMaSkillCoordinator,
        entry: ConfigEntry,
        description: AlexaMaSkillBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def is_on(self) -> bool:
        """Return the current state, with connection errors reported as off."""
        if self.coordinator.data is None or not self.coordinator.last_update_success:
            return False
        return self.entity_description.value_fn(self.coordinator.data)
