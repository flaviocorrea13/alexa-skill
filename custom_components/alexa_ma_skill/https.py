"""Cached HTTPS reachability checks for the Alexa MA Skill integration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_HTTPS_TIMEOUT = 10
_HTTPS_CACHE_TTL = timedelta(minutes=5)
_STREAM_FALLBACK_STATUSES = {405, 501}
_MAX_CACHE_ENTRIES = 128


def _skill_status_ok(status: int) -> bool:
    """Return True for expected responses from the public skill hostname.

    A GET to ``/`` is expected to return 401/403 because the panel and WAF
    protect that path. A 404 usually means the request hit a proxy without the
    add-on route, so it must not be treated as reachable.
    """
    return status < 400 or status in {401, 403}


class HttpsCheckCache:
    """Cache reachability checks so the stream is not opened every poll."""

    def __init__(
        self,
        hass: HomeAssistant,
        ttl: timedelta = _HTTPS_CACHE_TTL,
    ) -> None:
        """Initialize the cache."""
        self._session = async_get_clientsession(hass)
        self._ttl = ttl
        self._cache: dict[tuple[str, str, bool], tuple[bool, datetime]] = {}

    async def async_check_skill(self, host: str, ignore_https: bool) -> bool:
        """Check the public skill endpoint without downloading a body."""
        if not host:
            return False
        return await self._async_cached(
            ("skill", host, ignore_https),
            f"https://{host}/",
            ignore_https,
            stream=False,
        )

    async def async_check_stream(self, url: str, ignore_https: bool) -> bool:
        """Check the real public stream URL without downloading the stream."""
        if not url:
            return False
        return await self._async_cached(
            ("stream", url, ignore_https),
            url,
            ignore_https,
            stream=True,
        )

    async def _async_cached(
        self,
        key: tuple[str, str, bool],
        url: str,
        ignore_https: bool,
        *,
        stream: bool,
    ) -> bool:
        now = datetime.now(UTC)
        cached = self._cache.get(key)
        if cached is not None and now - cached[1] < self._ttl:
            return cached[0]

        result = await self._async_check(url, ignore_https, stream=stream)
        self._remember(key, result, now)
        return result

    def _remember(
        self, key: tuple[str, str, bool], result: bool, now: datetime
    ) -> None:
        """Store a result, keeping the cache bounded when stream URLs rotate."""
        if key not in self._cache and len(self._cache) >= _MAX_CACHE_ENTRIES:
            oldest_key = min(self._cache, key=lambda item: self._cache[item][1])
            self._cache.pop(oldest_key, None)
        self._cache[key] = (result, now)

    async def _async_check(
        self,
        url: str,
        ignore_https: bool,
        *,
        stream: bool,
    ) -> bool:
        kwargs: dict[str, Any] = {
            "timeout": aiohttp.ClientTimeout(total=_HTTPS_TIMEOUT),
            "allow_redirects": True,
        }
        if ignore_https:
            kwargs["ssl"] = False

        try:
            if stream:
                return await self._async_check_stream_url(url, kwargs)
            return await self._async_check_skill_url(url, kwargs)
        except (aiohttp.ClientError, TimeoutError, OSError, ValueError):
            return False

    async def _async_check_skill_url(
        self,
        url: str,
        kwargs: dict[str, Any],
    ) -> bool:
        async with self._session.get(url, **kwargs) as response:
            return _skill_status_ok(response.status)

    async def _async_check_stream_url(
        self,
        url: str,
        kwargs: dict[str, Any],
    ) -> bool:
        async with self._session.head(url, **kwargs) as response:
            if response.status in _STREAM_FALLBACK_STATUSES:
                return await self._async_get_stream(url, kwargs)
            return 200 <= response.status < 300 or response.status == 416

    async def _async_get_stream(
        self,
        url: str,
        kwargs: dict[str, Any],
    ) -> bool:
        headers = {**kwargs.get("headers", {}), "Range": "bytes=0-0"}
        request_kwargs = {**kwargs, "headers": headers}
        async with self._session.get(url, **request_kwargs) as response:
            return 200 <= response.status < 300 or response.status == 416
