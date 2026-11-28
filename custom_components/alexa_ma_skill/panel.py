"""Panel registration for the Alexa MA Skill integration."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    PANEL_ELEMENT,
    PANEL_FILENAME,
    PANEL_ICON,
    PANEL_STATIC_PATH,
    PANEL_TITLE,
    PANEL_URL,
)

_LOGGER = logging.getLogger(__name__)

PANEL_STATE_KEY = f"{DOMAIN}_panel"
BUNDLE_PATH = Path(__file__).parent / "frontend" / "dist" / PANEL_FILENAME


def _hash_file(path: Path) -> str:
    """Return a short SHA-256 content hash for cache busting."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _panel_state(hass: HomeAssistant) -> dict[str, Any]:
    """Return the mutable panel registration state."""
    return hass.data.setdefault(PANEL_STATE_KEY, {})


async def async_register_panel(hass: HomeAssistant) -> bool:
    """Register the admin panel and its compiled bundle once.

    Returns True when the panel is registered. A missing bundle or a failed
    registration is logged and leaves the flag unset, so a later reload can
    retry instead of leaving a permanently broken registration.
    """
    state = _panel_state(hass)
    if state.get("registered"):
        return True

    if not BUNDLE_PATH.is_file():
        _LOGGER.warning(
            "Alexa MA panel bundle is missing at %s; the integration will "
            "continue without the panel",
            BUNDLE_PATH,
        )
        return False

    try:
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    PANEL_STATIC_PATH,
                    str(BUNDLE_PATH),
                    cache_headers=False,
                )
            ]
        )
    except RuntimeError:
        # The static route may already be registered after a reload. It is
        # immutable in HA, so reuse it if the bundle path is unchanged.
        _LOGGER.debug("Static route %s already registered", PANEL_STATIC_PATH)
    except Exception as err:  # noqa: BLE001 - registration must not break setup
        _LOGGER.warning(
            "Could not register the Alexa MA panel static route: %s",
            type(err).__name__,
        )
        return False

    try:
        content_hash = await hass.async_add_executor_job(_hash_file, BUNDLE_PATH)
        module_url = f"{PANEL_STATIC_PATH}?v={content_hash}"
        await panel_custom.async_register_panel(
            hass,
            webcomponent_name=PANEL_ELEMENT,
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            frontend_url_path=PANEL_URL,
            config={},
            require_admin=True,
            embed_iframe=False,
            trust_external=False,
            module_url=module_url,
        )
    except Exception as err:  # noqa: BLE001 - registration must not break setup
        _LOGGER.warning(
            "Could not register the Alexa MA panel: %s",
            type(err).__name__,
        )
        return False

    state["registered"] = True
    state["module_url"] = module_url
    return True


async def async_unregister_panel(hass: HomeAssistant) -> None:
    """Remove the panel when the last config entry is unloaded."""
    state = _panel_state(hass)
    if not state.get("registered"):
        return
    try:
        frontend.async_remove_panel(hass, PANEL_URL)
    except Exception as err:  # noqa: BLE001 - unload must not fail
        _LOGGER.debug(
            "Could not remove the Alexa MA panel: %s",
            type(err).__name__,
        )
    state.clear()


async def async_unregister_panel_if_empty(hass: HomeAssistant) -> None:
    """Remove the panel only when no loaded runtime entry remains."""
    domain_data = hass.data.get(DOMAIN, {})
    if any(hasattr(runtime, "coordinator") for runtime in domain_data.values()):
        return
    await async_unregister_panel(hass)
