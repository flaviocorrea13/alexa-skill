#!/usr/bin/env python3
"""Validate repository metadata, add-on metadata, docs and safety rules.

The checks are intentionally offline and deterministic so the same script can
run locally and in CI. It depends only on PyYAML.

Exit code 0 means no errors. Warnings are reported but do not fail the run.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/flaviocorrea13/alexa-skill"
ISSUES_URL = f"{REPO_URL}/issues"
DOMAIN = "alexa_ma_skill"
ADDON_DIR = ROOT / "alexa_ma_skill"
INTEGRATION_DIR = ROOT / "custom_components" / DOMAIN
DOCS_DIR = ROOT / "docs"
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    ".ruff_cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
}
TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".sh",
    ".txt",
    ".toml",
    ".ini",
    ".cfg",
}
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?$")
DIGEST_RE = re.compile(r"@sha256:[0-9a-f]{64}$")
SECRET_PATTERNS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
)
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")

errors: list[str] = []
warnings: list[str] = []


def fail(message: str) -> None:
    """Record a blocking error."""
    errors.append(message)


def warn(message: str) -> None:
    """Record a non-blocking warning."""
    warnings.append(message)


def load_yaml(path: Path) -> Any:
    """Load a YAML file, recording a parse error."""
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as err:
        fail(f"{path.relative_to(ROOT)}: invalid YAML ({err})")
        return None


def load_json(path: Path) -> Any:
    """Load a JSON file, recording a parse error."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        fail(f"{path.relative_to(ROOT)}: invalid JSON ({err})")
        return None


def iter_files(suffixes: set[str] | None = None) -> list[Path]:
    """Return repository files, skipping generated and dependency directories."""
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if suffixes is not None and path.suffix.lower() not in suffixes:
            continue
        files.append(path)
    return sorted(files)


def check_repository_yaml() -> dict[str, Any]:
    """Validate repository.yaml and return it parsed."""
    path = ROOT / "repository.yaml"
    data = load_yaml(path)
    if not isinstance(data, dict):
        fail("repository.yaml: expected a mapping")
        return {}
    for key in ("name", "url", "maintainer"):
        if not str(data.get(key) or "").strip():
            fail(f"repository.yaml: missing {key}")
    if data.get("url") != REPO_URL:
        fail(f"repository.yaml: url must be {REPO_URL}")
    return data


def check_addon(config: dict[str, Any], integration_manifest: dict[str, Any]) -> None:
    """Validate the add-on manifest, Dockerfile and translations."""
    required = {
        "name",
        "version",
        "slug",
        "description",
        "url",
        "arch",
        "startup",
        "boot",
        "backup",
        "watchdog",
        "ports",
        "options",
        "schema",
    }
    missing = required - set(config)
    if missing:
        fail(f"addon config.yaml: missing keys {sorted(missing)}")
        return

    version = str(config["version"])
    if not VERSION_RE.match(version):
        fail(f"addon config.yaml: invalid version {version!r}")
    if version != integration_manifest.get("version"):
        fail(
            "version mismatch: add-on "
            f"{version!r} != integration {integration_manifest.get('version')!r}"
        )
    if config["slug"] != DOMAIN:
        fail(f"addon config.yaml: slug must be {DOMAIN!r}")
    if not str(config["description"]).strip():
        fail("addon config.yaml: empty description")
    if config.get("url") != REPO_URL:
        fail(f"addon config.yaml: url must be {REPO_URL}")

    arch = config.get("arch")
    allowed_arch = {"amd64", "aarch64", "armv7", "armhf", "i386"}
    if not isinstance(arch, list) or not arch:
        fail("addon config.yaml: arch must be a non-empty list")
    else:
        unknown = set(arch) - allowed_arch
        if unknown:
            fail(f"addon config.yaml: unsupported arch {sorted(unknown)}")

    ports = config.get("ports") or {}
    if not isinstance(ports, dict) or "5000/tcp" not in ports:
        fail("addon config.yaml: ports must map 5000/tcp")
    elif str(ports["5000/tcp"]) != "5000":
        fail("addon config.yaml: 5000/tcp must map to 5000")

    options = config.get("options") or {}
    schema = config.get("schema") or {}
    if not isinstance(options, dict) or not isinstance(schema, dict):
        fail("addon config.yaml: options and schema must be mappings")
        return
    unknown = set(options) - set(schema)
    if unknown:
        fail(f"addon config.yaml: option defaults without schema {sorted(unknown)}")
    if schema.get("SKILL_HOSTNAME") != "str":
        fail("addon config.yaml: SKILL_HOSTNAME must be required (str)")
    for key in ("PORT", "LOCALE", "TZ", "AWS_DEFAULT_REGION"):
        if key not in schema:
            fail(f"addon config.yaml: schema missing {key}")
    if "list(5000)" != schema.get("PORT"):
        fail("addon config.yaml: PORT must be list(5000)")

    if "image" in config:
        image = str(config["image"])
        if ":latest" in image or not DIGEST_RE.search(image):
            fail("addon config.yaml: image must be pinned by tag and digest")

    if config.get("backup") not in {"cold", "hot"}:
        fail("addon config.yaml: backup must be cold or hot")
    if not str(config.get("watchdog", "")).startswith("tcp://"):
        fail("addon config.yaml: watchdog must use tcp://")
    if "/setup" not in str(config.get("webui", "")):
        fail("addon config.yaml: webui must point to /setup")

    check_dockerfile(version)

    for locale in ("en", "pt-BR"):
        path = ADDON_DIR / "translations" / f"{locale}.yaml"
        if not path.is_file():
            fail(f"missing add-on translation {path.relative_to(ROOT)}")
            continue
        data = load_yaml(path)
        if not isinstance(data, dict):
            continue
        configuration = data.get("configuration")
        if not isinstance(configuration, dict):
            fail(f"{path.name}: missing configuration section")
            continue
        missing_keys = set(schema) - set(configuration)
        if missing_keys:
            fail(f"{path.name}: missing configuration keys {sorted(missing_keys)}")
        for key, value in configuration.items():
            if not isinstance(value, dict) or not str(value.get("name") or "").strip():
                fail(f"{path.name}: configuration.{key} needs a name")
        if "5000/tcp" not in (data.get("network") or {}):
            fail(f"{path.name}: missing network.5000/tcp")


def check_dockerfile(version: str) -> None:
    """Validate the add-on Dockerfile build contract."""
    path = ADDON_DIR / "Dockerfile"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        fail(f"Dockerfile: cannot read ({err})")
        return

    from_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip().upper().startswith("FROM ")
    ]
    if len(from_lines) != 1:
        fail("Dockerfile: expected exactly one FROM line")
        return
    image = from_lines[0].split(maxsplit=1)[1].split()[0]
    if ":latest" in image:
        fail("Dockerfile: must not use :latest")
    if not DIGEST_RE.search(image):
        fail("Dockerfile: FROM must be pinned with @sha256 digest")
    if "ENTRYPOINT" not in text or "CMD" not in text:
        fail("Dockerfile: ENTRYPOINT and CMD are required")
    if "COPY run.sh /run.sh" not in text:
        fail("Dockerfile: must copy run.sh")
    if "COPY addon_options.py" not in text:
        fail("Dockerfile: must copy addon_options.py")
    if f"ALEXA_MA_SKILL_VERSION={version}" in text:
        warn("Dockerfile: unexpected version build arg")


def check_integration() -> dict[str, Any]:
    """Validate the custom component layout, manifest and translations."""
    manifest_path = INTEGRATION_DIR / "manifest.json"
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        fail("integration manifest.json must contain an object")
        return {}
    keys = list(manifest)
    if keys[:2] != ["domain", "name"] or keys[2:] != sorted(keys[2:]):
        fail(
            "integration manifest.json: keys must be domain, name, then "
            "alphabetical order (Hassfest)"
        )
    required = {
        "domain",
        "name",
        "codeowners",
        "config_flow",
        "documentation",
        "integration_type",
        "iot_class",
        "issue_tracker",
        "version",
    }
    missing = required - set(manifest)
    if missing:
        fail(f"integration manifest.json: missing keys {sorted(missing)}")
    if manifest.get("domain") != DOMAIN:
        fail(f"integration manifest.json: domain must be {DOMAIN!r}")
    if manifest.get("documentation") != REPO_URL:
        fail(f"integration manifest.json: documentation must be {REPO_URL}")
    if manifest.get("issue_tracker") != ISSUES_URL:
        fail(f"integration manifest.json: issue_tracker must be {ISSUES_URL}")
    if not VERSION_RE.match(str(manifest.get("version", ""))):
        fail("integration manifest.json: invalid version")
    codeowners = manifest.get("codeowners")
    if not isinstance(codeowners, list) or not all(
        str(owner).startswith("@") for owner in codeowners
    ):
        fail("integration manifest.json: codeowners must be GitHub handles")

    if not (INTEGRATION_DIR / "config_flow.py").is_file():
        fail("integration: config_flow.py is missing")
    if not (INTEGRATION_DIR / "strings.json").is_file():
        fail("integration: strings.json is missing")

    strings_path = INTEGRATION_DIR / "strings.json"
    en_path = INTEGRATION_DIR / "translations" / "en.json"
    pt_path = INTEGRATION_DIR / "translations" / "pt-BR.json"
    strings = load_json(strings_path)
    en = load_json(en_path)
    pt = load_json(pt_path)
    if not all(isinstance(item, dict) for item in (strings, en, pt)):
        return {}
    if strings != en:
        fail("strings.json and translations/en.json differ")
    if key_structure(strings) != key_structure(pt):
        fail("translations/pt-BR.json structure differs from strings.json")

    check_entity_translations(strings)
    check_translation_values(strings)
    check_config_flow_translations(strings)

    for section in ("config", "options"):
        block = strings.get(section)
        if not isinstance(block, dict) or "step" not in block:
            fail(f"strings.json: missing {section}.step")
    return manifest


def check_config_flow_translations(strings: dict[str, Any]) -> None:
    """Cross-check step ids and menu options used by the config flow."""
    path = INTEGRATION_DIR / "config_flow.py"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    config_steps = (strings.get("config") or {}).get("step") or {}
    options_steps = (strings.get("options") or {}).get("step") or {}
    known_steps = set(config_steps) | set(options_steps)

    used_steps = set(re.findall(r'step_id="([a-z0-9_]+)"', text))
    missing_steps = used_steps - known_steps
    if missing_steps:
        fail(f"strings.json: missing flow steps {sorted(missing_steps)}")

    for block in re.findall(r"async_show_menu\((.*?)\)", text, re.DOTALL):
        menu = re.search(r"menu_options=\[([^\]]*)\]", block)
        if not menu:
            continue
        step_id = re.search(r'step_id="([a-z0-9_]+)"', block)
        if not step_id:
            continue
        names = re.findall(r'"([a-z0-9_]+)"', menu.group(1))
        for section in (config_steps, options_steps):
            definition = section.get(step_id.group(1))
            if isinstance(definition, dict) and "menu_options" in definition:
                translated = set(definition["menu_options"])
                missing = set(names) - translated
                if missing:
                    fail(
                        "strings.json: "
                        f"{step_id.group(1)} menu_options missing {sorted(missing)}"
                    )
                break
        else:
            fail(f"strings.json: no menu translation for step {step_id.group(1)!r}")
        missing_targets = set(names) - known_steps
        if missing_targets:
            fail(f"strings.json: menu targets are not steps {sorted(missing_targets)}")


def key_structure(value: Any) -> Any:
    """Return nested keys without values."""
    if isinstance(value, dict):
        return {key: key_structure(sub) for key, sub in value.items()}
    return None


def check_entity_translations(strings: dict[str, Any]) -> None:
    """Ensure entity translation keys used in code exist in strings.json."""
    entity = strings.get("entity") or {}
    for filename, platform in (
        ("sensor.py", "sensor"),
        ("binary_sensor.py", "binary_sensor"),
    ):
        path = INTEGRATION_DIR / filename
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        keys = set(re.findall(r'translation_key="([a-z0-9_]+)"', text))
        keys.update(re.findall(r'_attr_translation_key = "([a-z0-9_]+)"', text))
        available = entity.get(platform) or {}
        missing = keys - set(available)
        if missing:
            fail(f"strings.json: entity.{platform} missing {sorted(missing)}")


def check_translation_values(strings: dict[str, Any]) -> None:
    """Mirror the Hassfest rules that most often break custom integrations."""
    url_re = re.compile(r"https?://|www\.", re.IGNORECASE)
    html_re = re.compile(r"<[a-zA-Z/][^>]*>")
    quoted_placeholder_re = re.compile(r"'{\w+}'")
    placeholder_re = re.compile(r"{(.*?)}")

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, sub in value.items():
                walk(sub, f"{path}/{key}")
            return
        if not isinstance(value, str):
            return
        if url_re.search(value):
            fail(f"strings.json: URL not allowed in {path}")
        if html_re.search(value):
            fail(f"strings.json: HTML not allowed in {path}")
        if quoted_placeholder_re.search(value):
            fail(f"strings.json: quoted placeholder in {path}")
        for match in placeholder_re.finditer(value):
            name = match.group(1)
            if name and not name.isidentifier():
                fail(f"strings.json: invalid placeholder {name!r} in {path}")
        if value != value.strip():
            fail(f"strings.json: leading/trailing space in {path}")

    walk(strings, "")


def check_hacs() -> None:
    """Validate hacs.json metadata."""
    path = ROOT / "hacs.json"
    data = load_json(path)
    if not isinstance(data, dict):
        fail("hacs.json must contain an object")
        return
    allowed = {
        "content_in_root",
        "country",
        "filename",
        "hacs",
        "hide_default_branch",
        "homeassistant",
        "persistent_directory",
        "render_readme",
        "zip_release",
        "name",
    }
    unknown = set(data) - allowed
    if unknown:
        fail(f"hacs.json: unknown keys rejected by HACS {sorted(unknown)}")
    for key in ("name", "homeassistant"):
        if not str(data.get(key) or "").strip():
            fail(f"hacs.json: missing {key}")
    if not VERSION_RE.match(str(data.get("homeassistant", ""))):
        fail("hacs.json: homeassistant must be a version string")
    if "render_readme" in data and not isinstance(data["render_readme"], bool):
        fail("hacs.json: render_readme must be a boolean")

    components = [
        path
        for path in (ROOT / "custom_components").iterdir()
        if path.is_dir() and not path.name.startswith("__")
    ]
    if len(components) != 1:
        fail("HACS requires exactly one directory under custom_components/")
    elif components[0].name != DOMAIN:
        fail(f"custom_components directory must be {DOMAIN}")


def check_versions(config: dict[str, Any], manifest: dict[str, Any]) -> None:
    """Check version consistency with the changelog."""
    changelog = ADDON_DIR / "CHANGELOG.md"
    try:
        text = changelog.read_text(encoding="utf-8")
    except OSError as err:
        fail(f"CHANGELOG.md: cannot read ({err})")
        return
    version = str(config.get("version") or "")
    if (
        version
        and re.search(rf"^##\s+{re.escape(version)}\b", text, re.MULTILINE) is None
    ):
        fail(f"CHANGELOG.md: no section for version {version}")
    if version != manifest.get("version"):
        fail("CHANGELOG.md: integration/add-on versions are inconsistent")


def check_parsing() -> None:
    """Parse every YAML and JSON file in the repository."""
    for path in iter_files({".yaml", ".yml"}):
        load_yaml(path)
    for path in iter_files({".json"}):
        load_json(path)


def check_line_endings() -> None:
    """Fail on CRLF in text files."""
    for path in iter_files(TEXT_SUFFIXES):
        try:
            data = path.read_bytes()
        except OSError as err:
            fail(f"{path.relative_to(ROOT)}: cannot read ({err})")
            continue
        if b"\r\n" in data:
            fail(f"{path.relative_to(ROOT)}: CRLF line endings found")
        if data.startswith(b"\xef\xbb\xbf"):
            fail(f"{path.relative_to(ROOT)}: UTF-8 BOM found")


def check_secrets() -> None:
    """Look for common credential patterns in text files."""
    for path in iter_files(TEXT_SUFFIXES):
        if path.stat().st_size > 1_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                fail(
                    f"{path.relative_to(ROOT)}: possible secret "
                    f"({match.group(0)[:12]}...)"
                )


def check_markdown_links() -> None:
    """Validate relative links in the main docs."""
    for name in ("README.md", "AGENTS.md", "alexa_ma_skill/DOCS.md"):
        path = ROOT / name
        if not path.is_file():
            fail(f"missing {name}")
            continue
        text = path.read_text(encoding="utf-8")
        for target in LINK_RE.findall(text):
            target = target.strip()
            if (
                target.startswith(("http://", "https://", "mailto:", "#"))
                or "{" in target
                or "<" in target
            ):
                continue
            relative = target.split("#", 1)[0]
            if not relative:
                continue
            if not (path.parent / relative).resolve().exists():
                fail(f"{name}: broken relative link {target}")


def check_readme_sections() -> None:
    """Require the public README sections."""
    path = ROOT / "README.md"
    if not path.is_file():
        fail("README.md is missing")
        return
    text = path.read_text(encoding="utf-8")
    for heading in (
        "## Instalação",
        "## Segurança",
        "## Solução de problemas",
        "## Suporte",
        "## Licença",
    ):
        if heading not in text:
            fail(f"README.md: missing section {heading!r}")
    if REPO_URL not in text:
        fail("README.md: must reference the repository URL")


def check_distribution_docs() -> None:
    """Check that the distribution documents exist."""
    required = (
        "docs/DISTRIBUTION-READINESS.md",
        "docs/VALIDATION-MATRIX.md",
        "docs/HAOS-TEST-PLAN.md",
        "docs/releases/RELEASE-DRAFT.md",
        "docs/images/README.md",
        ".github/workflows/ci.yml",
    )
    for name in required:
        if not (ROOT / name).is_file():
            fail(f"missing distribution file {name}")


def check_workflows() -> None:
    """Validate the CI workflow contract."""
    path = ROOT / ".github" / "workflows" / "ci.yml"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    if "permissions:" not in text or "contents: read" not in text:
        fail("ci.yml: workflow must declare minimal read permissions")
    for forbidden in ("docker push", "gh release", "twine upload"):
        if forbidden in text:
            fail(f"ci.yml: forbidden publishing command {forbidden!r}")
    if ":latest" in text:
        fail("ci.yml: must not reference :latest images")
    for required in ("hassfest", "pytest", "ruff", "validate_repo.py"):
        if required not in text:
            fail(f"ci.yml: missing {required}")

    for reference in re.findall(r"uses:\s*([^\s#]+)", text):
        if "@" not in reference:
            fail(f"ci.yml: action without ref {reference!r}")
            continue
        pinned = reference.rsplit("@", 1)[1]
        if re.fullmatch(r"[0-9a-f]{40}", pinned) is None:
            fail(f"ci.yml: action not pinned to a commit SHA ({reference!r})")

    if re.search(r"ignore:\s*[^\n,]*,[^\n]*", text):
        fail("ci.yml: HACS ignore list must be space-separated")
    if 'comment: "false"' not in text:
        fail("ci.yml: HACS action must not post comments with a read-only token")
    if not (ROOT / ".github" / "dependabot.yml").is_file():
        warn("ci.yml: pinned actions without .github/dependabot.yml")


def check_hacs_brand_assets() -> None:
    """Warn about the brand asset required for the HACS default catalog."""
    brand_icon = INTEGRATION_DIR / "brand" / "icon.png"
    if not brand_icon.is_file():
        warn(
            "integration: no brand/icon.png; HACS default-catalog inclusion "
            "requires brand assets (custom repository installation still works)"
        )


def check_docs_dir() -> None:
    """Warn when the distribution docs directory is empty of images."""
    images = sorted((DOCS_DIR / "images").glob("*.png")) if DOCS_DIR.is_dir() else []
    if not images:
        warn("docs/images: no real screenshots committed (documented as pending)")


def main() -> int:
    """Run all checks."""
    if not INTEGRATION_DIR.is_dir():
        fail(f"missing integration directory {INTEGRATION_DIR}")
    repository = check_repository_yaml()
    manifest = check_integration()
    config_path = ADDON_DIR / "config.yaml"
    config = load_yaml(config_path)
    if not isinstance(config, dict):
        fail("addon config.yaml must contain a mapping")
        config = {}
    if config and manifest:
        check_addon(config, manifest)
        check_versions(config, manifest)
    if (
        repository
        and manifest
        and repository.get("url") != manifest.get("documentation")
    ):
        fail("repository.yaml url differs from integration documentation")
    check_hacs()
    check_parsing()
    check_line_endings()
    check_secrets()
    check_markdown_links()
    check_readme_sections()
    check_distribution_docs()
    check_workflows()
    check_hacs_brand_assets()
    check_docs_dir()

    for message in warnings:
        print(f"WARNING: {message}")
    for message in errors:
        print(f"ERROR: {message}")
    if errors:
        print(f"\n{len(errors)} error(s) found.")
        return 1
    print(f"Repository validation passed ({len(warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
