"""Config and options flows for the Alexa MA Skill integration."""

from __future__ import annotations

import asyncio
import logging
import secrets
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
    OptionsFlowWithConfigEntry,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    AlexaMaSkillApi,
    AlexaMaSkillApiError,
    AlexaMaSkillAuthError,
)
from .const import (
    ADDON_START_POLL_INTERVAL,
    ADDON_START_TIMEOUT,
    ALLOWED_LOCALES,
    CONF_ADDON_SLUG,
    CONF_BASE_URL,
    CONF_ENABLE_APL,
    CONF_IGNORE_HTTPS,
    CONF_LOCALE,
    CONF_MA_API_TOKEN,
    CONF_MA_API_URL,
    CONF_MA_HOSTNAME,
    CONF_MANAGED,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_SKILL_HOSTNAME,
    CONF_SKILL_ID,
    CONF_SKIP_URL_VALIDATION,
    CONF_USERNAME,
    DEFAULT_BASE_URL,
    DEFAULT_LOCALE,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    NAME,
)
from .setup import build_setup_checklist
from .supervisor import (
    AddonCandidate,
    AlexaMaSkillSupervisor,
    SupervisorOperationError,
    SupervisorUnavailableError,
    addon_hostname,
)
from .util import entry_config, mask_skill_ids_in_text

_LOGGER = logging.getLogger(__name__)

_HTTPS_TIMEOUT = 10
_CONFIRM_KEY = "confirm"


class _FlowError(Exception):
    """A flow error with a translation key and optional placeholders."""

    def __init__(
        self, error: str, placeholders: Mapping[str, str] | None = None
    ) -> None:
        super().__init__(error)
        self.error = error
        self.placeholders = dict(placeholders or {})


def _safe_input(value: Any) -> str:
    """Return a generic, safe representation for form errors.

    Never reproduce the supplied value, even when it looks like a hostname or
    token. Only the distinction between an empty and a non-empty input remains.
    """
    return "***" if str(value or "").strip() else ""


def _clean_hostname(value: Any, *, required: bool = True) -> str:
    """Validate and normalize a bare hostname."""
    text = str(value or "").strip()
    if not text:
        if required:
            raise _FlowError("invalid_hostname", {"host": ""})
        return ""
    if "://" in text:
        raise _FlowError("invalid_hostname", {"host": _safe_input(text)})
    text = text.rstrip(".")
    if not text:
        raise _FlowError("invalid_hostname", {"host": ""})
    if any(character in text for character in "/?#@\\ \t\r\n"):
        raise _FlowError("invalid_hostname", {"host": _safe_input(text)})
    if ":" in text:
        raise _FlowError("invalid_hostname", {"host": _safe_input(text)})
    if len(text) > 253:
        raise _FlowError("invalid_hostname", {"host": _safe_input(text)})
    return text


def _entry_title(hostname: Any) -> str:
    """Return the config entry title without exposing a full skill ID.

    The title is built from the hostname field. If a skill ID was pasted there
    by mistake, it is masked instead of being shown in the integrations list
    and in the device name.
    """
    return f"{NAME} ({mask_skill_ids_in_text(str(hostname or ''))})"


def _clean_base_url(value: Any) -> str:
    """Validate and normalize the internal add-on base URL."""
    text = str(value or "").strip()
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https"):
        raise _FlowError("invalid_hostname", {"host": _safe_input(text)})
    if not parsed.netloc or parsed.username or parsed.password:
        raise _FlowError("invalid_hostname", {"host": _safe_input(text)})
    if parsed.path not in ("", "/") or parsed.params or parsed.query or parsed.fragment:
        raise _FlowError("invalid_hostname", {"host": _safe_input(text)})
    return f"{parsed.scheme}://{parsed.netloc}"


def _clean_ma_api_url(value: Any) -> str:
    """Validate the optional Music Assistant API URL."""
    text = str(value or "").strip()
    if not text:
        return ""
    if any(character in text for character in " \t\r\n"):
        raise _FlowError("invalid_hostname", {"host": _safe_input(text)})
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https", "ws", "wss") or not parsed.netloc:
        raise _FlowError("invalid_hostname", {"host": _safe_input(text)})
    if parsed.username or parsed.password:
        raise _FlowError("invalid_hostname", {"host": _safe_input(text)})
    return text


def _validate_ma_api_pair(url: str, token: str, current_token: str = "") -> str:
    """Return the token to preserve, allowing MA_API_URL without a token."""
    token = "" if _is_masked(token) else token.strip()
    current_token = "" if _is_masked(current_token) else current_token.strip()
    if not url:
        if token:
            raise _FlowError("ma_api_incomplete")
        return ""
    return token or current_token


def _is_masked(value: object) -> bool:
    """Return True for masked placeholder values such as ********."""
    text = str(value or "")
    return bool(text) and len(text) >= 3 and set(text) == {"*"}


def _preserve_password(
    user_value: object, addon_value: object, entry_value: object
) -> str:
    """Preserve a panel password without using a secret file path for auth."""
    text = str(user_value or "")
    if text and not _is_masked(text):
        return text
    addon_text = str(addon_value or "")
    if addon_text and not _is_masked(addon_text) and not addon_text.startswith("/"):
        return addon_text
    entry_text = str(entry_value or "")
    return "" if _is_masked(entry_text) else entry_text


def _preserve_token(
    user_value: object,
    addon_value: object,
    entry_value: object,
    *,
    has_url: bool,
) -> str:
    """Preserve an MA token when the user did not enter a new one."""
    text = str(user_value or "").strip()
    if text and not _is_masked(text):
        return text
    if not has_url:
        return ""
    addon_text = str(addon_value or "").strip()
    if addon_text and not _is_masked(addon_text):
        return addon_text
    entry_text = str(entry_value or "").strip()
    return "" if _is_masked(entry_text) else entry_text


def _generate_credentials() -> tuple[str, str]:
    """Generate strong credentials for the add-on panel."""
    return (
        f"alexa_{secrets.token_hex(6)}",
        secrets.token_urlsafe(32),
    )


BOOL_OPTION_KEYS = {
    "ENABLE_APL",
    "SKIP_URL_VALIDATION",
    CONF_ENABLE_APL,
    CONF_SKIP_URL_VALIDATION,
}


def _normalise_bool_option(value: Any) -> bool:
    """Return a boolean for Supervisor option values."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _option_matches(options: Mapping[str, Any], key: str, value: Any) -> bool:
    """Compare an add-on option with the value we tried to write."""
    current = options.get(key)
    if key in BOOL_OPTION_KEYS:
        return _normalise_bool_option(current) == _normalise_bool_option(value)
    if key == "PORT":
        return str(current) == str(value)
    return str(current or "") == str(value or "")


def _validate_addon_options(
    options: Mapping[str, Any], expected: Mapping[str, Any]
) -> None:
    """Ensure the Supervisor stored the options we expect."""
    for key, value in expected.items():
        if not _option_matches(options, key, value):
            raise _FlowError("addon_options_invalid")


async def _async_check_https(
    hass: HomeAssistant,
    host: str,
    ignore_https: bool,
    *,
    expect_skill: bool = False,
) -> None:
    """Check that the public HTTPS endpoint is reachable."""
    url = f"https://{host}/"
    kwargs: dict[str, Any] = {
        "timeout": aiohttp.ClientTimeout(total=_HTTPS_TIMEOUT),
        "allow_redirects": False,
    }
    if ignore_https:
        kwargs["ssl"] = False
    try:
        async with async_get_clientsession(hass).get(url, **kwargs) as response:
            if expect_skill:
                if response.status not in (200, 401, 403):
                    raise _FlowError("https_unreachable", {"host": _safe_input(host)})
            elif response.status >= 500:
                raise _FlowError("https_unreachable", {"host": _safe_input(host)})
            return
    except (aiohttp.ClientError, TimeoutError, OSError) as err:
        raise _FlowError("https_unreachable", {"host": _safe_input(host)}) from err


async def _async_wait_for_status(api: AlexaMaSkillApi) -> None:
    """Wait for the add-on status endpoint to respond."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + ADDON_START_TIMEOUT
    while True:
        try:
            await api.async_get_status()
            return
        except AlexaMaSkillAuthError as err:
            raise _FlowError("invalid_auth") from err
        except AlexaMaSkillApiError as err:
            if loop.time() >= deadline:
                raise _FlowError("addon_start_timeout") from err
            await asyncio.sleep(ADDON_START_POLL_INTERVAL)


def _notify_options_issue(hass: HomeAssistant, message: str) -> None:
    """Show a non-secret notification about a partial options update."""
    try:
        from homeassistant.components import persistent_notification

        persistent_notification.async_create(
            hass,
            message,
            "Alexa MA Skill",
        )
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning(
            "Could not create the options notification: %s", type(err).__name__
        )


def _options_issue_message(hass: HomeAssistant, *, restart_failed: bool) -> str:
    """Return a localized message for a skipped or failed restart."""
    if str(hass.config.language).lower().startswith("pt"):
        if restart_failed:
            return (
                "As opções foram salvas, mas o reinício do add-on falhou. "
                "Reinicie o add-on manualmente e verifique os logs."
            )
        return (
            "As opções foram salvas. O reinício do add-on foi cancelado; "
            "reinicie manualmente para aplicar."
        )
    if restart_failed:
        return (
            "The options were saved, but the add-on restart failed. Restart "
            "the add-on manually and check the logs."
        )
    return (
        "The options were saved. The add-on restart was skipped; restart it "
        "manually to apply the changes."
    )


def _locale_selector() -> SelectSelector:
    """Return a locale selector."""
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                SelectOptionDict(value=locale, label=locale)
                for locale in ALLOWED_LOCALES
            ]
        )
    )


def _password_selector() -> TextSelector:
    """Return a password selector."""
    return TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


def _scan_interval_selector() -> NumberSelector:
    """Return the coordinator interval selector."""
    return NumberSelector(
        NumberSelectorConfig(
            min=MIN_SCAN_INTERVAL,
            max=MAX_SCAN_INTERVAL,
            step=1,
            mode=NumberSelectorMode.BOX,
        )
    )


def _addon_selector(candidates: list[AddonCandidate]) -> SelectSelector:
    """Return a selector for the matching add-on slugs."""
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                SelectOptionDict(
                    value=candidate.slug,
                    label=f"{candidate.name} ({candidate.slug})",
                )
                for candidate in candidates
            ]
        )
    )


async def _async_refresh_checklist(runtime: Any, *, stage: str) -> None:
    """Refresh the coordinator before building the checklist.

    ``async_request_refresh`` may return before the debounced update runs, so
    the checklist could be built from stale data. ``async_refresh`` waits for
    the public coordinator update to finish. A failure must not block the flow,
    but it must be logged so the form is not treated as successfully refreshed.
    """
    try:
        await runtime.coordinator.async_refresh()
    except Exception as err:  # noqa: BLE001 - keep the checklist usable
        _LOGGER.warning(
            "Checklist refresh %s failed; using the last known data: %s",
            stage,
            type(err).__name__,
        )
        return

    if not runtime.coordinator.last_update_success:
        _LOGGER.warning(
            "Checklist refresh %s did not complete successfully; "
            "the checklist may show outdated data",
            stage,
        )


class AlexaMaSkillConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Alexa MA Skill config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._pending_data: dict[str, Any] = {}
        self._reauth_entry: ConfigEntry | None = None
        self._addon_candidates: list[AddonCandidate] = []
        self._addon_slug: str = ""

    def _resolve_addon(self, preferred_slug: str = "") -> list[AddonCandidate]:
        """Discover matching add-ons and select one when unambiguous."""
        supervisor = AlexaMaSkillSupervisor(self.hass)
        candidates = supervisor.discover_addons()
        self._addon_candidates = candidates
        if not candidates:
            self._addon_slug = ""
        elif preferred_slug and any(
            candidate.slug == preferred_slug for candidate in candidates
        ):
            self._addon_slug = preferred_slug
        elif len(candidates) == 1:
            self._addon_slug = candidates[0].slug
        else:
            self._addon_slug = ""
        return candidates

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> AlexaMaSkillOptionsFlow:
        """Return the options flow."""
        return AlexaMaSkillOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Start the flow and choose managed or manual mode."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        supervisor = AlexaMaSkillSupervisor(self.hass)
        if supervisor.available:
            return await self.async_step_addon()
        return await self.async_step_manual()

    def _addon_schema(self, defaults: Mapping[str, Any] | None = None) -> vol.Schema:
        """Return the managed add-on schema."""
        defaults = defaults or {}
        return vol.Schema(
            {
                vol.Required(
                    CONF_SKILL_HOSTNAME,
                    default=defaults.get(CONF_SKILL_HOSTNAME, ""),
                ): TextSelector(),
                vol.Optional(
                    CONF_MA_HOSTNAME,
                    default=defaults.get(CONF_MA_HOSTNAME, ""),
                ): TextSelector(),
                vol.Required(
                    CONF_LOCALE,
                    default=defaults.get(CONF_LOCALE, DEFAULT_LOCALE),
                ): _locale_selector(),
                vol.Required(
                    CONF_ENABLE_APL,
                    default=bool(defaults.get(CONF_ENABLE_APL, False)),
                ): BooleanSelector(),
                vol.Required(
                    CONF_SKIP_URL_VALIDATION,
                    default=bool(defaults.get(CONF_SKIP_URL_VALIDATION, False)),
                ): BooleanSelector(),
                vol.Optional(
                    CONF_MA_API_URL,
                    default=defaults.get(CONF_MA_API_URL, ""),
                ): TextSelector(),
                vol.Optional(
                    CONF_MA_API_TOKEN,
                    default="",
                ): _password_selector(),
                vol.Required(
                    CONF_IGNORE_HTTPS,
                    default=bool(defaults.get(CONF_IGNORE_HTTPS, False)),
                ): BooleanSelector(),
            }
        )

    async def async_step_addon(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure the managed add-on."""
        schema = self._addon_schema(user_input)
        try:
            candidates = self._resolve_addon(self._addon_slug)
        except (SupervisorOperationError, SupervisorUnavailableError):
            return self.async_show_form(
                step_id="addon",
                data_schema=schema,
                errors={"base": "cannot_connect"},
            )
        if not candidates:
            return self.async_show_form(
                step_id="addon",
                data_schema=schema,
                errors={"base": "addon_not_installed"},
            )
        if not self._addon_slug:
            return await self.async_step_addon_select()
        if user_input is None:
            return self.async_show_form(step_id="addon", data_schema=schema)

        try:
            skill_hostname = _clean_hostname(user_input.get(CONF_SKILL_HOSTNAME))
            ma_hostname = _clean_hostname(
                user_input.get(CONF_MA_HOSTNAME), required=False
            )
            ma_api_url = _clean_ma_api_url(user_input.get(CONF_MA_API_URL, ""))
            ma_api_token = _validate_ma_api_pair(
                ma_api_url, str(user_input.get(CONF_MA_API_TOKEN) or "")
            )
            locale = str(user_input.get(CONF_LOCALE, DEFAULT_LOCALE))
            if locale not in ALLOWED_LOCALES:
                raise _FlowError("invalid_hostname", {"host": _safe_input(locale)})
            enable_apl = bool(user_input.get(CONF_ENABLE_APL, False))
            skip_url_validation = bool(user_input.get(CONF_SKIP_URL_VALIDATION, False))
            ignore_https = bool(user_input.get(CONF_IGNORE_HTTPS, False))

            supervisor = AlexaMaSkillSupervisor(self.hass)
            try:
                supervisor.select_addon(self._addon_slug)
            except SupervisorOperationError as err:
                raise _FlowError("cannot_connect") from err
            try:
                if not await supervisor.async_is_installed():
                    raise _FlowError("addon_not_installed")
                info = await supervisor.async_get_info()
            except (SupervisorOperationError, SupervisorUnavailableError) as err:
                raise _FlowError("cannot_connect") from err

            existing_skill_id = str(info.options.get("SKILL_ID") or "").strip()
            existing_ma_api_url = str(info.options.get("MA_API_URL") or "").strip()
            existing_ma_api_token = str(info.options.get("MA_API_TOKEN") or "")
            if not ma_api_url:
                ma_api_url = existing_ma_api_url
            if ma_api_url and not ma_api_token:
                ma_api_token = existing_ma_api_token

            existing_username = str(info.options.get("APP_USERNAME") or "").strip()
            existing_password = str(info.options.get("APP_PASSWORD") or "")
            reuse_credentials = bool(
                existing_username
                and existing_password
                and not existing_username.startswith("/")
                and not existing_password.startswith("/")
            )
            if reuse_credentials:
                username, password = existing_username, existing_password
            else:
                username, password = _generate_credentials()

            addon_options = {
                "SKILL_HOSTNAME": skill_hostname,
                "MA_HOSTNAME": ma_hostname,
                "APP_USERNAME": username,
                "APP_PASSWORD": password,
                "PORT": str(DEFAULT_PORT),
                "LOCALE": locale,
                "ENABLE_APL": enable_apl,
                "SKIP_URL_VALIDATION": skip_url_validation,
                "SKILL_ID": existing_skill_id,
                "MA_API_URL": ma_api_url,
                "MA_API_TOKEN": ma_api_token,
            }
            try:
                await supervisor.async_set_options(addon_options)
                updated_info = await supervisor.async_get_info()
            except (SupervisorOperationError, SupervisorUnavailableError) as err:
                raise _FlowError("addon_options_invalid") from err
            _validate_addon_options(updated_info.options, addon_options)

            base_url = (
                f"http://{updated_info.hostname or addon_hostname(self._addon_slug)}"
                f":{DEFAULT_PORT}"
            )
            api = AlexaMaSkillApi(
                self.hass,
                base_url,
                username,
                password,
                ignore_https=ignore_https,
            )
            try:
                await supervisor.async_start_or_restart()
            except (SupervisorOperationError, SupervisorUnavailableError) as err:
                raise _FlowError("cannot_connect") from err
            await _async_wait_for_status(api)

            # The public endpoint can only be tested after the add-on is running.
            await _async_check_https(
                self.hass, skill_hostname, ignore_https, expect_skill=True
            )
            if ma_hostname:
                await _async_check_https(self.hass, ma_hostname, ignore_https)

            self._pending_data = {
                CONF_MANAGED: True,
                CONF_ADDON_SLUG: self._addon_slug,
                CONF_BASE_URL: base_url,
                CONF_USERNAME: username,
                CONF_PASSWORD: password,
                CONF_SKILL_HOSTNAME: skill_hostname,
                CONF_MA_HOSTNAME: ma_hostname,
                CONF_LOCALE: locale,
                CONF_ENABLE_APL: enable_apl,
                CONF_SKIP_URL_VALIDATION: skip_url_validation,
                CONF_SKILL_ID: existing_skill_id,
                CONF_MA_API_URL: ma_api_url,
                CONF_MA_API_TOKEN: ma_api_token,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_IGNORE_HTTPS: ignore_https,
            }
            if reuse_credentials:
                return self.async_create_entry(
                    title=_entry_title(skill_hostname),
                    data=self._pending_data,
                )
            return await self.async_step_credentials()
        except _FlowError as err:
            return self.async_show_form(
                step_id="addon",
                data_schema=schema,
                errors={"base": err.error},
                description_placeholders=err.placeholders,
            )
        except Exception as err:  # noqa: BLE001 - never log form values
            _LOGGER.error(
                "Unexpected error in the add-on config flow: %s",
                type(err).__name__,
            )
            return self.async_show_form(
                step_id="addon",
                data_schema=schema,
                errors={"base": "cannot_connect"},
            )

    async def async_step_addon_select(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which matching add-on should be managed."""
        if not self._addon_candidates:
            return await self.async_step_addon()

        errors: dict[str, str] = {}
        if user_input is not None:
            selected = str(user_input.get(CONF_ADDON_SLUG) or "")
            if any(candidate.slug == selected for candidate in self._addon_candidates):
                self._addon_slug = selected
                return await self.async_step_addon()
            errors["base"] = "invalid_addon_slug"

        default = self._addon_slug or self._addon_candidates[0].slug
        return self.async_show_form(
            step_id="addon_select",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDON_SLUG, default=default): _addon_selector(
                        self._addon_candidates
                    )
                }
            ),
            errors=errors,
        )

    def _manual_schema(self, defaults: Mapping[str, Any] | None = None) -> vol.Schema:
        """Return the manual mode schema."""
        defaults = defaults or {}
        return vol.Schema(
            {
                vol.Required(
                    CONF_BASE_URL,
                    default=defaults.get(CONF_BASE_URL, DEFAULT_BASE_URL),
                ): TextSelector(),
                vol.Required(
                    CONF_USERNAME,
                    default=defaults.get(CONF_USERNAME, ""),
                ): TextSelector(),
                vol.Required(
                    CONF_PASSWORD,
                    default="",
                ): _password_selector(),
                vol.Required(
                    CONF_SKILL_HOSTNAME,
                    default=defaults.get(CONF_SKILL_HOSTNAME, ""),
                ): TextSelector(),
                vol.Optional(
                    CONF_MA_HOSTNAME,
                    default=defaults.get(CONF_MA_HOSTNAME, ""),
                ): TextSelector(),
                vol.Required(
                    CONF_LOCALE,
                    default=defaults.get(CONF_LOCALE, DEFAULT_LOCALE),
                ): _locale_selector(),
                vol.Required(
                    CONF_ENABLE_APL,
                    default=bool(defaults.get(CONF_ENABLE_APL, False)),
                ): BooleanSelector(),
                vol.Required(
                    CONF_SKIP_URL_VALIDATION,
                    default=bool(defaults.get(CONF_SKIP_URL_VALIDATION, False)),
                ): BooleanSelector(),
                vol.Optional(
                    CONF_MA_API_URL,
                    default=defaults.get(CONF_MA_API_URL, ""),
                ): TextSelector(),
                vol.Optional(
                    CONF_MA_API_TOKEN,
                    default="",
                ): _password_selector(),
                vol.Required(
                    CONF_IGNORE_HTTPS,
                    default=bool(defaults.get(CONF_IGNORE_HTTPS, False)),
                ): BooleanSelector(),
            }
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure an externally managed container."""
        schema = self._manual_schema(user_input)
        if user_input is None:
            return self.async_show_form(step_id="manual", data_schema=schema)

        try:
            base_url = _clean_base_url(user_input.get(CONF_BASE_URL))
            username = str(user_input.get(CONF_USERNAME) or "").strip()
            password = str(user_input.get(CONF_PASSWORD) or "")
            if not username or not password:
                raise _FlowError("invalid_auth")
            skill_hostname = _clean_hostname(user_input.get(CONF_SKILL_HOSTNAME))
            ma_hostname = _clean_hostname(
                user_input.get(CONF_MA_HOSTNAME), required=False
            )
            ma_api_url = _clean_ma_api_url(user_input.get(CONF_MA_API_URL, ""))
            ma_api_token = _validate_ma_api_pair(
                ma_api_url, str(user_input.get(CONF_MA_API_TOKEN) or "")
            )
            locale = str(user_input.get(CONF_LOCALE, DEFAULT_LOCALE))
            if locale not in ALLOWED_LOCALES:
                raise _FlowError("invalid_hostname", {"host": _safe_input(locale)})
            enable_apl = bool(user_input.get(CONF_ENABLE_APL, False))
            skip_url_validation = bool(user_input.get(CONF_SKIP_URL_VALIDATION, False))
            ignore_https = bool(user_input.get(CONF_IGNORE_HTTPS, False))

            api = AlexaMaSkillApi(
                self.hass,
                base_url,
                username,
                password,
                ignore_https=ignore_https,
            )
            try:
                await api.async_get_status()
            except AlexaMaSkillAuthError as err:
                raise _FlowError("invalid_auth") from err
            except AlexaMaSkillApiError as err:
                raise _FlowError("cannot_connect") from err

            data = {
                CONF_MANAGED: False,
                CONF_ADDON_SLUG: "",
                CONF_BASE_URL: base_url,
                CONF_USERNAME: username,
                CONF_PASSWORD: password,
                CONF_SKILL_HOSTNAME: skill_hostname,
                CONF_MA_HOSTNAME: ma_hostname,
                CONF_LOCALE: locale,
                CONF_ENABLE_APL: enable_apl,
                CONF_SKIP_URL_VALIDATION: skip_url_validation,
                CONF_SKILL_ID: "",
                CONF_MA_API_URL: ma_api_url,
                CONF_MA_API_TOKEN: ma_api_token,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_IGNORE_HTTPS: ignore_https,
            }
            return self.async_create_entry(
                title=_entry_title(skill_hostname),
                data=data,
            )
        except _FlowError as err:
            return self.async_show_form(
                step_id="manual",
                data_schema=schema,
                errors={"base": err.error},
                description_placeholders=err.placeholders,
            )
        except Exception as err:  # noqa: BLE001 - never log form values
            _LOGGER.error(
                "Unexpected error in the manual config flow: %s",
                type(err).__name__,
            )
            return self.async_show_form(
                step_id="manual",
                data_schema=schema,
                errors={"base": "cannot_connect"},
            )

    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show generated credentials once, then create the entry."""
        if user_input is None:
            return self.async_show_form(
                step_id="credentials",
                data_schema=vol.Schema(
                    {vol.Optional(_CONFIRM_KEY, default=True): BooleanSelector()}
                ),
                description_placeholders={
                    "username": self._pending_data.get(CONF_USERNAME, ""),
                    "password": self._pending_data.get(CONF_PASSWORD, ""),
                },
            )
        return self.async_create_entry(
            title=_entry_title(self._pending_data.get(CONF_SKILL_HOSTNAME, "")),
            data=self._pending_data,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Handle a reauthentication request."""
        entry_id = self.context.get("entry_id")
        entry = self.hass.config_entries.async_get_entry(entry_id) if entry_id else None
        if entry is None:
            return self.async_abort(reason="reauth_failed")
        self._reauth_entry = entry
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Reauthenticate in managed or manual mode."""
        entry = self._reauth_entry
        if entry is None:
            return self.async_abort(reason="reauth_failed")

        config = entry_config(entry)
        if bool(config.get(CONF_MANAGED, False)):
            try:
                await self._async_reauth_managed(entry, config)
            except _FlowError as err:
                return self.async_show_form(
                    step_id="reauth_confirm",
                    data_schema=vol.Schema(
                        {vol.Optional(_CONFIRM_KEY, default=True): BooleanSelector()}
                    ),
                    errors={"base": err.error},
                    description_placeholders=err.placeholders,
                )
            except Exception as err:  # noqa: BLE001 - never log form values
                _LOGGER.error(
                    "Unexpected error in managed reauth: %s",
                    type(err).__name__,
                )
                return self.async_show_form(
                    step_id="reauth_confirm",
                    data_schema=vol.Schema(
                        {vol.Optional(_CONFIRM_KEY, default=True): BooleanSelector()}
                    ),
                    errors={"base": "cannot_connect"},
                )
            return self.async_abort(reason="reauth_successful")

        schema = self._reauth_manual_schema(config, user_input)
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm", data_schema=schema)
        try:
            base_url = _clean_base_url(user_input.get(CONF_BASE_URL))
            username = str(user_input.get(CONF_USERNAME) or "").strip()
            password = str(user_input.get(CONF_PASSWORD) or "")
            if not username or not password:
                raise _FlowError("invalid_auth")
            ignore_https = bool(user_input.get(CONF_IGNORE_HTTPS, False))
            api = AlexaMaSkillApi(
                self.hass,
                base_url,
                username,
                password,
                ignore_https=ignore_https,
            )
            try:
                await api.async_get_status()
            except AlexaMaSkillAuthError as err:
                raise _FlowError("invalid_auth") from err
            except AlexaMaSkillApiError as err:
                raise _FlowError("cannot_connect") from err
            await self._async_update_entry(
                entry,
                {
                    CONF_BASE_URL: base_url,
                    CONF_USERNAME: username,
                    CONF_PASSWORD: password,
                    CONF_IGNORE_HTTPS: ignore_https,
                },
            )
            return self.async_abort(reason="reauth_successful")
        except _FlowError as err:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=schema,
                errors={"base": err.error},
                description_placeholders=err.placeholders,
            )
        except Exception as err:  # noqa: BLE001 - never log form values
            _LOGGER.error(
                "Unexpected error in manual reauth: %s",
                type(err).__name__,
            )
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=schema,
                errors={"base": "cannot_connect"},
            )

    def _reauth_manual_schema(
        self,
        config: Mapping[str, Any],
        defaults: Mapping[str, Any] | None = None,
    ) -> vol.Schema:
        """Return the manual reauth schema."""
        defaults = defaults or {}
        return vol.Schema(
            {
                vol.Required(
                    CONF_BASE_URL,
                    default=defaults.get(
                        CONF_BASE_URL,
                        config.get(CONF_BASE_URL, DEFAULT_BASE_URL),
                    ),
                ): TextSelector(),
                vol.Required(
                    CONF_USERNAME,
                    default=defaults.get(CONF_USERNAME, config.get(CONF_USERNAME, "")),
                ): TextSelector(),
                vol.Required(CONF_PASSWORD, default=""): _password_selector(),
                vol.Required(
                    CONF_IGNORE_HTTPS,
                    default=bool(
                        defaults.get(
                            CONF_IGNORE_HTTPS,
                            config.get(CONF_IGNORE_HTTPS, False),
                        )
                    ),
                ): BooleanSelector(),
            }
        )

    async def _async_reauth_managed(
        self, entry: ConfigEntry, config: Mapping[str, Any]
    ) -> None:
        """Re-read credentials from the managed add-on."""
        preferred_slug = str(config.get(CONF_ADDON_SLUG) or "").strip()
        supervisor = AlexaMaSkillSupervisor(self.hass)
        try:
            candidates = supervisor.discover_addons()
        except (SupervisorOperationError, SupervisorUnavailableError) as err:
            raise _FlowError("cannot_connect") from err
        if not candidates:
            raise _FlowError("addon_not_installed")
        if preferred_slug and any(
            candidate.slug == preferred_slug for candidate in candidates
        ):
            addon_slug = preferred_slug
        elif len(candidates) == 1:
            addon_slug = candidates[0].slug
        else:
            raise _FlowError("addon_selection_required")

        supervisor = AlexaMaSkillSupervisor(self.hass)
        try:
            supervisor.select_addon(addon_slug)
        except SupervisorOperationError as err:
            raise _FlowError("cannot_connect") from err
        try:
            if not await supervisor.async_is_installed():
                raise _FlowError("addon_not_installed")
            info = await supervisor.async_get_info()
        except (SupervisorOperationError, SupervisorUnavailableError) as err:
            raise _FlowError("cannot_connect") from err

        username = str(info.options.get("APP_USERNAME") or "").strip()
        password = str(info.options.get("APP_PASSWORD") or "")
        if (
            not username
            or not password
            or username.startswith("/")
            or password.startswith("/")
        ):
            raise _FlowError("addon_options_invalid")

        base_url = (
            f"http://{info.hostname or addon_hostname(addon_slug)}:{DEFAULT_PORT}"
        )
        api = AlexaMaSkillApi(
            self.hass,
            base_url,
            username,
            password,
            ignore_https=bool(config.get(CONF_IGNORE_HTTPS, False)),
        )
        try:
            await api.async_get_status()
        except AlexaMaSkillAuthError as err:
            raise _FlowError("invalid_auth") from err
        except AlexaMaSkillApiError as err:
            raise _FlowError("cannot_connect") from err

        await self._async_update_entry(
            entry,
            {
                CONF_ADDON_SLUG: addon_slug,
                CONF_BASE_URL: base_url,
                CONF_USERNAME: username,
                CONF_PASSWORD: password,
            },
        )

    async def _async_update_entry(
        self, entry: ConfigEntry, updates: Mapping[str, Any]
    ) -> None:
        """Update data and options without duplicating reload logic."""
        data = {**entry.data, **updates}
        options = {**entry.options, **updates} if entry.options else entry.options
        self.hass.config_entries.async_update_entry(entry, data=data, options=options)
        if entry.state is not ConfigEntryState.LOADED:
            await self.hass.config_entries.async_reload(entry.entry_id)


class AlexaMaSkillOptionsFlow(OptionsFlowWithConfigEntry):
    """Handle options for an existing entry."""

    def _discover_addons(
        self, config: Mapping[str, Any]
    ) -> tuple[list[AddonCandidate], str]:
        """Return matching add-ons and the currently selected slug."""
        if not bool(config.get(CONF_MANAGED, False)):
            return [], ""
        candidates = AlexaMaSkillSupervisor(self.hass).discover_addons()
        stored_slug = str(config.get(CONF_ADDON_SLUG) or "").strip()
        if stored_slug and any(
            candidate.slug == stored_slug for candidate in candidates
        ):
            return candidates, stored_slug
        if len(candidates) == 1:
            return candidates, candidates[0].slug
        return candidates, ""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the integration menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["settings", "setup"],
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit the integration and add-on settings."""
        entry = self.config_entry
        config = entry_config(entry)
        managed = bool(config.get(CONF_MANAGED, False))
        self._pending_config: dict[str, Any] | None = None
        self._pending_supervisor: AlexaMaSkillSupervisor | None = None
        self._pending_api: AlexaMaSkillApi | None = None
        self._pending_changes: list[str] = []
        suggested_skill_id = ""
        runtime = self.hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if runtime is not None and runtime.coordinator.data is not None:
            suggested_skill_id = runtime.coordinator.data.suggested_skill_id or ""
        try:
            addon_candidates, selected_addon_slug = self._discover_addons(config)
        except (SupervisorOperationError, SupervisorUnavailableError):
            addon_candidates, selected_addon_slug = [], ""
        schema = self._options_schema(
            config,
            managed,
            user_input,
            suggested_skill_id=suggested_skill_id,
            addon_candidates=addon_candidates,
            selected_addon_slug=selected_addon_slug,
        )
        if user_input is None:
            return self.async_show_form(step_id="settings", data_schema=schema)

        try:
            skill_hostname = _clean_hostname(user_input.get(CONF_SKILL_HOSTNAME))
            ma_hostname = _clean_hostname(
                user_input.get(CONF_MA_HOSTNAME), required=False
            )
            username = str(
                user_input.get(CONF_USERNAME) or config.get(CONF_USERNAME) or ""
            ).strip()
            password = str(
                user_input.get(CONF_PASSWORD) or config.get(CONF_PASSWORD) or ""
            )
            if not username or not password:
                raise _FlowError("invalid_auth")

            ma_api_url = _clean_ma_api_url(user_input.get(CONF_MA_API_URL, ""))
            ma_api_token = _validate_ma_api_pair(
                ma_api_url,
                str(user_input.get(CONF_MA_API_TOKEN) or ""),
                str(config.get(CONF_MA_API_TOKEN) or ""),
            )
            locale = str(user_input.get(CONF_LOCALE, DEFAULT_LOCALE))
            if locale not in ALLOWED_LOCALES:
                raise _FlowError("invalid_hostname", {"host": _safe_input(locale)})
            enable_apl = bool(user_input.get(CONF_ENABLE_APL, False))
            skip_url_validation = bool(user_input.get(CONF_SKIP_URL_VALIDATION, False))
            skill_id = str(user_input.get(CONF_SKILL_ID) or "").strip()
            try:
                scan_interval = int(
                    user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                )
            except (TypeError, ValueError):
                scan_interval = DEFAULT_SCAN_INTERVAL
            scan_interval = max(
                MIN_SCAN_INTERVAL, min(MAX_SCAN_INTERVAL, scan_interval)
            )
            ignore_https = bool(user_input.get(CONF_IGNORE_HTTPS, False))

            addon_slug = ""
            if managed:
                try:
                    candidates = AlexaMaSkillSupervisor(self.hass).discover_addons()
                except (
                    SupervisorOperationError,
                    SupervisorUnavailableError,
                ) as err:
                    raise _FlowError("cannot_connect") from err
                if not candidates:
                    raise _FlowError("addon_not_installed")
                requested_slug = str(
                    user_input.get(CONF_ADDON_SLUG) or config.get(CONF_ADDON_SLUG) or ""
                ).strip()
                if requested_slug and any(
                    candidate.slug == requested_slug for candidate in candidates
                ):
                    addon_slug = requested_slug
                elif len(candidates) == 1:
                    addon_slug = candidates[0].slug
                else:
                    raise _FlowError("addon_selection_required")

            base_url = (
                _clean_base_url(user_input.get(CONF_BASE_URL))
                if not managed
                else str(config.get(CONF_BASE_URL) or DEFAULT_BASE_URL)
            )

            addon_changes: dict[str, Any] = {}
            if managed:
                supervisor = AlexaMaSkillSupervisor(self.hass)
                try:
                    supervisor.select_addon(addon_slug)
                except SupervisorOperationError as err:
                    raise _FlowError("cannot_connect") from err
                try:
                    if not await supervisor.async_is_installed():
                        raise _FlowError("addon_not_installed")
                    info = await supervisor.async_get_info()
                except (
                    SupervisorOperationError,
                    SupervisorUnavailableError,
                ) as err:
                    raise _FlowError("cannot_connect") from err

                # Preserve raw secrets that the user did not change. If the
                # add-on stores a file path, keep the integration's stored
                # password for HTTP basic auth instead of using the path.
                password = _preserve_password(
                    user_input.get(CONF_PASSWORD),
                    info.options.get("APP_PASSWORD"),
                    config.get(CONF_PASSWORD),
                )
                if (
                    ma_api_url
                    and not str(user_input.get(CONF_MA_API_TOKEN) or "").strip()
                ):
                    ma_api_token = _preserve_token(
                        "",
                        info.options.get("MA_API_TOKEN"),
                        config.get(CONF_MA_API_TOKEN),
                        has_url=True,
                    )

                base_url = (
                    f"http://{info.hostname or addon_hostname(addon_slug)}"
                    f":{DEFAULT_PORT}"
                )
                addon_options = {
                    "SKILL_HOSTNAME": skill_hostname,
                    "MA_HOSTNAME": ma_hostname,
                    "APP_USERNAME": username,
                    "APP_PASSWORD": password,
                    "PORT": str(DEFAULT_PORT),
                    "LOCALE": locale,
                    "ENABLE_APL": enable_apl,
                    "SKIP_URL_VALIDATION": skip_url_validation,
                    "SKILL_ID": skill_id,
                    "MA_API_URL": ma_api_url,
                    "MA_API_TOKEN": ma_api_token,
                }
                addon_changes = {
                    key: value
                    for key, value in addon_options.items()
                    if not _option_matches(info.options, key, value)
                }
                api = AlexaMaSkillApi(
                    self.hass,
                    base_url,
                    username,
                    password,
                    ignore_https=ignore_https,
                )
                if addon_changes:
                    try:
                        await supervisor.async_set_options(addon_options)
                        updated_info = await supervisor.async_get_info()
                    except (
                        SupervisorOperationError,
                        SupervisorUnavailableError,
                    ) as err:
                        raise _FlowError("addon_options_invalid") from err
                    _validate_addon_options(updated_info.options, addon_options)
                else:
                    try:
                        await api.async_get_status()
                    except AlexaMaSkillAuthError as err:
                        raise _FlowError("invalid_auth") from err
                    except AlexaMaSkillApiError as err:
                        raise _FlowError("cannot_connect") from err
            else:
                api = AlexaMaSkillApi(
                    self.hass,
                    base_url,
                    username,
                    password,
                    ignore_https=ignore_https,
                )
                try:
                    await api.async_get_status()
                except AlexaMaSkillAuthError as err:
                    raise _FlowError("invalid_auth") from err
                except AlexaMaSkillApiError as err:
                    raise _FlowError("cannot_connect") from err

            new_config = {
                CONF_MANAGED: managed,
                CONF_ADDON_SLUG: addon_slug,
                CONF_BASE_URL: base_url,
                CONF_USERNAME: username,
                CONF_PASSWORD: password,
                CONF_SKILL_HOSTNAME: skill_hostname,
                CONF_MA_HOSTNAME: ma_hostname,
                CONF_LOCALE: locale,
                CONF_ENABLE_APL: enable_apl,
                CONF_SKIP_URL_VALIDATION: skip_url_validation,
                CONF_SKILL_ID: skill_id,
                CONF_MA_API_URL: ma_api_url,
                CONF_MA_API_TOKEN: ma_api_token,
                CONF_SCAN_INTERVAL: scan_interval,
                CONF_IGNORE_HTTPS: ignore_https,
            }
            runtime = self.hass.data.get(DOMAIN, {}).get(entry.entry_id)
            if runtime is not None:
                changed_keys = set(addon_changes)
                changed_keys.update(
                    key for key, value in new_config.items() if config.get(key) != value
                )
                if changed_keys:
                    await runtime.checklist.async_clear_for_keys(changed_keys)
            if managed and addon_changes:
                self._pending_config = new_config
                self._pending_supervisor = supervisor
                self._pending_api = api
                self._pending_changes = list(addon_changes)
                return await self.async_step_restart_confirm()
            return self.async_create_entry(title="", data=new_config)
        except _FlowError as err:
            return self.async_show_form(
                step_id="settings",
                data_schema=schema,
                errors={"base": err.error},
                description_placeholders=err.placeholders,
            )
        except Exception as err:  # noqa: BLE001 - never log form values
            _LOGGER.error(
                "Unexpected error in the options flow: %s",
                type(err).__name__,
            )
            return self.async_show_form(
                step_id="settings",
                data_schema=schema,
                errors={"base": "cannot_connect"},
            )

    async def async_step_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the assisted setup progress and manual confirmations."""
        runtime = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        if runtime is None:
            return self.async_abort(reason="not_loaded")

        await _async_refresh_checklist(runtime, stage="before opening")
        config = entry_config(self.config_entry)
        _state, attrs = build_setup_checklist(
            config,
            runtime.coordinator.data,
            self.hass.config.language,
            runtime.checklist.confirmations,
        )

        if user_input is not None:
            # Clear unchecked steps first so a dependent cannot be re-added in
            # the same submission after its prerequisite is unchecked.
            for step in attrs["manual_steps"]:
                if not bool(user_input.get(step["id"])):
                    await runtime.checklist.async_set(step["id"], False)

            # Rebuild after clearing; the previous statuses may still show a
            # prerequisite as done and would incorrectly restore dependents.
            _state, attrs = build_setup_checklist(
                config,
                runtime.coordinator.data,
                self.hass.config.language,
                runtime.checklist.confirmations,
            )
            status_by_id = {step["id"]: step["status"] for step in attrs["checklist"]}
            for step in attrs["manual_steps"]:
                if bool(user_input.get(step["id"])) and all(
                    status_by_id.get(dependency) in ("done", "not_applicable")
                    for dependency in step["dependencies"]
                ):
                    await runtime.checklist.async_set(step["id"], True)
            await _async_refresh_checklist(runtime, stage="after saving")
            if user_input.get("back_to_menu"):
                return await self.async_step_init()
            _state, attrs = build_setup_checklist(
                config,
                runtime.coordinator.data,
                self.hass.config.language,
                runtime.checklist.confirmations,
            )

        fields: dict[Any, Any] = {}
        for step in attrs["manual_steps"]:
            fields[vol.Optional(step["id"], default=step["confirmed"])] = (
                BooleanSelector()
            )
        fields[vol.Optional("back_to_menu", default=False)] = BooleanSelector()

        summary = "\n".join(
            f"[{'x' if step['done'] else ' '}] {step['title']} — {step['status_label']}"
            for step in attrs["checklist"]
        )
        details = "\n".join(
            f"{step['title']}: {step['result']}. {step['how_to_fix']}"
            for step in attrs["checklist"]
            if step["status"] in ("pending", "attention", "blocked")
        )
        progress = attrs["progress"]
        return self.async_show_form(
            step_id="setup",
            data_schema=vol.Schema(fields),
            description_placeholders={
                "progress": (
                    f"{progress['done']}/{progress['applicable']} "
                    f"({progress['percent']}%)"
                ),
                "next_step": progress.get("next_step_title") or "-",
                "summary": summary,
                "details": details or "-",
                "local_setup_url": attrs["local_setup_url"],
                "provider_api_url": attrs["provider_api_url"],
                "duplicate_warning": attrs["duplicate_warning"],
            },
        )

    async def async_step_restart_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask before restarting the add-on after saving options."""
        pending_config = getattr(self, "_pending_config", None)
        pending_supervisor = getattr(self, "_pending_supervisor", None)
        if pending_config is None or pending_supervisor is None:
            return await self.async_step_settings()

        if user_input is None:
            return self.async_show_form(
                step_id="restart_confirm",
                data_schema=vol.Schema(
                    {vol.Required(_CONFIRM_KEY, default=True): BooleanSelector()}
                ),
                description_placeholders={
                    "changes": ", ".join(getattr(self, "_pending_changes", []))
                },
            )

        if bool(user_input.get(_CONFIRM_KEY, True)):
            try:
                await pending_supervisor.async_start_or_restart()
                pending_api = getattr(self, "_pending_api", None)
                if pending_api is not None:
                    await _async_wait_for_status(pending_api)
            except (
                SupervisorOperationError,
                SupervisorUnavailableError,
                _FlowError,
            ) as err:
                _LOGGER.warning(
                    "Options saved, but add-on restart failed: %s",
                    type(err).__name__,
                )
                _notify_options_issue(
                    self.hass,
                    _options_issue_message(self.hass, restart_failed=True),
                )
            else:
                _LOGGER.info("Add-on restarted after options update")
        else:
            _LOGGER.info("Options saved; add-on restart skipped by user")
            _notify_options_issue(
                self.hass,
                _options_issue_message(self.hass, restart_failed=False),
            )

        self._pending_config = None
        self._pending_supervisor = None
        self._pending_api = None
        self._pending_changes = []
        return self.async_create_entry(title="", data=pending_config)

    def _options_schema(
        self,
        config: Mapping[str, Any],
        managed: bool,
        defaults: Mapping[str, Any] | None = None,
        *,
        suggested_skill_id: str = "",
        addon_candidates: list[AddonCandidate] | None = None,
        selected_addon_slug: str = "",
    ) -> vol.Schema:
        """Return the options schema."""
        defaults = defaults or {}
        current_locale = config.get(CONF_LOCALE, DEFAULT_LOCALE)
        if current_locale not in ALLOWED_LOCALES:
            current_locale = DEFAULT_LOCALE
        try:
            current_interval = int(
                config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            )
        except (TypeError, ValueError):
            current_interval = DEFAULT_SCAN_INTERVAL
        current_interval = max(
            MIN_SCAN_INTERVAL, min(MAX_SCAN_INTERVAL, current_interval)
        )

        fields: dict[Any, Any] = {
            vol.Required(
                CONF_SKILL_HOSTNAME,
                default=defaults.get(
                    CONF_SKILL_HOSTNAME, config.get(CONF_SKILL_HOSTNAME, "")
                ),
            ): TextSelector(),
            vol.Optional(
                CONF_MA_HOSTNAME,
                default=defaults.get(
                    CONF_MA_HOSTNAME, config.get(CONF_MA_HOSTNAME, "")
                ),
            ): TextSelector(),
            vol.Required(
                CONF_USERNAME,
                default=defaults.get(CONF_USERNAME, config.get(CONF_USERNAME, "")),
            ): TextSelector(),
            vol.Optional(CONF_PASSWORD, default=""): _password_selector(),
            vol.Required(
                CONF_LOCALE,
                default=defaults.get(CONF_LOCALE, current_locale),
            ): _locale_selector(),
            vol.Required(
                CONF_ENABLE_APL,
                default=bool(
                    defaults.get(CONF_ENABLE_APL, config.get(CONF_ENABLE_APL, False))
                ),
            ): BooleanSelector(),
            vol.Required(
                CONF_SKIP_URL_VALIDATION,
                default=bool(
                    defaults.get(
                        CONF_SKIP_URL_VALIDATION,
                        config.get(CONF_SKIP_URL_VALIDATION, False),
                    )
                ),
            ): BooleanSelector(),
            vol.Optional(
                CONF_SKILL_ID,
                default=defaults.get(
                    CONF_SKILL_ID,
                    config.get(CONF_SKILL_ID) or suggested_skill_id,
                ),
            ): TextSelector(),
            vol.Optional(
                CONF_MA_API_URL,
                default=defaults.get(CONF_MA_API_URL, config.get(CONF_MA_API_URL, "")),
            ): TextSelector(),
            vol.Optional(CONF_MA_API_TOKEN, default=""): _password_selector(),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, current_interval),
            ): _scan_interval_selector(),
            vol.Required(
                CONF_IGNORE_HTTPS,
                default=bool(
                    defaults.get(
                        CONF_IGNORE_HTTPS,
                        config.get(CONF_IGNORE_HTTPS, False),
                    )
                ),
            ): BooleanSelector(),
        }
        if managed and addon_candidates and len(addon_candidates) > 1:
            fields[
                vol.Required(
                    CONF_ADDON_SLUG,
                    default=defaults.get(
                        CONF_ADDON_SLUG,
                        selected_addon_slug or addon_candidates[0].slug,
                    ),
                )
            ] = _addon_selector(addon_candidates)
        if not managed:
            fields[
                vol.Required(
                    CONF_BASE_URL,
                    default=defaults.get(
                        CONF_BASE_URL,
                        config.get(CONF_BASE_URL, DEFAULT_BASE_URL),
                    ),
                )
            ] = TextSelector()
        return vol.Schema(fields)
