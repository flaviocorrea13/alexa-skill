"""Shared pytest configuration for the integration tests.

The Home Assistant test harness is only available on Linux. The plugin
registers the ``hass`` fixture and the ``enable_custom_integrations`` fixture.
"""

from __future__ import annotations

import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading the custom integration in every test."""
    yield
