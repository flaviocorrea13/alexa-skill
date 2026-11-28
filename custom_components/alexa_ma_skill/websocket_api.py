"""WebSocket API for the Alexa MA admin panel."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import probatio
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import DOMAIN, WS_PREFIX
from .panel import PANEL_STATE_KEY
from .panel_data import (
    PanelEntryNotFound,
    PanelError,
    async_build_overview,
    build_entries,
    resolve_entry,
)

_LOGGER = logging.getLogger(__name__)

REFRESH_COOLDOWN = 5.0
ENTRY_ID = probatio.All(str, probatio.Length(min=1, max=64))


def _schema(command: str, *, with_entry: bool = True) -> probatio.All:
    """Return a strict WebSocket command schema."""
    fields: dict[Any, Any] = {probatio.Required("type"): command}
    if with_entry:
        fields[probatio.Optional("entry_id")] = ENTRY_ID
    return probatio.All(probatio.Schema(fields, extra=probatio.PREVENT_EXTRA))


def _error_message(code: str) -> str:
    """Return a generic message for a panel error code."""
    return {
        "not_loaded": "The Alexa MA integration is not loaded",
        "entry_required": "Select one Alexa MA config entry",
        "entry_not_found": "The Alexa MA config entry was not found",
        "refresh_failed": "Could not refresh the Alexa MA data",
        "internal_error": "The Alexa MA panel request failed",
    }.get(code, "The Alexa MA panel request failed")


def _send_panel_error(
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    error: PanelError,
) -> None:
    """Send a stable, non-sensitive error."""
    connection.send_error(msg["id"], error.code, _error_message(error.code))


async def _refresh_state(hass: HomeAssistant) -> dict[str, Any]:
    """Return the shared refresh state."""
    return hass.data.setdefault(PANEL_STATE_KEY, {})


@websocket_api.require_admin
@websocket_api.websocket_command(_schema(f"{WS_PREFIX}/entries", with_entry=False))
@websocket_api.async_response
async def ws_entries(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return loaded Alexa MA config entries."""
    try:
        entries = build_entries(hass)
    except PanelError as err:
        _send_panel_error(connection, msg, err)
    except Exception as err:  # noqa: BLE001 - never expose exception details
        _LOGGER.debug("Panel entries failed: %s", type(err).__name__)
        connection.send_error(
            msg["id"], "internal_error", _error_message("internal_error")
        )
    else:
        connection.send_result(
            msg["id"],
            {
                "entries": entries,
                "default_entry_id": entries[0]["entry_id"]
                if len(entries) == 1
                else None,
            },
        )


@websocket_api.require_admin
@websocket_api.websocket_command(_schema(f"{WS_PREFIX}/overview"))
@websocket_api.async_response
async def ws_overview(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the sanitized overview."""
    try:
        payload = await async_build_overview(hass, msg.get("entry_id"))
    except PanelError as err:
        _send_panel_error(connection, msg, err)
    except Exception as err:  # noqa: BLE001 - never expose exception details
        _LOGGER.debug("Panel overview failed: %s", type(err).__name__)
        connection.send_error(
            msg["id"], "internal_error", _error_message("internal_error")
        )
    else:
        connection.send_result(msg["id"], payload)


@websocket_api.require_admin
@websocket_api.websocket_command(_schema(f"{WS_PREFIX}/refresh"))
@websocket_api.async_response
async def ws_refresh(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Refresh the coordinator on demand, with a per-entry cooldown.

    ``refreshed`` is ``True`` only when this command ran a coordinator update
    that finished successfully. ``False`` means the cooldown or a concurrent
    refresh prevented an update; the returned overview is the current
    snapshot. A finished but failed update is reported as ``refresh_failed``.
    """
    try:
        entry, runtime = resolve_entry(hass, msg.get("entry_id"))
    except PanelError as err:
        _send_panel_error(connection, msg, err)
        return

    state = await _refresh_state(hass)
    locks: dict[str, asyncio.Lock] = state.setdefault("refresh_locks", {})
    last_refresh: dict[str, float] = state.setdefault("refresh_last", {})
    lock = locks.setdefault(entry.entry_id, asyncio.Lock())
    refreshed = False

    # A refresh already running for this entry: answer with the data that is
    # available instead of queueing another heavy pass behind it.
    if not lock.locked():
        async with lock:
            last_attempt = last_refresh.get(entry.entry_id, 0.0)
            if time.monotonic() - last_attempt >= REFRESH_COOLDOWN:
                # The entry may have been unloaded between resolve and lock.
                if hass.data.get(DOMAIN, {}).get(entry.entry_id) is not runtime:
                    _send_panel_error(connection, msg, PanelEntryNotFound)
                    return
                try:
                    # ``async_refresh`` is the public coordinator API that
                    # runs the update now and returns only after it finishes.
                    # ``async_request_refresh`` would merely schedule a
                    # debounced run, so the command could report success
                    # before any new data existed (the coordinator debouncer
                    # waits 10 s, while this panel allows a retry after 5 s).
                    await runtime.coordinator.async_refresh()
                except Exception as err:  # noqa: BLE001 - no internal detail to UI
                    _LOGGER.debug("Panel refresh failed: %s", type(err).__name__)
                    connection.send_error(
                        msg["id"], "refresh_failed", _error_message("refresh_failed")
                    )
                    return
                finally:
                    # Start the cooldown when the attempt ends, so a slow or
                    # failing refresh cannot be retried immediately.
                    last_refresh[entry.entry_id] = time.monotonic()
                refreshed = True

    try:
        payload = await async_build_overview(hass, entry.entry_id)
    except PanelError as err:
        _send_panel_error(connection, msg, err)
    except Exception as err:  # noqa: BLE001 - never expose exception details
        _LOGGER.debug("Panel refresh overview failed: %s", type(err).__name__)
        connection.send_error(
            msg["id"], "internal_error", _error_message("internal_error")
        )
    else:
        if refreshed and not runtime.coordinator.last_update_success:
            connection.send_error(
                msg["id"], "refresh_failed", _error_message("refresh_failed")
            )
            return
        connection.send_result(
            msg["id"],
            {"success": True, "refreshed": refreshed, "overview": payload},
        )


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register panel commands once."""
    flag = f"{DOMAIN}_ws_registered"
    if hass.data.get(flag):
        return
    for command in (ws_entries, ws_overview, ws_refresh):
        websocket_api.async_register_command(hass, command)
    hass.data[flag] = True
