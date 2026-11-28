#!/usr/bin/env python3
"""Run selected official Hassfest plugins against this integration.

This is a local diagnostic helper, **not** a replacement for the official
Hassfest GitHub Action (``ghcr.io/home-assistant/hassfest``). It exists because
some development machines have no Docker/Linux environment.

Requirements:

- a checkout of the Home Assistant Core tag that matches the installed
  ``homeassistant`` package (for example ``2026.10.4``);
- the project virtualenv with Home Assistant installed.

Example::

    python scripts/run_hassfest_subset.py --core-path /path/to/core

The ``dependencies`` plugin is not included because it needs a full Core
checkout; the official action runs it in CI.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

DEFAULT_PLUGINS = (
    "json,manifest,translations,services,icons,integration_type,"
    "config_schema,codeowners,requirements,config_flow"
)


def main() -> int:
    """Run the selected plugins and return a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--core-path",
        required=True,
        type=Path,
        help="Path to the Home Assistant Core checkout",
    )
    parser.add_argument(
        "--integration-path",
        type=Path,
        default=Path("custom_components/alexa_ma_skill"),
        help="Path to the integration directory",
    )
    parser.add_argument(
        "--plugins",
        default=DEFAULT_PLUGINS,
        help="Comma-separated Hassfest plugin names",
    )
    args = parser.parse_args()

    core = args.core_path.resolve()
    integration_path = args.integration_path.resolve()
    if not (core / "script" / "hassfest").is_dir():
        print(f"not a Home Assistant Core checkout: {core}", file=sys.stderr)
        return 2
    if not (integration_path / "manifest.json").is_file():
        print(f"not an integration directory: {integration_path}", file=sys.stderr)
        return 2

    sys.path.insert(0, str(core))
    try:
        from script.hassfest.model import Config, Integration
    except ImportError as err:
        print(
            "cannot import the Hassfest package; install the Home Assistant "
            f"version that matches the checkout: {err}",
            file=sys.stderr,
        )
        return 2

    config = Config(
        root=core,
        specific_integrations=[integration_path],
        action="validate",
        requirements=False,
    )
    integration = Integration(integration_path, config)
    integration.load_manifest()
    integrations = {integration.domain: integration}

    for name in (item.strip() for item in args.plugins.split(",") if item.strip()):
        print(f"Validating {name}...", flush=True)
        try:
            module = importlib.import_module(f"script.hassfest.{name}")
        except Exception as err:  # noqa: BLE001 - report and continue
            print(f"  SKIP: {type(err).__name__}: {err}", flush=True)
            continue
        module.validate(integrations, config)

    errors = list(config.errors)
    for item in integrations.values():
        errors.extend(item.errors)
        for warning in item.warnings:
            print(f"WARNING: {warning}")

    print(f"Integrations: {len(integrations)}")
    print(f"Errors: {len(errors)}")
    for error in errors:
        print(f"ERROR: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
