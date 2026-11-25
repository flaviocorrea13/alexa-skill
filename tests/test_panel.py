"""Tests for panel registration and lifecycle."""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

try:
    import homeassistant  # noqa: F401

    from custom_components.alexa_ma_skill import panel
    from custom_components.alexa_ma_skill.const import (
        DOMAIN,
        PANEL_STATIC_PATH,
        PANEL_URL,
    )

    HA_AVAILABLE = True
except ImportError:
    HA_AVAILABLE = False


@unittest.skipUnless(HA_AVAILABLE, "Home Assistant libraries are not installed")
class PanelRegistrationTest(unittest.IsolatedAsyncioTestCase):
    """Validate registration, hash, idempotence, retry, and unload."""

    def _hass(self):
        class FakeHttp:
            def __init__(self):
                self.configs = []

            async def async_register_static_paths(self, configs):
                self.configs.extend(configs)

        hass = SimpleNamespace(
            data={},
            http=FakeHttp(),
        )

        async def _executor(func, *args):
            return func(*args)

        hass.async_add_executor_job = _executor
        return hass

    async def test_registers_panel_and_static_path_once(self) -> None:
        hass = self._hass()
        register = AsyncMock()
        with patch.object(panel.panel_custom, "async_register_panel", register):
            self.assertTrue(await panel.async_register_panel(hass))
            self.assertTrue(await panel.async_register_panel(hass))

        register.assert_awaited_once()
        self.assertEqual(len(hass.http.configs), 1)
        config = hass.http.configs[0]
        self.assertEqual(config.url_path, PANEL_STATIC_PATH)
        self.assertEqual(Path(config.path), panel.BUNDLE_PATH)
        expected_hash = hashlib.sha256(panel.BUNDLE_PATH.read_bytes()).hexdigest()[:12]
        self.assertEqual(
            register.await_args.kwargs["module_url"],
            f"{PANEL_STATIC_PATH}?v={expected_hash}",
        )
        self.assertEqual(register.await_args.kwargs["frontend_url_path"], PANEL_URL)
        self.assertTrue(register.await_args.kwargs["require_admin"])

    async def test_failed_registration_can_retry(self) -> None:
        hass = self._hass()
        register = AsyncMock(side_effect=[RuntimeError("boom"), None])
        with patch.object(panel.panel_custom, "async_register_panel", register):
            self.assertFalse(await panel.async_register_panel(hass))
            self.assertFalse(hass.data[panel.PANEL_STATE_KEY].get("registered", False))
            self.assertTrue(await panel.async_register_panel(hass))
        self.assertTrue(hass.data[panel.PANEL_STATE_KEY]["registered"])

    async def test_missing_bundle_does_not_register(self) -> None:
        hass = self._hass()
        with patch.object(panel, "BUNDLE_PATH", Path("does-not-exist.js")):
            register = AsyncMock()
            with patch.object(panel.panel_custom, "async_register_panel", register):
                self.assertFalse(await panel.async_register_panel(hass))
        register.assert_not_awaited()

    async def test_unregister_removes_panel(self) -> None:
        hass = self._hass()
        with (
            patch.object(panel.panel_custom, "async_register_panel", AsyncMock()),
            patch.object(panel.frontend, "async_remove_panel") as remove,
        ):
            await panel.async_register_panel(hass)
            await panel.async_unregister_panel(hass)
        remove.assert_called_once_with(hass, PANEL_URL)
        self.assertFalse(hass.data[panel.PANEL_STATE_KEY].get("registered", False))

    async def test_panel_is_removed_only_after_last_entry(self) -> None:
        hass = self._hass()
        hass.data[DOMAIN] = {
            "one": SimpleNamespace(coordinator=object()),
            "two": SimpleNamespace(coordinator=object()),
        }
        with (
            patch.object(panel.panel_custom, "async_register_panel", AsyncMock()),
            patch.object(panel.frontend, "async_remove_panel") as remove,
        ):
            await panel.async_register_panel(hass)
            await panel.async_unregister_panel_if_empty(hass)
            self.assertFalse(remove.called)
            hass.data[DOMAIN].pop("one")
            hass.data[DOMAIN].pop("two")
            await panel.async_unregister_panel_if_empty(hass)
        remove.assert_called_once_with(hass, PANEL_URL)
