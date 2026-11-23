"""HTTP client for the Alexa MA Skill add-on."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DETAILED_REQUEST_TIMEOUT, REQUEST_TIMEOUT, StatusLevel
from .util import parse_json_pre

_LED_RE = re.compile(r'class="led (green|yellow|red)"')


class AlexaMaSkillApiError(Exception):
    """Base error for the Alexa MA Skill API."""


class AlexaMaSkillAuthError(AlexaMaSkillApiError):
    """Authentication with the add-on failed."""


class AlexaMaSkillConnectionError(AlexaMaSkillApiError):
    """The add-on could not be reached."""


class AlexaMaSkillResponseError(AlexaMaSkillApiError):
    """The add-on returned an unexpected response."""


@dataclass(frozen=True, slots=True)
class SimpleStatus:
    """Result of the cheap status check."""

    http_status: int
    reachable: bool = True


@dataclass(frozen=True, slots=True)
class DetailedStatus:
    """Parsed payload from the detailed status endpoint."""

    skill_html: str
    skill_ask_html: str
    ma_api_html: str
    alexa_api_html: str
    metadata_html: str
    invocations_html: str
    created: bool
    skill_ask_level: StatusLevel
    ma_api_level: StatusLevel
    alexa_api_level: StatusLevel
    ma_api_details: dict[str, Any] | None = None
    stream_url: str | None = None


class AlexaMaSkillApi:
    """Client for the add-on HTTP endpoints."""

    def __init__(
        self,
        hass: HomeAssistant,
        base_url: str,
        username: str,
        password: str,
        *,
        ignore_https: bool = False,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the client."""
        self._session = session or async_get_clientsession(hass)
        self._base_url = base_url.rstrip("/")
        self._auth = (
            aiohttp.BasicAuth(username, password) if username or password else None
        )
        self._ignore_https = ignore_https

    async def async_get_status(self) -> SimpleStatus:
        """Return the cheap status result from the add-on."""
        _text, status = await self._async_request(
            "GET",
            "/status",
            accept="text/html",
            timeout=REQUEST_TIMEOUT,
        )
        return SimpleStatus(http_status=status)

    async def async_get_status_json(self) -> DetailedStatus:
        """Return the detailed status result from the add-on."""
        text, _status = await self._async_request(
            "GET",
            "/status?format=json",
            accept="application/json",
            timeout=DETAILED_REQUEST_TIMEOUT,
        )
        try:
            data = json.loads(text)
        except (TypeError, ValueError) as err:
            raise AlexaMaSkillResponseError(
                f"Invalid JSON from /status?format=json: {err}"
            ) from err
        if not isinstance(data, dict):
            raise AlexaMaSkillResponseError(
                "/status?format=json did not return a JSON object"
            )

        ma_api_html = _as_text(data.get("ma_api_html"))
        ma_api_details = parse_json_pre(ma_api_html)
        stream_url = None
        if ma_api_details:
            candidate = ma_api_details.get("streamUrl") or ma_api_details.get(
                "audioSources"
            )
            if isinstance(candidate, str) and candidate:
                stream_url = candidate

        return DetailedStatus(
            skill_html=_as_text(data.get("skill_html")),
            skill_ask_html=_as_text(data.get("skill_ask_html")),
            ma_api_html=ma_api_html,
            alexa_api_html=_as_text(data.get("alexa_api_html")),
            metadata_html=_as_text(data.get("metadata_html")),
            invocations_html=_as_text(data.get("invocations_html")),
            created=bool(data.get("created", False)),
            skill_ask_level=_parse_level(data.get("skill_ask_html")),
            ma_api_level=_parse_level(ma_api_html),
            alexa_api_level=_parse_level(data.get("alexa_api_html")),
            ma_api_details=ma_api_details,
            stream_url=stream_url,
        )

    async def _async_request(
        self,
        method: str,
        path: str,
        *,
        accept: str,
        timeout: int,
        json_data: Any | None = None,
    ) -> tuple[str, int]:
        """Perform a request and translate failures into API errors."""
        url = f"{self._base_url}{path}"
        kwargs: dict[str, Any] = {
            "auth": self._auth,
            "headers": {"Accept": accept},
            "timeout": aiohttp.ClientTimeout(total=timeout),
        }
        if json_data is not None:
            kwargs["json"] = json_data
        if self._ignore_https and url.startswith("https://"):
            kwargs["ssl"] = False

        try:
            async with self._session.request(method, url, **kwargs) as response:
                if response.status == 401:
                    raise AlexaMaSkillAuthError(f"Authentication failed for {path}")
                if response.status != 200:
                    raise AlexaMaSkillResponseError(
                        f"Unexpected HTTP status {response.status} for {path}"
                    )
                try:
                    text = await response.text()
                except UnicodeError as err:
                    raise AlexaMaSkillResponseError(
                        f"Invalid response encoding for {path}"
                    ) from err
                return text, response.status
        except AlexaMaSkillApiError:
            raise
        except TimeoutError as err:
            raise AlexaMaSkillConnectionError(f"Timeout accessing {path}") from err
        except aiohttp.ClientError as err:
            raise AlexaMaSkillConnectionError(
                f"Connection error accessing {path}: {err}"
            ) from err


def _as_text(value: Any) -> str:
    """Return a string for a JSON value."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _parse_level(value: Any) -> StatusLevel:
    """Derive a status level from an HTML fragment."""
    match = _LED_RE.search(_as_text(value))
    if match is None:
        return StatusLevel.UNKNOWN
    return StatusLevel(match.group(1))
