"""Sensors for the Alexa MA Skill integration."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, StatusLevel
from .coordinator import AlexaMaSkillCoordinator, AlexaMaSkillData
from .entity import AlexaMaSkillEntity, get_coordinator
from .setup import ChecklistManager, build_setup_checklist
from .util import (
    entry_config,
    html_to_text,
    mask_skill_ids_in_text,
    redact_stream_urls,
    skill_linked,
)

_MAX_STATE_LENGTH = 255

_SETUP_CHECKLIST_STEP_KEYS = (
    "id",
    "title",
    "description",
    "status",
    "status_label",
    "result",
    "mode",
    "dependencies",
    "optional",
    "how_to_fix",
    "done",
    "confirmed",
)
_STEP_TEXT_KEYS = {"title", "description", "status_label", "result", "how_to_fix"}
_STEP_BOOL_KEYS = {"optional", "done", "confirmed"}
_URL_WITH_QUERY_RE = re.compile(r"(https?://[^\s?#]+)\?[^\s]*")


def _clean_attribute_text(value: Any) -> str | None:
    """Return attribute text without skill IDs, HTML, or URL query strings."""
    if not isinstance(value, str):
        return None
    text = mask_skill_ids_in_text(redact_stream_urls(html_to_text(value)))
    text = _URL_WITH_QUERY_RE.sub(r"\1?[redacted]", text)
    return text.strip() or None


def _clean_step(step: dict[str, Any]) -> dict[str, Any]:
    """Return an allowlisted, sanitized copy of a checklist step."""
    cleaned: dict[str, Any] = {}
    for key in _SETUP_CHECKLIST_STEP_KEYS:
        if key not in step:
            continue
        value = step[key]
        if key in _STEP_TEXT_KEYS:
            cleaned[key] = _clean_attribute_text(value)
        elif key in _STEP_BOOL_KEYS:
            cleaned[key] = bool(value)
        elif key == "dependencies":
            cleaned[key] = (
                [str(item) for item in value] if isinstance(value, list) else []
            )
        else:
            cleaned[key] = str(value)
    return cleaned


def _setup_checklist_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    """Return the public, allowlisted attributes of the checklist sensor.

    ``build_setup_checklist`` also returns the full skill IDs, console values,
    public/internal URLs and the Cloudflare rule. Those stay available to the
    options flow, which calls the helper directly, but must never be published
    as entity attributes.
    """
    progress = attributes.get("progress") or {}
    warnings = attributes.get("warnings") or []
    return {
        "progress": {
            "done": int(progress.get("done", 0)),
            "pending": int(progress.get("pending", 0)),
            "blocked": int(progress.get("blocked", 0)),
            "attention": int(progress.get("attention", 0)),
            "not_applicable": int(progress.get("not_applicable", 0)),
            "total": int(progress.get("total", 0)),
            "applicable": int(progress.get("applicable", 0)),
            "percent": int(progress.get("percent", 0)),
            "complete": bool(progress.get("complete", False)),
            "next_step": progress.get("next_step"),
            "next_step_title": _clean_attribute_text(progress.get("next_step_title")),
        },
        "checklist": [
            _clean_step(step)
            for step in attributes.get("checklist") or []
            if isinstance(step, dict)
        ],
        "manual_steps": [
            _clean_step(step)
            for step in attributes.get("manual_steps") or []
            if isinstance(step, dict)
        ],
        "next_step": progress.get("next_step"),
        "next_step_title": _clean_attribute_text(progress.get("next_step_title")),
        "warnings": [
            text for text in (_clean_attribute_text(item) for item in warnings) if text
        ],
        "skill_found": bool(attributes.get("skill_found", False)),
        "endpoint_matches": bool(attributes.get("endpoint_matches", False)),
        "testing_enabled": bool(attributes.get("testing_enabled", False)),
        "skill_id_matches": attributes.get("skill_id_matches"),
    }


def _clean_status_text(value: str) -> str | None:
    """Return clean, redacted text without skill IDs from a status fragment."""
    text = mask_skill_ids_in_text(redact_stream_urls(html_to_text(value))).strip()
    if not text:
        return None
    return text[:_MAX_STATE_LENGTH]


def _overall_status(data: AlexaMaSkillData) -> str:
    """Return ok, warning, or error for the integration."""
    if not data.container_online:
        return "error"
    if data.detailed is None:
        return "warning" if data.reachable else "error"

    detailed = data.detailed
    levels = (
        detailed.skill_ask_level,
        detailed.ma_api_level,
        detailed.alexa_api_level,
    )
    if any(level is StatusLevel.RED for level in levels):
        return "error"
    if not data.https_skill_ok:
        return "error"
    if data.stream_url_present and not data.https_stream_ok:
        return "error"
    if data.skill_id_matches is False:
        return "error"
    if not data.configured_skill_id:
        return "warning"
    if any(level in (StatusLevel.YELLOW, StatusLevel.UNKNOWN) for level in levels):
        return "warning"
    if not skill_linked(detailed.skill_ask_html, detailed.skill_ask_level):
        return "warning"
    if data.detailed_error:
        return "warning"
    return "ok"


def _skill_status(data: AlexaMaSkillData) -> str | None:
    if data.detailed is None:
        return None
    return _clean_status_text(data.detailed.skill_ask_html)


def _ma_api_status(data: AlexaMaSkillData) -> str | None:
    if data.detailed is None:
        return None
    return _clean_status_text(data.detailed.ma_api_html)


def _alexa_api_status(data: AlexaMaSkillData) -> str | None:
    if data.detailed is None:
        return None
    return _clean_status_text(data.detailed.alexa_api_html)


@dataclass(frozen=True, kw_only=True)
class AlexaMaSkillSensorDescription(SensorEntityDescription):
    """Description of an Alexa MA Skill sensor."""

    value_fn: Callable[[AlexaMaSkillData], Any]


SENSORS: tuple[AlexaMaSkillSensorDescription, ...] = (
    AlexaMaSkillSensorDescription(
        key="overall_status",
        translation_key="overall_status",
        device_class=SensorDeviceClass.ENUM,
        options=["ok", "warning", "error"],
        value_fn=_overall_status,
    ),
    AlexaMaSkillSensorDescription(
        key="skill_status",
        translation_key="skill_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_skill_status,
    ),
    AlexaMaSkillSensorDescription(
        key="ma_api",
        translation_key="ma_api",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_ma_api_status,
    ),
    AlexaMaSkillSensorDescription(
        key="alexa_api",
        translation_key="alexa_api",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_alexa_api_status,
    ),
    AlexaMaSkillSensorDescription(
        key="last_check",
        translation_key="last_check",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.last_check,
    ),
    AlexaMaSkillSensorDescription(
        key="addon_version",
        translation_key="addon_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.addon_version,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = get_coordinator(hass, entry)
    checklist = hass.data[DOMAIN][entry.entry_id].checklist
    entities: list[SensorEntity] = [
        AlexaMaSkillSensor(coordinator, entry, description) for description in SENSORS
    ]
    entities.append(AlexaMaSkillSetupChecklistSensor(coordinator, entry, checklist))
    async_add_entities(entities)


class AlexaMaSkillSensor(AlexaMaSkillEntity, SensorEntity):
    """Representation of an Alexa MA Skill sensor."""

    entity_description: AlexaMaSkillSensorDescription

    def __init__(
        self,
        coordinator: AlexaMaSkillCoordinator,
        entry: ConfigEntry,
        description: AlexaMaSkillSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        data = self.coordinator.data
        key = self.entity_description.key
        if data is None:
            return "error" if key == "overall_status" else None
        if not self.coordinator.last_update_success:
            if key == "overall_status":
                return "error"
            if key in ("skill_status", "ma_api", "alexa_api"):
                return None
        return self.entity_description.value_fn(data)


class AlexaMaSkillSetupChecklistSensor(AlexaMaSkillEntity, SensorEntity):
    """Setup checklist and Amazon console values."""

    _attr_translation_key = "setup_checklist"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options: ClassVar[list[str]] = ["complete", "incomplete", "error"]
    _attr_icon = "mdi:clipboard-check-outline"

    def __init__(
        self,
        coordinator: AlexaMaSkillCoordinator,
        entry: ConfigEntry,
        checklist: ChecklistManager,
    ) -> None:
        """Initialize the setup checklist sensor."""
        super().__init__(coordinator, entry)
        self._checklist = checklist
        self._attr_unique_id = f"{entry.entry_id}_setup_checklist"

    @property
    def native_value(self) -> str:
        """Return complete, incomplete, or error."""
        state, _attributes = build_setup_checklist(
            entry_config(self._entry),
            self.coordinator.data,
            self.coordinator.hass.config.language,
            self._checklist.confirmations,
        )
        return state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the allowlisted checklist, progress, and next actions."""
        _state, attributes = build_setup_checklist(
            entry_config(self._entry),
            self.coordinator.data,
            self.coordinator.hass.config.language,
            self._checklist.confirmations,
        )
        return _setup_checklist_attributes(attributes)
