"""Home Assistant config-flow tests for the Alexa MA Skill integration.

These tests require the Home Assistant test harness (Linux CI). They are not
executed on Windows because the Home Assistant test plugin imports ``fcntl``.
The module is also import-safe when pytest or Home Assistant is not installed.
"""

from __future__ import annotations

from typing import ClassVar
from unittest.mock import patch

try:
    import pytest
    from homeassistant import config_entries
    from homeassistant.data_entry_flow import FlowResultType

    from custom_components.alexa_ma_skill.api import SimpleStatus
    from custom_components.alexa_ma_skill.const import DOMAIN
    from custom_components.alexa_ma_skill.supervisor import AddonCandidate

    TEST_READY = True
except ImportError:
    TEST_READY = False


if TEST_READY:
    FAKE_SLUG = "0a1b2c3d_alexa_ma_skill"

    @pytest.fixture(autouse=True)
    def auto_enable_custom_integrations(enable_custom_integrations):
        """Enable loading of the custom integration in tests."""
        yield

    class UnavailableSupervisor:
        """Supervisor that is not available (HA Container/Core)."""

        def __init__(self, hass, addon_slug=None):
            self.available = False
            self.manager_ready = False

    class FakeSupervisor:
        """Supervisor with a controlled candidate list."""

        candidates: ClassVar[list[AddonCandidate]] = []

        def __init__(self, hass, addon_slug=None):
            self.available = True
            self.manager_ready = bool(addon_slug)
            self.addon_slug = addon_slug

        def discover_addons(self) -> list[AddonCandidate]:
            return list(self.candidates)

    @pytest.mark.asyncio
    async def test_user_step_falls_back_to_manual(hass):
        """Supervisor unavailable should show the manual configuration form."""
        with patch(
            "custom_components.alexa_ma_skill.config_flow.AlexaMaSkillSupervisor",
            UnavailableSupervisor,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "manual"

    @pytest.mark.asyncio
    async def test_no_addon_shows_installation_error(hass):
        """No matching add-on should show addon_not_installed."""
        FakeSupervisor.candidates = []
        with patch(
            "custom_components.alexa_ma_skill.config_flow.AlexaMaSkillSupervisor",
            FakeSupervisor,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "addon"
        assert result["errors"] == {"base": "addon_not_installed"}

    @pytest.mark.asyncio
    async def test_one_addon_shows_config_form(hass):
        """One matching add-on should be selected automatically."""
        FakeSupervisor.candidates = [
            AddonCandidate(slug=FAKE_SLUG, name="Alexa MA Skill", version="0.1.1")
        ]
        with patch(
            "custom_components.alexa_ma_skill.config_flow.AlexaMaSkillSupervisor",
            FakeSupervisor,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "addon"
        assert not result.get("errors")

    @pytest.mark.asyncio
    async def test_multiple_addons_show_selector(hass):
        """Multiple matching add-ons should show the addon_select step."""
        FakeSupervisor.candidates = [
            AddonCandidate(slug=FAKE_SLUG, name="Alexa MA Skill", version="0.1.1"),
            AddonCandidate(
                slug="abcdef01_alexa_ma_skill",
                name="Alexa MA Skill",
                version="0.1.1",
            ),
        ]
        with patch(
            "custom_components.alexa_ma_skill.config_flow.AlexaMaSkillSupervisor",
            FakeSupervisor,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "addon_select"

    @pytest.mark.asyncio
    async def test_manual_flow_creates_entry(hass):
        """Manual mode should create an entry without a Supervisor add-on slug."""
        with patch(
            "custom_components.alexa_ma_skill.config_flow.AlexaMaSkillSupervisor",
            UnavailableSupervisor,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

        with patch(
            "custom_components.alexa_ma_skill.config_flow.AlexaMaSkillApi.async_get_status",
            return_value=SimpleStatus(http_status=200),
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    "base_url": "http://192.0.2.10:5000",
                    "username": "user",
                    "password": "password",
                    "skill_hostname": "skill.example.com",
                    "ma_hostname": "ma.example.com",
                    "locale": "pt-BR",
                    "enable_apl": False,
                    "skip_url_validation": False,
                    "ma_api_url": "",
                    "ma_api_token": "",
                    "ignore_https": False,
                },
            )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"]["managed"] is False
        assert result["data"]["addon_slug"] == ""

    @pytest.mark.asyncio
    async def test_manual_flow_rejects_token_without_url(hass):
        """MA_API_TOKEN without MA_API_URL should return a clear form error."""
        with patch(
            "custom_components.alexa_ma_skill.config_flow.AlexaMaSkillSupervisor",
            UnavailableSupervisor,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "base_url": "http://192.0.2.10:5000",
                "username": "user",
                "password": "password",
                "skill_hostname": "skill.example.com",
                "ma_hostname": "",
                "locale": "pt-BR",
                "enable_apl": False,
                "skip_url_validation": False,
                "ma_api_url": "",
                "ma_api_token": "token-without-url",
                "ignore_https": False,
            },
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "ma_api_incomplete"}
