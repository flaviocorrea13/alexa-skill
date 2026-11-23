"""Utility helpers for the Alexa MA Skill integration."""

from __future__ import annotations

import json
import re
from html import unescape
from html.parser import HTMLParser
from typing import Any

from homeassistant.config_entries import ConfigEntry

_PRE_RE = re.compile(r"<pre[^>]*>(.*?)</pre>", re.IGNORECASE | re.DOTALL)


def entry_config(entry: ConfigEntry) -> dict[str, Any]:
    """Return the effective configuration for a config entry."""
    return {**entry.data, **entry.options}


class _TextExtractor(HTMLParser):
    """Collect text nodes from a small HTML fragment."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    @property
    def text(self) -> str:
        """Return the collected text with whitespace collapsed."""
        return " ".join(" ".join(self._parts).split())


def html_to_text(value: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    if not value:
        return ""
    parser = _TextExtractor()
    try:
        parser.feed(value)
        parser.close()
    except Exception:  # noqa: BLE001 - malformed status fragments must not break polling
        return " ".join(value.split())
    return parser.text


def extract_pre_text(value: str) -> str | None:
    """Return the unescaped text inside the first pre block."""
    if not value:
        return None
    match = _PRE_RE.search(value)
    if match is None:
        return None
    return unescape(match.group(1))


def parse_json_pre(value: str) -> dict[str, Any] | None:
    """Parse the JSON object inside the first pre block."""
    pre_text = extract_pre_text(value)
    if not pre_text:
        return None
    try:
        data = json.loads(pre_text)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data
