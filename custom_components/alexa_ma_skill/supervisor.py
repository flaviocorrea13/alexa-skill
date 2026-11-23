"""Supervisor helpers for the Alexa MA Skill add-on."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import ADDON_NAME, ADDON_SLUG

if TYPE_CHECKING:
    from homeassistant.components.hassio import AddonInfo

_LOGGER = logging.getLogger(__name__)


class SupervisorUnavailableError(HomeAssistantError):
    """Supervisor is not available, for example on HA Container/Core."""


class SupervisorOperationError(HomeAssistantError):
    """A Supervisor operation failed."""


class AlexaMaSkillSupervisor:
    """Small wrapper around the hassio AddonManager."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the wrapper and detect Supervisor availability."""
        self._hass = hass
        self._manager: Any | None = None

        if "hassio" not in hass.config.components:
            _LOGGER.info(
                "Supervisor/hassio is not available; add-on management is disabled"
            )
            return

        try:
            from homeassistant.components.hassio import AddonManager
        except ImportError:
            _LOGGER.info(
                "hassio AddonManager is not available; add-on management is disabled"
            )
            return

        try:
            self._manager = AddonManager(hass, _LOGGER, ADDON_NAME, ADDON_SLUG)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Could not initialize hassio AddonManager: %s", err)
            self._manager = None

    @property
    def available(self) -> bool:
        """Return True when Supervisor add-on management is available."""
        return self._manager is not None

    async def async_get_info(self) -> AddonInfo:
        """Return add-on information."""
        manager = self._require_manager()
        try:
            return await manager.async_get_addon_info()
        except HomeAssistantError as err:
            raise SupervisorOperationError(str(err)) from err

    async def async_get_options(self) -> dict[str, Any]:
        """Return the current add-on options."""
        info = await self.async_get_info()
        return dict(info.options)

    async def async_is_installed(self) -> bool:
        """Return True when the add-on is installed."""
        self._require_manager()
        from homeassistant.components.hassio import AddonState

        info = await self.async_get_info()
        return info.state is not AddonState.NOT_INSTALLED

    async def async_is_running(self) -> bool:
        """Return True when the add-on is running."""
        self._require_manager()
        from homeassistant.components.hassio import AddonState

        info = await self.async_get_info()
        return info.state is AddonState.RUNNING

    async def async_get_running_and_version(
        self,
    ) -> tuple[bool, str | None]:
        """Return whether the add-on is running and its version."""
        self._require_manager()
        from homeassistant.components.hassio import AddonState

        info = await self.async_get_info()
        return info.state is AddonState.RUNNING, info.version

    async def async_set_options(self, options: dict[str, Any]) -> None:
        """Merge options into the add-on configuration."""
        manager = self._require_manager()
        try:
            await manager.async_configure_addon(options)
        except HomeAssistantError as err:
            raise SupervisorOperationError(str(err)) from err

    async def async_start(self) -> None:
        """Start the add-on."""
        manager = self._require_manager()
        try:
            await manager.async_start_addon()
        except HomeAssistantError as err:
            raise SupervisorOperationError(str(err)) from err

    async def async_restart(self) -> None:
        """Restart the add-on."""
        manager = self._require_manager()
        try:
            await manager.async_restart_addon()
        except HomeAssistantError as err:
            raise SupervisorOperationError(str(err)) from err

    async def async_stop(self) -> None:
        """Stop the add-on."""
        manager = self._require_manager()
        try:
            await manager.async_stop_addon()
        except HomeAssistantError as err:
            raise SupervisorOperationError(str(err)) from err

    async def async_start_or_restart(self) -> None:
        """Start a stopped add-on or restart a running one."""
        self._require_manager()
        from homeassistant.components.hassio import AddonState

        info = await self.async_get_info()
        if info.state is AddonState.RUNNING:
            await self.async_restart()
            return
        if info.state is AddonState.NOT_INSTALLED:
            raise SupervisorOperationError("The Alexa MA Skill add-on is not installed")
        await self.async_start()

    def _require_manager(self) -> Any:
        """Return the AddonManager or raise a clear error."""
        if self._manager is None:
            raise SupervisorUnavailableError(
                "Supervisor is not available; install the add-on on HA OS or Supervised"
            )
        return self._manager
