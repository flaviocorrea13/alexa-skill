"""Data update coordinator for the Alexa MA Skill integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
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
from .https import HttpsCheckCache
from .supervisor import (
    AlexaMaSkillSupervisor,
    SupervisorOperationError,
    SupervisorUnavailableError,
)
from .util import mask_skill_id, public_stream_url

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AlexaMaSkillData:
    """Data fetched from the add-on."""

    reachable: bool
    http_status: int
    detailed: DetailedStatus | None
    last_check: datetime | None
    detailed_error: str | None
    container_online: bool
    addon_version: str | None
    https_skill_ok: bool
    https_stream_ok: bool
    stream_url_present: bool
    detected_skill_id: str | None
    configured_skill_id: str
    skill_id_matches: bool | None
    suggested_skill_id: str | None


class AlexaMaSkillCoordinator(DataUpdateCoordinator[AlexaMaSkillData]):
    """Coordinate polling of the add-on status endpoints."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: AlexaMaSkillApi,
        *,
        supervisor: AlexaMaSkillSupervisor | None = None,
        skill_hostname: str = "",
        ma_hostname: str = "",
        ignore_https: bool = False,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        store: Store | None = None,
        configured_skill_id: str = "",
        initial_detected_skill_id: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self._supervisor = supervisor
        self._skill_hostname = skill_hostname
        self._ma_hostname = ma_hostname
        self._ignore_https = ignore_https
        self._https_cache = HttpsCheckCache(hass)
        self._last_detailed_attempt: datetime | None = None
        self._detailed: DetailedStatus | None = None
        self._last_check: datetime | None = None
        self._detailed_error: str | None = None
        self._addon_version: str | None = None
        self._store = store
        self._configured_skill_id = configured_skill_id.strip()
        self._detected_skill_id = initial_detected_skill_id

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

        container_online = simple.reachable
        if self._supervisor is not None and self._supervisor.available:
            try:
                (
                    container_online,
                    version,
                ) = await self._supervisor.async_get_running_and_version()
            except (SupervisorOperationError, SupervisorUnavailableError):
                container_online = simple.reachable
            else:
                if version is not None:
                    self._addon_version = version

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

        detected_skill_id: str | None = None
        try:
            setup = await self.api.async_get_setup_status()
        except AlexaMaSkillApiError as err:
            # The setup endpoint is optional for the other entities. A short
            # timeout keeps this poll cheap; failures stay at debug level.
            _LOGGER.debug("Setup status check failed: %s", err)
        else:
            if setup.skill_id:
                detected_skill_id = setup.skill_id
        if detected_skill_id is None and self._detailed is not None:
            detected_skill_id = self._detailed.detected_skill_id
        if detected_skill_id is None:
            detected_skill_id = self._detected_skill_id
        if detected_skill_id and detected_skill_id != self._detected_skill_id:
            self._detected_skill_id = detected_skill_id
            await self._async_save_detected_skill_id(detected_skill_id)

        if not self._configured_skill_id:
            skill_id_matches: bool | None = None
            suggested_skill_id = detected_skill_id
        elif detected_skill_id is None:
            skill_id_matches = None
            suggested_skill_id = None
        else:
            skill_id_matches = self._configured_skill_id == detected_skill_id
            suggested_skill_id = None if skill_id_matches else detected_skill_id

        https_skill_ok = False
        if self._skill_hostname:
            https_skill_ok = await self._https_cache.async_check_skill(
                self._skill_hostname,
                self._ignore_https,
            )

        stream_url_present = bool(self._detailed and self._detailed.stream_url)
        https_stream_ok = False
        if stream_url_present:
            stream_url = public_stream_url(
                self._detailed.stream_url or "",
                self._ma_hostname,
            )
            if stream_url:
                https_stream_ok = await self._https_cache.async_check_stream(
                    stream_url,
                    self._ignore_https,
                )

        return AlexaMaSkillData(
            reachable=simple.reachable,
            http_status=simple.http_status,
            detailed=self._detailed,
            last_check=self._last_check,
            detailed_error=self._detailed_error,
            container_online=container_online,
            addon_version=self._addon_version,
            https_skill_ok=https_skill_ok,
            https_stream_ok=https_stream_ok,
            stream_url_present=stream_url_present,
            detected_skill_id=detected_skill_id,
            configured_skill_id=self._configured_skill_id,
            skill_id_matches=skill_id_matches,
            suggested_skill_id=suggested_skill_id,
        )

    async def _async_save_detected_skill_id(self, skill_id: str) -> None:
        """Persist the last detected skill ID across add-on restarts."""
        if self._store is None:
            return
        _LOGGER.debug("Detected Alexa skill ID %s", mask_skill_id(skill_id))
        try:
            await self._store.async_save({"detected_skill_id": skill_id})
        except OSError as err:
            _LOGGER.debug("Could not persist the detected skill ID: %s", err)
