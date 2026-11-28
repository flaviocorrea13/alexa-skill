"""WebSocket API tests for the Alexa MA panel."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.alexa_ma_skill.api import DetailedStatus
from custom_components.alexa_ma_skill.const import DOMAIN, StatusLevel
from custom_components.alexa_ma_skill.coordinator import AlexaMaSkillData
from custom_components.alexa_ma_skill.panel import PANEL_STATE_KEY
from custom_components.alexa_ma_skill.websocket_api import (
    async_register_websocket_commands,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry, MockUser

GOOD_ID = "amzn1.ask.skill.11111111-1111-1111-1111-111111111111"
OTHER_ID = "amzn1.ask.skill.99999999-9999-9999-9999-999999999999"
THIRD_ID = "amzn1.ask.skill.abcdef01-2345-6789-abcd-ef0123456789"


def _data() -> AlexaMaSkillData:
    detailed = DetailedStatus(
        skill_html="",
        skill_ask_html="endpoint matches, testing enabled",
        ma_api_html="",
        alexa_api_html="",
        metadata_html="",
        invocations_html="",
        created=True,
        skill_ask_level=StatusLevel.GREEN,
        ma_api_level=StatusLevel.GREEN,
        alexa_api_level=StatusLevel.GREEN,
        ma_api_details=None,
        stream_url=None,
        detected_skill_id=OTHER_ID,
    )
    return AlexaMaSkillData(
        reachable=True,
        http_status=200,
        detailed=detailed,
        last_check=None,
        detailed_error=None,
        container_online=True,
        addon_installed=True,
        addon_hostname="local-alexa-ma-skill",
        addon_version="0.2.0",
        https_skill_ok=True,
        https_stream_ok=True,
        stream_url_present=False,
        detected_skill_id=OTHER_ID,
        configured_skill_id=GOOD_ID,
        skill_id_matches=False,
        suggested_skill_id=OTHER_ID,
    )


class FakeCoordinator:
    """Minimal stand-in for the public DataUpdateCoordinator surface.

    ``async_refresh`` mirrors the real coordinator: it runs the update and
    returns after it finishes, and a failure is reflected by
    ``last_update_success`` instead of an exception.
    """

    def __init__(self, data: AlexaMaSkillData | None = None) -> None:
        self.data = data if data is not None else _data()
        self.last_update_success = True
        self.refresh_calls = 0
        self.on_refresh: Callable[[FakeCoordinator], Awaitable[None]] | None = None

    async def async_refresh(self) -> None:
        """Run the configured update."""
        self.refresh_calls += 1
        if self.on_refresh is not None:
            await self.on_refresh(self)


def _runtime(*, supervisor=None, refresh=None):
    coordinator = FakeCoordinator()
    coordinator.on_refresh = refresh
    return SimpleNamespace(
        coordinator=coordinator,
        checklist=SimpleNamespace(confirmations={}),
        supervisor=supervisor or SimpleNamespace(available=False, manager_ready=False),
    )


def _entry(entry_id: str = "entry-1", title: str = "Alexa MA"):
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id=entry_id,
        title=title,
        data={},
        options={
            "managed": True,
            "addon_slug": "local_alexa_ma_skill",
            "skill_hostname": "skill.example.test",
            "ma_hostname": "stream.example.test",
            "skill_id": GOOD_ID,
            "ma_api_url": "http://192.0.2.10:8095",
        },
    )


async def _setup(hass, *, entries=1, runtime=None):
    for index in range(entries):
        entry = _entry(f"entry-{index + 1}", f"Alexa MA {index + 1}")
        entry.add_to_hass(hass)
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime or _runtime()
    async_register_websocket_commands(hass)


async def _call(client, payload):
    await client.send_json_auto_id(payload)
    return await client.receive_json()


@pytest.mark.asyncio
async def test_entries_and_overview_are_sanitized(hass, hass_ws_client):
    entry = _entry("entry-1", f"Alexa MA {THIRD_ID}")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _runtime()
    async_register_websocket_commands(hass)
    client = await hass_ws_client(hass)

    result = await _call(client, {"type": "alexa_ma_skill/entries"})
    assert result["success"] is True
    assert result["result"]["entries"][0]["entry_id"] == "entry-1"
    assert set(result["result"]["entries"][0]) == {
        "entry_id",
        "title",
        "managed",
        "addon_slug",
    }
    assert THIRD_ID not in json.dumps(result["result"])

    result = await _call(client, {"type": "alexa_ma_skill/overview"})
    assert result["success"] is True
    payload = result["result"]
    assert payload["state"] == "connected"
    assert payload["addon"]["version"] == "0.2.0"
    assert payload["addon"]["state"] == "running"
    assert payload["checklist"]["total"] == 16
    assert payload["alexa"]["configured_skill_id_masked"].startswith("amzn1.ask.skill.")
    assert "suggested_skill_id" not in payload["alexa"]

    serialized = json.dumps(payload)
    for full_id in (GOOD_ID, OTHER_ID, THIRD_ID):
        assert full_id not in serialized
    assert "192.0.2.10" not in serialized
    assert "stream.example.test" not in serialized
    assert "password" not in serialized.lower()
    assert "ma_api_token" not in serialized.lower()
    assert "entry.options" not in serialized.lower()
    assert "entry.data" not in serialized.lower()


@pytest.mark.asyncio
async def test_overview_does_not_query_supervisor(hass, hass_ws_client):
    supervisor = SimpleNamespace(
        available=True,
        manager_ready=True,
        async_get_info=AsyncMock(side_effect=AssertionError("no Supervisor I/O")),
    )
    await _setup(hass, runtime=_runtime(supervisor=supervisor))
    client = await hass_ws_client(hass)

    result = await _call(client, {"type": "alexa_ma_skill/overview"})
    assert result["success"] is True
    assert result["result"]["addon"]["available"] is True
    assert result["result"]["addon"]["state"] == "running"
    supervisor.async_get_info.assert_not_awaited()


@pytest.mark.asyncio
async def test_overview_requires_entry_when_multiple(hass, hass_ws_client):
    await _setup(hass, entries=2)
    client = await hass_ws_client(hass)
    result = await _call(client, {"type": "alexa_ma_skill/overview"})
    assert result["success"] is False
    assert result["error"]["code"] == "entry_required"

    result = await _call(
        client, {"type": "alexa_ma_skill/overview", "entry_id": "missing"}
    )
    assert result["success"] is False
    assert result["error"]["code"] == "entry_not_found"


@pytest.mark.asyncio
async def test_not_loaded_error(hass, hass_ws_client):
    async_register_websocket_commands(hass)
    client = await hass_ws_client(hass)
    result = await _call(client, {"type": "alexa_ma_skill/overview"})
    assert result["success"] is False
    assert result["error"]["code"] == "not_loaded"


@pytest.mark.asyncio
async def test_refresh_runs_update_and_is_throttled(hass, hass_ws_client):
    await _setup(hass)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    runtime = hass.data[DOMAIN][entry.entry_id]
    client = await hass_ws_client(hass)

    result = await _call(
        client, {"type": "alexa_ma_skill/refresh", "entry_id": entry.entry_id}
    )
    assert result["success"] is True
    assert result["result"]["refreshed"] is True
    assert runtime.coordinator.refresh_calls == 1

    result = await _call(
        client, {"type": "alexa_ma_skill/refresh", "entry_id": entry.entry_id}
    )
    assert result["success"] is True
    assert result["result"]["refreshed"] is False
    assert runtime.coordinator.refresh_calls == 1


@pytest.mark.asyncio
async def test_refresh_returns_the_updated_snapshot(hass, hass_ws_client):
    async def update(coordinator: FakeCoordinator) -> None:
        coordinator.data = replace(coordinator.data, addon_version="9.9.9")

    await _setup(hass, runtime=_runtime(refresh=update))
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    client = await hass_ws_client(hass)

    result = await _call(
        client, {"type": "alexa_ma_skill/refresh", "entry_id": entry.entry_id}
    )
    assert result["success"] is True
    assert result["result"]["refreshed"] is True
    assert result["result"]["overview"]["addon"]["version"] == "9.9.9"


@pytest.mark.asyncio
async def test_refresh_between_panel_and_coordinator_cooldowns_runs(
    hass, hass_ws_client
):
    await _setup(hass)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    runtime = hass.data[DOMAIN][entry.entry_id]
    client = await hass_ws_client(hass)

    first = await _call(
        client, {"type": "alexa_ma_skill/refresh", "entry_id": entry.entry_id}
    )
    assert first["success"] is True
    assert first["result"]["refreshed"] is True

    # The panel allows a retry after 5 s, while the coordinator debouncer
    # would wait 10 s. Move the panel cooldown clock forward by 6 s.
    hass.data[PANEL_STATE_KEY]["refresh_last"][entry.entry_id] -= 6.0

    second = await _call(
        client, {"type": "alexa_ma_skill/refresh", "entry_id": entry.entry_id}
    )
    assert second["success"] is True
    assert second["result"]["refreshed"] is True
    assert runtime.coordinator.refresh_calls == 2


@pytest.mark.asyncio
async def test_concurrent_refresh_runs_only_once(hass, hass_ws_client):
    await _setup(hass)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    runtime = hass.data[DOMAIN][entry.entry_id]
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_refresh(_coordinator: FakeCoordinator) -> None:
        started.set()
        await release.wait()

    runtime.coordinator.on_refresh = slow_refresh
    first_client = await hass_ws_client(hass)
    second_client = await hass_ws_client(hass)

    first_task = asyncio.create_task(
        _call(
            first_client,
            {"type": "alexa_ma_skill/refresh", "entry_id": entry.entry_id},
        )
    )
    await asyncio.wait_for(started.wait(), timeout=5)

    second = await _call(
        second_client,
        {"type": "alexa_ma_skill/refresh", "entry_id": entry.entry_id},
    )
    assert second["success"] is True
    assert second["result"]["refreshed"] is False

    release.set()
    first = await asyncio.wait_for(first_task, timeout=5)
    assert first["success"] is True
    assert first["result"]["refreshed"] is True
    assert runtime.coordinator.refresh_calls == 1


@pytest.mark.asyncio
async def test_refresh_failure_starts_cooldown(hass, hass_ws_client):
    async def fail(coordinator: FakeCoordinator) -> None:
        coordinator.last_update_success = False

    await _setup(hass, runtime=_runtime(refresh=fail))
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    runtime = hass.data[DOMAIN][entry.entry_id]
    client = await hass_ws_client(hass)

    result = await _call(
        client, {"type": "alexa_ma_skill/refresh", "entry_id": entry.entry_id}
    )
    assert result["success"] is False
    assert result["error"]["code"] == "refresh_failed"
    assert runtime.coordinator.refresh_calls == 1

    # A failing refresh must not be retried immediately.
    result = await _call(
        client, {"type": "alexa_ma_skill/refresh", "entry_id": entry.entry_id}
    )
    assert result["success"] is True
    assert result["result"]["refreshed"] is False
    assert runtime.coordinator.refresh_calls == 1


@pytest.mark.asyncio
async def test_refresh_entry_removed_during_request(hass, hass_ws_client):
    await _setup(hass)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    runtime = hass.data[DOMAIN][entry.entry_id]

    async def remove(_coordinator: FakeCoordinator) -> None:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    runtime.coordinator.on_refresh = remove
    client = await hass_ws_client(hass)

    result = await _call(
        client, {"type": "alexa_ma_skill/refresh", "entry_id": entry.entry_id}
    )
    assert result["success"] is False
    assert result["error"]["code"] == "entry_not_found"


@pytest.mark.asyncio
async def test_unknown_fields_are_rejected(hass, hass_ws_client):
    await _setup(hass)
    client = await hass_ws_client(hass)
    result = await _call(
        client, {"type": "alexa_ma_skill/overview", "unexpected": True}
    )
    assert result["success"] is False
    assert result["error"]["code"] == "invalid_format"


@pytest.mark.asyncio
async def test_non_admin_is_rejected(hass, hass_ws_client):
    await _setup(hass)
    user = MockUser(is_owner=False).add_to_hass(hass)
    refresh_token = await hass.auth.async_create_refresh_token(user, "test")
    token = hass.auth.async_create_access_token(refresh_token)
    client = await hass_ws_client(hass, access_token=token)
    result = await _call(client, {"type": "alexa_ma_skill/entries"})
    assert result["success"] is False
    assert result["error"]["code"] == "unauthorized"
