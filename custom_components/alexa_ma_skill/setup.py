"""Setup checklist and Amazon console values for Alexa MA Skill."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse

from homeassistant.helpers.storage import Store

from .const import (
    CONF_LOCALE,
    CONF_MA_API_URL,
    CONF_MA_HOSTNAME,
    CONF_MANAGED,
    CONF_SKILL_HOSTNAME,
    CONF_SKILL_ID,
    DEFAULT_LOCALE,
    INVOCATION_NAME,
    INVOCATION_SOURCE,
)
from .coordinator import AlexaMaSkillData
from .util import html_to_text

_LOGGER = logging.getLogger(__name__)

SKILL_NAME = "Music Assistant"
AMAZON_CONSOLE_URL = "https://developer.amazon.com/alexa/console/ask"
SSL_CERTIFICATE_TYPE = "Wildcard"


class StepStatus(StrEnum):
    """State of one setup step."""

    NOT_STARTED = "not_started"
    PENDING = "pending"
    CHECKING = "checking"
    DONE = "done"
    ATTENTION = "attention"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class StepMode(StrEnum):
    """Whether a step is automatic or requires the user."""

    AUTO = "auto"
    MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class StepDefinition:
    """Stable definition of one checklist step."""

    id: str
    mode: StepMode
    dependencies: tuple[str, ...] = ()
    optional: bool = False


STEP_DEFINITIONS: tuple[StepDefinition, ...] = (
    StepDefinition("addon_installed", StepMode.AUTO),
    StepDefinition("addon_started", StepMode.AUTO, ("addon_installed",)),
    StepDefinition("panel_credentials", StepMode.AUTO, ("addon_started",)),
    StepDefinition("skill_hostname", StepMode.AUTO),
    StepDefinition("ma_hostname", StepMode.AUTO, optional=True),
    StepDefinition("local_setup", StepMode.MANUAL, ("addon_started",)),
    StepDefinition("amazon_auth", StepMode.MANUAL, ("local_setup",)),
    StepDefinition("skill_created", StepMode.MANUAL, ("amazon_auth",)),
    StepDefinition("skill_id_obtained", StepMode.AUTO, ("skill_created",)),
    StepDefinition("skill_id_configured", StepMode.AUTO, ("skill_id_obtained",)),
    StepDefinition("skill_enabled", StepMode.MANUAL, ("skill_created",)),
    StepDefinition("provider_configured", StepMode.MANUAL, ("skill_created",)),
    StepDefinition("ma_api_tested", StepMode.MANUAL, ("provider_configured",)),
    StepDefinition(
        "stream_public", StepMode.AUTO, ("ma_hostname", "provider_configured")
    ),
    StepDefinition("playback_tested", StepMode.MANUAL, ("stream_public",)),
    StepDefinition("commands_tested", StepMode.MANUAL, ("ma_api_tested",)),
)

_STEP_TEXTS: dict[str, dict[str, dict[str, str]]] = {
    "pt": {
        "addon_installed": {
            "title": "Add-on instalado",
            "description": "O add-on Alexa MA Skill precisa existir no Supervisor.",
            "fix": "Adicione o repositório na loja de add-ons e instale o add-on.",
        },
        "addon_started": {
            "title": "Add-on iniciado",
            "description": "O add-on precisa estar em execução e responder ao serviço interno.",
            "fix": "Inicie o add-on no painel e verifique os logs.",
        },
        "panel_credentials": {
            "title": "Credenciais do painel",
            "description": "A integração precisa autenticar em /status e /setup.",
            "fix": "Defina APP_USERNAME e APP_PASSWORD nas opções do add-on e reinicie.",
        },
        "skill_hostname": {
            "title": "Hostname público da skill",
            "description": "Este endereço será usado pela Alexa para chamar a skill.",
            "fix": "Preencha um hostname puro, como skill.exemplo.com.",
        },
        "ma_hostname": {
            "title": "Hostname do stream",
            "description": "Endereço público usado para o áudio do Music Assistant.",
            "fix": "Preencha o hostname do stream ou aceite as limitações de áudio.",
        },
        "local_setup": {
            "title": "Acesso local ao setup",
            "description": "Abra o painel local do add-on e conclua o setup.",
            "fix": "Acesse http://<IP_DO_HA>:5000/setup na rede local.",
        },
        "amazon_auth": {
            "title": "Autorização Amazon",
            "description": "O login e a autorização da Amazon são manuais.",
            "fix": "Use a conta correta e conclua a autorização no painel do setup.",
        },
        "skill_created": {
            "title": "Skill criada ou reutilizada",
            "description": "O script procura skills chamadas 'Music Assistant'.",
            "fix": "Confira as skills existentes e confirme que aceita o comportamento.",
        },
        "skill_id_obtained": {
            "title": "Skill ID obtido",
            "description": "O ID aparece nos logs do setup como 'Done. Skill ID:'.",
            "fix": "Copie o valor amzn1.ask.skill... exibido no painel.",
        },
        "skill_id_configured": {
            "title": "Skill ID configurado",
            "description": "O add-on deve usar o ID da skill que chama o endpoint.",
            "fix": "Preencha SKILL_ID nas opções e reinicie o add-on.",
        },
        "skill_enabled": {
            "title": "Skill habilitada na Alexa",
            "description": "A skill precisa estar habilitada na conta Alexa correta.",
            "fix": "Abra Skills > Suas Skills > Dev e habilite a skill.",
        },
        "provider_configured": {
            "title": "Provider Alexa no Music Assistant",
            "description": "O MA precisa enviar o stream para o add-on.",
            "fix": "Use a URL interna, Basic Auth do painel e o domínio Amazon correto.",
        },
        "ma_api_tested": {
            "title": "API do Music Assistant testada",
            "description": "A API WebSocket na porta 8095 deve responder.",
            "fix": "Preencha MA_API_URL e o token quando a API exigir autenticação.",
        },
        "stream_public": {
            "title": "Stream público validado",
            "description": "O hostname do stream deve responder por HTTPS.",
            "fix": "Verifique DNS, certificado e a rota do stream no túnel.",
        },
        "playback_tested": {
            "title": "Reprodução testada",
            "description": "O áudio deve tocar em um Echo real.",
            "fix": "Inicie a reprodução no Music Assistant e confirme no Echo.",
        },
        "commands_tested": {
            "title": "Comandos testados",
            "description": "Teste próximo, anterior e pausa pela Alexa.",
            "fix": "Confirme MA_API_URL, o token e a associação em /devices.",
        },
    },
    "en": {
        "addon_installed": {
            "title": "Add-on installed",
            "description": "The Alexa MA Skill add-on must exist in the Supervisor.",
            "fix": "Add the repository to the add-on store and install the add-on.",
        },
        "addon_started": {
            "title": "Add-on running",
            "description": "The add-on must be running and answer its internal service.",
            "fix": "Start the add-on from the panel and check its logs.",
        },
        "panel_credentials": {
            "title": "Panel credentials",
            "description": "The integration must authenticate to /status and /setup.",
            "fix": "Set APP_USERNAME and APP_PASSWORD in the add-on options and restart.",
        },
        "skill_hostname": {
            "title": "Public skill hostname",
            "description": "Alexa uses this address to call the skill.",
            "fix": "Set a bare hostname, for example skill.example.com.",
        },
        "ma_hostname": {
            "title": "Stream hostname",
            "description": "Public address used for Music Assistant audio.",
            "fix": "Set the stream hostname or accept the audio limitations.",
        },
        "local_setup": {
            "title": "Local setup access",
            "description": "Open the local add-on panel and complete the setup.",
            "fix": "Open http://<HA_IP>:5000/setup on the local network.",
        },
        "amazon_auth": {
            "title": "Amazon authorization",
            "description": "Amazon sign-in and authorization are manual.",
            "fix": "Use the correct account and complete authorization in the setup panel.",
        },
        "skill_created": {
            "title": "Skill created or reused",
            "description": "The script looks for skills named 'Music Assistant'.",
            "fix": "Review existing skills and confirm you accept the behaviour.",
        },
        "skill_id_obtained": {
            "title": "Skill ID obtained",
            "description": "The ID appears in the setup logs as 'Done. Skill ID:'.",
            "fix": "Copy the amzn1.ask.skill... value shown in the panel.",
        },
        "skill_id_configured": {
            "title": "Skill ID configured",
            "description": "The add-on must use the ID of the skill calling its endpoint.",
            "fix": "Set SKILL_ID in the options and restart the add-on.",
        },
        "skill_enabled": {
            "title": "Skill enabled in Alexa",
            "description": "The skill must be enabled in the correct Alexa account.",
            "fix": "Open Skills > Your Skills > Dev and enable the skill.",
        },
        "provider_configured": {
            "title": "Alexa provider in Music Assistant",
            "description": "MA must send the stream to the add-on.",
            "fix": "Use the internal URL, panel basic auth, and the correct Amazon domain.",
        },
        "ma_api_tested": {
            "title": "Music Assistant API tested",
            "description": "The WebSocket API on port 8095 must respond.",
            "fix": "Set MA_API_URL and the token when the API requires authentication.",
        },
        "stream_public": {
            "title": "Public stream validated",
            "description": "The stream hostname must answer over HTTPS.",
            "fix": "Check DNS, the certificate, and the stream route in the tunnel.",
        },
        "playback_tested": {
            "title": "Playback tested",
            "description": "Audio must play on a real Echo.",
            "fix": "Start playback in Music Assistant and confirm on the Echo.",
        },
        "commands_tested": {
            "title": "Commands tested",
            "description": "Test next, previous, and pause through Alexa.",
            "fix": "Check MA_API_URL, the token, and the mapping on /devices.",
        },
    },
}

_INVALIDATION: dict[str, tuple[str, ...]] = {
    "ADDON_SLUG": (
        "local_setup",
        "skill_created",
        "skill_enabled",
        "provider_configured",
        "ma_api_tested",
        "playback_tested",
        "commands_tested",
    ),
    "SKILL_HOSTNAME": (
        "skill_created",
        "playback_tested",
        "commands_tested",
    ),
    "MA_HOSTNAME": ("provider_configured", "playback_tested"),
    "LOCALE": (
        "skill_created",
        "skill_enabled",
        "playback_tested",
        "commands_tested",
    ),
    "SKILL_ID": ("skill_enabled", "commands_tested"),
    "MA_API_URL": ("provider_configured", "ma_api_tested", "commands_tested"),
    "MA_API_TOKEN": ("provider_configured", "ma_api_tested", "commands_tested"),
    "APP_USERNAME": (
        "local_setup",
        "provider_configured",
        "ma_api_tested",
        "commands_tested",
    ),
    "APP_PASSWORD": (
        "local_setup",
        "provider_configured",
        "ma_api_tested",
        "commands_tested",
    ),
    "BASE_URL": ("local_setup", "provider_configured"),
}

_SKILL_ID_RE = re.compile(r"^amzn1\.ask\.skill\.[0-9A-Za-z-]+$")


def _confirmed(confirmations: Mapping[str, Any], step_id: str) -> bool:
    value = confirmations.get(step_id)
    if isinstance(value, dict):
        return bool(value.get("at"))
    return bool(value)


def _dependent_manual_steps(step_id: str) -> set[str]:
    """Return manual steps that depend on the given step, directly or not."""
    result: set[str] = set()
    seen: set[str] = set()
    frontier = {step_id}
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        for definition in STEP_DEFINITIONS:
            if current not in definition.dependencies or definition.id in seen:
                continue
            if definition.mode is StepMode.MANUAL:
                result.add(definition.id)
            frontier.add(definition.id)
    return result


class ChecklistManager:
    """Persist manual confirmations for the setup checklist."""

    def __init__(
        self,
        store: Store[dict[str, Any]],
        data: dict[str, Any] | None,
    ) -> None:
        """Initialize the manager from stored data."""
        self._store = store
        raw = data.get("confirmations") if isinstance(data, dict) else None
        self._confirmations: dict[str, dict[str, str]] = {}
        if isinstance(raw, dict):
            for key, value in raw.items():
                if isinstance(key, str) and isinstance(value, dict):
                    self._confirmations[key] = {
                        "at": str(value.get("at") or ""),
                    }

    @property
    def confirmations(self) -> dict[str, dict[str, str]]:
        """Return a copy of the persisted confirmations."""
        return dict(self._confirmations)

    def confirmed(self, step_id: str) -> bool:
        """Return True when the manual step is confirmed."""
        return _confirmed(self._confirmations, step_id)

    async def async_set(self, step_id: str, confirmed: bool) -> None:
        """Set or clear a manual confirmation."""
        if confirmed:
            self._confirmations[step_id] = {
                "at": datetime.now(UTC).isoformat(),
            }
        else:
            self._confirmations.pop(step_id, None)
            for dependent in _dependent_manual_steps(step_id):
                self._confirmations.pop(dependent, None)
        await self._async_save()

    async def async_clear_for_keys(self, keys: Iterable[str]) -> None:
        """Invalidate manual steps affected by changed configuration keys."""
        invalid: set[str] = set()
        for key in keys:
            invalid.update(_INVALIDATION.get(str(key).upper(), ()))
        changed = False
        for step_id in invalid:
            if self._confirmations.pop(step_id, None) is not None:
                changed = True
        if changed:
            await self._async_save()

    async def async_clear_all(self) -> None:
        """Clear all manual confirmations."""
        if self._confirmations:
            self._confirmations.clear()
            await self._async_save()

    async def _async_save(self) -> None:
        try:
            await self._store.async_save({"confirmations": self._confirmations})
        except OSError as err:
            _LOGGER.warning("Could not save the setup checklist: %s", err)


def _valid_hostname(value: str) -> bool:
    """Return True for a simple bare hostname."""
    if not value or "://" in value:
        return False
    return not any(character in value for character in "/?#@\\ \t\r\n:")


def _valid_ma_api_url(value: str) -> bool:
    """Return True for an accepted MA API URL."""
    if not value:
        return False
    parsed = urlparse(value)
    return (
        parsed.scheme in {"http", "https", "ws", "wss"}
        and bool(parsed.netloc)
        and not parsed.username
        and not parsed.password
    )


def _valid_skill_id(value: str) -> bool:
    """Return True for the documented Alexa skill ID format."""
    return bool(_SKILL_ID_RE.fullmatch(value))


def _status_label(status: StepStatus, language: str) -> str:
    labels = {
        "pt": {
            StepStatus.NOT_STARTED: "Não iniciado",
            StepStatus.PENDING: "Pendente",
            StepStatus.CHECKING: "Em verificação",
            StepStatus.DONE: "Concluído",
            StepStatus.ATTENTION: "Atenção",
            StepStatus.BLOCKED: "Bloqueado",
            StepStatus.NOT_APPLICABLE: "Não aplicável",
        },
        "en": {
            StepStatus.NOT_STARTED: "Not started",
            StepStatus.PENDING: "Pending",
            StepStatus.CHECKING: "Checking",
            StepStatus.DONE: "Completed",
            StepStatus.ATTENTION: "Attention",
            StepStatus.BLOCKED: "Blocked",
            StepStatus.NOT_APPLICABLE: "Not applicable",
        },
    }
    return labels[language][status]


_RESULT_TEXTS: dict[str, dict[str, str]] = {
    "pt": {
        "manual_mode": "Execução externa; Supervisor não se aplica",
        "addon_found": "Add-on encontrado no Supervisor",
        "addon_missing": "Add-on não instalado",
        "addon_unknown": "Estado do add-on não confirmado",
        "service_ok": "Serviço interno respondeu",
        "service_no_response": "Contêiner em execução, serviço sem resposta",
        "addon_stopped": "Add-on parado ou inacessível",
        "auth_ok": "Autenticação do painel aceita",
        "auth_unverified": "Autenticação ainda não verificada",
        "hostname_missing": "Hostname não configurado",
        "hostname_invalid": "Hostname com formato inválido",
        "hostname_valid": "Hostname com formato válido (DNS não testado)",
        "ma_hostname_missing": "Sem hostname de stream; áudio limitado",
        "ma_hostname_invalid": "Hostname de stream inválido",
        "ma_hostname_valid": "Hostname de stream com formato válido",
        "user_confirmed": "Confirmado pelo usuário",
        "awaiting_confirmation": "Aguardando confirmação",
        "manual_pending": "Ação manual pendente",
        "id_detected": "ID detectado pelo add-on",
        "id_from_user": "ID configurado pelo usuário",
        "id_invalid": "ID configurado com formato inválido",
        "id_missing": "Nenhum Skill ID disponível",
        "skill_id_missing": "SKILL_ID não configurado",
        "id_matches": "ID corresponde ao detectado",
        "id_differs": "ID diferente do detectado",
        "id_unverified": "ID configurado, correspondência não verificada",
        "ma_url_missing": "MA_API_URL não configurada",
        "ma_url_invalid": "MA_API_URL inválida",
        "ma_test_confirmed": "Teste da API confirmado pelo usuário",
        "ma_test_pending": "Teste da API do MA pendente",
        "stream_hostname_missing": "Sem hostname de stream",
        "stream_missing": "Nenhum stream recebido do MA",
        "stream_ok": "Stream alcançável por HTTPS",
        "stream_fail": "Stream não alcançável por HTTPS",
        "test_pending": "Teste manual pendente",
        "commands_not_configured": "Comandos não configurados",
        "blocked_dependency": "Dependência pendente",
        "not_started": "Não verificado",
    },
    "en": {
        "manual_mode": "External deployment; the Supervisor does not apply",
        "addon_found": "Add-on found in the Supervisor",
        "addon_missing": "Add-on not installed",
        "addon_unknown": "Add-on state not confirmed",
        "service_ok": "Internal service answered",
        "service_no_response": "Container running, service not answering",
        "addon_stopped": "Add-on stopped or unreachable",
        "auth_ok": "Panel authentication accepted",
        "auth_unverified": "Authentication not verified yet",
        "hostname_missing": "Hostname not configured",
        "hostname_invalid": "Hostname format invalid",
        "hostname_valid": "Hostname format valid (DNS not tested)",
        "ma_hostname_missing": "No stream hostname; audio limited",
        "ma_hostname_invalid": "Stream hostname invalid",
        "ma_hostname_valid": "Stream hostname format valid",
        "user_confirmed": "Confirmed by the user",
        "awaiting_confirmation": "Waiting for confirmation",
        "manual_pending": "Manual action pending",
        "id_detected": "ID detected by the add-on",
        "id_from_user": "ID provided by the user",
        "id_invalid": "Configured ID has an invalid format",
        "id_missing": "No Skill ID available",
        "skill_id_missing": "SKILL_ID not configured",
        "id_matches": "ID matches the detected one",
        "id_differs": "ID differs from the detected one",
        "id_unverified": "ID configured, match not verified",
        "ma_url_missing": "MA_API_URL not configured",
        "ma_url_invalid": "MA_API_URL invalid",
        "ma_test_confirmed": "API test confirmed by the user",
        "ma_test_pending": "Music Assistant API test pending",
        "stream_hostname_missing": "No stream hostname",
        "stream_missing": "No stream received from MA",
        "stream_ok": "Stream reachable over HTTPS",
        "stream_fail": "Stream not reachable over HTTPS",
        "test_pending": "Manual test pending",
        "commands_not_configured": "Commands not configured",
        "blocked_dependency": "Dependency pending",
        "not_started": "Not checked",
    },
}


def _step_status(
    step_id: str,
    config: Mapping[str, Any],
    data: AlexaMaSkillData,
    confirmations: Mapping[str, Any],
) -> tuple[StepStatus, str]:
    """Return the status and a localizable result code for one step."""
    skill_hostname = str(config.get(CONF_SKILL_HOSTNAME) or "").strip()
    ma_hostname = str(config.get(CONF_MA_HOSTNAME) or "").strip()
    skill_id = str(config.get(CONF_SKILL_ID) or "").strip()
    ma_api_url = str(config.get(CONF_MA_API_URL) or "").strip()

    if step_id == "addon_installed":
        if not bool(config.get(CONF_MANAGED, True)):
            return StepStatus.NOT_APPLICABLE, "manual_mode"
        if data.addon_installed is True:
            return StepStatus.DONE, "addon_found"
        if data.addon_installed is False:
            return StepStatus.BLOCKED, "addon_missing"
        return StepStatus.PENDING, "addon_unknown"
    if step_id == "addon_started":
        if data.reachable:
            return StepStatus.DONE, "service_ok"
        if data.container_online:
            return StepStatus.ATTENTION, "service_no_response"
        return StepStatus.PENDING, "addon_stopped"
    if step_id == "panel_credentials":
        if data.reachable:
            return StepStatus.DONE, "auth_ok"
        return StepStatus.PENDING, "auth_unverified"
    if step_id == "skill_hostname":
        if not skill_hostname:
            return StepStatus.PENDING, "hostname_missing"
        if not _valid_hostname(skill_hostname):
            return StepStatus.ATTENTION, "hostname_invalid"
        return StepStatus.DONE, "hostname_valid"
    if step_id == "ma_hostname":
        if not ma_hostname:
            return StepStatus.ATTENTION, "ma_hostname_missing"
        if not _valid_hostname(ma_hostname):
            return StepStatus.ATTENTION, "ma_hostname_invalid"
        return StepStatus.DONE, "ma_hostname_valid"
    if step_id == "local_setup":
        return (
            (StepStatus.DONE, "user_confirmed")
            if _confirmed(confirmations, step_id)
            else (StepStatus.PENDING, "awaiting_confirmation")
        )
    if step_id in (
        "amazon_auth",
        "skill_created",
        "skill_enabled",
        "provider_configured",
    ):
        return (
            (StepStatus.DONE, "user_confirmed")
            if _confirmed(confirmations, step_id)
            else (StepStatus.PENDING, "manual_pending")
        )
    if step_id == "skill_id_obtained":
        detected = data.detected_skill_id
        if detected:
            return StepStatus.DONE, "id_detected"
        if skill_id:
            if _valid_skill_id(skill_id):
                return StepStatus.DONE, "id_from_user"
            return StepStatus.ATTENTION, "id_invalid"
        return StepStatus.PENDING, "id_missing"
    if step_id == "skill_id_configured":
        if not skill_id:
            return StepStatus.PENDING, "skill_id_missing"
        if data.skill_id_matches is True:
            return StepStatus.DONE, "id_matches"
        if data.skill_id_matches is False:
            return StepStatus.ATTENTION, "id_differs"
        return StepStatus.ATTENTION, "id_unverified"
    if step_id == "ma_api_tested":
        if not ma_api_url:
            return StepStatus.NOT_APPLICABLE, "ma_url_missing"
        if not _valid_ma_api_url(ma_api_url):
            return StepStatus.ATTENTION, "ma_url_invalid"
        if _confirmed(confirmations, step_id):
            return StepStatus.DONE, "ma_test_confirmed"
        return StepStatus.PENDING, "ma_test_pending"
    if step_id == "stream_public":
        if not ma_hostname:
            return StepStatus.ATTENTION, "stream_hostname_missing"
        if not data.stream_url_present:
            return StepStatus.PENDING, "stream_missing"
        if data.https_stream_ok:
            return StepStatus.DONE, "stream_ok"
        return StepStatus.ATTENTION, "stream_fail"
    if step_id == "playback_tested":
        return (
            (StepStatus.DONE, "user_confirmed")
            if _confirmed(confirmations, step_id)
            else (StepStatus.PENDING, "test_pending")
        )
    if step_id == "commands_tested":
        if not ma_api_url:
            return StepStatus.NOT_APPLICABLE, "commands_not_configured"
        return (
            (StepStatus.DONE, "user_confirmed")
            if _confirmed(confirmations, step_id)
            else (StepStatus.PENDING, "test_pending")
        )
    return StepStatus.NOT_STARTED, "not_started"


def _skill_flags(
    data: AlexaMaSkillData,
) -> tuple[bool, bool, bool]:
    """Return skill found, endpoint matches, and testing enabled flags."""
    if data.detailed is None:
        return False, False, False
    text = html_to_text(data.detailed.skill_ask_html).lower()
    skill_found = (
        "interaction model" in text and "interaction model not found" not in text
    )
    endpoint_matches = "endpoint matches" in text
    testing_enabled = "testing enabled" in text
    return skill_found, endpoint_matches, testing_enabled


def _usage_example(language_key: str) -> str:
    """Return a localized usage example for the fixed invocation name."""
    if language_key == "pt":
        return f"Alexa, abra {INVOCATION_NAME}"
    return f"Alexa, open {INVOCATION_NAME}"


def _empty_data() -> AlexaMaSkillData:
    """Return a safe placeholder when the coordinator has no data yet."""
    return AlexaMaSkillData(
        reachable=False,
        http_status=0,
        detailed=None,
        last_check=None,
        detailed_error="Add-on status unavailable",
        container_online=False,
        addon_installed=None,
        addon_hostname=None,
        addon_version=None,
        https_skill_ok=False,
        https_stream_ok=False,
        stream_url_present=False,
        detected_skill_id=None,
        configured_skill_id="",
        skill_id_matches=None,
        suggested_skill_id=None,
    )


def build_setup_checklist(
    config: dict[str, Any],
    data: AlexaMaSkillData | None,
    language: str,
    confirmations: Mapping[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build the 16-step setup checklist state and attributes."""
    if data is None:
        data = _empty_data()
    language_key = "pt" if str(language).lower().startswith("pt") else "en"
    text = _STEP_TEXTS[language_key]
    confirmations = confirmations or {}

    steps: list[dict[str, Any]] = []
    statuses: dict[str, StepStatus] = {}
    for definition in STEP_DEFINITIONS:
        status, result_code = _step_status(definition.id, config, data, confirmations)
        if definition.id != "addon_installed":
            dependencies_done = all(
                statuses.get(dependency) in (StepStatus.DONE, StepStatus.NOT_APPLICABLE)
                for dependency in definition.dependencies
            )
            if status is not StepStatus.NOT_APPLICABLE and not dependencies_done:
                status = StepStatus.BLOCKED
                result_code = "blocked_dependency"
        statuses[definition.id] = status
        step_text = text[definition.id]
        steps.append(
            {
                "id": definition.id,
                "title": step_text["title"],
                "description": step_text["description"],
                "status": status.value,
                "status_label": _status_label(status, language_key),
                "result": _RESULT_TEXTS[language_key][result_code],
                "mode": definition.mode.value,
                "dependencies": list(definition.dependencies),
                "optional": definition.optional,
                "how_to_fix": step_text["fix"],
                "done": status is StepStatus.DONE,
                "confirmed": _confirmed(confirmations, definition.id),
            }
        )

    applicable = [step for step in steps if step["status"] != StepStatus.NOT_APPLICABLE]
    done = [step for step in steps if step["status"] == StepStatus.DONE]
    pending = [step for step in steps if step["status"] == StepStatus.PENDING]
    blocked = [step for step in steps if step["status"] == StepStatus.BLOCKED]
    attention = [step for step in steps if step["status"] == StepStatus.ATTENTION]
    next_step = next(
        (
            step
            for step in steps
            if step["status"] in (StepStatus.PENDING, StepStatus.ATTENTION)
            and all(
                statuses.get(dependency) in (StepStatus.DONE, StepStatus.NOT_APPLICABLE)
                for dependency in step["dependencies"]
            )
        ),
        None,
    )
    if next_step is None:
        next_step = next(
            (step for step in steps if step["status"] == StepStatus.BLOCKED),
            None,
        )
    percent = round(len(done) * 100 / len(applicable)) if applicable else 100
    complete = all(step["status"] == StepStatus.DONE for step in applicable)

    skill_found, endpoint_matches, testing_enabled = _skill_flags(data)
    skill_hostname = str(config.get(CONF_SKILL_HOSTNAME) or "").strip()
    configured_skill_id = str(config.get(CONF_SKILL_ID) or "").strip()
    detected_skill_id = data.detected_skill_id
    suggested_skill_id = data.suggested_skill_id
    invocation = INVOCATION_NAME
    usage_example = _usage_example(language_key)
    managed = bool(config.get(CONF_MANAGED, True))
    locale = str(config.get(CONF_LOCALE) or DEFAULT_LOCALE)
    endpoint_url = f"https://{skill_hostname}/" if skill_hostname else None
    cloudflare_rule = (
        f'(http.host eq "{skill_hostname}" and not '
        '(http.request.uri.path eq "/" and http.request.method eq "POST"))'
        if skill_hostname
        else None
    )
    local_setup_url = (
        f"http://{data.addon_hostname or '<IP_DO_HOME_ASSISTANT>'}:5000/setup"
    )
    provider_api_url = f"http://{data.addon_hostname or '<slug-com-hifens>'}:5000"
    duplicate_warning = (
        "O script upstream procura skills chamadas 'Music Assistant'. "
        "Se houver mais de uma, apaga as extras e mantém a primeira."
        if language_key == "pt"
        else "The upstream script looks for skills named 'Music Assistant'. "
        "If more than one exists, it deletes the extras and keeps the first."
    )
    warnings = [
        "O login na Amazon é sempre manual."
        if language_key == "pt"
        else "The Amazon login is always manual.",
        duplicate_warning,
        (
            "O nome de exibição é 'Music Assistant' e o invocation é 'music assistant'."
            if language_key == "pt"
            else "The display name is 'Music Assistant' and the invocation is 'music assistant'."
        ),
        (
            "Exponha apenas POST /; mantenha /setup e /status na rede local."
            if language_key == "pt"
            else "Expose only POST /; keep /setup and /status on the local network."
        ),
        (
            "Use TLS 1.2 ou superior; TLS 1.3 não é suportado pela imagem upstream."
            if language_key == "pt"
            else "Use TLS 1.2 or newer; the upstream image does not support TLS 1.3."
        ),
    ]
    if not managed:
        warnings.append(
            "No modo manual, os valores precisam ser configurados no contêiner externo."
            if language_key == "pt"
            else "In manual mode, configure these values in the external container."
        )

    console_values = {
        "skill_name": SKILL_NAME,
        "invocation_name": invocation,
        "invocation_source": INVOCATION_SOURCE,
        "usage_example": usage_example,
        "endpoint_url": endpoint_url,
        "local_setup_url": local_setup_url,
        "provider_api_url": provider_api_url,
        "locale": locale,
        "skill_id": configured_skill_id or None,
        "detected_skill_id": detected_skill_id,
        "suggested_skill_id": suggested_skill_id,
        "amazon_console_url": AMAZON_CONSOLE_URL,
        "ssl_certificate_type": SSL_CERTIFICATE_TYPE,
        "testing_enabled": testing_enabled,
        "endpoint_matches": endpoint_matches,
    }
    attributes = {
        "skill_name": SKILL_NAME,
        "invocation_name": invocation,
        "invocation_source": INVOCATION_SOURCE,
        "usage_example": usage_example,
        "endpoint_url": endpoint_url,
        "local_setup_url": local_setup_url,
        "provider_api_url": provider_api_url,
        "locale": locale,
        "skill_id": configured_skill_id or None,
        "configured_skill_id": configured_skill_id or None,
        "detected_skill_id": detected_skill_id,
        "suggested_skill_id": suggested_skill_id,
        "skill_id_matches": data.skill_id_matches,
        "amazon_console_url": AMAZON_CONSOLE_URL,
        "ssl_certificate_type": SSL_CERTIFICATE_TYPE,
        "cloudflare_rule": cloudflare_rule,
        "skill_found": skill_found,
        "endpoint_matches": endpoint_matches,
        "testing_enabled": testing_enabled,
        "stream_url_present": data.stream_url_present,
        "https_stream_ok": data.https_stream_ok,
        "checklist": steps,
        "steps": steps,
        "manual_steps": [
            step
            for step in steps
            if step["mode"] == StepMode.MANUAL.value
            and step["status"]
            not in (StepStatus.NOT_APPLICABLE.value, StepStatus.BLOCKED.value)
        ],
        "progress": {
            "done": len(done),
            "pending": len(pending),
            "blocked": len(blocked),
            "attention": len(attention),
            "not_applicable": len(steps) - len(applicable),
            "total": len(steps),
            "applicable": len(applicable),
            "percent": percent,
            "complete": complete,
            "next_step": next_step["id"] if next_step else None,
            "next_step_title": next_step["title"] if next_step else None,
        },
        "next_actions": [
            step["how_to_fix"]
            for step in steps
            if step["status"] in (StepStatus.PENDING, StepStatus.BLOCKED)
        ][:8],
        "warnings": warnings,
        "duplicate_warning": duplicate_warning,
        "console_values": console_values,
    }
    if complete:
        state = "complete"
    elif not data.container_online and not data.reachable:
        state = "error"
    else:
        state = "incomplete"
    return state, attributes
