"""Supervisor helpers for the Alexa MA Skill add-on."""

from __future__ import annotations

import logging
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class AddonCandidate:
    """Add-on installed in the Supervisor that matches this integration."""

    slug: str
    name: str
    version: str | None


def addon_hostname(slug: str) -> str:
    """Return the internal add-on hostname derived from its Supervisor slug."""
    return slug.replace("_", "-")


class AlexaMaSkillSupervisor:
    """Small wrapper around the hassio AddonManager."""

    def __init__(
        self,
        hass: HomeAssistant,
        addon_slug: str | None = None,
    ) -> None:
        """Initialize the wrapper and detect Supervisor availability."""
        self._hass = hass
        self._manager: Any | None = None
        self._available = False

        if "hassio" not in hass.config.components:
            _LOGGER.info(
                "Supervisor/hassio is not available; add-on management is disabled"
            )
            return

        try:
            from homeassistant.components.hassio import AddonManager  # noqa: F401
        except ImportError:
            _LOGGER.info(
                "hassio AddonManager is not available; add-on management is disabled"
            )
            return

        self._available = True
        if addon_slug:
            try:
                self.select_addon(addon_slug)
            except SupervisorOperationError:
                _LOGGER.warning(
                    "Could not initialize the add-on manager for slug %s",
                    addon_slug,
                )

    @property
    def available(self) -> bool:
        """Return True when Supervisor add-on management is available."""
        return self._available

    @property
    def manager_ready(self) -> bool:
        """Return True when an add-on slug has been selected."""
        return self._manager is not None

    @property
    def addon_slug(self) -> str | None:
        """Return the selected add-on slug, if any."""
        if self._manager is None:
            return None
        return str(self._manager.addon_slug)

    def discover_addons(self) -> list[AddonCandidate]:
        """Return add-ons whose slug is the base slug or ends with it.

        Custom add-on repositories receive a ``<hash>_`` prefix from the
        Supervisor, so the installed slug may be ``0cc21073_alexa_ma_skill``
        instead of the repository slug ``alexa_ma_skill``.
        """
        if not self._available:
            return []

        from homeassistant.components.hassio import HassioNotReadyError, get_addons_info

        try:
            addons = get_addons_info(self._hass)
        except HassioNotReadyError as err:
            raise SupervisorUnavailableError(
                "The Supervisor add-on list is not ready"
            ) from err

        candidates: list[AddonCandidate] = []
        for slug, info in addons.items():
            if slug != ADDON_SLUG and not slug.endswith(f"_{ADDON_SLUG}"):
                continue
            data = info or {}
            name = str(data.get("name") or slug)
            version = data.get("version")
            candidates.append(
                AddonCandidate(
                    slug=slug,
                    name=name,
                    version=str(version) if version is not None else None,
                )
            )

        candidates.sort(key=lambda candidate: candidate.slug)
        if not candidates:
            _LOGGER.debug(
                "No add-on matching %s or *_%s; found slugs: %s",
                ADDON_SLUG,
                ADDON_SLUG,
                sorted(addons),
            )
        elif len(candidates) > 1:
            _LOGGER.debug(
                "Multiple add-ons match the Alexa MA Skill base slug: %s",
                [candidate.slug for candidate in candidates],
            )
        return candidates

    def select_addon(self, addon_slug: str) -> None:
        """Create the manager for the selected Supervisor slug."""
        if not self._available:
            raise SupervisorUnavailableError(
                "Supervisor is not available; install the add-on on HA OS or Supervised"
            )

        from homeassistant.components.hassio import AddonManager

        try:
            self._manager = AddonManager(
                self._hass,
                _LOGGER,
                ADDON_NAME,
                addon_slug,
            )
        except Exception as err:
            self._manager = None
            raise SupervisorOperationError(
                f"Could not initialize the add-on manager for {addon_slug}: {err}"
            ) from err
        _LOGGER.debug("Selected add-on slug %s", addon_slug)

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
                "No Alexa MA Skill add-on slug has been selected"
            )
        return self._manager
