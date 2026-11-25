"""Tests for the sanitized panel data layer."""

from __future__ import annotations

import json
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

try:
    import homeassistant  # noqa: F401

    from custom_components.alexa_ma_skill.api import DetailedStatus
    from custom_components.alexa_ma_skill.const import DOMAIN, StatusLevel
    from custom_components.alexa_ma_skill.coordinator import AlexaMaSkillData
    from custom_components.alexa_ma_skill.panel_data import (
        PanelEntryNotFound,
        PanelEntryRequired,
        PanelNotLoaded,
        build_addon_summary,
        build_entries,
        build_overview_payload,
        resolve_entry,
    )
    from custom_components.alexa_ma_skill.util import (
        mask_skill_id,
        mask_skill_identifier,
    )

    HA_AVAILABLE = True
except ImportError:
    HA_AVAILABLE = False

GOOD_ID = "amzn1.ask.skill.11111111-1111-1111-1111-111111111111"
OTHER_ID = "amzn1.ask.skill.99999999-9999-9999-9999-999999999999"
THIRD_ID = "amzn1.ask.skill.abcdef01-2345-6789-abcd-ef0123456789"
MISTYPED_SECRET = "mistyped-secret-0123456789"


def _detailed() -> DetailedStatus:
    return DetailedStatus(
        skill_html="<span>ok</span>",
        skill_ask_html="endpoint matches, testing enabled",
        ma_api_html='<pre>{"streamUrl":"https://stream.example.test/a?token=x"}</pre>',
        alexa_api_html="ok",
        metadata_html="meta",
        invocations_html="invocations",
        created=True,
        skill_ask_level=StatusLevel.GREEN,
        ma_api_level=StatusLevel.GREEN,
        alexa_api_level=StatusLevel.GREEN,
        ma_api_details={"streamUrl": "https://stream.example.test/a?token=x"},
        stream_url="https://stream.example.test/a?token=x",
        detected_skill_id=OTHER_ID,
    )


def _data(
    *,
    detailed: DetailedStatus | None = None,
    last_check: datetime | None = None,
    detailed_error: str | None = None,
    installed: bool | None = True,
    online: bool = True,
    reachable: bool = True,
    configured: str = GOOD_ID,
    detected: str | None = OTHER_ID,
    suggested: str | None = None,
    matches: bool | None = False,
) -> AlexaMaSkillData:
    return AlexaMaSkillData(
        reachable=reachable,
        http_status=200 if reachable else 0,
        detailed=detailed,
        last_check=last_check,
        detailed_error=detailed_error,
        container_online=online,
        addon_installed=installed,
        addon_hostname="local-alexa-ma-skill",
        addon_version="0.2.0",
        https_skill_ok=True,
        https_stream_ok=True,
        stream_url_present=detailed is not None,
        detected_skill_id=detected,
        configured_skill_id=configured,
        skill_id_matches=matches,
        suggested_skill_id=suggested,
    )


def _entry(
    entry_id: str = "entry-1",
    title: str = "Alexa MA",
    skill_id: str = GOOD_ID,
):
    return SimpleNamespace(
        entry_id=entry_id,
        title=title,
        data={},
        options={
            "managed": True,
            "addon_slug": "local_alexa_ma_skill",
            "skill_hostname": "skill.example.test",
            "ma_hostname": "stream.example.test",
            "skill_id": skill_id,
            "ma_api_url": "http://192.0.2.10:8095",
        },
    )


def _runtime(data: AlexaMaSkillData | None = None):
    return SimpleNamespace(
        coordinator=SimpleNamespace(
            data=data if data is not None else _data(detailed=_detailed()),
            last_update_success=True,
            async_request_refresh=AsyncMock(),
        ),
        checklist=SimpleNamespace(confirmations={}),
        supervisor=SimpleNamespace(
            available=False,
            manager_ready=False,
            async_get_info=AsyncMock(side_effect=AssertionError("no Supervisor I/O")),
        ),
    )


def _hass(entries: list[SimpleNamespace], runtimes: dict[str, Any]):
    return SimpleNamespace(
        data={DOMAIN: runtimes},
        config=SimpleNamespace(language="en"),
        config_entries=SimpleNamespace(
            async_entries=lambda domain: entries,
        ),
    )


RUNNING_ADDON = {
    "available": True,
    "installed": True,
    "running": True,
    "state": "running",
    "version": "0.2.0",
    "hostname": "local-alexa-ma-skill",
    "error": None,
}


@unittest.skipUnless(HA_AVAILABLE, "Home Assistant libraries are not installed")
class PanelDataTest(unittest.TestCase):
    """Validate entry selection and the overview allowlist."""

    def test_entries_only_include_safe_fields(self) -> None:
        entry = _entry(title=f"Alexa MA {GOOD_ID}")
        runtime = _runtime()
        hass = _hass([entry], {entry.entry_id: runtime})
        entries = build_entries(hass)
        self.assertEqual(len(entries), 1)
        self.assertEqual(
            set(entries[0]), {"entry_id", "title", "managed", "addon_slug"}
        )
        self.assertEqual(entries[0]["addon_slug"], "local_alexa_ma_skill")
        self.assertNotIn(GOOD_ID, json.dumps(entries))

    def test_entry_resolution(self) -> None:
        entry = _entry()
        runtime = _runtime()
        hass = _hass([entry], {entry.entry_id: runtime})
        self.assertEqual(resolve_entry(hass, None)[0], entry)
        self.assertEqual(resolve_entry(hass, entry.entry_id)[0], entry)

        with self.assertRaises(PanelEntryNotFound):
            resolve_entry(hass, "missing")

        with self.assertRaises(PanelNotLoaded):
            resolve_entry(_hass([], {}), None)

        second = _entry("entry-2", "Second")
        hass_two = _hass(
            [entry, second], {entry.entry_id: runtime, second.entry_id: _runtime()}
        )
        with self.assertRaises(PanelEntryRequired):
            resolve_entry(hass_two, None)

    def test_overview_is_sanitized(self) -> None:
        entry = _entry()
        runtime = _runtime()
        hass = _hass([entry], {entry.entry_id: runtime})
        payload = build_overview_payload(hass, entry, runtime, RUNNING_ADDON, "0.2.0")
        self.assertEqual(payload["state"], "connected")
        self.assertEqual(payload["checklist"]["total"], 16)
        self.assertEqual(payload["music_assistant"]["level"], "green")
        self.assertEqual(payload["addon"]["version"], "0.2.0")
        self.assertEqual(
            payload["alexa"]["configured_skill_id_masked"], mask_skill_id(GOOD_ID)
        )
        self.assertEqual(
            payload["alexa"]["detected_skill_id_masked"], mask_skill_id(OTHER_ID)
        )

        serialized = json.dumps(payload)
        for full_id in (GOOD_ID, OTHER_ID, THIRD_ID):
            self.assertNotIn(full_id, serialized)
        self.assertNotIn("stream.example.test", serialized)
        self.assertNotIn("token=x", serialized)
        self.assertNotIn("password", serialized.lower())
        self.assertNotIn("ma_api_token", serialized.lower())
        self.assertNotIn("entry.data", serialized)
        self.assertNotIn("entry.options", serialized)

    def test_skill_id_fields_never_expose_full_values(self) -> None:
        # Three full IDs enter through three different paths: the configured
        # value, the coordinator snapshot, and the config entry title.
        entry = _entry(title=f"Alexa MA {THIRD_ID}", skill_id=THIRD_ID)
        data = _data(detected=GOOD_ID, suggested=OTHER_ID, matches=False)
        runtime = _runtime(data)
        hass = _hass([entry], {entry.entry_id: runtime})

        payload = build_overview_payload(hass, entry, runtime, RUNNING_ADDON, "0.2.0")
        alexa = payload["alexa"]
        self.assertEqual(alexa["configured_skill_id_masked"], mask_skill_id(THIRD_ID))
        self.assertEqual(alexa["detected_skill_id_masked"], mask_skill_id(GOOD_ID))
        self.assertIs(alexa["skill_id_matches"], False)
        self.assertIs(alexa["skill_id_suggested"], True)
        # The masked detected ID already carries the suggested value.
        self.assertNotIn("suggested_skill_id", alexa)
        self.assertIn(mask_skill_id(THIRD_ID), payload["entry"]["title"])

        serialized = json.dumps(payload)
        for full_id in (GOOD_ID, OTHER_ID, THIRD_ID):
            self.assertNotIn(full_id, serialized)

    def test_skill_id_suggested_is_false_when_configured_matches(self) -> None:
        entry = _entry(skill_id=GOOD_ID)
        data = _data(detected=GOOD_ID, suggested=None, matches=True)
        runtime = _runtime(data)
        hass = _hass([entry], {entry.entry_id: runtime})
        payload = build_overview_payload(hass, entry, runtime, RUNNING_ADDON, "0.2.0")
        self.assertIs(payload["alexa"]["skill_id_matches"], True)
        self.assertIs(payload["alexa"]["skill_id_suggested"], False)

    def test_no_data_keeps_skill_fields_unknown(self) -> None:
        entry = _entry()
        runtime = SimpleNamespace(
            coordinator=SimpleNamespace(
                data=None, last_update_success=True, async_request_refresh=AsyncMock()
            ),
            checklist=SimpleNamespace(confirmations={}),
            supervisor=None,
        )
        hass = _hass([entry], {entry.entry_id: runtime})
        payload = build_overview_payload(hass, entry, runtime, RUNNING_ADDON, None)
        self.assertEqual(payload["state"], "error")
        self.assertIsNone(payload["alexa"]["detected_skill_id_masked"])
        self.assertIsNone(payload["alexa"]["skill_id_suggested"])
        self.assertIsNone(payload["checklist"])

    def test_masking_rejects_other_formats(self) -> None:
        self.assertIsNone(mask_skill_identifier(None))
        self.assertIsNone(mask_skill_identifier("   "))
        self.assertEqual(mask_skill_identifier(MISTYPED_SECRET), "***")
        self.assertEqual(mask_skill_identifier("amzn1.ask.skill"), "***")
        self.assertEqual(mask_skill_identifier(GOOD_ID), mask_skill_id(GOOD_ID))

        entry = _entry(skill_id=MISTYPED_SECRET)
        runtime = _runtime(_data(detected=None, suggested=None))
        hass = _hass([entry], {entry.entry_id: runtime})
        payload = build_overview_payload(hass, entry, runtime, RUNNING_ADDON, "0.2.0")
        self.assertEqual(payload["alexa"]["configured_skill_id_masked"], "***")
        serialized = json.dumps(payload)
        self.assertNotIn(MISTYPED_SECRET, serialized)
        self.assertNotIn(MISTYPED_SECRET[:16], serialized)

    def test_states(self) -> None:
        entry = _entry()
        runtime = _runtime()
        hass = _hass([entry], {entry.entry_id: runtime})

        def state(config, data, addon):
            local_entry = SimpleNamespace(
                entry_id="entry-1", title="Alexa MA", data={}, options=config
            )
            return build_overview_payload(
                hass, local_entry, _runtime(data), addon, "0.2.0"
            )["state"]

        base_addon = {"installed": True, "running": True}
        self.assertEqual(
            state({}, _data(detailed=_detailed()), base_addon), "config_incomplete"
        )
        self.assertEqual(
            state(
                {
                    "managed": True,
                    "skill_hostname": "skill.example.test",
                    "skill_id": GOOD_ID,
                },
                _data(detailed=_detailed()),
                {"installed": False, "running": False},
            ),
            "addon_not_found",
        )
        self.assertEqual(
            state(
                {
                    "managed": True,
                    "skill_hostname": "skill.example.test",
                    "skill_id": GOOD_ID,
                },
                _data(detailed=_detailed()),
                {"installed": True, "running": False},
            ),
            "addon_stopped",
        )
        red_detailed = replace(_detailed(), ma_api_level=StatusLevel.RED)
        self.assertEqual(
            state(
                {
                    "managed": True,
                    "skill_hostname": "skill.example.test",
                    "skill_id": GOOD_ID,
                },
                _data(detailed=red_detailed),
                base_addon,
            ),
            "ma_unavailable",
        )
        self.assertEqual(
            state(
                {
                    "managed": True,
                    "skill_hostname": "skill.example.test",
                    "skill_id": GOOD_ID,
                },
                _data(detailed=_detailed(), detailed_error="connection failed"),
                base_addon,
            ),
            "error",
        )

    def test_stale_flag(self) -> None:
        entry = _entry()
        runtime = _runtime(
            _data(
                detailed=_detailed(),
                last_check=datetime.now(UTC) - timedelta(minutes=30),
            )
        )
        hass = _hass([entry], {entry.entry_id: runtime})
        payload = build_overview_payload(
            hass, entry, runtime, {"installed": True, "running": True}, "0.2.0"
        )
        self.assertTrue(payload["stale"])

    def test_addon_summary_is_pure_and_has_no_options(self) -> None:
        supervisor = SimpleNamespace(
            available=True,
            manager_ready=True,
            async_get_info=MagicMock(
                side_effect=AssertionError("summary must not call the Supervisor")
            ),
        )
        runtime = SimpleNamespace(supervisor=supervisor)
        summary = build_addon_summary(runtime, _data(detailed=_detailed()))
        self.assertTrue(summary["available"])
        self.assertTrue(summary["installed"])
        self.assertTrue(summary["running"])
        self.assertEqual(summary["state"], "running")
        self.assertEqual(summary["version"], "0.2.0")
        self.assertIsNone(summary["error"])
        self.assertNotIn("options", summary)
        supervisor.async_get_info.assert_not_called()

        stopped = build_addon_summary(runtime, _data(installed=True, online=False))
        self.assertEqual(stopped["state"], "not_running")

        missing = build_addon_summary(runtime, _data(installed=False, online=False))
        self.assertEqual(missing["state"], "not_installed")

        unavailable = build_addon_summary(
            SimpleNamespace(supervisor=None), _data(installed=None, online=True)
        )
        self.assertFalse(unavailable["available"])
        self.assertEqual(unavailable["error"], "supervisor_unavailable")
        self.assertIsNone(unavailable["state"])

        # Without a live Supervisor the summary keeps the last coordinator
        # snapshot instead of inventing a state.
        last_known = build_addon_summary(
            SimpleNamespace(supervisor=None), _data(installed=True, online=True)
        )
        self.assertFalse(last_known["available"])
        self.assertEqual(last_known["state"], "running")

        self.assertNotIn("secret", json.dumps(summary))
