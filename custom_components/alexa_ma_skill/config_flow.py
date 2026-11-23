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
    DEFAULT_HOST,
    DEFAULT_LOCALE,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    NAME,
)
from .supervisor import (
    AlexaMaSkillSupervisor,
    SupervisorOperationError,
    SupervisorUnavailableError,
)
from .util import entry_config

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


def _clean_hostname(value: Any, *, required: bool = True) -> str:
    """Validate and normalize a bare hostname."""
    text = str(value or "").strip()
    if not text:
        if required:
            raise _FlowError("invalid_hostname", {"host": ""})
        return ""
    if "://" in text:
        raise _FlowError("invalid_hostname", {"host": text})
    text = text.rstrip(".")
    if not text:
        raise _FlowError("invalid_hostname", {"host": ""})
    if any(character in text for character in "/?#@\\ \t\r\n"):
        raise _FlowError("invalid_hostname", {"host": text})
    if ":" in text:
        raise _FlowError("invalid_hostname", {"host": text})
    if len(text) > 253:
        raise _FlowError("invalid_hostname", {"host": text})
    return text


def _clean_base_url(value: Any) -> str:
    """Validate and normalize the internal add-on base URL."""
    text = str(value or "").strip()
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https"):
        raise _FlowError("invalid_hostname", {"host": text})
    if not parsed.netloc or parsed.username or parsed.password:
        raise _FlowError("invalid_hostname", {"host": text})
    if parsed.path not in ("", "/") or parsed.params or parsed.query or parsed.fragment:
        raise _FlowError("invalid_hostname", {"host": text})
    return f"{parsed.scheme}://{parsed.netloc}"


def _clean_ma_api_url(value: Any) -> str:
    """Validate the optional Music Assistant API URL."""
    text = str(value or "").strip()
    if not text:
        return ""
    if any(character in text for character in " \t\r\n"):
        raise _FlowError("invalid_hostname", {"host": text})
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https", "ws", "wss") or not parsed.netloc:
        raise _FlowError("invalid_hostname", {"host": text})
    if parsed.username or parsed.password:
        raise _FlowError("invalid_hostname", {"host": text})
    return text


def _validate_ma_api_pair(url: str, token: str, current_token: str = "") -> str:
    """Require MA_API_URL and MA_API_TOKEN to be provided together."""
    token = token.strip()
    current_token = current_token.strip()
    effective_token = token or (current_token if url else "")
    if bool(url) != bool(effective_token):
        raise _FlowError("ma_api_incomplete")
    return effective_token


def _generate_credentials() -> tuple[str, str]:
    """Generate strong credentials for the add-on panel."""
    return (
        f"alexa_{secrets.token_hex(6)}",
        secrets.token_urlsafe(32),
    )


def _option_matches(options: Mapping[str, Any], key: str, value: Any) -> bool:
    """Compare an add-on option with the value we tried to write."""
    current = options.get(key)
    if key in (CONF_ENABLE_APL, CONF_SKIP_URL_VALIDATION):
        return bool(current) == bool(value)
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
    hass: HomeAssistant, host: str, ignore_https: bool
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
            if response.status >= 500:
                raise _FlowError("https_unreachable", {"host": host})
            return
    except (aiohttp.ClientError, TimeoutError, OSError) as err:
        raise _FlowError("https_unreachable", {"host": host}) from err


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


class AlexaMaSkillConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Alexa MA Skill config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._pending_data: dict[str, Any] = {}
        self._reauth_entry: ConfigEntry | None = None

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
                vol.Required(
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
        if user_input is None:
            return self.async_show_form(step_id="addon", data_schema=schema)

        try:
            skill_hostname = _clean_hostname(user_input.get(CONF_SKILL_HOSTNAME))
            ma_hostname = _clean_hostname(user_input.get(CONF_MA_HOSTNAME))
            ma_api_url = _clean_ma_api_url(user_input.get(CONF_MA_API_URL, ""))
            ma_api_token = _validate_ma_api_pair(
                ma_api_url, str(user_input.get(CONF_MA_API_TOKEN) or "")
            )
            locale = str(user_input.get(CONF_LOCALE, DEFAULT_LOCALE))
            if locale not in ALLOWED_LOCALES:
                raise _FlowError("invalid_hostname", {"host": locale})
            enable_apl = bool(user_input.get(CONF_ENABLE_APL, False))
            skip_url_validation = bool(user_input.get(CONF_SKIP_URL_VALIDATION, False))
            ignore_https = bool(user_input.get(CONF_IGNORE_HTTPS, False))

            supervisor = AlexaMaSkillSupervisor(self.hass)
            try:
                if not await supervisor.async_is_installed():
                    raise _FlowError("addon_not_installed")
                info = await supervisor.async_get_info()
            except (SupervisorOperationError, SupervisorUnavailableError) as err:
                raise _FlowError("cannot_connect") from err

            existing_skill_id = str(info.options.get("SKILL_ID") or "").strip()
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

            base_url = f"http://{updated_info.hostname or DEFAULT_HOST}:{DEFAULT_PORT}"
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
            await _async_check_https(self.hass, skill_hostname, ignore_https)
            await _async_check_https(self.hass, ma_hostname, ignore_https)

            self._pending_data = {
                CONF_MANAGED: True,
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
                vol.Required(
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
            ma_hostname = _clean_hostname(user_input.get(CONF_MA_HOSTNAME))
            ma_api_url = _clean_ma_api_url(user_input.get(CONF_MA_API_URL, ""))
            ma_api_token = _validate_ma_api_pair(
                ma_api_url, str(user_input.get(CONF_MA_API_TOKEN) or "")
            )
            locale = str(user_input.get(CONF_LOCALE, DEFAULT_LOCALE))
            if locale not in ALLOWED_LOCALES:
                raise _FlowError("invalid_hostname", {"host": locale})
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
                title=f"{NAME} ({skill_hostname})",
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
            title=f"{NAME} ({self._pending_data.get(CONF_SKILL_HOSTNAME, '')})",
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
        supervisor = AlexaMaSkillSupervisor(self.hass)
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

        base_url = f"http://{info.hostname or DEFAULT_HOST}:{DEFAULT_PORT}"
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

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit the integration and add-on settings."""
        entry = self.config_entry
        config = entry_config(entry)
        managed = bool(config.get(CONF_MANAGED, False))
        schema = self._options_schema(config, managed, user_input)
        if user_input is None:
            return self.async_show_form(step_id="init", data_schema=schema)

        try:
            skill_hostname = _clean_hostname(user_input.get(CONF_SKILL_HOSTNAME))
            ma_hostname = _clean_hostname(user_input.get(CONF_MA_HOSTNAME))
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
                raise _FlowError("invalid_hostname", {"host": locale})
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

            base_url = (
                _clean_base_url(user_input.get(CONF_BASE_URL))
                if not managed
                else str(config.get(CONF_BASE_URL) or DEFAULT_BASE_URL)
            )

            if managed:
                supervisor = AlexaMaSkillSupervisor(self.hass)
                try:
                    if not await supervisor.async_is_installed():
                        raise _FlowError("addon_not_installed")
                    info = await supervisor.async_get_info()
                except (
                    SupervisorOperationError,
                    SupervisorUnavailableError,
                ) as err:
                    raise _FlowError("cannot_connect") from err

                base_url = f"http://{info.hostname or DEFAULT_HOST}:{DEFAULT_PORT}"
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
                    try:
                        await supervisor.async_start_or_restart()
                    except (
                        SupervisorOperationError,
                        SupervisorUnavailableError,
                    ) as err:
                        raise _FlowError("cannot_connect") from err
                    api = AlexaMaSkillApi(
                        self.hass,
                        base_url,
                        username,
                        password,
                        ignore_https=ignore_https,
                    )
                    await _async_wait_for_status(api)
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
            return self.async_create_entry(title="", data=new_config)
        except _FlowError as err:
            return self.async_show_form(
                step_id="init",
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
                step_id="init",
                data_schema=schema,
                errors={"base": "cannot_connect"},
            )

    def _options_schema(
        self,
        config: Mapping[str, Any],
        managed: bool,
        defaults: Mapping[str, Any] | None = None,
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
            vol.Required(
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
                default=defaults.get(CONF_SKILL_ID, config.get(CONF_SKILL_ID, "")),
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
