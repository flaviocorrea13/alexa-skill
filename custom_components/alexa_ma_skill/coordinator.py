"""Data update coordinator for the Alexa MA Skill integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import (
    AlexaMaSkillApi,
    AlexaMaSkillApiError,
    AlexaMaSkillAuthError,
    AlexaMaSkillConnectionError,
    DetailedStatus,
)
from .const import DEFAULT_SCAN_INTERVAL, DETAILED_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AlexaMaSkillData:
    """Data fetched from the add-on."""

    reachable: bool
    http_status: int
    detailed: DetailedStatus | None
    last_check: datetime | None
    detailed_error: str | None


class AlexaMaSkillCoordinator(DataUpdateCoordinator[AlexaMaSkillData]):
    """Coordinate polling of the add-on status endpoints."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: AlexaMaSkillApi,
        *,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self._last_detailed_attempt: datetime | None = None
        self._detailed: DetailedStatus | None = None
        self._last_check: datetime | None = None
        self._detailed_error: str | None = None

    async def _async_update_data(self) -> AlexaMaSkillData:
        """Fetch the cheap status every poll and the detailed status every 5 min."""
        now = datetime.now(UTC)

        try:
            simple = await self.api.async_get_status()
        except AlexaMaSkillAuthError as err:
            raise ConfigEntryAuthFailed(
                "Authentication failed for the Alexa MA Skill add-on"
            ) from err
        except AlexaMaSkillConnectionError as err:
            raise UpdateFailed(f"Could not connect to the add-on: {err}") from err
        except AlexaMaSkillApiError as err:
            raise UpdateFailed(f"Unexpected response from the add-on: {err}") from err

        if (
            self._last_detailed_attempt is None
            or now - self._last_detailed_attempt >= DETAILED_SCAN_INTERVAL
        ):
            self._last_detailed_attempt = now
            try:
                detailed = await self.api.async_get_status_json()
            except AlexaMaSkillAuthError as err:
                raise ConfigEntryAuthFailed(
                    "Authentication failed for the Alexa MA Skill add-on"
                ) from err
            except AlexaMaSkillApiError as err:
                self._detailed_error = str(err)
                _LOGGER.warning("Detailed status check failed: %s", err)
            else:
                self._detailed = detailed
                self._last_check = datetime.now(UTC)
                self._detailed_error = None

        return AlexaMaSkillData(
            reachable=simple.reachable,
            http_status=simple.http_status,
            detailed=self._detailed,
            last_check=self._last_check,
            detailed_error=self._detailed_error,
        )
