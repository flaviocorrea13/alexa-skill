"""Unit tests for integration helpers that do not need a running HA instance.

These tests run with the Home Assistant libraries installed (for example the
project virtualenv). They are skipped automatically when Home Assistant is not
available.
"""

from __future__ import annotations

import asyncio
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
    from custom_components.alexa_ma_skill.binary_sensor import _skill_id_valid
    from custom_components.alexa_ma_skill.config_flow import (
        AlexaMaSkillOptionsFlow,
        _clean_hostname,
        _clean_ma_api_url,
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
        _coordinator_data,
        _mask_skill_id_fields,
    )
    from custom_components.alexa_ma_skill.https import _skill_status_ok
    from custom_components.alexa_ma_skill.sensor import _overall_status
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
        mask_skill_id,
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

    def test_setup_form_reads_and_stores_manual_steps(self) -> None:
        manager = ChecklistManager(self.FakeStore(), {"confirmations": {}})

        async def refresh() -> None:
            return None

        coordinator = SimpleNamespace(data=_data(), async_request_refresh=refresh)
        runtime = SimpleNamespace(coordinator=coordinator, checklist=manager)
        entry = SimpleNamespace(entry_id="entry", data={}, options={})
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

        result = asyncio.run(flow.async_step_setup(None))
        self.assertEqual(result["step_id"], "setup")
        self.assertIn("summary", result["description_placeholders"])
        self.assertIn("progress", result["description_placeholders"])

        result = asyncio.run(flow.async_step_setup({"local_setup": True}))
        self.assertTrue(manager.confirmed("local_setup"))
        self.assertEqual(result["step_id"], "setup")


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


@unittest.skipUnless(HA_AVAILABLE, "Home Assistant libraries are not installed")
class DiagnosticsMaskingTest(unittest.TestCase):
    """Ensure diagnostics do not expose complete skill IDs."""

    def test_skill_ids_are_masked(self) -> None:
        data = _data()
        payload = _coordinator_data(data)
        payload["entry"] = {"data": {"skill_id": OTHER_ID}}
        masked = _mask_skill_id_fields(payload)
        text = repr(masked)
        self.assertNotIn(GOOD_ID, text)
        self.assertNotIn(OTHER_ID, text)
        self.assertIn("...", text)


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
