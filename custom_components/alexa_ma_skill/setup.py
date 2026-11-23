"""Setup checklist and Amazon console values for Alexa MA Skill."""

from __future__ import annotations

from typing import Any

from .const import (
    CONF_LOCALE,
    CONF_MANAGED,
    CONF_SKILL_HOSTNAME,
    CONF_SKILL_ID,
    DEFAULT_LOCALE,
)
from .coordinator import AlexaMaSkillData
from .util import html_to_text

SKILL_NAME = "Music Assistant"
AMAZON_CONSOLE_URL = "https://developer.amazon.com/alexa/console/ask"
SSL_CERTIFICATE_TYPE = "Wildcard"

INVOCATION_NAMES: dict[str, tuple[str, str | None]] = {
    "pt-BR": ("minha rádio", "Alexa, abra minha rádio"),
    "en-US": ("my radio", "Alexa, open my radio"),
    "en-GB": ("my radio", "Alexa, open my radio"),
    "en-AU": ("my radio", "Alexa, open my radio"),
    "en-CA": ("my radio", "Alexa, open my radio"),
    "en-IN": ("my radio", "Alexa, open my radio"),
    "de-DE": ("mein radio", "Alexa, öffne mein radio"),
    "es-ES": ("mi radio", "Alexa, abre mi radio"),
    "es-MX": ("mi radio", "Alexa, abre mi radio"),
    "fr-FR": ("ma radio", "Alexa, ouvre ma radio"),
    "fr-CA": ("", None),
    "it-IT": ("la mia radio", "Alexa, apri la mia radio"),
    "nl-NL": ("", None),
}

_TEXTS: dict[str, dict[str, Any]] = {
    "pt": {
        "addon_online": "Add-on em execução",
        "https_skill": "HTTPS público da skill",
        "skill_found": "Skill encontrada no console",
        "endpoint_matches": "Endpoint corresponde a SKILL_HOSTNAME",
        "testing_enabled": "Testing habilitado",
        "skill_id": "SKILL_ID configurado",
        "invocation": "Frase de invocação definida",
        "https_stream": "HTTPS do stream (quando houver stream)",
        "action_start": "Inicie o add-on e verifique os logs.",
        "action_https_skill": (
            "Verifique o DNS, o túnel e o certificado de SKILL_HOSTNAME."
        ),
        "action_setup": "Abra o /setup local e execute o setup da skill.",
        "action_endpoint": (
            "Ajuste o endpoint no console da Amazon ou execute o setup novamente."
        ),
        "action_testing": ("Habilite testing no console da Amazon (Development)."),
        "action_skill_id": ("Copie o Skill ID para as opções da integração/add-on."),
        "action_invocation": (
            "O locale selecionado não tem frase de invocação no upstream; "
            "use outro locale ou ajuste o modelo."
        ),
        "action_stream": ("Verifique o DNS, o túnel e o certificado de MA_HOSTNAME."),
        "warning_manual_login": "O login na Amazon é sempre manual.",
        "warning_extra_skills": (
            "O script upstream procura skills chamadas 'Music Assistant'. "
            "Se houver mais de uma, apaga as extras e mantém a primeira."
        ),
        "warning_display_name": (
            "O nome de exibição criado pelo manifesto é 'Music Assistant'; "
            "a frase de invocação vem do modelo de interação."
        ),
        "warning_public_exposure": (
            "Exponha apenas POST /; mantenha /setup e /status na rede local."
        ),
        "warning_tls": (
            "Use TLS 1.2 ou superior; TLS 1.3 não é suportado pela imagem upstream."
        ),
        "warning_certificate": (
            "O manifesto usa sslCertificateType: Wildcard; ajuste para Trusted "
            "se a Amazon recusar o endpoint."
        ),
        "warning_locale_invocation": (
            "Este locale não define frase de invocação no upstream; "
            "a criação da skill pode falhar."
        ),
        "warning_manual_mode": (
            "No modo manual, os valores precisam ser configurados no contêiner "
            "externo; a integração não altera o ambiente dele."
        ),
        "steps": [
            "Configure SKILL_HOSTNAME, MA_HOSTNAME e os túneis HTTPS.",
            "Abra http://<add-on>:5000/setup na rede local.",
            "Faça login na Amazon manualmente e cole o código.",
            "Aguarde o Skill ID e habilite testing.",
            "Salve o Skill ID nas opções da integração/add-on.",
            "Habilite a skill no app Alexa e teste a frase de invocação.",
        ],
    },
    "en": {
        "addon_online": "Add-on running",
        "https_skill": "Skill public HTTPS",
        "skill_found": "Skill found in the console",
        "endpoint_matches": "Endpoint matches SKILL_HOSTNAME",
        "testing_enabled": "Testing enabled",
        "skill_id": "SKILL_ID configured",
        "invocation": "Invocation name defined",
        "https_stream": "Stream HTTPS (when a stream exists)",
        "action_start": "Start the add-on and check its logs.",
        "action_https_skill": (
            "Check DNS, the tunnel, and the SKILL_HOSTNAME certificate."
        ),
        "action_setup": "Open the local /setup and run the skill setup.",
        "action_endpoint": (
            "Fix the endpoint in the Amazon console or run setup again."
        ),
        "action_testing": (
            "Enable testing in the Amazon developer console (Development)."
        ),
        "action_skill_id": ("Copy the Skill ID to the integration/add-on options."),
        "action_invocation": (
            "The selected locale has no invocation name upstream; "
            "use another locale or adjust the model."
        ),
        "action_stream": ("Check DNS, the tunnel, and the MA_HOSTNAME certificate."),
        "warning_manual_login": "The Amazon login is always manual.",
        "warning_extra_skills": (
            "The upstream script looks for skills named 'Music Assistant'. "
            "If more than one exists, it deletes the extras and keeps the first."
        ),
        "warning_display_name": (
            "The manifest creates the display name 'Music Assistant'; "
            "the invocation name comes from the interaction model."
        ),
        "warning_public_exposure": (
            "Expose only POST /; keep /setup and /status on the local network."
        ),
        "warning_tls": (
            "Use TLS 1.2 or newer; the upstream image does not support TLS 1.3."
        ),
        "warning_certificate": (
            "The manifest uses sslCertificateType: Wildcard; change it to Trusted "
            "if Amazon rejects the endpoint."
        ),
        "warning_locale_invocation": (
            "This locale has no invocation name upstream; skill creation may fail."
        ),
        "warning_manual_mode": (
            "In manual mode, configure these values in the external container; "
            "the integration does not change its environment."
        ),
        "steps": [
            "Configure SKILL_HOSTNAME, MA_HOSTNAME, and the HTTPS tunnels.",
            "Open http://<add-on>:5000/setup on the local network.",
            "Log in to Amazon manually and paste the code.",
            "Wait for the Skill ID and enable testing.",
            "Save the Skill ID in the integration/add-on options.",
            "Enable the skill in the Alexa app and test the invocation phrase.",
        ],
    },
}


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


def _invocation(locale: str) -> tuple[str, str | None]:
    """Return the invocation name and usage example for a locale."""
    return INVOCATION_NAMES.get(locale, ("", None))


def build_setup_checklist(
    config: dict[str, Any],
    data: AlexaMaSkillData,
    language: str,
) -> tuple[str, dict[str, Any]]:
    """Build the setup checklist state and attributes."""
    language_key = "pt" if str(language).lower().startswith("pt") else "en"
    text = _TEXTS[language_key]

    managed = bool(config.get(CONF_MANAGED, True))
    skill_hostname = str(config.get(CONF_SKILL_HOSTNAME) or "").strip()
    locale = str(config.get(CONF_LOCALE) or DEFAULT_LOCALE)
    skill_id = str(config.get(CONF_SKILL_ID) or "").strip()
    invocation, usage_example = _invocation(locale)
    skill_found, endpoint_matches, testing_enabled = _skill_flags(data)

    stream_present = data.stream_url_present
    stream_done: bool | None = data.https_stream_ok if stream_present else None

    checklist = [
        {"step": text["addon_online"], "done": data.container_online},
        {"step": text["https_skill"], "done": data.https_skill_ok},
        {"step": text["skill_found"], "done": skill_found},
        {"step": text["endpoint_matches"], "done": endpoint_matches},
        {"step": text["testing_enabled"], "done": testing_enabled},
        {"step": text["skill_id"], "done": bool(skill_id)},
        {"step": text["invocation"], "done": bool(invocation)},
        {"step": text["https_stream"], "done": stream_done},
    ]

    next_actions: list[str] = []
    if not data.container_online:
        next_actions.append(text["action_start"])
    if not data.https_skill_ok:
        next_actions.append(text["action_https_skill"])
    if not skill_found:
        next_actions.append(text["action_setup"])
    if not endpoint_matches:
        next_actions.append(text["action_endpoint"])
    if not testing_enabled:
        next_actions.append(text["action_testing"])
    if not skill_id:
        next_actions.append(text["action_skill_id"])
    if not invocation:
        next_actions.append(text["action_invocation"])
    if stream_present and not data.https_stream_ok:
        next_actions.append(text["action_stream"])

    warnings = [
        text["warning_manual_login"],
        text["warning_extra_skills"],
        text["warning_display_name"],
        text["warning_public_exposure"],
        text["warning_tls"],
        text["warning_certificate"],
    ]
    if not invocation:
        warnings.append(text["warning_locale_invocation"])
    if not managed:
        warnings.append(text["warning_manual_mode"])

    endpoint_url = f"https://{skill_hostname}/" if skill_hostname else None
    cloudflare_rule = (
        f'(http.host eq "{skill_hostname}" and not '
        '(http.request.uri.path eq "/" and http.request.method eq "POST"))'
        if skill_hostname
        else None
    )

    stream_ok = (not stream_present) or data.https_stream_ok
    complete = all(
        (
            data.container_online,
            data.https_skill_ok,
            skill_found,
            endpoint_matches,
            testing_enabled,
            bool(skill_id),
            bool(invocation),
            stream_ok,
        )
    )
    state = "complete" if complete else "incomplete"
    if not data.container_online:
        state = "error"

    console_values = {
        "skill_name": SKILL_NAME,
        "invocation_name": invocation or None,
        "usage_example": usage_example,
        "endpoint_url": endpoint_url,
        "locale": locale,
        "skill_id": skill_id or None,
        "amazon_console_url": AMAZON_CONSOLE_URL,
        "ssl_certificate_type": SSL_CERTIFICATE_TYPE,
        "testing_enabled": testing_enabled,
        "endpoint_matches": endpoint_matches,
    }

    attributes = {
        "skill_name": SKILL_NAME,
        "invocation_name": invocation or None,
        "usage_example": usage_example,
        "endpoint_url": endpoint_url,
        "locale": locale,
        "skill_id": skill_id or None,
        "amazon_console_url": AMAZON_CONSOLE_URL,
        "ssl_certificate_type": SSL_CERTIFICATE_TYPE,
        "cloudflare_rule": cloudflare_rule,
        "skill_found": skill_found,
        "endpoint_matches": endpoint_matches,
        "testing_enabled": testing_enabled,
        "stream_url_present": stream_present,
        "https_stream_ok": data.https_stream_ok,
        "checklist": checklist,
        "next_actions": next_actions,
        "steps": list(text["steps"]),
        "warnings": warnings,
        "console_values": console_values,
    }
    return state, attributes
