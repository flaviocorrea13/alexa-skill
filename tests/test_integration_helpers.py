"""Unit tests for integration helpers that do not need a running HA instance.

These tests run with the Home Assistant libraries installed (for example the
project virtualenv). They are skipped automatically when Home Assistant is not
available.
"""

from __future__ import annotations

import asyncio
import json
import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, ClassVar
from unittest.mock import patch

try:
    import homeassistant  # noqa: F401

    from custom_components.alexa_ma_skill.api import (
        AlexaMaSkillApi,
        DetailedStatus,
        SetupStatus,
        SimpleStatus,
    )
    from custom_components.alexa_ma_skill.binary_sensor import (
        _skill_id_attributes,
        _skill_id_valid,
    )
    from custom_components.alexa_ma_skill.config_flow import (
        AlexaMaSkillOptionsFlow,
        _clean_hostname,
        _clean_ma_api_url,
        _entry_title,
        _FlowError,
        _option_matches,
        _preserve_password,
        _preserve_token,
        _safe_input,
        _validate_addon_options,
        _validate_ma_api_pair,
    )
    from custom_components.alexa_ma_skill.const import DOMAIN, StatusLevel
    from custom_components.alexa_ma_skill.coordinator import (
        AlexaMaSkillCoordinator,
        AlexaMaSkillData,
    )
    from custom_components.alexa_ma_skill.diagnostics import (
        TO_REDACT,
        _coordinator_data,
        _mask_skill_id_fields,
        async_get_config_entry_diagnostics,
    )
    from custom_components.alexa_ma_skill.https import _skill_status_ok
    from custom_components.alexa_ma_skill.entity import (
        AlexaMaSkillEntity,
        safe_entry_title,
    )
    from custom_components.alexa_ma_skill.sensor import (
        SENSORS,
        AlexaMaSkillSensor,
        AlexaMaSkillSetupChecklistSensor,
        _overall_status,
        _setup_checklist_attributes,
    )
    from custom_components.alexa_ma_skill.setup import (
        _RESULT_TEXTS,
        _STEP_TEXTS,
        STEP_DEFINITIONS,
        ChecklistManager,
        build_setup_checklist,
    )
    from custom_components.alexa_ma_skill.supervisor import (
        AddonCandidate,
        AlexaMaSkillSupervisor,
        SupervisorOperationError,
        addon_hostname,
    )
    from custom_components.alexa_ma_skill.util import (
        extract_skill_id,
        is_valid_skill_id,
        mask_skill_id,
        mask_skill_identifier,
        mask_skill_ids_in_text,
    )

    HA_AVAILABLE = True
except ImportError:
    HA_AVAILABLE = False

    class _Missing:
        """Placeholder used when Home Assistant is not installed."""

    AlexaMaSkillApi = _Missing


GOOD_ID = "amzn1.ask.skill.11111111-1111-1111-1111-111111111111"
OTHER_ID = "amzn1.ask.skill.99999999-9999-9999-9999-999999999999"
FAKE_SLUG = "0a1b2c3d_alexa_ma_skill"


def _step(attrs: dict[str, Any], step_id: str) -> dict[str, Any]:
    """Return one checklist step from the attributes."""
    return next(step for step in attrs["checklist"] if step["id"] == step_id)


@unittest.skipUnless(HA_AVAILABLE, "Home Assistant libraries are not installed")
class ConfigFlowHelperTest(unittest.TestCase):
    """Validate hostname, URL and add-on option helpers."""

    def test_hostname_accepts_bare_hostname(self) -> None:
        self.assertEqual(_clean_hostname("skill.example.com"), "skill.example.com")
        self.assertEqual(_clean_hostname("skill.example.com."), "skill.example.com")
        self.assertEqual(_clean_hostname("", required=False), "")

    def test_hostname_rejects_invalid_forms(self) -> None:
        for value in (
            "https://skill.example.com",
            "skill.example.com/setup",
            "skill.example.com:5000",
            "skill example.com",
        ):
            with self.subTest(value=value), self.assertRaises(_FlowError):
                _clean_hostname(value)

    def test_ma_api_url_validation(self) -> None:
        for value in (
            "http://192.0.2.10:8095",
            "https://ma.example.com:8095/",
            "ws://192.0.2.10:8095",
            "wss://ma.example.com:8095/ws",
        ):
            with self.subTest(value=value):
                self.assertEqual(_clean_ma_api_url(value), value)
        for value in (
            "ftp://192.0.2.10:8095",
            "192.0.2.10:8095",
            "http://user:pass@192.0.2.10:8095",
            "http://192.0.2.10:8095 with space",
        ):
            with self.subTest(value=value), self.assertRaises(_FlowError):
                _clean_ma_api_url(value)

    def test_ma_api_pair_allows_url_without_token(self) -> None:
        self.assertEqual(_validate_ma_api_pair("http://ma:8095", ""), "")
        self.assertEqual(_validate_ma_api_pair("http://ma:8095", " tok "), "tok")
        self.assertEqual(
            _validate_ma_api_pair("http://ma:8095", "", "existing"), "existing"
        )
        self.assertEqual(_validate_ma_api_pair("", "", "existing"), "")

    def test_safe_input_redacts_credentials(self) -> None:
        self.assertEqual(_safe_input("user:pass@example.com"), "***@example.com")
        self.assertEqual(
            _safe_input("https://user:pass@example.com"), "***@example.com"
        )
        self.assertEqual(_safe_input("example.com"), "example.com")
        self.assertEqual(_safe_input(None), "")

    def test_options_schema_optional_ma_hostname_and_selector(self) -> None:
        """The options schema follows the add-on schema and adds a slug selector."""
        flow = object.__new__(AlexaMaSkillOptionsFlow)
        config = {
            "skill_hostname": "skill.example.com",
            "ma_hostname": "",
            "username": "user",
            "locale": "pt-BR",
            "managed": True,
        }
        schema = flow._options_schema(config, managed=True)
        keys = {
            getattr(key, "schema", None): type(key).__name__ for key in schema.schema
        }
        self.assertEqual(keys["skill_hostname"], "Required")
        self.assertEqual(keys["ma_hostname"], "Optional")
        self.assertNotIn("addon_slug", keys)

        candidates = [
            AddonCandidate(slug=FAKE_SLUG, name="Alexa MA Skill", version="0.1.1"),
            AddonCandidate(
                slug="abcdef01_alexa_ma_skill",
                name="Alexa MA Skill",
                version="0.1.1",
            ),
        ]
        schema = flow._options_schema(
            config,
            managed=True,
            addon_candidates=candidates,
            selected_addon_slug=FAKE_SLUG,
        )
        keys = {
            getattr(key, "schema", None): type(key).__name__ for key in schema.schema
        }
        self.assertEqual(keys["addon_slug"], "Required")

    def test_ma_api_pair_rejects_token_without_url(self) -> None:
        with self.assertRaises(_FlowError):
            _validate_ma_api_pair("", "tok")
        self.assertEqual(_validate_ma_api_pair("", "********"), "")

    def test_secret_preservation(self) -> None:
        self.assertEqual(_preserve_password("new", "addon", "entry"), "new")
        self.assertEqual(_preserve_password("", "addon", "entry"), "addon")
        self.assertEqual(_preserve_password("", "/data/path", "entry"), "entry")
        self.assertEqual(_preserve_password("", "", "entry"), "entry")
        self.assertEqual(_preserve_token("new", "addon", "entry", has_url=True), "new")
        self.assertEqual(_preserve_token("", "addon", "entry", has_url=True), "addon")
        self.assertEqual(_preserve_token("", "", "entry", has_url=True), "entry")
        self.assertEqual(_preserve_token("", "addon", "entry", has_url=False), "")
        self.assertEqual(_preserve_password("********", "addon", "entry"), "addon")
        self.assertEqual(
            _preserve_token("********", "addon", "entry", has_url=True), "addon"
        )
        self.assertEqual(_preserve_password("", "", "********"), "")
        self.assertEqual(_preserve_token("", "", "********", has_url=True), "")

    def test_option_matching_and_preservation(self) -> None:
        self.assertTrue(_option_matches({"PORT": "5000"}, "PORT", "5000"))
        self.assertFalse(_option_matches({"PORT": "5001"}, "PORT", "5000"))
        self.assertTrue(_option_matches({"ENABLE_APL": True}, "ENABLE_APL", "true"))
        _validate_addon_options(
            {"SKILL_HOSTNAME": "skill.example.com", "UNKNOWN": "keep"},
            {"SKILL_HOSTNAME": "skill.example.com"},
        )
        with self.assertRaises(_FlowError):
            _validate_addon_options(
                {"SKILL_HOSTNAME": "other.example.com"},
                {"SKILL_HOSTNAME": "skill.example.com"},
            )

    def test_skill_status_rejects_404(self) -> None:
        self.assertTrue(_skill_status_ok(200))
        self.assertTrue(_skill_status_ok(401))
        self.assertTrue(_skill_status_ok(403))
        self.assertFalse(_skill_status_ok(404))
        self.assertFalse(_skill_status_ok(500))


class FakeHassConfig:
    """Minimal hass.config for options-flow tests."""

    language = "pt-BR"


class FakeOptionsHass:
    """Minimal hass object for options-flow tests."""

    config = FakeHassConfig()


@unittest.skipUnless(HA_AVAILABLE, "Home Assistant libraries are not installed")
class OptionsFlowRestartTest(unittest.TestCase):
    """Validate the explicit restart-confirmation step."""

    class FakeSupervisor:
        def __init__(self, fail: bool = False) -> None:
            self.fail = fail
            self.restarted = False

        async def async_start_or_restart(self) -> None:
            if self.fail:
                raise SupervisorOperationError("restart failed")
            self.restarted = True

    def _flow(self, supervisor, *, api=None):
        flow = object.__new__(AlexaMaSkillOptionsFlow)
        flow.hass = FakeOptionsHass()
        flow._pending_config = {"managed": True}
        flow._pending_supervisor = supervisor
        flow._pending_api = api
        flow._pending_changes = ["SKILL_HOSTNAME"]
        flow.created = None

        def create_entry(title, data):
            flow.created = data
            return {"type": "create_entry", "data": data}

        flow.async_create_entry = create_entry
        return flow

    def test_restart_is_skipped_without_consent(self) -> None:
        supervisor = self.FakeSupervisor()
        flow = self._flow(supervisor)
        with patch(
            "custom_components.alexa_ma_skill.config_flow._notify_options_issue"
        ):
            result = asyncio.run(flow.async_step_restart_confirm({"confirm": False}))
        self.assertFalse(supervisor.restarted)
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(flow.created, {"managed": True})

    def test_restart_runs_after_confirmation(self) -> None:
        supervisor = self.FakeSupervisor()
        flow = self._flow(supervisor)
        result = asyncio.run(flow.async_step_restart_confirm({"confirm": True}))
        self.assertTrue(supervisor.restarted)
        self.assertEqual(result["type"], "create_entry")

    def test_restart_failure_still_saves_options(self) -> None:
        supervisor = self.FakeSupervisor(fail=True)
        flow = self._flow(supervisor)
        with patch(
            "custom_components.alexa_ma_skill.config_flow._notify_options_issue"
        ) as notify:
            result = asyncio.run(flow.async_step_restart_confirm({"confirm": True}))
        self.assertEqual(result["type"], "create_entry")
        self.assertTrue(notify.called)


@unittest.skipUnless(HA_AVAILABLE, "Home Assistant libraries are not installed")
class SetupFlowTest(unittest.TestCase):
    """Validate the setup form processing without a full HA instance."""

    class FakeStore:
        def __init__(self) -> None:
            self.saved = None

        async def async_save(self, data) -> None:
            self.saved = data

    class BlockingCoordinator:
        """Coordinator whose configured refresh call waits for a release."""

        def __init__(self, data, updated, *, block_call: int = 1) -> None:
            self.data = data
            self.updated = updated
            self.last_update_success = True
            self.block_call = block_call
            self.calls = 0
            self.started = asyncio.Event()
            self.release = asyncio.Event()

        async def async_refresh(self) -> None:
            self.calls += 1
            if self.calls != self.block_call:
                return
            self.started.set()
            await self.release.wait()
            self.data = self.updated

    def _make_flow(self, coordinator, manager):
        entry = SimpleNamespace(entry_id="entry", data={}, options={})
        runtime = SimpleNamespace(coordinator=coordinator, checklist=manager)
        hass = SimpleNamespace(
            data={DOMAIN: {"entry": runtime}},
            config=SimpleNamespace(language="pt-BR"),
            config_entries=SimpleNamespace(
                async_get_known_entry=lambda entry_id: entry
            ),
        )
        flow = object.__new__(AlexaMaSkillOptionsFlow)
        flow.hass = hass
        flow.handler = "entry"
        flow._config_entry = entry
        flow.async_show_form = lambda **kwargs: {
            "type": "form",
            **kwargs,
        }
        flow.async_show_menu = lambda **kwargs: {"type": "menu", **kwargs}
        flow.async_abort = lambda **kwargs: {"type": "abort", **kwargs}
        return flow

    @staticmethod
    def _checklist_spy(calls):
        def spy(config, data, language, confirmations):
            calls.append(data)
            return build_setup_checklist(config, data, language, confirmations)

        return spy

    def test_setup_form_reads_and_stores_manual_steps(self) -> None:
        manager = ChecklistManager(self.FakeStore(), {"confirmations": {}})

        async def refresh() -> None:
            return None

        coordinator = SimpleNamespace(
            data=_data(),
            async_refresh=refresh,
            last_update_success=True,
        )
        flow = self._make_flow(coordinator, manager)

        result = asyncio.run(flow.async_step_setup(None))
        self.assertEqual(result["step_id"], "setup")
        self.assertIn("summary", result["description_placeholders"])
        self.assertIn("progress", result["description_placeholders"])

        result = asyncio.run(flow.async_step_setup({"local_setup": True}))
        self.assertTrue(manager.confirmed("local_setup"))
        self.assertEqual(result["step_id"], "setup")

    def test_initial_open_waits_for_refresh_and_uses_updated_data(self) -> None:
        old_data = _data()
        new_data = _data(addon_version="9.9.9")
        manager = ChecklistManager(self.FakeStore(), {"confirmations": {}})
        coordinator = self.BlockingCoordinator(old_data, new_data)
        flow = self._make_flow(coordinator, manager)
        calls = []

        async def scenario():
            with patch(
                "custom_components.alexa_ma_skill.config_flow.build_setup_checklist",
                side_effect=self._checklist_spy(calls),
            ):
                task = asyncio.create_task(flow.async_step_setup(None))
                await asyncio.wait_for(coordinator.started.wait(), timeout=1)
                self.assertFalse(task.done())
                self.assertEqual(calls, [])
                coordinator.release.set()
                return await asyncio.wait_for(task, timeout=1)

        result = asyncio.run(scenario())

        self.assertEqual(calls[-1], new_data)
        self.assertEqual(result["step_id"], "setup")

    def test_saving_waits_for_refresh_and_uses_updated_data(self) -> None:
        old_data = _data()
        new_data = _data(addon_version="9.9.9")
        manager = ChecklistManager(self.FakeStore(), {"confirmations": {}})
        coordinator = self.BlockingCoordinator(old_data, new_data, block_call=3)
        flow = self._make_flow(coordinator, manager)
        calls = []

        async def scenario():
            with patch(
                "custom_components.alexa_ma_skill.config_flow.build_setup_checklist",
                side_effect=self._checklist_spy(calls),
            ):
                await flow.async_step_setup(None)
                self.assertEqual(calls, [old_data])
                task = asyncio.create_task(flow.async_step_setup({"local_setup": True}))
                await asyncio.wait_for(coordinator.started.wait(), timeout=1)
                self.assertFalse(task.done())
                self.assertTrue(manager.confirmed("local_setup"))
                self.assertEqual(calls, [old_data, old_data])
                coordinator.release.set()
                return await asyncio.wait_for(task, timeout=1)

        result = asyncio.run(scenario())

        self.assertEqual(calls, [old_data, old_data, new_data])
        self.assertTrue(manager.confirmed("local_setup"))
        self.assertEqual(result["step_id"], "setup")

    def test_refresh_exception_keeps_form_usable_and_logs_warning(self) -> None:
        data = _data()
        manager = ChecklistManager(self.FakeStore(), {"confirmations": {}})
        calls = []

        async def failing_refresh() -> None:
            raise RuntimeError("offline")

        coordinator = SimpleNamespace(
            data=data,
            async_refresh=failing_refresh,
            last_update_success=True,
        )
        flow = self._make_flow(coordinator, manager)

        with (
            patch(
                "custom_components.alexa_ma_skill.config_flow.build_setup_checklist",
                side_effect=self._checklist_spy(calls),
            ),
            self.assertLogs(
                "custom_components.alexa_ma_skill.config_flow", level="WARNING"
            ) as logs,
        ):
            result = asyncio.run(flow.async_step_setup(None))

        self.assertEqual(result["step_id"], "setup")
        self.assertEqual(calls, [data])
        self.assertTrue(any("failed" in line for line in logs.output))

    def test_failed_refresh_state_keeps_form_usable_and_logs_warning(self) -> None:
        data = _data()
        manager = ChecklistManager(self.FakeStore(), {"confirmations": {}})
        calls = []

        async def refresh() -> None:
            return None

        coordinator = SimpleNamespace(
            data=data,
            async_refresh=refresh,
            last_update_success=False,
        )
        flow = self._make_flow(coordinator, manager)

        with (
            patch(
                "custom_components.alexa_ma_skill.config_flow.build_setup_checklist",
                side_effect=self._checklist_spy(calls),
            ),
            self.assertLogs(
                "custom_components.alexa_ma_skill.config_flow", level="WARNING"
            ) as logs,
        ):
            result = asyncio.run(flow.async_step_setup(None))

        self.assertEqual(result["step_id"], "setup")
        self.assertEqual(calls, [data])
        self.assertTrue(any("outdated" in line for line in logs.output))


@unittest.skipUnless(HA_AVAILABLE, "Home Assistant libraries are not installed")
class ChecklistPersistenceTest(unittest.TestCase):
    """Validate checklist IDs, persistence and selective invalidation."""

    class FakeStore:
        def __init__(self) -> None:
            self.saved = None

        async def async_save(self, data) -> None:
            self.saved = data

    def test_sixteen_stable_steps(self) -> None:
        ids = [definition.id for definition in STEP_DEFINITIONS]
        self.assertEqual(len(ids), 16)
        self.assertEqual(len(set(ids)), 16)
        self.assertEqual(ids[0], "addon_installed")
        self.assertEqual(ids[-1], "commands_tested")

    def test_step_and_result_texts_in_both_languages(self) -> None:
        ids = {definition.id for definition in STEP_DEFINITIONS}
        for language in ("pt", "en"):
            texts = _STEP_TEXTS[language]
            self.assertEqual(set(texts), ids)
            for step_text in texts.values():
                for key in ("title", "description", "fix"):
                    self.assertTrue(step_text[key].strip())
        self.assertEqual(set(_RESULT_TEXTS["pt"]), set(_RESULT_TEXTS["en"]))
        self.assertEqual(
            _RESULT_TEXTS["pt"]["addon_found"], "Add-on encontrado no Supervisor"
        )
        self.assertEqual(
            _RESULT_TEXTS["en"]["addon_found"], "Add-on found in the Supervisor"
        )

    def test_checklist_is_translated(self) -> None:
        config = {"skill_hostname": "skill.example.com", "locale": "pt-BR"}
        _state, pt_attrs = build_setup_checklist(config, _data(), "pt-BR", {})
        _state, en_attrs = build_setup_checklist(config, _data(), "en-US", {})
        self.assertEqual(
            _step(pt_attrs, "addon_installed")["result"],
            "Add-on encontrado no Supervisor",
        )
        self.assertEqual(
            _step(en_attrs, "addon_installed")["result"],
            "Add-on found in the Supervisor",
        )
        self.assertEqual(
            _step(en_attrs, "addon_installed")["title"], "Add-on installed"
        )
        self.assertEqual(
            _step(pt_attrs, "addon_installed")["title"], "Add-on instalado"
        )
        for step in en_attrs["checklist"]:
            self.assertNotIn("ã", step["result"])
            self.assertNotIn("ç", step["how_to_fix"])

    def test_confirm_persist_and_clear(self) -> None:
        store = self.FakeStore()
        manager = ChecklistManager(store, {"confirmations": {}})
        asyncio.run(manager.async_set("amazon_auth", True))
        self.assertTrue(manager.confirmed("amazon_auth"))
        self.assertIn("amazon_auth", manager.confirmations)
        self.assertIn("confirmations", store.saved)
        reloaded = ChecklistManager(store, store.saved)
        self.assertTrue(reloaded.confirmed("amazon_auth"))

        asyncio.run(manager.async_set("amazon_auth", False))
        self.assertFalse(manager.confirmed("amazon_auth"))

    def test_unchecking_prerequisite_clears_dependents(self) -> None:
        store = self.FakeStore()
        manager = ChecklistManager(store, {"confirmations": {}})
        asyncio.run(manager.async_set("amazon_auth", True))
        asyncio.run(manager.async_set("skill_created", True))
        asyncio.run(manager.async_set("provider_configured", True))
        asyncio.run(manager.async_set("commands_tested", True))
        self.assertTrue(manager.confirmed("commands_tested"))
        asyncio.run(manager.async_set("amazon_auth", False))
        self.assertFalse(manager.confirmed("amazon_auth"))
        self.assertFalse(manager.confirmed("skill_created"))
        self.assertFalse(manager.confirmed("provider_configured"))
        self.assertFalse(manager.confirmed("commands_tested"))

    def test_invalidation_keeps_unrelated_confirmations(self) -> None:
        store = self.FakeStore()
        manager = ChecklistManager(
            store,
            {
                "confirmations": {
                    "amazon_auth": {"at": "2026-01-01T00:00:00+00:00"},
                    "skill_created": {"at": "2026-01-01T00:00:00+00:00"},
                    "provider_configured": {"at": "2026-01-01T00:00:00+00:00"},
                    "commands_tested": {"at": "2026-01-01T00:00:00+00:00"},
                }
            },
        )
        asyncio.run(manager.async_clear_for_keys(["SKILL_HOSTNAME"]))
        self.assertTrue(manager.confirmed("amazon_auth"))
        self.assertFalse(manager.confirmed("skill_created"))
        # The provider talks to the add-on through the internal URL, so a public
        # skill hostname change must not discard that confirmation.
        self.assertTrue(manager.confirmed("provider_configured"))
        self.assertFalse(manager.confirmed("commands_tested"))

    def test_addon_slug_clears_manual_steps(self) -> None:
        store = self.FakeStore()
        manager = ChecklistManager(
            store,
            {
                "confirmations": {
                    "amazon_auth": {"at": "2026-01-01T00:00:00+00:00"},
                    "provider_configured": {"at": "2026-01-01T00:00:00+00:00"},
                }
            },
        )
        asyncio.run(manager.async_clear_for_keys(["ADDON_SLUG"]))
        self.assertTrue(manager.confirmed("amazon_auth"))
        self.assertFalse(manager.confirmed("provider_configured"))


@unittest.skipUnless(HA_AVAILABLE, "Home Assistant libraries are not installed")
class UtilAndChecklistTest(unittest.TestCase):
    """Validate ID parsing, masking and checklist semantics."""

    def test_skill_id_parsing_and_masking(self) -> None:
        self.assertEqual(extract_skill_id(f"Created skill: {GOOD_ID}"), GOOD_ID)
        self.assertEqual(extract_skill_id(f"old {OTHER_ID}\nDone. {GOOD_ID}"), GOOD_ID)
        self.assertIsNone(extract_skill_id("nothing"))
        masked = mask_skill_id(GOOD_ID)
        self.assertNotIn(GOOD_ID, masked or "")
        self.assertEqual(
            mask_skill_ids_in_text(f"{GOOD_ID} {OTHER_ID}").count("..."), 2
        )

    def test_checklist_semantics(self) -> None:
        data = _data()
        config = {
            "skill_hostname": "skill.example.com",
            "ma_hostname": "ma.example.com",
            "ma_api_url": "http://ma.example.com:8095",
            "skill_id": GOOD_ID,
            "locale": "pt-BR",
            "managed": True,
        }
        confirmations = {
            step_id: {"at": "2026-01-01T00:00:00+00:00"}
            for step_id in (
                "local_setup",
                "amazon_auth",
                "skill_created",
                "skill_enabled",
                "provider_configured",
                "ma_api_tested",
                "playback_tested",
                "commands_tested",
            )
        }
        state, attrs = build_setup_checklist(config, data, "pt-BR", confirmations)
        self.assertEqual(state, "complete")
        self.assertEqual(attrs["invocation_name"], "music assistant")
        self.assertEqual(attrs["usage_example"], "Alexa, abra music assistant")
        self.assertEqual(len(attrs["checklist"]), 16)
        self.assertEqual(attrs["progress"]["done"], 16)
        self.assertEqual(attrs["progress"]["percent"], 100)
        self.assertIsNone(attrs["progress"]["next_step"])

        state, attrs = build_setup_checklist(
            dict(config, skill_id=""),
            _data(
                configured_skill_id="",
                skill_id_matches=None,
                suggested_skill_id=GOOD_ID,
            ),
            "pt-BR",
            confirmations,
        )
        self.assertEqual(state, "incomplete")
        self.assertEqual(_step(attrs, "skill_id_configured")["status"], "pending")
        self.assertTrue(any("SKILL_ID" in action for action in attrs["next_actions"]))

        state, attrs = build_setup_checklist(
            dict(config, skill_id=OTHER_ID),
            _data(
                configured_skill_id=OTHER_ID,
                detected_skill_id=GOOD_ID,
                skill_id_matches=False,
                suggested_skill_id=GOOD_ID,
            ),
            "pt-BR",
            confirmations,
        )
        self.assertEqual(state, "incomplete")
        self.assertEqual(_step(attrs, "skill_id_configured")["status"], "attention")

        state, attrs = build_setup_checklist(
            config,
            _data(detected_skill_id=None, skill_id_matches=None),
            "pt-BR",
            confirmations,
        )
        self.assertEqual(state, "incomplete")
        self.assertEqual(_step(attrs, "skill_id_configured")["status"], "attention")

    def test_progress_counts_and_not_applicable(self) -> None:
        config = {
            "skill_hostname": "skill.example.com",
            "ma_hostname": "",
            "locale": "pt-BR",
            "managed": True,
        }
        state, attrs = build_setup_checklist(config, _data(), "pt-BR", {})
        self.assertEqual(state, "incomplete")
        self.assertEqual(_step(attrs, "ma_hostname")["status"], "attention")
        self.assertEqual(_step(attrs, "ma_api_tested")["status"], "not_applicable")
        self.assertEqual(_step(attrs, "commands_tested")["status"], "not_applicable")
        self.assertEqual(attrs["progress"]["not_applicable"], 2)
        self.assertEqual(attrs["progress"]["total"], 16)
        self.assertLess(attrs["progress"]["percent"], 100)
        self.assertEqual(_step(attrs, "local_setup")["status"], "pending")

    def test_empty_data_shows_unavailable_state(self) -> None:
        state, attrs = build_setup_checklist(
            {"skill_hostname": "skill.example.com", "locale": "pt-BR"},
            None,
            "pt-BR",
            {},
        )
        self.assertEqual(state, "error")
        self.assertEqual(_step(attrs, "addon_started")["status"], "blocked")
        self.assertTrue(attrs["progress"]["next_step"])

    def test_sensor_and_binary_semantics(self) -> None:
        self.assertEqual(_overall_status(_data()), "ok")
        self.assertEqual(
            _overall_status(_data(configured_skill_id="", skill_id_matches=None)),
            "warning",
        )
        self.assertEqual(
            _overall_status(
                _data(
                    configured_skill_id=OTHER_ID,
                    skill_id_matches=False,
                    suggested_skill_id=GOOD_ID,
                )
            ),
            "error",
        )
        self.assertEqual(
            _overall_status(_data(detected_skill_id=None, skill_id_matches=None)),
            "ok",
        )
        self.assertTrue(_skill_id_valid(_data()))
        self.assertFalse(
            _skill_id_valid(_data(configured_skill_id="", skill_id_matches=None))
        )
        self.assertFalse(
            _skill_id_valid(_data(skill_id_matches=False, suggested_skill_id=GOOD_ID))
        )


@unittest.skipUnless(HA_AVAILABLE, "Home Assistant libraries are not installed")
class SkillIdAttributeTest(unittest.TestCase):
    """Ensure the Skill ID entity never exposes full identifiers."""

    MISTYPED_SECRET = "mistyped-secret-0123456789"

    def test_attributes_are_masked(self) -> None:
        attributes = _skill_id_attributes(
            _data(
                configured_skill_id=GOOD_ID,
                detected_skill_id=OTHER_ID,
                suggested_skill_id=OTHER_ID,
                skill_id_matches=False,
            )
        )
        self.assertEqual(
            set(attributes),
            {
                "configured_skill_id_masked",
                "detected_skill_id_masked",
                "skill_id_suggested",
                "skill_id_matches",
            },
        )
        self.assertEqual(
            attributes["configured_skill_id_masked"], mask_skill_id(GOOD_ID)
        )
        self.assertEqual(
            attributes["detected_skill_id_masked"], mask_skill_id(OTHER_ID)
        )
        self.assertIs(attributes["skill_id_suggested"], True)
        self.assertIs(attributes["skill_id_matches"], False)

        serialized = json.dumps(attributes, default=str)
        self.assertNotIn(GOOD_ID, serialized)
        self.assertNotIn(OTHER_ID, serialized)
        self.assertNotIn("suggested_skill_id", attributes)

    def test_matching_id_has_no_suggestion(self) -> None:
        attributes = _skill_id_attributes(
            _data(
                configured_skill_id=GOOD_ID,
                detected_skill_id=GOOD_ID,
                suggested_skill_id=None,
                skill_id_matches=True,
            )
        )
        self.assertIs(attributes["skill_id_suggested"], False)
        self.assertIs(attributes["skill_id_matches"], True)
        self.assertEqual(attributes["detected_skill_id_masked"], mask_skill_id(GOOD_ID))

    def test_unknown_ids_become_none(self) -> None:
        attributes = _skill_id_attributes(
            _data(
                configured_skill_id="",
                detected_skill_id=None,
                suggested_skill_id=None,
                skill_id_matches=None,
            )
        )
        self.assertIsNone(attributes["configured_skill_id_masked"])
        self.assertIsNone(attributes["detected_skill_id_masked"])
        self.assertIs(attributes["skill_id_suggested"], False)
        self.assertIsNone(attributes["skill_id_matches"])

    def test_invalid_values_are_fully_masked(self) -> None:
        attributes = _skill_id_attributes(
            _data(
                configured_skill_id=self.MISTYPED_SECRET,
                detected_skill_id=self.MISTYPED_SECRET,
                suggested_skill_id=None,
                skill_id_matches=None,
            )
        )
        self.assertEqual(attributes["configured_skill_id_masked"], "***")
        self.assertEqual(attributes["detected_skill_id_masked"], "***")
        serialized = json.dumps(attributes, default=str)
        self.assertNotIn(self.MISTYPED_SECRET, serialized)
        self.assertNotIn(self.MISTYPED_SECRET[:16], serialized)

    def test_state_logic_is_unchanged(self) -> None:
        self.assertTrue(_skill_id_valid(_data()))
        self.assertFalse(
            _skill_id_valid(_data(configured_skill_id="", skill_id_matches=None))
        )
        self.assertFalse(
            _skill_id_valid(_data(skill_id_matches=False, suggested_skill_id=GOOD_ID))
        )


class SkillIdPublicationTest(unittest.TestCase):
    """Ensure every published text is free of complete skill IDs."""

    MISTYPED = "amzn1.ask.skill.mistyped-secret"
    TOKEN = "fake-ma-token-0123456789"

    def _detailed(self) -> DetailedStatus:
        ma_api = json.dumps(
            {
                "streamUrl": "https://stream.example.test/a?token=x",
                "note": GOOD_ID,
            }
        )
        return DetailedStatus(
            skill_html=f"<span>{GOOD_ID}</span>",
            skill_ask_html=(
                f'<span class="led green">{GOOD_ID}</span> endpoint matches; '
                f"testing enabled; detected {OTHER_ID}"
            ),
            ma_api_html=f"<pre>{ma_api}</pre>",
            alexa_api_html=f'<span class="led green"></span> ok {GOOD_ID}',
            metadata_html=f"<p>{OTHER_ID}</p>",
            invocations_html=f"<p>{GOOD_ID}</p>",
            created=True,
            skill_ask_level=StatusLevel.GREEN,
            ma_api_level=StatusLevel.GREEN,
            alexa_api_level=StatusLevel.GREEN,
        )

    def _sensor(self, key: str) -> AlexaMaSkillSensor:
        description = next(item for item in SENSORS if item.key == key)
        sensor = object.__new__(AlexaMaSkillSensor)
        sensor.entity_description = description
        sensor.coordinator = SimpleNamespace(
            data=_data(detailed=self._detailed()),
            last_update_success=True,
        )
        return sensor

    def test_status_sensors_hide_complete_skill_ids(self) -> None:
        for key in ("skill_status", "ma_api", "alexa_api"):
            sensor = self._sensor(key)
            value = sensor.native_value
            self.assertIsInstance(value, str)
            self.assertIn("...", value)
            payload = json.dumps(
                {
                    "state": value,
                    "attributes": getattr(sensor, "extra_state_attributes", None),
                },
                default=str,
            )
            for full_id in (GOOD_ID, OTHER_ID):
                self.assertNotIn(full_id, payload)
            self.assertNotIn("token=x", payload)

    def test_status_text_handles_ids_outside_html(self) -> None:
        self.assertEqual(
            mask_skill_ids_in_text(f"Done. Skill ID: {GOOD_ID}."),
            f"Done. Skill ID: {mask_skill_id(GOOD_ID)}.",
        )

    def test_malformed_candidates_are_fully_masked(self) -> None:
        self.assertEqual(mask_skill_ids_in_text(f"id {self.MISTYPED}"), "id ***")
        self.assertEqual(mask_skill_ids_in_text("amzn1.ask.skill.abc.def"), "***")
        self.assertEqual(mask_skill_ids_in_text("amzn1.ask.skill.1111-2222"), "***")
        self.assertEqual(mask_skill_identifier(self.MISTYPED), "***")
        self.assertFalse(is_valid_skill_id(self.MISTYPED))
        self.assertFalse(is_valid_skill_id("amzn1.ask.skill"))
        self.assertFalse(is_valid_skill_id(self.TOKEN))
        self.assertTrue(is_valid_skill_id(GOOD_ID))
        self.assertTrue(is_valid_skill_id(f"  {OTHER_ID}  "))

    def test_tokens_without_alexa_prefix_are_not_reinterpreted(self) -> None:
        # The helper only targets skill-ID-like values; it must not invent a
        # partial mask for an unrelated token.
        self.assertEqual(mask_skill_ids_in_text(self.TOKEN), self.TOKEN)
        self.assertEqual(mask_skill_identifier(self.TOKEN), "***")

    def test_detection_is_unchanged(self) -> None:
        self.assertEqual(extract_skill_id(f"Created skill: {GOOD_ID}"), GOOD_ID)
        self.assertEqual(extract_skill_id(f"old {OTHER_ID}\nDone. {GOOD_ID}"), GOOD_ID)
        self.assertIsNone(extract_skill_id("nothing"))


@unittest.skipUnless(HA_AVAILABLE, "Home Assistant libraries are not installed")
class EntryTitleSanitizationTest(unittest.TestCase):
    """Ensure a skill ID pasted as hostname never reaches the UI."""

    def test_title_masks_skill_id_hostname(self) -> None:
        title = _entry_title(GOOD_ID)
        self.assertTrue(title.startswith("Alexa MA Skill ("))
        self.assertIn(mask_skill_id(GOOD_ID), title)
        self.assertNotIn(GOOD_ID, title)

    def test_title_keeps_normal_hostname(self) -> None:
        self.assertEqual(
            _entry_title("skill.example.test"), "Alexa MA Skill (skill.example.test)"
        )
        self.assertEqual(_entry_title(""), "Alexa MA Skill ()")

    def test_safe_entry_title_masks_any_title(self) -> None:
        raw = f"Alexa MA ({OTHER_ID})"
        self.assertEqual(safe_entry_title(raw), f"Alexa MA ({mask_skill_id(OTHER_ID)})")

    def test_device_info_name_is_sanitized(self) -> None:
        entity = object.__new__(AlexaMaSkillEntity)
        entity._entry = SimpleNamespace(
            entry_id="entry-1", title=f"Alexa MA ({GOOD_ID})"
        )
        entity.coordinator = SimpleNamespace(data=_data())
        serialized = json.dumps(dict(entity.device_info), default=str)
        self.assertNotIn(GOOD_ID, serialized)
        self.assertIn("Alexa MA Skill", serialized)


@unittest.skipUnless(HA_AVAILABLE, "Home Assistant libraries are not installed")
class ApiParsingTest(unittest.TestCase):
    """Validate /status and /setup JSON parsing without a real HTTP server."""

    class FakeApi(AlexaMaSkillApi):
        def __init__(self, status_text: str, setup_text: str) -> None:
            super().__init__(None, "http://localhost", "u", "p", session=object())
            self.status_text = status_text
            self.setup_text = setup_text

        async def _async_request(
            self, method, path, *, accept, timeout, json_data=None
        ):
            if path.startswith("/status"):
                return self.status_text, 200
            return self.setup_text, 200

    def test_setup_status_parses_last_skill_id(self) -> None:
        api = self.FakeApi(
            "{}",
            '{"logs": ["old", "Done. Skill ID: '
            + GOOD_ID
            + '", "more"], "auth_url": null, "active": false, "created": true}',
        )
        setup = asyncio.run(api.async_get_setup_status())
        self.assertEqual(setup.skill_id, GOOD_ID)
        self.assertTrue(setup.created)
        self.assertEqual(setup.logs[1], f"Done. Skill ID: {GOOD_ID}")

    def test_detailed_status_extracts_id(self) -> None:
        api = self.FakeApi(
            '{"skill_ask_html": "<span class=\\"led yellow\\"></span> '
            f'interaction model {GOOD_ID} found; endpoint not set", '
            '"ma_api_html": "", "alexa_api_html": ""}',
            "{}",
        )
        detailed = asyncio.run(api.async_get_status_json())
        self.assertEqual(detailed.detected_skill_id, GOOD_ID)

    def test_empty_setup_logs(self) -> None:
        api = self.FakeApi("{}", '{"logs": []}')
        setup = asyncio.run(api.async_get_setup_status())
        self.assertIsNone(setup.skill_id)
        self.assertEqual(setup.logs, ())


class _FakeResponse:
    """Minimal aiohttp-like response for the auth header test."""

    status = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def text(self) -> str:
        return "ok"


class _FakeSession:
    """Capture request kwargs without opening a connection."""

    def __init__(self) -> None:
        self.kwargs: dict[str, Any] = {}

    def request(self, _method: str, _url: str, **kwargs):
        self.kwargs = kwargs
        return _FakeResponse()


@unittest.skipUnless(HA_AVAILABLE, "Home Assistant libraries are not installed")
class ApiAuthHeaderTest(unittest.TestCase):
    """Validate basic auth without the deprecated aiohttp.BasicAuth API."""

    def test_authorization_header_is_set(self) -> None:
        session = _FakeSession()
        api = AlexaMaSkillApi(
            None, "http://localhost:5000", "user", "pass", session=session
        )
        asyncio.run(api.async_get_status())
        self.assertEqual(
            session.kwargs["headers"]["Authorization"], "Basic dXNlcjpwYXNz"
        )
        self.assertNotIn("auth", session.kwargs)

    def test_no_authorization_header_without_credentials(self) -> None:
        session = _FakeSession()
        api = AlexaMaSkillApi(None, "http://localhost:5000", "", "", session=session)
        asyncio.run(api.async_get_status())
        self.assertNotIn("Authorization", session.kwargs["headers"])
        self.assertNotIn("auth", session.kwargs)


class FakeConfig:
    """Minimal hass.config for Supervisor discovery tests."""

    components: ClassVar[set[str]] = {"hassio"}


class FakeHass:
    """Minimal hass object for Supervisor discovery tests."""

    config = FakeConfig()


@unittest.skipUnless(HA_AVAILABLE, "Home Assistant libraries are not installed")
class SupervisorDiscoveryTest(unittest.TestCase):
    """Validate add-on discovery without a real Supervisor."""

    class FakeManager:
        instances: ClassVar[list[object]] = []

        def __init__(self, hass, logger, addon_name, addon_slug):
            self.addon_slug = addon_slug
            self.__class__.instances.append(self)

    @staticmethod
    def _info() -> dict[str, object]:
        return {"name": "Alexa MA Skill", "version": "0.1.1", "state": "started"}

    def test_discovery_matches_exact_and_prefixed_slugs(self) -> None:
        addons = {
            "core_mosquitto": self._info(),
            "0a1b2c3d_alexa_ma_skill": self._info(),
            "alexa_ma_skill": self._info(),
            "abcdef01_alexa_ma_skill": self._info(),
        }
        with patch(
            "homeassistant.components.hassio.get_addons_info", return_value=addons
        ):
            supervisor = AlexaMaSkillSupervisor(FakeHass())
            candidates = supervisor.discover_addons()
        self.assertEqual(
            [candidate.slug for candidate in candidates],
            [
                "0a1b2c3d_alexa_ma_skill",
                "abcdef01_alexa_ma_skill",
                "alexa_ma_skill",
            ],
        )
        self.assertEqual(
            addon_hostname("0a1b2c3d_alexa_ma_skill"),
            "0a1b2c3d-alexa-ma-skill",
        )

    def test_discovery_without_match_is_empty(self) -> None:
        with patch(
            "homeassistant.components.hassio.get_addons_info",
            return_value={"core_mosquitto": self._info()},
        ):
            supervisor = AlexaMaSkillSupervisor(FakeHass())
            self.assertEqual(supervisor.discover_addons(), [])


CHECKLIST_TEST_CONFIG = {
    "managed": True,
    "locale": "pt-BR",
    "skill_hostname": "skill.example.test",
    "ma_hostname": "stream.example.test",
    "skill_id": GOOD_ID,
    "ma_api_url": "http://192.0.2.10:8095",
}


@unittest.skipUnless(HA_AVAILABLE, "Home Assistant libraries are not installed")
class SetupChecklistAttributesTest(unittest.TestCase):
    """Ensure sensor.setup_checklist publishes only public attributes."""

    ALLOWED = {
        "progress",
        "checklist",
        "manual_steps",
        "next_step",
        "next_step_title",
        "warnings",
        "skill_found",
        "endpoint_matches",
        "testing_enabled",
        "skill_id_matches",
    }

    FORBIDDEN = (
        "skill_id",
        "configured_skill_id",
        "detected_skill_id",
        "suggested_skill_id",
        "console_values",
        "endpoint_url",
        "local_setup_url",
        "provider_api_url",
        "cloudflare_rule",
        "amazon_console_url",
        "usage_example",
        "next_actions",
    )

    def _attributes(self, **overrides: Any) -> tuple[str, dict[str, Any]]:
        state, attributes = build_setup_checklist(
            CHECKLIST_TEST_CONFIG,
            _data(**overrides),
            "pt-BR",
            {},
        )
        return state, _setup_checklist_attributes(attributes)

    def test_only_allowlisted_keys_are_published(self) -> None:
        state, attributes = self._attributes()
        self.assertEqual(state, "incomplete")
        self.assertEqual(set(attributes), self.ALLOWED)
        for key in self.FORBIDDEN:
            self.assertNotIn(key, attributes)

    def test_no_full_skill_id_or_console_values(self) -> None:
        _state, attributes = self._attributes()
        serialized = json.dumps(attributes, default=str)
        self.assertNotIn(GOOD_ID, serialized)
        self.assertNotIn(OTHER_ID, serialized)
        self.assertNotIn("console_values", serialized)
        self.assertNotIn("amzn1.ask.skill.11111111", serialized)
        self.assertNotIn("192.0.2.10", serialized)
        self.assertNotIn("skill.example.test", serialized)

    def test_checklist_content_is_preserved(self) -> None:
        _state, attributes = self._attributes()
        self.assertEqual(attributes["progress"]["total"], 16)
        self.assertEqual(len(attributes["checklist"]), 16)
        self.assertTrue(attributes["manual_steps"])
        step = attributes["manual_steps"][0]
        self.assertTrue(
            {"id", "title", "status", "mode", "done", "confirmed", "how_to_fix"}
            <= set(step)
        )
        self.assertIsInstance(step["confirmed"], bool)
        self.assertIsInstance(step["dependencies"], list)
        self.assertIn(
            attributes["next_step"],
            [item["id"] for item in attributes["checklist"]],
        )

    def test_nested_values_are_sanitized(self) -> None:
        attributes = _setup_checklist_attributes(
            {
                "progress": {"total": 1, "next_step_title": f"Use {GOOD_ID}"},
                "checklist": [
                    {
                        "id": "skill_id_obtained",
                        "title": f"Skill {OTHER_ID}",
                        "description": f"<pre>{GOOD_ID}</pre>",
                        "status": "pending",
                        "status_label": "Pendente",
                        "result": "r",
                        "mode": "manual",
                        "dependencies": ["skill_created"],
                        "optional": False,
                        "how_to_fix": "Open https://stream.example.test/a?token=x",
                        "done": False,
                        "confirmed": True,
                        "unexpected": f"leak {GOOD_ID}",
                    }
                ],
                "manual_steps": [],
                "warnings": [f"Detected {GOOD_ID}", "plain warning"],
                "skill_found": True,
                "endpoint_matches": True,
                "testing_enabled": True,
                "skill_id_matches": False,
                "skill_id": GOOD_ID,
                "configured_skill_id": GOOD_ID,
                "detected_skill_id": OTHER_ID,
                "suggested_skill_id": OTHER_ID,
                "console_values": {"skill_id": GOOD_ID},
            }
        )
        serialized = json.dumps(attributes, default=str)
        for full_id in (GOOD_ID, OTHER_ID):
            self.assertNotIn(full_id, serialized)
        self.assertNotIn("token=x", serialized)
        self.assertNotIn("console_values", attributes)
        self.assertNotIn("unexpected", attributes["checklist"][0])
        self.assertEqual(
            attributes["progress"]["next_step_title"],
            f"Use {mask_skill_id(GOOD_ID)}",
        )
        self.assertEqual(attributes["warnings"][1], "plain warning")
        self.assertIs(attributes["skill_id_matches"], False)
        self.assertIs(attributes["skill_found"], True)

    def test_entity_state_and_attributes(self) -> None:
        sensor = object.__new__(AlexaMaSkillSetupChecklistSensor)
        sensor._checklist = SimpleNamespace(confirmations={})
        sensor.coordinator = SimpleNamespace(
            data=_data(),
            hass=SimpleNamespace(config=SimpleNamespace(language="pt-BR")),
        )
        sensor._entry = SimpleNamespace(
            entry_id="entry-1",
            title="Alexa MA",
            data={},
            options=CHECKLIST_TEST_CONFIG,
        )

        expected_state, _attributes = build_setup_checklist(
            CHECKLIST_TEST_CONFIG,
            sensor.coordinator.data,
            "pt-BR",
            {},
        )
        self.assertEqual(sensor.native_value, expected_state)
        self.assertEqual(set(sensor.extra_state_attributes), self.ALLOWED)


@unittest.skipUnless(HA_AVAILABLE, "Home Assistant libraries are not installed")
class DiagnosticsMaskingTest(unittest.TestCase):
    """Ensure diagnostics do not expose complete skill IDs or secrets."""

    MISTYPED_SECRET = "mistyped-secret-0123456789"
    PASSWORD = "super-secret-password"
    TOKEN = "ma-token-value-123"

    def test_skill_ids_are_masked(self) -> None:
        data = _data()
        payload = _coordinator_data(data)
        payload["entry"] = {"data": {"skill_id": OTHER_ID}}
        masked = _mask_skill_id_fields(payload)
        text = repr(masked)
        self.assertNotIn(GOOD_ID, text)
        self.assertNotIn(OTHER_ID, text)
        self.assertIn("...", text)

    def test_valid_ids_keep_the_existing_representation(self) -> None:
        payload = _coordinator_data(_data(detected_skill_id=GOOD_ID))
        masked = _mask_skill_id_fields(payload)
        self.assertEqual(masked["detected_skill_id"], mask_skill_id(GOOD_ID))
        self.assertEqual(masked["detected_skill_id"], mask_skill_identifier(GOOD_ID))
        self.assertEqual(masked["configured_skill_id"], mask_skill_id(GOOD_ID))

    def test_invalid_ids_become_fully_masked(self) -> None:
        payload = _coordinator_data(
            _data(
                configured_skill_id=self.MISTYPED_SECRET,
                detected_skill_id=self.MISTYPED_SECRET,
                suggested_skill_id=self.MISTYPED_SECRET,
            )
        )
        payload["entry"] = {"data": {"skill_id": self.MISTYPED_SECRET}}
        masked = _mask_skill_id_fields(payload)
        self.assertEqual(masked["configured_skill_id"], "***")
        self.assertEqual(masked["detected_skill_id"], "***")
        self.assertEqual(masked["suggested_skill_id"], "***")
        self.assertEqual(masked["entry"]["data"]["skill_id"], "***")
        text = repr(masked)
        self.assertNotIn(self.MISTYPED_SECRET, text)
        self.assertNotIn(self.MISTYPED_SECRET[:16], text)

    def test_config_entry_diagnostics_hide_secrets(self) -> None:
        entry = SimpleNamespace(
            entry_id="entry-1",
            data={"skill_id": GOOD_ID},
            options={
                "skill_id": OTHER_ID,
                "password": self.PASSWORD,
                "ma_api_token": self.TOKEN,
                "skill_hostname": "skill.example.test",
            },
        )
        runtime = SimpleNamespace(
            coordinator=SimpleNamespace(data=_data()),
            supervisor=SimpleNamespace(manager_ready=False),
        )
        hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: runtime}})

        result = asyncio.run(async_get_config_entry_diagnostics(hass, entry))

        self.assertEqual(
            result["coordinator"]["configured_skill_id"], mask_skill_id(GOOD_ID)
        )
        self.assertEqual(result["entry"]["data"]["skill_id"], mask_skill_id(GOOD_ID))
        self.assertEqual(
            result["entry"]["options"]["skill_id"], mask_skill_id(OTHER_ID)
        )
        self.assertEqual(
            result["entry"]["options"]["skill_hostname"], "skill.example.test"
        )
        self.assertEqual(result["coordinator"]["http_status"], 200)
        self.assertIs(result["addon"]["available"], False)

        serialized = json.dumps(result, default=str)
        for secret in (
            GOOD_ID,
            OTHER_ID,
            self.PASSWORD,
            self.TOKEN,
            "super-secret",
        ):
            self.assertNotIn(secret, serialized)
        self.assertIn("REDACTED", serialized)
        self.assertTrue(TO_REDACT)


@unittest.skipUnless(HA_AVAILABLE, "Home Assistant libraries are not installed")
class CoordinatorLogicTest(unittest.TestCase):
    """Validate detected/configured skill ID relationships."""

    class FakeApi:
        def __init__(self, setup_id=None, status_id=None, setup_error=None):
            self.setup_id = setup_id
            self.status_id = status_id
            self.setup_error = setup_error

        async def async_get_status(self):
            return SimpleStatus(http_status=200)

        async def async_get_status_json(self):
            return DetailedStatus(
                skill_html="",
                skill_ask_html="",
                ma_api_html="",
                alexa_api_html="",
                metadata_html="",
                invocations_html="",
                created=False,
                skill_ask_level=StatusLevel.UNKNOWN,
                ma_api_level=StatusLevel.UNKNOWN,
                alexa_api_level=StatusLevel.UNKNOWN,
                detected_skill_id=self.status_id,
            )

        async def async_get_setup_status(self):
            if self.setup_error:
                raise self.setup_error
            return SetupStatus(
                logs=(),
                auth_url=None,
                active=False,
                created=False,
                skill_id=self.setup_id,
            )

    def _coordinator(self, api, configured="", stored=None):
        coordinator = AlexaMaSkillCoordinator.__new__(AlexaMaSkillCoordinator)
        coordinator.api = api
        coordinator._supervisor = None
        coordinator._skill_hostname = ""
        coordinator._ma_hostname = ""
        coordinator._ignore_https = False
        coordinator._last_detailed_attempt = None
        coordinator._detailed = None
        coordinator._last_check = None
        coordinator._detailed_error = None
        coordinator._addon_version = None
        coordinator._addon_installed = None
        coordinator._addon_hostname = None
        coordinator._store = None
        coordinator._configured_skill_id = configured
        coordinator._detected_skill_id = stored
        coordinator._https_cache = None
        coordinator.saved = []

        async def save(skill_id):
            coordinator.saved.append(skill_id)

        coordinator._async_save_detected_skill_id = save
        return coordinator

    def test_setup_id_suggestion_and_mismatch(self) -> None:
        coordinator = self._coordinator(self.FakeApi(setup_id=GOOD_ID))
        data = asyncio.run(coordinator._async_update_data())
        self.assertEqual(data.detected_skill_id, GOOD_ID)
        self.assertEqual(data.suggested_skill_id, GOOD_ID)
        self.assertEqual(coordinator.saved, [GOOD_ID])

        coordinator = self._coordinator(
            self.FakeApi(setup_id=GOOD_ID), configured=OTHER_ID
        )
        data = asyncio.run(coordinator._async_update_data())
        self.assertFalse(data.skill_id_matches)
        self.assertEqual(data.suggested_skill_id, GOOD_ID)

    def test_no_detection_has_no_penalty(self) -> None:
        coordinator = self._coordinator(self.FakeApi(), configured=OTHER_ID)
        data = asyncio.run(coordinator._async_update_data())
        self.assertIsNone(data.detected_skill_id)
        self.assertIsNone(data.skill_id_matches)
        self.assertIsNone(data.suggested_skill_id)


def _data(**overrides) -> AlexaMaSkillData:
    detailed = DetailedStatus(
        skill_html="",
        skill_ask_html=(
            '<span class="led green"></span> interaction model found; '
            "endpoint matches; testing enabled"
        ),
        ma_api_html='<span class="led green"></span> ok',
        alexa_api_html='<span class="led green"></span> ok',
        metadata_html="",
        invocations_html="",
        created=False,
        skill_ask_level=StatusLevel.GREEN,
        ma_api_level=StatusLevel.GREEN,
        alexa_api_level=StatusLevel.GREEN,
    )
    values = {
        "reachable": True,
        "http_status": 200,
        "detailed": detailed,
        "last_check": datetime.now(UTC),
        "detailed_error": None,
        "container_online": True,
        "addon_installed": True,
        "addon_hostname": "0a1b2c3d-alexa-ma-skill",
        "addon_version": "0.1.1",
        "https_skill_ok": True,
        "https_stream_ok": True,
        "stream_url_present": True,
        "detected_skill_id": GOOD_ID,
        "configured_skill_id": GOOD_ID,
        "skill_id_matches": True,
        "suggested_skill_id": None,
    }
    values.update(overrides)
    return AlexaMaSkillData(**values)


if __name__ == "__main__":
    unittest.main()
