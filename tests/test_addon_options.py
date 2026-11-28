"""Tests for the add-on option preparation script.

These tests use only the Python standard library and do not require Home
Assistant, Docker or a running add-on. POSIX permission assertions are skipped
on non-POSIX platforms.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "alexa_ma_skill" / "addon_options.py"

spec = importlib.util.spec_from_file_location("addon_options", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load {MODULE_PATH}")
addon_options = importlib.util.module_from_spec(spec)
spec.loader.exec_module(addon_options)


def base_options() -> dict[str, object]:
    """Return valid default options for the tests."""
    return {
        "SKILL_HOSTNAME": "skill.example.com",
        "MA_HOSTNAME": "ma.example.com",
        "APP_USERNAME": "",
        "APP_PASSWORD": "",
        "PORT": "5000",
        "LOCALE": "pt-BR",
        "TZ": "America/Sao_Paulo",
        "AWS_DEFAULT_REGION": "us-east-1",
        "ENABLE_APL": False,
        "SKIP_URL_VALIDATION": False,
        "SKILL_ID": "",
        "MA_API_URL": "",
        "MA_API_TOKEN": "",
    }


class AddonOptionsTest(unittest.TestCase):
    """Exercise credential generation, persistence and validation."""

    def setUp(self) -> None:
        """Create isolated secret paths for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.original_paths = (
            addon_options.USERNAME_FILE,
            addon_options.PASSWORD_FILE,
            addon_options.MA_TOKEN_FILE,
        )
        addon_options.USERNAME_FILE = self.root / "generated_app_username"
        addon_options.PASSWORD_FILE = self.root / "generated_app_password"
        addon_options.MA_TOKEN_FILE = self.root / "generated_ma_api_token"

    def tearDown(self) -> None:
        """Restore module paths and remove temporary files."""
        (
            addon_options.USERNAME_FILE,
            addon_options.PASSWORD_FILE,
            addon_options.MA_TOKEN_FILE,
        ) = self.original_paths
        self.temp_dir.cleanup()

    def test_generates_and_reuses_credentials(self) -> None:
        """Generated credentials are stable across a simulated restart."""
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            runtime = addon_options._prepare(base_options())

        username = addon_options.USERNAME_FILE.read_text(encoding="utf-8").strip()
        password = addon_options.PASSWORD_FILE.read_text(encoding="utf-8").strip()
        self.assertTrue(username.startswith("alexa_"))
        self.assertGreaterEqual(len(password), 32)
        self.assertEqual(runtime["APP_USERNAME"], str(addon_options.USERNAME_FILE))
        self.assertEqual(runtime["APP_PASSWORD"], str(addon_options.PASSWORD_FILE))
        self.assertNotIn(password, output.getvalue())

        options_path = self.root / "options.json"
        addon_options._write_options(options_path, runtime)
        written = json.loads(options_path.read_text(encoding="utf-8"))
        self.assertEqual(written["APP_USERNAME"], str(addon_options.USERNAME_FILE))
        self.assertEqual(written["APP_PASSWORD"], str(addon_options.PASSWORD_FILE))
        self.assertNotIn(password, options_path.read_text(encoding="utf-8"))

        reused = addon_options._prepare(dict(written))
        self.assertEqual(reused["APP_USERNAME"], str(addon_options.USERNAME_FILE))
        self.assertEqual(reused["APP_PASSWORD"], str(addon_options.PASSWORD_FILE))
        self.assertEqual(
            addon_options.USERNAME_FILE.read_text(encoding="utf-8").strip(), username
        )
        self.assertEqual(
            addon_options.PASSWORD_FILE.read_text(encoding="utf-8").strip(), password
        )

    @unittest.skipUnless(os.name == "posix", "POSIX permissions only")
    def test_secret_files_are_mode_600(self) -> None:
        """Generated credential and env files are not world-readable."""
        runtime = addon_options._prepare(base_options())
        env_path = self.root / "env.bin"
        addon_options._write_env_export(env_path, runtime)
        for path in (
            addon_options.USERNAME_FILE,
            addon_options.PASSWORD_FILE,
            env_path,
        ):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_explicit_credentials_are_preserved(self) -> None:
        """Explicit panel credentials are used instead of generated ones."""
        options = base_options()
        options["APP_USERNAME"] = "myuser"
        options["APP_PASSWORD"] = "my password with spaces"
        runtime = addon_options._prepare(options)
        self.assertEqual(runtime["APP_USERNAME"], "myuser")
        self.assertEqual(runtime["APP_PASSWORD"], "my password with spaces")

    def test_explicit_credentials_remove_stale_generated_files(self) -> None:
        """Switching to explicit credentials does not leave stale secrets."""
        addon_options._prepare(base_options())
        old_username = addon_options.USERNAME_FILE.read_text(encoding="utf-8").strip()
        old_password = addon_options.PASSWORD_FILE.read_text(encoding="utf-8").strip()

        explicit = base_options()
        explicit["APP_USERNAME"] = "myuser"
        explicit["APP_PASSWORD"] = "my password"
        addon_options._prepare(explicit)
        self.assertFalse(addon_options.USERNAME_FILE.exists())
        self.assertFalse(addon_options.PASSWORD_FILE.exists())

        regenerated = addon_options._prepare(base_options())
        new_username = addon_options.USERNAME_FILE.read_text(encoding="utf-8").strip()
        new_password = addon_options.PASSWORD_FILE.read_text(encoding="utf-8").strip()
        self.assertNotEqual(new_username, old_username)
        self.assertNotEqual(new_password, old_password)
        self.assertEqual(regenerated["APP_USERNAME"], str(addon_options.USERNAME_FILE))

    def test_missing_options_file_is_treated_as_empty(self) -> None:
        """A missing options file is treated as an empty configuration."""
        options = addon_options._read_options(self.root / "missing.json")
        self.assertEqual(options, {})
        with self.assertRaises(addon_options.ConfigError):
            addon_options._prepare(options)

    def test_invalid_options_json_is_rejected(self) -> None:
        """Invalid JSON is reported as a configuration error."""
        path = self.root / "options.json"
        path.write_text("{not-json", encoding="utf-8")
        with self.assertRaises(addon_options.ConfigError):
            addon_options._read_options(path)

    def test_env_export_handles_spaces_and_newlines(self) -> None:
        """The NUL-separated export preserves spaces and newlines."""
        options = base_options()
        options["APP_PASSWORD"] = "line one\nline two with spaces"
        runtime = addon_options._prepare(options)
        env_path = self.root / "env.bin"
        addon_options._write_env_export(env_path, runtime)
        records = [record for record in env_path.read_bytes().split(b"\0") if record]
        env = dict(record.decode("utf-8").split("=", 1) for record in records)
        self.assertEqual(env["APP_PASSWORD"], "line one\nline two with spaces")

    def test_ma_api_url_validation(self) -> None:
        """MA API URL accepts HTTP(S)/WS(S) and rejects credentials."""
        for valid in (
            "http://192.0.2.10:8095",
            "https://ma.example.com:8095/",
            "ws://192.0.2.10:8095",
            "wss://ma.example.com:8095/ws",
        ):
            with self.subTest(valid=valid):
                options = base_options()
                options["MA_API_URL"] = valid
                self.assertEqual(addon_options._prepare(options)["MA_API_URL"], valid)

        for invalid in (
            "ftp://192.0.2.10:8095",
            "192.0.2.10:8095",
            "http://user:pass@192.0.2.10:8095",
            "http://192.0.2.10:8095 with space",
        ):
            with (
                self.subTest(invalid=invalid),
                self.assertRaises(addon_options.ConfigError),
            ):
                options = base_options()
                options["MA_API_URL"] = invalid
                addon_options._prepare(options)

    def test_ma_token_is_stored_in_file(self) -> None:
        """A raw MA token is replaced by a mode-600 file path."""
        options = base_options()
        options["MA_API_URL"] = "http://192.0.2.10:8095"
        options["MA_API_TOKEN"] = "secret-token-value"
        runtime = addon_options._prepare(options)
        self.assertEqual(runtime["MA_API_TOKEN"], str(addon_options.MA_TOKEN_FILE))
        self.assertEqual(
            addon_options.MA_TOKEN_FILE.read_text(encoding="utf-8").strip(),
            "secret-token-value",
        )
        options_path = self.root / "options.json"
        addon_options._write_options(options_path, runtime)
        self.assertNotIn("secret-token-value", options_path.read_text(encoding="utf-8"))

    def test_clearing_ma_token_removes_generated_file(self) -> None:
        """Clearing the MA token removes stale generated data."""
        options = base_options()
        options["MA_API_URL"] = "http://192.0.2.10:8095"
        options["MA_API_TOKEN"] = "secret-token-value"
        addon_options._prepare(options)
        cleared = addon_options._prepare(base_options())
        self.assertEqual(cleared["MA_API_TOKEN"], "")
        self.assertFalse(addon_options.MA_TOKEN_FILE.exists())

    def test_empty_ma_hostname_is_accepted(self) -> None:
        """MA_HOSTNAME is optional in the schema."""
        options = base_options()
        options["MA_HOSTNAME"] = ""
        self.assertEqual(addon_options._prepare(options)["MA_HOSTNAME"], "")

    def test_invalid_hostnames_are_rejected(self) -> None:
        """Schemes, paths, ports and spaces are rejected."""
        for bad in (
            "https://skill.example.com",
            "skill.example.com/setup",
            "skill.example.com:5000",
            "skill example.com",
        ):
            with self.subTest(bad=bad), self.assertRaises(addon_options.ConfigError):
                options = base_options()
                options["SKILL_HOSTNAME"] = bad
                addon_options._prepare(options)

    def test_missing_skill_hostname_is_rejected(self) -> None:
        """SKILL_HOSTNAME is required."""
        options = base_options()
        options["SKILL_HOSTNAME"] = ""
        with self.assertRaises(addon_options.ConfigError):
            addon_options._prepare(options)

    def test_invalid_port_and_locale_are_rejected(self) -> None:
        """Only port 5000 and supported locales are accepted."""
        for key, value in (("PORT", "5001"), ("LOCALE", "xx-XX")):
            with self.subTest(key=key), self.assertRaises(addon_options.ConfigError):
                options = base_options()
                options[key] = value
                addon_options._prepare(options)

    def test_trailing_dot_is_removed(self) -> None:
        """A trailing dot is normalized for bare hostnames."""
        self.assertEqual(
            addon_options._clean_hostname(
                "SKILL_HOSTNAME", "skill.example.com.", required=True
            ),
            "skill.example.com",
        )

    def test_boolean_normalization(self) -> None:
        """Common boolean representations are normalized."""
        self.assertEqual(addon_options._normalise_bool(True), "true")
        self.assertEqual(addon_options._normalise_bool("yes"), "true")
        self.assertEqual(addon_options._normalise_bool("0"), "false")


if __name__ == "__main__":
    unittest.main()
