"""Utility helpers for the Alexa MA Skill integration."""

from __future__ import annotations

import json
import re
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse, urlunparse

from homeassistant.config_entries import ConfigEntry

from .const import StatusLevel

_PRE_RE = re.compile(r"<pre[^>]*>(.*?)</pre>", re.IGNORECASE | re.DOTALL)
_STREAM_JSON_RE = re.compile(
    r'("(?:streamUrl|audioSources)"\s*:\s*")[^"]*(")',
    re.IGNORECASE,
)


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


def redact_stream_urls(value: str) -> str:
    """Redact stream URLs embedded in JSON-like status text."""
    if not value:
        return ""
    return _STREAM_JSON_RE.sub(r"\1**REDACTED**\2", value)


def skill_linked(skill_ask_html: str, level: StatusLevel) -> bool:
    """Return True when the skill exists, matches, and testing is enabled."""
    text = html_to_text(skill_ask_html).lower()
    return (
        level is StatusLevel.GREEN
        and "endpoint matches" in text
        and "testing enabled" in text
    )


def public_stream_url(value: str, ma_hostname: str) -> str | None:
    """Rewrite a stream URL to its public HTTPS hostname."""
    if not value:
        return None
    parsed = urlparse(value)
    if not parsed.netloc:
        return None
    if ma_hostname:
        return urlunparse(
            (
                "https",
                ma_hostname,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )
    if parsed.scheme == "https":
        return value
    return None
