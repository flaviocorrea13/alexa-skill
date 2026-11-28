#!/usr/bin/env python3
"""Prepare runtime configuration for the Alexa MA Skill add-on.

Home Assistant writes the user options to ``/data/options.json``. The upstream
application also reloads that file at import time and copies every value into
``os.environ``, so the entrypoint must rewrite the runtime copy with resolved
secret file paths before the application starts.

The script never prints secret values. It writes a NUL-separated list of
``KEY=VALUE`` records so the shell entrypoint can export values safely, even
when a value contains spaces or line breaks.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

DATA_DIR = Path("/data")
USERNAME_FILE = DATA_DIR / "generated_app_username"
PASSWORD_FILE = DATA_DIR / "generated_app_password"
MA_TOKEN_FILE = DATA_DIR / "generated_ma_api_token"

FIXED_PORT = "5000"
DEFAULT_LOCALE = "pt-BR"
DEFAULT_TZ = "America/Sao_Paulo"
DEFAULT_AWS_REGION = "us-east-1"

ALLOWED_LOCALES = (
    "pt-BR",
    "en-US",
    "en-GB",
    "en-AU",
    "en-CA",
    "en-IN",
    "de-DE",
    "es-ES",
    "es-MX",
    "fr-FR",
    "fr-CA",
    "it-IT",
    "nl-NL",
)

RUNTIME_KEYS = (
    "SKILL_HOSTNAME",
    "MA_HOSTNAME",
    "APP_USERNAME",
    "APP_PASSWORD",
    "PORT",
    "LOCALE",
    "TZ",
    "AWS_DEFAULT_REGION",
    "ENABLE_APL",
    "SKIP_URL_VALIDATION",
    "SKILL_ID",
    "MA_API_URL",
    "MA_API_TOKEN",
)


class ConfigError(Exception):
    """A user-facing configuration error that contains no secret values."""


def _as_text(value: object) -> str:
    """Return a stable string for a JSON option value."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    return ""


def _normalise_bool(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return (
        "true"
        if _as_text(value).strip().lower() in {"1", "true", "yes", "on"}
        else "false"
    )


def _read_options(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Could not read {path}: {exc}") from exc
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a JSON object.")
    return data


def _write_atomic(path: Path, content: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        os.chmod(path, mode)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _read_generated(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""
    except OSError as exc:
        raise ConfigError(
            f"Could not read the generated credential file {path}: {exc}"
        ) from exc


def _write_secret(path: Path, value: str) -> None:
    _write_atomic(path, value + "\n", 0o600)


def _remove_generated_secret(path: Path, label: str) -> None:
    """Remove a stale generated secret when explicit credentials are used."""
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except OSError as exc:
        print(
            f"Warning: could not remove the stale generated file for {label} "
            f"at {path}: {exc}",
            file=sys.stderr,
        )
        return
    print(f"Removed stale generated file for {label}: {path}.")


def _same_path(value: str, path: Path) -> bool:
    try:
        return os.path.normpath(value) == os.path.normpath(str(path))
    except (TypeError, ValueError):
        return False


def _resolve_secret(
    options: dict[str, object],
    key: str,
    generated_path: Path,
    generator: Callable[[], str],
    label: str,
    *,
    strip_value: bool,
) -> str:
    """Resolve a required secret, generating and persisting it when absent."""
    raw = _as_text(options.get(key))
    if raw.strip():
        candidate = raw.strip() if strip_value else raw
        if _same_path(candidate, generated_path):
            value = _read_generated(generated_path)
            if value:
                options[key] = str(generated_path)
                return value
            # The managed file is missing or empty; regenerate below.
        else:
            configured_path = Path(candidate)
            try:
                is_file = configured_path.is_file()
            except OSError:
                is_file = False
            if is_file:
                try:
                    value = configured_path.read_text(encoding="utf-8").strip()
                except OSError as exc:
                    raise ConfigError(
                        f"Could not read the file configured for {key}: {exc}"
                    ) from exc
                if value:
                    options[key] = candidate
                    _remove_generated_secret(generated_path, label)
                    return value
                # An empty file is treated as "not configured" and regenerated.
            else:
                options[key] = candidate
                _remove_generated_secret(generated_path, label)
                return candidate

    value = _read_generated(generated_path)
    if not value:
        value = generator()
        _write_secret(generated_path, value)
        print(f"Generated {label} in {generated_path} (mode 600).")
    options[key] = str(generated_path)
    return value


def _resolve_optional_secret(
    options: dict[str, object],
    key: str,
    generated_path: Path,
    label: str,
) -> str:
    """Resolve an optional secret without generating one when it is empty."""
    raw = _as_text(options.get(key)).strip()
    if not raw:
        try:
            generated_path.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            print(
                f"Warning: could not remove the stale {label} file "
                f"{generated_path}: {exc}",
                file=sys.stderr,
            )
        options[key] = ""
        return ""

    if _same_path(raw, generated_path):
        value = _read_generated(generated_path)
        options[key] = str(generated_path) if value else ""
        return value

    configured_path = Path(raw)
    try:
        is_file = configured_path.is_file()
    except OSError:
        is_file = False
    if is_file:
        try:
            value = configured_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ConfigError(
                f"Could not read the file configured for {key}: {exc}"
            ) from exc
        options[key] = raw
        return value

    # Store a raw token in a mode-600 file and pass the path to the upstream
    # app. The upstream logger prints option values for every key except
    # APP_USERNAME/APP_PASSWORD, so a path keeps the token out of the logs.
    _write_secret(generated_path, raw)
    options[key] = str(generated_path)
    print(f"Stored {label} in {generated_path} (mode 600).")
    return raw


def _generate_username() -> str:
    return "alexa_" + secrets.token_hex(6)


def _generate_password() -> str:
    return secrets.token_urlsafe(32)


def _clean_hostname(key: str, value: object, *, required: bool) -> str:
    text = _as_text(value).strip()
    if not text:
        if required:
            raise ConfigError(
                f"{key} is required. Set the public hostname in the add-on "
                "configuration."
            )
        return ""
    if "://" in text:
        raise ConfigError(
            f"{key} must be a bare hostname, without http:// or https://."
        )
    text = text.removesuffix(".")
    if any(character in text for character in "/?#@\\ \t\r\n"):
        raise ConfigError(
            f"{key} must be a bare hostname without paths, ports, query "
            "strings, or spaces."
        )
    if ":" in text:
        raise ConfigError(
            f"{key} must not include a port. Publish the service on HTTPS "
            "port 443 through your tunnel."
        )
    if len(text) > 253:
        raise ConfigError(f"{key} is too long to be a valid hostname.")
    return text


def _validate_port(value: object) -> str:
    text = _as_text(value).strip() or FIXED_PORT
    if not text.isdigit():
        raise ConfigError("PORT must be a number.")
    port = int(text)
    if not 1 <= port <= 65535:
        raise ConfigError("PORT must be between 1 and 65535.")
    if text != FIXED_PORT:
        raise ConfigError(
            f"PORT must be {FIXED_PORT}. The add-on maps 5000/tcp and the "
            "watchdog uses port 5000."
        )
    return text


def _validate_locale(value: object) -> str:
    text = _as_text(value).strip() or DEFAULT_LOCALE
    if text not in ALLOWED_LOCALES:
        raise ConfigError("LOCALE must be one of: " + ", ".join(ALLOWED_LOCALES) + ".")
    return text


def _validate_ma_api_url(value: object) -> str:
    """Validate the optional Music Assistant API URL."""
    text = _as_text(value).strip()
    if not text:
        return ""
    if any(character in text for character in "\r\n\t "):
        raise ConfigError("MA_API_URL must not contain spaces or line breaks.")
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https", "ws", "wss"}:
        raise ConfigError("MA_API_URL must use http://, https://, ws:// or wss://.")
    if not parsed.netloc:
        raise ConfigError("MA_API_URL must include a host and port.")
    if parsed.username or parsed.password:
        raise ConfigError(
            "MA_API_URL must not contain credentials; use MA_API_TOKEN instead."
        )
    return text


def _prepare(options: dict[str, object]) -> dict[str, str]:
    skill_hostname = _clean_hostname(
        "SKILL_HOSTNAME", options.get("SKILL_HOSTNAME"), required=True
    )
    ma_hostname = _clean_hostname(
        "MA_HOSTNAME", options.get("MA_HOSTNAME"), required=False
    )
    port = _validate_port(options.get("PORT"))
    locale = _validate_locale(options.get("LOCALE"))
    timezone = _as_text(options.get("TZ")).strip() or DEFAULT_TZ
    aws_region = (
        _as_text(options.get("AWS_DEFAULT_REGION")).strip() or DEFAULT_AWS_REGION
    )
    enable_apl = _normalise_bool(options.get("ENABLE_APL"))
    skip_url_validation = _normalise_bool(options.get("SKIP_URL_VALIDATION"))
    skill_id = _as_text(options.get("SKILL_ID")).strip()
    ma_api_url = _validate_ma_api_url(options.get("MA_API_URL"))

    _resolve_secret(
        options,
        "APP_USERNAME",
        USERNAME_FILE,
        _generate_username,
        "the add-on username",
        strip_value=True,
    )
    _resolve_secret(
        options,
        "APP_PASSWORD",
        PASSWORD_FILE,
        _generate_password,
        "the add-on password",
        strip_value=False,
    )
    _resolve_optional_secret(
        options,
        "MA_API_TOKEN",
        MA_TOKEN_FILE,
        "the Music Assistant API token",
    )

    runtime: dict[str, str] = {
        "SKILL_HOSTNAME": skill_hostname,
        "MA_HOSTNAME": ma_hostname,
        "APP_USERNAME": _as_text(options.get("APP_USERNAME")),
        "APP_PASSWORD": _as_text(options.get("APP_PASSWORD")),
        "PORT": port,
        "LOCALE": locale,
        "TZ": timezone,
        "AWS_DEFAULT_REGION": aws_region,
        "ENABLE_APL": enable_apl,
        "SKIP_URL_VALIDATION": skip_url_validation,
        "SKILL_ID": skill_id,
        "MA_API_URL": ma_api_url,
        "MA_API_TOKEN": _as_text(options.get("MA_API_TOKEN")),
    }
    return runtime


def _write_options(path: Path, options: dict[str, str]) -> None:
    content = json.dumps(options, ensure_ascii=False, indent=2) + "\n"
    _write_atomic(path, content, 0o600)


def _write_env_export(path: Path, options: dict[str, str]) -> None:
    records = bytearray()
    for key in RUNTIME_KEYS:
        value = options.get(key, "")
        records.extend(f"{key}={value}".encode())
        records.append(0)
    try:
        path.write_bytes(bytes(records))
        os.chmod(path, 0o600)
    except OSError as exc:
        raise ConfigError(
            f"Could not write the environment export file: {exc}"
        ) from exc


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: addon_options.py <options.json> <env-export-file>",
            file=sys.stderr,
        )
        return 2

    options_path = Path(argv[1])
    env_path = Path(argv[2])

    try:
        raw_options = _read_options(options_path)
        runtime_options = _prepare(raw_options)
        _write_options(options_path, runtime_options)
        _write_env_export(env_path, runtime_options)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    print("Configuration ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
